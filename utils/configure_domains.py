#!/usr/bin/env python

"""
Utility to configure allowed domains for web scraping in the agent configuration.
"""

import os
import sys
import argparse
from pathlib import Path

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

def list_domains():
    """List all currently allowed domains."""
    if hasattr(config, 'ALLOWED_DOMAINS') and config.ALLOWED_DOMAINS:
        print("\nCurrently allowed domains:")
        for domain in config.ALLOWED_DOMAINS:
            print(f"  - {domain}")
        print(f"\nTotal: {len(config.ALLOWED_DOMAINS)} domains")
    else:
        print("\nNo domain restrictions configured (all domains are allowed)")

def add_domain(domain, update_file=True):
    """Add a domain to the allowed list."""
    if not hasattr(config, 'ALLOWED_DOMAINS') or config.ALLOWED_DOMAINS is None:
        config.ALLOWED_DOMAINS = []
    
    if domain in config.ALLOWED_DOMAINS:
        print(f"'{domain}' is already in allowed domains")
        return False
    
    config.ALLOWED_DOMAINS.append(domain)
    print(f"Added '{domain}' to allowed domains")
    
    if update_file:
        return update_config_file()
    return True

def remove_domain(domain, update_file=True):
    """Remove a domain from the allowed list."""
    if not hasattr(config, 'ALLOWED_DOMAINS') or not config.ALLOWED_DOMAINS:
        print("No domains are currently configured")
        return False
    
    if domain not in config.ALLOWED_DOMAINS:
        print(f"'{domain}' is not in allowed domains")
        return False
    
    config.ALLOWED_DOMAINS.remove(domain)
    print(f"Removed '{domain}' from allowed domains")
    
    if update_file:
        return update_config_file()
    return True

def allow_all_domains(update_file=True):
    """Set the configuration to allow all domains."""
    config.ALLOWED_DOMAINS = []
    print("Configuration updated to allow all domains")
    
    if update_file:
        return update_config_file()
    return True

def update_config_file():
    """Update the config.py file with the current domain settings."""
    config_file = get_config_file_path()
    if not config_file or not config_file.exists():
        print(f"Error: Could not find config file at {config_file}")
        return False
    
    try:
        # Read the current config file
        with open(config_file, 'r') as f:
            lines = f.readlines()
        
        # Find the ALLOWED_DOMAINS definition or prepare to add it
        found = False
        for i, line in enumerate(lines):
            if line.strip().startswith('ALLOWED_DOMAINS'):
                # Replace the existing definition
                domains_str = ", ".join([f"'{d}'" for d in config.ALLOWED_DOMAINS])
                lines[i] = f"ALLOWED_DOMAINS = [{domains_str}]\n"
                found = True
                break
        
        # If not found, add the definition at the end
        if not found:
            domains_str = ", ".join([f"'{d}'" for d in config.ALLOWED_DOMAINS])
            lines.append(f"\n# Web domains allowed for scraping\nALLOWED_DOMAINS = [{domains_str}]\n")
        
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
    parser = argparse.ArgumentParser(description="Configure allowed domains for web scraping")
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--list", action="store_true", help="List currently allowed domains")
    group.add_argument("--add", metavar="DOMAIN", help="Add a domain to allowed list")
    group.add_argument("--remove", metavar="DOMAIN", help="Remove a domain from allowed list")
    group.add_argument("--allow-all", action="store_true", help="Allow all domains (empty restriction list)")
    group.add_argument("--add-common", action="store_true", help="Add common domains (google.com, wikipedia.org, etc.)")
    
    args = parser.parse_args()
    
    # Get the config file path
    config_file = get_config_file_path()
    if config_file:
        print(f"Config file: {config_file}")
    else:
        print("Warning: Could not locate config.py file")
    
    # Execute the requested action
    if args.list or (not args.add and not args.remove and not args.allow_all and not args.add_common):
        list_domains()
    
    elif args.add:
        add_domain(args.add)
    
    elif args.remove:
        remove_domain(args.remove)
    
    elif args.allow_all:
        allow_all_domains()
    
    elif args.add_common:
        print("Adding common domains:")
        common_domains = [
            "google.com", 
            "wikipedia.org", 
            "github.com", 
            "stackoverflow.com",
            "medium.com",
            "nytimes.com",
            "bbc.com",
            "cnn.com",
            "reuters.com",
            "openai.com",
            "docs.python.org",
            "pytorch.org",
            "tensorflow.org"
        ]
        
        for domain in common_domains:
            add_domain(domain, update_file=False)
        
        update_config_file()

if __name__ == "__main__":
    main() 