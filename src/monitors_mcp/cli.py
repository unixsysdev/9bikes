"""
Command-line interface for the Claude Monitor System
"""
import asyncio
import logging
import os
import sys
from typing import Optional
import click
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from .mcp_server import mcp_server
from .database import db_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@click.group()
def cli():
    """Claude Monitor System - MCP Server for distributed monitoring"""
    pass

@cli.command()
@click.option('--transport', type=click.Choice(['stdio', 'sse']), default='stdio',
              help='Transport mechanism for MCP communication')
@click.option('--host', default='localhost', help='Host for SSE transport')
@click.option('--port', default=9121, help='Port for SSE transport')
def start_mcp_server(transport: str, host: str, port: int):
    """Start the MCP server"""
    try:
        logger.info(f"Starting Claude Monitor System MCP Server...")
        logger.info(f"Transport: {transport}")
        if transport == 'sse':
            logger.info(f"SSE endpoint: http://{host}:{port}/sse")
        
        # FastMCP handles the event loop itself
        mcp_server.start(transport, host, port)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)

@cli.command()
def init_db():
    """Initialize the database"""
    try:
        logger.info("Initializing database...")
        db_manager.initialize_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)

@cli.command()
def test_connections():
    """Test database connections"""
    try:
        logger.info("Testing database connections...")
        results = db_manager.test_connections()
        
        for service, result in results.items():
            status = result['status']
            if status == 'connected':
                logger.info(f"✓ {service.upper()}: Connected")
            else:
                logger.error(f"✗ {service.upper()}: {result.get('error', 'Unknown error')}")
        
        all_connected = all(r['status'] == 'connected' for r in results.values())
        if not all_connected:
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        sys.exit(1)

@cli.command()
@click.option('--email', required=True, help='User email address')
def create_user(email: str):
    """Create a new user account"""
    try:
        from .auth import auth_manager
        
        logger.info(f"Creating user: {email}")
        user = auth_manager.get_or_create_user(email)
        logger.info(f"User created successfully: {user.id}")
        
    except Exception as e:
        logger.error(f"User creation failed: {e}")
        sys.exit(1)

@cli.command()
def list_users():
    """List all users"""
    try:
        from .models import User
        
        with db_manager.get_db_session() as session:
            users = session.query(User).all()
            
            if not users:
                logger.info("No users found")
                return
            
            logger.info(f"Found {len(users)} users:")
            for user in users:
                logger.info(f"  {user.id}: {user.email} (tier: {user.tier}, created: {user.created_at})")
                
    except Exception as e:
        logger.error(f"Failed to list users: {e}")
        sys.exit(1)

@cli.command()
@click.option('--user-id', required=True, help='User ID')
def list_monitors(user_id: str):
    """List monitors for a user"""
    try:
        from .models import Monitor
        
        with db_manager.get_db_session() as session:
            monitors = session.query(Monitor).filter(Monitor.user_id == user_id).all()
            
            if not monitors:
                logger.info(f"No monitors found for user {user_id}")
                return
            
            logger.info(f"Found {len(monitors)} monitors for user {user_id}:")
            for monitor in monitors:
                logger.info(f"  {monitor.id}: {monitor.name} ({monitor.monitor_type}) - {monitor.status}")
                
    except Exception as e:
        logger.error(f"Failed to list monitors: {e}")
        sys.exit(1)

@cli.command()
def setup():
    """Complete setup including database initialization and connection testing"""
    try:
        logger.info("Setting up Claude Monitor System...")
        
        # Initialize database
        logger.info("1. Initializing database...")
        db_manager.initialize_database()
        
        # Test connections
        logger.info("2. Testing connections...")
        results = db_manager.test_connections()
        
        all_connected = True
        for service, result in results.items():
            status = result['status']
            if status == 'connected':
                logger.info(f"   ✓ {service.upper()}: Connected")
            else:
                logger.error(f"   ✗ {service.upper()}: {result.get('error', 'Unknown error')}")
                all_connected = False
        
        if all_connected:
            logger.info("✓ Setup completed successfully!")
            logger.info("You can now start the MCP server with: monitors-mcp start-mcp-server")
        else:
            logger.error("✗ Setup failed - some connections are not working")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        sys.exit(1)


def main():
    """Main entry point"""
    cli()

if __name__ == '__main__':
    main()
