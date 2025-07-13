#!/usr/bin/env python3
"""Test the API fixes for SecureAsk"""

import requests
import json
import sys

# API endpoint
API_URL = "https://c812e514-d8f5-42db-ad93-bbc36e2f406b-00-34xg5tvub1ese.picard.replit.dev/api/v1/query"

# Test questions
questions = [
    "What climate-risk disclosures did Apple include in its 2024 10-K?",
    "What are Tesla's supply chain sustainability challenges?",
    "How do retail investors view Microsoft's AI strategy?",
]

print("🧪 Testing SecureAsk API Fixes\n")

for i, question in enumerate(questions):
    print(f"Test {i+1}: {question}")
    
    # Test with include_answer=False (citations only)
    payload = {
        "question": question,
        "max_hops": 3,
        "sources": ["sec", "reddit", "tiktok"],
        "include_answer": False
    }
    
    try:
        response = requests.post(API_URL, json=payload)
        if response.status_code == 200:
            data = response.json()
            result = data.get("result", {})
            
            print(f"✅ Status: {data.get('status')}")
            print(f"   Answer: {result.get('answer', 'None (as expected)')}")
            print(f"   Citations: {len(result.get('citations', []))} found")
            
            # Show first citation snippet
            citations = result.get('citations', [])
            if citations:
                first_citation = citations[0]
                print(f"   First citation snippet: {first_citation['snippet'][:100]}...")
                
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
    
    print("-" * 80)
    
print("\n💡 Summary:")
print("If citations now contain question-specific content instead of generic text,")
print("the fix is working! MindStudio can use these rich citations for synthesis.")