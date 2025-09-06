"""Authentication models and schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class UserDB(Base):
    """Database model for users."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)  # Nullable for OAuth users
    full_name = Column(String(255), nullable=True)
    avatar_url = Column(Text, nullable=True)
    auth_provider = Column(String(50), default="local")  # local, google, github
    provider_id = Column(String(255), nullable=True)  # OAuth provider user ID
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Additional fields for enterprise features
    organization_id = Column(Integer, nullable=True)
    role = Column(String(50), default="user")  # user, admin, super_admin
    preferences = Column(Text, nullable=True)  # JSON string for user preferences


# Pydantic models for API
class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None


class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field(..., min_length=8)
    confirm_password: str


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    """Schema for Google OAuth."""
    id_token: str


class User(UserBase):
    """User response schema."""
    id: int
    is_active: bool
    is_verified: bool
    auth_provider: str
    role: str
    created_at: datetime
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    full_name: Optional[str] = None
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    preferences: Optional[dict] = None


class PasswordChange(BaseModel):
    """Schema for changing password."""
    current_password: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


class TokenData(BaseModel):
    """Token payload data."""
    user_id: int
    email: str
    role: str
    exp: datetime
