"""
Web scraping tools for the AI Research Agent.
"""
import time
import re
import json
import urllib.parse
import hashlib
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup, NavigableString
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
    
    def __init__(self, cache_dir: Optional[str] = None, cache_expiry: int = 24):
        """
        Initialize the web scraping tool with defaults from config.
        
        Args:
            cache_dir: Directory to store cached responses. None disables caching.
            cache_expiry: Cache expiry time in hours
        """
        self.user_agent = config.USER_AGENT
        self.timeout = config.REQUEST_TIMEOUT
        self.allowed_domains = config.ALLOWED_DOMAINS
        
        # Rate limiting
        self.request_count = 0
        self.request_start_time = time.time()
        self.rate_limit = config.WEB_RATE_LIMIT
        
        # Cache configuration
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.cache_expiry = timedelta(hours=cache_expiry)
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Web cache enabled at {self.cache_dir} with expiry of {cache_expiry} hours")
        
        # Use rotating proxies if available
        self.proxies = getattr(config, 'PROXIES', [])
        self.current_proxy_index = 0
        
        logger.info("Initialized WebScrapingTool")
    
    def _get_next_proxy(self) -> Optional[Dict[str, str]]:
        """Get the next proxy from the rotation."""
        if not self.proxies:
            return None
            
        proxy = self.proxies[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
        return proxy
    
    def _get_cache_path(self, url_or_query: str, is_search: bool = False) -> Optional[Path]:
        """
        Generate a cache file path for a URL or search query.
        
        Args:
            url_or_query: URL or search query
            is_search: True if this is a search query, False if it's a URL
            
        Returns:
            Path to the cache file or None if caching is disabled
        """
        if not self.cache_dir:
            return None
            
        # Create a hash of the URL/query to use as filename
        prefix = "search_" if is_search else "page_"
        hashed = hashlib.md5(url_or_query.encode('utf-8')).hexdigest()
        return self.cache_dir / f"{prefix}{hashed}.json"
    
    def _save_to_cache(self, cache_path: Path, data: Any) -> bool:
        """
        Save data to cache.
        
        Args:
            cache_path: Path to save to
            data: Data to cache
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get the corrected date by applying any configured offset
            current_time = datetime.now()
            if hasattr(AgentLogger, '_date_offset'):
                current_time = current_time - AgentLogger._date_offset
                
            with open(cache_path, 'w', encoding='utf-8') as f:
                cache_entry = {
                    'timestamp': current_time.isoformat(),
                    'data': data
                }
                json.dump(cache_entry, f)
            return True
        except Exception as e:
            logger.warning(f"Failed to save to cache {cache_path}: {str(e)}")
            return False
    
    def _load_from_cache(self, cache_path: Path) -> Optional[Any]:
        """
        Load data from cache if it exists and is not expired.
        
        Args:
            cache_path: Path to load from
            
        Returns:
            Cached data or None if not available/expired
        """
        if not cache_path.exists():
            return None
            
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_entry = json.load(f)
                
            # Check expiry with corrected current time
            timestamp = datetime.fromisoformat(cache_entry['timestamp'])
            
            current_time = datetime.now()
            if hasattr(AgentLogger, '_date_offset'):
                current_time = current_time - AgentLogger._date_offset
                
            if current_time - timestamp > self.cache_expiry:
                logger.info(f"Cache expired for {cache_path}")
                return None
                
            logger.info(f"Loaded from cache: {cache_path}")
            return cache_entry['data']
        except Exception as e:
            logger.warning(f"Failed to load from cache {cache_path}: {str(e)}")
            return None
    
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

    def _clean_html_content(self, soup: BeautifulSoup) -> str:
        """
        Clean and extract meaningful content from HTML.
        
        Args:
            soup: BeautifulSoup object representing the HTML
            
        Returns:
            Cleaned text content
        """
        # Remove unwanted elements
        for element in soup(['script', 'style', 'header', 'footer', 'nav', 'aside', 'noscript', 'iframe', 'form']):
            element.extract()
            
        # Remove elements with certain classes/IDs that typically contain non-content
        for selector in [
            '[class*="cookie"]', 
            '[class*="banner"]', 
            '[class*="ad-"]', 
            '[class*="sidebar"]',
            '[id*="popup"]',
            '[class*="popup"]',
            '[id*="cookie"]',
            '[class*="advertisement"]',
            '[id*="advertisement"]'
        ]:
            for element in soup.select(selector):
                element.extract()
        
        # Get text content with smart formatting
        result = []
        
        # Extract title first
        title_tag = soup.find('title')
        if title_tag:
            result.append(title_tag.get_text().strip())
            result.append("\n\n")
        
        # Extract headings with proper hierarchy
        for i, heading in enumerate(soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])):
            text = heading.get_text().strip()
            if text:
                # Add extra newlines based on heading level
                if i > 0:
                    result.append('\n\n')
                result.append(text)
                result.append('\n')
        
        # Extract paragraphs
        for p in soup.find_all('p'):
            text = p.get_text().strip()
            if text:
                result.append(text)
                result.append('\n\n')
        
        # Extract list items
        for ul in soup.find_all(['ul', 'ol']):
            for li in ul.find_all('li'):
                text = li.get_text().strip()
                if text:
                    result.append(f"• {text}")
                    result.append('\n')
            result.append('\n')
        
        # Join and clean up
        text = ''.join(result)
        
        # Clean up multiple newlines and spaces
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {2,}", " ", text)
        
        return text.strip()
    
    def fetch_page(self, url: str, use_cache: bool = True) -> Optional[WebPage]:
        """
        Fetch and parse a web page.
        
        Args:
            url: The URL to fetch
            use_cache: Whether to use caching
            
        Returns:
            WebPage object if successful, None otherwise
        """
        # Validate URL
        if not self._validate_url(url):
            return None
            
        # Check cache
        cache_path = self._get_cache_path(url) if use_cache else None
        if cache_path:
            cached_data = self._load_from_cache(cache_path)
            if cached_data:
                return WebPage(**cached_data)
        
        # Check rate limit
        self._check_rate_limit()
        self.request_count += 1
        
        # Set up headers and proxies
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "cross-site"
        }
        
        proxies = self._get_next_proxy()
        
        # Maximum number of retries for transient errors
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                logger.info(f"Fetching web page: {url}" + 
                         (f" (Proxy: {proxies})" if proxies else ""))
                
                response = requests.get(
                    url, 
                    headers=headers, 
                    timeout=self.timeout,
                    proxies=proxies,
                    allow_redirects=True
                )
                
                # Check if the request was successful
                if response.status_code != 200:
                    logger.error(f"Failed to fetch {url}: HTTP {response.status_code}")
                    
                    # For some status codes, we should rotate proxy and retry
                    if response.status_code in [403, 429, 503]:
                        logger.warning(f"Status code {response.status_code} suggests rate limiting. Rotating proxy.")
                        proxies = self._get_next_proxy()
                        retry_count += 1
                        time.sleep(2 * retry_count)  # Exponential backoff
                        continue
                    
                    return None
                
                # Auto-detect and set correct encoding if possible
                if 'charset' not in response.headers.get('content-type', '').lower():
                    # Try to detect encoding from content
                    response.encoding = response.apparent_encoding
                
                # Parse HTML content
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Extract title
                title_tag = soup.find("title")
                title = title_tag.text.strip() if title_tag else "No title"
                
                # Extract main content with improved cleaning
                cleaned_text = self._clean_html_content(soup)
                
                # Create WebPage object
                page = WebPage(
                    url=url,
                    title=title,
                    content=cleaned_text,
                    html=response.text,
                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                    metadata={
                        "status_code": response.status_code,
                        "content_type": response.headers.get("Content-Type"),
                        "content_length": len(response.text),
                        "final_url": response.url  # In case of redirects
                    }
                )
                
                # Save to cache if enabled
                if cache_path:
                    self._save_to_cache(cache_path, page.dict())
                
                logger.info(f"Successfully fetched {url}: {title} ({len(cleaned_text)} chars)")
                return page
                
            except requests.RequestException as e:
                logger.error(f"Error fetching {url}: {str(e)}")
                
                # For connection errors, retry with different proxy
                if isinstance(e, (requests.ConnectionError, requests.Timeout)):
                    logger.warning(f"Connection error. Rotating proxy and retrying.")
                    proxies = self._get_next_proxy()
                    retry_count += 1
                    time.sleep(2 * retry_count)  # Exponential backoff
                    continue
                
                return None
            except Exception as e:
                logger.error(f"Unexpected error processing {url}: {str(e)}")
                return None
        
        logger.error(f"Failed to fetch {url} after {max_retries} retries")
        return None
    
    def search_google(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """
        Perform a Google search and return a list of results.
        
        Args:
            query: The search query
            num_results: Maximum number of results to return
            
        Returns:
            List of search result dictionaries with title, url, and snippet
        """
        logger.info(f"Performing Google search for: {query}")
        
        # First try Google Search API if configured
        try:
            if hasattr(config, 'GOOGLE_SEARCH_API_KEY') and config.GOOGLE_SEARCH_API_KEY:
                return self._search_with_google_api(query, num_results)
        except Exception as e:
            logger.error(f"Error using Google Search API: {str(e)}")
        
        # If Google API fails or not configured, use direct web search fallback
        try:
            logger.info("Google Search API not available, using direct web search fallback")
            return self._direct_web_search(query, num_results)
        except Exception as e:
            logger.error(f"Error using direct web search fallback: {str(e)}")
            
            # Last resort - return helpful message if all else fails
            return [
                {
                    "title": "Web Search Fallback Failed",
                    "url": "https://example.com/search-error",
                    "snippet": "The search operation failed. Consider implementing a search API like Serper.dev, SerpAPI, or configure a custom search engine."
                }
            ]
    
    def _search_with_google_api(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """
        Search using the Google Custom Search API.
        
        Args:
            query: The search query
            num_results: Maximum number of results to return
            
        Returns:
            List of search result dictionaries
        """
        api_key = getattr(config, 'GOOGLE_SEARCH_API_KEY', '')
        cx = getattr(config, 'GOOGLE_SEARCH_ENGINE_ID', '')
        
        if not api_key or not cx:
            raise ValueError("Google Search API key or engine ID not configured")
        
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': api_key,
            'cx': cx,
            'q': query,
            'num': min(num_results, 10)  # Google limits to 10 results per query
        }
        
        response = requests.get(url, params=params, timeout=self.timeout)
        if response.status_code != 200:
            raise Exception(f"API request failed with status {response.status_code}: {response.text}")
        
        data = response.json()
        results = []
        
        if 'items' in data:
            for item in data['items']:
                results.append({
                    'title': item.get('title', ''),
                    'url': item.get('link', ''),
                    'snippet': item.get('snippet', '')
                })
                
        return results
    
    def _direct_web_search(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """
        Perform a direct web search by scraping search engines.
        This is a fallback method when Google API is not available.
        
        Args:
            query: The search query
            num_results: Maximum number of results to return
            
        Returns:
            List of search result dictionaries
        """
        # Try multiple search engines with fallbacks
        search_engines = [
            self._search_duckduckgo,
            self._search_bing,
            self._search_fallback
        ]
        
        results = []
        for search_engine in search_engines:
            try:
                results = search_engine(query, num_results)
                if results and len(results) > 0:
                    break
            except Exception as e:
                logger.warning(f"Search engine attempt failed: {str(e)}")
                continue
        
        return results[:num_results]
    
    def _search_duckduckgo(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """
        Search using DuckDuckGo's lite version.
        
        Args:
            query: The search query
            num_results: Maximum number of results to return
            
        Returns:
            List of search result dictionaries
        """
        # Use the lite version which is easier to parse
        url = "https://lite.duckduckgo.com/lite/"
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        }
        
        data = {
            "q": query
        }
        
        self._check_rate_limit()
        self.request_count += 1
        
        response = requests.post(url, headers=headers, data=data, timeout=self.timeout)
        soup = BeautifulSoup(response.text, "html.parser")
        
        results = []
        # DuckDuckGo lite uses tables for results
        for tr in soup.find_all('tr'):
            # Get all td elements within the tr
            tds = tr.find_all('td')
            # Each result has multiple td elements
            if len(tds) >= 2:
                a_tag = tds[0].find('a')
                if a_tag and a_tag.get('href'):
                    # The first td contains the title and link
                    title = a_tag.text.strip()
                    url = a_tag.get('href')
                    
                    # The next td often contains the snippet
                    snippet = ""
                    if len(tds) > 1:
                        snippet = tds[1].text.strip()
                    
                    # Skip internal DuckDuckGo navigation links
                    if not url.startswith('/lite'):
                        results.append({
                            'title': title,
                            'url': url,
                            'snippet': snippet
                        })
            
            if len(results) >= num_results:
                break
                
        return results
    
    def _search_bing(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """
        Search using Bing.
        
        Args:
            query: The search query
            num_results: Maximum number of results to return
            
        Returns:
            List of search result dictionaries
        """
        url = f"https://www.bing.com/search"
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5"
        }
        
        params = {
            "q": query,
            "count": num_results
        }
        
        self._check_rate_limit()
        self.request_count += 1
        
        response = requests.get(url, headers=headers, params=params, timeout=self.timeout)
        soup = BeautifulSoup(response.text, "html.parser")
        
        results = []
        # Bing search results are in <li class="b_algo"> elements
        for li in soup.select("li.b_algo"):
            # Get the title and URL
            h2 = li.select_one("h2")
            if not h2:
                continue
                
            a_tag = h2.select_one("a")
            if not a_tag:
                continue
                
            title = a_tag.text.strip()
            result_url = a_tag.get("href", "")
            
            # Get the snippet
            p_tag = li.select_one("p")
            snippet = p_tag.text.strip() if p_tag else ""
            
            results.append({
                "title": title,
                "url": result_url,
                "snippet": snippet
            })
            
            if len(results) >= num_results:
                break
                
        return results
    
    def _search_fallback(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """
        A dummy fallback that returns a message about the search limitations.
        
        Args:
            query: The search query
            num_results: Maximum number of results to return
            
        Returns:
            List with a single message about search limitations
        """
        dummy_domains = [
            "https://en.wikipedia.org/wiki/",
            "https://www.bbc.com/news/",
            "https://www.nytimes.com/",
            "https://www.reuters.com/",
            "https://www.theguardian.com/"
        ]
        
        query_terms = query.split()
        results = []
        
        # Create some semi-plausible dummy results based on query terms
        for i in range(min(num_results, len(dummy_domains))):
            domain = dummy_domains[i % len(dummy_domains)]
            term = query_terms[i % len(query_terms)].lower()
            
            results.append({
                "title": f"Research on {term.capitalize()} (Simulated Result)",
                "url": f"{domain}{term.replace(' ', '_')}",
                "snippet": (
                    f"This is a simulated search result for '{query}'. "
                    f"To get real search results, configure a search API integration. "
                    f"Dummy content related to {term}."
                )
            })
        
        return results
    
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
            # Parse HTML content
            soup = BeautifulSoup(page.html, "html.parser")
            
            # Find elements matching the selector
            elements = soup.select(selector)
            
            if not elements:
                logger.warning(f"No elements found for selector '{selector}' on {url}")
                return ""
            
            # Extract and join text from all matching elements
            texts = [elem.get_text().strip() for elem in elements]
            result = "\n".join(texts)
            
            logger.info(f"Extracted {len(texts)} elements with selector '{selector}' from {url}")
            return result
            
        except Exception as e:
            logger.error(f"Error extracting text with selector '{selector}' from {url}: {str(e)}")
            return ""
            
    def analyze_webpage(self, url: str) -> Dict[str, Any]:
        """
        Analyze a webpage to extract key information and structured content.
        
        This method fetches a webpage and performs intelligent analysis to extract:
        - Main content
        - Key points
        - Important metadata
        - Article structure
        
        Args:
            url: The URL of the webpage to analyze
            
        Returns:
            Dictionary with extracted information
        """
        page = self.fetch_page(url)
        if not page:
            return {
                "url": url,
                "success": False,
                "error": "Failed to fetch webpage"
            }
        
        try:
            # Parse HTML content
            soup = BeautifulSoup(page.html, "html.parser")
            
            # Extract metadata and key information
            result = {
                "url": url,
                "title": page.title,
                "success": True,
                "timestamp": page.timestamp,
                "main_content": page.content,
                "metadata": page.metadata,
                "structure": {}
            }
            
            # Try to identify the main article content
            article = soup.find(["article", "main"])
            if article:
                result["main_content"] = article.get_text(strip=True)
            
            # Extract headings to understand structure
            headings = []
            for heading in soup.find_all(["h1", "h2", "h3"]):
                headings.append({
                    "level": int(heading.name[1]),
                    "text": heading.get_text(strip=True)
                })
            result["structure"]["headings"] = headings
            
            # Extract lists (could be key points)
            lists = []
            for list_elem in soup.find_all(["ul", "ol"]):
                list_items = []
                for item in list_elem.find_all("li"):
                    list_items.append(item.get_text(strip=True))
                if list_items:
                    lists.append({
                        "type": list_elem.name,
                        "items": list_items
                    })
            result["structure"]["lists"] = lists
            
            # Extract tables
            tables = []
            for table in soup.find_all("table"):
                table_data = []
                rows = table.find_all("tr")
                
                # Process headers
                headers = []
                header_row = table.find("thead")
                if header_row:
                    for th in header_row.find_all(["th"]):
                        headers.append(th.get_text(strip=True))
                
                # Process data rows
                for row in rows:
                    row_data = []
                    for cell in row.find_all(["td", "th"]):
                        row_data.append(cell.get_text(strip=True))
                    if row_data:  # Skip empty rows
                        table_data.append(row_data)
                
                if table_data:
                    tables.append({
                        "headers": headers,
                        "data": table_data
                    })
            result["structure"]["tables"] = tables
            
            # Extract key dates using a simple pattern
            date_pattern = re.compile(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\b')
            dates = date_pattern.findall(page.content)
            result["extracted_dates"] = dates
            
            logger.info(f"Successfully analyzed webpage: {url}")
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing webpage {url}: {str(e)}")
            return {
                "url": url,
                "success": False,
                "error": str(e),
                "content": page.content if page else None
            } 