# Path: src/rdt/checksum.py
import zlib
import logging

log = logging.getLogger(__name__)


def calculate_checksum(data: bytes) -> int:
    """
    Computes the CRC32 checksum for the given data.
    Ensures the result is an unsigned 32-bit integer (0 to 2^32-1).
    """
    log.debug(f"Calculating checksum for data of length {len(data)} bytes.")
    checksum = zlib.crc32(data) & 0xFFFFFFFF
    log.debug(f"Checksum calculated: {checksum}")
    return checksum
