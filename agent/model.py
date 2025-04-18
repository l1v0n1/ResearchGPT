"""
OpenAI model wrapper for the AI Research Agent.
"""
import time
import json
from typing import Dict, List, Any, Optional, Union, Tuple

import openai
from openai import OpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from agent import config
from agent.logger import AgentLogger

logger = AgentLogger(__name__)

class ModelAPIWrapper:
    """
    A wrapper for the OpenAI API that handles requests, retries, and rate limits.
    """
    
    def __init__(self):
        """
        Initialize the OpenAI API client with credentials from config.
        """
        # Configure OpenAI API
        self.client = OpenAI(
            api_key=config.OPENAI_API_KEY,
            organization=config.OPENAI_ORGANIZATION
        )
        
        # Default parameters
        self.model = config.MODEL_NAME
        self.max_tokens = config.MAX_TOKENS
        self.temperature = config.TEMPERATURE
        
        # Rate limiting
        self.request_count = 0
        self.request_start_time = time.time()
        self.rate_limit = config.API_RATE_LIMIT
        
        logger.info(f"Initialized ModelAPIWrapper with model {self.model}")
    
    def _check_rate_limit(self):
        """
        Check if the current request would exceed the rate limit.
        If necessary, sleep to stay within rate limits.
        """
        current_time = time.time()
        elapsed = current_time - self.request_start_time
        
        # Reset counter after 60 seconds
        if elapsed >= 60:
            self.request_count = 0
            self.request_start_time = current_time
            return
        
        # If we're at the rate limit, sleep until the minute is up
        if self.request_count >= self.rate_limit:
            sleep_time = 60 - elapsed
            logger.warning(f"Rate limit reached. Sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
            self.request_count = 0
            self.request_start_time = time.time()
        
    @retry(
        retry=retry_if_exception_type((
            openai.RateLimitError,
            openai.APITimeoutError,
            openai.APIConnectionError
        )),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(5)
    )
    def _call_api(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """
        Make a request to the OpenAI API with retry logic.
        
        Args:
            messages: A list of message dictionaries for the conversation
            **kwargs: Additional parameters to pass to the API
            
        Returns:
            The API response as a dictionary
        """
        # Check rate limit before making request
        self._check_rate_limit()
        
        # Track request for rate limiting
        self.request_count += 1
        
        # Get start time for logging
        start_time = time.time()
        
        try:
            response = self.client.chat.completions.create(
                model=kwargs.get("model", self.model),
                messages=messages,
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature),
                n=kwargs.get("n", 1),
                stream=kwargs.get("stream", False)
            )
            
            # Log successful request
            elapsed = time.time() - start_time
            tokens_used = response.usage.total_tokens
            logger.debug(
                f"API request successful",
                elapsed_time=f"{elapsed:.2f}s",
                tokens=tokens_used
            )
            
            # Convert to dict for consistent handling
            response_dict = response.model_dump()
            return response_dict
            
        except Exception as e:
            # Log the error
            elapsed = time.time() - start_time
            logger.error(
                f"API request failed: {str(e)}",
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
        Generate text using the OpenAI chat completions API.
        
        Args:
            prompt: The user prompt to send to the model
            system_message: Optional system message to set context
            conversation_history: Optional conversation history
            **kwargs: Additional parameters to pass to the API
            
        Returns:
            The generated text as a string
        """
        # Construct messages array
        messages = []
        
        # Add system message if provided
        if system_message:
            messages.append({"role": "system", "content": system_message})
        else:
            # Use default system message based on agent objective
            messages.append({
                "role": "system",
                "content": (
                    f"You are {config.AGENT_NAME}. "
                    f"Your objective is to {config.AGENT_OBJECTIVE} "
                    f"{config.AGENT_DESCRIPTION}"
                )
            })
        
        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)
        
        # Add user prompt
        messages.append({"role": "user", "content": prompt})
        
        # Call the API
        response = self._call_api(messages, **kwargs)
        
        # Extract the generated text
        generated_text = response["choices"][0]["message"]["content"]
        
        return generated_text
    
    def generate_json(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate structured JSON output using the OpenAI chat completions API.
        
        Args:
            prompt: The user prompt to send to the model
            system_message: Optional system message to set context
            **kwargs: Additional parameters to pass to the API
            
        Returns:
            The generated content as a Python dictionary
        """
        # If no system message is provided, create one that requests JSON output
        if system_message is None:
            system_message = (
                f"You are {config.AGENT_NAME}. "
                f"Your objective is to {config.AGENT_OBJECTIVE} "
                f"{config.AGENT_DESCRIPTION} "
                f"Respond with valid JSON only, no explanations or other text."
            )
        
        # Generate text with the JSON format instruction
        response_text = self.generate_text(
            prompt=prompt + "\nRespond with valid JSON only.",
            system_message=system_message,
            **kwargs
        )
        
        # Parse the response as JSON
        try:
            # Handle case where the model wraps the JSON in code blocks
            if response_text.startswith("```json"):
                response_text = response_text.split("```json")[1]
            if response_text.endswith("```"):
                response_text = response_text.split("```")[0]
            
            # Strip any non-JSON text around the response
            response_text = response_text.strip()
            
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            logger.debug(f"Raw response: {response_text}")
            
            # Return empty dict as fallback
            return {} 