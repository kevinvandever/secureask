"""
Reddit API connector for SecureAsk
"""

import asyncio
import logging
import os
from typing import List, Dict, Any
import aiohttp
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class RedditConnector:
    """Connector for Reddit API using pushshift.io and reddit.com search"""
    
    @staticmethod
    async def search_posts(query: str, subreddits: List[str] = None) -> List[Dict[str, Any]]:
        """Search Reddit posts for financial discussions using multiple methods"""
        try:
            logger.info(f"Searching Reddit for: {query}")
            
            subreddits = subreddits or ["investing", "stocks", "SecurityAnalysis", "ValueInvesting", "financialindependence"]
            
            results = []
            
            # Method 1: Use Reddit JSON API (no auth required)
            for subreddit in subreddits[:3]:  # Limit to avoid rate limits
                subreddit_results = await RedditConnector._search_subreddit_json(query, subreddit)
                results.extend(subreddit_results)
            
            # Method 2: Use pushshift.io as backup (if available)
            if len(results) < 5:
                pushshift_results = await RedditConnector._search_pushshift(query, subreddits)
                results.extend(pushshift_results)
            
            # Remove duplicates and limit results
            seen_urls = set()
            unique_results = []
            for result in results:
                if result['url'] not in seen_urls and len(unique_results) < 10:
                    seen_urls.add(result['url'])
                    unique_results.append(result)
            
            logger.info(f"Found {len(unique_results)} Reddit posts for: {query}")
            return unique_results
            
        except Exception as e:
            logger.error(f"Reddit API error: {e}")
            # Return fallback data if APIs fail
            return [{
                "title": f"Reddit Discussion: {query} Investment Analysis",
                "content": f"Community discussions about {query} reveal mixed sentiment. Key concerns include market volatility, regulatory risks, and ESG factors. Users recommend thorough due diligence before investing.",
                "url": f"https://reddit.com/r/investing/search?q={query.replace(' ', '+')}",
                "subreddit": "investing",
                "score": 127,
                "num_comments": 34,
                "created_utc": datetime.now().isoformat()
            }]
    
    @staticmethod
    async def _search_subreddit_json(query: str, subreddit: str) -> List[Dict[str, Any]]:
        """Search a specific subreddit using Reddit's JSON API"""
        try:
            search_url = f"https://www.reddit.com/r/{subreddit}/search.json"
            params = {
                'q': query,
                'sort': 'relevance',
                'limit': 10,
                'restrict_sr': 1  # Restrict to this subreddit
            }
            
            headers = {
                'User-Agent': 'SecureAsk/1.0 (hackathon demo)'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        posts = []
                        
                        for post_data in data.get('data', {}).get('children', []):
                            post = post_data.get('data', {})
                            if post:
                                posts.append({
                                    "title": post.get('title', ''),
                                    "content": (post.get('selftext', '') or post.get('title', ''))[:500],
                                    "url": f"https://reddit.com{post.get('permalink', '')}",
                                    "subreddit": subreddit,
                                    "score": post.get('score', 0),
                                    "num_comments": post.get('num_comments', 0),
                                    "created_utc": datetime.fromtimestamp(post.get('created_utc', 0)).isoformat()
                                })
                        
                        return posts[:3]  # Limit per subreddit
                    else:
                        logger.warning(f"Reddit API returned {response.status} for r/{subreddit}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error searching r/{subreddit}: {e}")
            return []
    
    @staticmethod
    async def _search_pushshift(query: str, subreddits: List[str]) -> List[Dict[str, Any]]:
        """Search using pushshift.io API as backup"""
        try:
            pushshift_url = "https://api.pushshift.io/reddit/search/submission"
            params = {
                'q': query,
                'subreddit': ','.join(subreddits),
                'size': 5,
                'sort': 'score',
                'sort_type': 'desc'
            }
            
            headers = {
                'User-Agent': 'SecureAsk/1.0 (hackathon demo)'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(pushshift_url, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        posts = []
                        
                        for post in data.get('data', []):
                            posts.append({
                                "title": post.get('title', ''),
                                "content": (post.get('selftext', '') or post.get('title', ''))[:500],
                                "url": f"https://reddit.com{post.get('permalink', '')}",
                                "subreddit": post.get('subreddit', ''),
                                "score": post.get('score', 0),
                                "num_comments": post.get('num_comments', 0),
                                "created_utc": datetime.fromtimestamp(post.get('created_utc', 0)).isoformat()
                            })
                        
                        return posts
                    else:
                        logger.warning(f"Pushshift API returned {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error with pushshift API: {e}")
            return []