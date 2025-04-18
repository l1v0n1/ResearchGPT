"""
Logging configuration for the AI Research Agent.
"""
import logging
import os
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

from agent import config

class AgentLogger:
    """
    A custom logger for the AI Research Agent that provides consistent logging
    across all components of the application.
    """

    def __init__(self, name: str, log_file: Optional[str] = None):
        """
        Initialize the logger with a name and optional log file.

        Args:
            name: The name of the logger, typically the module name.
            log_file: Path to the log file. If None, uses the default path from config.
        """
        self.logger = logging.getLogger(name)
        
        # Set the log level from configuration
        log_level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
        self.logger.setLevel(log_level)
        
        # Check if handlers are already configured to avoid duplicate handlers
        if not self.logger.handlers:
            # Create a formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            # Configure console handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            console_handler.setLevel(log_level)
            self.logger.addHandler(console_handler)
            
            # Configure file handler if log file is provided
            if log_file is None:
                log_file = config.LOG_FILE
                
            # Ensure the directory exists
            log_dir = Path(log_file).parent
            os.makedirs(log_dir, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            file_handler.setLevel(log_level)
            self.logger.addHandler(file_handler)
    
    def debug(self, message: str, **kwargs):
        """Log a debug message."""
        self._log_with_metadata(self.logger.debug, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log an info message."""
        self._log_with_metadata(self.logger.info, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log a warning message."""
        self._log_with_metadata(self.logger.warning, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log an error message."""
        self._log_with_metadata(self.logger.error, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log a critical message."""
        self._log_with_metadata(self.logger.critical, message, **kwargs)
    
    def _log_with_metadata(self, log_func, message: str, **kwargs):
        """
        Add metadata to the log message.
        
        Args:
            log_func: The logging function to use (debug, info, etc.)
            message: The log message
            **kwargs: Additional metadata to include in the log
        """
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "agent": config.AGENT_NAME,
        }
        metadata.update(kwargs)
        
        # Format metadata as string if present
        if metadata:
            metadata_str = " | ".join(f"{k}={v}" for k, v in metadata.items())
            message = f"{message} | {metadata_str}"
        
        log_func(message)

# Create a default logger for the agent
agent_logger = AgentLogger("agent") 