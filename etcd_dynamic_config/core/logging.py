import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class ContextFilter(logging.Filter):
    """Filter that adds service and environment context to all log records"""

    def __init__(self, service_name: str, service_version: str, environment: str):
        super().__init__()
        self.service_name = service_name
        self.service_version = service_version
        self.environment = environment

    def filter(self, record: logging.LogRecord) -> bool:
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
    return os.getenv("APPLICATION_NAME", "GsControlUnit")


def get_environment() -> str:
    """Get environment from environment or default"""
    return os.getenv("ENVIRONMENT", "development")


def get_application_version() -> str:
    """Get application version from environment or default"""
    return os.getenv("APPLICATION_VERSION", "0.0.1")


class SerilogLikeJSONFormatter(logging.Formatter):
    SERILOG_LEVELS = {
        "CRITICAL": "Fatal",
        "ERROR": "Error",
        "WARNING": "Warning",
        "INFO": "Information",
        "DEBUG": "Debug",
        "NOTSET": "Verbose",
    }

    def __init__(self, include_ecs_version: Optional[str] = "8.10.0"):
        super().__init__()
        self.include_ecs_version = include_ecs_version

    def format(self, record: logging.LogRecord) -> str:
        doc: Dict[str, Any] = {}

        ts = (
            datetime.fromtimestamp(record.created, tz=timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
        )
        doc["@timestamp"] = ts

        level = self.SERILOG_LEVELS.get(
            record.levelname.upper(), record.levelname.title()
        )
        if isinstance(level, str):
            level = level.replace("\u001b[31m", "").replace("\u001b[39m", "")
        doc["level"] = level

        doc["message"] = record.getMessage()

        if record.exc_info:
            doc["exception"] = self.formatException(record.exc_info)
            exc_type = (
                record.exc_info[0].__name__ if record.exc_info[0] else "Exception"
            )
            exc_msg = str(record.exc_info[1]) if record.exc_info[1] else doc["message"]
            doc["error"] = {
                "type": exc_type,
                "message": exc_msg,
                "stack_trace": doc["exception"],
            }

        skip = {
            "args",
            "asctime",
            "created",
            "exc_info",
            "exc_text",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "message",
            "msg",
            "name",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "stack_info",
            "thread",
            "threadName",
        }
        for k, v in record.__dict__.items():
            if k not in skip and k not in doc:
                doc[k] = v

        if self.include_ecs_version:
            doc["ecs.version"] = self.include_ecs_version

        return json.dumps(doc, ensure_ascii=False)


def setup_logging(
    level: str = "INFO",
    disable_uvicorn_access: bool = True,
    sql_level: Optional[str] = None,
    application_name: Optional[str] = None,
    exclude_fields: Optional[list] = None,
    stack_trace_limit: Optional[int] = None,
) -> None:
    app_name = application_name or get_application_name()
    app_version = get_application_version()
    app_environment = get_environment()

    context_filter = ContextFilter(app_name, app_version, app_environment)

    formatter = SerilogLikeJSONFormatter(include_ecs_version="8.10.0")

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.addFilter(context_filter)

    numeric_level = getattr(logging, str(level).upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.handlers = [handler]
    root_logger.filters.clear()
    root_logger.addFilter(context_filter)

    loggers_config = [
        ("httpx", numeric_level),
        ("uvicorn", numeric_level),
        ("uvicorn.error", numeric_level),
        ("sqlalchemy", sql_level or logging.WARNING),
        ("app", numeric_level),
    ]
    for logger_name, logger_level in loggers_config:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logger_level)
        logger.handlers = [handler]
        logger.filters.clear()
        logger.addFilter(context_filter)
        logger.propagate = False

    access_logger = logging.getLogger("uvicorn.access")
    access_logger.handlers = [handler]
    access_logger.filters.clear()
    access_logger.addFilter(context_filter)
    access_logger.propagate = False
    access_logger.setLevel(logging.WARNING if disable_uvicorn_access else numeric_level)

    app_logger = logging.getLogger("app")
    app_logger.info(
        "logging_configured",
        extra={
            "service": {"name": app_name, "version": app_version},
            "environment": app_environment,
            "event": {"category": "application", "action": "logging_started"},
            "message_template": "logging_configured",
        },
    )


# Для ошибок логируй logger.error("...", exc_info=True) — тогда поле exception заполнится и разберётся пайплайном.