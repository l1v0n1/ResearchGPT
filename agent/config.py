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
    "wikimedia.org",
    "arxiv.org",
    "scholar.google.com",
    "researchgate.net",
    "semanticscholar.org",
    "sciencedirect.com",
    "pubmed.ncbi.nlm.nih.gov",
    "ncbi.nlm.nih.gov",
    "nature.com",
    "science.org",
    "jstor.org",
    "ssrn.com",
    "tandfonline.com",
    "springer.com",
    "sciencemag.org",
    "pnas.org",
    "cell.com",
    "acs.org",
    "frontiersin.org",
    "plos.org",
    "mdpi.com",
    "apa.org",
    "academic.oup.com",
    "elsevier.com",
    "sage.com",
    "wiley.com",
    "biorxiv.org",
    "medrxiv.org",
    "psychologytoday.com",
    "scientificamerican.com",
    "thelancet.com",
    "bmj.com",
    "newscientist.com",
    "mit.edu",
    "harvard.edu",
    "stanford.edu",
    "berkeley.edu",
    "caltech.edu",
    "cam.ac.uk",
    "ox.ac.uk",
    "cornell.edu",
    "princeton.edu",
    "yale.edu",
    "columbia.edu",
    "uchicago.edu",
    "ucl.ac.uk",
    "imperial.ac.uk",
    "eth.ch",
    "tsinghua.edu.cn",
    
    # News and journalism
    "news.google.com", # Meta-source
    "reuters.com",
    "apnews.com",
    "bbc.com", # Also handles bbc.co.uk implicitly
    "nytimes.com",
    "washingtonpost.com",
    "theguardian.com",
    "aljazeera.com",
    "bloomberg.com",
    "wsj.com",
    "cnn.com",
    "nbcnews.com",
    "abcnews.go.com",
    "cbsnews.com",
    "foxnews.com",
    "npr.org",
    "pbs.org",
    "time.com",
    "forbes.com",
    "theatlantic.com",
    "axios.com",
    "politico.com",
    "usatoday.com",
    "latimes.com",
    "economist.com",
    "ft.com",
    "cnbc.com",
    "businessinsider.com",
    "vox.com",
    "slate.com",
    "newyorker.com",
    "independent.co.uk",
    "telegraph.co.uk",
    "huffpost.com",
    "thehill.com",
    "apnews.com",
    "france24.com",
    "dw.com",
    "euronews.com",
    "scmp.com",
    "abc.net.au",
    "cbc.ca",
    "dailymail.co.uk",
    "france24.com",
    "indiatimes.com",
    "timesofindia.indiatimes.com",
    "japantimes.co.jp",
    "kyodonews.net",
    "reuters.com",
    "straitstimes.com",
    
    # Tech and developer resources
    "github.com",
    "stackoverflow.com",
    "stackexchange.com",
    "medium.com",
    "dev.to",
    "arxiv-sanity.com",
    "ieee.org",
    "acm.org",
    "techcrunch.com",
    "wired.com",
    "theverge.com",
    "arstechnica.com",
    "thenextweb.com",
    "venturebeat.com",
    "engadget.com",
    "makeuseof.com",
    "digitaltrends.com",
    "gizmodo.com",
    "slashdot.org",
    "hackaday.com",
    "techradar.com",
    "cnet.com",
    "zdnet.com",
    "informationweek.com",
    "infoworld.com",
    "computerworld.com",
    "tomshardware.com",
    "techrepublic.com",
    "lifewire.com",
    "howtogeek.com",
    "androidcentral.com",
    "9to5mac.com",
    "9to5google.com",
    "xda-developers.com",
    "ifixit.com",
    "geeksforgeeks.org",
    "w3schools.com",
    "tutorialspoint.com",
    "freecodecamp.org",
    "codeproject.com",
    "kaggle.com",
    "codepen.io",
    "gitlab.com",
    "bitcointalk.org",
    "producthunt.com",
    "macrumors.com",
    "androidauthority.com",
    "hackernoon.com",
    "towardsdatascience.com",
    
    # Social and discussion (Use with caution)
    "reddit.com",
    "hackernews.com",
    "ycombinator.com",
    "quora.com",
    "stackoverflow.blog",
    "slatestarcodex.com",
    "lesswrong.com",
    "metafilter.com",
    "lobste.rs",
    "indiehackers.com",
    
    # Government and institutions
    "nih.gov",
    "cdc.gov",
    "who.int",
    "un.org",
    "worldbank.org",
    "europa.eu",
    "ec.europa.eu",
    "nasa.gov",
    "gov.uk",
    "whitehouse.gov",
    "congress.gov",
    "senate.gov",
    "house.gov",
    "state.gov",
    "defense.gov",
    "fda.gov",
    "epa.gov",
    "irs.gov",
    "nsf.gov",
    "noaa.gov",
    "usda.gov",
    "energy.gov",
    "justice.gov",
    "treasury.gov",
    "fbi.gov",
    "cia.gov",
    "gpo.gov",
    "loc.gov",
    "nist.gov",
    "usgs.gov",
    "census.gov",
    "bls.gov",
    "federalreserve.gov",
    "imf.org",
    "wto.org",
    "oecd.org",
    "nato.int",
    "interpol.int",
    "icj-cij.org",
    "icc-cpi.int",
    "opcw.org",
    "iaea.org",
    "unhcr.org",
    "unicef.org",
    "wfp.org",
    
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
    "skyandtelescope.org",
    "planetary.org",
    "astronomynow.com",
    "spacedaily.com",
    "spaceref.com",
    "astrobiology.com",
    "spaceindustrynews.com",
    "amnh.org",
    "spacex.com",
    "blueorigin.com",
    "rocketlabusa.com",
    "esa.int",
    "isro.gov.in",
    "jaxa.jp",
    "roscosmos.ru",
    "cnsa.gov.cn",
    "satellite-evolution.com",
    
    # Business and economics
    "bloomberg.com",
    "wsj.com",
    "ft.com",
    "cnbc.com",
    "economist.com",
    "marketwatch.com",
    "finance.yahoo.com",
    "investopedia.com",
    "morningstar.com",
    "fool.com",
    "businessinsider.com",
    "seekingalpha.com",
    "barrons.com",
    "hbr.org",
    "mckinsey.com",
    "bcg.com",
    "deloitte.com",
    "pwc.com",
    "kpmg.com",
    "ey.com",
    "weforum.org",
    "fastcompany.com",
    "inc.com",
    "entrepreneur.com",
    "fortune.com",
    "bankrate.com",
    "nerdwallet.com",
    
    # Health and medicine
    "who.int",
    "cdc.gov",
    "nih.gov",
    "mayoclinic.org",
    "healthline.com",
    "webmd.com",
    "medscape.com",
    "medicalnewstoday.com",
    "everydayhealth.com",
    "drugs.com",
    "nejm.org",
    "jamanetwork.com",
    "thelancet.com",
    "bmj.com",
    "health.harvard.edu",
    "hopkinsmedicine.org",
    "clevelandclinic.org",
    "stanfordhealthcare.org",
    "uofmhealth.org",
    "aafp.org",
    "cancer.gov",
    "cancer.org",
    "heart.org",
    "diabetes.org",
    "psychiatry.org",
    "nimh.nih.gov",
    
    # Climate, environment, and energy
    "climate.gov",
    "ipcc.ch",
    "epa.gov",
    "nature.org",
    "wwf.org",
    "greenpeace.org",
    "sierraclub.org",
    "ucsusa.org",
    "nrdc.org",
    "worldwildlife.org",
    "iea.org",
    "irena.org",
    "energy.gov",
    "eia.gov",
    "climatecentral.org",
    "carbonbrief.org",
    "insideclimatenews.org",
    "greentechmedia.com",
    "cleantechnica.com",
    "grist.org",
    "theenergymix.com",
    "renewableenergyworld.com",
    
    # Other broad info sites
    "britannica.com",
    "nationalgeographic.com",
    "howstuffworks.com",
    "smithsonianmag.com",
    "pbs.org",
    "history.com",
    "livescience.com",
    "sciencealert.com",
    "sciencenews.org",
    "phys.org",
    "discovermagazine.com",
    "mentalfloss.com",
    "thoughtco.com",
    "iflscience.com",
    "snopes.com",
    "factcheck.org",
    "politifact.com",
    "ted.com",
    "bigthink.com",
    "knowyourmeme.com",
    "dictionary.com",
    "merriam-webster.com",
    "etymonline.com",
    "grammarly.com",
    "urbandictionary.com",
    "archive.org",
    "gutenberg.org",
    "openculture.com",
    "khanacademy.org",
    "coursera.org",
    "edx.org",
    "udemy.com",
    "mitopencourseware.org",
    "ocw.mit.edu",
    "opensecrets.org",
    "wikihow.com",
    "lifehacker.com",
    "instructables.com"
]

# Rate limiting (Less critical for local Ollama, but can keep structure)
API_RATE_LIMIT = 1000 # Increase significantly for local Ollama
WEB_RATE_LIMIT = 20  # Increased to handle more domains 