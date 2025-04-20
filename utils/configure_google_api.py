#!/usr/bin/env python

"""
Utility to configure and test Google Search API settings.
"""

import os
import sys
import argparse
from pathlib import Path
import requests
import json

# Add the parent directory to the path to ensure imports work correctly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import config

def get_config_file_path():
    """Get the path to the config.py file."""
    # Look in the agent module directory
    try:
        agent_dir = Path(config.__file__).parent
        config_file = agent_dir / "config.py"
        return config_file
    except:
        return None

def show_current_settings():
    """Display current Google API settings."""
    print("\nCurrent Google Search API Settings:")
    
    # API Key
    api_key = getattr(config, 'GOOGLE_API_KEY', None)
    if api_key:
        # Mask the API key for security
        masked_key = api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:]
        print(f"  GOOGLE_API_KEY: {masked_key}")
    else:
        print("  GOOGLE_API_KEY: Not configured")
    
    # CSE ID
    cse_id = getattr(config, 'GOOGLE_CSE_ID', None)
    if cse_id:
        # Mask the CSE ID for security
        masked_id = cse_id[:4] + "*" * (len(cse_id) - 8) + cse_id[-4:]
        print(f"  GOOGLE_CSE_ID: {masked_id}")
    else:
        print("  GOOGLE_CSE_ID: Not configured")
    
    # Search API method preference
    search_method = getattr(config, 'SEARCH_API_METHOD', 'fallback')
    print(f"  SEARCH_API_METHOD: {search_method}")

def test_api_key(api_key, cse_id, query="test"):
    """Test if the provided API key and CSE ID work correctly."""
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key,
        "cx": cse_id,
        "q": query
    }
    
    try:
        print(f"\nTesting Google Search API with query: '{query}'")
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            if "items" in data and len(data["items"]) > 0:
                print(f"✅ API test successful! Found {len(data['items'])} results.")
                print("\nFirst result:")
                first_item = data["items"][0]
                print(f"  Title: {first_item.get('title', 'No title')}")
                print(f"  URL: {first_item.get('link', 'No URL')}")
                return True
            else:
                print("⚠️ API request successful but no results found.")
                return True
        else:
            error_data = response.json() if response.text else {"error": {"message": "Unknown error"}}
            error_message = error_data.get("error", {}).get("message", "Unknown error")
            print(f"❌ API test failed with status {response.status_code}: {error_message}")
            return False
    
    except Exception as e:
        print(f"❌ API test failed: {str(e)}")
        return False

def update_config_file(api_key=None, cse_id=None, search_method=None):
    """Update the config.py file with the Google API settings."""
    config_file = get_config_file_path()
    if not config_file or not config_file.exists():
        print(f"Error: Could not find config file at {config_file}")
        return False
    
    try:
        # Read the current config file
        with open(config_file, 'r') as f:
            lines = f.readlines()
        
        # Track which settings we've updated
        api_key_found = cse_id_found = search_method_found = False
        
        # Update existing settings
        for i, line in enumerate(lines):
            # Update API key
            if api_key is not None and line.strip().startswith('GOOGLE_API_KEY'):
                lines[i] = f"GOOGLE_API_KEY = '{api_key}'\n"
                api_key_found = True
            
            # Update CSE ID
            if cse_id is not None and line.strip().startswith('GOOGLE_CSE_ID'):
                lines[i] = f"GOOGLE_CSE_ID = '{cse_id}'\n"
                cse_id_found = True
            
            # Update search method
            if search_method is not None and line.strip().startswith('SEARCH_API_METHOD'):
                lines[i] = f"SEARCH_API_METHOD = '{search_method}'\n"
                search_method_found = True
        
        # Add settings that weren't found
        if api_key is not None and not api_key_found:
            lines.append(f"\n# Google Custom Search API key\nGOOGLE_API_KEY = '{api_key}'\n")
        
        if cse_id is not None and not cse_id_found:
            lines.append(f"\n# Google Custom Search Engine ID\nGOOGLE_CSE_ID = '{cse_id}'\n")
        
        if search_method is not None and not search_method_found:
            lines.append(f"\n# Preferred search API method (google, direct, fallback)\nSEARCH_API_METHOD = '{search_method}'\n")
        
        # Write the updated file
        with open(config_file, 'w') as f:
            f.writelines(lines)
        
        print(f"Updated config file: {config_file}")
        return True
    
    except Exception as e:
        print(f"Error updating config file: {str(e)}")
        return False

def main():
    """Main function to parse arguments and run the utility."""
    parser = argparse.ArgumentParser(description="Configure and test Google Search API settings")
    
    parser.add_argument("--show", action="store_true", help="Show current API settings")
    parser.add_argument("--set-key", metavar="API_KEY", help="Set Google API Key")
    parser.add_argument("--set-cse", metavar="CSE_ID", help="Set Google Custom Search Engine ID")
    parser.add_argument("--set-method", choices=["google", "direct", "fallback"], 
                        help="Set preferred search method (google, direct, fallback)")
    parser.add_argument("--test", action="store_true", help="Test the current API settings")
    parser.add_argument("--query", default="latest news", help="Test search query (default: 'latest news')")
    
    args = parser.parse_args()
    
    # Get the config file path
    config_file = get_config_file_path()
    if config_file:
        print(f"Config file: {config_file}")
    else:
        print("Warning: Could not locate config.py file")
    
    # Show current settings if requested or if no other action specified
    if args.show or (not args.set_key and not args.set_cse and not args.set_method and not args.test):
        show_current_settings()
    
    # Update settings if requested
    if args.set_key or args.set_cse or args.set_method:
        update_config_file(
            api_key=args.set_key, 
            cse_id=args.set_cse, 
            search_method=args.set_method
        )
        
        # Reload config to reflect changes
        import importlib
        importlib.reload(config)
        show_current_settings()
    
    # Test API if requested
    if args.test:
        api_key = getattr(config, 'GOOGLE_API_KEY', None)
        cse_id = getattr(config, 'GOOGLE_CSE_ID', None)
        
        if not api_key or not cse_id:
            print("\n❌ Cannot test API: API key or CSE ID is missing")
            print("Please configure them with --set-key and --set-cse options")
        else:
            test_api_key(api_key, cse_id, args.query)

if __name__ == "__main__":
    main() 