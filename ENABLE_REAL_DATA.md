# Enable Real Data for Reddit and TikTok in SecureAsk

This guide explains how to enable real data fetching from Reddit and TikTok instead of using mock data.

## Current Status

Both Reddit and TikTok connectors are already implemented to fetch real data, but they fall back to mock data when API credentials are missing or invalid.

## 1. Enable Real Reddit Data

### Option A: Use Public Reddit JSON API (No Auth Required - Limited)

The current implementation already tries to use Reddit's public JSON API. To ensure it works:

1. **Check if it's already working** by looking at your Replit logs:
   ```
   logger.info(f"Found {len(unique_results)} Reddit posts for: {query}")
   ```

2. **Common issues**:
   - Rate limiting (Reddit limits unauthenticated requests)
   - User-Agent blocking (some subreddits block generic user agents)
   - Network issues on Replit

3. **Quick fix** - Add delays between requests:
   ```python
   # In reddit_connector.py, line 29, add:
   await asyncio.sleep(0.5)  # Add delay between subreddit searches
   ```

### Option B: Use Reddit OAuth2 API (Recommended)

1. **Create a Reddit App**:
   - Go to https://www.reddit.com/prefs/apps
   - Click "Create App" or "Create Another App"
   - Fill in:
     - Name: SecureAsk
     - App type: Select "script"
     - Description: Financial intelligence API
     - About URL: Your API URL
     - Redirect URI: http://localhost:8000/callback (not used for script apps)
   - Click "Create app"

2. **Get your credentials**:
   - Client ID: The string under "personal use script"
   - Client Secret: The secret string

3. **Update your Replit environment variables**:
   - Go to Replit Secrets (lock icon in sidebar)
   - Add:
     ```
     REDDIT_CLIENT_ID=your_actual_client_id
     REDDIT_CLIENT_SECRET=your_actual_client_secret
     REDDIT_USER_AGENT=SecureAsk/1.0 by /u/yourusername
     ```

4. **Update the RedditConnector** to use OAuth2 (optional enhancement).

## 2. Enable Real TikTok Data

### Using Apify (Current Implementation)

1. **Create an Apify account**:
   - Go to https://apify.com
   - Sign up for a free account
   - You get $5 free credits monthly (enough for ~1000 TikTok searches)

2. **Get your API token**:
   - Go to Settings → Integrations → API
   - Copy your Personal API token

3. **Update your Replit environment variables**:
   - Go to Replit Secrets
   - Add:
     ```
     APIFY_TOKEN=your_actual_apify_token
     ```
   - Note: The env var in code looks for `APIFY_TOKEN` (line 27 of tiktok_connector.py)

4. **Verify the actor is available**:
   - The connector uses `clockworks/free-tiktok-scraper`
   - Check if it's still available at: https://apify.com/clockworks/free-tiktok-scraper
   - If not, find an alternative TikTok scraper on Apify Store

### Alternative: RapidAPI TikTok API

If Apify doesn't work, you can use RapidAPI's TikTok API:

1. Sign up at https://rapidapi.com
2. Subscribe to a TikTok API (many have free tiers)
3. Update the TikTokConnector to use RapidAPI instead

## 3. Testing Real Data

Once you've added the credentials:

1. **Restart your Replit**:
   - Click "Stop" then "Run" in Replit

2. **Test with curl**:
   ```bash
   curl -X POST https://your-replit-url/api/v1/query \
     -H "Content-Type: application/json" \
     -d '{
       "question": "What are Apple ESG risks?",
       "sources": ["reddit", "tiktok"],
       "include_answer": true
     }'
   ```

3. **Check the logs** in Replit console:
   - Look for: "No APIFY_TOKEN found, using fallback data" (TikTok)
   - Look for: "Reddit API returned {status}" messages
   - If you see these, the credentials aren't loaded properly

## 4. Troubleshooting

### Reddit Issues:
- **429 Too Many Requests**: Add authentication or increase delays
- **403 Forbidden**: Check User-Agent header, some subreddits block bots
- **Empty results**: Try different subreddits or search terms

### TikTok Issues:
- **Apify token invalid**: Check token in Apify dashboard
- **Actor not found**: The free scraper might be deprecated, find another
- **Timeout**: TikTok scraping can be slow, increase timeout

### Quick Debug:
Add this to your connectors to see what's happening:
```python
logger.error(f"Using fallback data. Token present: {bool(api_token)}")
```

## 5. Monitor Usage

- **Reddit**: Public API has strict rate limits (~60 requests per minute)
- **Apify**: Monitor credits at https://console.apify.com/billing
- **Logs**: Check Replit logs for API errors and fallback usage

## Note on Fallback Data

The current implementation returns comprehensive fallback data when APIs fail. This ensures the demo always works but masks real API issues. Consider reducing fallback data to see actual errors during development.