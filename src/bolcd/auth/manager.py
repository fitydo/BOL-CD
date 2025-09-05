"""Authentication manager for handling user authentication and authorization."""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import bcrypt
import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from google.auth.transport import requests
from google.oauth2 import id_token

from .models import UserDB, User, UserCreate, Token, TokenData, Base


class AuthManager:
    """Manages authentication operations."""
    
    def __init__(self, database_url: Optional[str] = None):
        """Initialize authentication manager."""
        self.database_url = database_url or os.getenv(
            "BOLCD_DATABASE_URL", 
            "sqlite:///./bolcd_auth.db"
        )
        self.secret_key = os.getenv("BOLCD_JWT_SECRET", secrets.token_urlsafe(32))
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        self.refresh_token_expire_days = 7
        self.google_client_id = os.getenv("BOLCD_GOOGLE_CLIENT_ID")
        
        # Initialize database
        self.engine = create_engine(self.database_url)
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Create demo accounts on initialization
        self._create_demo_accounts()
    
    def get_db(self) -> Session:
        """Get database session."""
        db = self.SessionLocal()
        try:
            return db
        finally:
            db.close()
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return bcrypt.checkpw(
            plain_password.encode('utf-8'), 
            hashed_password.encode('utf-8')
        )
    
    def create_access_token(self, data: Dict[str, Any]) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire, "type": "access"})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create a JWT refresh token."""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        to_encode.update({"exp": expire, "type": "refresh"})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def decode_token(self, token: str) -> Optional[TokenData]:
        """Decode and validate a JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return TokenData(
                user_id=payload.get("user_id"),
                email=payload.get("email"),
                role=payload.get("role"),
                exp=datetime.fromtimestamp(payload.get("exp"))
            )
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def register_user(self, user_data: UserCreate, db: Session) -> Optional[User]:
        """Register a new user."""
        # Validate passwords match
        if user_data.password != user_data.confirm_password:
            raise ValueError("Passwords do not match")
        
        # Check if user exists
        existing_user = db.query(UserDB).filter(
            (UserDB.email == user_data.email) | 
            (UserDB.username == user_data.username)
        ).first()
        
        if existing_user:
            raise ValueError("User with this email or username already exists")
        
        # Create new user
        db_user = UserDB(
            email=user_data.email,
            username=user_data.username,
            full_name=user_data.full_name,
            hashed_password=self.hash_password(user_data.password),
            auth_provider="local",
            is_active=True,
            is_verified=False  # Require email verification
        )
        
        try:
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            return User.from_orm(db_user)
        except IntegrityError:
            db.rollback()
            raise ValueError("Failed to create user")
    
    def authenticate_user(self, email: str, password: str, db: Session) -> Optional[User]:
        """Authenticate a user with email and password."""
        user = db.query(UserDB).filter(UserDB.email == email).first()
        
        if not user or not user.hashed_password:
            return None
        
        if not self.verify_password(password, user.hashed_password):
            return None
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        return User.from_orm(user)
    
    def authenticate_google(self, id_token_str: str, db: Session) -> Optional[User]:
        """Authenticate a user with Google OAuth."""
        if not self.google_client_id:
            raise ValueError("Google OAuth not configured")
        
        try:
            # Verify the Google ID token
            idinfo = id_token.verify_oauth2_token(
                id_token_str, 
                requests.Request(), 
                self.google_client_id
            )
            
            # Extract user info
            email = idinfo.get("email")
            name = idinfo.get("name")
            picture = idinfo.get("picture")
            google_id = idinfo.get("sub")
            
            if not email:
                return None
            
            # Check if user exists
            user = db.query(UserDB).filter(UserDB.email == email).first()
            
            if user:
                # Update existing user
                user.last_login = datetime.utcnow()
                if not user.avatar_url and picture:
                    user.avatar_url = picture
                if not user.full_name and name:
                    user.full_name = name
            else:
                # Create new user
                username = email.split("@")[0]
                # Ensure unique username
                base_username = username
                counter = 1
                while db.query(UserDB).filter(UserDB.username == username).first():
                    username = f"{base_username}{counter}"
                    counter += 1
                
                user = UserDB(
                    email=email,
                    username=username,
                    full_name=name,
                    avatar_url=picture,
                    auth_provider="google",
                    provider_id=google_id,
                    is_active=True,
                    is_verified=True  # Google accounts are pre-verified
                )
                db.add(user)
            
            db.commit()
            db.refresh(user)
            return User.from_orm(user)
            
        except ValueError as e:
            # Invalid token
            return None
    
    def create_tokens(self, user: User) -> Token:
        """Create access and refresh tokens for a user."""
        token_data = {
            "user_id": user.id,
            "email": user.email,
            "role": user.role
        }
        
        access_token = self.create_access_token(token_data)
        refresh_token = self.create_refresh_token(token_data)
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.access_token_expire_minutes * 60
        )
    
    def get_current_user(self, token: str, db: Session) -> Optional[User]:
        """Get current user from token."""
        token_data = self.decode_token(token)
        if not token_data:
            return None
        
        user = db.query(UserDB).filter(UserDB.id == token_data.user_id).first()
        if not user:
            return None
        
        return User.from_orm(user)
    
    def update_user(self, user_id: int, updates: Dict[str, Any], db: Session) -> Optional[User]:
        """Update user profile."""
        user = db.query(UserDB).filter(UserDB.id == user_id).first()
        if not user:
            return None
        
        for key, value in updates.items():
            if hasattr(user, key) and value is not None:
                setattr(user, key, value)
        
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        return User.from_orm(user)
    
    def change_password(self, user_id: int, current_password: str, new_password: str, db: Session) -> bool:
        """Change user password."""
        user = db.query(UserDB).filter(UserDB.id == user_id).first()
        if not user or not user.hashed_password:
            return False
        
        if not self.verify_password(current_password, user.hashed_password):
            return False
        
        user.hashed_password = self.hash_password(new_password)
        user.updated_at = datetime.utcnow()
        db.commit()
        return True
    
    def delete_user(self, user_id: int, db: Session) -> bool:
        """Delete a user account."""
        user = db.query(UserDB).filter(UserDB.id == user_id).first()
        if not user:
            return False
        
        db.delete(user)
        db.commit()
        return True
    
    def create_or_update_sso_user(self, *, email: str, full_name: Optional[str], provider: str, provider_id: Optional[str], db: Session) -> Optional[User]:
        """Create or update SSO user (SAML/OIDC/SCIM)."""
        existing = db.query(UserDB).filter(UserDB.email == email).first()
        if existing:
            existing.full_name = full_name or existing.full_name
            existing.auth_provider = provider
            existing.provider_id = provider_id
            existing.last_login = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return User.from_orm(existing)
        # Create new SSO user
        username = email.split("@")[0]
        base_username = username
        counter = 1
        while db.query(UserDB).filter(UserDB.username == username).first():
            username = f"{base_username}{counter}"
            counter += 1
        db_user = UserDB(
            email=email,
            username=username,
            full_name=full_name or email,
            hashed_password="",  # No password for SSO users
            auth_provider=provider,
            provider_id=provider_id,
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow(),
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return User.from_orm(db_user)
    
    def _create_demo_accounts(self):
        """Create demo accounts if they don't exist."""
        db = self.SessionLocal()
        try:
            # Demo admin account
            admin_email = "admin@demo.com"
            if not db.query(UserDB).filter(UserDB.email == admin_email).first():
                admin_user = UserDB(
                    email=admin_email,
                    username="admin",
                    full_name="Demo Administrator",
                    hashed_password=self.hash_password("admin123"),
                    auth_provider="local",
                    is_active=True,
                    is_verified=True,
                    role="admin"
                )
                db.add(admin_user)
            
            # Demo regular user account
            user_email = "user@demo.com"
            if not db.query(UserDB).filter(UserDB.email == user_email).first():
                demo_user = UserDB(
                    email=user_email,
                    username="demouser",
                    full_name="Demo User",
                    hashed_password=self.hash_password("user123"),
                    auth_provider="local",
                    is_active=True,
                    is_verified=True,
                    role="user"
                )
                db.add(demo_user)
            
            # Demo analyst account
            analyst_email = "analyst@demo.com"
            if not db.query(UserDB).filter(UserDB.email == analyst_email).first():
                analyst_user = UserDB(
                    email=analyst_email,
                    username="analyst",
                    full_name="Security Analyst",
                    hashed_password=self.hash_password("analyst123"),
                    auth_provider="local",
                    is_active=True,
                    is_verified=True,
                    role="analyst",
                    avatar_url="https://ui-avatars.com/api/?name=Security+Analyst&background=6366f1&color=fff"
                )
                db.add(analyst_user)
            
            db.commit()
            print("Demo accounts created successfully:")
            print("  Admin: admin@demo.com / admin123")
            print("  User: user@demo.com / user123")
            print("  Analyst: analyst@demo.com / analyst123")
            
        except Exception as e:
            print(f"Warning: Could not create demo accounts: {e}")
            db.rollback()
        finally:
            db.close()
