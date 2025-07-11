"""
Redis client for SecureAsk caching operations
"""

import json
import logging
import os
from typing import Any, Optional
import redis.asyncio as redis

logger = logging.getLogger(__name__)

class RedisClient:
    """Async Redis client for caching"""
    
    def __init__(self):
        self.client = None
        self.url = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    async def connect(self):
        """Connect to Redis"""
        try:
            self.client = redis.from_url(
                self.url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Test connection
            await self.client.ping()
            logger.info("✅ Redis connected")
            
        except Exception as e:
            logger.warning(f"⚠️ Redis connection failed: {e}")
            logger.info("Continuing without cache...")
            self.client = None
    
    async def close(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()
            logger.info("Redis connection closed")
    
    async def get(self, key: str) -> Optional[str]:
        """Get value by key"""
        if not self.client:
            return None
        
        try:
            return await self.client.get(key)
        except Exception as e:
            logger.error(f"Redis GET failed: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: str,
        ex: Optional[int] = None
    ) -> bool:
        """Set key-value pair with optional expiration"""
        if not self.client:
            return False
        
        try:
            await self.client.set(key, value, ex=ex)
            return True
        except Exception as e:
            logger.error(f"Redis SET failed: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key"""
        if not self.client:
            return False
        
        try:
            await self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis DELETE failed: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self.client:
            return False
        
        try:
            return bool(await self.client.exists(key))
        except Exception as e:
            logger.error(f"Redis EXISTS failed: {e}")
            return False
    
    async def cache_external_api_response(
        self,
        source: str,
        query: str,
        data: Any,
        ttl: int = 900  # 15 minutes
    ) -> bool:
        """Cache external API response"""
        if not self.client:
            return False
        
        cache_key = f"external_api:{source}:{hash(query)}"
        try:
            serialized = json.dumps(data, default=str)
            return await self.set(cache_key, serialized, ex=ttl)
        except Exception as e:
            logger.error(f"Failed to cache API response: {e}")
            return False
    
    async def get_cached_external_api_response(
        self,
        source: str,
        query: str
    ) -> Optional[Any]:
        """Get cached external API response"""
        if not self.client:
            return None
        
        cache_key = f"external_api:{source}:{hash(query)}"
        try:
            cached = await self.get(cache_key)
            if cached:
                return json.loads(cached)
            return None
        except Exception as e:
            logger.error(f"Failed to get cached API response: {e}")
            return None