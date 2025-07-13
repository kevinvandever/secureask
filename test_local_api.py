#!/usr/bin/env python3
"""Test the GraphRAG engine locally to verify fixes"""

import asyncio
from core.graphrag_engine import GraphRAGEngine
from core.models import SourceType
from db.neo4j_client import Neo4jClient
from db.redis_client import RedisClient

async def test_fix():
    # Initialize clients
    neo4j = Neo4jClient()
    redis = RedisClient()
    
    # Create engine
    engine = GraphRAGEngine(neo4j, redis)
    
    # Test question
    question = "What climate-risk disclosures did Apple include in its 2024 10-K?"
    
    # Mock external data response
    from core.models import ExternalAPIResponse
    
    # Create mock SEC data
    sec_response = ExternalAPIResponse(
        source=SourceType.SEC,
        data=[{
            "company": "AAPL",
            "filing_type": "10-K", 
            "url": "https://www.sec.gov/test",
            "content": "Apple Inc. faces several climate-related risks. Physical risks include disruption from extreme weather. Transition risks include carbon pricing. We have committed to carbon neutrality by 2030.",
            "cik": "0000320193",
            "accession": "test-001"
        }],
        metadata={},
        cached=False
    )
    
    # Test the reasoning function directly
    result = await engine._run_graphrag_reasoning(
        question=question,
        relevant_nodes=[],
        external_data=[sec_response],
        include_answer=False
    )
    
    print(f"Answer: {result['answer']}")
    print(f"Citations: {len(result['citations'])}")
    
    for i, citation in enumerate(result['citations']):
        print(f"\nCitation {i+1}:")
        print(f"  Source: {citation['source']}")
        print(f"  Snippet: {citation['snippet'][:100]}...")

if __name__ == "__main__":
    asyncio.run(test_fix())