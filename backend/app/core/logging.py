"""
Logging configuration.

Configures structured logging for the application.
Uses Python's standard logging with a clean, readable format.
"""

import logging
import sys

from app.config.settings import get_settings

settings = get_settings()


def configure_logging() -> None:
    """Set up application-wide logging."""
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Silence noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info("Logging configured — level: %s", logging.getLevelName(log_level))


def get_logger(name: str) -> logging.Logger:
    """Return a named logger. Use in each module for consistent naming."""
    return logging.getLogger(name)
