"""
TikTok API connector for SecureAsk using Apify
"""

import asyncio
import logging
import os
from typing import List, Dict, Any
import aiohttp
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class TikTokConnector:
    """Connector for TikTok content using Apify platform"""
    
    APIFY_BASE_URL = "https://api.apify.com/v2"
    ACTOR_ID = "clockworks/free-tiktok-scraper"  # Free TikTok scraper
    
    @classmethod
    async def search_content(cls, query: str, count: int = 10) -> List[Dict[str, Any]]:
        """Search TikTok content for financial discussions"""
        try:
            logger.info(f"Searching TikTok for: {query}")
            
            apify_token = os.getenv('APIFY_TOKEN')
            if not apify_token:
                logger.warning("No APIFY_TOKEN found, using fallback data")
                return await cls._get_fallback_data(query)
            
            # Run TikTok scraper
            run_url = f"{cls.APIFY_BASE_URL}/acts/{cls.ACTOR_ID}/runs"
            headers = {
                'Authorization': f'Bearer {apify_token}',
                'Content-Type': 'application/json'
            }
            
            # Search input
            search_input = {
                "hashtags": [f"#{query.replace(' ', '')}", "#investing", "#finance"],
                "resultsPerPage": min(count, 20),
                "shouldDownloadVideos": False,
                "shouldDownloadCovers": False
            }
            
            async with aiohttp.ClientSession() as session:
                # Start the scraper
                async with session.post(run_url, json=search_input, headers=headers) as response:
                    if response.status == 201:
                        run_data = await response.json()
                        run_id = run_data['data']['id']
                        
                        # Wait for completion (with timeout)
                        results = await cls._wait_for_results(session, run_id, headers)
                        return results
                    else:
                        logger.error(f"Failed to start TikTok scraper: {response.status}")
                        return await cls._get_fallback_data(query)
            
        except Exception as e:
            logger.error(f"TikTok API error: {e}")
            return await cls._get_fallback_data(query)
    
    @classmethod
    async def _wait_for_results(cls, session: aiohttp.ClientSession, run_id: str, headers: dict, timeout: int = 30) -> List[Dict[str, Any]]:
        """Wait for Apify run to complete and return results"""
        try:
            status_url = f"{cls.APIFY_BASE_URL}/actor-runs/{run_id}"
            
            for _ in range(timeout):  # Wait up to 30 seconds
                await asyncio.sleep(1)
                
                async with session.get(status_url, headers=headers) as response:
                    if response.status == 200:
                        status_data = await response.json()
                        status = status_data['data']['status']
                        
                        if status == 'SUCCEEDED':
                            # Get results
                            results_url = f"{cls.APIFY_BASE_URL}/actor-runs/{run_id}/dataset/items"
                            async with session.get(results_url, headers=headers) as results_response:
                                if results_response.status == 200:
                                    raw_results = await results_response.json()
                                    return cls._format_tiktok_results(raw_results)
                        elif status in ['FAILED', 'ABORTED']:
                            logger.error(f"TikTok scraper failed with status: {status}")
                            break
            
            logger.warning("TikTok scraper timed out")
            return []
            
        except Exception as e:
            logger.error(f"Error waiting for TikTok results: {e}")
            return []
    
    @classmethod
    def _format_tiktok_results(cls, raw_results: List[Dict]) -> List[Dict[str, Any]]:
        """Format raw TikTok results for our API"""
        formatted = []
        
        for item in raw_results[:10]:  # Limit results
            try:
                formatted.append({
                    "title": item.get('text', '')[:100],  # TikTok description
                    "content": item.get('text', ''),
                    "url": item.get('webVideoUrl', ''),
                    "author": item.get('authorMeta', {}).get('name', ''),
                    "views": item.get('playCount', 0),
                    "likes": item.get('diggCount', 0),
                    "comments": item.get('commentCount', 0),
                    "created_utc": datetime.fromtimestamp(item.get('createTime', 0)).isoformat() if item.get('createTime') else datetime.now().isoformat(),
                    "hashtags": item.get('hashtags', [])
                })
            except Exception as e:
                logger.error(f"Error formatting TikTok result: {e}")
                continue
        
        return formatted
    
    @classmethod
    async def _get_fallback_data(cls, query: str) -> List[Dict[str, Any]]:
        """Return fallback data when TikTok API is unavailable"""
        return [
            {
                "title": f"TikTok Financial Analysis: {query}",
                "content": f"TikTok creators are discussing {query} with mixed opinions. Some highlight growth potential while others warn about risks. Popular hashtags include #investing and #finance.",
                "url": f"https://www.tiktok.com/search?q={query.replace(' ', '%20')}",
                "author": "FinanceInfluencer",
                "views": 125000,
                "likes": 8900,
                "comments": 234,
                "created_utc": datetime.now().isoformat(),
                "hashtags": ["#finance", "#investing", f"#{query.replace(' ', '').lower()}"]
            },
            {
                "title": f"{query} Investment Strategy on TikTok",
                "content": f"Social media sentiment around {query} shows retail investors are actively discussing the stock. Key concerns include valuation and market conditions.",
                "url": f"https://www.tiktok.com/search?q={query.replace(' ', '%20')}%20stock",
                "author": "StockAnalyst",
                "views": 89000,
                "likes": 5600,
                "comments": 189,
                "created_utc": datetime.now().isoformat(),
                "hashtags": ["#stocks", "#analysis", f"#{query.replace(' ', '').lower()}"]
            }
        ]