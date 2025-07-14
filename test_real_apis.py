#!/usr/bin/env python3
"""Test script to verify Reddit and TikTok real data fetching"""

import asyncio
import json
from connectors.reddit_connector import RedditConnector
from connectors.tiktok_connector import TikTokConnector

async def test_reddit():
    """Test Reddit API with real data"""
    print("\n🔍 Testing Reddit Connector...")
    print("-" * 50)
    
    try:
        # Test with a simple query
        results = await RedditConnector.search_posts(
            query="Apple ESG risks",
            subreddits=["investing", "stocks"]
        )
        
        print(f"✅ Found {len(results)} Reddit posts")
        
        if results and len(results) > 0:
            # Check if it's real data or mock
            first_post = results[0]
            if "12345" in first_post.get('url', ''):
                print("⚠️  WARNING: This appears to be MOCK data")
                print("   Check that REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET are set in Replit Secrets")
            else:
                print("✨ This appears to be REAL Reddit data!")
                print(f"\nFirst post:")
                print(f"  Title: {first_post.get('title', '')[:80]}...")
                print(f"  URL: {first_post.get('url', '')}")
                print(f"  Score: {first_post.get('score', 0)}")
                print(f"  Subreddit: r/{first_post.get('subreddit', '')}")
        
        return results
        
    except Exception as e:
        print(f"❌ Reddit test failed: {e}")
        return []

async def test_tiktok():
    """Test TikTok API with real data"""
    print("\n📱 Testing TikTok Connector...")
    print("-" * 50)
    
    try:
        # Test with a simple query
        results = await TikTokConnector.search_content(
            query="Apple stock",
            count=5
        )
        
        print(f"✅ Found {len(results)} TikTok videos")
        
        if results and len(results) > 0:
            # Check if it's real data or mock
            first_video = results[0]
            if "FinanceInfluencer" in first_video.get('author', ''):
                print("⚠️  WARNING: This appears to be MOCK data")
                print("   Check that APIFY_TOKEN is set in Replit Secrets")
            else:
                print("✨ This appears to be REAL TikTok data!")
                print(f"\nFirst video:")
                print(f"  Title: {first_video.get('title', '')[:80]}...")
                print(f"  Author: @{first_video.get('author', '')}")
                print(f"  Views: {first_video.get('views', 0):,}")
                print(f"  URL: {first_video.get('url', '')}")
        
        return results
        
    except Exception as e:
        print(f"❌ TikTok test failed: {e}")
        return []

async def test_full_api():
    """Test the full API endpoint"""
    print("\n🚀 Testing Full API Query...")
    print("-" * 50)
    
    import aiohttp
    
    # Update this with your Replit URL
    api_url = "https://secureask-kevin-vandever.replit.app"
    
    query_data = {
        "question": "What are Apple's ESG risks?",
        "sources": ["reddit", "tiktok"],  # Only test social media
        "include_answer": True
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{api_url}/api/v1/query",
                json=query_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    result = data.get('result', {})
                    citations = result.get('citations', [])
                    
                    print(f"✅ API query successful!")
                    print(f"   Citations returned: {len(citations)}")
                    
                    # Check source distribution
                    sources = {}
                    for citation in citations:
                        source = citation.get('source', 'unknown')
                        sources[source] = sources.get(source, 0) + 1
                    
                    print(f"   Source breakdown: {sources}")
                    
                    # Show sample citations
                    print("\nSample citations:")
                    for i, citation in enumerate(citations[:3]):
                        print(f"\n   Citation {i+1}:")
                        print(f"   Source: {citation.get('source')}")
                        print(f"   Snippet: {citation.get('snippet', '')[:100]}...")
                        
                else:
                    print(f"❌ API request failed with status: {response.status}")
                    error_text = await response.text()
                    print(f"   Error: {error_text[:200]}")
                    
    except Exception as e:
        print(f"❌ API test failed: {e}")

async def main():
    """Run all tests"""
    print("=" * 60)
    print("🧪 SecureAsk Real Data Testing")
    print("=" * 60)
    
    # Test individual connectors
    reddit_results = await test_reddit()
    tiktok_results = await test_tiktok()
    
    # Test full API
    await test_full_api()
    
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    print("=" * 60)
    print(f"Reddit: {'✅ Working' if reddit_results else '❌ Not working'}")
    print(f"TikTok: {'✅ Working' if tiktok_results else '❌ Not working'}")
    print("\nNext steps:")
    print("1. If you see MOCK data warnings, add the required API tokens to Replit Secrets")
    print("2. If you see real data, you're ready to use with MindStudio!")
    print("3. Check Replit logs for any error details")

if __name__ == "__main__":
    asyncio.run(main())