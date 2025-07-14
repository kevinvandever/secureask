"""
SecureAsk GraphRAG Engine
Wrapper around Microsoft GraphRAG for financial intelligence queries
"""

import asyncio
import logging
import time
import uuid
import re
import hashlib
from datetime import datetime
from typing import List, Optional, Dict, Any
import structlog

from core.models import (
    QueryRequest, QueryResponse, QueryStatus, QueryResult, Citation, 
    ProcessingContext, SourceType, ExternalAPIResponse
)
from connectors.sec_connector import SECConnector
from connectors.reddit_connector import RedditConnector
from connectors.tiktok_connector import TikTokConnector

logger = structlog.get_logger(__name__)

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
        user_id: str = "demo",
        include_answer: bool = True
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
            logger.info("Processing new query", query_id=query_id, question_preview=question[:100])
            
            # Step 1: Initial graph traversal to find relevant nodes
            relevant_nodes = await self._find_relevant_nodes(question, max_hops)
            logger.info("Found relevant nodes", node_count=len(relevant_nodes))
            
            # Step 2: Fetch external data if needed
            external_data = await self._fetch_external_data(question, sources)
            logger.info("External data fetched", source_count=len(external_data))
            
            # Step 3: Update graph with new information
            if external_data:
                await self._update_graph_with_external_data(external_data)
            
            # Step 4: Run GraphRAG reasoning
            result = await self._run_graphrag_reasoning(
                question, relevant_nodes, external_data, include_answer
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
            
            # Cache the result using enhanced caching (only if Redis is available)
            if self.redis:
                try:
                    query_hash = hashlib.md5(f"{question}:{sorted(sources)}:{max_hops}".encode()).hexdigest()
                    await self.redis.cache_query_result(query_hash, response.model_dump(), ttl=1800)
                except Exception as cache_error:
                    logger.warning("Failed to cache query result", error=str(cache_error))
            
            return response
            
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            logger.error("Query processing failed", query_id=query_id, processing_time=processing_time, error=str(e), exc_info=True)
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
        
        logger.info("Finding relevant nodes", question_preview=question[:50])
        
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
        
        logger.info("Extracted query components", ticker=company_ticker, search_terms=search_terms)
        logger.info("Sources requested", sources=sources, source_types=[type(s).__name__ for s in sources])
        
        # Fetch data from each source concurrently
        tasks = []
        for source in sources:
            logger.info("Processing source", source=source, source_type=type(source).__name__)
            if source == SourceType.SEC and company_ticker:
                logger.info("Adding SEC task", ticker=company_ticker)
                tasks.append(self._fetch_sec_data(company_ticker))
            elif source == SourceType.REDDIT:
                logger.info("Adding Reddit task", search_terms=search_terms)
                tasks.append(self._fetch_reddit_data(search_terms))
            elif source == SourceType.TIKTOK:
                logger.info("Adding TikTok task", search_terms=search_terms)
                tasks.append(self._fetch_tiktok_data(search_terms))
            else:
                logger.warning("Unmatched source", source=source, source_value=str(source))
        
        # Execute all fetches concurrently
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            external_data = [r for r in results if isinstance(r, ExternalAPIResponse)]
        
        logger.info("External data collection complete", successful_sources=len(external_data))
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
        """Fetch SEC filing data with caching"""
        cache_key = f"sec_filings_{ticker}_10K"
        
        try:
            # Check cache first (only if Redis is available)
            cached_data = None
            if self.redis:
                try:
                    cached_data = await self.redis.get_cached_external_api_response("sec", cache_key)
                except Exception as cache_error:
                    logger.warning("Redis cache unavailable", error=str(cache_error))
            
            if cached_data:
                logger.info("SEC data served from cache", ticker=ticker)
                return ExternalAPIResponse(
                    source=SourceType.SEC,
                    data=cached_data,
                    metadata={"ticker": ticker, "query_time": datetime.utcnow().isoformat()},
                    cached=True
                )
            
            # Fetch fresh data
            start_time = time.time()
            filings = await SECConnector.search_filings(ticker, "10-K")
            response_time = round((time.time() - start_time) * 1000, 2)
            
            # Cache the result - only if Redis is available
            if self.redis:
                try:
                    await self.redis.cache_external_api_response("sec", cache_key, filings, ttl=3600)  # 1 hour TTL
                except Exception as cache_error:
                    logger.warning("Failed to cache SEC data", error=str(cache_error))
            
            logger.info("SEC data fetched and cached", ticker=ticker, response_time=response_time)
            
            return ExternalAPIResponse(
                source=SourceType.SEC,
                data=filings,
                metadata={"ticker": ticker, "query_time": datetime.utcnow().isoformat(), "response_time": response_time},
                cached=False
            )
        except Exception as e:
            logger.error("SEC API error", ticker=ticker, error=str(e), exc_info=True)
            return ExternalAPIResponse(
                source=SourceType.SEC,
                data=[],
                metadata={"error": str(e)},
                cached=False
            )
    
    async def _fetch_reddit_data(self, search_terms: str) -> ExternalAPIResponse:
        """Fetch Reddit discussion data with caching"""
        cache_key = f"reddit_posts_{hashlib.md5(search_terms.encode()).hexdigest()}"
        
        try:
            # Check cache first (only if Redis is available)
            cached_data = None
            if self.redis:
                try:
                    cached_data = await self.redis.get_cached_external_api_response("reddit", cache_key)
                except Exception as cache_error:
                    logger.warning("Redis cache unavailable", error=str(cache_error))
            
            if cached_data:
                logger.info("Reddit data served from cache", search_terms=search_terms)
                return ExternalAPIResponse(
                    source=SourceType.REDDIT,
                    data=cached_data,
                    metadata={"search_terms": search_terms, "query_time": datetime.utcnow().isoformat()},
                    cached=True
                )
            
            # Fetch fresh data
            start_time = time.time()
            posts = await RedditConnector.search_posts(search_terms)
            response_time = round((time.time() - start_time) * 1000, 2)
            
            # Cache the result (shorter TTL for social media) - only if Redis is available
            if self.redis:
                try:
                    await self.redis.cache_external_api_response("reddit", cache_key, posts, ttl=900)  # 15 minutes TTL
                except Exception as cache_error:
                    logger.warning("Failed to cache Reddit data", error=str(cache_error))
            
            logger.info("Reddit data fetched and cached", search_terms=search_terms, response_time=response_time)
            
            return ExternalAPIResponse(
                source=SourceType.REDDIT,
                data=posts,
                metadata={"search_terms": search_terms, "query_time": datetime.utcnow().isoformat(), "response_time": response_time},
                cached=False
            )
        except Exception as e:
            logger.error("Reddit API error", search_terms=search_terms, error=str(e), exc_info=True)
            return ExternalAPIResponse(
                source=SourceType.REDDIT,
                data=[],
                metadata={"error": str(e)},
                cached=False
            )
    
    async def _fetch_tiktok_data(self, search_terms: str) -> ExternalAPIResponse:
        """Fetch TikTok content data with caching"""
        cache_key = f"tiktok_content_{hashlib.md5(search_terms.encode()).hexdigest()}"
        
        try:
            # Check cache first (only if Redis is available)
            cached_data = None
            if self.redis:
                try:
                    cached_data = await self.redis.get_cached_external_api_response("tiktok", cache_key)
                except Exception as cache_error:
                    logger.warning("Redis cache unavailable", error=str(cache_error))
            
            if cached_data:
                logger.info("TikTok data served from cache", search_terms=search_terms)
                return ExternalAPIResponse(
                    source=SourceType.TIKTOK,
                    data=cached_data,
                    metadata={"search_terms": search_terms, "query_time": datetime.utcnow().isoformat()},
                    cached=True
                )
            
            # Fetch fresh data
            start_time = time.time()
            content = await TikTokConnector.search_content(search_terms)
            response_time = round((time.time() - start_time) * 1000, 2)
            
            # Cache the result (shorter TTL for social media) - only if Redis is available
            if self.redis:
                try:
                    await self.redis.cache_external_api_response("tiktok", cache_key, content, ttl=900)  # 15 minutes TTL
                except Exception as cache_error:
                    logger.warning("Failed to cache TikTok data", error=str(cache_error))
            
            logger.info("TikTok data fetched and cached", search_terms=search_terms, response_time=response_time)
            
            return ExternalAPIResponse(
                source=SourceType.TIKTOK,
                data=content,
                metadata={"search_terms": search_terms, "query_time": datetime.utcnow().isoformat(), "response_time": response_time},
                cached=False
            )
        except Exception as e:
            logger.error("TikTok API error", search_terms=search_terms, error=str(e), exc_info=True)
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
        
        logger.info("Updating graph with external data", source_count=len(external_data))
        pass
    
    async def _run_graphrag_reasoning(
        self, question: str, relevant_nodes: List[Dict], external_data: List[ExternalAPIResponse], include_answer: bool = True
    ) -> Dict[str, Any]:
        """Run GraphRAG reasoning to generate answer using real data"""
        logger.info("Running GraphRAG reasoning", node_count=len(relevant_nodes), external_sources=len(external_data))
        
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
        
        # Extract question-specific content
        answer_content = self._extract_relevant_content(question, sec_data, reddit_data, tiktok_data)
        
        # Build comprehensive citations with full content
        # SEC citations - increase to 5
        for filing in sec_data[:5]:
            content = filing.get('content', '')
            # Extract larger, more relevant snippet based on question keywords
            snippet = self._extract_relevant_snippet(content, question, 500)
            citations.append(Citation(
                node_id=f"sec_{filing.get('cik', 'unknown')}_{filing.get('accession', 'unknown')}",
                source=SourceType.SEC,
                url=filing.get('url', ''),
                snippet=snippet,
                confidence=0.95
            ).model_dump())
        
        # Reddit citations - increase to 5
        for post in reddit_data[:5]:
            content = post.get('content', '')
            snippet = self._extract_relevant_snippet(content, question, 400)
            citations.append(Citation(
                node_id=f"reddit_{abs(hash(post.get('url', '')))}",
                source=SourceType.REDDIT,
                url=post.get('url', ''),
                snippet=snippet,
                confidence=0.78
            ).model_dump())
        
        # TikTok citations - increase to 3
        for content in tiktok_data[:3]:
            text = content.get('content', '')
            snippet = self._extract_relevant_snippet(text, question, 300)
            citations.append(Citation(
                node_id=f"tiktok_{abs(hash(content.get('url', '')))}",
                source=SourceType.TIKTOK,
                url=content.get('url', ''),
                snippet=snippet,
                confidence=0.65
            ).model_dump())
        
        # Build graph path showing reasoning flow
        graph_path = ["query_analysis"]
        if sec_data:
            graph_path.append("sec_filings")
        if reddit_data:
            graph_path.append("reddit_discussions")
        if tiktok_data:
            graph_path.append("tiktok_content")
        graph_path.append("synthesis")
        
        # Control answer generation based on parameter
        if include_answer:
            # Only generate answer if explicitly requested
            answer = answer_content if answer_content else "Based on the citations provided, please refer to the source documents for specific details."
        else:
            # Return None to let MindStudio handle synthesis
            answer = None
        
        return {
            "answer": answer,
            "citations": citations,
            "graph_path": graph_path,
            "raw_data": {
                "sec_count": len(sec_data),
                "reddit_count": len(reddit_data),
                "tiktok_count": len(tiktok_data)
            }
        }
    
    def _extract_relevant_content(self, question: str, sec_data: List[Dict], reddit_data: List[Dict], tiktok_data: List[Dict]) -> str:
        """Extract question-specific content from all sources"""
        # Return None to let MindStudio handle synthesis from raw citations
        # This prevents generic templated responses
        return None
    
    def _extract_relevant_snippet(self, content: str, question: str, max_length: int = 500) -> str:
        """Extract relevant snippet based on question keywords"""
        if not content:
            return "No content available"
        
        # Extract keywords from question
        keywords = []
        question_lower = question.lower()
        
        # Look for specific terms in the question
        important_terms = ['climate', 'risk', 'esg', 'disclosure', 'apple', 'tesla', 
                          'supply chain', 'regulatory', 'environmental', 'social', 
                          'governance', '10-k', '10k', '2024', '2023', 'carbon', 
                          'emissions', 'sustainability']
        
        for term in important_terms:
            if term in question_lower:
                keywords.append(term)
        
        # Find the most relevant section
        sentences = content.split('. ')
        relevant_sentences = []
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            # Score sentence based on keyword matches
            score = sum(1 for keyword in keywords if keyword in sentence_lower)
            if score > 0:
                relevant_sentences.append((score, sentence))
        
        # Sort by relevance and take top sentences
        relevant_sentences.sort(key=lambda x: x[0], reverse=True)
        
        # Build snippet from most relevant sentences
        snippet_parts = []
        current_length = 0
        
        for score, sentence in relevant_sentences:
            if current_length + len(sentence) <= max_length:
                snippet_parts.append(sentence)
                current_length += len(sentence)
            else:
                break
        
        if snippet_parts:
            snippet = '. '.join(snippet_parts)
            if len(snippet) > max_length:
                snippet = snippet[:max_length] + '...'
            return snippet
        
        # Fallback to beginning of content if no keywords match
        return content[:max_length] + '...' if len(content) > max_length else content
    
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
            if self.redis:
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
        
        logger.info("Ingesting document", source=source, url=url[:100] if url else None)
        
        return {
            "document_id": str(uuid.uuid4()),
            "triples_extracted": 42,
            "nodes_created": 15,
            "edges_created": 27
        }