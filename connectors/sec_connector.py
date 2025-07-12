"""
SEC EDGAR API connector for SecureAsk
"""

import asyncio
import aiohttp
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class SECConnector:
    """Connector for SEC EDGAR API"""
    
    BASE_URL = "https://data.sec.gov"
    HEADERS = {
        "User-Agent": "SecureAsk/1.0 (hackathon demo)",
        "Accept": "application/json"
    }
    
    @classmethod
    async def search_filings(cls, company_ticker: str, filing_type: str = "10-K") -> List[Dict[str, Any]]:
        """Search for SEC filings - returns demo data for hackathon"""
        try:
            logger.info(f"Fetching SEC filings for {company_ticker}")
            
            # For demo, return realistic mock data
            if company_ticker.upper() == "AAPL":
                return [{
                    "company": "AAPL",
                    "filing_type": "10-K",
                    "url": "https://www.sec.gov/Archives/edgar/data/320193/000032019323000106/aapl-20230930.htm",
                    "content": """Apple Inc. faces several ESG and climate-related risks that could materially affect our business:
                    
                    Climate Change Risks: We face both physical and transition risks related to climate change. Physical risks include 
                    disruption to our supply chain from extreme weather events, particularly in Asia where many of our suppliers operate. 
                    Flooding in Thailand and typhoons in China have previously caused production delays.
                    
                    Environmental Compliance: Increasing environmental regulations globally may require significant capital expenditures 
                    to modify our products and manufacturing processes. The EU's circular economy requirements and right-to-repair 
                    legislation could impact our product design and business model.
                    
                    Supply Chain ESG: We rely on suppliers who may not meet evolving ESG standards. Issues with conflict minerals, 
                    labor practices, or environmental violations in our supply chain could result in reputational damage, regulatory 
                    penalties, and operational disruptions.
                    
                    Carbon Neutrality Commitments: We have committed to becoming carbon neutral across our entire supply chain by 2030. 
                    Failure to meet these targets could result in reputational harm and potential litigation from stakeholders.""",
                    "date": "2023-11-03",
                    "cik": "0000320193",
                    "accession": "0000320193-23-000106"
                }]
            elif company_ticker.upper() == "TSLA":
                return [{
                    "company": "TSLA",
                    "filing_type": "10-K",
                    "url": "https://www.sec.gov/Archives/edgar/data/1318605/000131860524000024/tsla-20231231.htm",
                    "content": """Tesla faces unique ESG risks as an electric vehicle manufacturer:
                    
                    Battery Supply Chain: Critical mineral sourcing for batteries poses significant ESG risks including environmental 
                    damage from mining, human rights concerns in cobalt sourcing, and geopolitical risks in lithium supply.
                    
                    Manufacturing Environmental Impact: Despite producing zero-emission vehicles, our manufacturing processes have 
                    substantial environmental impacts including water usage, chemical handling, and energy consumption.""",
                    "date": "2024-01-29",
                    "cik": "0001318605",
                    "accession": "0001318605-24-000024"
                }]
            else:
                return [{
                    "company": company_ticker,
                    "filing_type": filing_type,
                    "url": f"https://www.sec.gov/Archives/edgar/data/example/{company_ticker.lower()}-10k.htm",
                    "content": f"{company_ticker} faces various ESG risks including climate change impacts, supply chain sustainability, "
                             f"regulatory compliance, and stakeholder expectations around environmental and social responsibility.",
                    "date": "2024-03-15",
                    "cik": "0000000000",
                    "accession": "0000000000-24-000001"
                }]
            
        except Exception as e:
            logger.error(f"SEC API error: {e}")
            return []
    
    @classmethod
    async def _get_company_cik(cls, session: aiohttp.ClientSession, ticker: str) -> str:
        """Get company CIK from ticker - hardcoded for demo"""
        # Hardcoded CIKs for major companies
        ticker_to_cik = {
            'AAPL': '0000320193',  # Apple
            'MSFT': '0000789019',  # Microsoft
            'GOOGL': '0001652044', # Alphabet
            'AMZN': '0001018724',  # Amazon
            'TSLA': '0001318605',  # Tesla
            'META': '0001326801',  # Meta
            'NVDA': '0001045810',  # Nvidia
        }
        return ticker_to_cik.get(ticker.upper(), "")
    
    @classmethod
    async def _get_filing_content(cls, session: aiohttp.ClientSession, cik: str, accession: str) -> str:
        """Extract text content from SEC filing"""
        try:
            # Try to get the main filing document
            filing_url = f"{cls.BASE_URL}/Archives/edgar/data/{cik}/{accession.replace('-', '')}/0001.txt"
            
            async with session.get(filing_url) as response:
                if response.status == 200:
                    content = await response.text()
                    # Extract meaningful content (skip headers, focus on business sections)
                    lines = content.split('\n')
                    meaningful_content = []
                    in_content = False
                    
                    for line in lines:
                        if any(keyword in line.upper() for keyword in ['BUSINESS', 'RISK FACTORS', 'ITEM 1A', 'ITEM 7']):
                            in_content = True
                        elif line.startswith('</') or line.startswith('<SEC-'):
                            in_content = False
                        
                        if in_content and line.strip() and not line.startswith('<'):
                            meaningful_content.append(line.strip())
                    
                    return ' '.join(meaningful_content)
                else:
                    return f"SEC filing content for CIK {cik}, accession {accession}"
        except Exception as e:
            logger.error(f"Error getting filing content: {e}")
            return f"SEC filing content for CIK {cik}, accession {accession}"