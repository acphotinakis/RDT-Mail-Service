import pytest
import logging
from src.common.logger import setup_logger, get_class_logger


def test_setup_logger():
    """Tests that the logger is set up correctly."""
    logger = setup_logger("test_logger", level="DEBUG")
    assert logger.name == "test_logger"
    assert logger.level == logging.DEBUG


class MyClass:
    def __init__(self):
        self.log = get_class_logger(self)


def test_get_class_logger():
    """Tests that the class logger is created with the correct name."""
    instance = MyClass()
    assert instance.log.name == "MyClass"
