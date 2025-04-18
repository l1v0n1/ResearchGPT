"""
Web scraping tools for the AI Research Agent.
"""
import time
import re
import json
import urllib.parse
from typing import Dict, List, Any, Optional, Union, Tuple

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, validator

from agent import config
from agent.logger import AgentLogger

logger = AgentLogger(__name__)

class WebPage(BaseModel):
    """Model for web page data."""
    url: str
    title: str
    content: str
    html: Optional[str] = None
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class WebScrapingTool:
    """
    A tool for scraping and extracting information from web pages.
    """
    
    def __init__(self):
        """Initialize the web scraping tool with defaults from config."""
        self.user_agent = config.USER_AGENT
        self.timeout = config.REQUEST_TIMEOUT
        self.allowed_domains = config.ALLOWED_DOMAINS
        
        # Rate limiting
        self.request_count = 0
        self.request_start_time = time.time()
        self.rate_limit = config.WEB_RATE_LIMIT
        
        logger.info("Initialized WebScrapingTool")
    
    def _check_rate_limit(self):
        """
        Check if the current request would exceed the rate limit.
        If necessary, sleep to stay within rate limits.
        """
        current_time = time.time()
        elapsed = current_time - self.request_start_time
        
        # Reset counter after 60 seconds
        if elapsed >= 60:
            self.request_count = 0
            self.request_start_time = current_time
            return
        
        # If we're at the rate limit, sleep until the minute is up
        if self.request_count >= self.rate_limit:
            sleep_time = 60 - elapsed
            logger.warning(f"Web request rate limit reached. Sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
            self.request_count = 0
            self.request_start_time = time.time()
    
    def _validate_url(self, url: str) -> bool:
        """
        Check if a URL is allowed based on domain restrictions.
        
        Args:
            url: The URL to validate
            
        Returns:
            True if the URL is allowed, False otherwise
        """
        try:
            parsed_url = urllib.parse.urlparse(url)
            domain = parsed_url.netloc
            
            # If no allowed domains are specified, allow all
            if not self.allowed_domains:
                return True
            
            # Check if domain or any parent domain is in allowed list
            for allowed_domain in self.allowed_domains:
                if domain == allowed_domain or domain.endswith(f".{allowed_domain}"):
                    return True
                    
            logger.warning(f"Domain not allowed: {domain}")
            return False
        except Exception as e:
            logger.error(f"Error validating URL {url}: {str(e)}")
            return False
    
    def fetch_page(self, url: str) -> Optional[WebPage]:
        """
        Fetch and parse a web page.
        
        Args:
            url: The URL to fetch
            
        Returns:
            WebPage object if successful, None otherwise
        """
        # Validate URL
        if not self._validate_url(url):
            return None
        
        # Check rate limit
        self._check_rate_limit()
        self.request_count += 1
        
        # Set up headers
        headers = {
            "User-Agent": self.user_agent
        }
        
        try:
            logger.info(f"Fetching web page: {url}")
            response = requests.get(url, headers=headers, timeout=self.timeout)
            
            # Check if the request was successful
            if response.status_code != 200:
                logger.error(f"Failed to fetch {url}: HTTP {response.status_code}")
                return None
            
            # Parse HTML content
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract title
            title_tag = soup.find("title")
            title = title_tag.text if title_tag else "No title"
            
            # Extract main content
            # Remove script and style tags
            for script in soup(["script", "style"]):
                script.extract()
            
            # Get text content
            text = soup.get_text(separator="\n")
            
            # Clean up text: remove multiple newlines and spaces
            text = re.sub(r"\n+", "\n", text)
            text = re.sub(r" +", " ", text)
            text = text.strip()
            
            # Create WebPage object
            page = WebPage(
                url=url,
                title=title,
                content=text,
                html=response.text,
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                metadata={
                    "status_code": response.status_code,
                    "content_type": response.headers.get("Content-Type"),
                    "content_length": len(response.text)
                }
            )
            
            logger.info(f"Successfully fetched {url}: {title} ({len(text)} chars)")
            return page
            
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error processing {url}: {str(e)}")
            return None
    
    def search_google(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """
        Perform a Google search and return a list of results.
        Note: This is a simplistic implementation and should be replaced with
        a proper Google Search API in production.
        
        Args:
            query: The search query
            num_results: Maximum number of results to return
            
        Returns:
            List of search result dictionaries with title, url, and snippet
        """
        logger.info(f"Performing Google search for: {query}")
        
        # This is where you'd typically use the Google Search API
        # For now, we'll just return a message about the limitation
        logger.warning("Google Search API not implemented")
        
        return [
            {
                "title": "Google Search API Required",
                "url": "https://developers.google.com/custom-search/v1/overview",
                "snippet": "This is a placeholder. In a production environment, integrate with Google Custom Search API or similar."
            }
        ]
    
    def extract_links(self, url: str) -> List[Dict[str, str]]:
        """
        Extract all links from a web page.
        
        Args:
            url: The URL to extract links from
            
        Returns:
            List of dictionaries with link text and URL
        """
        page = self.fetch_page(url)
        if not page:
            return []
        
        # Parse HTML content using BeautifulSoup
        soup = BeautifulSoup(page.html, "html.parser")
        
        # Extract all links
        links = []
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            text = a_tag.get_text().strip()
            
            # Skip empty links or javascript
            if not href or href.startswith("javascript:"):
                continue
                
            # Resolve relative URLs
            if not href.startswith(("http://", "https://")):
                base_url = urllib.parse.urljoin(url, "")
                href = urllib.parse.urljoin(base_url, href)
            
            links.append({
                "text": text,
                "url": href
            })
        
        logger.info(f"Extracted {len(links)} links from {url}")
        return links
    
    def extract_text_with_selector(self, url: str, selector: str) -> str:
        """
        Extract text from a specific part of a web page using CSS selectors.
        
        Args:
            url: The URL to extract from
            selector: CSS selector to target specific elements
            
        Returns:
            Extracted text
        """
        page = self.fetch_page(url)
        if not page:
            return ""
        
        try:
            # Parse HTML content using BeautifulSoup
            soup = BeautifulSoup(page.html, "html.parser")
            
            # Find elements matching the selector
            elements = soup.select(selector)
            
            if not elements:
                logger.warning(f"No elements found with selector '{selector}' on {url}")
                return ""
            
            # Extract text from matched elements
            texts = [elem.get_text().strip() for elem in elements]
            result = "\n".join(texts)
            
            logger.info(f"Extracted {len(texts)} elements with selector '{selector}' from {url}")
            return result
            
        except Exception as e:
            logger.error(f"Error extracting text with selector '{selector}' from {url}: {str(e)}")
            return "" 