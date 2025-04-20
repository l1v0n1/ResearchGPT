"""
Logging configuration for the AI Research Agent.
"""
import logging
import os
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

from agent import config

class AgentLogger:
    """
    A custom logger for the AI Research Agent that provides consistent logging
    across all components of the application.
    """

    # Class-level date offset to apply to all loggers
    _date_offset = timedelta(days=0)

    @classmethod
    def set_date_offset(cls, days=0, hours=0, minutes=0):
        """
        Set a global date offset to apply to all timestamps.
        This is useful for correcting system time issues without changing the system clock.
        
        Args:
            days: Days to offset
            hours: Hours to offset
            minutes: Minutes to offset
        """
        cls._date_offset = timedelta(days=days, hours=hours, minutes=minutes)
        logging.info(f"Date offset set to {cls._date_offset}")

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
        # Apply the date offset to the current time to get the correct timestamp
        current_time = datetime.now() - self._date_offset
        
        metadata = {
            "timestamp": current_time.isoformat(),
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

def set_global_date_offset(year_diff=0, month_diff=0, day_diff=0):
    """
    Utility function to set a global date offset based on the difference between 
    the current system time and the actual correct time.
    
    Args:
        year_diff: Difference in years (current - correct)
        month_diff: Difference in months (current - correct)
        day_diff: Difference in days (current - correct)
    
    Example:
        If system shows 2025-04-20 but it's actually 2024-04-26:
        set_global_date_offset(year_diff=1, month_diff=0, day_diff=-6)
    """
    now = datetime.now()
    
    # Calculate approximate days from year and month differences
    days_from_years = year_diff * 365
    days_from_months = month_diff * 30  # Approximation
    
    # Total days difference
    total_days = days_from_years + days_from_months + day_diff
    
    AgentLogger.set_date_offset(days=total_days)
    
    corrected_date = datetime.now() - timedelta(days=total_days)
    print(f"Date offset set: System time {now} → Corrected time {corrected_date}")
    return corrected_date 