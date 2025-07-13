"""
Core data models for SecureAsk GraphRAG API
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from enum import Enum

class SourceType(str, Enum):
    """Available data sources"""
    SEC = "sec"
    REDDIT = "reddit"
    TIKTOK = "tiktok"

class QueryStatus(str, Enum):
    """Query processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Citation(BaseModel):
    """Citation for a piece of information"""
    node_id: str = Field(..., description="Graph node identifier")
    source: SourceType = Field(..., description="Data source")
    url: str = Field(..., description="Source URL")
    snippet: str = Field(..., description="Relevant text snippet")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")

class QueryRequest(BaseModel):
    """Request model for GraphRAG queries"""
    question: str = Field(..., min_length=1, max_length=1000, description="Natural language question")
    max_hops: int = Field(2, ge=1, le=3, description="Maximum graph traversal depth")
    sources: List[SourceType] = Field(
        default=[SourceType.SEC, SourceType.REDDIT, SourceType.TIKTOK],
        description="Data sources to include"
    )
    include_answer: bool = Field(True, description="Whether to generate an answer or just return citations")

class QueryResult(BaseModel):
    """Result data for completed queries"""
    answer: Optional[str] = Field(None, description="Generated answer (optional)")
    citations: List[Citation] = Field(..., description="Supporting citations")
    graph_path: List[str] = Field(..., description="Graph node IDs traversed")
    processing_time: int = Field(..., description="Processing time in milliseconds")

class QueryResponse(BaseModel):
    """Response model for GraphRAG queries"""
    query_id: str = Field(..., description="Unique query identifier")
    question: str = Field(..., description="Original question")
    status: QueryStatus = Field(..., description="Processing status")
    result: Optional[QueryResult] = Field(None, description="Query results if completed")
    created_at: datetime = Field(..., description="Query creation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Query completion timestamp")

class IngestRequest(BaseModel):
    """Request model for document ingestion"""
    source: SourceType = Field(..., description="Data source type")
    url: str = Field(..., description="Document URL")
    content: str = Field(..., description="Document content")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class GraphNode(BaseModel):
    """Graph node model"""
    id: str = Field(..., description="Unique node identifier")
    type: str = Field(..., description="Node type (Company, Risk, etc.)")
    name: str = Field(..., description="Display name")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Node properties")
    source: Optional[Dict[str, Any]] = Field(None, description="Source information")

class GraphEdge(BaseModel):
    """Graph edge model"""
    id: str = Field(..., description="Unique edge identifier")
    from_node_id: str = Field(..., description="Source node ID")
    to_node_id: str = Field(..., description="Target node ID")
    relationship_type: str = Field(..., description="Type of relationship")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Edge properties")
    weight: float = Field(1.0, description="Relationship strength")

class GraphPath(BaseModel):
    """Graph traversal path"""
    nodes: List[GraphNode] = Field(..., description="Nodes in path")
    edges: List[GraphEdge] = Field(..., description="Edges in path")
    length: int = Field(..., description="Path length")

class ExternalAPIResponse(BaseModel):
    """Response from external APIs"""
    source: SourceType = Field(..., description="API source")
    data: List[Dict[str, Any]] = Field(..., description="Retrieved data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Response metadata")
    cached: bool = Field(False, description="Whether response was cached")

class ProcessingContext(BaseModel):
    """Context for query processing"""
    user_id: str = Field(..., description="User identifier")
    query_id: str = Field(..., description="Query identifier")
    question: str = Field(..., description="Original question")
    max_hops: int = Field(..., description="Maximum traversal depth")
    sources: List[SourceType] = Field(..., description="Enabled sources")
    start_time: datetime = Field(default_factory=datetime.utcnow, description="Processing start time")