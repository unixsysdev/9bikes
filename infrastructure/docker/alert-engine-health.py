"""
Health check server for Alert Engine
Provides /health and /ready endpoints for Kubernetes probes
"""

import asyncio
import json
import logging
from datetime import datetime
from aiohttp import web
import os

logger = logging.getLogger(__name__)


class HealthServer:
    """Simple health check server for Kubernetes"""
    
    def __init__(self, port: int = 8080):
        self.port = port
        self.app = web.Application()
        self.setup_routes()
        self.start_time = datetime.utcnow()
        
    def setup_routes(self):
        """Setup health check routes"""
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/ready', self.readiness_check)
        self.app.router.add_get('/status', self.status_check)
    
    async def health_check(self, request):
        """Liveness probe - is the service running?"""
        return web.json_response({
            "status": "healthy",
            "service": "alert-engine",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds()
        })
    
    async def readiness_check(self, request):
        """Readiness probe - is the service ready to handle requests?"""
        
        # Check database connectivity
        try:
            from src.monitors_mcp.database import db_manager
            with db_manager.get_db_session() as session:
                session.execute("SELECT 1")
            db_ready = True
        except Exception as e:
            logger.error(f"Database not ready: {e}")
            db_ready = False
        
        # Check Redis connectivity
        try:
            import redis.asyncio as redis
            redis_url = os.getenv("REDIS_URL", "redis://:your_redis_password@localhost:6379/1")
            redis_client = redis.from_url(redis_url)
            await redis_client.ping()
            await redis_client.close()
            redis_ready = True
        except Exception as e:
            logger.error(f"Redis not ready: {e}")
            redis_ready = False
        
        all_ready = db_ready and redis_ready
        status_code = 200 if all_ready else 503
        
        return web.json_response({
            "status": "ready" if all_ready else "not_ready",
            "service": "alert-engine",
            "checks": {
                "database": "ready" if db_ready else "not_ready",
                "redis": "ready" if redis_ready else "not_ready"
            },
            "timestamp": datetime.utcnow().isoformat()
        }, status=status_code)
    
    async def status_check(self, request):
        """Extended status information"""
        return web.json_response({
            "service": "alert-engine",
            "version": "1.0.0",
            "environment": os.getenv("ENVIRONMENT", "development"),
            "start_time": self.start_time.isoformat(),
            "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds(),
            "config": {
                "evaluation_interval": os.getenv("ALERT_EVALUATION_INTERVAL", "30"),
                "log_level": os.getenv("LOG_LEVEL", "INFO"),
                "database_configured": bool(os.getenv("DATABASE_URL")),
                "redis_configured": bool(os.getenv("REDIS_URL")),
                "sendgrid_configured": bool(os.getenv("SENDGRID_API_KEY")),
                "slack_configured": bool(os.getenv("SLACK_WEBHOOK_URL")),
                "discord_configured": bool(os.getenv("DISCORD_WEBHOOK_URL")),
                "teams_configured": bool(os.getenv("TEAMS_WEBHOOK_URL"))
            }
        })
    
    async def start(self):
        """Start the health check server"""
        logger.info(f"🏥 Starting health check server on port {self.port}")
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        
        # Keep running
        while True:
            await asyncio.sleep(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    health_server = HealthServer()
    asyncio.run(health_server.start())
