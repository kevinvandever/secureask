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
        """Search for SEC filings by company ticker using real SEC EDGAR API"""
        try:
            logger.info(f"Fetching real SEC filings for {company_ticker}")
            
            async with aiohttp.ClientSession(headers=cls.HEADERS) as session:
                # First, get the CIK for the company
                cik = await cls._get_company_cik(session, company_ticker)
                if not cik:
                    logger.warning(f"Could not find CIK for {company_ticker}")
                    return []
                
                # Search for filings
                search_url = f"{cls.BASE_URL}/submissions/CIK{cik}.json"
                
                async with session.get(search_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        filings = []
                        
                        # Parse recent filings
                        recent_filings = data.get('filings', {}).get('recent', {})
                        forms = recent_filings.get('form', [])
                        dates = recent_filings.get('filingDate', [])
                        accessions = recent_filings.get('accessionNumber', [])
                        
                        for i, form in enumerate(forms[:5]):  # Get last 5 filings
                            if filing_type.upper() in form.upper():
                                # Get filing content
                                content = await cls._get_filing_content(session, cik, accessions[i])
                                
                                filings.append({
                                    "company": company_ticker,
                                    "filing_type": form,
                                    "url": f"https://www.sec.gov/Archives/edgar/data/{cik}/{accessions[i].replace('-', '')}/{form.lower()}.htm",
                                    "content": content[:2000] + "..." if len(content) > 2000 else content,  # Truncate for GraphRAG
                                    "date": dates[i],
                                    "cik": cik,
                                    "accession": accessions[i]
                                })
                        
                        logger.info(f"Found {len(filings)} {filing_type} filings for {company_ticker}")
                        return filings
                    else:
                        logger.error(f"SEC API error: {response.status}")
                        return []
            
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