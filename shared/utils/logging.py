"""
Logging utilities for all services.

This module provides standardized logging configuration and utilities
that can be used across all microservices.
"""

import json
import logging
import sys
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, Optional, Union

import structlog
from pythonjsonlogger import jsonlogger
from structlog.types import EventDict, Processor, WrappedLogger


def add_timestamp(
    logger: WrappedLogger, name: str, event_dict: EventDict
) -> EventDict:
    """Add ISO-format timestamp to the event dictionary.

    Args:
        logger: The wrapped logger instance
        name: The name of the logger
        event_dict: The event dictionary to modify

    Returns:
        EventDict: Modified event dictionary with timestamp
    """
    event_dict["timestamp"] = datetime.utcnow().isoformat()
    return event_dict


def add_service_info(
    service_name: str, environment: str
) -> Processor:
    """Create a processor that adds service information to log events.

    Args:
        service_name: Name of the service
        environment: Deployment environment

    Returns:
        Processor: Structlog processor function
    """
    def processor(
        logger: WrappedLogger, name: str, event_dict: EventDict
    ) -> EventDict:
        """Add service information to the event dictionary.

        Args:
            logger: The wrapped logger instance
            name: The name of the logger
            event_dict: The event dictionary to modify

        Returns:
            EventDict: Modified event dictionary with service info
        """
        event_dict["service"] = service_name
        event_dict["environment"] = environment
        return event_dict
    return processor


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter for logging.

    This formatter ensures all log records are formatted as JSON with
    consistent fields and structure.
    """

    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any]
    ) -> None:
        """Add custom fields to the log record.

        Args:
            log_record: The log record to modify
            record: The original log record
            message_dict: Additional message dictionary
        """
        super().add_fields(log_record, record, message_dict)
        
        if not log_record.get("timestamp"):
            log_record["timestamp"] = datetime.utcnow().isoformat()
        if log_record.get("level"):
            log_record["level"] = log_record["level"].upper()
        else:
            log_record["level"] = record.levelname


def setup_logging(
    service_name: str,
    environment: str,
    log_level: Union[str, int] = logging.INFO,
    json_output: bool = True
) -> None:
    """Configure logging for the service.

    Args:
        service_name: Name of the service
        environment: Deployment environment
        log_level: Logging level to use
        json_output: Whether to output logs in JSON format
    """
    # Convert string log level to integer if needed
    if isinstance(log_level, str):
        log_level = getattr(logging, log_level.upper())

    # Configure structlog
    processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        add_service_info(service_name, environment),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard logging
    handler = logging.StreamHandler(sys.stdout)
    if json_output:
        formatter = CustomJsonFormatter(
            "%(timestamp)s %(level)s %(name)s %(message)s"
        )
        handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a logger instance for the given name.

    Args:
        name: Name for the logger (typically __name__)

    Returns:
        structlog.BoundLogger: Configured logger instance
    """
    return structlog.get_logger(name)


def log_function_call(
    logger: Optional[structlog.BoundLogger] = None,
    level: str = "DEBUG"
) -> Callable:
    """Decorator to log function calls with arguments and return values.

    Args:
        logger: Logger instance to use (if None, creates one)
        level: Log level to use for the messages

    Returns:
        Callable: Decorator function
    """
    def decorator(func: Callable) -> Callable:
        nonlocal logger
        if logger is None:
            logger = get_logger(func.__module__)

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            func_name = func.__name__
            log_level = getattr(logging, level.upper())

            # Log function call
            logger.log(
                log_level,
                f"Calling {func_name}",
                args=args,
                kwargs=kwargs
            )

            try:
                result = func(*args, **kwargs)
                # Log successful return
                logger.log(
                    log_level,
                    f"{func_name} completed",
                    result=result
                )
                return result
            except Exception as e:
                # Log exception
                logger.exception(
                    f"Error in {func_name}",
                    error=str(e),
                    error_type=type(e).__name__
                )
                raise

        return wrapper
    return decorator 