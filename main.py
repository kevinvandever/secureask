#!/usr/bin/env python3
"""
SecureAsk GraphRAG API
Main FastAPI application wrapping Microsoft GraphRAG for financial intelligence
"""

import asyncio
import logging
import os
import time
import hashlib
from contextlib import asynccontextmanager
from typing import Dict, Any, List

from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn
import structlog

# Import our modules (we'll create these next)
from core.graphrag_engine import GraphRAGEngine
from core.models import QueryRequest, QueryResponse, IngestRequest
from core.logging_config import setup_logging, RequestLoggingMiddleware, log_query_processing, log_cache_operation
from db.neo4j_client import Neo4jClient
from db.redis_client import RedisClient
from middleware.auth import AuthMiddleware
from middleware.rate_limit import RateLimitMiddleware, rate_limit_query, rate_limit_auth
from connectors.sec_connector import SECConnector
from connectors.reddit_connector import RedditConnector

# Configure structured logging
logger = setup_logging()

# Global clients (initialized in lifespan)
neo4j_client: Neo4jClient = None
redis_client: RedisClient = None
graphrag_engine: GraphRAGEngine = None
rate_limiter: RateLimitMiddleware = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources"""
    global neo4j_client, redis_client, graphrag_engine, rate_limiter
    
    try:
        logger.info("🚀 Starting SecureAsk GraphRAG API...")
        
        # Initialize clients
        neo4j_client = Neo4jClient()
        await neo4j_client.connect()
        
        redis_client = RedisClient()
        await redis_client.connect()
        
        # Initialize rate limiter
        rate_limiter = RateLimitMiddleware(redis_client)
        
        # Initialize GraphRAG engine
        graphrag_engine = GraphRAGEngine(neo4j_client, redis_client)
        await graphrag_engine.initialize()
        
        logger.info("✅ SecureAsk API initialized successfully")
        yield
        
    except Exception as e:
        logger.error("❌ Failed to initialize SecureAsk API", error=str(e), exc_info=True)
        raise
    finally:
        # Cleanup
        if neo4j_client:
            await neo4j_client.close()
        if redis_client:
            await redis_client.close()
        logger.info("🔌 SecureAsk API shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="SecureAsk GraphRAG API",
    description="Graph-based RAG API for multi-hop reasoning across financial documents",
    version="1.0.0",
    lifespan=lifespan
)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Welcome page
@app.get("/")
async def root():
    """Welcome page with API documentation"""
    return {
        "message": "🔍 Welcome to SecureAsk GraphRAG API",
        "description": "Multi-hop reasoning across SEC filings, Reddit, and TikTok",
        "endpoints": {
            "health": "/health",
            "query": "POST /api/v1/query",
            "auth": "POST /api/v1/auth/demo (optional)"
        },
        "example_query": {
            "url": "POST /api/v1/query",
            "body": {
                "question": "What are Apple's ESG risks?",
                "sources": ["sec", "reddit", "tiktok"]
            }
        },
        "hackathon": "MindStudio.ai"
    }

# Health check endpoint with detailed status
@app.get("/health")
async def health_check():
    """Health check endpoint with service dependencies"""
    health_status = {
        "status": "healthy",
        "service": "SecureAsk GraphRAG API",
        "version": "1.0.0",
        "timestamp": time.time(),
        "dependencies": {}
    }
    
    # Check Neo4j
    try:
        if neo4j_client and neo4j_client.driver:
            await neo4j_client.driver.verify_connectivity()
            health_status["dependencies"]["neo4j"] = "healthy"
        else:
            health_status["dependencies"]["neo4j"] = "disconnected"
    except Exception:
        health_status["dependencies"]["neo4j"] = "unhealthy"
        health_status["status"] = "degraded"
    
    # Check Redis
    try:
        if redis_client and redis_client.client:
            await redis_client.client.ping()
            health_status["dependencies"]["redis"] = "healthy"
        else:
            health_status["dependencies"]["redis"] = "disconnected"
    except Exception:
        health_status["dependencies"]["redis"] = "unhealthy"
        # Redis failure doesn't make service unhealthy, just disables caching
    
    return health_status

# Main query endpoint with rate limiting
@app.post("/api/v1/query", response_model=QueryResponse)
@rate_limit_query("30/minute")  # Higher limit for production demo
async def create_query(
    request: QueryRequest,
    http_request: Request,
    # user: dict = Depends(AuthMiddleware.verify_token)  # Disabled for hackathon demo
) -> QueryResponse:
    """
    Submit a query for GraphRAG processing with caching and rate limiting
    
    This endpoint:
    1. Validates the query and checks rate limits
    2. Checks cache for similar queries
    3. Performs graph traversal to find relevant nodes
    4. Fetches live data from external sources if needed
    5. Uses GraphRAG to synthesize an answer
    6. Caches results and returns with citations and graph paths
    """
    start_time = time.time()
    
    try:
        # Check rate limits
        await rate_limiter.check_rate_limit(http_request, "query", "30/minute")
        
        # Generate cache key for query
        query_hash = hashlib.md5(
            f"{request.question}:{sorted(request.sources)}:{request.max_hops}".encode()
        ).hexdigest()
        
        # Check cache first
        cached_result = await redis_client.get_cached_query_result(query_hash)
        if cached_result:
            log_cache_operation("hit", query_hash, True)
            logger.info("Query served from cache", query_hash=query_hash)
            return QueryResponse(**cached_result)
        
        log_cache_operation("miss", query_hash, False)
        logger.info("Processing new query", query_preview=request.question[:100])
        
        # Process the query using GraphRAG
        result = await graphrag_engine.process_query(
            question=request.question,
            max_hops=request.max_hops,
            sources=request.sources,
            user_id="demo-user"  # Fixed for hackathon
        )
        
        processing_time = round((time.time() - start_time) * 1000, 2)
        
        # Cache the result
        await redis_client.cache_query_result(
            query_hash, 
            result.model_dump(), 
            ttl=1800  # 30 minutes
        )
        
        # Log query metrics
        log_query_processing(
            query=request.question,
            sources=request.sources,
            processing_time=processing_time,
            graph_hops=request.max_hops,
            result_count=len(result.citations) if result.citations else 0
        )
        
        logger.info("Query completed", processing_time=processing_time, query_hash=query_hash)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        processing_time = round((time.time() - start_time) * 1000, 2)
        logger.error(
            "Query processing failed", 
            error=str(e), 
            processing_time=processing_time,
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query processing failed: {str(e)}"
        )

# Get query status/results
@app.get("/api/v1/query/{query_id}", response_model=QueryResponse)
async def get_query(
    query_id: str,
    user: dict = Depends(AuthMiddleware.verify_token)
) -> QueryResponse:
    """Get query status and results by ID"""
    try:
        result = await graphrag_engine.get_query_result(query_id, user["user_id"])
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Query not found"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve query {query_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve query"
        )

# Document ingestion endpoint
@app.post("/api/v1/ingest")
async def ingest_document(
    request: IngestRequest,
    user: dict = Depends(AuthMiddleware.verify_token)
):
    """Ingest a document into the knowledge graph"""
    try:
        result = await graphrag_engine.ingest_document(
            source=request.source,
            url=request.url,
            content=request.content,
            metadata=request.metadata
        )
        return result
    except Exception as e:
        logger.error(f"Document ingestion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document ingestion failed: {str(e)}"
        )

# Graph search request model
class GraphSearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    node_type: Optional[str] = Field(None, description="Filter by node type")
    limit: int = Field(10, description="Maximum results")

# Graph search endpoint
@app.post("/api/v1/graph/search")
async def search_graph(
    request: GraphSearchRequest,
    user: dict = Depends(AuthMiddleware.verify_token)
):
    """Search nodes in the knowledge graph"""
    try:
        results = await neo4j_client.search_nodes(
            query_text=request.query,
            node_type=request.node_type,
            limit=request.limit
        )
        return {"nodes": results, "totalCount": len(results)}
    except Exception as e:
        logger.error(f"Graph search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Graph search failed"
        )

# Demo authentication endpoint with rate limiting
@app.post("/api/v1/auth/demo")
@rate_limit_auth("10/minute")
async def demo_login(http_request: Request):
    """Create a demo JWT token for hackathon"""
    try:
        # Check rate limits
        await rate_limiter.check_rate_limit(http_request, "auth", "10/minute")
        
        token = AuthMiddleware.create_token(
            user_id="demo-user",
            role="analyst"
        )
        
        logger.info("Demo token created", user_id="demo-user")
        return {"token": token, "user_id": "demo-user"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Token creation failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token creation failed"
        )

# Enhanced error handler with structured logging
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with structured logging"""
    error_id = f"err_{int(time.time() * 1000000)}"
    
    logger.error(
        "Unhandled exception",
        error_id=error_id,
        error_type=type(exc).__name__,
        error_message=str(exc),
        path=str(request.url.path),
        method=request.method,
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "error_id": error_id,
                "timestamp": time.time()
            }
        }
    )

# Add rate limit headers to responses
@app.middleware("http")
async def add_rate_limit_headers(request: Request, call_next):
    """Add rate limit headers to responses"""
    response = await call_next(request)
    
    # Add rate limit headers if available
    if hasattr(request.state, 'rate_limit_remaining'):
        response.headers["X-RateLimit-Limit"] = str(request.state.rate_limit_limit)
        response.headers["X-RateLimit-Remaining"] = str(request.state.rate_limit_remaining)
        response.headers["X-RateLimit-Reset"] = str(request.state.rate_limit_reset)
    
    return response

if __name__ == "__main__":
    # For local development
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )