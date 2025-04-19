"""
Configuration settings for the AI Research Agent.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Agent objective and identity
AGENT_NAME = "Research Assistant"
AGENT_OBJECTIVE = "Provide research summaries on demand by querying internal documents and web resources."
AGENT_DESCRIPTION = """
This AI research agent assists users by retrieving information from various sources,
analyzing and summarizing content, and presenting comprehensive research briefs.
The agent maintains memory of previous interactions to build context over time.
"""

# --- Ollama Configuration --- 
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:latest") # Primary model for generation
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text") # Model for embeddings
OLLAMA_REQUEST_TIMEOUT = int(os.getenv("OLLAMA_REQUEST_TIMEOUT", 120)) # Default 120 seconds

# --- General Model Configuration (used by wrapper) ---
MODEL_NAME = OLLAMA_MODEL # Use the Ollama model name as the primary identifier
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4096")) # Context window size
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))

# File paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
DOCUMENT_DIR = Path(os.getenv("DOCUMENT_DIR", str(DATA_DIR / "documents")))
SUMMARIES_DIR = Path(os.getenv("SUMMARIES_DIR", str(DATA_DIR / "summaries")))

# Ensure necessary directories exist
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)
DOCUMENT_DIR.mkdir(exist_ok=True, parents=True)
SUMMARIES_DIR.mkdir(exist_ok=True, parents=True)

# Database configuration
DB_PATH = os.getenv("DB_PATH", str(DATA_DIR / "memory.db"))

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", str(LOG_DIR / "agent.log"))

# Web scraping configuration
USER_AGENT = os.getenv("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 30)) # Keep separate timeout for web requests

# Google Search API Configuration
GOOGLE_SEARCH_API_KEY = os.getenv("GOOGLE_SEARCH_API_KEY", "")
GOOGLE_SEARCH_ENGINE_ID = os.getenv("GOOGLE_SEARCH_ENGINE_ID", "")

# Tool configuration
TOOLS = {
    "web_search": {
        "enabled": True,
        "description": "Search the web for information on a given topic"
    },
    "document_search": {
        "enabled": True,
        "description": "Search local documents for relevant information"
    }
}

# Security and validation
MAX_QUERY_LENGTH = 500  # Maximum length of user queries
ALLOWED_DOMAINS = [  # Domains that the agent is allowed to scrape
    # Academic and reference sources
    "wikipedia.org",
    "arxiv.org",
    "scholar.google.com",
    "researchgate.net",
    "semanticscholar.org",
    "sciencedirect.com",
    "pubmed.ncbi.nlm.nih.gov",
    "ncbi.nlm.nih.gov",
    
    # News and journalism
    "news.google.com",
    "reuters.com",
    "apnews.com",
    "bbc.com",
    "nytimes.com",
    "washingtonpost.com",
    "theguardian.com",
    "aljazeera.com",
    "bloomberg.com",
    
    # Tech and developer resources
    "github.com",
    "stackoverflow.com",
    "medium.com",
    "dev.to",
    "arxiv-sanity.com",
    "ieee.org",
    "acm.org",
    
    # Social and discussion
    "reddit.com",
    "hackernews.com",
    "ycombinator.com",
    
    # Government and institutions
    "nih.gov",
    "cdc.gov",
    "who.int",
    "un.org",
    "worldbank.org",
    "europa.eu",
    "nasa.gov",
    
    # Space and technology news
    "space.com",
    "spacenews.com", 
    "universetoday.com",
    "nasaspaceflight.com",
    "arstechnica.com",
    "techcrunch.com",
    "theverge.com",
    "wired.com",
    "cnet.com",
    "zdnet.com",
    "spaceflightnow.com",
    "astronomy.com",
    "skyandtelescope.org"
]

# Rate limiting (Less critical for local Ollama, but can keep structure)
API_RATE_LIMIT = 1000 # Increase significantly for local Ollama
WEB_RATE_LIMIT = 10  # Keep web rate limit 