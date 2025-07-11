"""
SecureAsk GraphRAG Engine
Wrapper around Microsoft GraphRAG for financial intelligence queries
"""

import asyncio
import logging
import time
import uuid
import re
from datetime import datetime
from typing import List, Optional, Dict, Any

from core.models import (
    QueryRequest, QueryResponse, QueryStatus, QueryResult, Citation, 
    ProcessingContext, SourceType, ExternalAPIResponse
)
from connectors.sec_connector import SECConnector
from connectors.reddit_connector import RedditConnector
from connectors.tiktok_connector import TikTokConnector

logger = logging.getLogger(__name__)

class GraphRAGEngine:
    """Main GraphRAG processing engine for SecureAsk"""
    
    def __init__(self, neo4j_client, redis_client):
        self.neo4j = neo4j_client
        self.redis = redis_client
        self.active_queries: Dict[str, ProcessingContext] = {}
        
    async def initialize(self):
        """Initialize the GraphRAG engine"""
        logger.info("Initializing GraphRAG engine...")
        
        # TODO: Initialize GraphRAG components
        # - Load GraphRAG configuration
        # - Set up embedding models
        # - Initialize search engines
        
        logger.info("✅ GraphRAG engine initialized")
    
    async def process_query(
        self,
        question: str,
        max_hops: int = 2,
        sources: List[SourceType] = None,
        user_id: str = "demo"
    ) -> QueryResponse:
        """
        Process a query using GraphRAG
        
        This is the main entry point that:
        1. Creates initial graph context
        2. Fetches external data if needed
        3. Runs GraphRAG reasoning
        4. Returns structured results
        """
        start_time = time.time()
        query_id = str(uuid.uuid4())
        sources = sources or [SourceType.SEC, SourceType.REDDIT, SourceType.TIKTOK]
        
        context = ProcessingContext(
            user_id=user_id,
            query_id=query_id,
            question=question,
            max_hops=max_hops,
            sources=sources
        )
        
        self.active_queries[query_id] = context
        
        try:
            logger.info(f"Processing query {query_id}: {question[:100]}...")
            
            # Step 1: Initial graph traversal to find relevant nodes
            relevant_nodes = await self._find_relevant_nodes(question, max_hops)
            logger.info(f"Found {len(relevant_nodes)} relevant nodes")
            
            # Step 2: Fetch external data if needed
            external_data = await self._fetch_external_data(question, sources)
            logger.info(f"Fetched data from {len(external_data)} sources")
            
            # Step 3: Update graph with new information
            if external_data:
                await self._update_graph_with_external_data(external_data)
            
            # Step 4: Run GraphRAG reasoning (mock for now)
            result = await self._run_graphrag_reasoning(
                question, relevant_nodes, external_data
            )
            
            processing_time = int((time.time() - start_time) * 1000)
            
            response = QueryResponse(
                query_id=query_id,
                question=question,
                status=QueryStatus.COMPLETED,
                result=QueryResult(
                    answer=result["answer"],
                    citations=result["citations"],
                    graph_path=result["graph_path"],
                    processing_time=processing_time
                ),
                created_at=context.start_time,
                completed_at=datetime.utcnow()
            )
            
            # Cache the result
            await self.redis.set(
                f"query_result:{query_id}",
                response.model_dump_json(),
                ex=3600  # 1 hour TTL
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Query processing failed: {e}")
            return QueryResponse(
                query_id=query_id,
                question=question,
                status=QueryStatus.FAILED,
                result=None,
                created_at=context.start_time,
                completed_at=datetime.utcnow()
            )
        finally:
            # Cleanup
            self.active_queries.pop(query_id, None)
    
    async def _find_relevant_nodes(self, question: str, max_hops: int) -> List[Dict]:
        """Find relevant nodes in the graph using semantic search"""
        # For now, return mock data - in real implementation:
        # 1. Use text embedding to find semantically similar nodes
        # 2. Perform graph traversal to expand context
        # 3. Score nodes by relevance
        
        logger.info(f"Finding relevant nodes for: {question}")
        
        # Mock relevant nodes
        return [
            {
                "id": "company_AAPL",
                "type": "Company",
                "name": "Apple Inc.",
                "relevance": 0.95
            },
            {
                "id": "risk_climate_001",
                "type": "Risk",
                "name": "Climate Change Risk",
                "relevance": 0.87
            }
        ]
    
    async def _fetch_external_data(
        self, question: str, sources: List[SourceType]
    ) -> List[ExternalAPIResponse]:
        """Fetch relevant data from external sources using real APIs"""
        external_data = []
        
        # Extract company ticker from question for SEC queries
        company_ticker = self._extract_company_ticker(question)
        
        # Extract search terms for social media
        search_terms = self._extract_search_terms(question)
        
        logger.info(f"Extracted ticker: {company_ticker}, search terms: {search_terms}")
        
        # Fetch data from each source concurrently
        tasks = []
        for source in sources:
            if source == SourceType.SEC and company_ticker:
                tasks.append(self._fetch_sec_data(company_ticker))
            elif source == SourceType.REDDIT:
                tasks.append(self._fetch_reddit_data(search_terms))
            elif source == SourceType.TIKTOK:
                tasks.append(self._fetch_tiktok_data(search_terms))
        
        # Execute all fetches concurrently
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            external_data = [r for r in results if isinstance(r, ExternalAPIResponse)]
        
        logger.info(f"Fetched data from {len(external_data)} sources successfully")
        return external_data
    
    def _extract_company_ticker(self, question: str) -> Optional[str]:
        """Extract company ticker from question"""
        # Common company tickers and names
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
    
    def _extract_search_terms(self, question: str) -> str:
        """Extract relevant search terms from question"""
        # Remove common question words and keep relevant terms
        stop_words = {'what', 'are', 'the', 'is', 'how', 'does', 'do', 'can', 'will', 'would', 'should'}
        words = re.findall(r'\b\w+\b', question.lower())
        relevant_words = [w for w in words if w not in stop_words and len(w) > 2]
        return ' '.join(relevant_words[:5])  # Limit to 5 most relevant terms
    
    async def _fetch_sec_data(self, ticker: str) -> ExternalAPIResponse:
        """Fetch SEC filing data"""
        try:
            filings = await SECConnector.search_filings(ticker, "10-K")
            return ExternalAPIResponse(
                source=SourceType.SEC,
                data=filings,
                metadata={"ticker": ticker, "query_time": datetime.utcnow().isoformat()},
                cached=False
            )
        except Exception as e:
            logger.error(f"SEC API error: {e}")
            return ExternalAPIResponse(
                source=SourceType.SEC,
                data=[],
                metadata={"error": str(e)},
                cached=False
            )
    
    async def _fetch_reddit_data(self, search_terms: str) -> ExternalAPIResponse:
        """Fetch Reddit discussion data"""
        try:
            posts = await RedditConnector.search_posts(search_terms)
            return ExternalAPIResponse(
                source=SourceType.REDDIT,
                data=posts,
                metadata={"search_terms": search_terms, "query_time": datetime.utcnow().isoformat()},
                cached=False
            )
        except Exception as e:
            logger.error(f"Reddit API error: {e}")
            return ExternalAPIResponse(
                source=SourceType.REDDIT,
                data=[],
                metadata={"error": str(e)},
                cached=False
            )
    
    async def _fetch_tiktok_data(self, search_terms: str) -> ExternalAPIResponse:
        """Fetch TikTok content data"""
        try:
            content = await TikTokConnector.search_content(search_terms)
            return ExternalAPIResponse(
                source=SourceType.TIKTOK,
                data=content,
                metadata={"search_terms": search_terms, "query_time": datetime.utcnow().isoformat()},
                cached=False
            )
        except Exception as e:
            logger.error(f"TikTok API error: {e}")
            return ExternalAPIResponse(
                source=SourceType.TIKTOK,
                data=[],
                metadata={"error": str(e)},
                cached=False
            )
    
    async def _update_graph_with_external_data(
        self, external_data: List[ExternalAPIResponse]
    ):
        """Update the knowledge graph with new external data"""
        # In real implementation:
        # 1. Extract entities and relationships from external data
        # 2. Create new graph triples
        # 3. Store in Neo4j
        # 4. Update embeddings
        
        logger.info("Updating graph with external data")
        pass
    
    async def _run_graphrag_reasoning(
        self, question: str, relevant_nodes: List[Dict], external_data: List[ExternalAPIResponse]
    ) -> Dict[str, Any]:
        """Run GraphRAG reasoning to generate answer using real data"""
        logger.info("Running GraphRAG reasoning with real data")
        
        # Collect all data sources for analysis
        sec_data = []
        reddit_data = []
        tiktok_data = []
        citations = []
        
        for response in external_data:
            if response.source == SourceType.SEC:
                sec_data.extend(response.data)
            elif response.source == SourceType.REDDIT:
                reddit_data.extend(response.data)
            elif response.source == SourceType.TIKTOK:
                tiktok_data.extend(response.data)
        
        # Build answer based on available data
        answer_parts = []
        
        # Start with SEC official information
        if sec_data:
            sec_content = self._summarize_sec_data(sec_data)
            answer_parts.append(f"According to recent SEC filings, {sec_content}")
            
            # Add SEC citations
            for filing in sec_data[:2]:  # Limit to 2 main citations
                citations.append(Citation(
                    node_id=f"sec_{filing.get('cik', 'unknown')}",
                    source=SourceType.SEC,
                    url=filing.get('url', ''),
                    snippet=filing.get('content', '')[:200] + "...",
                    confidence=0.95
                ).model_dump())
        
        # Add Reddit sentiment and discussion
        if reddit_data:
            reddit_summary = self._summarize_reddit_data(reddit_data)
            answer_parts.append(f"Social media discussions on Reddit reveal {reddit_summary}")
            
            # Add Reddit citations
            for post in reddit_data[:2]:  # Limit to 2 main citations
                citations.append(Citation(
                    node_id=f"reddit_{hash(post.get('url', ''))}",
                    source=SourceType.REDDIT,
                    url=post.get('url', ''),
                    snippet=post.get('content', '')[:200] + "...",
                    confidence=0.78
                ).model_dump())
        
        # Add TikTok social sentiment
        if tiktok_data:
            tiktok_summary = self._summarize_tiktok_data(tiktok_data)
            answer_parts.append(f"TikTok content analysis shows {tiktok_summary}")
            
            # Add TikTok citations
            for content in tiktok_data[:1]:  # Limit to 1 citation
                citations.append(Citation(
                    node_id=f"tiktok_{hash(content.get('url', ''))}",
                    source=SourceType.TIKTOK,
                    url=content.get('url', ''),
                    snippet=content.get('content', '')[:200] + "...",
                    confidence=0.65
                ).model_dump())
        
        # Combine answer parts
        if answer_parts:
            answer = " ".join(answer_parts)
        else:
            answer = "I wasn't able to find sufficient information to provide a comprehensive answer to your question. This could be due to API limitations or the specific nature of your query."
        
        # Build graph path showing reasoning flow
        graph_path = ["query_analysis"]
        if sec_data:
            graph_path.append("sec_filings")
        if reddit_data:
            graph_path.append("reddit_discussions")
        if tiktok_data:
            graph_path.append("tiktok_content")
        graph_path.append("synthesis")
        
        return {
            "answer": answer,
            "citations": citations,
            "graph_path": graph_path
        }
    
    def _summarize_sec_data(self, sec_data: List[Dict]) -> str:
        """Summarize SEC filing data"""
        if not sec_data:
            return "no recent SEC filings were available for analysis."
        
        # Extract key themes from SEC data
        key_themes = []
        for filing in sec_data:
            content = filing.get('content', '').lower()
            if 'risk' in content or 'climate' in content:
                key_themes.append("regulatory and climate risks")
            if 'supply' in content or 'chain' in content:
                key_themes.append("supply chain considerations")
            if 'esg' in content or 'environment' in content:
                key_themes.append("ESG factors")
        
        return f"the company has disclosed {', '.join(set(key_themes)) if key_themes else 'various business factors'} in their regulatory filings."
    
    def _summarize_reddit_data(self, reddit_data: List[Dict]) -> str:
        """Summarize Reddit discussion data"""
        if not reddit_data:
            return "limited social media discussion."
        
        # Analyze sentiment and themes
        total_score = sum(post.get('score', 0) for post in reddit_data)
        avg_score = total_score / len(reddit_data) if reddit_data else 0
        
        sentiment = "mixed sentiment" if avg_score < 50 else "generally positive sentiment" if avg_score > 100 else "moderate engagement"
        
        return f"{sentiment} among retail investors, with discussions focusing on investment strategies and market analysis."
    
    def _summarize_tiktok_data(self, tiktok_data: List[Dict]) -> str:
        """Summarize TikTok content data"""
        if not tiktok_data:
            return "limited social media content."
        
        # Analyze engagement metrics
        total_views = sum(content.get('views', 0) for content in tiktok_data)
        avg_views = total_views / len(tiktok_data) if tiktok_data else 0
        
        engagement = "high engagement" if avg_views > 50000 else "moderate engagement" if avg_views > 10000 else "limited engagement"
        
        return f"{engagement} with financial content creators discussing investment perspectives and market trends."
    
    async def get_query_result(self, query_id: str, user_id: str) -> Optional[QueryResponse]:
        """Retrieve cached query result"""
        try:
            cached_result = await self.redis.get(f"query_result:{query_id}")
            if cached_result:
                return QueryResponse.model_validate_json(cached_result)
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve query result: {e}")
            return None
    
    async def ingest_document(
        self, source: SourceType, url: str, content: str, metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Ingest a document into the knowledge graph"""
        # Mock document ingestion
        # In real implementation:
        # 1. Extract entities and relationships from document
        # 2. Create graph triples
        # 3. Store in Neo4j
        # 4. Generate embeddings
        
        logger.info(f"Ingesting document from {source}: {url}")
        
        return {
            "document_id": str(uuid.uuid4()),
            "triples_extracted": 42,
            "nodes_created": 15,
            "edges_created": 27
        }