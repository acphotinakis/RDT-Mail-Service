import logging
import inspect
import sys
from logging import Logger, FileHandler, StreamHandler, Formatter
from typing import Optional, Dict
from contextlib import contextmanager

# Holds ALL registered root loggers
_registered_loggers: Dict[str, Logger] = {}


class ColoredFormatter(Formatter):
    """
    Custom formatter that adds ANSI colors to the levelname.
    Ensures alignment by padding the level name before applying color codes.
    """

    # ANSI Escape Codes
    RESET = "\033[0m"
    COLORS = {
        logging.DEBUG: "\033[36m",  # Cyan
        logging.INFO: "\033[32m",  # Green
        logging.WARNING: "\033[33m",  # Yellow
        logging.ERROR: "\033[31m",  # Red
        logging.CRITICAL: "\033[35m",  # Magenta
    }

    def format(self, record):
        # Save original value
        orig_levelname = record.levelname

        # 1. Pad the level name to 8 characters (e.g. "INFO    ")
        #    This ensures visual alignment in the logs despite color codes.
        padded_level = f"{orig_levelname:<8}"

        # 2. Apply color if available
        color = self.COLORS.get(record.levelno)
        if color:
            record.levelname = f"{color}{padded_level}{self.RESET}"
        else:
            record.levelname = padded_level

        # 3. Format the record
        try:
            return super().format(record)
        finally:
            # Restore original value to avoid side effects if record is reused
            record.levelname = orig_levelname


# -------------------------------------------------------------------
# Automatic detection of caller class/function
# -------------------------------------------------------------------
def _detect_origin() -> str:
    """
    Automatically detect the class or function that called the logger.
    Skips the current file to find the actual caller.
    """
    # Walk up the stack until we find a frame outside of this file
    frame = inspect.currentframe()
    while frame:
        if frame.f_code.co_filename != __file__:
            break
        frame = frame.f_back

    if not frame:
        return "Unknown"

    func_name = frame.f_code.co_name
    # Check if inside a class (has 'self')
    if "self" in frame.f_locals:
        cls = frame.f_locals["self"].__class__.__name__
        return f"{cls}.{func_name}"

    return func_name


# -------------------------------------------------------------------
# Register a logger pipeline
# -------------------------------------------------------------------
def register_logger(
    key: str, name: str, level: str = "INFO", log_file: Optional[str] = None
) -> Logger:
    """
    Creates a named logger pipeline that writes to both Console and File.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level.upper())

    # Clear old handlers to prevent duplicates
    if logger.hasHandlers():
        logger.handlers.clear()

    # Shared Formatter
    # Note: %(levelname)s is used here; padding/color is handled in ColoredFormatter
    formatter = ColoredFormatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # --- Console Handler ---
    console_handler = StreamHandler(sys.stdout)
    console_handler.setLevel(level.upper())
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # --- File Handler ---
    if log_file:
        file_handler = FileHandler(log_file, mode="w", encoding="utf-8")
        file_handler.setLevel(level.upper())
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.propagate = False
    _registered_loggers[key] = logger
    return logger


# -------------------------------------------------------------------
# Get a logger by pipeline name
# -------------------------------------------------------------------
def get_logger(key: str) -> Logger:
    if key not in _registered_loggers:
        # Fallback or raise error.
        # raising error helps catch initialization issues.
        raise RuntimeError(f"Logger '{key}' not registered!")
    return _registered_loggers[key]


# -------------------------------------------------------------------
# Core Logging Implementation
# -------------------------------------------------------------------
def _log_impl(logger_key: str, level: str, message: str, origin: Optional[str] = None, **kwargs):
    logger = get_logger(logger_key)
    origin = origin or _detect_origin()

    # Prepend origin to the message
    final_msg = f"{origin}: {message}"

    # Delegate to standard logger
    log_method = getattr(logger, level.lower())
    log_method(final_msg, **kwargs)


# -------------------------------------------------------------------
# Public Logging Shortcuts (DETAILED PIPELINE)
# -------------------------------------------------------------------
def log_info_detailed(msg: str, origin: Optional[str] = None, **kwargs):
    _log_impl("detailed", "INFO", msg, origin, **kwargs)


def log_debug_detailed(msg: str, origin: Optional[str] = None, **kwargs):
    _log_impl("detailed", "DEBUG", msg, origin, **kwargs)


def log_warning_detailed(msg: str, origin: Optional[str] = None, **kwargs):
    _log_impl("detailed", "WARNING", msg, origin, **kwargs)


def log_error_detailed(msg: str, origin: Optional[str] = None, **kwargs):
    _log_impl("detailed", "ERROR", msg, origin, **kwargs)


# -------------------------------------------------------------------
# Generic public shortcuts (specify logger key)
# -------------------------------------------------------------------
def log_info(key: str, msg: str, origin: Optional[str] = None):
    _log_impl(key, "INFO", msg, origin)


def log_debug(key: str, msg: str, origin: Optional[str] = None):
    _log_impl(key, "DEBUG", msg, origin)


def log_warning(key: str, msg: str, origin: Optional[str] = None):
    _log_impl(key, "WARNING", msg, origin)


def log_error(key: str, msg: str, origin: Optional[str] = None):
    _log_impl(key, "ERROR", msg, origin)


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
