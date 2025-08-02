#!/usr/bin/env python3
"""
Alert Engine Entry Point
Standalone service for continuous alert evaluation
"""

import asyncio
import logging
import signal
import sys
import os
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from monitors_mcp.alert_engine import AlertEngine

# Import health server
sys.path.insert(0, str(Path(__file__).parent.parent / "docker"))
from alert_engine_health import HealthServer


async def main():
    """Main entry point with graceful shutdown"""
    
    # Setup logging
    log_level = os.getenv("LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    logger = logging.getLogger(__name__)
    logger.info("🚀 Starting Alert Engine Service")
    
    # Create services
    alert_engine = AlertEngine()
    health_server = HealthServer()
    
    # Setup graceful shutdown
    shutdown_event = asyncio.Event()
    
    def signal_handler():
        logger.info("📡 Received shutdown signal")
        shutdown_event.set()
    
    # Register signal handlers
    if hasattr(signal, 'SIGTERM'):
        loop = asyncio.get_event_loop()
        loop.add_signal_handler(signal.SIGTERM, signal_handler)
        loop.add_signal_handler(signal.SIGINT, signal_handler)
    
    try:
        # Start both services concurrently
        await asyncio.gather(
            alert_engine.start(),
            health_server.start(),
            shutdown_event.wait()
        )
    except Exception as e:
        logger.error(f"❌ Service error: {e}")
    finally:
        logger.info("🛑 Shutting down Alert Engine")
        await alert_engine.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Alert Engine stopped")
        sys.exit(0)
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        sys.exit(1)
