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

# OpenAI API configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_ORGANIZATION = os.getenv("OPENAI_ORGANIZATION")

# Model configuration
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4-1106-preview")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", 4096))
TEMPERATURE = float(os.getenv("TEMPERATURE", 0.7))

# File paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
DOCUMENT_DIR = Path(os.getenv("DOCUMENT_DIR", str(DATA_DIR / "documents")))

# Ensure necessary directories exist
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)
DOCUMENT_DIR.mkdir(exist_ok=True, parents=True)

# Database configuration
DB_PATH = os.getenv("DB_PATH", str(DATA_DIR / "memory.db"))

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", str(LOG_DIR / "agent.log"))

# Web scraping configuration
USER_AGENT = os.getenv("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 30))

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
    "wikipedia.org",
    "arxiv.org",
    "scholar.google.com",
    "news.google.com",
    "github.com",
    "stackoverflow.com",
    "medium.com",
    "reddit.com"
]

# Rate limiting
API_RATE_LIMIT = 20  # Maximum requests per minute to OpenAI API
WEB_RATE_LIMIT = 10  # Maximum web requests per minute 