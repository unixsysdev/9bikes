"""
Notification Manager - Handles alert delivery via multiple channels
"""

import logging
import os
from datetime import datetime
from typing import Dict, List, Any

import httpx
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# These imports will need to be adjusted for infrastructure deployment
# from ..models import Alert, Monitor, AlertRule, User
# from ..database import db_manager

logger = logging.getLogger(__name__)


class NotificationManager:
    """
    Multi-channel notification delivery system

    Supports:
    - Email via SendGrid
    - Slack webhooks
    - Discord webhooks
    - Microsoft Teams webhooks
    - SMS via Twilio (future)
    """

    def __init__(self):
        self.sendgrid_client = self._init_sendgrid()
        self.http_client = httpx.AsyncClient(timeout=30.0)

    def _init_sendgrid(self):
        """Initialize SendGrid client"""
        api_key = os.getenv("SENDGRID_API_KEY")
        if api_key:
            return SendGridAPIClient(api_key)
        else:
            logger.warning("SendGrid API key not found, email notifications disabled")
            return None

    async def send_alert_notification(self, alert: Alert, monitor: Monitor, rule: AlertRule):
        """
        Send alert notification via all configured channels
        """
        logger.info(f"📢 Sending notifications for alert {alert.id}")

        # Get user info and notification preferences
        with db_manager.get_db_session() as session:
            user = session.query(User).filter(User.id == alert.user_id).first()
            if not user:
                logger.error(f"User {alert.user_id} not found for alert {alert.id}")
                return

        # Get notification preferences (from user profile or alert rule)
        notification_prefs = self._get_notification_preferences(user, rule)

        # Track delivery channels
        delivered_channels = []

        # Send email notification
        if notification_prefs.get("email", True):  # Default to email enabled
            try:
                await self._send_email_notification(alert, monitor, rule, user)
                delivered_channels.append("email")
                logger.info(f"✅ Email notification sent for alert {alert.id}")
            except Exception as e:
                logger.error(f"❌ Failed to send email for alert {alert.id}: {e}")

        # Send Slack notification
        slack_webhook = notification_prefs.get("slack_webhook")
        if slack_webhook:
            try:
                await self._send_slack_notification(alert, monitor, rule, slack_webhook)
                delivered_channels.append("slack")
                logger.info(f"✅ Slack notification sent for alert {alert.id}")
            except Exception as e:
                logger.error(f"❌ Failed to send Slack notification for alert {alert.id}: {e}")

        # Send Discord notification
        discord_webhook = notification_prefs.get("discord_webhook")
        if discord_webhook:
            try:
                await self._send_discord_notification(alert, monitor, rule, discord_webhook)
                delivered_channels.append("discord")
                logger.info(f"✅ Discord notification sent for alert {alert.id}")
            except Exception as e:
                logger.error(f"❌ Failed to send Discord notification for alert {alert.id}: {e}")

        # Send Teams notification
        teams_webhook = notification_prefs.get("teams_webhook")
        if teams_webhook:
            try:
                await self._send_teams_notification(alert, monitor, rule, teams_webhook)
                delivered_channels.append("teams")
                logger.info(f"✅ Teams notification sent for alert {alert.id}")
            except Exception as e:
                logger.error(f"❌ Failed to send Teams notification for alert {alert.id}: {e}")

        # Update alert with delivery status
        await self._update_alert_delivery_status(alert.id, delivered_channels)

    def _get_notification_preferences(self, user: User, rule: AlertRule) -> Dict[str, Any]:
        """Get notification preferences for user/rule"""
        # TODO: Implement user notification preferences in database
        # For now, use environment variables or defaults

        return {
            "email": True,
            "slack_webhook": os.getenv("SLACK_WEBHOOK_URL"),
            "discord_webhook": os.getenv("DISCORD_WEBHOOK_URL"),
            "teams_webhook": os.getenv("TEAMS_WEBHOOK_URL"),
            "email_format": "html",  # html or text
        }

    async def _send_email_notification(self, alert: Alert, monitor: Monitor, rule: AlertRule, user: User):
        """Send alert notification via email"""
        if not self.sendgrid_client:
            logger.warning("SendGrid not configured, cannot send email")
            return

        # Build email content
        subject = f"🚨 Alert: {rule.title}"

        # Get trigger data for context
        trigger_data = alert.data.get("trigger_data", []) if alert.data else []
        latest_value = "N/A"
        if trigger_data and len(trigger_data) > 0:
            first_point = trigger_data[0]
            # Try to find the monitored value
            condition = alert.data.get("condition", {}) if alert.data else {}
            field = condition.get("field", "value")
            if field in first_point:
                latest_value = first_point[field]

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                <h1 style="margin: 0; font-size: 24px;">🚨 Monitor Alert</h1>
                <p style="margin: 5px 0 0 0; opacity: 0.9;">{rule.title}</p>
            </div>
            
            <div style="background: white; padding: 20px; border: 1px solid #e1e5e9; border-radius: 0 0 8px 8px;">
                <div style="background: #f8f9fa; padding: 15px; border-radius: 6px; margin-bottom: 20px;">
                    <h3 style="margin: 0 0 10px 0; color: #333;">Alert Details</h3>
                    <p><strong>Monitor:</strong> {monitor.name}</p>
                    <p><strong>Severity:</strong> <span style="color: {'#dc3545' if alert.severity == 'critical' else '#fd7e14' if alert.severity == 'high' else '#ffc107' if alert.severity == 'medium' else '#28a745'}; font-weight: bold;">{alert.severity.upper()}</span></p>
                    <p><strong>Triggered:</strong> {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
                    <p><strong>Current Value:</strong> {latest_value}</p>
                </div>
                
                <div style="margin-bottom: 20px;">
                    <h4 style="color: #333; margin-bottom: 10px;">Condition</h4>
                    <div style="background: #e9ecef; padding: 10px; border-radius: 4px; font-family: monospace; font-size: 14px;">
                        {self._format_condition_for_email(condition)}
                    </div>
                </div>
                
                <div style="border-top: 1px solid #e1e5e9; padding-top: 15px; font-size: 12px; color: #666;">
                    <p>This alert was generated by the Claude Monitor System.</p>
                    <p>Alert ID: {alert.id}</p>
                </div>
            </div>
        </body>
        </html>
        """

        # Send email
        message = Mail(from_email="alerts@monitors.ai", to_emails=user.email, subject=subject, html_content=html_content)

        response = self.sendgrid_client.send(message)
        logger.info(f"Email sent with status: {response.status_code}")

    def _format_condition_for_email(self, condition: Dict[str, Any]) -> str:
        """Format alert condition for email display"""
        if not condition:
            return "No condition specified"

        field = condition.get("field", "value")
        operator = condition.get("operator", ">")
        value = condition.get("value", 0)
        aggregation = condition.get("aggregation", "latest")

        return f"{aggregation}({field}) {operator} {value}"

    async def _send_slack_notification(self, alert: Alert, monitor: Monitor, rule: AlertRule, webhook_url: str):
        """Send alert notification to Slack"""

        # Choose color based on severity
        color_map = {"low": "#28a745", "medium": "#ffc107", "high": "#fd7e14", "critical": "#dc3545"}

        # Get trigger context
        condition = alert.data.get("condition", {}) if alert.data else {}

        slack_message = {
            "attachments": [
                {
                    "color": color_map.get(alert.severity, "#666666"),
                    "title": f"🚨 {rule.title}",
                    "title_link": f"https://monitors.ai/alerts/{alert.id}",  # TODO: Implement web interface
                    "fields": [
                        {"title": "Monitor", "value": monitor.name, "short": True},
                        {"title": "Severity", "value": alert.severity.upper(), "short": True},
                        {"title": "Condition", "value": self._format_condition_for_slack(condition), "short": False},
                        {"title": "Triggered", "value": alert.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"), "short": True},
                    ],
                    "footer": "Claude Monitor System",
                    "footer_icon": "https://monitors.ai/icon.png",
                    "ts": int(alert.created_at.timestamp()),
                }
            ]
        }

        async with self.http_client as client:
            response = await client.post(webhook_url, json=slack_message)
            response.raise_for_status()

    def _format_condition_for_slack(self, condition: Dict[str, Any]) -> str:
        """Format condition for Slack display"""
        if not condition:
            return "No condition specified"

        field = condition.get("field", "value")
        operator = condition.get("operator", ">")
        value = condition.get("value", 0)
        aggregation = condition.get("aggregation", "latest")

        return f"`{aggregation}({field}) {operator} {value}`"

    async def _send_discord_notification(self, alert: Alert, monitor: Monitor, rule: AlertRule, webhook_url: str):
        """Send alert notification to Discord"""

        # Discord embed colors (decimal)
        color_map = {"low": 0x28A745, "medium": 0xFFC107, "high": 0xFD7E14, "critical": 0xDC3545}

        condition = alert.data.get("condition", {}) if alert.data else {}

        discord_message = {
            "embeds": [
                {
                    "title": f"🚨 {rule.title}",
                    "color": color_map.get(alert.severity, 0x666666),
                    "fields": [
                        {"name": "Monitor", "value": monitor.name, "inline": True},
                        {"name": "Severity", "value": alert.severity.upper(), "inline": True},
                        {"name": "Condition", "value": f"```{self._format_condition_for_slack(condition)}```", "inline": False},
                    ],
                    "footer": {"text": "Claude Monitor System"},
                    "timestamp": alert.created_at.isoformat(),
                }
            ]
        }

        async with self.http_client as client:
            response = await client.post(webhook_url, json=discord_message)
            response.raise_for_status()

    async def _send_teams_notification(self, alert: Alert, monitor: Monitor, rule: AlertRule, webhook_url: str):
        """Send alert notification to Microsoft Teams"""

        # Teams message card format
        condition = alert.data.get("condition", {}) if alert.data else {}

        teams_message = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": {"low": "28a745", "medium": "ffc107", "high": "fd7e14", "critical": "dc3545"}.get(alert.severity, "666666"),
            "summary": f"Alert: {rule.title}",
            "sections": [
                {
                    "activityTitle": f"🚨 {rule.title}",
                    "activitySubtitle": f"Monitor: {monitor.name}",
                    "facts": [
                        {"name": "Severity", "value": alert.severity.upper()},
                        {"name": "Condition", "value": self._format_condition_for_slack(condition)},
                        {"name": "Triggered", "value": alert.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")},
                    ],
                    "markdown": True,
                }
            ],
        }

        async with self.http_client as client:
            response = await client.post(webhook_url, json=teams_message)
            response.raise_for_status()

    async def _update_alert_delivery_status(self, alert_id: str, delivered_channels: List[str]):
        """Update alert record with delivery status"""
        try:
            with db_manager.get_db_session() as session:
                alert = session.query(Alert).filter(Alert.id == alert_id).first()
                if alert:
                    alert.delivered_channels = delivered_channels
                    alert.delivered_at = datetime.utcnow()
                    alert.status = "delivered" if delivered_channels else "failed"
                    session.commit()
                    logger.info(f"Updated delivery status for alert {alert_id}: {delivered_channels}")
        except Exception as e:
            logger.error(f"Error updating alert delivery status: {e}")

    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()
