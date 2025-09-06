"""
Redis cache implementation for high availability.

This module provides a Redis-based caching layer for BOL-CD to support:
- Distributed rate limiting across multiple nodes
- Session state management
- Temporary result caching
- Leader election for scheduled tasks
"""

import json
import os
import time
from typing import Any, Optional, Dict, List
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

try:
    import redis
    from redis.sentinel import Sentinel
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not installed. Running in standalone mode.")


class CacheBackend:
    """Abstract cache backend interface."""
    
    def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        raise NotImplementedError
    
    def delete(self, key: str) -> bool:
        raise NotImplementedError
    
    def exists(self, key: str) -> bool:
        raise NotImplementedError
    
    def incr(self, key: str, amount: int = 1) -> int:
        raise NotImplementedError
    
    def expire(self, key: str, ttl: int) -> bool:
        raise NotImplementedError
    
    def get_lock(self, key: str, timeout: int = 10) -> Any:
        raise NotImplementedError


class RedisCache(CacheBackend):
    """Redis-based cache implementation with Sentinel support."""
    
    def __init__(self, 
                 host: Optional[str] = None,
                 port: int = 6379,
                 db: int = 0,
                 password: Optional[str] = None,
                 sentinels: Optional[List[tuple]] = None,
                 service_name: str = "mymaster",
                 decode_responses: bool = True,
                 **kwargs):
        """
        Initialize Redis cache.
        
        Args:
            host: Redis host (ignored if sentinels provided)
            port: Redis port
            db: Redis database number
            password: Redis password
            sentinels: List of (host, port) tuples for Sentinel nodes
            service_name: Sentinel service name
            decode_responses: Whether to decode responses to strings
            **kwargs: Additional redis client arguments
        """
        if not REDIS_AVAILABLE:
            raise ImportError("redis-py is required for Redis cache. Install with: pip install redis")
        
        self.config = {
            'db': db,
            'password': password,
            'decode_responses': decode_responses,
            **kwargs
        }
        
        if sentinels:
            # High availability mode with Sentinel
            self.sentinel = Sentinel(sentinels, socket_connect_timeout=0.5)
            self.client = self.sentinel.master_for(service_name, **self.config)
            self.slave_client = self.sentinel.slave_for(service_name, **self.config)
            logger.info(f"Connected to Redis via Sentinel (service: {service_name})")
        else:
            # Standalone mode
            host = host or os.getenv('BOLCD_REDIS_HOST', 'localhost')
            self.client = redis.Redis(host=host, port=port, **self.config)
            self.slave_client = self.client  # Same client for reads in standalone
            logger.info(f"Connected to standalone Redis at {host}:{port}")
        
        # Test connection
        try:
            self.client.ping()
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            value = self.slave_client.get(key)
            if value and value.startswith('{'):
                # Try to deserialize JSON
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    pass
            return value
        except Exception as e:
            logger.error(f"Redis GET failed for key {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL."""
        try:
            # Serialize complex objects as JSON
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            
            if ttl:
                return bool(self.client.setex(key, ttl, value))
            else:
                return bool(self.client.set(key, value))
        except Exception as e:
            logger.error(f"Redis SET failed for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            logger.error(f"Redis DELETE failed for key {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            return bool(self.slave_client.exists(key))
        except Exception as e:
            logger.error(f"Redis EXISTS failed for key {key}: {e}")
            return False
    
    def incr(self, key: str, amount: int = 1) -> int:
        """Atomic increment operation."""
        try:
            return self.client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Redis INCR failed for key {key}: {e}")
            return 0
    
    def expire(self, key: str, ttl: int) -> bool:
        """Set TTL on existing key."""
        try:
            return bool(self.client.expire(key, ttl))
        except Exception as e:
            logger.error(f"Redis EXPIRE failed for key {key}: {e}")
            return False
    
    @contextmanager
    def get_lock(self, key: str, timeout: int = 10):
        """
        Distributed lock using Redis.
        
        Args:
            key: Lock key
            timeout: Lock timeout in seconds
        """
        lock_key = f"lock:{key}"
        lock_value = f"{os.getpid()}:{time.time()}"
        
        try:
            # Try to acquire lock
            acquired = self.client.set(lock_key, lock_value, nx=True, ex=timeout)
            if not acquired:
                raise RuntimeError(f"Could not acquire lock for {key}")
            
            logger.debug(f"Acquired lock: {lock_key}")
            yield
            
        finally:
            # Release lock only if we own it
            current = self.client.get(lock_key)
            if current == lock_value:
                self.client.delete(lock_key)
                logger.debug(f"Released lock: {lock_key}")


class MemoryCache(CacheBackend):
    """In-memory cache fallback for development/testing."""
    
    def __init__(self):
        self.store: Dict[str, Any] = {}
        self.ttls: Dict[str, float] = {}
        logger.info("Using in-memory cache (not suitable for production)")
    
    def _cleanup_expired(self):
        """Remove expired keys."""
        now = time.time()
        expired = [k for k, exp in self.ttls.items() if exp < now]
        for k in expired:
            del self.store[k]
            del self.ttls[k]
    
    def get(self, key: str) -> Optional[Any]:
        self._cleanup_expired()
        return self.store.get(key)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        self.store[key] = value
        if ttl:
            self.ttls[key] = time.time() + ttl
        elif key in self.ttls:
            del self.ttls[key]
        return True
    
    def delete(self, key: str) -> bool:
        if key in self.store:
            del self.store[key]
            if key in self.ttls:
                del self.ttls[key]
            return True
        return False
    
    def exists(self, key: str) -> bool:
        self._cleanup_expired()
        return key in self.store
    
    def incr(self, key: str, amount: int = 1) -> int:
        current = self.get(key) or 0
        if isinstance(current, str):
            current = int(current)
        new_val = current + amount
        self.set(key, new_val)
        return new_val
    
    def expire(self, key: str, ttl: int) -> bool:
        if key in self.store:
            self.ttls[key] = time.time() + ttl
            return True
        return False
    
    @contextmanager
    def get_lock(self, key: str, timeout: int = 10):
        """Simple lock for single-process mode."""
        lock_key = f"lock:{key}"
        if self.exists(lock_key):
            raise RuntimeError(f"Could not acquire lock for {key}")
        
        self.set(lock_key, True, ttl=timeout)
        try:
            yield
        finally:
            self.delete(lock_key)


def get_cache() -> CacheBackend:
    """
    Factory function to get appropriate cache backend.
    
    Returns:
        CacheBackend instance (Redis if available and configured, Memory otherwise)
    """
    # Check for Redis configuration
    redis_enabled = os.getenv('BOLCD_REDIS_ENABLED', '').lower() in ('1', 'true')
    
    if not redis_enabled or not REDIS_AVAILABLE:
        return MemoryCache()
    
    # Parse Sentinel configuration if provided
    sentinels_str = os.getenv('BOLCD_REDIS_SENTINELS', '')
    sentinels = []
    if sentinels_str:
        for sentinel in sentinels_str.split(','):
            host, port = sentinel.strip().split(':')
            sentinels.append((host, int(port)))
    
    return RedisCache(
        host=os.getenv('BOLCD_REDIS_HOST'),
        port=int(os.getenv('BOLCD_REDIS_PORT', '6379')),
        db=int(os.getenv('BOLCD_REDIS_DB', '0')),
        password=os.getenv('BOLCD_REDIS_PASSWORD'),
        sentinels=sentinels if sentinels else None,
        service_name=os.getenv('BOLCD_REDIS_SERVICE', 'mymaster')
    )


# Global cache instance
_cache: Optional[CacheBackend] = None


def get_global_cache() -> CacheBackend:
    """Get or create global cache instance."""
    global _cache
    if _cache is None:
        _cache = get_cache()
    return _cache
