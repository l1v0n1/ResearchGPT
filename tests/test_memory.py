"""
Tests for the memory module.
"""
import os
import unittest
import tempfile
import sqlite3
from pathlib import Path

from agent.memory import Memory

class TestMemory(unittest.TestCase):
    """Tests for the Memory class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory and database
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_memory.db"
        
        # Initialize the memory with the test database
        self.memory = Memory(db_path=str(self.db_path))
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()
    
    def test_initialization(self):
        """Test that the database is properly initialized."""
        # Check that the database file exists
        self.assertTrue(self.db_path.exists())
        
        # Check that the tables were created
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check conversations table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='conversations'")
            self.assertIsNotNone(cursor.fetchone())
            
            # Check facts table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='facts'")
            self.assertIsNotNone(cursor.fetchone())
            
            # Check documents table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='documents'")
            self.assertIsNotNone(cursor.fetchone())
    
    def test_write_and_read_conversation(self):
        """Test writing and reading conversation memories."""
        # Write a conversation memory
        content = {
            "session_id": "test_session",
            "role": "user",
            "content": "Test message"
        }
        memory_id = self.memory.write_memory("conversation", content)
        
        # Check that the write was successful
        self.assertGreater(memory_id, 0)
        
        # Read the memory back
        memory = self.memory.read_memory("conversation", memory_id)
        
        # Check the memory contents
        self.assertEqual(memory["session_id"], "test_session")
        self.assertEqual(memory["role"], "user")
        self.assertEqual(memory["content"], "Test message")
    
    def test_write_and_read_fact(self):
        """Test writing and reading fact memories."""
        # Write a fact memory
        content = {
            "fact": "Test fact",
            "source": "Test source",
            "confidence": 0.9
        }
        memory_id = self.memory.write_memory("fact", content)
        
        # Check that the write was successful
        self.assertGreater(memory_id, 0)
        
        # Read the memory back
        memory = self.memory.read_memory("fact", memory_id)
        
        # Check the memory contents
        self.assertEqual(memory["fact"], "Test fact")
        self.assertEqual(memory["source"], "Test source")
        self.assertEqual(memory["confidence"], 0.9)
    
    def test_write_and_read_document(self):
        """Test writing and reading document memories."""
        # Write a document memory
        content = {
            "title": "Test Document",
            "content": "Test content",
            "url": "https://example.com"
        }
        memory_id = self.memory.write_memory("document", content)
        
        # Check that the write was successful
        self.assertGreater(memory_id, 0)
        
        # Read the memory back
        memory = self.memory.read_memory("document", memory_id)
        
        # Check the memory contents
        self.assertEqual(memory["title"], "Test Document")
        self.assertEqual(memory["content"], "Test content")
        self.assertEqual(memory["url"], "https://example.com")
    
    def test_search_memory(self):
        """Test searching for memories."""
        # Write some test memories
        self.memory.write_memory("conversation", {
            "session_id": "test_session",
            "role": "user",
            "content": "Test message one"
        })
        
        self.memory.write_memory("conversation", {
            "session_id": "test_session",
            "role": "assistant",
            "content": "Test response one"
        })
        
        self.memory.write_memory("conversation", {
            "session_id": "other_session",
            "role": "user",
            "content": "Test message two"
        })
        
        # Search by content
        results = self.memory.search_memory("conversation", query="one")
        self.assertEqual(len(results), 2)
        
        # Search by session_id
        results = self.memory.search_memory("conversation", filters={"session_id": "test_session"})
        self.assertEqual(len(results), 2)
        
        # Search by role
        results = self.memory.search_memory("conversation", filters={"role": "assistant"})
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["content"], "Test response one")
    
    def test_get_conversation_history(self):
        """Test getting conversation history."""
        # Write some test conversations
        self.memory.write_memory("conversation", {
            "session_id": "test_session",
            "role": "user",
            "content": "Hello"
        })
        
        self.memory.write_memory("conversation", {
            "session_id": "test_session",
            "role": "assistant",
            "content": "Hi there!"
        })
        
        self.memory.write_memory("conversation", {
            "session_id": "test_session",
            "role": "user",
            "content": "How are you?"
        })
        
        # Get conversation history
        history = self.memory.get_conversation_history("test_session")
        
        # Check the history
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[0]["content"], "Hello")
        self.assertEqual(history[1]["role"], "assistant")
        self.assertEqual(history[2]["role"], "user")
        self.assertEqual(history[2]["content"], "How are you?")
    
    def test_delete_memory(self):
        """Test deleting memories."""
        # Write a test memory
        memory_id = self.memory.write_memory("conversation", {
            "session_id": "test_session",
            "role": "user",
            "content": "Delete me"
        })
        
        # Verify it exists
        memory = self.memory.read_memory("conversation", memory_id)
        self.assertIsNotNone(memory)
        
        # Delete the memory
        success = self.memory.delete_memory("conversation", memory_id)
        self.assertTrue(success)
        
        # Verify it's gone
        memory = self.memory.read_memory("conversation", memory_id)
        self.assertIsNone(memory)
        
        # Try to delete non-existent memory
        success = self.memory.delete_memory("conversation", 9999)
        self.assertFalse(success)

if __name__ == "__main__":
    unittest.main() 