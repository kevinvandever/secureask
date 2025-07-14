#!/usr/bin/env python3
"""Simple debug script to understand GraphRAG external data fetching"""

import asyncio
import logging
from core.models import SourceType

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_fetch_external_data():
    """Test the _fetch_external_data method directly"""
    print("=" * 60)
    print("🔍 Testing GraphRAG External Data Fetching")
    print("=" * 60)
    
    # Create a mock engine to test the method
    class MockGraphRAGEngine:
        def __init__(self):
            self.neo4j = None
            self.redis = None
            
        def _extract_company_ticker(self, question: str):
            """Extract company ticker from question"""
            # Same logic as in GraphRAG engine
            import re
            ticker_patterns = {
                r'\b(AAPL|Apple)\b': 'AAPL',
                r'\b(MSFT|Microsoft)\b': 'MSFT',
                r'\b(GOOGL|GOOG|Google|Alphabet)\b': 'GOOGL',
                r'\b(AMZN|Amazon)\b': 'AMZN',
                r'\b(TSLA|Tesla)\b': 'TSLA',
                r'\b(META|Facebook|Meta)\b': 'META',
                r'\b(NVDA|Nvidia)\b': 'NVDA',
                r'\b(NFLX|Netflix)\b': 'NFLX',
                r'\b(CRM|Salesforce)\b': 'CRM',
                r'\b(ORCL|Oracle)\b': 'ORCL'
            }
            
            for pattern, ticker in ticker_patterns.items():
                if re.search(pattern, question, re.IGNORECASE):
                    return ticker
            
            return None
        
        def _extract_search_terms(self, question: str):
            """Extract relevant search terms from question"""
            import re
            stop_words = {'what', 'are', 'the', 'is', 'how', 'does', 'do', 'can', 'will', 'would', 'should'}
            words = re.findall(r'\b\w+\b', question.lower())
            relevant_words = [w for w in words if w not in stop_words and len(w) > 2]
            return ' '.join(relevant_words[:5])
        
        async def _fetch_external_data(self, question: str, sources: list):
            """Replicate the GraphRAG engine's _fetch_external_data method"""
            from core.models import ExternalAPIResponse
            from connectors.sec_connector import SECConnector
            from connectors.reddit_connector import RedditConnector
            from connectors.tiktok_connector import TikTokConnector
            
            external_data = []
            
            # Extract company ticker from question for SEC queries
            company_ticker = self._extract_company_ticker(question)
            
            # Extract search terms for social media
            search_terms = self._extract_search_terms(question)
            
            logger.info(f"Extracted query components: ticker={company_ticker}, search_terms={search_terms}")
            
            # Fetch data from each source concurrently
            tasks = []
            for source in sources:
                print(f"🔄 Processing source: {source}")
                if source == SourceType.SEC and company_ticker:
                    print(f"  ✅ Adding SEC task for ticker: {company_ticker}")
                    tasks.append(self._fetch_sec_data(company_ticker))
                elif source == SourceType.REDDIT:
                    print(f"  ✅ Adding Reddit task for terms: {search_terms}")
                    tasks.append(self._fetch_reddit_data(search_terms))
                elif source == SourceType.TIKTOK:
                    print(f"  ✅ Adding TikTok task for terms: {search_terms}")
                    tasks.append(self._fetch_tiktok_data(search_terms))
                else:
                    print(f"  ❌ Skipping source: {source} (conditions not met)")
            
            print(f"📊 Total tasks to execute: {len(tasks)}")
            
            # Execute all fetches concurrently
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for i, result in enumerate(results):
                    if isinstance(result, ExternalAPIResponse):
                        print(f"  ✅ Task {i+1} succeeded: {result.source} with {len(result.data)} items")
                        external_data.append(result)
                    else:
                        print(f"  ❌ Task {i+1} failed: {result}")
            
            logger.info(f"External data collection complete: {len(external_data)} successful sources")
            return external_data
        
        async def _fetch_sec_data(self, ticker: str):
            """Fetch SEC data"""
            from core.models import ExternalAPIResponse
            from connectors.sec_connector import SECConnector
            from datetime import datetime
            
            print(f"  🔍 Fetching SEC data for {ticker}")
            try:
                filings = await SECConnector.search_filings(ticker, "10-K")
                print(f"  ✅ SEC returned {len(filings)} filings")
                return ExternalAPIResponse(
                    source=SourceType.SEC,
                    data=filings,
                    metadata={"ticker": ticker, "query_time": datetime.utcnow().isoformat()},
                    cached=False
                )
            except Exception as e:
                print(f"  ❌ SEC error: {e}")
                return ExternalAPIResponse(
                    source=SourceType.SEC,
                    data=[],
                    metadata={"error": str(e)},
                    cached=False
                )
        
        async def _fetch_reddit_data(self, search_terms: str):
            """Fetch Reddit data"""
            from core.models import ExternalAPIResponse
            from connectors.reddit_connector import RedditConnector
            from datetime import datetime
            
            print(f"  🔍 Fetching Reddit data for '{search_terms}'")
            try:
                posts = await RedditConnector.search_posts(search_terms)
                print(f"  ✅ Reddit returned {len(posts)} posts")
                return ExternalAPIResponse(
                    source=SourceType.REDDIT,
                    data=posts,
                    metadata={"search_terms": search_terms, "query_time": datetime.utcnow().isoformat()},
                    cached=False
                )
            except Exception as e:
                print(f"  ❌ Reddit error: {e}")
                return ExternalAPIResponse(
                    source=SourceType.REDDIT,
                    data=[],
                    metadata={"error": str(e)},
                    cached=False
                )
        
        async def _fetch_tiktok_data(self, search_terms: str):
            """Fetch TikTok data"""
            from core.models import ExternalAPIResponse
            from connectors.tiktok_connector import TikTokConnector
            from datetime import datetime
            
            print(f"  🔍 Fetching TikTok data for '{search_terms}'")
            try:
                content = await TikTokConnector.search_content(search_terms)
                print(f"  ✅ TikTok returned {len(content)} videos")
                return ExternalAPIResponse(
                    source=SourceType.TIKTOK,
                    data=content,
                    metadata={"search_terms": search_terms, "query_time": datetime.utcnow().isoformat()},
                    cached=False
                )
            except Exception as e:
                print(f"  ❌ TikTok error: {e}")
                return ExternalAPIResponse(
                    source=SourceType.TIKTOK,
                    data=[],
                    metadata={"error": str(e)},
                    cached=False
                )
    
    # Test the method
    engine = MockGraphRAGEngine()
    
    # Test question
    question = "What are Apple's ESG risks?"
    sources = [SourceType.SEC, SourceType.REDDIT, SourceType.TIKTOK]
    
    print(f"Question: {question}")
    print(f"Sources: {sources}")
    print()
    
    # Test _extract_company_ticker
    ticker = engine._extract_company_ticker(question)
    print(f"Extracted ticker: {ticker}")
    
    # Test _extract_search_terms
    search_terms = engine._extract_search_terms(question)
    print(f"Extracted search terms: {search_terms}")
    print()
    
    # Test _fetch_external_data
    print("🚀 Starting external data fetch...")
    external_data = await engine._fetch_external_data(question, sources)
    
    print(f"\n📊 Final results: {len(external_data)} responses")
    for i, response in enumerate(external_data):
        print(f"  Response {i+1}: {response.source} with {len(response.data)} items")

if __name__ == "__main__":
    asyncio.run(test_fetch_external_data())