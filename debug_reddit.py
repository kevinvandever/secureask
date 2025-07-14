#!/usr/bin/env python3
"""Debug Reddit connector issues"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, '/Users/kevinvandever/kev-dev/secureask')

from connectors.reddit_connector import RedditConnector
from core.models import SourceType

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

async def test_source_enum():
    """Test source type enum"""
    print(f"\n🔍 Testing source types...")
    print(f"SourceType.REDDIT = '{SourceType.REDDIT}'")
    print(f"Request source 'reddit' == SourceType.REDDIT: {'reddit' == SourceType.REDDIT}")
    
if __name__ == "__main__":
    asyncio.run(test_reddit_directly())
    asyncio.run(test_source_enum())