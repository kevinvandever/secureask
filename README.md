# SecureAsk - Graph-Structured RAG for Financial Intelligence

Enterprise-grade GraphRAG system for multi-hop reasoning across SEC filings, Reddit, and TikTok.

## Quick Deploy for MindStudio

```bash
# Deploy to Railway
cd apps/api
./deploy.sh
```

## API Endpoints

- Production: https://secureask-api.up.railway.app/api/v1/query
- Health: https://secureask-api.up.railway.app/health
- Auth: https://secureask-api.up.railway.app/api/v1/auth/demo

## Features

- Real SEC EDGAR API integration
- Live Reddit data fetching  
- TikTok content analysis via Apify
- Neo4j graph database
- Multi-source reasoning
- Full citation trails

Built for MindStudio.ai Hackathon.
