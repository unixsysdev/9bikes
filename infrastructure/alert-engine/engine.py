"""
Alert Engine Service - Continuous background alert evaluation
Runs independently in Kubernetes, separate from MCP server
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from influxdb_client_3 import InfluxDBClient3
import redis.asyncio as redis

# These imports will need to be adjusted for infrastructure deployment
# from ..database import db_manager  
# from ..models import AlertRule, Alert, Monitor
from .notification_manager import NotificationManager

logger = logging.getLogger(__name__)


class AlertEngine:
    """
    Continuous alert evaluation engine

    This service:
    1. Polls InfluxDB for new monitor data
    2. Evaluates alert rules against data points
    3. Generates alerts when conditions are met
    4. Respects cooldown periods
    5. Triggers notifications
    """

    def __init__(self):
        self.influx_client = self._init_influx_client()
        self.redis_client = None
        self.notification_manager = NotificationManager()
        self.evaluation_interval = int(os.getenv("ALERT_EVALUATION_INTERVAL", "30"))  # seconds
        self.running = False

    def _init_influx_client(self) -> Optional[InfluxDBClient3]:
        """Initialize InfluxDB client"""
        try:
            influx_url = os.getenv("INFLUXDB_URL", "http://localhost:8086")
            influx_token = os.getenv("INFLUXDB_TOKEN", "monitors_token")
            influx_org = os.getenv("INFLUXDB_ORG", "monitors")
            influx_database = os.getenv("INFLUXDB_DATABASE", "monitors")

            return InfluxDBClient3(host=influx_url, token=influx_token, org=influx_org, database=influx_database)
        except Exception as e:
            logger.warning(f"InfluxDB not available, using simulation mode: {e}")
            return None

    async def _init_redis(self):
        """Initialize Redis connection for cooldown tracking"""
        try:
            redis_url = os.getenv("REDIS_URL", "redis://:your_redis_password@localhost:6379/1")
            self.redis_client = redis.from_url(redis_url)
            await self.redis_client.ping()
            logger.info("Connected to Redis for cooldown tracking")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None

    async def start(self):
        """Start the alert engine main loop"""
        logger.info("🚨 Starting Alert Engine Service")
        await self._init_redis()
        self.running = True

        while self.running:
            try:
                await self._evaluation_cycle()
                await asyncio.sleep(self.evaluation_interval)
            except Exception as e:
                logger.error(f"Error in alert evaluation cycle: {e}")
                await asyncio.sleep(self.evaluation_interval)

    async def stop(self):
        """Stop the alert engine"""
        logger.info("🛑 Stopping Alert Engine Service")
        self.running = False
        if self.redis_client:
            await self.redis_client.close()

    async def _evaluation_cycle(self):
        """Single evaluation cycle - check all active alert rules"""
        logger.debug("🔍 Starting alert evaluation cycle")

        # Get all active alert rules
        with db_manager.get_db_session() as session:
            alert_rules = session.query(AlertRule).filter(AlertRule.is_active).all()

        logger.debug(f"Found {len(alert_rules)} active alert rules to evaluate")

        for rule in alert_rules:
            try:
                await self._evaluate_rule(rule)
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.id}: {e}")

    async def _evaluate_rule(self, rule: AlertRule):
        """Evaluate a single alert rule against recent data"""

        # Check cooldown - don't fire alerts too frequently
        if await self._is_in_cooldown(rule):
            logger.debug(f"Rule {rule.id} is in cooldown, skipping")
            return

        # Get recent data for this monitor
        monitor_data = await self._get_recent_monitor_data(rule.monitor_id)
        if not monitor_data:
            logger.debug(f"No recent data for monitor {rule.monitor_id}")
            return

        # Evaluate condition against data
        triggered = self._evaluate_condition(rule.condition, monitor_data)

        if triggered:
            logger.info(f"🔥 Alert rule {rule.id} triggered: {rule.title}")
            await self._create_alert(rule, monitor_data)
            await self._set_cooldown(rule)

    async def _get_recent_monitor_data(self, monitor_id: str) -> List[Dict[str, Any]]:
        """Get recent data points for a monitor from InfluxDB"""
        if not self.influx_client:
            # Simulation mode - generate fake data
            return self._generate_fake_monitor_data(monitor_id)

        try:
            # Query last 5 minutes of data
            query = f"""
            SELECT *
            FROM "monitor_data"
            WHERE "monitor_id" = '{monitor_id}'
            AND time >= now() - 5m
            ORDER BY time DESC
            LIMIT 100
            """

            result = self.influx_client.query(query)

            # Convert to list of dictionaries
            data_points = []
            for record in result:
                data_points.append(
                    {
                        "time": record.get("time"),
                        "monitor_id": record.get("monitor_id"),
                        "value": record.get("value"),
                        "price": record.get("price"),
                        "response_time": record.get("response_time"),
                        "status_code": record.get("status_code"),
                        "is_up": record.get("is_up"),
                        "symbol": record.get("symbol"),
                        "url": record.get("url"),
                    }
                )

            return data_points

        except Exception as e:
            logger.error(f"Error querying InfluxDB for monitor {monitor_id}: {e}")
            return []

    def _generate_fake_monitor_data(self, monitor_id: str) -> List[Dict[str, Any]]:
        """Generate fake data for simulation mode"""
        import random

        # Get monitor type to generate appropriate fake data
        with db_manager.get_db_session() as session:
            monitor = session.query(Monitor).filter(Monitor.id == monitor_id).first()
            if not monitor:
                return []

        data_points = []
        now = datetime.utcnow()

        for i in range(5):  # Last 5 data points
            timestamp = now - timedelta(minutes=i)

            if "crypto" in monitor.monitor_type:
                data_points.append(
                    {
                        "time": timestamp,
                        "monitor_id": monitor_id,
                        "price": random.uniform(40000, 70000),  # Bitcoin-like price
                        "symbol": "BTC",
                        "provider": "binance",
                    }
                )
            elif "http" in monitor.monitor_type or "website" in monitor.monitor_type:
                is_up = random.choice([True, True, True, False])  # 75% uptime
                data_points.append(
                    {
                        "time": timestamp,
                        "monitor_id": monitor_id,
                        "response_time": random.uniform(100, 2000),
                        "status_code": 200 if is_up else random.choice([500, 503, 404]),
                        "is_up": is_up,
                        "url": monitor.config.get("url", "https://example.com"),
                    }
                )
            else:
                # Generic numeric value
                data_points.append({"time": timestamp, "monitor_id": monitor_id, "value": random.uniform(0, 100)})

        return data_points

    def _evaluate_condition(self, condition: Dict[str, Any], data_points: List[Dict[str, Any]]) -> bool:
        """
        Evaluate alert condition against data points

        Condition format:
        {
            "type": "threshold",
            "field": "price",
            "operator": ">",
            "value": 50000,
            "aggregation": "latest"  # latest, avg, max, min
        }
        """
        if not data_points:
            return False

        condition_type = condition.get("type", "threshold")
        field = condition.get("field", "value")
        operator = condition.get("operator", ">")
        threshold_value = condition.get("value", 0)
        aggregation = condition.get("aggregation", "latest")

        # Extract field values from data points
        field_values = []
        for point in data_points:
            if field in point and point[field] is not None:
                field_values.append(float(point[field]))

        if not field_values:
            return False

        # Apply aggregation
        if aggregation == "latest":
            current_value = field_values[0]  # Most recent
        elif aggregation == "avg":
            current_value = sum(field_values) / len(field_values)
        elif aggregation == "max":
            current_value = max(field_values)
        elif aggregation == "min":
            current_value = min(field_values)
        else:
            current_value = field_values[0]

        # Evaluate condition
        if condition_type == "threshold":
            if operator == ">":
                return current_value > threshold_value
            elif operator == "<":
                return current_value < threshold_value
            elif operator == ">=":
                return current_value >= threshold_value
            elif operator == "<=":
                return current_value <= threshold_value
            elif operator == "==":
                return abs(current_value - threshold_value) < 0.001  # Float comparison
            elif operator == "!=":
                return abs(current_value - threshold_value) >= 0.001

        return False

    async def _is_in_cooldown(self, rule: AlertRule) -> bool:
        """Check if alert rule is in cooldown period"""
        if not self.redis_client:
            return False

        cooldown_key = f"alert_cooldown:{rule.id}"
        return await self.redis_client.exists(cooldown_key)

    async def _set_cooldown(self, rule: AlertRule):
        """Set cooldown period for alert rule"""
        if not self.redis_client:
            return

        cooldown_key = f"alert_cooldown:{rule.id}"
        cooldown_seconds = (rule.cooldown_minutes or 5) * 60
        await self.redis_client.setex(cooldown_key, cooldown_seconds, "1")

    async def _create_alert(self, rule: AlertRule, trigger_data: List[Dict[str, Any]]):
        """Create a new alert record and trigger notifications"""
        try:
            # Get user and monitor info
            with db_manager.get_db_session() as session:
                monitor = session.query(Monitor).filter(Monitor.id == rule.monitor_id).first()
                if not monitor:
                    logger.error(f"Monitor {rule.monitor_id} not found for alert rule {rule.id}")
                    return

                # Create alert record
                alert = Alert(
                    rule_id=rule.id,
                    monitor_id=rule.monitor_id,
                    user_id=rule.user_id,
                    severity=rule.severity,
                    title=rule.title,
                    data={"trigger_data": trigger_data[:3], "condition": rule.condition},  # Store trigger context
                    status="pending",
                )

                session.add(alert)
                session.flush()  # Get the alert ID
                session.commit()

                logger.info(f"✅ Created alert {alert.id} for rule {rule.id}")

                # Trigger notification
                await self.notification_manager.send_alert_notification(alert, monitor, rule)

        except Exception as e:
            logger.error(f"Error creating alert for rule {rule.id}: {e}")


async def main():
    """Main entry point for the alert engine service"""
    engine = AlertEngine()

    try:
        await engine.start()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await engine.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    asyncio.run(main())
