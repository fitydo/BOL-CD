"""
API Key Authentication with Scoped Access Control
"""
import os
from fastapi import Header, HTTPException
from typing import Optional, Set
import hashlib
import logging

# Parse API keys from environment
# Format: 'condensed:KEY1,full:KEY2,delta:KEY3,admin:KEY_ADMIN'
RAW_KEYS = os.getenv("BOLCD_API_KEYS", "condensed:demo-key-condensed,full:demo-key-full,admin:demo-key-admin")
KEYS = {}

# Hashing configuration (avoid weak hashing per CodeQL)
# Supported: plain, pbkdf2
HASH_METHOD = os.getenv("BOLCD_HASH_METHOD", os.getenv("BOLCD_HASH_KEYS", "plain")).lower()
PBKDF2_SALT = os.getenv("BOLCD_API_KEY_SALT", "bolcd-api-key-pepper").encode()
PBKDF2_ITERATIONS = int(os.getenv("BOLCD_API_KEY_ITERS", "200000"))
logger = logging.getLogger(__name__)

for pair in [p.strip() for p in RAW_KEYS.split(",") if p.strip()]:
    try:
        scope, key = pair.split(":", 1)
        # Store derived keys securely when hashing is enabled
        if HASH_METHOD in ("true", "pbkdf2"):
            derived = hashlib.pbkdf2_hmac(
                "sha256", key.encode(), PBKDF2_SALT, PBKDF2_ITERATIONS
            ).hex()
            KEYS[derived] = scope
        else:
            KEYS[key] = scope
    except ValueError:
        print(f"⚠️ Invalid API key format: {pair}")

def verify_api_key(key: str) -> Optional[str]:
    """Verify API key and return scope"""
    if HASH_METHOD in ("true", "pbkdf2"):
        derived = hashlib.pbkdf2_hmac(
            "sha256", key.encode(), PBKDF2_SALT, PBKDF2_ITERATIONS
        ).hex()
        return KEYS.get(derived)
    return KEYS.get(key)

def require_scope(allowed_scopes: Set[str]):
    """Dependency to require specific scopes"""
    async def dependency(x_api_key: Optional[str] = Header(None)):
        if not x_api_key:
            raise HTTPException(
                status_code=401, 
                detail="API key required",
                headers={"WWW-Authenticate": "ApiKey"}
            )
        
        scope = verify_api_key(x_api_key)
        if not scope:
            raise HTTPException(
                status_code=401,
                detail="Invalid API key"
            )
        
        # Admin scope has access to everything
        if scope != "admin" and scope not in allowed_scopes:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required: {allowed_scopes}, Got: {scope}"
            )
        
        return {"scope": scope, "key_id": x_api_key[:8] + "..."}
    
    return dependency

def get_current_scope(x_api_key: Optional[str] = Header(None)) -> dict:
    """Get current API key scope without requiring specific permissions"""
    if not x_api_key:
        return {"scope": "anonymous", "key_id": None}
    
    scope = verify_api_key(x_api_key)
    if not scope:
        return {"scope": "invalid", "key_id": x_api_key[:8] + "..."}
    
    return {"scope": scope, "key_id": x_api_key[:8] + "..."}
