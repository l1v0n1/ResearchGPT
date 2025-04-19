"""
Mock Ollama API responses for testing.
"""
import json

def mock_ollama_chat_response(content="This is a test response.", model="llama3"):
    """Generate a mock successful Ollama /api/chat response."""
    return json.dumps({
        "model": model,
        "created_at": "2023-08-04T08:52:19.385406455Z",
        "message": {
            "role": "assistant",
            "content": content,
        },
        "done": True,
        # Include example stats, adjust if needed for specific tests
        "total_duration": 5589007333,
        "load_duration": 3012781416,
        "prompt_eval_count": 26,
        "prompt_eval_duration": 113001000,
        "eval_count": 13,
        "eval_duration": 2445041000
    })

def mock_ollama_embedding_response(model="nomic-embed-text", embedding_list=None):
    """Generate a mock successful Ollama /api/embeddings response."""
    if embedding_list is None:
        embedding_list = [0.1] * 768 # Default embedding size, adjust if needed
    return json.dumps({
        "model": model,
        "embedding": embedding_list
    })

def mock_ollama_error_response(status_code=500, error_message="Internal server error"):
    """Generate a mock Ollama error response."""
    return status_code, json.dumps({"error": error_message}) 