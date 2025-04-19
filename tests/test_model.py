"""
Tests for the Ollama model module.
"""
import os
import unittest
from unittest.mock import patch, MagicMock
import requests
import requests_mock # Use requests_mock for intercepting HTTP
import json
import importlib # Import importlib for reloading

# Import modules to be reloaded
from agent import config 
from agent import model as model_module
from agent.model import ModelAPIWrapper, OllamaError, OllamaConnectionError, OllamaResponseError
from tests.mock_ollama import mock_ollama_chat_response, mock_ollama_error_response

# --- Add print for validation ---
# print(f"DEBUG: OLLAMA_MODEL at test_model.py import time: {config.OLLAMA_MODEL}")
# --- End validation print ---

# # Load environment variables for config - MOVED TO setUp
# os.environ["OLLAMA_BASE_URL"] = "http://mock-ollama:11434"
# os.environ["OLLAMA_MODEL"] = "test-model"

class TestOllamaModelAPIWrapper(unittest.TestCase):
    """Tests for the ModelAPIWrapper class using Ollama."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Set environment variables *before* reloading modules
        os.environ["OLLAMA_BASE_URL"] = "http://mock-ollama:11434"
        os.environ["OLLAMA_MODEL"] = "test-model"
        os.environ["OLLAMA_EMBED_MODEL"] = "test-embed-model" # Ensure this is set too
        
        # Reload the config and model modules to pick up test env vars
        importlib.reload(config)
        importlib.reload(model_module)
        # We need to re-import the class after reloading the module
        from agent.model import ModelAPIWrapper 

        # Commented out validation prints
        # print(f"DEBUG: os.getenv('OLLAMA_MODEL') in setUp before init: {os.getenv('OLLAMA_MODEL')}")
        self.model = ModelAPIWrapper()
        # print(f"DEBUG: self.model.model after init in setUp: {self.model.model}")
        
        self.chat_endpoint = f"{self.model.base_url}/api/chat"
        self.adapter = requests_mock.Adapter()
        self.session = requests.Session()
        self.session.mount('mock://', self.adapter) 
        # Patch requests.post globally for the duration of the test class or individual tests
        # Using requests_mock is generally cleaner for mocking HTTP calls

    def test_initialization(self):
        """Test proper initialization of the Ollama wrapper."""
        self.assertEqual(self.model.model, "test-model") # Should now be correct
        self.assertEqual(self.model.base_url, "http://mock-ollama:11434")
    
    @requests_mock.Mocker()
    def test_generate_text_success(self, m):
        """Test successful text generation."""
        mock_response_text = "This is Ollama's response."
        m.post(self.chat_endpoint, text=mock_ollama_chat_response(content=mock_response_text, model="test-model")) # Ensure mock response uses correct model
        
        result = self.model.generate_text("Test prompt")
        
        self.assertEqual(result, mock_response_text)
        self.assertEqual(m.call_count, 1)
        history = m.request_history[0]
        self.assertEqual(history.method, 'POST')
        self.assertEqual(history.url, self.chat_endpoint)
        sent_payload = json.loads(history.text)
        self.assertEqual(sent_payload['model'], "test-model") # Check correct model sent
        self.assertEqual(sent_payload['messages'][-1]['content'], "Test prompt")
        self.assertNotIn("format", sent_payload) # Should not request JSON format

    @requests_mock.Mocker()
    def test_generate_json_success(self, m):
        """Test successful JSON generation."""
        mock_json_obj = {"key": "value", "list": [1, 2]}
        mock_response_text = json.dumps(mock_json_obj)
        # Ensure mock response uses correct model
        m.post(self.chat_endpoint, text=mock_ollama_chat_response(content=mock_response_text, model="test-model"))
        
        result = self.model.generate_json("Test prompt for JSON")
        
        self.assertEqual(result, mock_json_obj)
        self.assertEqual(m.call_count, 1)
        history = m.request_history[0]
        sent_payload = json.loads(history.text)
        self.assertEqual(sent_payload['model'], "test-model") # Check correct model sent
        self.assertEqual(sent_payload['format'], "json") # Should request JSON format
        self.assertTrue(sent_payload['messages'][-1]['content'].endswith("single JSON object."))
        
    @requests_mock.Mocker()
    def test_generate_json_parsing_error(self, m):
        """Test JSON generation when Ollama returns invalid JSON."""
        invalid_json_text = "This is not JSON{"
        m.post(self.chat_endpoint, text=mock_ollama_chat_response(content=invalid_json_text, model="test-model"))
        
        result = self.model.generate_json("Test prompt for JSON")
        
        # Should return empty dict on parsing failure
        self.assertEqual(result, {})
        self.assertEqual(m.call_count, 1)
        history = m.request_history[0]
        self.assertEqual(json.loads(history.text)['format'], "json")

    @requests_mock.Mocker()
    def test_ollama_connection_error(self, m):
        """Test handling of connection errors."""
        m.post(self.chat_endpoint, exc=requests.exceptions.ConnectionError("Failed to connect"))
        
        # Test generate_text, expect empty string as fallback
        result_text = self.model.generate_text("Test prompt")
        self.assertEqual(result_text, "")
        
        # Test generate_json, expect empty dict as fallback
        result_json = self.model.generate_json("Test prompt for JSON")
        self.assertEqual(result_json, {})
        
        # The call should have been attempted multiple times due to retry
        # 2 calls * 3 attempts = 6
        self.assertEqual(m.call_count, 6) # Corrected assertion

    @requests_mock.Mocker()
    def test_ollama_response_error(self, m):
        """Test handling of non-200 responses."""
        status_code, error_response = mock_ollama_error_response(status_code=503, error_message="Model unavailable")
        m.post(self.chat_endpoint, text=error_response, status_code=status_code)
        
        # Test generate_text, expect empty string
        result_text = self.model.generate_text("Test prompt")
        self.assertEqual(result_text, "")
        
        # Test generate_json, expect empty dict
        result_json = self.model.generate_json("Test prompt for JSON")
        self.assertEqual(result_json, {})
        
        # 2 calls * 3 attempts = 6
        self.assertEqual(m.call_count, 6) # Corrected assertion

# Remove the old test class if it exists, or just replace the content
# Ensure this class is named TestOllamaModelAPIWrapper or similar

if __name__ == "__main__":
    unittest.main() 