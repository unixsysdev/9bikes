"""
Alert Engine Module

Continuous background alert evaluation and notification system.
Runs independently in Kubernetes, separate from MCP server.
"""

from .engine import AlertEngine
from .notification_manager import NotificationManager

__all__ = ["AlertEngine", "NotificationManager"]
