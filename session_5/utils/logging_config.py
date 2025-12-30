"""
Logging Configuration

Provides structured logging setup for Kafka applications.
Supports both console and file logging with JSON formatting.
"""

import json
import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add extra fields if present
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "event_id"):
            log_data["event_id"] = record.event_id
        if hasattr(record, "event_type"):
            log_data["event_type"] = record.event_type
        if hasattr(record, "partition"):
            log_data["partition"] = record.partition
        if hasattr(record, "offset"):
            log_data["offset"] = record.offset
        if hasattr(record, "processing_time_ms"):
            log_data["processing_time_ms"] = record.processing_time_ms
        if hasattr(record, "alert_type"):
            log_data["alert_type"] = record.alert_type
        if hasattr(record, "alert_message"):
            log_data["alert_message"] = record.alert_message
        if hasattr(record, "severity"):
            log_data["severity"] = record.severity
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


class SimpleFormatter(logging.Formatter):
    """Simple human-readable formatter for console output"""
    
    def format(self, record):
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        level = record.levelname
        logger = record.name
        message = record.getMessage()
        
        # Build log line
        log_line = f"[{timestamp}] {level:8} [{logger}] {message}"
        
        # Add extra fields
        extras = []
        if hasattr(record, "user_id"):
            extras.append(f"user_id={record.user_id}")
        if hasattr(record, "event_id"):
            extras.append(f"event_id={record.event_id}")
        if hasattr(record, "partition"):
            extras.append(f"partition={record.partition}")
        if hasattr(record, "offset"):
            extras.append(f"offset={record.offset}")
        
        if extras:
            log_line += f" | {' '.join(extras)}"
        
        return log_line


def setup_logging(
    name: str,
    level: str = None,
    log_to_file: bool = True,
    log_dir: str = "logs",
    json_format: bool = False,
    console_output: bool = True
) -> logging.Logger:
    """
    Setup logging configuration
    
    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to file
        log_dir: Directory for log files
        json_format: Use JSON format (for production)
        console_output: Output to console
    
    Returns:
        Configured logger
    """
    # Get log level from environment or use default
    log_level = level or os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Choose formatter
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = SimpleFormatter()
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level))
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if log_to_file:
        # Create log directory
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)
        
        # Create rotating file handler
        file_handler = RotatingFileHandler(
            log_path / f"{name}.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(getattr(logging, log_level))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

