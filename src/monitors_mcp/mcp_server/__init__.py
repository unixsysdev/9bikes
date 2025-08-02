"""
MCP Server implementation for Claude Monitor System
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent
import asyncio

from ..auth import auth_manager
from ..database import db_manager
from ..models import Monitor, Secret, AlertRule, Alert, User
from ..monitors.template_engine import MonitorTemplateEngine
from ..monitors.capabilities import MONITOR_CAPABILITIES

logger = logging.getLogger(__name__)


class MonitorsMCPServer:
    """Main MCP Server for Claude Monitor System using FastMCP"""

    def __init__(self):
        self.current_session: Optional[Dict[str, Any]] = None
        self.template_engine = MonitorTemplateEngine()
        self.mcp_server: Optional[FastMCP] = None

    def create_mcp_server(self, host: str = "127.0.0.1", port: int = 9122) -> FastMCP:
        """Create FastMCP server with all tools registered"""

        # Create FastMCP server
        self.mcp_server = FastMCP(name="claude-monitor-system", host=host, port=port)

        # Register all tools
        self._register_tools()

        return self.mcp_server

    def _register_tools(self):
        """Register all MCP tools with FastMCP"""

        @self.mcp_server.tool()
        async def authenticate(email: str = None, otp: str = None) -> str:
            """Authenticate user with email/OTP flow"""
            try:
                if not email and not otp:
                    # Check cached session
                    cached_session = auth_manager.load_cached_session()
                    if cached_session and auth_manager.validate_session(cached_session.get("token")):
                        self.current_session = cached_session
                        return json.dumps(
                            {"authenticated": True, "user_id": cached_session["user"]["id"], "email": cached_session["user"]["email"]}
                        )

                    return json.dumps(
                        {"authenticated": False, "message": "No cached session found. Please provide email to start authentication."}
                    )

                if email and not otp:
                    # Step 1: Generate and send OTP
                    generated_otp = auth_manager.generate_otp()
                    await auth_manager.store_otp(generated_otp, email)
                    success = await auth_manager.send_otp_email(email, generated_otp)

                    return json.dumps(
                        {
                            "success": success,
                            "message": (
                                f"OTP sent to {email}. Please check your email and provide the code." if success else "Failed to send OTP"
                            ),
                        }
                    )

                if email and otp:
                    # Step 2: Verify OTP and create session
                    verified_email = await auth_manager.verify_otp(otp)

                    if verified_email and (verified_email.decode() if isinstance(verified_email, bytes) else verified_email) == email:
                        # Create user if doesn't exist
                        user_data = auth_manager.get_or_create_user(email)

                        # Create session
                        session_data = auth_manager.create_session(user_data)
                        self.current_session = session_data
                        auth_manager.cache_session_locally(session_data)

                        return json.dumps(
                            {
                                "success": True,
                                "message": "Authentication successful",
                                "user": {"id": user_data["id"], "email": user_data["email"]},
                            }
                        )
                    else:
                        return json.dumps({"success": False, "message": "Invalid OTP or email mismatch"})

                return json.dumps({"success": False, "message": "Invalid authentication parameters"})

            except Exception as e:
                logger.error(f"Authentication error: {e}")
                return json.dumps({"success": False, "message": f"Authentication failed: {str(e)}"})

        @self.mcp_server.tool()
        async def get_monitor_capabilities() -> str:
            """Get available monitor types and their capabilities"""
            try:
                capabilities = {}
                for category, monitors in MONITOR_CAPABILITIES.items():
                    capabilities[category] = {"description": monitors["description"], "providers": list(monitors["providers"].keys())}

                return json.dumps({"success": True, "capabilities": capabilities})

            except Exception as e:
                logger.error(f"Error getting capabilities: {e}")
                return json.dumps({"success": False, "message": f"Failed to get capabilities: {str(e)}"})

        @self.mcp_server.tool()
        async def suggest_monitor(description: str) -> str:
            """Suggest monitor type and configuration based on user description"""
            try:
                inference = self.template_engine.infer_monitor_need(description)

                if inference["suggested_capabilities"]:
                    # Get the primary suggestion
                    primary_capability = inference["suggested_capabilities"][0]

                    # Get the default provider for this capability
                    capability_info = MONITOR_CAPABILITIES.get(primary_capability, {})
                    providers = list(capability_info.get("providers", {}).keys())
                    default_provider = providers[0] if providers else None

                    if default_provider:
                        # Build configuration wizard for this capability
                        wizard = self.template_engine.build_config_wizard(primary_capability, default_provider)

                        return json.dumps(
                            {
                                "success": True,
                                "suggestion": {
                                    "capability": primary_capability,
                                    "provider": default_provider,
                                    "confidence": inference["confidence"],
                                    "follow_up": inference["follow_up"],
                                },
                                "wizard": wizard,
                            }
                        )
                    else:
                        return json.dumps({"success": False, "message": f"No providers available for capability: {primary_capability}"})
                else:
                    return json.dumps({"success": False, "message": "Could not determine monitor type from description"})

            except Exception as e:
                logger.error(f"Error suggesting monitor: {e}")
                return json.dumps({"success": False, "message": f"Failed to suggest monitor: {str(e)}"})

        @self.mcp_server.tool()
        async def create_monitor(name: str, monitor_type: str, config: dict, secrets: dict = None) -> str:
            """Create a new monitor"""
            try:
                if not self.current_session:
                    return json.dumps({"success": False, "message": "Authentication required"})

                user_id = self.current_session["user"]["id"]

                # Store secrets if provided
                secret_ids = {}
                if secrets:
                    for key, value in secrets.items():
                        secret = Secret.create(user_id=user_id, name=f"{name}_{key}", value=value)
                        secret_ids[key] = secret.id

                # Create monitor
                monitor = Monitor.create(user_id=user_id, name=name, monitor_type=monitor_type, config=config, secret_ids=secret_ids)

                # Deploy monitor to Kubernetes
                from ..deployment import deployment_manager

                deployment_result = await deployment_manager.deploy_monitor(
                    monitor_id=monitor.id,
                    monitor_config={"user_id": user_id, "monitor_type": monitor_type, "config": config},
                    secrets=secrets,
                )

                # Update monitor with deployment info
                if deployment_result.get("deployment_id"):
                    from ..database import db_manager
                    from ..models import Monitor as MonitorModel

                    with db_manager.get_db_session() as session:
                        monitor_obj = session.query(MonitorModel).filter(MonitorModel.id == monitor.id).first()
                        if monitor_obj:
                            monitor_obj.deployment_id = deployment_result["deployment_id"]
                            monitor_obj.status = "deploying" if deployment_result["status"] == "deployed" else "error"
                            session.commit()

                return json.dumps(
                    {
                        "success": True,
                        "monitor": {
                            "id": monitor.id,
                            "name": monitor.name,
                            "type": monitor.monitor_type,
                            "status": monitor.status,
                            "created_at": monitor.created_at.isoformat(),
                            "deployment": deployment_result,
                        },
                    }
                )

            except Exception as e:
                logger.error(f"Error creating monitor: {e}")
                return json.dumps({"success": False, "message": f"Failed to create monitor: {str(e)}"})

        @self.mcp_server.tool()
        async def list_monitors() -> str:
            """List all monitors for the authenticated user"""
            try:
                if not self.current_session:
                    return json.dumps({"success": False, "message": "Authentication required"})

                user_id = self.current_session["user"]["id"]
                monitors = Monitor.get_by_user(user_id)

                monitor_list = []
                for monitor in monitors:
                    monitor_list.append(
                        {
                            "id": monitor.id,
                            "name": monitor.name,
                            "type": monitor.monitor_type,
                            "status": monitor.status,
                            "created_at": monitor.created_at.isoformat(),
                            "last_check": monitor.last_check.isoformat() if monitor.last_check else None,
                        }
                    )

                return json.dumps({"success": True, "monitors": monitor_list})

            except Exception as e:
                logger.error(f"Error listing monitors: {e}")
                return json.dumps({"success": False, "message": f"Failed to list monitors: {str(e)}"})

        @self.mcp_server.tool()
        async def get_monitor_status(monitor_id: str) -> str:
            """Get detailed status of a specific monitor"""
            try:
                if not self.current_session:
                    return json.dumps({"success": False, "message": "Authentication required"})

                user_id = self.current_session["user"]["id"]
                monitor = Monitor.get_by_id_and_user(monitor_id, user_id)

                if not monitor:
                    return json.dumps({"success": False, "message": "Monitor not found"})

                # Get recent alerts
                alerts = Alert.get_by_monitor(monitor_id, limit=10)
                alert_list = []
                for alert in alerts:
                    alert_list.append(
                        {"id": alert.id, "level": alert.level, "message": alert.message, "triggered_at": alert.triggered_at.isoformat()}
                    )

                return json.dumps(
                    {
                        "success": True,
                        "monitor": {
                            "id": monitor.id,
                            "name": monitor.name,
                            "type": monitor.monitor_type,
                            "status": monitor.status,
                            "config": monitor.config,
                            "created_at": monitor.created_at.isoformat(),
                            "last_check": monitor.last_check.isoformat() if monitor.last_check else None,
                            "recent_alerts": alert_list,
                        },
                    }
                )

            except Exception as e:
                logger.error(f"Error getting monitor status: {e}")
                return json.dumps({"success": False, "message": f"Failed to get monitor status: {str(e)}"})

        @self.mcp_server.tool()
        async def delete_monitor(monitor_id: str) -> str:
            """Delete a monitor"""
            try:
                if not self.current_session:
                    return json.dumps({"success": False, "message": "Authentication required"})

                user_id = self.current_session["user"]["id"]
                monitor = Monitor.get_by_id_and_user(monitor_id, user_id)

                if not monitor:
                    return json.dumps({"success": False, "message": "Monitor not found"})

                # Stop Kubernetes deployment
                if monitor.deployment_id:
                    from ..deployment import deployment_manager

                    await deployment_manager.stop_monitor(monitor.deployment_id)

                # Delete associated secrets
                for secret_id in monitor.secret_ids.values():
                    Secret.delete(secret_id)

                # Delete monitor
                Monitor.delete(monitor_id)

                return json.dumps({"success": True, "message": f"Monitor '{monitor.name}' deleted successfully"})

            except Exception as e:
                logger.error(f"Error deleting monitor: {e}")
                return json.dumps({"success": False, "message": f"Failed to delete monitor: {str(e)}"})

        @self.mcp_server.tool()
        async def get_deployment_status(monitor_id: str) -> str:
            """Get the Kubernetes deployment status of a monitor"""
            try:
                if not self.current_session:
                    return json.dumps({"success": False, "message": "Authentication required"})

                user_id = self.current_session["user"]["id"]
                monitor = Monitor.get_by_id_and_user(monitor_id, user_id)

                if not monitor:
                    return json.dumps({"success": False, "message": "Monitor not found"})

                if not monitor.deployment_id:
                    return json.dumps(
                        {"success": True, "deployment_status": {"status": "not_deployed", "message": "Monitor has not been deployed yet"}}
                    )

                # Get deployment status from Kubernetes
                from ..deployment import deployment_manager

                deployment_status = await deployment_manager.get_monitor_status(monitor.deployment_id)

                return json.dumps(
                    {
                        "success": True,
                        "monitor": {"id": monitor.id, "name": monitor.name, "deployment_id": monitor.deployment_id},
                        "deployment_status": deployment_status,
                    }
                )

            except Exception as e:
                logger.error(f"Error getting deployment status: {e}")
                return json.dumps({"success": False, "message": f"Failed to get deployment status: {str(e)}"})

        @self.mcp_server.tool()
        async def get_monitor_data(monitor_id: str, time_range: str = "1h", measurement: str = None) -> str:
            """Get collected data from a monitor for analysis"""
            try:
                if not self.current_session:
                    return json.dumps({"success": False, "message": "Authentication required"})

                user_id = self.current_session["user"]["id"]
                monitor = Monitor.get_by_id_and_user(monitor_id, user_id)

                if not monitor:
                    return json.dumps({"success": False, "message": "Monitor not found"})

                # Get data from InfluxDB
                from ..data_manager import data_manager

                data = await data_manager.get_monitor_data(monitor_id, time_range, measurement)

                return json.dumps(
                    {"success": True, "monitor": {"id": monitor.id, "name": monitor.name, "type": monitor.monitor_type}, "data": data}
                )

            except Exception as e:
                logger.error(f"Error getting monitor data: {e}")
                return json.dumps({"success": False, "message": f"Failed to get monitor data: {str(e)}"})

        @self.mcp_server.tool()
        async def get_crypto_analysis(monitor_id: str, time_range: str = "24h") -> str:
            """Get crypto price data with statistical analysis"""
            try:
                if not self.current_session:
                    return json.dumps({"success": False, "message": "Authentication required"})

                user_id = self.current_session["user"]["id"]
                monitor = Monitor.get_by_id_and_user(monitor_id, user_id)

                if not monitor:
                    return json.dumps({"success": False, "message": "Monitor not found"})

                # Get crypto price history
                from ..data_manager import data_manager

                crypto_data = await data_manager.get_crypto_price_history(monitor_id, None, time_range)

                return json.dumps(
                    {
                        "success": True,
                        "monitor": {"id": monitor.id, "name": monitor.name, "type": monitor.monitor_type},
                        "analysis": crypto_data,
                    }
                )

            except Exception as e:
                logger.error(f"Error getting crypto analysis: {e}")
                return json.dumps({"success": False, "message": f"Failed to get crypto analysis: {str(e)}"})

        @self.mcp_server.tool()
        async def get_website_uptime_analysis(monitor_id: str, time_range: str = "24h") -> str:
            """Get website uptime statistics and analysis"""
            try:
                if not self.current_session:
                    return json.dumps({"success": False, "message": "Authentication required"})

                user_id = self.current_session["user"]["id"]
                monitor = Monitor.get_by_id_and_user(monitor_id, user_id)

                if not monitor:
                    return json.dumps({"success": False, "message": "Monitor not found"})

                # Get uptime statistics
                from ..data_manager import data_manager

                uptime_data = await data_manager.get_website_uptime_stats(monitor_id, time_range)

                return json.dumps(
                    {
                        "success": True,
                        "monitor": {"id": monitor.id, "name": monitor.name, "type": monitor.monitor_type},
                        "uptime_analysis": uptime_data,
                    }
                )

            except Exception as e:
                logger.error(f"Error getting uptime analysis: {e}")
                return json.dumps({"success": False, "message": f"Failed to get uptime analysis: {str(e)}"})

        @self.mcp_server.tool()
        async def query_monitor_data_custom(monitor_id: str, query_description: str) -> str:
            """Execute custom data analysis queries on monitor data"""
            try:
                if not self.current_session:
                    return json.dumps({"success": False, "message": "Authentication required"})

                user_id = self.current_session["user"]["id"]
                monitor = Monitor.get_by_id_and_user(monitor_id, user_id)

                if not monitor:
                    return json.dumps({"success": False, "message": "Monitor not found"})

                # For now, convert natural language to basic queries
                # In a full implementation, you could use an LLM to generate Flux queries
                if "price" in query_description.lower() and "crypto" in monitor.monitor_type:
                    from ..data_manager import data_manager

                    time_range = "24h"
                    if "hour" in query_description:
                        time_range = "1h"
                    elif "week" in query_description:
                        time_range = "7d"

                    data = await data_manager.get_crypto_price_history(monitor_id, None, time_range)

                    return json.dumps(
                        {
                            "success": True,
                            "query": query_description,
                            "monitor": {"id": monitor.id, "name": monitor.name, "type": monitor.monitor_type},
                            "results": data,
                        }
                    )

                elif "uptime" in query_description.lower() and "website" in monitor.monitor_type:
                    from ..data_manager import data_manager

                    time_range = "24h"
                    if "hour" in query_description:
                        time_range = "1h"
                    elif "week" in query_description:
                        time_range = "7d"

                    data = await data_manager.get_website_uptime_stats(monitor_id, time_range)

                    return json.dumps(
                        {
                            "success": True,
                            "query": query_description,
                            "monitor": {"id": monitor.id, "name": monitor.name, "type": monitor.monitor_type},
                            "results": data,
                        }
                    )

                else:
                    return json.dumps(
                        {
                            "success": False,
                            "message": f"Could not understand query: '{query_description}'. Try asking for 'price data', 'uptime stats', etc.",
                        }
                    )

            except Exception as e:
                logger.error(f"Error executing custom query: {e}")
                return json.dumps({"success": False, "message": f"Failed to execute query: {str(e)}"})

        @self.mcp_server.tool()
        async def create_alert_rule(
            monitor_id: str, title: str, condition: dict, severity: str = "medium", cooldown_minutes: int = 5
        ) -> str:
            """Create a new alert rule for a monitor"""
            try:
                if not self.current_session:
                    return json.dumps({"success": False, "message": "Authentication required"})

                user_id = self.current_session["user"]["id"]

                # Validate monitor ownership
                monitor = Monitor.get_by_id_and_user(monitor_id, user_id)
                if not monitor:
                    return json.dumps({"success": False, "message": "Monitor not found or access denied"})

                # Validate condition format
                required_fields = ["type", "field", "operator", "value"]
                if not all(field in condition for field in required_fields):
                    return json.dumps({"success": False, "message": f"Condition must include: {required_fields}"})

                # Validate severity
                valid_severities = ["low", "medium", "high", "critical"]
                if severity not in valid_severities:
                    return json.dumps({"success": False, "message": f"Severity must be one of: {valid_severities}"})

                # Create alert rule
                from ..models import AlertRule

                with db_manager.get_db_session() as session:
                    rule = AlertRule(
                        monitor_id=monitor_id,
                        user_id=user_id,
                        title=title,
                        condition=condition,
                        severity=severity,
                        cooldown_minutes=cooldown_minutes,
                    )
                    session.add(rule)
                    session.flush()
                    session.commit()

                    return json.dumps(
                        {
                            "success": True,
                            "alert_rule": {
                                "id": rule.id,
                                "title": rule.title,
                                "monitor_id": rule.monitor_id,
                                "condition": rule.condition,
                                "severity": rule.severity,
                                "cooldown_minutes": rule.cooldown_minutes,
                                "is_active": rule.is_active,
                                "created_at": rule.created_at.isoformat(),
                            },
                        }
                    )

            except Exception as e:
                logger.error(f"Error creating alert rule: {e}")
                return json.dumps({"success": False, "message": f"Failed to create alert rule: {str(e)}"})

        @self.mcp_server.tool()
        async def list_alert_rules(monitor_id: str = None) -> str:
            """List alert rules for a monitor or all monitors"""
            try:
                if not self.current_session:
                    return json.dumps({"success": False, "message": "Authentication required"})

                user_id = self.current_session["user"]["id"]

                from ..models import AlertRule

                with db_manager.get_db_session() as session:
                    query = session.query(AlertRule).filter(AlertRule.user_id == user_id)

                    if monitor_id:
                        # Validate monitor ownership
                        monitor = Monitor.get_by_id_and_user(monitor_id, user_id)
                        if not monitor:
                            return json.dumps({"success": False, "message": "Monitor not found or access denied"})
                        query = query.filter(AlertRule.monitor_id == monitor_id)

                    rules = query.all()

                    rule_list = []
                    for rule in rules:
                        rule_list.append(
                            {
                                "id": rule.id,
                                "title": rule.title,
                                "monitor_id": rule.monitor_id,
                                "condition": rule.condition,
                                "severity": rule.severity,
                                "cooldown_minutes": rule.cooldown_minutes,
                                "is_active": rule.is_active,
                                "created_at": rule.created_at.isoformat(),
                            }
                        )

                    return json.dumps({"success": True, "alert_rules": rule_list})

            except Exception as e:
                logger.error(f"Error listing alert rules: {e}")
                return json.dumps({"success": False, "message": f"Failed to list alert rules: {str(e)}"})

        @self.mcp_server.tool()
        async def list_alerts(monitor_id: str = None, limit: int = 20) -> str:
            """List recent alerts for a monitor or all monitors"""
            try:
                if not self.current_session:
                    return json.dumps({"success": False, "message": "Authentication required"})

                user_id = self.current_session["user"]["id"]

                with db_manager.get_db_session() as session:
                    query = session.query(Alert).filter(Alert.user_id == user_id)

                    if monitor_id:
                        # Validate monitor ownership
                        monitor = Monitor.get_by_id_and_user(monitor_id, user_id)
                        if not monitor:
                            return json.dumps({"success": False, "message": "Monitor not found or access denied"})
                        query = query.filter(Alert.monitor_id == monitor_id)

                    alerts = query.order_by(Alert.created_at.desc()).limit(limit).all()

                    alert_list = []
                    for alert in alerts:
                        alert_list.append(
                            {
                                "id": alert.id,
                                "title": alert.title,
                                "monitor_id": alert.monitor_id,
                                "rule_id": alert.rule_id,
                                "severity": alert.severity,
                                "status": alert.status,
                                "delivered_channels": alert.delivered_channels,
                                "created_at": alert.created_at.isoformat(),
                                "delivered_at": alert.delivered_at.isoformat() if alert.delivered_at else None,
                                "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
                            }
                        )

                    return json.dumps({"success": True, "alerts": alert_list})

            except Exception as e:
                logger.error(f"Error listing alerts: {e}")
                return json.dumps({"success": False, "message": f"Failed to list alerts: {str(e)}"})

        @self.mcp_server.tool()
        async def acknowledge_alert(alert_id: str) -> str:
            """Acknowledge an alert to mark it as handled"""
            try:
                if not self.current_session:
                    return json.dumps({"success": False, "message": "Authentication required"})

                user_id = self.current_session["user"]["id"]

                with db_manager.get_db_session() as session:
                    alert = session.query(Alert).filter(Alert.id == alert_id, Alert.user_id == user_id).first()

                    if not alert:
                        return json.dumps({"success": False, "message": "Alert not found or access denied"})

                    alert.acknowledged_at = datetime.utcnow()
                    alert.status = "acknowledged"
                    session.commit()

                    return json.dumps(
                        {
                            "success": True,
                            "message": f"Alert {alert_id} acknowledged",
                            "alert": {"id": alert.id, "status": alert.status, "acknowledged_at": alert.acknowledged_at.isoformat()},
                        }
                    )

            except Exception as e:
                logger.error(f"Error acknowledging alert: {e}")
                return json.dumps({"success": False, "message": f"Failed to acknowledge alert: {str(e)}"})

        @self.mcp_server.tool()
        async def update_alert_rule(
            rule_id: str,
            title: str = None,
            condition: dict = None,
            severity: str = None,
            cooldown_minutes: int = None,
            is_active: bool = None,
        ) -> str:
            """Update an existing alert rule"""
            try:
                if not self.current_session:
                    return json.dumps({"success": False, "message": "Authentication required"})

                user_id = self.current_session["user"]["id"]

                from ..models import AlertRule

                with db_manager.get_db_session() as session:
                    rule = session.query(AlertRule).filter(AlertRule.id == rule_id, AlertRule.user_id == user_id).first()

                    if not rule:
                        return json.dumps({"success": False, "message": "Alert rule not found or access denied"})

                    # Update fields if provided
                    if title is not None:
                        rule.title = title
                    if condition is not None:
                        # Validate condition format
                        required_fields = ["type", "field", "operator", "value"]
                        if not all(field in condition for field in required_fields):
                            return json.dumps({"success": False, "message": f"Condition must include: {required_fields}"})
                        rule.condition = condition
                    if severity is not None:
                        valid_severities = ["low", "medium", "high", "critical"]
                        if severity not in valid_severities:
                            return json.dumps({"success": False, "message": f"Severity must be one of: {valid_severities}"})
                        rule.severity = severity
                    if cooldown_minutes is not None:
                        rule.cooldown_minutes = cooldown_minutes
                    if is_active is not None:
                        rule.is_active = is_active

                    session.commit()

                    return json.dumps(
                        {
                            "success": True,
                            "alert_rule": {
                                "id": rule.id,
                                "title": rule.title,
                                "monitor_id": rule.monitor_id,
                                "condition": rule.condition,
                                "severity": rule.severity,
                                "cooldown_minutes": rule.cooldown_minutes,
                                "is_active": rule.is_active,
                                "created_at": rule.created_at.isoformat(),
                            },
                        }
                    )

            except Exception as e:
                logger.error(f"Error updating alert rule: {e}")
                return json.dumps({"success": False, "message": f"Failed to update alert rule: {str(e)}"})

        @self.mcp_server.tool()
        async def delete_alert_rule(rule_id: str) -> str:
            """Delete an alert rule"""
            try:
                if not self.current_session:
                    return json.dumps({"success": False, "message": "Authentication required"})

                user_id = self.current_session["user"]["id"]

                from ..models import AlertRule

                with db_manager.get_db_session() as session:
                    rule = session.query(AlertRule).filter(AlertRule.id == rule_id, AlertRule.user_id == user_id).first()

                    if not rule:
                        return json.dumps({"success": False, "message": "Alert rule not found or access denied"})

                    session.delete(rule)
                    session.commit()

                    return json.dumps({"success": True, "message": f"Alert rule {rule_id} deleted"})

            except Exception as e:
                logger.error(f"Error deleting alert rule: {e}")
                return json.dumps({"success": False, "message": f"Failed to delete alert rule: {str(e)}"})

    def start(self, transport_type: str, host: str, port: int):
        """Start the MCP server"""
        logger.info("Starting Claude Monitor System MCP Server...")

        # Initialize database
        db_manager.initialize_database()

        # Test connections
        results = db_manager.test_connections()
        logger.info(f"Database connections: {results}")

        # Create and run FastMCP server
        mcp = self.create_mcp_server(host, port)
        logger.info(f"Starting FastMCP server with transport: {transport_type}")

        # Let FastMCP handle the transport (this will block)
        mcp.run(transport=transport_type)


# Global server instance
mcp_server = MonitorsMCPServer()
