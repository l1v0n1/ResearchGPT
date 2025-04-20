# Web Search Configuration Tools

This directory contains several utilities to help configure and test web search capabilities for the MyAgent research assistant.

## 1. Domain Configuration (`configure_domains.py`)

This script allows you to configure which domains are allowed for web scraping.

### Usage

```bash
# List currently allowed domains
python utils/configure_domains.py --list

# Add a specific domain
python utils/configure_domains.py --add example.com

# Remove a domain
python utils/configure_domains.py --remove example.com

# Add a set of common domains
python utils/configure_domains.py --add-common

# Allow all domains (empty restriction list)
python utils/configure_domains.py --allow-all
```

## 2. Google Search API Configuration (`configure_google_api.py`)

This script helps you configure and test Google Search API settings.

### Usage

```bash
# Show current Google API settings
python utils/configure_google_api.py --show

# Set your Google API Key
python utils/configure_google_api.py --set-key YOUR_API_KEY

# Set your Custom Search Engine ID
python utils/configure_google_api.py --set-cse YOUR_CSE_ID

# Set preferred search method
python utils/configure_google_api.py --set-method google

# Test the current API settings
python utils/configure_google_api.py --test

# Test with a specific query
python utils/configure_google_api.py --test --query "artificial intelligence"
```

## 3. Search API Test (`test_search_api.py`)

This script provides a quick way to test if the Google Search API is working and demonstrates domain allowlisting.

### Usage

```bash
# Run the test
python utils/test_search_api.py
```

## Getting a Google API Key and Custom Search Engine ID

To use the Google Search API, you need:

1. A Google API Key from the [Google Cloud Console](https://console.cloud.google.com/)
2. A Custom Search Engine ID from the [Programmable Search Engine Control Panel](https://programmablesearchengine.google.com/)

### Steps to obtain a Google API Key:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Navigate to "APIs & Services" > "Library"
4. Search for and enable the "Custom Search API"
5. Go to "APIs & Services" > "Credentials"
6. Click "Create Credentials" > "API Key"
7. Copy your API key

### Steps to create a Custom Search Engine:

1. Go to the [Programmable Search Engine Control Panel](https://programmablesearchengine.google.com/)
2. Click "Add" to create a new search engine
3. Choose the sites you want to search or select "Search the entire web"
4. Give your search engine a name and create it
5. Click "Control Panel" and then "Basics"
6. Copy your "Search engine ID" (cx value)

## Notes

- **Domain Restrictions**: Empty `ALLOWED_DOMAINS` list means all domains are allowed
- **Search Methods**: 
  - `google`: Use the Google Custom Search API (requires API key and CSE ID)
  - `direct`: Use direct web search (no API key required, but less reliable)
  - `fallback`: Try Google API first, then fall back to direct search if not available
- **Rate Limits**: The Google Custom Search API has a free tier limit of 100 queries per day

## Implementation Notes

These tools were created to solve two common issues with the MyAgent research assistant:

1. **Domain Restrictions**: The agent has built-in domain restrictions for security, but sometimes these restrictions can be too limiting for certain research tasks. The domain configuration tools allow you to:
   - Add new trusted domains dynamically
   - Remove domains that aren't needed
   - Quickly add common domains with the `--add-common` option
   - Allow all domains if needed (use with caution)

2. **Google Search API Configuration**: The agent uses Google Search for web queries, but the API requires proper configuration with API keys. The Google API tools allow you to:
   - Check your current API settings
   - Set or update your API key and Custom Search Engine ID
   - Test if your API configuration is working correctly
   - Switch between search methods (Google API, direct search, or fallback)

The tools demonstrate how the agent handles domain restrictions and search functionality:
- The `_validate_url` method in `WebScrapingTool` checks domains against the allowed list
- The search methods cascade from Google API to fallback methods based on availability
- Both domain restrictions and API settings are stored in the main config file

These utilities make it easier to configure and test the agent's web search capabilities without modifying the core code. 