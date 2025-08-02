"""
Database connection and initialization
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator
import redis.asyncio as aioredis
import redis
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database connections and initialization"""
    
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL", "mysql+pymysql://monitors:monitors_pass_2025@localhost:3306/monitors_db")
        self.redis_url = os.getenv("REDIS_URL", "redis://:your_redis_password@localhost:6379/1")
        self.influx_url = os.getenv("INFLUX_URL", "http://localhost:8086")
        self.influx_token = os.getenv("INFLUX_TOKEN", "fUN6ATPuQtqJWBkjxsOreHMOPwNTUqlUv5c84SVP4HZkxpm1pb8PAUHIfXVZbsbHy_pck6yPszey_qnaaH2SAw==")
        self.influx_org = os.getenv("INFLUX_ORG", "monitors")
        self.influx_bucket = os.getenv("INFLUX_BUCKET", "monitor_data")
        
        # SQLAlchemy setup
        self.engine = create_engine(
            self.database_url,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=False
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Redis setup
        self.redis_client = None
        self.async_redis_client = None
        
        # InfluxDB setup
        self.influx_client = None
        self.influx_write_api = None
        self.influx_query_api = None
    
    def initialize_database(self):
        """Initialize database tables"""
        from ..models import Base
        
        try:
            # Create all tables
            Base.metadata.create_all(bind=self.engine)
            
            # Migrate existing monitors to have secret_ids field
            self._migrate_monitors()
            
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise
    
    def _migrate_monitors(self):
        """Add secret_ids column to existing monitors if needed"""
        try:
            with self.get_db_session() as session:
                # Check if any monitors have NULL secret_ids and update them
                session.execute(
                    "UPDATE monitors SET secret_ids = '{}' WHERE secret_ids IS NULL"
                )
                session.commit()
        except Exception as e:
            # If the column doesn't exist yet, this will fail, which is fine
            logger.debug(f"Monitor migration note: {e}")
            pass
    
    def get_redis_client(self) -> redis.Redis:
        """Get synchronous Redis client"""
        if not self.redis_client:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
        return self.redis_client
    
    async def get_async_redis_client(self) -> aioredis.Redis:
        """Get asynchronous Redis client"""
        if not self.async_redis_client:
            self.async_redis_client = aioredis.from_url(self.redis_url, decode_responses=True)
        return self.async_redis_client
    
    def get_influx_client(self) -> InfluxDBClient:
        """Get InfluxDB client"""
        if not self.influx_client:
            self.influx_client = InfluxDBClient(
                url=self.influx_url,
                token=self.influx_token,
                org=self.influx_org
            )
            self.influx_write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)
            self.influx_query_api = self.influx_client.query_api()
        return self.influx_client
    
    @contextmanager
    def get_db_session(self) -> Generator[Session, None, None]:
        """Get database session with context management"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def test_connections(self) -> dict:
        """Test all database connections"""
        results = {}
        
        # Test MySQL
        try:
            with self.get_db_session() as session:
                session.execute(text("SELECT 1"))
            results["mysql"] = {"status": "connected", "url": self.database_url.split("@")[1]}
        except Exception as e:
            results["mysql"] = {"status": "error", "error": str(e)}
        
        # Test Redis
        try:
            redis_client = self.get_redis_client()
            redis_client.ping()
            results["redis"] = {"status": "connected", "url": self.redis_url.split("@")[1] if "@" in self.redis_url else self.redis_url}
        except Exception as e:
            results["redis"] = {"status": "error", "error": str(e)}
        
        # Test InfluxDB
        try:
            influx_client = self.get_influx_client()
            health = influx_client.health()
            results["influxdb"] = {"status": "connected", "health": health.status}
        except Exception as e:
            results["influxdb"] = {"status": "error", "error": str(e)}
        
        return results
    
    def close_connections(self):
        """Close all database connections"""
        if self.redis_client:
            self.redis_client.close()
        
        if self.influx_client:
            self.influx_client.close()
        
        if self.engine:
            self.engine.dispose()

# Global database manager instance
db_manager = DatabaseManager()
