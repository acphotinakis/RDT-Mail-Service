"""
File: util.py
----------------------------------------
Description:
    Provides utility functions for the RDT protocol.

Author:
    Caleb Talbott

Last Edited:
    2025-11-1
"""

from enum import Enum


class PrintType(Enum):
    DEBUG = ("\033[96m", 0)
    INFO = ("\033[93m", 1)
    ERROR = ("\033[91m", 2)
    SUCCESS = ("\033[92m", 3)


LOGGING_LEVEL = PrintType.INFO


def print_info(message: str, print_type: PrintType):
    if print_type.value[1] >= LOGGING_LEVEL.value[1]:
        print(f"{print_type.value[0]}{message}\033[0m")


def calculate_checksum(data: bytes) -> int:
    if len(data) % 2 == 1:
        data += b"\x00"

    checksum = 0
    for i in range(0, len(data), 2):
        word = (data[i] << 8) + data[i + 1]
        checksum += word
        checksum = (checksum & 0xFFFF) + (checksum >> 16)  # carry around

    return ~checksum & 0xFFFF
