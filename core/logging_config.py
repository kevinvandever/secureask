"""
Structured logging configuration for SecureAsk
"""

import os
import sys
import time
import structlog
import logging
from typing import Any, Dict
from fastapi import Request
import json

class SecurityFilter:
    """Filter to remove sensitive information from logs"""
    
    SENSITIVE_KEYS = {
        'password', 'token', 'secret', 'key', 'auth', 'authorization',
        'api_key', 'access_token', 'refresh_token', 'jwt', 'credential'
    }
    
    def filter_sensitive(self, data: Any) -> Any:
        """Recursively filter sensitive data"""
        if isinstance(data, dict):
            return {
                k: "[REDACTED]" if any(sensitive in k.lower() for sensitive in self.SENSITIVE_KEYS)
                else self.filter_sensitive(v)
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [self.filter_sensitive(item) for item in data]
        elif isinstance(data, str) and len(data) > 50:
            # Truncate very long strings (likely content)
            return data[:100] + "..." if len(data) > 100 else data
        return data

def add_request_context(logger, method_name, event_dict):
    """Add request context to log events"""
    # Try to get request from context
    request = getattr(structlog.contextvars.get_contextvars(), 'request', None)
    if request:
        event_dict.update({
            'request_id': getattr(request.state, 'request_id', None),
            'method': request.method,
            'path': str(request.url.path),
            'user_agent': request.headers.get('user-agent', 'unknown')
        })
    return event_dict

def add_performance_metrics(logger, method_name, event_dict):
    """Add performance metrics to log events"""
    if 'processing_time' not in event_dict:
        # Try to calculate from start_time in context
        start_time = getattr(structlog.contextvars.get_contextvars(), 'start_time', None)
        if start_time:
            event_dict['processing_time'] = round((time.time() - start_time) * 1000, 2)
    return event_dict

def setup_logging():
    """Configure structured logging for SecureAsk"""
    
    # Determine log level
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    # Determine if we're in production
    is_production = os.getenv('ENVIRONMENT', 'development') == 'production'
    
    # Configure structlog
    structlog.configure(
        processors=[
            # Add context processors
            structlog.contextvars.merge_contextvars,
            add_request_context,
            add_performance_metrics,
            
            # Standard processors
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            
            # JSON formatter for production, pretty print for development
            structlog.processors.JSONRenderer() if is_production 
            else structlog.dev.ConsoleRenderer(colors=True)
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level, logging.INFO),
        force=True
    )
    
    # Set specific logger levels
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    
    return structlog.get_logger()

class RequestLoggingMiddleware:
    """Middleware to add request logging and metrics"""
    
    def __init__(self, app):
        self.app = app
        self.security_filter = SecurityFilter()
        self.logger = structlog.get_logger(__name__)
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope)
        start_time = time.time()
        
        # Generate request ID
        request_id = f"req_{int(start_time * 1000000)}"
        
        # Set context variables
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            start_time=start_time,
            request=request
        )
        
        # Log request start
        self.logger.info(
            "Request started",
            method=request.method,
            path=str(request.url.path),
            query_params=dict(request.query_params),
            user_agent=request.headers.get('user-agent', 'unknown'),
            request_id=request_id
        )
        
        # Track response
        response_data = {}
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                response_data["status_code"] = message["status"]
                response_data["headers"] = dict(message.get("headers", []))
            await send(message)
        
        try:
            await self.app(scope, receive, send_wrapper)
            
            # Log successful request
            processing_time = round((time.time() - start_time) * 1000, 2)
            self.logger.info(
                "Request completed",
                status_code=response_data.get("status_code"),
                processing_time=processing_time,
                request_id=request_id
            )
            
        except Exception as e:
            # Log error
            processing_time = round((time.time() - start_time) * 1000, 2)
            self.logger.error(
                "Request failed",
                error=str(e),
                error_type=type(e).__name__,
                processing_time=processing_time,
                request_id=request_id,
                exc_info=True
            )
            raise
        
        finally:
            # Clear context
            structlog.contextvars.clear_contextvars()

def log_external_api_call(source: str, endpoint: str, response_time: float, success: bool):
    """Log external API calls with metrics"""
    logger = structlog.get_logger("external_api")
    
    if success:
        logger.info(
            "External API call successful",
            source=source,
            endpoint=endpoint,
            response_time=response_time,
            success=success
        )
    else:
        logger.warning(
            "External API call failed",
            source=source,
            endpoint=endpoint,
            response_time=response_time,
            success=success
        )

def log_cache_operation(operation: str, key: str, hit: bool, ttl: int = None):
    """Log cache operations"""
    logger = structlog.get_logger("cache")
    
    logger.info(
        f"Cache {operation}",
        operation=operation,
        key=key[:50] + "..." if len(key) > 50 else key,  # Truncate long keys
        cache_hit=hit,
        ttl=ttl
    )

def log_query_processing(
    query: str, 
    sources: list, 
    processing_time: float, 
    graph_hops: int,
    result_count: int
):
    """Log GraphRAG query processing"""
    logger = structlog.get_logger("graphrag")
    
    logger.info(
        "GraphRAG query processed",
        query_length=len(query),
        query_preview=query[:100] + "..." if len(query) > 100 else query,
        sources=sources,
        processing_time=processing_time,
        graph_hops=graph_hops,
        result_count=result_count
    )

def log_security_event(event_type: str, details: dict, severity: str = "warning"):
    """Log security-related events"""
    logger = structlog.get_logger("security")
    
    # Filter sensitive information
    security_filter = SecurityFilter()
    filtered_details = security_filter.filter_sensitive(details)
    
    log_func = getattr(logger, severity.lower(), logger.warning)
    log_func(
        f"Security event: {event_type}",
        event_type=event_type,
        severity=severity,
        **filtered_details
    )