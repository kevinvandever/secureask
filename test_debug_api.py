#!/usr/bin/env python3
"""Debug script to test the actual API"""

import asyncio
import json
import aiohttp

async def test_api_with_debug():
    """Test the API with debug output"""
    api_url = "http://localhost:8000"
    
    query_data = {
        "question": "What are Apple's ESG risks?",
        "sources": ["sec", "reddit", "tiktok"],
        "include_answer": False
    }
    
    print("=" * 60)
    print("🔍 Testing Real API with Debug")
    print("=" * 60)
    print(f"Query: {query_data}")
    print()
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{api_url}/api/v1/query",
                json=query_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                print(f"Status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    result = data.get('result', {})
                    citations = result.get('citations', [])
                    
                    print(f"✅ API query successful!")
                    print(f"   Total citations: {len(citations)}")
                    
                    # Check source distribution
                    sources = {}
                    for citation in citations:
                        source = citation.get('source', 'unknown')
                        sources[source] = sources.get(source, 0) + 1
                    
                    print(f"   Source breakdown: {sources}")
                    
                    # Show all citations
                    print("\n📊 All Citations:")
                    for i, citation in enumerate(citations):
                        print(f"\nCitation {i+1}:")
                        print(f"  Source: {citation.get('source')}")
                        print(f"  URL: {citation.get('url', 'N/A')}")
                        print(f"  Snippet: {citation.get('snippet', '')[:100]}...")
                        print(f"  Confidence: {citation.get('confidence', 'N/A')}")
                        
                    # Show raw data if available
                    raw_data = result.get('raw_data', {})
                    if raw_data:
                        print(f"\n📈 Raw Data Counts:")
                        print(f"  SEC: {raw_data.get('sec_count', 0)}")
                        print(f"  Reddit: {raw_data.get('reddit_count', 0)}")
                        print(f"  TikTok: {raw_data.get('tiktok_count', 0)}")
                        
                else:
                    print(f"❌ API request failed with status: {response.status}")
                    error_text = await response.text()
                    print(f"   Error: {error_text}")
                    
    except Exception as e:
        print(f"❌ API test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_api_with_debug())