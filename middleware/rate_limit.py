"""
Rate limiting middleware for SecureAsk API
"""

import time
import hashlib
from typing import Callable, Optional
from fastapi import Request, HTTPException, status
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import redis.asyncio as redis
import logging

logger = logging.getLogger(__name__)

class RateLimitMiddleware:
    """Advanced rate limiting with Redis backend"""
    
    def __init__(self, redis_client, default_rate_limit: str = "100/minute"):
        self.redis_client = redis_client
        self.default_rate_limit = default_rate_limit
        
        # Initialize slowapi limiter
        self.limiter = Limiter(
            key_func=self._get_rate_limit_key,
            storage_uri=redis_client.url if redis_client and redis_client.client else "memory://",
            default_limits=[default_rate_limit]
        )
    
    def _get_rate_limit_key(self, request: Request) -> str:
        """Generate rate limit key based on IP and user"""
        # Try to get user ID from request
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            return f"user:{user_id}"
        
        # Fall back to IP address
        return f"ip:{get_remote_address(request)}"
    
    async def check_rate_limit(
        self,
        request: Request,
        endpoint: str,
        rate_limit: Optional[str] = None
    ) -> bool:
        """Check rate limit for specific endpoint"""
        if not self.redis_client or not self.redis_client.client:
            logger.warning("Rate limiting disabled - no Redis connection")
            return True
        
        key = self._get_rate_limit_key(request)
        endpoint_key = f"rate_limit:{key}:{endpoint}"
        
        try:
            # Use sliding window rate limiting
            current_time = int(time.time())
            window_size = self._parse_rate_limit(rate_limit or self.default_rate_limit)
            
            # Remove old entries
            await self.redis_client.client.zremrangebyscore(
                endpoint_key, 0, current_time - window_size['window']
            )
            
            # Count current requests
            current_count = await self.redis_client.client.zcard(endpoint_key)
            
            if current_count >= window_size['limit']:
                # Rate limit exceeded
                logger.warning(f"Rate limit exceeded for {key} on {endpoint}: {current_count}/{window_size['limit']}")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "Rate limit exceeded",
                        "limit": window_size['limit'],
                        "window": f"{window_size['window']}s",
                        "retry_after": window_size['window']
                    }
                )
            
            # Add current request
            await self.redis_client.client.zadd(
                endpoint_key, {str(current_time): current_time}
            )
            await self.redis_client.client.expire(endpoint_key, window_size['window'])
            
            # Add rate limit headers to response
            request.state.rate_limit_remaining = window_size['limit'] - current_count - 1
            request.state.rate_limit_limit = window_size['limit']
            request.state.rate_limit_reset = current_time + window_size['window']
            
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # Fail open - allow request if rate limiting fails
            return True
    
    def _parse_rate_limit(self, rate_limit: str) -> dict:
        """Parse rate limit string like '100/minute' or '10/second'"""
        try:
            limit, period = rate_limit.split('/')
            limit = int(limit)
            
            if period.startswith('second'):
                window = 1
            elif period.startswith('minute'):
                window = 60
            elif period.startswith('hour'):
                window = 3600
            elif period.startswith('day'):
                window = 86400
            else:
                window = 60  # default to minute
            
            return {'limit': limit, 'window': window}
        except:
            # Default fallback
            return {'limit': 100, 'window': 60}

# Rate limiting decorators for different endpoint types
def rate_limit_query(rate: str = "20/minute"):
    """Rate limit for query endpoints"""
    def decorator(func):
        func._rate_limit = rate
        func._rate_limit_type = "query"
        return func
    return decorator

def rate_limit_auth(rate: str = "10/minute"):
    """Rate limit for authentication endpoints"""
    def decorator(func):
        func._rate_limit = rate
        func._rate_limit_type = "auth"
        return func
    return decorator

def rate_limit_ingest(rate: str = "5/minute"):
    """Rate limit for data ingestion endpoints"""
    def decorator(func):
        func._rate_limit = rate
        func._rate_limit_type = "ingest"
        return func
    return decorator

# Rate limit configuration for different user tiers
RATE_LIMITS = {
    "free": {
        "query": "20/minute",
        "auth": "10/minute", 
        "ingest": "5/minute"
    },
    "pro": {
        "query": "100/minute",
        "auth": "50/minute",
        "ingest": "25/minute"
    },
    "enterprise": {
        "query": "1000/minute",
        "auth": "200/minute",
        "ingest": "100/minute"
    }
}

def get_rate_limit_for_user(user_tier: str, endpoint_type: str) -> str:
    """Get rate limit based on user tier and endpoint type"""
    return RATE_LIMITS.get(user_tier, RATE_LIMITS["free"]).get(endpoint_type, "10/minute")