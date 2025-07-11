#!/bin/bash

# SecureAsk API Deployment Script
# Deploys to Railway with proper environment configuration

echo "🚀 Deploying SecureAsk GraphRAG API to Railway..."

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Installing..."
    curl -fsSL https://railway.app/install.sh | sh
    export PATH=$PATH:~/.railway/bin
fi

# Login to Railway
echo "🔐 Logging into Railway..."
railway login --browserless

# Create a new Railway project
echo "📦 Creating Railway project..."
railway init secureask-api --template blank

# Set environment variables
echo "🔧 Setting environment variables..."

# Neo4j Configuration (use the existing Aura instance)
railway env set NEO4J_URI="neo4j+s://5abb8f53.databases.neo4j.io"
railway env set NEO4J_USERNAME="neo4j"
railway env set NEO4J_PASSWORD="your-password-here"  # You'll need to update this

# Redis Configuration (Railway will provide)
railway env set REDIS_URL=""  # Will be set automatically by Railway Redis addon

# JWT Secret
railway env set JWT_SECRET="$(openssl rand -hex 32)"

# API Configuration
railway env set ENVIRONMENT="production"
railway env set LOG_LEVEL="info"
railway env set PORT="8000"

# Optional: External API keys (set these if you have them)
# railway env set APIFY_TOKEN="your-apify-token"
# railway env set REDDIT_CLIENT_ID="your-reddit-client-id"

# Add Redis addon
echo "📊 Adding Redis addon..."
railway add redis

# Deploy the service
echo "🚀 Deploying to Railway..."
railway up --detach

# Get the deployment URL
echo "🌐 Getting deployment URL..."
DEPLOY_URL=$(railway status --json | grep -o '"url":"[^"]*' | cut -d'"' -f4)

echo ""
echo "✅ Deployment complete!"
echo "🌐 API URL: $DEPLOY_URL"
echo "📋 Health check: $DEPLOY_URL/health"
echo "🔗 Query endpoint: $DEPLOY_URL/api/v1/query"
echo ""
echo "📝 Next steps:"
echo "1. Update Neo4j password in Railway dashboard"
echo "2. Test the API endpoints"
echo "3. Update MindStudio workflow with the API URL"
echo ""
echo "🎯 For judges, use:"
echo "   - Demo URL: $DEPLOY_URL/api/v1/query"
echo "   - Health URL: $DEPLOY_URL/health"
echo "   - Auth URL: $DEPLOY_URL/api/v1/auth/demo"