"""
JobSnipr — Logging
Rotating file logs + console output, structured tags for grep-ability.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler


def setup_logging(level: str = "INFO", log_file: str = "jobsnipr.log") -> logging.Logger:
    logger = logging.getLogger("jobsnipr")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False

    if logger.handlers:
        return logger  # already configured (e.g. re-imported)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)

    try:
        file_handler = RotatingFileHandler(
            log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)
    except OSError:
        # Read-only filesystem or similar — console logging still works.
        logger.warning("Could not attach file log handler; continuing with console only.")

    return logger


def get_logger() -> logging.Logger:
    """Fetch the shared jobsnipr logger. Safe to call before setup_logging()
    has run — logging falls back to Python's default handler configuration
    until main.py calls setup_logging() with the real settings."""
    return logging.getLogger("jobsnipr")
