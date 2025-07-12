"""
Redis client for SecureAsk caching operations
"""

import json
import logging
import os
import asyncio
from typing import Any, Optional
import redis.asyncio as redis
from functools import wraps

logger = logging.getLogger(__name__)

class RedisClient:
    """Async Redis client for caching with retry logic"""
    
    def __init__(self):
        self.client = None
        self.url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.max_retries = 3
        self.retry_delay = 1.0
    
    def with_retry(self, func):
        """Decorator for Redis operations with retry logic"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not self.client:
                return None if 'get' in func.__name__ else False
            
            for attempt in range(self.max_retries):
                try:
                    return await func(*args, **kwargs)
                except (redis.ConnectionError, redis.TimeoutError) as e:
                    if attempt == self.max_retries - 1:
                        logger.error(f"Redis operation failed after {self.max_retries} attempts: {e}")
                        return None if 'get' in func.__name__ else False
                    
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                    logger.warning(f"Redis retry {attempt + 1}/{self.max_retries}: {e}")
                except Exception as e:
                    logger.error(f"Redis operation error: {e}")
                    return None if 'get' in func.__name__ else False
        return wrapper
    
    async def connect(self):
        """Connect to Redis with connection pooling"""
        try:
            self.client = redis.from_url(
                self.url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
                max_connections=20
            )
            
            # Test connection
            await self.client.ping()
            logger.info("✅ Redis connected with connection pooling")
            
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
        """Get value by key with retry logic"""
        @self.with_retry
        async def _get():
            return await self.client.get(key)
        
        return await _get()
    
    async def set(
        self,
        key: str,
        value: str,
        ex: Optional[int] = None
    ) -> bool:
        """Set key-value pair with optional expiration and retry logic"""
        @self.with_retry
        async def _set():
            await self.client.set(key, value, ex=ex)
            return True
        
        return await _set()
    
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
        """Cache external API response with compression"""
        if not self.client:
            return False
        
        cache_key = f"external_api:{source}:{abs(hash(query))}"
        try:
            serialized = json.dumps(data, default=str, separators=(',', ':'))
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
        
        cache_key = f"external_api:{source}:{abs(hash(query))}"
        try:
            cached = await self.get(cache_key)
            if cached:
                return json.loads(cached)
            return None
        except Exception as e:
            logger.error(f"Failed to get cached API response: {e}")
            return None
    
    async def cache_query_result(
        self,
        query_hash: str,
        result: Any,
        ttl: int = 1800  # 30 minutes
    ) -> bool:
        """Cache GraphRAG query result"""
        cache_key = f"query_result:{query_hash}"
        try:
            serialized = json.dumps(result, default=str, separators=(',', ':'))
            return await self.set(cache_key, serialized, ex=ttl)
        except Exception as e:
            logger.error(f"Failed to cache query result: {e}")
            return False
    
    async def get_cached_query_result(self, query_hash: str) -> Optional[Any]:
        """Get cached GraphRAG query result"""
        cache_key = f"query_result:{query_hash}"
        try:
            cached = await self.get(cache_key)
            if cached:
                return json.loads(cached)
            return None
        except Exception as e:
            logger.error(f"Failed to get cached query result: {e}")
            return None