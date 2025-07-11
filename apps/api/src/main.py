#!/usr/bin/env python3
"""
SecureAsk GraphRAG API
Main FastAPI application wrapping Microsoft GraphRAG for financial intelligence
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, Any, List

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn

# Import our modules (we'll create these next)
from core.graphrag_engine import GraphRAGEngine
from core.models import QueryRequest, QueryResponse, IngestRequest
from db.neo4j_client import Neo4jClient
from db.redis_client import RedisClient
from middleware.auth import AuthMiddleware
from connectors.sec_connector import SECConnector
from connectors.reddit_connector import RedditConnector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global clients (initialized in lifespan)
neo4j_client: Neo4jClient = None
redis_client: RedisClient = None
graphrag_engine: GraphRAGEngine = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources"""
    global neo4j_client, redis_client, graphrag_engine
    
    try:
        logger.info("🚀 Starting SecureAsk GraphRAG API...")
        
        # Initialize clients
        neo4j_client = Neo4jClient()
        await neo4j_client.connect()
        
        redis_client = RedisClient()
        await redis_client.connect()
        
        # Initialize GraphRAG engine
        graphrag_engine = GraphRAGEngine(neo4j_client, redis_client)
        await graphrag_engine.initialize()
        
        logger.info("✅ SecureAsk API initialized successfully")
        yield
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize SecureAsk API: {e}")
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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "SecureAsk GraphRAG API",
        "version": "1.0.0"
    }

# Main query endpoint
@app.post("/api/v1/query", response_model=QueryResponse)
async def create_query(
    request: QueryRequest,
    user: dict = Depends(AuthMiddleware.verify_token)
) -> QueryResponse:
    """
    Submit a query for GraphRAG processing
    
    This endpoint:
    1. Validates the query
    2. Performs graph traversal to find relevant nodes
    3. Fetches live data from external sources if needed
    4. Uses GraphRAG to synthesize an answer
    5. Returns results with citations and graph paths
    """
    try:
        logger.info(f"Processing query: {request.question[:100]}...")
        
        # Process the query using GraphRAG
        result = await graphrag_engine.process_query(
            question=request.question,
            max_hops=request.max_hops,
            sources=request.sources,
            user_id=user["user_id"]
        )
        
        logger.info(f"Query completed in {result.processing_time}ms")
        return result
        
    except Exception as e:
        logger.error(f"Query processing failed: {e}")
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

# Demo authentication endpoint
@app.post("/api/v1/auth/demo")
async def demo_login():
    """Create a demo JWT token for hackathon"""
    token = AuthMiddleware.create_token(
        user_id="demo-user",
        role="analyst"
    )
    return {"token": token, "user_id": "demo-user"}

# Error handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "timestamp": "2025-07-11T00:00:00Z"
            }
        }
    )

if __name__ == "__main__":
    # For local development
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )