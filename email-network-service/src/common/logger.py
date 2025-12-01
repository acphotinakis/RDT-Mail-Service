import logging
from logging import Logger, FileHandler, Formatter
from rich.logging import RichHandler
from typing import Optional
from contextlib import contextmanager

_default_logger: Optional[Logger] = None


def setup_logger(name: str = "APP", level: str = "INFO", log_file: Optional[str] = None) -> Logger:
    global _default_logger

    logger = logging.getLogger(name)
    logger.setLevel(level.upper())

    # Custom format including class name
    FORMAT = "[%(name)s] - %(levelname)s - %(message)s"

    if not logger.handlers:
        # Rich terminal handler
        rich_handler = RichHandler(
            rich_tracebacks=True,
            markup=True,
            show_time=True,
            show_level=True,
            show_path=False,
        )
        rich_handler.setLevel(level.upper())
        rich_handler.setFormatter(logging.Formatter(FORMAT))
        logger.addHandler(rich_handler)

        # Optional file logging
        if log_file:
            file_handler = FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(level.upper())
            file_formatter = Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

        logger.propagate = False

    _default_logger = logger
    return logger


# ──────────────────────────────────────────────────────────────────────────────
# Helper to get a logger for *each class*
# ──────────────────────────────────────────────────────────────────────────────


def get_class_logger(obj) -> Logger:
    """
    Returns a logger named after the class of the object calling it.
    Example result: 'SMTPClient', 'POP3Server', 'ComposeWindow'
    """
    logger = logging.getLogger(obj.__class__.__name__)
    logger.setLevel(logging.DEBUG)

    # Only attach handler once
    if not logger.handlers and _default_logger and _default_logger.handlers:
        for h in _default_logger.handlers:
            logger.addHandler(h)

    logger.propagate = False
    return logger


# ──────────────────────────────────────────────────────────────────────────────
# Convenience functions (use default logger)
# ──────────────────────────────────────────────────────────────────────────────


def debug(msg: str):
    if _default_logger:
        _default_logger.debug(msg)


def info(msg: str):
    if _default_logger:
        _default_logger.info(msg)


def warning(msg: str):
    if _default_logger:
        _default_logger.warning(msg)


def error(msg: str):
    if _default_logger:
        _default_logger.error(msg)


def critical(msg: str):
    if _default_logger:
        _default_logger.critical(msg)


# ──────────────────────────────────────────────────────────────────────────────
# Context manager for logging code blocks
# ──────────────────────────────────────────────────────────────────────────────


@contextmanager
def log_block(name: str):
    if not _default_logger:
        raise RuntimeError("Logger not initialized. Call setup_logger() first.")

    _default_logger.info(f"START: {name}")
    try:
        yield
        _default_logger.info(f"END: {name}")
    except Exception as e:
        _default_logger.exception(f"ERROR in {name}: {e}")
        raise
