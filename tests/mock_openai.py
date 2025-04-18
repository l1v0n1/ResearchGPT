"""
Mock OpenAI API responses for testing.
"""
from unittest.mock import MagicMock
import json

class MockUsage:
    """Mock for API usage statistics."""
    def __init__(self, prompt_tokens=10, completion_tokens=20, total_tokens=30):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens
        
    def model_dump(self):
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens
        }

class MockCompletionChoice:
    """Mock for a completion choice."""
    def __init__(self, text="This is a test response"):
        self.message = {"content": text}
        self.index = 0
        self.finish_reason = "stop"
        
    def model_dump(self):
        return {
            "message": self.message,
            "index": self.index,
            "finish_reason": self.finish_reason
        }

class MockCompletionResponse:
    """Mock for a completion response."""
    def __init__(
        self, 
        text="This is a test response", 
        prompt_tokens=10,
        completion_tokens=20
    ):
        self.choices = [MockCompletionChoice(text)]
        self.usage = MockUsage(prompt_tokens, completion_tokens)
        self.id = "cmpl-mock123"
        self.created = 1677858242
        self.model = "gpt-4-1106-preview"
        
    def model_dump(self):
        return {
            "id": self.id,
            "created": self.created,
            "model": self.model,
            "choices": [choice.model_dump() for choice in self.choices],
            "usage": self.usage.model_dump()
        }

def mock_openai_client():
    """
    Create a mock OpenAI client that returns predetermined responses.
    
    Returns:
        A MagicMock object configured to return test responses
    """
    client = MagicMock()
    
    # Mock the chat completion create method
    chat_mock = MagicMock()
    chat_mock.create.return_value = MockCompletionResponse()
    client.chat.completions = chat_mock
    
    # Mock the JSON response
    json_response = MockCompletionResponse(
        text=json.dumps({"key": "value", "items": [1, 2, 3]})
    )
    chat_mock.create.side_effect = lambda **kwargs: (
        json_response if kwargs.get("prompt", "").endswith("JSON") else MockCompletionResponse()
    )
    
    return client 