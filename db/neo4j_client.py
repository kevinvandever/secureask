"""
Neo4j client for SecureAsk knowledge graph operations
"""

import asyncio
import logging
import os
from typing import List, Dict, Any, Optional
from neo4j import AsyncGraphDatabase, AsyncSession
from contextlib import asynccontextmanager

from core.models import GraphNode, GraphEdge, GraphPath

logger = logging.getLogger(__name__)

class Neo4jClient:
    """Async Neo4j client for graph operations"""
    
    def __init__(self):
        self.driver = None
        self.uri = os.getenv("NEO4J_URI", "neo4j+s://5abb8f53.databases.neo4j.io")
        self.user = os.getenv("NEO4J_USER", "neo4j") 
        self.password = os.getenv("NEO4J_PASSWORD", "7A2n-4htBFcaRHC4J-GCoc3ir6w6fykl4iZRX8dhaM0")
    
    async def connect(self):
        """Connect to Neo4j"""
        try:
            self.driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
                max_connection_pool_size=50
            )
            
            # Test connection
            async with self.driver.session() as session:
                result = await session.run("RETURN 'Connected' as status")
                record = await result.single()
                logger.info(f"✅ Neo4j connected: {record['status']}")
                
        except Exception as e:
            logger.error(f"❌ Failed to connect to Neo4j: {e}")
            raise
    
    async def close(self):
        """Close Neo4j connection"""
        if self.driver:
            await self.driver.close()
            logger.info("Neo4j connection closed")
    
    @asynccontextmanager
    async def session(self) -> AsyncSession:
        """Get an async session"""
        async with self.driver.session() as session:
            yield session
    
    async def search_nodes(
        self,
        query_text: str,
        node_type: Optional[str] = None,
        limit: int = 10
    ) -> List[GraphNode]:
        """Search nodes by text"""
        try:
            async with self.session() as session:
                if node_type:
                    cypher = f"""
                    MATCH (n:{node_type})
                    WHERE n.name CONTAINS $query OR n.description CONTAINS $query
                    RETURN n
                    ORDER BY n.name
                    LIMIT $limit
                    """
                else:
                    cypher = """
                    MATCH (n)
                    WHERE n.name CONTAINS $query OR n.description CONTAINS $query
                    RETURN n
                    ORDER BY n.name
                    LIMIT $limit
                    """
                
                result = await session.run(cypher, query=query_text, limit=limit)
                nodes = []
                
                async for record in result:
                    node = record['n']
                    nodes.append(GraphNode(
                        id=node.get('id', str(node.id)),
                        type=list(node.labels)[0] if node.labels else 'Node',
                        name=node.get('name', ''),
                        properties=dict(node),
                        source=node.get('source', {})
                    ))
                
                return nodes
                
        except Exception as e:
            logger.error(f"Node search failed: {e}")
            return []
    
    async def find_related_nodes(
        self,
        start_node_id: str,
        max_hops: int = 2,
        relationship_types: Optional[List[str]] = None
    ) -> List[GraphPath]:
        """Find nodes related to start node within max_hops"""
        try:
            async with self.session() as session:
                # Build relationship pattern
                rel_pattern = ""
                if relationship_types:
                    rel_types = "|".join(f":{rt}" for rt in relationship_types)
                    rel_pattern = f"[{rel_types}]"
                else:
                    rel_pattern = ""
                
                cypher = f"""
                MATCH path = (start {{id: $start_id}})-[{rel_pattern}*1..{max_hops}]-(end)
                WHERE start <> end
                RETURN path
                ORDER BY length(path)
                LIMIT 100
                """
                
                result = await session.run(cypher, start_id=start_node_id)
                paths = []
                
                async for record in result:
                    path = record['path']
                    paths.append(self._parse_path(path))
                
                return paths
                
        except Exception as e:
            logger.error(f"Related nodes search failed: {e}")
            return []
    
    async def create_triple(
        self,
        subject_id: str,
        subject_props: Dict[str, Any],
        predicate: str,
        object_id: str,
        object_props: Dict[str, Any],
        edge_props: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a triple (subject-predicate-object) in the graph"""
        try:
            async with self.session() as session:
                cypher = """
                MERGE (s {id: $subject_id})
                SET s += $subject_props
                MERGE (o {id: $object_id})
                SET o += $object_props
                MERGE (s)-[r:RELATES {type: $predicate}]->(o)
                SET r += $edge_props
                RETURN elementId(r) as edge_id
                """
                
                result = await session.run(
                    cypher,
                    subject_id=subject_id,
                    subject_props=subject_props,
                    object_id=object_id,
                    object_props=object_props,
                    predicate=predicate,
                    edge_props=edge_props or {}
                )
                
                record = await result.single()
                return record['edge_id']
                
        except Exception as e:
            logger.error(f"Triple creation failed: {e}")
            raise
    
    async def get_node_count(self) -> int:
        """Get total node count"""
        try:
            async with self.session() as session:
                result = await session.run("MATCH (n) RETURN count(n) as count")
                record = await result.single()
                return record['count']
        except Exception as e:
            logger.error(f"Node count failed: {e}")
            return 0
    
    def _parse_path(self, neo4j_path) -> GraphPath:
        """Convert Neo4j path to GraphPath model"""
        nodes = []
        edges = []
        
        for node in neo4j_path.nodes:
            nodes.append(GraphNode(
                id=node.get('id', str(node.id)),
                type=list(node.labels)[0] if node.labels else 'Node',
                name=node.get('name', ''),
                properties=dict(node),
                source=node.get('source', {})
            ))
        
        for rel in neo4j_path.relationships:
            edges.append(GraphEdge(
                id=str(rel.id),
                from_node_id=str(rel.start_node.id),
                to_node_id=str(rel.end_node.id),
                relationship_type=rel.type,
                properties=dict(rel),
                weight=rel.get('weight', 1.0)
            ))
        
        return GraphPath(
            nodes=nodes,
            edges=edges,
            length=len(neo4j_path)
        )