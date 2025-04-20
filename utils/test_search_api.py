#!/usr/bin/env python

"""
Test script to verify Google Search API functionality and demonstrate domain allowlisting.
"""

import sys
import os
from pathlib import Path

# Add the parent directory to the path to ensure imports work correctly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.tools.web import WebScrapingTool
from agent import config

def test_search_api():
    """Test if the Google Search API is working."""
    print("Testing Google Search API...")
    
    # Create a web scraping tool with no domain restrictions
    web_tool = WebScrapingTool(cache_dir=None)
    
    # Temporarily allow all domains by overriding the validation method
    original_validate = web_tool._validate_url
    web_tool._validate_url = lambda url: True
    
    try:
        # Test the search API
        query = "artificial intelligence news"
        results = web_tool.search_google(query, num_results=3)
        
        if not results:
            print("❌ No search results returned. API may not be configured or is not working.")
            return False
        
        print(f"✅ Search API returned {len(results)} results for query: '{query}'")
        
        # Display the results
        for i, result in enumerate(results):
            print(f"\nResult {i+1}:")
            print(f"  Title: {result.get('title', 'No title')}")
            print(f"  URL: {result.get('url', 'No URL')}")
            print(f"  Snippet: {result.get('snippet', 'No snippet')[:100]}...")
        
        # Test fetching one of the pages
        if results and "url" in results[0]:
            url = results[0]["url"]
            print(f"\nTesting page fetch for: {url}")
            page = web_tool.fetch_page(url)
            
            if page:
                print(f"✅ Successfully fetched page: {page.title} ({len(page.content)} chars)")
                return True
            else:
                print(f"❌ Failed to fetch page: {url}")
                return False
        
        return True
    
    finally:
        # Restore the original URL validation method
        web_tool._validate_url = original_validate

def print_allowed_domains():
    """Print the currently allowed domains."""
    print("\nCurrently allowed domains:")
    if hasattr(config, 'ALLOWED_DOMAINS') and config.ALLOWED_DOMAINS:
        for domain in config.ALLOWED_DOMAINS:
            print(f"  - {domain}")
    else:
        print("  No domain restrictions (all domains are allowed)")

def add_allowed_domain(domain):
    """Add a domain to the allowed list."""
    if not hasattr(config, 'ALLOWED_DOMAINS') or config.ALLOWED_DOMAINS is None:
        config.ALLOWED_DOMAINS = []
    
    if domain not in config.ALLOWED_DOMAINS:
        config.ALLOWED_DOMAINS.append(domain)
        print(f"Added '{domain}' to allowed domains")
    else:
        print(f"'{domain}' is already in allowed domains")

def main():
    """Main function to run the tests."""
    print("=" * 50)
    print("Google Search API and Domain Allowlisting Test")
    print("=" * 50)
    
    # Print current allowed domains
    print_allowed_domains()
    
    # Example of adding a domain
    print("\nAdding example.com to allowed domains:")
    add_allowed_domain("example.com")
    add_allowed_domain("openai.com")
    add_allowed_domain("github.com")
    
    # Print updated allowed domains
    print_allowed_domains()
    
    # Run the search API test
    print("\n" + "=" * 50)
    result = test_search_api()
    print("=" * 50)
    
    if result:
        print("\nGoogle Search API test completed successfully!")
    else:
        print("\nGoogle Search API test failed. Check your API configuration.")
        print("Possible issues:")
        print("1. Missing or invalid API key in your environment variables.")
        print("2. Rate limiting from the API service.")
        print("3. Network connectivity issues.")
        print("\nCheck your config.py file for GOOGLE_API_KEY and GOOGLE_CSE_ID settings.")

if __name__ == "__main__":
    main() 