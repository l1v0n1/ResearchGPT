"""
Document retrieval tools for the AI Research Agent using Ollama embeddings.
"""
import os
import json
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
import re

import numpy as np
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
try:
    # Try the new recommended import first
    from langchain_ollama import OllamaEmbeddings
except ImportError:
    # Fall back to the deprecated import if necessary
    from langchain_community.embeddings import OllamaEmbeddings
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    UnstructuredMarkdownLoader,
    JSONLoader,
    CSVLoader,
    Docx2txtLoader,
    UnstructuredHTMLLoader
)
from pydantic import BaseModel, Field

from agent import config
from agent.logger import AgentLogger

logger = AgentLogger(__name__)

# Default config values if not found in config module
DEFAULT_EMBEDDING_MODEL = "nomic-embed-text"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_DOCUMENTS_PATH = "documents"

class DocumentChunk(BaseModel):
    """Model for a chunk of a document."""
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentIndexEntry(BaseModel):
    """Model for document index entry."""
    id: str
    filename: str
    path: str
    type: str  # pdf, txt, html, md, etc.
    title: Optional[str] = None
    created_at: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentSearchResult(BaseModel):
    """Model for document search result."""
    document_id: str
    filename: str
    content: str
    score: float = 0.0
    page_number: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentSummary(BaseModel):
    """Model for document summary."""
    document_id: str
    filename: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentRetrievalTool:
    """
    A tool for retrieving and searching documents using Ollama embeddings.
    """
    
    # Supported file types mapping to their loaders
    SUPPORTED_FILE_TYPES = {
        # Document formats
        '.txt': TextLoader,
        '.pdf': PyPDFLoader,
        '.csv': CSVLoader,
        '.md': UnstructuredMarkdownLoader,
        '.docx': Docx2txtLoader,
        '.html': UnstructuredHTMLLoader,
        '.htm': UnstructuredHTMLLoader,
        '.json': JSONLoader,
        
        # Programming languages
        '.py': TextLoader,    # Python
        '.js': TextLoader,    # JavaScript
        '.ts': TextLoader,    # TypeScript
        '.jsx': TextLoader,   # React JSX
        '.tsx': TextLoader,   # React TSX
        '.java': TextLoader,  # Java
        '.c': TextLoader,     # C
        '.cpp': TextLoader,   # C++
        '.h': TextLoader,     # C/C++ header
        '.cs': TextLoader,    # C#
        '.go': TextLoader,    # Go
        '.rb': TextLoader,    # Ruby
        '.php': TextLoader,   # PHP
        '.swift': TextLoader, # Swift
        '.kt': TextLoader,    # Kotlin
        '.rs': TextLoader,    # Rust
        '.sql': TextLoader,   # SQL
        '.sh': TextLoader,    # Shell
        '.yaml': TextLoader,  # YAML
        '.yml': TextLoader,   # YAML
        '.toml': TextLoader,  # TOML
        '.xml': TextLoader,   # XML
        '.css': TextLoader,   # CSS
        '.scss': TextLoader,  # SCSS
        '.less': TextLoader,  # LESS
    }
    
    # Default chunking parameters
    DEFAULT_CHUNK_SIZE = 1000
    DEFAULT_CHUNK_OVERLAP = 200
    
    def __init__(self, document_dir: Optional[str] = None):
        """
        Initialize the document retrieval tool.
        
        Args:
            document_dir: Directory where documents are stored
        """
        self.document_dir = Path(document_dir or getattr(config, 'DOCUMENT_DIR', DEFAULT_DOCUMENTS_PATH))
        self.vector_store_path = self.document_dir / "vector_store"
        
        # Create directory if it doesn't exist
        os.makedirs(self.document_dir, exist_ok=True)
        
        # Initialize index storage
        self.index_path = self.document_dir / 'index.json'
        self.document_index = self._load_document_index()
        
        # Initialize vector store for search
        self.vector_store = None
        self._load_vector_store()
        
        logger.info(f"Initialized DocumentRetrievalTool with {len(self.document_index)} indexed documents")
    
    def _get_file_hash(self, file_path: str) -> str:
        """
        Generate a hash from file content to serve as a unique ID.
        
        Args:
            file_path: Path to the file
            
        Returns:
            SHA-256 hash of the file content
        """
        try:
            with open(file_path, 'rb') as f:
                file_hash = hashlib.sha256()
                # Read and update hash in chunks for large files
                for byte_block in iter(lambda: f.read(4096), b""):
                    file_hash.update(byte_block)
                return file_hash.hexdigest()
        except Exception as e:
            logger.error(f"Error generating hash for {file_path}: {str(e)}")
            # Fallback to using path and modification time
            stat = os.stat(file_path)
            return hashlib.sha256(f"{file_path}:{stat.st_mtime}".encode()).hexdigest()
    
    def _load_document_index(self) -> Dict[str, DocumentIndexEntry]:
        """
        Load the document index from disk.
        
        Returns:
            Dictionary of document IDs to DocumentIndexEntry objects
        """
        if not self.index_path.exists():
            return {}
            
        try:
            with open(self.index_path, 'r') as f:
                index_data = json.load(f)
                
            # Convert to DocumentIndexEntry objects
            return {
                doc_id: DocumentIndexEntry(**doc_data)
                for doc_id, doc_data in index_data.items()
            }
        except Exception as e:
            logger.error(f"Error loading document index: {str(e)}")
            # If index is corrupted, start with an empty index
            return {}
    
    def _save_document_index(self):
        """Save the document index to disk."""
        try:
            index_data = {
                doc_id: doc_entry.model_dump()
                for doc_id, doc_entry in self.document_index.items()
            }
            
            with open(self.index_path, 'w') as f:
                json.dump(index_data, f, indent=2)
                
            logger.info(f"Document index saved with {len(index_data)} entries")
        except Exception as e:
            logger.error(f"Error saving document index: {str(e)}")
    
    def _load_vector_store(self):
        """
        Load the FAISS vector store if it exists.
        """
        if self.vector_store_path.exists():
            try:
                embeddings = self._get_embeddings()
                if not embeddings:
                    logger.warning("Could not initialize embeddings, vector search will be unavailable")
                    return
                    
                self.vector_store = FAISS.load_local(
                    str(self.vector_store_path),
                    embeddings,
                    allow_dangerous_deserialization=True  # Required for security in newer FAISS versions
                )
                logger.info(f"Loaded vector store from {self.vector_store_path}")
            except Exception as e:
                logger.error(f"Error loading vector store: {str(e)}")
                # If loading fails, we'll rebuild it when needed
                self.vector_store = None
    
    def _get_embeddings(self):
        """
        Get embeddings model with error handling.
        
        Returns:
            OllamaEmbeddings instance or None if initialization fails
        """
        try:
            return OllamaEmbeddings(
                model=getattr(config, 'EMBEDDING_MODEL', DEFAULT_EMBEDDING_MODEL),
                base_url=getattr(config, 'OLLAMA_BASE_URL', DEFAULT_OLLAMA_BASE_URL)
            )
        except Exception as e:
            logger.error(f"Error initializing embeddings: {str(e)}")
            return None
            
    def _extract_document_content(self, file_path: str) -> List[Document]:
        """
        Extract content from a document file.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            List of Document objects
        """
        ext = os.path.splitext(file_path)[1].lower()
        
        # Check if file type is supported
        if ext not in self.SUPPORTED_FILE_TYPES:
            logger.warning(f"Unsupported file type: {ext}")
            return []
            
        loader_class = self.SUPPORTED_FILE_TYPES[ext]
        
        try:
            # Special handling for PDF files to improve extraction
            if ext == '.pdf':
                docs = self._extract_pdf_content(file_path)
            # Special handling for JSON files
            elif ext == '.json':
                docs = self._extract_json_content(file_path)
            # Special handling for code files
            elif ext in ['.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.c', '.cpp', '.h', '.cs', 
                         '.go', '.rb', '.php', '.swift', '.kt', '.rs', '.sql', '.sh', 
                         '.yaml', '.yml', '.toml', '.xml', '.css', '.scss', '.less']:
                docs = self._extract_code_content(file_path, ext)
            else:
                # Use the appropriate loader for other file types
                loader = loader_class(file_path)
                docs = loader.load()
            
            # Add source path to metadata
            for doc in docs:
                if not hasattr(doc, 'metadata'):
                    doc.metadata = {}
                doc.metadata["source"] = file_path
                
            logger.info(f"Extracted {len(docs)} document pages from {file_path}")
            return docs
        except Exception as e:
            logger.error(f"Error extracting content from {file_path}: {str(e)}")
            # Try a fallback approach: read as text if possible
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                doc = Document(
                    page_content=content, 
                    metadata={"source": file_path}
                )
                return [doc]
            except Exception as e2:
                logger.error(f"Fallback extraction failed for {file_path}: {str(e2)}")
                return []

    def _extract_pdf_content(self, file_path: str) -> List[Document]:
        """
        Enhanced PDF content extraction.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            List of Document objects
        """
        try:
            loader = PyPDFLoader(file_path)
            documents = loader.load()
            
            # Post-process to clean up the text
            for doc in documents:
                # Remove multiple spaces
                doc.page_content = re.sub(r'\s+', ' ', doc.page_content)
                # Remove empty lines
                doc.page_content = re.sub(r'\n\s*\n', '\n', doc.page_content)
                # Clean up PDF artifacts
                doc.page_content = re.sub(r'(\w+)-\s+(\w+)', r'\1\2', doc.page_content)
                
            return documents
        except Exception as e:
            logger.error(f"Error in PDF extraction for {file_path}: {str(e)}")
            # Try a more aggressive fallback if needed
            return []
            
    def _extract_json_content(self, file_path: str) -> List[Document]:
        """
        Special handling for JSON files.
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            List of Document objects
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Convert JSON to string for simple indexing
            content = json.dumps(data, indent=2)
            
            # Create a document
            doc = Document(
                page_content=content,
                metadata={"source": file_path}
            )
            
            return [doc]
        except Exception as e:
            logger.error(f"Error in JSON extraction for {file_path}: {str(e)}")
            return []
            
    def _extract_code_content(self, file_path: str, extension: str) -> List[Document]:
        """
        Enhanced code file content extraction with special handling for programming files.
        
        Args:
            file_path: Path to the code file
            extension: File extension (with dot)
            
        Returns:
            List of Document objects
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            # Get the programming language from the extension
            language = extension.lstrip('.').lower()
            
            # Handle special cases for language names
            language_map = {
                'py': 'python',
                'js': 'javascript',
                'ts': 'typescript',
                'jsx': 'javascript react',
                'tsx': 'typescript react',
                'cpp': 'c++',
                'h': 'c/c++ header',
                'cs': 'c#',
                'rb': 'ruby',
                'kt': 'kotlin',
                'rs': 'rust',
                'sh': 'shell/bash',
            }
            
            if language in language_map:
                language = language_map[language]
                
            # Count lines of code and detect imports/packages
            lines = content.split('\n')
            line_count = len(lines)
            
            # Create metadata with code-specific information
            filename = os.path.basename(file_path)
            metadata = {
                "source": file_path,
                "language": language,
                "filename": filename,
                "line_count": line_count,
                "file_size_bytes": os.path.getsize(file_path),
                "content_type": "code"
            }
            
            # Try to detect imports/packages/includes for popular languages
            imports = []
            
            # Python imports
            if language == 'python':
                for line in lines:
                    if line.strip().startswith('import ') or line.strip().startswith('from '):
                        imports.append(line.strip())
                        
            # JavaScript/TypeScript imports
            elif language in ['javascript', 'typescript', 'javascript react', 'typescript react']:
                for line in lines:
                    if line.strip().startswith('import ') or line.strip().startswith('require('):
                        imports.append(line.strip())
                        
            # Java/Kotlin imports
            elif language in ['java', 'kotlin']:
                for line in lines:
                    if line.strip().startswith('import '):
                        imports.append(line.strip())
            
            if imports:
                metadata["imports"] = imports[:10]  # Limit to first 10 imports
                
            # Create document
            doc = Document(
                page_content=content,
                metadata=metadata
            )
            
            return [doc]
            
        except Exception as e:
            logger.error(f"Error in code extraction for {file_path}: {str(e)}")
            # Fallback to basic text loading
            loader = TextLoader(file_path)
            try:
                return loader.load()
            except:
                return []

    def _chunk_document(self, documents: List[Document], 
                       chunk_size: Optional[int] = None, 
                       chunk_overlap: Optional[int] = None) -> List[Document]:
        """
        Split documents into smaller chunks for better indexing.
        
        Args:
            documents: List of Document objects
            chunk_size: Size of each chunk (default: self.DEFAULT_CHUNK_SIZE)
            chunk_overlap: Overlap between chunks (default: self.DEFAULT_CHUNK_OVERLAP)
            
        Returns:
            List of Document chunks
        """
        if not documents:
            return []
            
        chunk_size = chunk_size or self.DEFAULT_CHUNK_SIZE
        chunk_overlap = chunk_overlap or self.DEFAULT_CHUNK_OVERLAP
        
        # Create a splitter with smart defaults based on content type
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        try:
            # Split the documents into chunks
            chunks = splitter.split_documents(documents)
            return chunks
        except Exception as e:
            logger.error(f"Error chunking documents: {str(e)}")
            # Return original documents as fallback
            return documents

    def index_document(self, file_path: str) -> Optional[str]:
        """
        Index a document for search and retrieval.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            ID of the indexed document, or None if indexing failed
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return None
            
        # Generate a unique ID for the document
        doc_id = self._get_file_hash(str(file_path))
        
        # Extract file type and other metadata
        filename = file_path.name
        file_ext = file_path.suffix.lower()
        file_type = file_ext.lstrip('.')
        
        # Create index entry
        index_entry = DocumentIndexEntry(
            id=doc_id,
            filename=filename,
            path=str(file_path.absolute()),
            type=file_type,
            created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            metadata={
                "size_bytes": file_path.stat().st_size,
                "last_modified": time.ctime(file_path.stat().st_mtime)
            }
        )
        
        # Extract document content
        logger.info(f"Extracting content from {filename}")
        doc_pages = self._extract_document_content(str(file_path))
        
        if not doc_pages:
            logger.error(f"Failed to extract content from {file_path}")
            return None
            
        # Chunk the document for better search
        doc_chunks = self._chunk_document(doc_pages)
        
        if not doc_chunks:
            logger.error(f"Failed to chunk document: {file_path}")
            return None
            
        # Add to vector store
        embeddings = self._get_embeddings()
        if not embeddings:
            logger.warning("Could not initialize embeddings, document will be indexed but not searchable")
        else:
            try:
                # Initialize vector store if needed
                if self.vector_store is None:
                    self.vector_store = FAISS.from_documents(
                        doc_chunks, 
                        embeddings
                    )
                else:
                    # Add to existing vector store
                    self.vector_store.add_documents(doc_chunks)
                
                # Save vector store
                self.vector_store_path.parent.mkdir(parents=True, exist_ok=True)
                self.vector_store.save_local(str(self.vector_store_path))
                logger.info(f"Vector store saved to {self.vector_store_path}")
            except Exception as e:
                logger.error(f"Error adding document to vector store: {str(e)}")
                # Continue with index update even if vector store fails
        
        # Update index
        self.document_index[doc_id] = index_entry
        self._save_document_index()
        
        logger.info(f"Document indexed successfully: {filename} (ID: {doc_id})")
        return doc_id

    def search(self, query: str, num_results: int = 5) -> List[DocumentSearchResult]:
        """
        Search for documents using vector store.
        
        Args:
            query: Search query
            num_results: Number of results to return
            
        Returns:
            List of document search results
        """
        if self.vector_store is None:
            logger.error("Vector store not initialized")
            return []
        
        try:
            docs_and_scores = self.vector_store.similarity_search_with_score(
                query, 
                k=num_results
            )
            
            results = []
            for doc, score in docs_and_scores:
                # Find document ID from the source path
                source_path = doc.metadata.get('source', '')
                doc_id = None
                
                # Try to find by exact path
                for id, entry in self.document_index.items():
                    if entry.path == source_path or Path(source_path).resolve() == Path(entry.path).resolve():
                        doc_id = id
                        break
                
                # If not found by exact path, try a more flexible approach
                if doc_id is None:
                    source_filename = Path(source_path).name
                    for id, entry in self.document_index.items():
                        if entry.filename == source_filename:
                            doc_id = id
                            break
                
                # If still not found, log and skip
                if doc_id is None:
                    logger.warning(f"Document not found in index: {source_path}")
                    # Create a result with limited information
                    result = DocumentSearchResult(
                        document_id="unknown",
                        filename=Path(source_path).name,
                        content=doc.page_content,
                        score=float(score),
                        page_number=doc.metadata.get('page'),
                        metadata=doc.metadata
                    )
                else:
                    result = DocumentSearchResult(
                        document_id=doc_id,
                        filename=self.document_index[doc_id].filename,
                        content=doc.page_content,
                        score=float(score),
                        page_number=doc.metadata.get('page'),
                        metadata=doc.metadata
                    )
                
                results.append(result)
                
            return results
        except Exception as e:
            logger.error(f"Error during search: {str(e)}")
            return []

    def get_document(self, document_id: str) -> Optional[DocumentSummary]:
        """
        Get document summary by ID.
        
        Args:
            document_id: ID of the document (can be partial ID)
            
        Returns:
            Document summary, or None if document not found
        """
        # Handle partial document ID (like "a8b8685a...")
        if document_id.endswith('...') or len(document_id) < 64:
            # Find matching document with partial ID
            for doc_id in self.document_index:
                if doc_id.startswith(document_id.rstrip('.')):
                    document_id = doc_id
                    break
                    
        if document_id not in self.document_index:
            logger.error(f"Document not found: {document_id}")
            return None
            
        doc_entry = self.document_index[document_id]
        
        # Extract content for summary
        doc_pages = self._extract_document_content(doc_entry.path)
        
        if not doc_pages:
            logger.error(f"Failed to extract content from {doc_entry.path}")
            return None
            
        # Combine the first few pages for a summary
        content = "\n\n".join([page.page_content for page in doc_pages[:3]])
        
        # Truncate if too long
        if len(content) > 1000:
            content = content[:1000] + "..."
            
        return DocumentSummary(
            document_id=document_id,
            filename=doc_entry.filename,
            content=content,
            metadata=doc_entry.metadata
        )
        
    def list_documents(self) -> List[DocumentIndexEntry]:
        """
        List all indexed documents.
        
        Returns:
            List of document index entries
        """
        return list(self.document_index.values()) 