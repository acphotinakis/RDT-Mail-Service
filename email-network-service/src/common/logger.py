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

    # --- Console Handler (rich panels) ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level.upper())
    console_handler.setFormatter(logging.Formatter("[%(name)s] %(levelname)s: %(message)s"))
    logger.addHandler(console_handler)

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
# def _panel_and_log(logger_key: str, level: str, message: str, origin: Optional[str] = None):
#     logger = get_logger(logger_key)

#     # Automatic detection of origin if not supplied
#     origin = origin or _detect_origin()

#     # Console rich panel
#     print_panel(level, origin, message)

#     # File logger (plain text)
#     getattr(logger, level.lower())(f"{origin}: {message}")


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


# import logging
# from logging import Logger, FileHandler, Formatter
# from typing import Optional
# from contextlib import contextmanager
# from rich.console import Console
# from rich.panel import Panel
# from rich.text import Text
# from rich.logging import RichHandler


# _default_logger: Optional[Logger] = None
# _console = Console()


# # --------------------------
# # Helper to print rich panel
# # --------------------------
# def print_panel(level: str, name: str, message: str):
#     body = f"Debug Type: {level}\n" f"Class: {name}\n" f"Message:\n" f"    {message}"

#     panel = Panel(
#         Text(body, style="white"),
#         border_style="cyan",
#         title=f"[bold]{name}[/bold]",
#         padding=(1, 2),
#     )

#     _console.print(panel)


# # --------------------------
# # Main logger setup
# # --------------------------
# # def setup_logger(name: str = "APP", level: str = "INFO", log_file: Optional[str] = None) -> Logger:
# #     global _default_logger

# #     if not log_file:
# #         raise ValueError("log_file is required")

# #     logger = logging.getLogger(name)
# #     logger.setLevel(level.upper())

# #     # Clear old handlers
# #     for h in list(logger.handlers):
# #         logger.removeHandler(h)

# #     # --------------------------
# #     # FILE LOGGER (plain text)
# #     # --------------------------
# #     file_handler = FileHandler(log_file, mode="w", encoding="utf-8")
# #     file_handler.setLevel(level.upper())
# #     file_handler.setFormatter(
# #         Formatter(
# #             "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
# #             datefmt="%Y-%m-%d %H:%M:%S",
# #         )
# #     )
# #     logger.addHandler(file_handler)

# #     logger.propagate = False
# #     _default_logger = logger
# #     return logger


# def setup_logger(name: str = "APP", level: str = "INFO", log_file: Optional[str] = None) -> Logger:
#     """
#     Creates the root logger for the whole application.
#     STDOUT: Rich panels
#     FILE:   Plain text logs
#     """
#     global _default_logger

#     logger = logging.getLogger(name)
#     logger.setLevel(level.upper())

#     # --- Clear previous handlers ---
#     for h in list(logger.handlers):
#         logger.removeHandler(h)

#     # --- Rich console handler ---
#     # (Prints simple console logs; panel printing is handled manually)
#     console_handler = logging.StreamHandler()
#     console_handler.setLevel(level.upper())
#     console_handler.setFormatter(logging.Formatter("[%(name)s] %(levelname)s: %(message)s"))
#     logger.addHandler(console_handler)

#     # --- FILE handler (plain text) ---
#     if log_file:
#         file_handler = FileHandler(log_file, mode="w", encoding="utf-8")
#         file_handler.setLevel(level.upper())
#         file_handler.setFormatter(
#             Formatter(
#                 "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
#                 datefmt="%Y-%m-%d %H:%M:%S",
#             )
#         )
#         logger.addHandler(file_handler)

#     logger.propagate = False
#     _default_logger = logger
#     return logger


# # -------------------------------------------------------------------
# # Class-based loggers
# # -------------------------------------------------------------------
# def get_class_logger(obj_or_name) -> Logger:
#     """Returns a logger with inherited file handler from the default logger."""
#     global _default_logger

#     name = obj_or_name if isinstance(obj_or_name, str) else obj_or_name.__class__.__name__
#     logger = logging.getLogger(name)

#     # Inherit handlers if needed
#     if _default_logger and not logger.handlers:
#         for handler in _default_logger.handlers:
#             logger.addHandler(handler)

#     logger.setLevel(_default_logger.level if _default_logger else logging.INFO)
#     logger.propagate = False
#     return logger


# # -------------------------------------------------------------------
# # Panel + File Logging Wrapper
# # -------------------------------------------------------------------
# def _panel_and_log(level: str, msg: str, name: str):
#     """Prints pretty panel to stdout and logs plain-text to file."""
#     print_panel(level, name, msg)

#     logger = logging.getLogger(name)

#     # Fallback: If logger has no handlers, use root logger
#     if not logger.handlers and _default_logger:
#         logger = _default_logger

#     getattr(logger, level.lower())(msg)


# def _safe_logger_name(name: Optional[str]) -> str:
#     if name:
#         return name
#     if _default_logger:
#         return _default_logger.name
#     return "ROOT"


# # -------------------------------------------------------------------
# # Public Logging API
# # -------------------------------------------------------------------
# def info(msg: str, name: Optional[str] = None):
#     _panel_and_log("INFO", msg, _safe_logger_name(name))


# def debug(msg: str, name: Optional[str] = None):
#     _panel_and_log("DEBUG", msg, _safe_logger_name(name))


# def warning(msg: str, name: Optional[str] = None):
#     _panel_and_log("WARNING", msg, _safe_logger_name(name))


# def error(msg: str, name: Optional[str] = None):
#     _panel_and_log("ERROR", msg, _safe_logger_name(name))


# def critical(msg: str, name: Optional[str] = None):
#     _panel_and_log("CRITICAL", msg, _safe_logger_name(name))


# # -------------------------------------------------------------------
# # LOG BLOCK CONTEXT MANAGER  (NOW WORKS FOR LOG FILE!)
# # -------------------------------------------------------------------
# @contextmanager
# def log_block(title: str, name: str = "BLOCK"):
#     """
#     Emits panel + file logs on entry and exit.
#     """
#     block = get_class_logger(name)

#     # Start
#     print_panel("\nINFO", name, f"START: {title}")
#     block.info(f"START: {title}")

#     try:
#         yield
#         # End
#         print_panel("INFO", name, f"END: {title}")
#         block.info(f"END: {title}\n")

#     except Exception as e:
#         print_panel("ERROR", name, f"ERROR in {title}: {e}")
#         block.error(f"ERROR in {title}: {e}\n")
#         raise
