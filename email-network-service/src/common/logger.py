import logging
from logging import Logger, FileHandler, Formatter
from typing import Optional
from contextlib import contextmanager
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

_default_logger: Optional[Logger] = None
_console = Console()


# --------------------------
# Helper to print rich panel
# --------------------------
def print_panel(level: str, name: str, message: str):
    body = f"Debug Type: {level}\n" f"Class: {name}\n" f"Message:\n" f"    {message}"

    panel = Panel(
        Text(body, style="white"),
        border_style="cyan",
        title=f"[bold]{name}[/bold]",
        padding=(1, 2),
    )

    _console.print(panel)


# --------------------------
# Main logger setup
# --------------------------
def setup_logger(name: str = "APP", level: str = "INFO", log_file: Optional[str] = None) -> Logger:
    global _default_logger

    if not log_file:
        raise ValueError("log_file is required")

    logger = logging.getLogger(name)
    logger.setLevel(level.upper())

    # Clear old handlers
    for h in list(logger.handlers):
        logger.removeHandler(h)

    # --------------------------
    # FILE LOGGER (plain text)
    # --------------------------
    file_handler = FileHandler(log_file, mode="w", encoding="utf-8")
    file_handler.setLevel(level.upper())
    file_handler.setFormatter(
        Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(file_handler)

    logger.propagate = False
    _default_logger = logger
    return logger


# --------------------------
# Class-level loggers
# --------------------------
def get_class_logger(obj_or_name) -> Logger:
    global _default_logger

    name = obj_or_name if isinstance(obj_or_name, str) else obj_or_name.__class__.__name__
    logger = logging.getLogger(name)

    # Attach file handler only
    if _default_logger and not logger.handlers:
        for handler in _default_logger.handlers:
            logger.addHandler(handler)

    logger.setLevel(_default_logger.level if _default_logger else logging.INFO)
    logger.propagate = False
    return logger


# --------------------------
# Logging wrappers
# --------------------------
def _panel_and_log(level: str, msg: str, name: str):
    # Print beautiful panel to stdout
    print_panel(level, name, msg)

    # Log plain text to file
    logger = logging.getLogger(name)
    getattr(logger, level.lower())(msg)


def _safe_logger_name(name: Optional[str]) -> str:
    """Return a safe logger name even if _default_logger is None."""
    if name:
        return name
    if _default_logger:
        return _default_logger.name
    return "ROOT"


def info(msg: str, name: Optional[str] = None):
    n = _safe_logger_name(name)
    _panel_and_log("INFO", msg, n)


def debug(msg: str, name: Optional[str] = None):
    n = _safe_logger_name(name)
    _panel_and_log("DEBUG", msg, n)


def warning(msg: str, name: Optional[str] = None):
    n = _safe_logger_name(name)
    _panel_and_log("WARNING", msg, n)


def error(msg: str, name: Optional[str] = None):
    n = _safe_logger_name(name)
    _panel_and_log("ERROR", msg, n)


def critical(msg: str, name: Optional[str] = None):
    n = _safe_logger_name(name)
    _panel_and_log("CRITICAL", msg, n)


# --------------------------
# Context manager
# --------------------------
@contextmanager
def log_block(title: str):
    info(f"START: {title}", name="BLOCK")
    try:
        yield
        info(f"END: {title}", name="BLOCK")
    except Exception as e:
        error(f"ERROR in {title}: {e}", name="BLOCK")
        raise
