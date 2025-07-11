"""
Authentication middleware for SecureAsk API
"""

import os
import jwt
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

class AuthMiddleware:
    """JWT authentication middleware for hackathon demo"""
    
    JWT_SECRET = os.getenv("JWT_SECRET", "hackathon-secret-key-change-in-production")
    ALGORITHM = "HS256"
    
    @staticmethod
    def create_token(user_id: str, role: str = "analyst") -> str:
        """Create a JWT token for demo purposes"""
        payload = {
            "sub": user_id,
            "role": role,
            "exp": datetime.utcnow() + timedelta(hours=24),  # 24 hour expiry
            "iat": datetime.utcnow(),
            "iss": "secureask-api"
        }
        
        return jwt.encode(
            payload,
            AuthMiddleware.JWT_SECRET,
            algorithm=AuthMiddleware.ALGORITHM
        )
    
    @staticmethod
    async def verify_token(
        credentials: HTTPAuthorizationCredentials = Security(security)
    ) -> dict:
        """Verify and decode JWT token"""
        token = credentials.credentials
        
        try:
            payload = jwt.decode(
                token,
                AuthMiddleware.JWT_SECRET,
                algorithms=[AuthMiddleware.ALGORITHM]
            )
            
            # Extract user info
            user_id = payload.get("sub")
            role = payload.get("role", "analyst")
            
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: missing user ID"
                )
            
            return {
                "user_id": user_id,
                "role": role,
                "exp": payload.get("exp"),
                "iat": payload.get("iat")
            }
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )
    
    @staticmethod
    def require_role(required_role: str):
        """Decorator to require specific role (not used in hackathon demo)"""
        def decorator(func):
            async def wrapper(*args, user: dict = Security(verify_token), **kwargs):
                if user.get("role") != required_role:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Role '{required_role}' required"
                    )
                return await func(*args, user=user, **kwargs)
            return wrapper
        return decorator