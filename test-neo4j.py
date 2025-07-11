#!/usr/bin/env python3
"""
Quick Neo4j Aura connection test for SecureAsk
"""

from neo4j import GraphDatabase
import sys

# Replace with your actual credentials from Aura
NEO4J_URI="neo4j+s://5abb8f53.databases.neo4j.io"
NEO4J_USER="neo4j"
NEO4J_PASSWORD="7A2n-4htBFcaRHC4J-GCoc3ir6w6fykl4iZRX8dhaM0"

def test_connection():
    """Test Neo4j Aura connection and create sample data"""
    
    try:
        # Create driver
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        
        # Test connection
        with driver.session() as session:
            result = session.run("RETURN 'Connection successful!' as message")
            record = result.single()
            print(f"✅ {record['message']}")
            
            # Create sample SecureAsk graph data
            print("Creating sample graph for SecureAsk...")
            
            # Create sample nodes
            session.run("""
                CREATE (apple:Company {
                    id: 'company_AAPL',
                    name: 'Apple Inc.',
                    ticker: 'AAPL',
                    sector: 'Technology'
                })
                CREATE (climate_risk:Risk {
                    id: 'risk_climate_001',
                    type: 'ESG',
                    category: 'Climate',
                    description: 'Supply chain climate exposure',
                    severity: 'HIGH'
                })
                CREATE (sec_filing:Document {
                    id: 'doc_sec_10k_2024',
                    source: 'sec',
                    type: '10-K',
                    url: 'https://sec.gov/example'
                })
                CREATE (apple)-[:DISCUSSES {confidence: 0.95}]->(climate_risk)
                CREATE (climate_risk)-[:MENTIONED_IN]->(sec_filing)
            """)
            
            # Test graph traversal (this is what GraphRAG will do)
            result = session.run("""
                MATCH path = (c:Company {ticker: 'AAPL'})-[*1..2]-(r:Risk)
                RETURN c.name as company, r.description as risk, length(path) as hops
            """)
            
            print("\n🔍 Sample GraphRAG query results:")
            for record in result:
                print(f"   Company: {record['company']}")
                print(f"   Risk: {record['risk']}")
                print(f"   Hops: {record['hops']}")
                
            # Test performance
            import time
            start = time.time()
            result = session.run("""
                MATCH (n) RETURN count(n) as node_count
            """)
            end = time.time()
            
            count = result.single()['node_count']
            print(f"\n⚡ Performance: {count} nodes queried in {(end-start)*1000:.1f}ms")
            
            print("\n🎉 Neo4j Aura is ready for SecureAsk!")
            
        driver.close()
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\n🔧 Troubleshooting:")
        print("1. Check your Neo4j Aura credentials")
        print("2. Ensure instance is running (green status)")
        print("3. Verify URI format: neo4j+s://xxxxx.databases.neo4j.io")
        return False

if __name__ == "__main__":
    if NEO4J_URI == "neo4j+s://YOUR_INSTANCE_ID.databases.neo4j.io":
        print("❌ Please update the credentials in this file first!")
        print("   1. Replace NEO4J_URI with your instance URI")
        print("   2. Replace NEO4J_PASSWORD with generated password")
        sys.exit(1)
    
    success = test_connection()
    sys.exit(0 if success else 1)