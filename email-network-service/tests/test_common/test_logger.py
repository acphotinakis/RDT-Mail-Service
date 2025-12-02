import pytest

from src.common.logger import *


def test_setup_logger():
    """Tests that the logger is set up correctly."""
    logger = setup_logger("test_logger", level="DEBUG")
    assert logger.name == "test_logger"
    assert logger.level == logging.DEBUG


class MyClass:
    def __init__(self):
        


def test_get_class_logger():
    """Tests that the class logger is created with the correct name."""
    instance = MyClass()
    assert instance.log.name == "MyClass"
