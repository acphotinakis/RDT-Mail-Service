# src/common/logger.py
import logging
from rich.logging import RichHandler


def setup_logger(name: str = "APP", level: str = "INFO") -> logging.Logger:
    """
    Configures and returns a logger with a RichHandler for attractive terminal output.
    This acts as a wrapper, allowing you to use standard logging calls (log.info, etc.)
    while getting the visual benefits of the 'rich' library.

    Args:
        name: The name of the logger (e.g., the module name).
        level: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    # Create a logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Check if the logger already has handlers to avoid duplicate logs if called multiple times
    if not logger.handlers:
        # Create a RichHandler for stylized output
        rich_handler = RichHandler(
            rich_tracebacks=True,  # Pretty print exceptions
            markup=True,  # Allow rich markup in logs
            show_time=True,
            show_level=True,
            show_path=False,  # Keep the output clean
        )
        rich_handler.setLevel(level)

        # Add the handler to the logger
        logger.addHandler(rich_handler)

        # Prevent propagation to the root logger if it also has handlers configured
        logger.propagate = False

    return logger
