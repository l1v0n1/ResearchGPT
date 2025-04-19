# ResearchGPT - Implementation Summary

This document explains the architecture and implementation details of the ResearchGPT agent, which provides comprehensive research capabilities using local LLMs via Ollama.

## 1. Agent Architecture Overview

The agent follows a modular architecture with clear separation of concerns:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  User Interface │────▶│     Planner     │────▶│    Executor     │
│       (CLI)     │     │                 │     │                 │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │                        │
                               │                        │
                               ▼                        ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │                 │     │                 │
                        │  Ollama Wrapper │     │      Tools      │
                        │                 │     │                 │
                        │                 │     │                 │
                        └─────────────────┘     └─────────────────┘
                               │                        │
                               │                        ▼
                               │                ┌─────────────────┐
                               │                │                 │
                               └───────────────▶│     Memory      │
                                                │                 │
                                                │                 │
                                                └─────────────────┘
```

## 2. Key Components

### 2.1. Planning and Execution Pipeline

The agent uses a clear planning and execution pipeline:

1. **Planning** (`agent/planner.py`): 
   - Uses Ollama LLM to generate a structured research plan
   - Validates steps to ensure they have the required parameters
   - Provides fallback mechanisms when planning fails

2. **Execution** (`agent/executor.py`):
   - Executes each step in the plan by calling the appropriate tools
   - Collects and manages intermediate results
   - Generates a final summary based on all collected information

### 2.2. Tools Integration

The agent includes specialized tools:

1. **Web Research** (`agent/tools/web.py`):
   - Search engine integration (Google API or direct web scraping)
   - Web page fetching and content extraction
   - Link extraction for further research
   - Domain allowlisting for security

2. **Document Retrieval** (`agent/tools/documents.py`):
   - Vector-based search using Ollama embeddings
   - Document indexing and parsing
   - Multiple file format support (text, PDF, Markdown, JSON, code files)
   - Enhanced error handling and content extraction

Both tool modules implement robust error handling, rate limiting, and validation.

### 2.3. Memory and Knowledge Management

The agent implements comprehensive knowledge management:

- **Persistent Memory** (`agent/memory.py`):
  - Stores conversation history, facts, and document references
  - Uses SQLite for reliable storage
  - Maintains context across interactions

- **Summary Management** (`app/cli.py`):
  - Saves research summaries with meaningful filenames based on queries
  - Organizes summaries with YAML frontmatter containing metadata
  - Provides commands to list and view saved summaries
  - Creates a knowledge base of past research

### 2.4. Ollama Integration

The agent uses a custom Ollama wrapper (`agent/model.py`) that:

- Abstracts the Ollama API interactions
- Implements retry mechanisms for reliability
- Supports both text generation and embeddings
- Handles different model types and parameters
- Falls back gracefully when model services are unavailable

### 2.5. User Interface

The CLI interface (`app/cli.py`) provides:

- Interactive and single-query modes
- Plan preview functionality (with --dry-run flag)
- Document indexing and management
- Summary browsing and viewing
- Rich text output using the `rich` library
- Syntax highlighting for code documents

## 3. Safety and Security Considerations

The agent implements several safety mechanisms:

1. **Input Validation**: User queries are validated and sanitized
2. **URL Validation**: Web scraping only occurs on allowed domains
3. **Rate Limiting**: Both API calls and web requests are rate-limited
4. **Execution Preview**: Users can review plans before execution with `--dry-run`
5. **Error Handling**: Robust error handling throughout the codebase

## 4. Performance Optimizations

Performance considerations include:

1. **Efficient Memory Usage**: SQLite database with proper indexing
2. **Vector Search**: FAISS library for efficient document retrieval
3. **Document Chunking**: Smart document splitting for better search
4. **Error Recovery**: Fallback mechanisms for extraction failures

## 5. Extensibility

The agent is designed for extensibility:

1. **Modular Architecture**: Each component can be extended or replaced
2. **Pluggable Tools**: New tools can be added by implementing the appropriate interfaces
3. **Configuration System**: Centralized configuration in `agent/config.py`
4. **Clear Interfaces**: Well-defined input/output contracts between components

## 6. Testing

Test coverage includes:

1. **Unit Tests**: For individual components
2. **Tool-specific Tests**: Dedicated test files for document and web tools
3. **Model Integration Tests**: To verify Ollama interaction

## 7. Recent Enhancements

The latest version includes several key improvements:

1. **Enhanced Document Handling**:
   - Improved PDF content extraction
   - Better code file parsing with language detection
   - Robust error handling for document processing

2. **Knowledge Management**:
   - Summary saving with meaningful filenames
   - YAML frontmatter for metadata
   - Commands to browse and view past research

3. **User Experience**:
   - Syntax highlighting for code documents
   - Better command structure in interactive mode
   - More detailed error reporting

## 8. Conclusion

ResearchGPT combines the power of local language models with specialized research tools to create a powerful, privacy-focused research assistant. The modular design ensures it can be easily extended and maintained while providing comprehensive research capabilities to users. 