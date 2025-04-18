"""
Document retrieval tools for the AI Research Agent.
"""
import os
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple

import numpy as np
from langchain.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import (
    TextLoader,
    PyPDFLoader,
    UnstructuredMarkdownLoader,
    JSONLoader
)
from pydantic import BaseModel, Field

from agent import config
from agent.logger import AgentLogger

logger = AgentLogger(__name__)

class DocumentChunk(BaseModel):
    """Model for a chunk of a document."""
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentRetrievalTool:
    """
    A tool for retrieving and searching documents.
    """
    
    def __init__(self, document_dir: Optional[str] = None):
        """
        Initialize the document retrieval tool.
        
        Args:
            document_dir: Directory containing documents to index.
                        If None, uses the default from config.
        """
        self.document_dir = Path(document_dir or config.DOCUMENT_DIR)
        
        # Ensure the document directory exists
        self.document_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize empty vector store
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=config.OPENAI_API_KEY
        )
        self.vector_store = None
        
        # Text splitter for chunking documents
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100
        )
        
        # Load the vector store if available
        self._load_or_create_vector_store()
        
        logger.info(f"Initialized DocumentRetrievalTool with directory: {self.document_dir}")
    
    def _load_or_create_vector_store(self):
        """
        Load the vector store from disk if it exists, or create a new one.
        """
        index_path = self.document_dir / "vector_store"
        
        if index_path.exists():
            try:
                logger.info(f"Loading vector store from {index_path}")
                self.vector_store = FAISS.load_local(
                    str(index_path),
                    self.embeddings
                )
                logger.info("Vector store loaded successfully")
            except Exception as e:
                logger.error(f"Error loading vector store: {str(e)}")
                self.vector_store = None
        
        # If loading failed or no vector store exists, create a new one
        if self.vector_store is None:
            logger.info("Creating new vector store")
            self.vector_store = FAISS.from_texts(
                ["Vector store initialization placeholder"], 
                self.embeddings
            )
            self._save_vector_store()
    
    def _save_vector_store(self):
        """
        Save the vector store to disk.
        """
        index_path = self.document_dir / "vector_store"
        
        try:
            if self.vector_store:
                logger.info(f"Saving vector store to {index_path}")
                self.vector_store.save_local(str(index_path))
                logger.info("Vector store saved successfully")
        except Exception as e:
            logger.error(f"Error saving vector store: {str(e)}")
    
    def _get_loader_for_file(self, file_path: Path):
        """
        Get the appropriate document loader for a file based on its extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            A document loader instance or None if the file type is not supported
        """
        file_extension = file_path.suffix.lower()
        
        try:
            if file_extension == '.txt':
                return TextLoader(str(file_path))
            elif file_extension == '.pdf':
                return PyPDFLoader(str(file_path))
            elif file_extension in ['.md', '.markdown']:
                return UnstructuredMarkdownLoader(str(file_path))
            elif file_extension == '.json':
                return JSONLoader(
                    file_path=str(file_path),
                    jq_schema='.',
                    text_content=False
                )
            else:
                logger.warning(f"Unsupported file extension: {file_extension}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating loader for {file_path}: {str(e)}")
            return None
    
    def index_document(self, file_path: str) -> bool:
        """
        Index a document file.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            True if indexing was successful, False otherwise
        """
        file_path = Path(file_path)
        
        # Check if file exists
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return False
        
        logger.info(f"Indexing document: {file_path}")
        
        # Get appropriate loader
        loader = self._get_loader_for_file(file_path)
        if not loader:
            return False
        
        try:
            # Load document
            documents = loader.load()
            
            # Split document into chunks
            chunks = self.text_splitter.split_documents(documents)
            
            # Add metadata about the source file
            for chunk in chunks:
                chunk.metadata["source"] = str(file_path)
                chunk.metadata["filename"] = file_path.name
                
            # Add chunks to vector store
            if chunks:
                logger.info(f"Adding {len(chunks)} chunks to vector store")
                self.vector_store.add_documents(chunks)
                
                # Save updated vector store
                self._save_vector_store()
                
                logger.info(f"Successfully indexed document: {file_path}")
                return True
            else:
                logger.warning(f"No content extracted from document: {file_path}")
                return False
                
        except Exception as e:
            logger.error(f"Error indexing document {file_path}: {str(e)}")
            return False
    
    def index_directory(self, directory: Optional[str] = None) -> int:
        """
        Index all documents in a directory.
        
        Args:
            directory: Directory to index. If None, uses the default document directory.
            
        Returns:
            Number of successfully indexed documents
        """
        if directory is None:
            directory = self.document_dir
        else:
            directory = Path(directory)
        
        if not directory.exists():
            logger.error(f"Directory not found: {directory}")
            return 0
        
        logger.info(f"Indexing all documents in {directory}")
        
        # Supported file extensions
        supported_extensions = ['.txt', '.pdf', '.md', '.markdown', '.json']
        
        # Find all document files
        document_files = []
        for ext in supported_extensions:
            document_files.extend(directory.glob(f"**/*{ext}"))
        
        # Index each document
        success_count = 0
        for file_path in document_files:
            if self.index_document(str(file_path)):
                success_count += 1
        
        logger.info(f"Indexed {success_count} out of {len(document_files)} documents")
        return success_count
    
    def search(
        self, 
        query: str, 
        max_results: int = 5
    ) -> List[DocumentChunk]:
        """
        Search for relevant document chunks using the vector store.
        
        Args:
            query: The search query
            max_results: Maximum number of results to return
            
        Returns:
            List of DocumentChunk objects
        """
        logger.info(f"Searching for: {query}")
        
        if not self.vector_store:
            logger.error("Vector store not initialized")
            return []
        
        try:
            # Search the vector store
            search_results = self.vector_store.similarity_search_with_score(
                query, 
                k=max_results
            )
            
            # Convert to DocumentChunk objects
            results = []
            for doc, score in search_results:
                # Convert score from distance to similarity (0-1 range)
                similarity = 1.0 - min(score, 1.0)
                
                chunk = DocumentChunk(
                    text=doc.page_content,
                    metadata={
                        "similarity": similarity,
                        "source": doc.metadata.get("source", ""),
                        "filename": doc.metadata.get("filename", ""),
                        **doc.metadata
                    }
                )
                results.append(chunk)
            
            logger.info(f"Found {len(results)} relevant document chunks")
            return results
            
        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}")
            return []
    
    def get_document_summary(self, file_path: str) -> str:
        """
        Generate a summary of a document.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Summary text of the document
        """
        file_path = Path(file_path)
        
        # Check if file exists
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return ""
        
        # Get appropriate loader
        loader = self._get_loader_for_file(file_path)
        if not loader:
            return ""
        
        try:
            # Load document
            documents = loader.load()
            
            # Join the content of all documents
            text = "\n\n".join([doc.page_content for doc in documents])
            
            # For long documents, truncate for the summary
            if len(text) > 10000:
                text = text[:10000] + "..."
                
            logger.info(f"Generated summary for {file_path}")
            return text
            
        except Exception as e:
            logger.error(f"Error generating summary for {file_path}: {str(e)}")
            return ""
    
    def list_documents(self) -> List[Dict[str, Any]]:
        """
        List all indexed documents.
        
        Returns:
            List of dictionaries with document information
        """
        try:
            # Get all unique document sources from vector store
            if not self.vector_store:
                return []
                
            # Get all documents from the document directory
            supported_extensions = ['.txt', '.pdf', '.md', '.markdown', '.json']
            document_files = []
            for ext in supported_extensions:
                document_files.extend(self.document_dir.glob(f"**/*{ext}"))
            
            # Create info objects for each document
            documents = []
            for file_path in document_files:
                rel_path = file_path.relative_to(self.document_dir)
                
                # Get file stats
                stats = file_path.stat()
                
                documents.append({
                    "filename": file_path.name,
                    "path": str(rel_path),
                    "full_path": str(file_path),
                    "size_bytes": stats.st_size,
                    "modified": time.ctime(stats.st_mtime),
                    "type": file_path.suffix[1:].upper()  # Remove the dot from extension
                })
            
            logger.info(f"Listed {len(documents)} documents")
            return documents
            
        except Exception as e:
            logger.error(f"Error listing documents: {str(e)}")
            return [] 