#!/usr/bin/env python3
"""Test the API locally"""

import requests
import json

# Start the API server first: python -m uvicorn main:app --port 8000

BASE_URL = "http://localhost:8000"

# Test health endpoint
print("1. Testing health endpoint...")
response = requests.get(f"{BASE_URL}/health")
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}\n")

# Get auth token
print("2. Getting auth token...")
response = requests.post(f"{BASE_URL}/api/v1/auth/demo")
print(f"Status: {response.status_code}")
auth_data = response.json()
print(f"Response: {auth_data}\n")
token = auth_data["token"]

# Test query endpoint
print("3. Testing GraphRAG query...")
headers = {"Authorization": f"Bearer {token}"}
query_data = {
    "question": "What are Apple's main ESG risks according to recent filings?",
    "max_hops": 2,
    "sources": ["sec", "reddit"]
}

response = requests.post(
    f"{BASE_URL}/api/v1/query",
    json=query_data,
    headers=headers
)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print(f"Query ID: {result['query_id']}")
    print(f"Answer: {result['result']['answer'][:200]}...")
    print(f"Citations: {len(result['result']['citations'])}")
else:
    print(f"Error: {response.text}")