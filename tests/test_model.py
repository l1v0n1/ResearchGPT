"""
Tests for the model module.
"""
import os
import unittest
from unittest.mock import patch, MagicMock

from agent.model import ModelAPIWrapper

class TestModelAPIWrapper(unittest.TestCase):
    """Tests for the ModelAPIWrapper class."""
    
    @patch("agent.model.OpenAI")
    def setUp(self, mock_openai):
        """Set up test fixtures."""
        self.mock_openai = mock_openai
        self.mock_client = MagicMock()
        mock_openai.return_value = self.mock_client
        
        os.environ["OPENAI_API_KEY"] = "test_key"
        self.model = ModelAPIWrapper()
    
    def test_initialization(self):
        """Test proper initialization of the wrapper."""
        self.assertEqual(self.model.model, "gpt-4-1106-preview")
        self.mock_openai.assert_called_once()
    
    @patch("agent.model.ModelAPIWrapper._call_api")
    def test_generate_text(self, mock_call_api):
        """Test text generation."""
        # Set up mock
        mock_call_api.return_value = {
            "choices": [{"message": {"content": "Test response"}}]
        }
        
        # Call method
        result = self.model.generate_text("Test prompt")
        
        # Check results
        self.assertEqual(result, "Test response")
        mock_call_api.assert_called_once()
        
        # Check messages format
        args, kwargs = mock_call_api.call_args
        messages = args[0]
        self.assertEqual(messages[-1]["role"], "user")
        self.assertEqual(messages[-1]["content"], "Test prompt")
    
    @patch("agent.model.ModelAPIWrapper._call_api")
    def test_generate_json(self, mock_call_api):
        """Test JSON generation."""
        # Set up mock
        mock_call_api.return_value = {
            "choices": [{"message": {"content": '{"key": "value"}'}}]
        }
        
        # Call method
        result = self.model.generate_json("Test prompt")
        
        # Check results
        self.assertIsInstance(result, dict)
        self.assertEqual(result["key"], "value")
        mock_call_api.assert_called_once()
    
    @patch("agent.model.ModelAPIWrapper._call_api")
    def test_generate_json_handles_invalid_json(self, mock_call_api):
        """Test handling of invalid JSON response."""
        # Set up mock with invalid JSON
        mock_call_api.return_value = {
            "choices": [{"message": {"content": "Not valid JSON"}}]
        }
        
        # Call method
        result = self.model.generate_json("Test prompt")
        
        # Check results - should return empty dict on error
        self.assertIsInstance(result, dict)
        self.assertEqual(result, {})

if __name__ == "__main__":
    unittest.main() 