# src/rdt/rdt_packet.py
import struct
import logging
import zlib
from src.rdt.checksum import calculate_checksum

log = logging.getLogger(__name__)

# --- Packet Constants ---
TYPE_DATA = 0
TYPE_ACK = 1
HEADER_FORMAT = "!BBI"  # Seq (1B), Type (1B), Checksum (4B)
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)


# def calculate_checksum(data: bytes) -> int:
#     """Computes CRC32 checksum."""
#     return zlib.crc32(data) & 0xFFFFFFFF


def make_packet(seq_num: int, is_ack: bool, payload: bytes) -> bytes:
    """
    Constructs a binary packet.
    Format: [SEQ: 1B] [TYPE: 1B] [CHECKSUM: 4B] [PAYLOAD: N Bytes]
    """
    pkt_type = TYPE_ACK if is_ack else TYPE_DATA

    # 1. Create header with Checksum = 0 temporarily
    temp_header = struct.pack(HEADER_FORMAT, seq_num, pkt_type, 0)

    # 2. Calculate checksum over the entire packet (header + payload)
    checksum = calculate_checksum(temp_header + payload)

    # 3. Re-pack header with valid checksum
    final_header = struct.pack(HEADER_FORMAT, seq_num, pkt_type, checksum)

    return final_header + payload


def make_data_packet(seq_num: int, data: bytes) -> bytes:
    return make_packet(seq_num, False, data)


def make_ack_packet(seq_num: int) -> bytes:
    return make_packet(seq_num, True, b"")


def unpack_and_validate(packet_bytes: bytes) -> dict | None:
    """
    Parses binary packet, verifies checksum, and returns a dict
    compatible with the rest of the application.
    """
    if len(packet_bytes) < HEADER_SIZE:
        log.warning(f"Packet too short: {len(packet_bytes)} bytes.")
        return None

    try:
        # 1. Split Header and Payload
        header_bytes = packet_bytes[:HEADER_SIZE]
        payload = packet_bytes[HEADER_SIZE:]

        # 2. Unpack Header
        seq, pkt_type, received_checksum = struct.unpack(HEADER_FORMAT, header_bytes)

        # 3. Verify Checksum
        # Reconstruct header with 0 checksum to verify validity
        clean_header = struct.pack(HEADER_FORMAT, seq, pkt_type, 0)
        calculated_checksum = calculate_checksum(clean_header + payload)

        if received_checksum != calculated_checksum:
            log.warning(
                f"Checksum mismatch! Got {received_checksum}, expected {calculated_checksum}"
            )
            return None

        # 4. Return Dict Interface
        return {
            "is_ack": (pkt_type == TYPE_ACK),
            "seq": seq,
            "data": payload,
            "checksum": received_checksum,
        }

    except struct.error as e:
        log.error(f"Packet structure error: {e}")
        return None
