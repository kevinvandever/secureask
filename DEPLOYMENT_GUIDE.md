# SecureAsk API Deployment Guide

## Quick Start for Hackathon Judges

### Available API Environments

Your MindStudio workflow can use these URLs:

```
┌─────────────────────────────────────────────────────────────────┐
│ 🌐 Production (Railway)                                         │
│ https://secureask-api.up.railway.app/api/v1/query              │
├─────────────────────────────────────────────────────────────────┤
│ 🚀 Backup (Render)                                             │
│ https://secureask-api.onrender.com/api/v1/query                │
├─────────────────────────────────────────────────────────────────┤
│ ⚡ Serverless (Netlify)                                         │
│ https://secureask.netlify.app/.netlify/functions/api/v1/query  │
├─────────────────────────────────────────────────────────────────┤
│ 🔧 Local Development                                            │
│ http://localhost:8000/api/v1/query                             │
└─────────────────────────────────────────────────────────────────┘
```

### For MindStudio Configuration

**Recommended for Demo:**
- **Primary URL**: `https://secureask-api.up.railway.app/api/v1/query`
- **Health Check**: `https://secureask-api.up.railway.app/health`
- **Auth Token**: `https://secureask-api.up.railway.app/api/v1/auth/demo`

## Sample Questions for Judges to Test

### ESG and Risk Analysis
- "What are Apple's climate risks according to recent SEC filings?"
- "How is Tesla's ESG performance discussed on Reddit?"
- "What supply chain risks does Microsoft face?"

### Market Sentiment
- "What do retail investors think about NVIDIA's growth prospects?"
- "How is Amazon's AWS business perceived on social media?"
- "What are the main concerns about Meta's metaverse strategy?"

### Multi-Source Analysis
- "Compare SEC filings vs social media sentiment for Google's AI investments"
- "What regulatory risks does TikTok face according to official and social sources?"

## Real Data Sources

### 🏛️ SEC EDGAR API
- **Real SEC filings** (10-K, 10-Q, 8-K)
- **Live data** from sec.gov
- **Company tickers**: AAPL, MSFT, GOOGL, AMZN, TSLA, META, NVDA, NFLX, CRM, ORCL

### 📱 Reddit API
- **Subreddits**: r/investing, r/stocks, r/SecurityAnalysis, r/ValueInvesting
- **Real posts and discussions**
- **Sentiment analysis** from community

### 🎵 TikTok Content (via Apify)
- **Financial content creators**
- **Investment discussions**
- **Social sentiment analysis**

## Architecture Highlights

### Multi-Hop Graph Reasoning
```
User Question → Entity Extraction → Graph Search → External APIs → Synthesis
     ↓              ↓                   ↓              ↓           ↓
  "Apple risks"   [AAPL]         Neo4j nodes    SEC+Reddit    Final Answer
```

### Data Governance
- **No data copying** - queries at source
- **Full citation trails** - every fact is sourced
- **Real-time synthesis** - fresh data every query

### Performance Features
- **Concurrent API calls** - SEC/Reddit/TikTok in parallel
- **Smart caching** - Redis for repeated queries
- **Graceful fallbacks** - handles API failures

## Deployment Status

### ✅ Production Ready Features
- Real SEC EDGAR API integration
- Live Reddit data fetching
- TikTok content analysis (via Apify)
- Neo4j Aura cloud database
- JWT authentication
- Error handling and fallbacks
- Full citation tracking
- Multi-environment deployment

### 🔧 Technical Stack
- **Backend**: FastAPI + Python 3.11
- **Graph DB**: Neo4j Aura (cloud)
- **Cache**: Redis
- **APIs**: SEC EDGAR, Reddit JSON, Apify TikTok
- **Deployment**: Railway (primary), Render (backup)
- **Frontend**: MindStudio.ai workflow

## Quick Deploy Commands

```bash
# Deploy to Railway
cd apps/api
./deploy.sh

# Deploy backup to Render
# (Connect GitHub repo to Render service)

# Test deployment
curl https://secureask-api.up.railway.app/health
```

## Environment Variables

```env
# Database
NEO4J_URI=neo4j+s://5abb8f53.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password

# Cache
REDIS_URL=redis://...

# Security
JWT_SECRET=your-secret-key

# Optional APIs
APIFY_TOKEN=your-apify-token
REDDIT_CLIENT_ID=your-reddit-client-id
```

## For Production Scale

### Additional Environments
- **Staging**: `https://secureask-staging.up.railway.app/api/v1/query`
- **Development**: `https://secureask-dev.up.railway.app/api/v1/query`
- **Testing**: `https://secureask-test.up.railway.app/api/v1/query`

### Enterprise Features
- Rate limiting and API quotas
- User authentication and authorization
- Audit logging and compliance
- Custom data source connectors
- Advanced graph algorithms
- Real-time monitoring

## Contact for Demo Issues

If judges encounter any issues:
1. Check health endpoint first
2. Try backup URL (Render)
3. Use fallback mode in MindStudio
4. Contact demo support

**Primary Demo URL**: https://secureask-api.up.railway.app/api/v1/query