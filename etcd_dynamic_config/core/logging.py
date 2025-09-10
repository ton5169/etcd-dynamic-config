"""ECS-compatible logging configuration for etcd-dynamic-config."""

import logging
import os
import sys
from typing import Optional

import ecs_logging


class ContextFilter(logging.Filter):
    """Filter that adds service and environment context to all log records"""

    def __init__(self, service_name: str, service_version: str, environment: str):
        super().__init__()
        self.service_name = service_name
        self.service_version = service_version
        self.environment = environment

    def filter(self, record: logging.LogRecord) -> bool:
        # Add service and environment to the record's __dict__
        # This will be picked up by the ECS formatter
        if not hasattr(record, "service"):
            record.service = {
                "name": self.service_name,
                "version": self.service_version,
            }
        if not hasattr(record, "environment"):
            record.environment = self.environment
        return True


def get_application_name() -> str:
    """Get application name from environment or default"""
    return os.getenv("APPLICATION_NAME", "etcd-dynamic-config")


def get_environment() -> str:
    """Get environment from environment or default"""
    return os.getenv("ENVIRONMENT", "development")


def get_application_version() -> str:
    """Get application version from environment or default"""
    return os.getenv("APPLICATION_VERSION", "0.1.0")


def setup_logging(
    level: str = "INFO",
    disable_uvicorn_access: bool = True,
    sql_level: Optional[str] = None,
    application_name: Optional[str] = None,
    exclude_fields: Optional[list] = None,
    stack_trace_limit: Optional[int] = None,
) -> None:
    """
    Setup ECS-compatible logging according to Elastic documentation.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        disable_uvicorn_access: Disable uvicorn access logs
        sql_level: Separate logging level for SQLAlchemy
        application_name: Override application name
        exclude_fields: List of fields to exclude from logs
        stack_trace_limit: Limit stack trace frames (None for unlimited)
    """
    # Set default exclude fields if not provided
    if exclude_fields is None:
        exclude_fields = [
            "log.origin.file.line",  # Exclude line numbers for performance
            "log.origin.file.name",  # Exclude file names for performance
            "process.pid",  # Process ID might not be needed
            "process.thread.id",  # Thread ID might not be needed
        ]

    # Get application info
    app_name = application_name or get_application_name()
    app_version = get_application_version()
    app_environment = get_environment()

    # Create context filter for automatic service/environment fields
    context_filter = ContextFilter(app_name, app_version, app_environment)

    # Create ECS formatter with proper configuration
    formatter = ecs_logging.StdlibFormatter(
        exclude_fields=exclude_fields,
        stack_trace_limit=stack_trace_limit,
    )

    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.addFilter(context_filter)  # Add context filter to handler

    # Setup root logger
    numeric_level = getattr(logging, str(level).upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.handlers = [handler]  # Replace all handlers
    root_logger.addFilter(context_filter)  # Add context filter to root logger

    # Setup specific loggers
    loggers_config = [
        ("httpx", numeric_level),
        ("uvicorn", numeric_level),
        ("uvicorn.error", numeric_level),
        ("sqlalchemy", sql_level or logging.WARNING),
        ("etcd_dynamic_config", numeric_level),
    ]

    for logger_name, logger_level in loggers_config:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logger_level)
        logger.handlers = [handler]
        logger.addFilter(context_filter)  # Add context filter to each logger
        logger.propagate = False

    # Special handling for uvicorn access logs
    access_logger = logging.getLogger("uvicorn.access")
    access_logger.handlers = [handler]
    access_logger.addFilter(context_filter)  # Add context filter to access logger
    access_logger.propagate = False
    if disable_uvicorn_access:
        access_logger.setLevel(logging.WARNING)
    else:
        access_logger.setLevel(numeric_level)

    # Add application context to all loggers
    app_logger = logging.getLogger("etcd_dynamic_config")
    app_logger.info(
        "logging_configured",
        extra={
            "service": {
                "name": app_name,
                "version": get_application_version(),
            },
            "environment": get_environment(),
            "event": {
                "category": "application",
                "action": "logging_started",
            },
        },
    )
