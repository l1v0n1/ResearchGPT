# ResearchGPT

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![OpenAI](https://img.shields.io/badge/OpenAI-API-green.svg)](https://openai.com/blog/openai-api)
[![Tests](https://github.com/l1v0n1/ResearchGPT/actions/workflows/python-tests.yml/badge.svg)](https://github.com/l1v0n1/ResearchGPT/actions/workflows/python-tests.yml)
[![Lint](https://github.com/l1v0n1/ResearchGPT/actions/workflows/lint.yml/badge.svg)](https://github.com/l1v0n1/ResearchGPT/actions/workflows/lint.yml)
[![Docker](https://github.com/l1v0n1/ResearchGPT/actions/workflows/docker-build.yml/badge.svg)](https://github.com/l1v0n1/ResearchGPT/actions/workflows/docker-build.yml)

A production-ready AI agent that provides research summaries by querying internal documents and web resources.

## Features

- **Intelligent Research Planning**: Dynamically creates structured research plans based on user queries
- **Web Information Retrieval**: Searches and extracts relevant information from web sources
- **Document Analysis**: Searches through local document repositories using vector embeddings
- **Long-term Memory**: Maintains context across research sessions with persistent storage
- **Transparent Execution**: Provides clear visibility into research steps with dry-run preview mode
- **Interactive Mode**: Supports ongoing research sessions with context retention
- **Comprehensive Summaries**: Generates well-organized summaries with source citations

## Architecture

```
ResearchGPT/
├── agent/                # Core agent components
│   ├── __init__.py
│   ├── config.py         # Configuration settings
│   ├── model.py          # LLM integration
│   ├── memory.py         # Persistent memory store
│   ├── planner.py        # Planning module
│   ├── executor.py       # Execution engine
│   ├── logger.py         # Logging utilities
│   └── tools/            # Tool integrations
│       ├── __init__.py
│       ├── web.py        # Web scraping tools
│       └── documents.py  # Document retrieval tools
├── app/                  # User interfaces
│   ├── __init__.py
│   └── cli.py            # Command-line interface
├── tests/                # Testing suite
│   ├── __init__.py
│   ├── test_model.py
│   ├── test_tools.py
│   ├── test_memory.py
│   └── test_integration.py
├── benchmarks/           # Performance testing
│   └── benchmark.py
├── docs/                 # Documentation
│   ├── summary.md
│   └── checklist.md
├── .env.example          # Example environment variables
├── requirements.txt      # Dependencies
├── Dockerfile            # Container configuration
└── README.md             # This file
```

## Documentation

- [Implementation Summary](docs/summary.md) - Overview of the architecture and design principles
- [OpenAI Guide Compliance](docs/checklist.md) - Checklist showing compliance with OpenAI's agent guidelines

## Prerequisites

- Python 3.10 or higher
- OpenAI API key

## Setup Instructions

1. **Clone the repository**:
   ```bash
   git clone https://github.com/l1v0n1/ResearchGPT.git
   cd ResearchGPT
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

5. **Run the agent**:
   ```bash
   python -m app.cli
   ```

## Usage Examples

### Basic Research Query

```bash
python -m app.cli "Summarize recent developments in quantum computing"
```

### Preview Execution Plan

```bash
python -m app.cli --dry-run "Find papers about renewable energy published in 2023"
```

### Start Interactive Session

```bash
python -m app.cli --interactive
```

### Manage Documents

Index a document:
```bash
python -m app.cli --index-document path/to/document.pdf
```

List indexed documents:
```bash
python -m app.cli --list-documents
```

Index all documents in a directory:
```bash
python -m app.cli --index-directory path/to/documents/
```

## Docker Support

Build the container:
```bash
docker build -t researchgpt .
```

Run the container:
```bash
docker run -it --env-file .env researchgpt "Your research query here"
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure tests pass and add new tests for new functionality. Run tests with:
```bash
pytest
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built following OpenAI's [A Practical Guide to Building Agents](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf)
- Uses the OpenAI API for language model capabilities 