# Path: src/rdt/checksum.py
import zlib


def calculate_checksum(data: bytes) -> int:
    """
    Computes the CRC32 checksum for the given data.
    Ensures the result is an unsigned 32-bit integer (0 to 2^32-1).
    """
    # zlib.crc32 returns a signed 32-bit integer in Python 3.
    # Applying '& 0xffffffff' converts it to an unsigned 32-bit integer representation.
    return zlib.crc32(data) & 0xFFFFFFFF
