"""
Authentication and session management for the Claude Monitor System
"""
import os
import time
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from cryptography.fernet import Fernet
import hashlib
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv

# Ensure .env is loaded
load_dotenv()

from ..models import User, Session
from ..database import db_manager

logger = logging.getLogger(__name__)

class AuthManager:
    """Handles authentication, OTP, and session management"""
    
    def __init__(self):
        self.jwt_secret = os.getenv("JWT_SECRET", "your-jwt-secret-here")
        self.master_key = os.getenv("MASTER_KEY", "your-master-encryption-key-here")
        self.sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
        
        # Debug logging
        logger.info(f"JWT_SECRET loaded: {'Yes' if self.jwt_secret != 'your-jwt-secret-here' else 'No'}")
        logger.info(f"SENDGRID_API_KEY loaded: {'Yes' if self.sendgrid_api_key else 'No'}")
        if self.sendgrid_api_key:
            logger.info(f"SENDGRID_API_KEY starts with: {self.sendgrid_api_key[:10]}...")
        
        # Generate encryption key from master key
        self.encryption_key = self._derive_encryption_key(self.master_key)
        self.fernet = Fernet(self.encryption_key)
    
    def _derive_encryption_key(self, master_key: str) -> bytes:
        """Derive a proper encryption key from master key"""
        key_bytes = hashlib.pbkdf2_hmac('sha256', master_key.encode(), b'salt', 100000, 32)
        return Fernet.generate_key()  # For now, generate a new key each time
    
    def generate_otp(self) -> str:
        """Generate a 6-digit OTP code"""
        return f"{secrets.randbelow(1000000):06d}"
    
    async def send_otp_email(self, email: str, otp: str) -> bool:
        """Send OTP via email using SendGrid"""
        try:
            if not self.sendgrid_api_key:
                logger.warning("SendGrid API key not configured, printing OTP to console")
                print(f"OTP for {email}: {otp}")
                return True
            
            sg = SendGridAPIClient(api_key=self.sendgrid_api_key)
            
            message = Mail(
                from_email='noreply@monitors.ai',
                to_emails=email,
                subject='Your Claude Monitor System Access Code',
                html_content=f'''
                <h2>Claude Monitor System</h2>
                <p>Your access code is: <strong style="font-size: 24px; color: #2563eb;">{otp}</strong></p>
                <p>This code will expire in 5 minutes.</p>
                <p>If you didn't request this code, please ignore this email.</p>
                '''
            )
            
            response = sg.send(message)
            logger.info(f"OTP sent to {email}, status: {response.status_code}")
            return response.status_code == 202
            
        except Exception as e:
            logger.error(f"Failed to send OTP email to {email}: {e}")
            # Fallback: print to console for development
            print(f"OTP for {email}: {otp}")
            return True
    
    async def store_otp(self, otp: str, email: str, expires_in: int = 300) -> None:
        """Store OTP in Redis with expiration"""
        redis_client = await db_manager.get_async_redis_client()
        await redis_client.setex(f"otp:{otp}", expires_in, email)
    
    async def verify_otp(self, otp: str) -> Optional[str]:
        """Verify OTP and return email if valid"""
        redis_client = await db_manager.get_async_redis_client()
        email = await redis_client.get(f"otp:{otp}")
        if email:
            await redis_client.delete(f"otp:{otp}")  # Use OTP only once
        return email
    
    def get_or_create_user(self, email: str) -> User:
        """Get existing user or create new one"""
        with db_manager.get_db_session() as session:
            user = session.query(User).filter(User.email == email).first()
            if not user:
                user = User(email=email)
                session.add(user)
                session.flush()  # Get the ID
                logger.info(f"Created new user: {user.id} ({email})")
            else:
                user.last_login = datetime.utcnow()
                logger.info(f"User login: {user.id} ({email})")
            
            session.commit()
            # Return a detached object with the data we need
            return {
                "id": user.id,
                "email": user.email,
                "tier": user.tier,
                "created_at": user.created_at
            }
    
    def create_session(self, user: User) -> Dict[str, Any]:
        """Create a new session for the user"""
        session_id = f"ses_{secrets.token_hex(8)}"
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        # Extract user data (user is now a dict)
        user_id = user["id"]
        user_email = user["email"]  
        user_tier = user["tier"]
        
        # Create JWT token
        payload = {
            "user_id": user_id,
            "session_id": session_id,
            "tier": user_tier,
            "permissions": self._get_user_permissions(user),
            "exp": expires_at.timestamp(),
            "iat": time.time()
        }
        
        token = jwt.encode(payload, self.jwt_secret, algorithm="HS256")
        
        # Store session in database
        with db_manager.get_db_session() as db_session:
            session_obj = Session(
                id=session_id,
                user_id=user_id,
                token=token,
                expires_at=expires_at
            )
            db_session.add(session_obj)
            db_session.commit()
        
        # Cache session data in Redis
        import json
        redis_client = db_manager.get_redis_client()
        redis_session_data = {
            "session_id": session_id,
            "token": token,
            "user": {
                "id": user_id,
                "email": user_email,
                "tier": user_tier
            },
            "permissions": payload["permissions"]
        }
        redis_client.setex(f"session:{session_id}", 86400, json.dumps(redis_session_data))
        
        return {
            "session_id": session_id,
            "token": token,
            "expires_at": expires_at.isoformat(),
            "user": {
                "id": user_id,
                "email": user_email,
                "tier": user_tier
            }
        }
    
    def _get_user_permissions(self, user) -> list:
        """Get user permissions based on tier"""
        base_permissions = ["create_monitor", "read_data", "manage_secrets"]
        
        user_tier = user["tier"] if isinstance(user, dict) else user.tier
        if user_tier == "pro":
            base_permissions.extend(["advanced_alerts", "custom_monitors"])
        elif user_tier == "enterprise":
            base_permissions.extend(["advanced_alerts", "custom_monitors", "team_management", "api_access"])
        
        return base_permissions
    
    def validate_session(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate session token and return user data"""
        try:
            # Decode JWT
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            
            # Check expiration
            if payload["exp"] < time.time():
                return None
            
            # Get from Redis cache
            redis_client = db_manager.get_redis_client()
            session_data = redis_client.get(f"session:{payload['session_id']}")
            
            if session_data:
                import json
                return json.loads(session_data)
            
            # Fallback to database
            with db_manager.get_db_session() as session:
                session_obj = session.query(Session).filter(
                    Session.id == payload["session_id"],
                    Session.is_active == True,
                    Session.expires_at > datetime.utcnow()
                ).first()
                
                if session_obj:
                    user = session.query(User).filter(User.id == session_obj.user_id).first()
                    return {
                        "session_id": session_obj.id,
                        "token": token,
                        "user": {
                            "id": user.id,
                            "email": user.email,
                            "tier": user.tier
                        },
                        "permissions": self._get_user_permissions({"id": user.id, "email": user.email, "tier": user.tier})
                    }
            
            return None
            
        except jwt.InvalidTokenError:
            return None
        except Exception as e:
            logger.error(f"Session validation error: {e}")
            return None
    
    def cache_session_locally(self, session_data: Dict[str, Any], device_path: str = "~/.claude-monitors") -> None:
        """Cache session locally for MCP client persistence"""
        import json
        import os
        
        device_dir = os.path.expanduser(device_path)
        os.makedirs(device_dir, exist_ok=True)
        
        # Encrypt session data
        encrypted_data = self.fernet.encrypt(json.dumps(session_data).encode())
        
        with open(os.path.join(device_dir, "session.enc"), "wb") as f:
            f.write(encrypted_data)
    
    def load_cached_session(self, device_path: str = "~/.claude-monitors") -> Optional[Dict[str, Any]]:
        """Load cached session from local storage"""
        import json
        import os
        
        session_file = os.path.join(os.path.expanduser(device_path), "session.enc")
        
        try:
            if os.path.exists(session_file):
                with open(session_file, "rb") as f:
                    encrypted_data = f.read()
                
                decrypted_data = self.fernet.decrypt(encrypted_data)
                session_data = json.loads(decrypted_data.decode())
                
                # Validate session is still active
                if self.validate_session(session_data.get("token")):
                    return session_data
                
        except Exception as e:
            logger.error(f"Failed to load cached session: {e}")
        
        return None

# Global auth manager instance
auth_manager = AuthManager()
