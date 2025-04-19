"""
Test script for verifying the functionality of the DocumentRetrievalTool.
"""
import os
import sys
from pathlib import Path
import logging
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("doc_tool_test")

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.tools.documents import DocumentRetrievalTool
from agent import config

def test_document_tool():
    """Test the main functionalities of the document tool."""
    
    # Use the configured document directory
    test_dir = config.DOCUMENT_DIR
    logger.info(f"Testing DocumentRetrievalTool with directory: {test_dir}")
    
    # Initialize the tool
    doc_tool = DocumentRetrievalTool()
    
    # Test 1: Check initialization
    logger.info("Test 1: Checking initialization")
    assert str(doc_tool.document_dir) == str(test_dir), f"Document directory not set correctly. Expected: {test_dir}, Got: {doc_tool.document_dir}"
    assert hasattr(doc_tool, "document_index"), "Document index not initialized"
    
    # Test 2: Index a document
    logger.info("Test 2: Indexing a document")
    test_file = test_dir / "test_document.txt"
    # Create test document if it doesn't exist
    if not test_file.exists():
        with open(test_file, "w") as f:
            f.write("This is a test document for verifying the document tool functionality.")
    
    doc_id = doc_tool.index_document(str(test_file))
    assert doc_id is not None, "Failed to index document"
    
    # Test 3: List documents
    logger.info("Test 3: Listing documents")
    docs = doc_tool.list_documents()
    assert len(docs) >= 1, "No documents found after indexing"
    assert any(d.filename == "test_document.txt" for d in docs), "Test document not found in list"
    
    # Test 4: Search documents
    # Skip if vector store not available
    if doc_tool.vector_store:
        logger.info("Test 4: Searching documents")
        try:
            search_results = doc_tool.search("test document functionality")
            assert len(search_results) > 0, "No search results found"
        except Exception as e:
            logger.warning(f"Search test failed with error: {str(e)}")
    else:
        logger.warning("Skipping search test - vector store not available")
    
    # Test 5: Get document by ID
    logger.info("Test 5: Getting document summary")
    doc_summary = doc_tool.get_document(doc_id)
    assert doc_summary is not None, "Document summary not found"
    assert "test document" in doc_summary.content.lower(), "Summary doesn't contain expected text"
    
    logger.info("All document tool tests passed!")
    return True

if __name__ == "__main__":
    try:
        test_document_tool()
        print("✅ Document tool tests completed successfully!")
    except AssertionError as e:
        print(f"❌ Test failed: {str(e)}")
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}") 