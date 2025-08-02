"""
Base Monitor Container - Template for all monitor types
"""
import os
import json
import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional
import aiohttp
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

logger = logging.getLogger(__name__)

class BaseMonitor(ABC):
    """Base class for all monitor implementations"""
    
    def __init__(self):
        self.monitor_id = os.getenv("MONITOR_ID")
        self.config = json.loads(os.getenv("CONFIG", "{}"))
        self.influx_url = os.getenv("INFLUX_URL", "http://influxdb:8086")
        self.influx_token = os.getenv("INFLUX_TOKEN")
        self.influx_org = os.getenv("INFLUX_ORG", "monitors")
        self.influx_bucket = os.getenv("INFLUX_BUCKET", "monitor_data")
        
        # Health check server
        self.health_server = None
        self.is_healthy = False
        self.is_ready = False
        
        # InfluxDB client
        self.influx_client = None
        self.write_api = None
        
        self._initialize_influx()
        
    def _initialize_influx(self):
        """Initialize InfluxDB client"""
        try:
            if self.influx_token:
                self.influx_client = InfluxDBClient(
                    url=self.influx_url,
                    token=self.influx_token,
                    org=self.influx_org
                )
                self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)
                logger.info("InfluxDB client initialized")
            else:
                logger.warning("No InfluxDB token provided, data will not be persisted")
        except Exception as e:
            logger.error(f"Failed to initialize InfluxDB: {e}")
    
    async def start(self):
        """Start the monitor"""
        logger.info(f"Starting monitor {self.monitor_id}")
        
        # Start health check server
        await self._start_health_server()
        
        # Mark as ready
        self.is_ready = True
        self.is_healthy = True
        
        # Start monitoring loop
        try:
            await self.monitor_loop()
        except Exception as e:
            logger.error(f"Monitor loop failed: {e}")
            self.is_healthy = False
            raise
    
    async def _start_health_server(self):
        """Start HTTP health check server"""
        from aiohttp import web
        
        async def health_handler(request):
            status = 200 if self.is_healthy else 503
            return web.json_response({
                "status": "healthy" if self.is_healthy else "unhealthy",
                "monitor_id": self.monitor_id
            }, status=status)
        
        async def ready_handler(request):
            status = 200 if self.is_ready else 503
            return web.json_response({
                "status": "ready" if self.is_ready else "not_ready",
                "monitor_id": self.monitor_id
            }, status=status)
        
        app = web.Application()
        app.router.add_get("/health", health_handler)
        app.router.add_get("/ready", ready_handler)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", 8080)
        await site.start()
        
        logger.info("Health check server started on port 8080")
    
    async def write_data_point(self, measurement: str, fields: Dict[str, Any], 
                             tags: Optional[Dict[str, str]] = None):
        """Write a data point to InfluxDB"""
        if not self.write_api:
            logger.debug(f"No InfluxDB connection, skipping data point: {measurement}")
            return
        
        try:
            point = Point(measurement)
            
            # Add monitor metadata as tags
            point.tag("monitor_id", self.monitor_id)
            if tags:
                for key, value in tags.items():
                    point.tag(key, value)
            
            # Add fields
            for key, value in fields.items():
                point.field(key, value)
            
            # Add timestamp
            point.time(datetime.utcnow())
            
            # Write to InfluxDB
            self.write_api.write(bucket=self.influx_bucket, record=point)
            logger.debug(f"Wrote data point: {measurement}")
            
        except Exception as e:
            logger.error(f"Failed to write data point: {e}")
    
    @abstractmethod
    async def monitor_loop(self):
        """Main monitoring loop - implement in subclasses"""
        pass
    
    async def stop(self):
        """Stop the monitor"""
        logger.info(f"Stopping monitor {self.monitor_id}")
        self.is_healthy = False
        self.is_ready = False
        
        if self.influx_client:
            self.influx_client.close()

class WebsiteMonitor(BaseMonitor):
    """Website uptime/response time monitor"""
    
    async def monitor_loop(self):
        """Monitor website uptime and response time"""
        url = self.config.get("url")
        interval = self.config.get("interval", 60)  # Default 60 seconds
        
        if not url:
            raise ValueError("Website URL not configured")
        
        logger.info(f"Monitoring website: {url} every {interval}s")
        
        async with aiohttp.ClientSession() as session:
            while self.is_healthy:
                try:
                    start_time = datetime.utcnow()
                    
                    async with session.get(url, timeout=30) as response:
                        response_time = (datetime.utcnow() - start_time).total_seconds()
                        
                        # Write data point
                        await self.write_data_point(
                            measurement="website_check",
                            fields={
                                "response_time": response_time,
                                "status_code": response.status,
                                "is_up": response.status < 400
                            },
                            tags={
                                "url": url,
                                "monitor_type": "website"
                            }
                        )
                        
                        logger.info(f"Website check: {url} -> {response.status} ({response_time:.2f}s)")
                
                except Exception as e:
                    logger.error(f"Website check failed: {e}")
                    
                    # Write failure data point
                    await self.write_data_point(
                        measurement="website_check",
                        fields={
                            "response_time": -1,
                            "status_code": 0,
                            "is_up": False,
                            "error": str(e)
                        },
                        tags={
                            "url": url,
                            "monitor_type": "website"
                        }
                    )
                
                # Wait for next check
                await asyncio.sleep(interval)

class CryptoMonitor(BaseMonitor):
    """Cryptocurrency price monitor"""
    
    async def monitor_loop(self):
        """Monitor crypto prices"""
        symbol = self.config.get("symbol", "BTCUSDT")
        provider = self.config.get("provider", "binance")
        interval = self.config.get("interval", 30)  # Default 30 seconds
        
        logger.info(f"Monitoring crypto {symbol} on {provider} every {interval}s")
        
        if provider == "binance":
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        else:
            raise ValueError(f"Unsupported crypto provider: {provider}")
        
        async with aiohttp.ClientSession() as session:
            while self.is_healthy:
                try:
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            price = float(data["price"])
                            
                            # Write data point
                            await self.write_data_point(
                                measurement="crypto_price",
                                fields={
                                    "price": price
                                },
                                tags={
                                    "symbol": symbol,
                                    "provider": provider,
                                    "monitor_type": "crypto"
                                }
                            )
                            
                            logger.info(f"Crypto price: {symbol} -> ${price}")
                        else:
                            logger.error(f"Failed to fetch price: HTTP {response.status}")
                
                except Exception as e:
                    logger.error(f"Crypto price check failed: {e}")
                
                # Wait for next check
                await asyncio.sleep(interval)

# Monitor type registry
MONITOR_TYPES = {
    "website_monitoring": WebsiteMonitor,
    "crypto_trading": CryptoMonitor,
}

async def main():
    """Main entry point"""
    monitor_type = os.getenv("MONITOR_TYPE", "website_monitoring")
    
    monitor_class = MONITOR_TYPES.get(monitor_type)
    if not monitor_class:
        raise ValueError(f"Unknown monitor type: {monitor_type}")
    
    monitor = monitor_class()
    
    try:
        await monitor.start()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await monitor.stop()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
