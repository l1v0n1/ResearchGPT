"""
Test script for verifying the functionality of the WebScrapingTool.
"""
import os
import sys
import logging
from typing import List, Dict

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("web_tool_test")

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.tools.web import WebScrapingTool
from agent import config

def test_web_tool():
    """Test the main functionalities of the web scraping tool."""
    
    logger.info("Testing WebScrapingTool")
    
    # Initialize the tool
    web_tool = WebScrapingTool()
    
    # Test 1: Check initialization
    logger.info("Test 1: Checking initialization")
    assert web_tool.user_agent == config.USER_AGENT, "User agent not set correctly"
    assert web_tool.timeout == config.REQUEST_TIMEOUT, "Timeout not set correctly"
    assert web_tool.allowed_domains == config.ALLOWED_DOMAINS, "Allowed domains not set correctly"
    
    # Test 2: Test URL validation
    logger.info("Test 2: Testing URL validation")
    valid_url = "https://en.wikipedia.org/wiki/Python_(programming_language)"
    invalid_url = "https://example.com/test"  # Assuming this is not in the allowed domains
    
    assert web_tool._validate_url(valid_url) is True, f"Valid URL {valid_url} not validated correctly"
    if "example.com" not in config.ALLOWED_DOMAINS:
        assert web_tool._validate_url(invalid_url) is False, f"Invalid URL {invalid_url} not rejected correctly"
    
    # Test 3: Fetch a page
    logger.info("Test 3: Testing page fetching")
    page = web_tool.fetch_page(valid_url)
    assert page is not None, "Failed to fetch a valid page"
    assert page.url == valid_url, "URL mismatch in fetched page"
    assert len(page.content) > 0, "Empty content in fetched page"
    assert page.title and len(page.title) > 0, "Title missing in fetched page"
    
    # Test 4: Extract links
    logger.info("Test 4: Testing link extraction")
    links = web_tool.extract_links(valid_url)
    assert isinstance(links, list), "extract_links should return a list"
    assert len(links) > 0, "No links extracted from Wikipedia page"
    
    # Check link structure
    if links:
        link = links[0]
        assert "url" in link, "Link missing URL"
        assert "text" in link, "Link missing text"
    
    # Test 5: Extract text with selector
    logger.info("Test 5: Testing text extraction with selector")
    # Wikipedia's first paragraph is usually in the first p element
    text = web_tool.extract_text_with_selector(valid_url, "div.mw-parser-output > p")
    assert text and len(text) > 0, "No text extracted with selector"
    
    # Test 6: Test search functionality
    logger.info("Test 6: Testing search functionality")
    search_results = web_tool.search_google("Python programming language")
    assert isinstance(search_results, list), "search_google should return a list"
    
    # Basic check of each search result
    for result in search_results:
        assert isinstance(result, dict), "Each search result should be a dictionary"
        assert "title" in result, "Search result missing title"
        assert "url" in result, "Search result missing URL"
        assert "snippet" in result, "Search result missing snippet"
    
    logger.info("All web tool tests passed!")
    return True

if __name__ == "__main__":
    try:
        test_web_tool()
        print("✅ Web tool tests completed successfully!")
    except AssertionError as e:
        print(f"❌ Test failed: {str(e)}")
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}") 