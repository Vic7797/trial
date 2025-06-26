import logging
import sys
import json
import time
from typing import Any, Dict, Optional
from fastapi import Request
from contextvars import ContextVar
import uuid
from datetime import datetime
from logging.handlers import RotatingFileHandler
import os

request_id_ctx_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)

def get_request_id() -> str:
    """Get or generate a request ID."""
    req_id = request_id_ctx_var.get()
    if not req_id:
        req_id = str(uuid.uuid4())
        request_id_ctx_var.set(req_id)
    return req_id

class JsonFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record):
        log_record = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'message': record.getMessage(),
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'request_id': get_request_id(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)
            
        return json.dumps(log_record)

def setup_logging():
    """Configure logging with JSON formatter and handlers."""
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Configure root logger
    root_logger.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # File handler for ELK
    log_file_path = "/app/logs/app.log"
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
    file_handler = RotatingFileHandler(log_file_path, maxBytes=5*1024*1024, backupCount=3, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    
    # Set formatter
    formatter = JsonFormatter()
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    # Add handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Configure uvicorn loggers
    for name in ['uvicorn', 'uvicorn.error', 'uvicorn.access', 'fastapi']:
        logging.getLogger(name).handlers.clear()
        logging.getLogger(name).propagate = True

# Initialize logging when module is imported
setup_logging()

def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    return logging.getLogger(name)

# Common logger for the application
logger = get_logger(__name__)

def log_request(request: Request, response=None, process_time: float = 0):
    """Log HTTP request details."""
    request_id = get_request_id()
    
    # Add request ID to response headers
    if response:
        response.headers['X-Request-ID'] = request_id
    
    # Skip logging for health checks
    if request.url.path == '/health':
        return
    
    log_data = {
        'request_id': request_id,
        'method': request.method,
        'url': str(request.url),
        'client': request.client.host if request.client else None,
        'user_agent': request.headers.get('user-agent'),
        'process_time': f"{process_time:.3f}s"
    }
    
    if response:
        log_data.update({
            'status_code': response.status_code,
            'response_size': response.headers.get('content-length', 0)
        })
    
    logger.info("Request processed", extra=log_data)