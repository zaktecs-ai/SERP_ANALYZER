"""Centralized logging for the Fiverr SERP Analyzer."""

import logging
import os
from datetime import datetime
from pathlib import Path


def setup_logging(log_dir: str = "logs") -> tuple:
    """Set up collection and error loggers.

    Returns (collection_logger, error_logger).
    """
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    # Collection logger
    collection_logger = logging.getLogger("collection")
    collection_logger.setLevel(logging.DEBUG)
    collection_logger.handlers.clear()

    col_fh = logging.FileHandler(
        os.path.join(log_dir, "collection.log"), encoding="utf-8"
    )
    col_fh.setLevel(logging.DEBUG)
    col_fmt = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    col_fh.setFormatter(col_fmt)
    collection_logger.addHandler(col_fh)

    # Error logger
    error_logger = logging.getLogger("errors")
    error_logger.setLevel(logging.WARNING)
    error_logger.handlers.clear()

    err_fh = logging.FileHandler(
        os.path.join(log_dir, "errors.log"), encoding="utf-8"
    )
    err_fh.setLevel(logging.WARNING)
    err_fmt = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    err_fh.setFormatter(err_fmt)
    error_logger.addHandler(err_fh)

    return collection_logger, error_logger


def log_collection(logger, keyword: str, url: str, position: int = None,
                   message: str = "", level: str = "info"):
    """Log a collection event."""
    pos_str = f"pos={position}" if position is not None else "pos=N/A"
    msg = f"keyword='{keyword}' | url={url} | {pos_str} | {message}"
    if level == "error":
        logger.error(msg)
    elif level == "warning":
        logger.warning(msg)
    else:
        logger.info(msg)


def log_error(logger, keyword: str, error_type: str, detail: str = ""):
    """Log an error event."""
    msg = f"keyword='{keyword}' | type={error_type} | {detail}"
    logger.warning(msg)


def log_challenge(logger, keyword: str, url: str, wait_seconds: float):
    """Log a challenge-pause event."""
    msg = (f"CHALLENGE_PAUSE | keyword='{keyword}' | url={url} | "
           f"wait_seconds={wait_seconds:.1f}")
    logger.info(msg)