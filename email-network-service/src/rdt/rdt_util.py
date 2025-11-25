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


def calculate_checksum(data: bytes) -> int:
    if len(data) % 2 == 1:
        data += b"\x00"

    checksum = 0
    for i in range(0, len(data), 2):
        word = (data[i] << 8) + data[i + 1]
        checksum += word
        checksum = (checksum & 0xFFFF) + (checksum >> 16)  # carry around

    return ~checksum & 0xFFFF
