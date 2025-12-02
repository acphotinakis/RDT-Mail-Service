import logging
from logging import Logger, FileHandler, Formatter
from typing import Optional
from contextlib import contextmanager

_default_logger: Optional[Logger] = None


# ------------------------------------------------------------------------------
# MAIN LOGGER INITIALIZATION
# ------------------------------------------------------------------------------
def setup_logger(name: str = "APP", level: str = "INFO", log_file: Optional[str] = None) -> Logger:
    """
    Initializes the root/default logger used by all class/module loggers.
    ALL logs go *only* to the specified file.
    No console logging allowed.
    """
    global _default_logger

    if not log_file:
        raise ValueError("A log_file must be provided. File-only logging is required.")

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level.upper())

    # Clear any pre-existing handlers (important!)
    for h in list(logger.handlers):
        logger.removeHandler(h)

    # Force overwrite mode
    file_handler = FileHandler(log_file, mode="w", encoding="utf-8")
    file_handler.setLevel(level.upper())

    file_formatter = Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)

    # Attach ONLY the file handler
    logger.addHandler(file_handler)

    # Prevent propagation (so nothing leaks to root handlers)
    logger.propagate = False

    _default_logger = logger
    return logger


# ------------------------------------------------------------------------------
# CLASS-LEVEL LOGGER
# ------------------------------------------------------------------------------
def get_class_logger(obj_or_name) -> Logger:
    global _default_logger

    if isinstance(obj_or_name, str):
        name = obj_or_name
    else:
        name = obj_or_name.__class__.__name__

    logger = logging.getLogger(name)

    # Inherit file-only handlers
    if _default_logger and not logger.handlers:
        for handler in _default_logger.handlers:
            logger.addHandler(handler)

    logger.setLevel(_default_logger.level if _default_logger else logging.INFO)
    logger.propagate = False
    return logger


# ------------------------------------------------------------------------------
# SIMPLE SHORTCUT LOGGING FUNCTIONS
# ------------------------------------------------------------------------------
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


# ------------------------------------------------------------------------------
# CONTEXT MANAGER
# ------------------------------------------------------------------------------
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


# import logging
# from logging import Logger, FileHandler, Formatter
# from rich.logging import RichHandler
# from typing import Optional
# from contextlib import contextmanager

# _default_logger: Optional[Logger] = None


# # ------------------------------------------------------------------------------
# # MAIN LOGGER INITIALIZATION
# # ------------------------------------------------------------------------------
# def setup_logger(name: str = "APP", level: str = "INFO", log_file: Optional[str] = None) -> Logger:
#     """
#     Initializes the root/default logger used by all class/module loggers.
#     """
#     global _default_logger

#     # Ensure logging module is imported
#     logger = logging.getLogger(name)
#     logger.setLevel(level.upper())

#     # Standard rich format for terminal
#     CUSTOM_FORMAT = (
#         "\n####################################\n"
#         "Debug Type: %(levelname)s\n"
#         "Class: %(name)s\n"
#         "Message: %(message)s\n"
#         "####################################\n"
#     )

#     if not logger.handlers:
#         # Rich handler for console output
#         rich_handler = RichHandler(
#             rich_tracebacks=True,
#             markup=True,
#             show_time=False,
#             show_level=False,
#             show_path=False,
#         )
#         rich_handler.setLevel(level.upper())
#         rich_handler.setFormatter(logging.Formatter(CUSTOM_FORMAT))
#         logger.addHandler(rich_handler)

#         # Optional file logging
#         if log_file:
#             file_handler = FileHandler(log_file, mode="w", encoding="utf-8")
#             file_handler.setLevel(level.upper())
#             file_formatter = Formatter(
#                 "%(levelname)-8s | %(name)s | %(message)s",
#             )
#             file_handler.setFormatter(file_formatter)
#             logger.addHandler(file_handler)

#         logger.propagate = False

#     _default_logger = logger
#     return logger


# # ------------------------------------------------------------------------------
# # CLASS-LEVEL LOGGER
# # ------------------------------------------------------------------------------
# def get_class_logger(obj_or_name) -> Logger:
#     """
#     Returns a logger named after the class or provided name.

#     Usage:
#         self.logger = get_class_logger(self)        # for classes
#         logger = get_class_logger("RDT_PACKET")     # for modules
#     """
#     global _default_logger

#     # Determine logger name
#     if isinstance(obj_or_name, str):
#         name = obj_or_name
#     else:
#         name = obj_or_name.__class__.__name__

#     logger = logging.getLogger(name)

#     # Inherit handlers from default logger ONCE
#     if not logger.handlers:
#         if _default_logger:
#             for handler in _default_logger.handlers:
#                 logger.addHandler(handler)

#     # Match levels
#     if _default_logger:
#         logger.setLevel(_default_logger.level)

#     logger.propagate = False
#     return logger


# # ------------------------------------------------------------------------------
# # SIMPLE SHORTCUT LOGGING FUNCTIONS
# # ------------------------------------------------------------------------------
# def debug(msg: str):
#     if _default_logger:
#         _default_logger.debug(msg)


# def info(msg: str):
#     if _default_logger:
#         _default_logger.info(msg)


# def warning(msg: str):
#     if _default_logger:
#         _default_logger.warning(msg)


# def error(msg: str):
#     if _default_logger:
#         _default_logger.error(msg)


# def critical(msg: str):
#     if _default_logger:
#         _default_logger.critical(msg)


# # ------------------------------------------------------------------------------
# # CONTEXT MANAGER
# # ------------------------------------------------------------------------------
# @contextmanager
# def log_block(name: str):
#     if not _default_logger:
#         raise RuntimeError("Logger not initialized. Call setup_logger() first.")

#     _default_logger.info(f"START: {name}")
#     try:
#         yield
#         _default_logger.info(f"END: {name}")
#     except Exception as e:
#         _default_logger.exception(f"ERROR in {name}: {e}")
#         raise
