"""
Database models for the Claude Monitor System
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pydantic import BaseModel
import uuid

Base = declarative_base()

class User(Base):
    """User model for authentication and authorization"""
    __tablename__ = "users"
    
    id = Column(String(50), primary_key=True, default=lambda: f"usr_{uuid.uuid4().hex[:8]}")
    email = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    tier = Column(String(20), default="free")  # free, pro, enterprise
    is_active = Column(Boolean, default=True)
    
    # Relationships
    monitors = relationship("Monitor", back_populates="user")
    sessions = relationship("Session", back_populates="user")
    secrets = relationship("Secret", back_populates="user")
    alerts = relationship("Alert", back_populates="user")

class Session(Base):
    """User sessions for authentication"""
    __tablename__ = "sessions"
    
    id = Column(String(50), primary_key=True, default=lambda: f"ses_{uuid.uuid4().hex[:8]}")
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False)
    token = Column(String(512), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", back_populates="sessions")

class Monitor(Base):
    """Monitor instances"""
    __tablename__ = "monitors"
    
    id = Column(String(50), primary_key=True, default=lambda: f"mon_{uuid.uuid4().hex[:8]}")
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    monitor_type = Column(String(50), nullable=False)  # api_poller, websocket_stream, webhook_receiver
    config = Column(JSON, nullable=False)
    secret_ids = Column(JSON, default=lambda: {})  # Map of secret names to secret IDs
    status = Column(String(20), default="starting")  # starting, running, paused, error, stopped
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_data_at = Column(DateTime)
    deployment_id = Column(String(100))  # Kubernetes deployment ID
    
    # Relationships
    user = relationship("User", back_populates="monitors")
    alert_rules = relationship("AlertRule", back_populates="monitor")
    alerts = relationship("Alert", back_populates="monitor")

    
    @classmethod
    def create(cls, user_id: str, name: str, monitor_type: str, config: dict, secret_ids: dict = None):
        """Create a new monitor"""
        from .database import db_manager
        
        with db_manager.get_db_session() as session:
            monitor = cls(
                user_id=user_id,
                name=name,
                monitor_type=monitor_type,
                config=config,
                secret_ids=secret_ids or {}
            )
            session.add(monitor)
            session.flush()  # Get the ID
            session.commit()
            return monitor
    
    @classmethod
    def get_by_user(cls, user_id: str):
        """Get all monitors for a user"""
        from .database import db_manager
        
        with db_manager.get_db_session() as session:
            return session.query(cls).filter(cls.user_id == user_id).all()
    
    @classmethod
    def get_by_id_and_user(cls, monitor_id: str, user_id: str):
        """Get a specific monitor by ID and user"""
        from .database import db_manager
        
        with db_manager.get_db_session() as session:
            return session.query(cls).filter(
                cls.id == monitor_id,
                cls.user_id == user_id
            ).first()
    
    @classmethod
    def delete(cls, monitor_id: str):
        """Delete a monitor"""
        from .database import db_manager
        
        with db_manager.get_db_session() as session:
            monitor = session.query(cls).filter(cls.id == monitor_id).first()
            if monitor:
                session.delete(monitor)
                session.commit()
                return True
            return False

class Secret(Base):
    """Encrypted user secrets"""
    __tablename__ = "secrets"
    
    id = Column(String(50), primary_key=True, default=lambda: f"sec_{uuid.uuid4().hex[:8]}")
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    encrypted_value = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="secrets")

    
    @classmethod
    def create(cls, user_id: str, name: str, value: str, description: str = None):
        """Create a new secret"""
        from .database import db_manager
        from .auth import auth_manager
        
        # Encrypt the value
        encrypted_value = auth_manager.fernet.encrypt(value.encode()).decode()
        
        with db_manager.get_db_session() as session:
            secret = cls(
                user_id=user_id,
                name=name,
                description=description,
                encrypted_value=encrypted_value
            )
            session.add(secret)
            session.flush()  # Get the ID
            session.commit()
            return secret
    
    @classmethod
    def delete(cls, secret_id: str):
        """Delete a secret"""
        from .database import db_manager
        
        with db_manager.get_db_session() as session:
            secret = session.query(cls).filter(cls.id == secret_id).first()
            if secret:
                session.delete(secret)
                session.commit()
                return True
            return False

class AlertRule(Base):
    """Alert rules configuration"""
    __tablename__ = "alert_rules"
    
    id = Column(String(50), primary_key=True, default=lambda: f"rule_{uuid.uuid4().hex[:8]}")
    monitor_id = Column(String(50), ForeignKey("monitors.id"), nullable=False)
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    condition = Column(JSON, nullable=False)  # {"type": "threshold", "field": "value", "operator": ">", "value": 100}
    severity = Column(String(20), nullable=False)  # low, medium, high, critical
    cooldown_minutes = Column(Integer, default=5)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    monitor = relationship("Monitor", back_populates="alert_rules")
    alerts = relationship("Alert", back_populates="rule")

class Alert(Base):
    """Generated alerts"""
    __tablename__ = "alerts"
    
    id = Column(String(50), primary_key=True, default=lambda: f"alert_{uuid.uuid4().hex[:8]}")
    rule_id = Column(String(50), ForeignKey("alert_rules.id"), nullable=False)
    monitor_id = Column(String(50), ForeignKey("monitors.id"), nullable=False)
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False)
    severity = Column(String(20), nullable=False)
    title = Column(String(255), nullable=False)
    data = Column(JSON)  # Trigger data
    status = Column(String(20), default="pending")  # pending, delivered, acknowledged, expired
    delivered_channels = Column(JSON)  # ["email", "slack"]
    delivered_at = Column(DateTime)
    acknowledged_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    notification_preferences = Column(JSON)  # Snapshot of preferences at alert time
    
    # Relationships
    rule = relationship("AlertRule", back_populates="alerts")
    monitor = relationship("Monitor", back_populates="alerts")
    user = relationship("User", back_populates="alerts")

    
    @classmethod
    def get_by_monitor(cls, monitor_id: str, limit: int = 10):
        """Get alerts for a monitor"""
        from .database import db_manager
        
        with db_manager.get_db_session() as session:
            return session.query(cls).filter(
                cls.monitor_id == monitor_id
            ).order_by(cls.created_at.desc()).limit(limit).all()

# Pydantic models for API
class UserCreate(BaseModel):
    email: str

class UserResponse(BaseModel):
    id: str
    email: str
    tier: str
    created_at: datetime
    
class MonitorCreate(BaseModel):
    name: str
    description: Optional[str] = None
    monitor_type: str
    config: Dict[str, Any]

class MonitorResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    monitor_type: str
    status: str
    created_at: datetime
    last_data_at: Optional[datetime]
    
class SecretCreate(BaseModel):
    name: str
    value: str
    description: Optional[str] = None

class SecretResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    created_at: datetime
    last_used: Optional[datetime]

class AlertRuleCreate(BaseModel):
    title: str
    condition: Dict[str, Any]
    severity: str
    cooldown_minutes: int = 5

class AlertResponse(BaseModel):
    id: str
    title: str
    severity: str
    status: str
    created_at: datetime
    data: Optional[Dict[str, Any]]
