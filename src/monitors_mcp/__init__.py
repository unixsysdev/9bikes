"""
Claude Monitor System - MCP Server
A distributed monitoring system enabling Claude to orchestrate long-running data collection processes.
"""

__version__ = "0.1.0"

from .mcp_server import mcp_server
from .database import db_manager
from .auth import auth_manager
from .models import User, Monitor, Secret, Alert, AlertRule

__all__ = [
    "mcp_server",
    "db_manager", 
    "auth_manager",
    "User",
    "Monitor", 
    "Secret",
    "Alert",
    "AlertRule"
]
