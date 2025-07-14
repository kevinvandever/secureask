#!/usr/bin/env python3
"""Debug Reddit connector issues"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, '/Users/kevinvandever/kev-dev/secureask')

from connectors.reddit_connector import RedditConnector
from core.models import SourceType
from core.graphrag_engine import GraphRAGEngine
import re

async def test_reddit_directly():
    """Test Reddit connector directly"""
    print("🧪 Testing Reddit connector directly...")
    
    try:
        results = await RedditConnector.search_posts(
            query="Microsoft ESG concerns",
            subreddits=["investing", "stocks"]
        )
        
        print(f"✅ Reddit connector returned {len(results)} posts")
        if results:
            print(f"First post: {results[0]['title'][:80]}...")
            print(f"URL: {results[0]['url']}")
        else:
            print("❌ No posts returned")
            
        return results
        
    except Exception as e:
        print(f"❌ Reddit connector failed: {e}")
        import traceback
        traceback.print_exc()
        return []

async def test_search_terms():
    """Test search terms extraction"""
    print(f"\n🔍 Testing search terms extraction...")
    
    question = "Microsoft ESG concerns"
    
    # Replicate the search term extraction logic
    stop_words = {'what', 'are', 'the', 'is', 'how', 'does', 'do', 'can', 'will', 'would', 'should'}
    words = re.findall(r'\b\w+\b', question.lower())
    relevant_words = [w for w in words if w not in stop_words and len(w) > 2]
    search_terms = ' '.join(relevant_words[:5])
    
    print(f"Question: '{question}'")
    print(f"Words: {words}")
    print(f"Relevant words: {relevant_words}")
    print(f"Search terms: '{search_terms}'")
    print(f"Search terms empty? {not search_terms}")

async def test_source_enum():
    """Test source type enum"""
    print(f"\n🔍 Testing source types...")
    print(f"SourceType.REDDIT = '{SourceType.REDDIT}'")
    print(f"SourceType.REDDIT.value = '{SourceType.REDDIT.value}'")
    print(f"Request source 'reddit' == SourceType.REDDIT: {'reddit' == SourceType.REDDIT}")
    print(f"Request source 'reddit' == SourceType.REDDIT.value: {'reddit' == SourceType.REDDIT.value}")
    
    # Test the actual sources list
    sources = ["reddit"]
    print(f"Sources list: {sources}")
    for source in sources:
        print(f"  '{source}' == SourceType.REDDIT: {source == SourceType.REDDIT}")
        print(f"  '{source}' == SourceType.REDDIT.value: {source == SourceType.REDDIT.value}")
    
if __name__ == "__main__":
    asyncio.run(test_reddit_directly())
    asyncio.run(test_search_terms())
    asyncio.run(test_source_enum())