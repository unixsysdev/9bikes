"""
InfluxDB Data Manager - Handles querying monitor data for analysis
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from influxdb_client import InfluxDBClient
import pandas as pd
import json

logger = logging.getLogger(__name__)

class MonitorDataManager:
    """Manages querying monitor data from InfluxDB"""
    
    def __init__(self):
        import os
        self.influx_url = os.getenv("INFLUX_URL", "http://localhost:8086")
        self.influx_token = os.getenv("INFLUX_TOKEN")
        self.influx_org = os.getenv("INFLUX_ORG", "monitors")
        self.influx_bucket = os.getenv("INFLUX_BUCKET", "monitor_data")
        
        self.client = None
        self.query_api = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize InfluxDB client"""
        try:
            if self.influx_token:
                self.client = InfluxDBClient(
                    url=self.influx_url,
                    token=self.influx_token,
                    org=self.influx_org
                )
                self.query_api = self.client.query_api()
                logger.info("InfluxDB data manager initialized")
            else:
                logger.warning("No InfluxDB token, data queries will be simulated")
        except Exception as e:
            logger.error(f"Failed to initialize InfluxDB client: {e}")
    
    async def get_monitor_data(self, monitor_id: str, time_range: str = "1h", 
                             measurement: str = None, limit: int = 1000) -> Dict[str, Any]:
        """Get data for a specific monitor"""
        try:
            if not self.query_api:
                return await self._simulate_data(monitor_id, time_range, measurement)
            
            # Build Flux query
            query = f'''
                from(bucket: "{self.influx_bucket}")
                |> range(start: -{time_range})
                |> filter(fn: (r) => r["monitor_id"] == "{monitor_id}")
            '''
            
            if measurement:
                query += f'|> filter(fn: (r) => r["_measurement"] == "{measurement}")'
            
            query += f'|> limit(n: {limit})'
            
            # Execute query
            result = self.query_api.query(query=query)
            
            # Convert to readable format
            data_points = []
            for table in result:
                for record in table.records:
                    data_points.append({
                        "time": record.get_time().isoformat(),
                        "measurement": record.get_measurement(),
                        "field": record.get_field(),
                        "value": record.get_value(),
                        "tags": record.values
                    })
            
            return {
                "monitor_id": monitor_id,
                "time_range": time_range,
                "measurement": measurement,
                "data_points": data_points,
                "count": len(data_points)
            }
            
        except Exception as e:
            logger.error(f"Failed to query monitor data: {e}")
            return {
                "error": str(e),
                "monitor_id": monitor_id
            }
    
    async def get_crypto_price_history(self, monitor_id: str, symbol: str = None, 
                                     time_range: str = "24h") -> Dict[str, Any]:
        """Get crypto price history with analysis-ready format"""
        try:
            if not self.query_api:
                return await self._simulate_crypto_data(monitor_id, symbol, time_range)
            
            # Build query for crypto price data
            query = f'''
                from(bucket: "{self.influx_bucket}")
                |> range(start: -{time_range})
                |> filter(fn: (r) => r["monitor_id"] == "{monitor_id}")
                |> filter(fn: (r) => r["_measurement"] == "crypto_price")
                |> filter(fn: (r) => r["_field"] == "price")
            '''
            
            if symbol:
                query += f'|> filter(fn: (r) => r["symbol"] == "{symbol}")'
            
            query += '|> sort(columns: ["_time"])'
            
            result = self.query_api.query(query=query)
            
            # Convert to analysis format
            prices = []
            for table in result:
                for record in table.records:
                    prices.append({
                        "timestamp": record.get_time().isoformat(),
                        "price": record.get_value(),
                        "symbol": record.values.get("symbol"),
                        "provider": record.values.get("provider")
                    })
            
            # Calculate basic statistics
            if prices:
                price_values = [p["price"] for p in prices]
                stats = {
                    "count": len(price_values),
                    "min": min(price_values),
                    "max": max(price_values),
                    "avg": sum(price_values) / len(price_values),
                    "latest": price_values[-1],
                    "change": price_values[-1] - price_values[0] if len(price_values) > 1 else 0,
                    "change_percent": ((price_values[-1] - price_values[0]) / price_values[0] * 100) if len(price_values) > 1 and price_values[0] > 0 else 0
                }
            else:
                stats = {}
            
            return {
                "monitor_id": monitor_id,
                "symbol": symbol,
                "time_range": time_range,
                "prices": prices,
                "statistics": stats
            }
            
        except Exception as e:
            logger.error(f"Failed to get crypto price history: {e}")
            return {"error": str(e)}
    
    async def get_website_uptime_stats(self, monitor_id: str, time_range: str = "24h") -> Dict[str, Any]:
        """Get website uptime statistics"""
        try:
            if not self.query_api:
                return await self._simulate_uptime_data(monitor_id, time_range)
            
            # Query for website check data
            query = f'''
                from(bucket: "{self.influx_bucket}")
                |> range(start: -{time_range})
                |> filter(fn: (r) => r["monitor_id"] == "{monitor_id}")
                |> filter(fn: (r) => r["_measurement"] == "website_check")
                |> sort(columns: ["_time"])
            '''
            
            result = self.query_api.query(query=query)
            
            # Process data
            checks = []
            response_times = []
            uptime_count = 0
            total_count = 0
            
            for table in result:
                for record in table.records:
                    field = record.get_field()
                    value = record.get_value()
                    
                    if field == "is_up":
                        total_count += 1
                        if value:
                            uptime_count += 1
                    elif field == "response_time" and value > 0:
                        response_times.append(value)
                    
                    checks.append({
                        "timestamp": record.get_time().isoformat(),
                        "field": field,
                        "value": value,
                        "url": record.values.get("url")
                    })
            
            # Calculate statistics
            uptime_percentage = (uptime_count / total_count * 100) if total_count > 0 else 0
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            return {
                "monitor_id": monitor_id,
                "time_range": time_range,
                "uptime_percentage": uptime_percentage,
                "total_checks": total_count,
                "successful_checks": uptime_count,
                "average_response_time": avg_response_time,
                "checks": checks[-100:]  # Last 100 checks
            }
            
        except Exception as e:
            logger.error(f"Failed to get uptime stats: {e}")
            return {"error": str(e)}
    
    async def query_custom(self, monitor_id: str, custom_query: str) -> Dict[str, Any]:
        """Execute custom Flux query for advanced analysis"""
        try:
            if not self.query_api:
                return {"error": "InfluxDB not available", "simulated": True}
            
            # Inject monitor_id filter for security
            if "monitor_id" not in custom_query:
                custom_query = custom_query.replace(
                    f'from(bucket: "{self.influx_bucket}")',
                    f'from(bucket: "{self.influx_bucket}") |> filter(fn: (r) => r["monitor_id"] == "{monitor_id}")'
                )
            
            result = self.query_api.query(query=custom_query)
            
            # Convert result to JSON-serializable format
            data = []
            for table in result:
                for record in table.records:
                    data.append({
                        "time": record.get_time().isoformat(),
                        "measurement": record.get_measurement(),
                        "field": record.get_field(),
                        "value": record.get_value(),
                        "tags": {k: v for k, v in record.values.items() if not k.startswith("_")}
                    })
            
            return {
                "query": custom_query,
                "results": data,
                "count": len(data)
            }
            
        except Exception as e:
            logger.error(f"Custom query failed: {e}")
            return {"error": str(e)}
    
    async def _simulate_crypto_data(self, monitor_id: str, symbol: str, time_range: str) -> Dict[str, Any]:
        """Simulate crypto data for development"""
        import random
        from datetime import datetime, timedelta
        
        # Generate fake Bitcoin price data
        base_price = 45000
        prices = []
        start_time = datetime.utcnow() - timedelta(hours=24)
        
        for i in range(100):  # 100 data points
            timestamp = start_time + timedelta(minutes=i * 14.4)  # Every ~14 minutes
            price = base_price + random.uniform(-2000, 2000)  # +/- $2000 variation
            prices.append({
                "timestamp": timestamp.isoformat(),
                "price": round(price, 2),
                "symbol": symbol or "BTCUSDT",
                "provider": "binance"
            })
        
        price_values = [p["price"] for p in prices]
        stats = {
            "count": len(price_values),
            "min": min(price_values),
            "max": max(price_values),
            "avg": sum(price_values) / len(price_values),
            "latest": price_values[-1],
            "change": price_values[-1] - price_values[0],
            "change_percent": ((price_values[-1] - price_values[0]) / price_values[0] * 100)
        }
        
        return {
            "monitor_id": monitor_id,
            "symbol": symbol or "BTCUSDT", 
            "time_range": time_range,
            "prices": prices,
            "statistics": stats,
            "simulated": True
        }
    
    async def _simulate_uptime_data(self, monitor_id: str, time_range: str) -> Dict[str, Any]:
        """Simulate uptime data for development"""
        import random
        
        total_checks = 144  # Every 10 minutes for 24h
        successful_checks = int(total_checks * 0.98)  # 98% uptime
        
        return {
            "monitor_id": monitor_id,
            "time_range": time_range,
            "uptime_percentage": 98.0,
            "total_checks": total_checks,
            "successful_checks": successful_checks,
            "average_response_time": 0.25,
            "simulated": True
        }
    
    async def _simulate_data(self, monitor_id: str, time_range: str, measurement: str) -> Dict[str, Any]:
        """Simulate general data for development"""
        return {
            "monitor_id": monitor_id,
            "time_range": time_range,
            "measurement": measurement,
            "data_points": [],
            "count": 0,
            "simulated": True,
            "message": "InfluxDB not available - this would contain real monitor data"
        }

# Global data manager instance
data_manager = MonitorDataManager()
