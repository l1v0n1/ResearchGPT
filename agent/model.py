"""
Ollama model wrapper for the AI Research Agent.
"""
import time
import json
import requests # Use requests for HTTP calls
from typing import Dict, List, Any, Optional, Union, Tuple

# No longer using openai library
# import openai
# from openai import OpenAI

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from agent import config
from agent.logger import AgentLogger

logger = AgentLogger(__name__)

# Define exceptions for Ollama
class OllamaError(Exception):
    """Base exception for Ollama API errors."""
    pass

class OllamaConnectionError(OllamaError):
    """Exception for connection issues with the Ollama server."""
    pass

class OllamaResponseError(OllamaError):
    """Exception for non-200 responses from the Ollama API."""
    def __init__(self, status_code, message):
        self.status_code = status_code
        super().__init__(f"Ollama API request failed with status {status_code}: {message}")

class ModelAPIWrapper:
    """
    A wrapper for the Ollama API that handles requests, retries, and basic processing.
    Uses the /api/chat endpoint.
    """
    
    def __init__(self):
        """
        Initialize the Ollama API wrapper with settings from config.
        """
        self.base_url = config.OLLAMA_BASE_URL
        self.chat_endpoint = f"{self.base_url}/api/chat"
        self.model = config.OLLAMA_MODEL
        self.temperature = config.TEMPERATURE
        self.request_timeout = config.OLLAMA_REQUEST_TIMEOUT
        self.max_tokens = config.MAX_TOKENS # Keep for potential context management

        # Rate limiting (optional for local Ollama, but kept for structure)
        self.request_count = 0
        self.request_start_time = time.time()
        self.rate_limit = config.API_RATE_LIMIT
        
        logger.info(f"Initialized ModelAPIWrapper for Ollama model {self.model} at {self.base_url}")
    
    def _check_rate_limit(self):
        """
        Check if the current request would exceed the rate limit.
        If necessary, sleep to stay within rate limits.
        (Less critical for local Ollama, adjust self.rate_limit in config)
        """
        current_time = time.time()
        elapsed = current_time - self.request_start_time
        
        if elapsed >= 60:
            self.request_count = 0
            self.request_start_time = current_time
            return
        
        if self.request_count >= self.rate_limit:
            sleep_time = 60 - elapsed
            logger.warning(f"Rate limit ({self.rate_limit}/min) reached. Sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
            self.request_count = 0
            self.request_start_time = time.time()
        
    @retry(
        retry=retry_if_exception_type((requests.exceptions.ConnectionError, OllamaConnectionError, OllamaResponseError)),
        wait=wait_exponential(multiplier=1, min=2, max=30), # Shorter max wait for local
        stop=stop_after_attempt(3) # Fewer attempts for local
    )
    def _call_api(self, messages: List[Dict[str, str]], format_json: bool = False, **kwargs) -> Dict[str, Any]:
        """
        Make a request to the Ollama /api/chat endpoint with retry logic.
        
        Args:
            messages: A list of message dictionaries for the conversation.
            format_json: If True, requests JSON format from Ollama.
            **kwargs: Additional parameters for the Ollama API.
            
        Returns:
            The Ollama API response content as a dictionary.
            
        Raises:
            OllamaConnectionError: If connection to Ollama fails.
            OllamaResponseError: If Ollama returns a non-200 status code.
        """
        self._check_rate_limit() 
        self.request_count += 1
        start_time = time.time()

        headers = {"Content-Type": "application/json"}
        payload = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "stream": False, # Don't stream for this wrapper
            "options": {
                "temperature": kwargs.get("temperature", self.temperature),
                # Add other Ollama options if needed (e.g., num_ctx for context window)
                # "num_ctx": self.max_tokens 
            }
        }

        if format_json:
            payload["format"] = "json"

        logger.debug(f"Sending request to Ollama: {json.dumps(payload, indent=2)}")

        try:
            response = requests.post(
                self.chat_endpoint,
                headers=headers,
                data=json.dumps(payload),
                timeout=self.request_timeout
            )
            
            elapsed = time.time() - start_time

            if response.status_code == 200:
                response_data = response.json()
                tokens_used = response_data.get("eval_count", 0) # Ollama uses eval_count
                logger.debug(
                    f"Ollama request successful",
                    elapsed_time=f"{elapsed:.2f}s",
                    tokens_evaluated=tokens_used
                )
                return response_data
            else:
                error_msg = response.text
                try: # Try to parse JSON error
                    error_json = response.json()
                    error_msg = error_json.get("error", response.text)
                except json.JSONDecodeError:
                    pass # Keep original text if not JSON
                    
                logger.error(
                    f"Ollama request failed with status {response.status_code}: {error_msg}",
                    elapsed_time=f"{elapsed:.2f}s"
                )
                raise OllamaResponseError(response.status_code, error_msg)
                
        except requests.exceptions.RequestException as e:
            elapsed = time.time() - start_time
            logger.error(
                f"Ollama connection failed: {str(e)}",
                elapsed_time=f"{elapsed:.2f}s",
                error_type=type(e).__name__
            )
            raise OllamaConnectionError(f"Connection error: {str(e)}") from e
        except Exception as e: # Catch other potential errors
            elapsed = time.time() - start_time
            logger.error(
                f"Unexpected error during Ollama request: {str(e)}",
                elapsed_time=f"{elapsed:.2f}s",
                error_type=type(e).__name__
            )
            raise
    
    def generate_text(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> str:
        """
        Generate text using the Ollama chat completions API.
        
        Args:
            prompt: The user prompt to send to the model.
            system_message: Optional system message to set context.
            conversation_history: Optional conversation history.
            **kwargs: Additional parameters to pass to the Ollama API.
            
        Returns:
            The generated text as a string.
        """
        messages = []
        
        if system_message:
            messages.append({"role": "system", "content": system_message})
        else:
            # Add a default system message with date check
            current_year = time.strftime("%Y")
            current_date = time.strftime("%B %d, %Y")
            
            date_reminder = f"Today's date is {current_date}. When discussing 'latest' or recent news, " \
                           f"ensure all dates referenced are accurate and not in the future. Always use " \
                           f"the current year ({current_year}) for recent events unless explicitly specified otherwise."
            
            default_system = f"""# ResearchGPT - Advanced Research AI Assistant

## Core Purpose
You are {config.AGENT_NAME}, an advanced AI research assistant designed to provide comprehensive, accurate, and well-sourced information on a wide range of topics. Your primary objective is to {config.AGENT_OBJECTIVE} 

## Capabilities
- **Comprehensive Research**: Search and analyze information from diverse web sources and local documents
- **Intelligent Reasoning**: Break down complex topics into coherent, structured responses
- **Critical Analysis**: Assess the reliability of sources and present balanced viewpoints
- **Adaptive Learning**: Build on previous interactions to provide increasingly relevant information
- **Time-Awareness**: {date_reminder}

## Research Methodology
1. **Understanding the Query**: Carefully analyze user questions to identify key information needs
2. **Source Selection**: Access appropriate sources based on topic requirements
3. **Information Synthesis**: Combine data from multiple reliable sources for comprehensive coverage
4. **Verification**: Cross-check facts across multiple sources where possible
5. **Structured Presentation**: Organize findings in a clear, logical format
6. **Citation**: Properly attribute information to original sources

## Knowledge Management
- Maintain memory of previous interactions for contextual awareness
- Store and retrieve research summaries as needed
- Organize information hierarchically to facilitate comprehensive understanding
- Present information in useful formats based on topic and complexity

## Research Ethics
- Prioritize reliable, peer-reviewed sources when available
- Present balanced viewpoints and acknowledge controversies
- Distinguish between facts, consensus views, and more speculative claims
- Acknowledge limitations in available information
- Maintain intellectual humility and avoid overconfidence

## Interaction Style
- Clear and concise in communication
- Adaptable to different levels of detail based on user needs
- Proactive in providing relevant context beyond direct questions
- Transparent about research methods and sourcing

{config.AGENT_DESCRIPTION}

IMPORTANT TIME CONTEXT: {date_reminder}
"""
            
            messages.append({"role": "system", "content": default_system})
        
        if conversation_history:
            messages.extend(conversation_history)
        
        messages.append({"role": "user", "content": prompt})
        
        try:
            response_data = self._call_api(messages, format_json=False, **kwargs)
            
            # Extract the generated text from Ollama response
            # Ollama's chat response format has the content in response['message']['content']
            generated_text = response_data.get("message", {}).get("content", "")
            
            if not generated_text:
                 logger.warning("Ollama response did not contain generated text.", response=response_data)
            
            return generated_text.strip()
            
        except (OllamaError, Exception) as e:
            logger.error(f"Failed to generate text with Ollama: {str(e)}")
            # Return empty string or raise exception based on desired handling
            return "" 
    
    def generate_json(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate structured JSON output using Ollama. 
        Note: Relies on the model's ability to follow JSON instructions and Ollama's format=json.
        
        Args:
            prompt: The user prompt to send to the model.
            system_message: Optional system message to set context.
            **kwargs: Additional parameters to pass to the Ollama API.
            
        Returns:
            The generated content as a Python dictionary, or {} if parsing fails.
        """
        if system_message is None:
            system_message = (
                f"You are {config.AGENT_NAME}. "
                f"Your objective is to {config.AGENT_OBJECTIVE} "
                f"{config.AGENT_DESCRIPTION} "
                f"Respond ONLY with valid JSON. Do not include any other text, explanations, or markdown formatting." 
            )
        
        # Add explicit instruction for JSON in the user prompt as well
        json_prompt = prompt + "\n\nRespond ONLY with valid JSON. The entire response must be a single JSON object."
        
        messages = []
        messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": json_prompt})
        
        try:
            # Request JSON format from Ollama
            response_data = self._call_api(messages, format_json=True, **kwargs)
            response_text = response_data.get("message", {}).get("content", "")

            if not response_text:
                logger.error("Ollama JSON response was empty.")
                return {}
            
            # Parse the response text as JSON
            # Ollama's format=json should ideally return only JSON, but parse defensively
            try:
                # Sometimes models still wrap in ```json ... ``` despite instructions
                if response_text.startswith("```json"):
                    response_text = response_text.split("```json", 1)[1]
                if response_text.endswith("```"):
                    response_text = response_text.rsplit("```", 1)[0]
                
                return json.loads(response_text.strip())
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Ollama JSON response: {str(e)}", raw_response=response_text)
                return {}
                
        except (OllamaError, Exception) as e:
            logger.error(f"Failed to generate JSON with Ollama: {str(e)}")
            return {} 