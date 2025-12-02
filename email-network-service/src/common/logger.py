import logging
from logging import Logger, FileHandler, Formatter
from typing import Optional, Dict
from contextlib import contextmanager
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
import inspect

_console = Console()

# Holds ALL registered root loggers
_registered_loggers: Dict[str, Logger] = {}


# -------------------------------------------------------------------
# Automatic detection of caller class/function
# -------------------------------------------------------------------
def _detect_origin() -> str:
    """
    Automatically detect the class or function that called the logger.
    Returns: 'ClassName.method' or 'function'.
    """
    stack = inspect.stack()
    caller_frame = stack[2].frame
    func_name = stack[2].function

    # Check if inside a class (has 'self')
    if "self" in caller_frame.f_locals:
        cls = caller_frame.f_locals["self"].__class__.__name__
        return f"{cls}.{func_name}"

    return func_name


# -------------------------------------------------------------------
# Helper: Pretty Rich panel to stdout
# -------------------------------------------------------------------
def print_panel(level: str, origin: str, message: str):
    body = f"Debug Type: {level}\nClass: {origin}\nMessage:\n    {message}"

    panel = Panel(
        Text(body, style="white"),
        border_style="cyan",
        title=f"[bold]{origin}[/bold]",
        padding=(1, 2),
    )
    _console.print(panel)


# -------------------------------------------------------------------
# Register a logger pipeline
# -------------------------------------------------------------------
def register_logger(
    key: str, name: str, level: str = "INFO", log_file: Optional[str] = None
) -> Logger:
    """
    Creates a named logger pipeline.
    Example keys:
      - 'detailed'
      - 'simple'
    """

    logger = logging.getLogger(name)
    logger.setLevel(level.upper())

    # Clear old handlers
    for h in list(logger.handlers):
        logger.removeHandler(h)

    # # --- Console Handler (rich panels) ---
    # console_handler = logging.StreamHandler()
    # console_handler.setLevel(level.upper())
    # console_handler.setFormatter(logging.Formatter("[%(name)s] %(levelname)s: %(message)s"))
    # logger.addHandler(console_handler)

    # --- File Handler ---
    if log_file:
        file_handler = FileHandler(log_file, mode="w", encoding="utf-8")
        file_handler.setLevel(level.upper())
        file_handler.setFormatter(
            Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(file_handler)

    logger.propagate = False
    _registered_loggers[key] = logger
    return logger


# -------------------------------------------------------------------
# Get a logger by pipeline name
# -------------------------------------------------------------------
def get_logger(key: str) -> Logger:
    if key not in _registered_loggers:
        raise RuntimeError(f"Logger '{key}' not registered!")
    return _registered_loggers[key]


# -------------------------------------------------------------------
# Panel + File Logging (with auto origin)
# -------------------------------------------------------------------


def _panel_and_log(
    logger_key: str, level: str, message: str, origin: Optional[str] = None, **kwargs
):
    logger = get_logger(logger_key)
    origin = origin or _detect_origin()

    print_panel(level, origin, message)

    # Send exc_info=True to logger if provided
    if kwargs.get("exc_info"):
        getattr(logger, level.lower())(f"{origin}: {message}", exc_info=True)
    else:
        getattr(logger, level.lower())(f"{origin}: {message}")


# -------------------------------------------------------------------
# Public Logging Shortcuts (DETAILED PIPELINE)
# -------------------------------------------------------------------
def log_info_detailed(msg: str, origin: Optional[str] = None, **kwargs):
    _panel_and_log("detailed", "INFO", msg, origin, **kwargs)


def log_debug_detailed(msg: str, origin: Optional[str] = None, **kwargs):
    _panel_and_log("detailed", "DEBUG", msg, origin, **kwargs)


def log_warning_detailed(msg: str, origin: Optional[str] = None, **kwargs):
    _panel_and_log("detailed", "WARNING", msg, origin, **kwargs)


def log_error_detailed(msg: str, origin: Optional[str] = None, **kwargs):
    _panel_and_log("detailed", "ERROR", msg, origin, **kwargs)


# -------------------------------------------------------------------
# Public Logging Shortcuts (SIMPLE PIPELINE)
# -------------------------------------------------------------------
def log_info_simple(msg: str, origin: Optional[str] = None):
    _panel_and_log("simple", "INFO", msg, origin)


def log_warning_simple(msg: str, origin: Optional[str] = None):
    _panel_and_log("simple", "WARNING", msg, origin)


def log_error_simple(msg: str, origin: Optional[str] = None):
    _panel_and_log("simple", "ERROR", msg, origin)


# -------------------------------------------------------------------
# Generic public shortcuts (specify logger key)
# -------------------------------------------------------------------
def log_info(key: str, msg: str, origin: Optional[str] = None):
    _panel_and_log(key, "INFO", msg, origin)


def log_debug(key: str, msg: str, origin: Optional[str] = None):
    _panel_and_log(key, "DEBUG", msg, origin)


def log_warning(key: str, msg: str, origin: Optional[str] = None):
    _panel_and_log(key, "WARNING", msg, origin)


def log_error(key: str, msg: str, origin: Optional[str] = None):
    _panel_and_log(key, "ERROR", msg, origin)


# -------------------------------------------------------------------
# Context block (works for any logger)
# -------------------------------------------------------------------
@contextmanager
def log_block(key: str, title: str, origin: Optional[str] = None):
    origin = origin or _detect_origin()
    log_info(key, f"START: {title}", origin)
    try:
        yield
        log_info(key, f"END: {title}", origin)
    except Exception as e:
        log_error(key, f"ERROR in {title}: {e}", origin)
        raise


@contextmanager
def log_block_detailed(title: str, origin: Optional[str] = None):
    """Block logger for the detailed log file."""
    with log_block("detailed", title, origin=origin):
        yield


@contextmanager
def log_block_simple(title: str, origin: Optional[str] = None):
    """Block logger for the simple log file."""
    with log_block("simple", title, origin=origin):
        yield
