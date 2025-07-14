#!/bin/bash
# Quick test script for SecureAsk API with real data

echo "🧪 Testing SecureAsk API Real Data"
echo "=================================="

# Your Replit URL
API_URL="https://secureask-kevin-vandever.replit.app"

echo ""
echo "1️⃣ Testing Reddit only:"
echo "------------------------"
curl -X POST "$API_URL/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are Apple ESG risks?",
    "sources": ["reddit"],
    "include_answer": false
  }' | jq '.result.citations[] | {source, snippet: .snippet[0:100]}'

echo ""
echo ""
echo "2️⃣ Testing TikTok only:"
echo "------------------------"
curl -X POST "$API_URL/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Apple sustainability",
    "sources": ["tiktok"],
    "include_answer": false
  }' | jq '.result.citations[] | {source, author, title: .title[0:80]}'

echo ""
echo ""
echo "3️⃣ Testing Both Sources:"
echo "-------------------------"
curl -X POST "$API_URL/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Tesla ESG concerns",
    "sources": ["reddit", "tiktok"],
    "include_answer": true
  }' | jq '{
    answer: .result.answer[0:200],
    citation_count: (.result.citations | length),
    sources: [.result.citations[].source] | unique
  }'

echo ""
echo ""
echo "✅ Check the results above:"
echo "- If you see real URLs and varied content, real data is working!"
echo "- If you see generic content or mock URLs, check your API tokens"
echo "- Look for 'FinanceInfluencer' (TikTok) or '12345' (Reddit) = mock data"