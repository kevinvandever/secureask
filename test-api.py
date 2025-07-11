#!/usr/bin/env python3
"""
Test script for SecureAsk GraphRAG API
"""

import asyncio
import aiohttp
import json
import sys

API_BASE = "http://localhost:8000"

async def test_api():
    """Test the SecureAsk API endpoints"""
    
    async with aiohttp.ClientSession() as session:
        try:
            # Test health endpoint
            print("🔍 Testing health endpoint...")
            async with session.get(f"{API_BASE}/health") as response:
                if response.status == 200:
                    health = await response.json()
                    print(f"✅ Health check: {health['status']}")
                else:
                    print(f"❌ Health check failed: {response.status}")
                    return False
            
            # Get demo JWT token
            print("\n🔑 Getting demo JWT token...")
            async with session.post(f"{API_BASE}/api/v1/auth/demo") as response:
                if response.status == 200:
                    auth_data = await response.json()
                    token = auth_data["token"]
                    print(f"✅ Got demo token for user: {auth_data['user_id']}")
                else:
                    print(f"❌ Failed to get demo token: {response.status}")
                    return False
            
            # Set up headers with token
            headers = {"Authorization": f"Bearer {token}"}
            
            # Test query endpoint
            print("\n🤖 Testing GraphRAG query...")
            query_data = {
                "question": "What are Apple's main ESG risks according to recent filings?",
                "max_hops": 2,
                "sources": ["sec", "reddit"]
            }
            
            async with session.post(
                f"{API_BASE}/api/v1/query",
                json=query_data,
                headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Query completed in {result['result']['processing_time']}ms")
                    print(f"   Answer: {result['result']['answer'][:100]}...")
                    print(f"   Citations: {len(result['result']['citations'])}")
                    print(f"   Graph path: {' -> '.join(result['result']['graph_path'])}")
                else:
                    error = await response.text()
                    print(f"❌ Query failed: {response.status}")
                    print(f"   Error: {error}")
                    return False
            
            # Test graph search
            print("\n🔍 Testing graph search...")
            search_params = {
                "query": "Apple",
                "limit": 5
            }
            
            async with session.post(
                f"{API_BASE}/api/v1/graph/search",
                params=search_params,
                headers=headers
            ) as response:
                if response.status == 200:
                    results = await response.json()
                    print(f"✅ Found {results['totalCount']} nodes")
                    for node in results['nodes'][:2]:
                        print(f"   - {node['name']} ({node['type']})")
                else:
                    print(f"❌ Graph search failed: {response.status}")
            
            print("\n🎉 All API tests passed!")
            return True
            
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            return False

if __name__ == "__main__":
    print("🚀 Testing SecureAsk GraphRAG API")
    print("Make sure the API is running on http://localhost:8000")
    print("-" * 50)
    
    success = asyncio.run(test_api())
    sys.exit(0 if success else 1)