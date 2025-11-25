# Path: src/rdt/rdt_packet.py
import pickle
import logging
from .checksum import calculate_checksum

log = logging.getLogger(__name__)


def make_data_packet(seq_num: int, data: bytes) -> bytes:
    """Creates a serialized DATA packet with seq number, payload, and checksum."""
    log.debug(f"Creating DATA packet for SEQ={seq_num} with payload size={len(data)}")
    pkt_dict = {"is_ack": False, "seq": seq_num, "data": data}
    # Calculate checksum on the pickled data dictionary
    raw_pickle = pickle.dumps(pkt_dict)
    pkt_dict["checksum"] = calculate_checksum(raw_pickle)
    # Return final pickled packet including checksum
    final_packet = pickle.dumps(pkt_dict)
    log.debug(f"DATA packet created with size={len(final_packet)} bytes.")
    return final_packet


def make_ack_packet(seq_num: int) -> bytes:
    """Creates a serialized ACK packet for a given sequence number."""
    log.debug(f"Creating ACK packet for SEQ={seq_num}")
    pkt_dict = {
        "is_ack": True,
        "seq": seq_num,
        # ACK packets don't strictly need data payload, but structure should be consistent
        "data": b"",
    }
    raw_pickle = pickle.dumps(pkt_dict)
    pkt_dict["checksum"] = calculate_checksum(raw_pickle)
    final_packet = pickle.dumps(pkt_dict)
    log.debug(f"ACK packet created with size={len(final_packet)} bytes.")
    return final_packet


def unpack_and_validate(packet_bytes: bytes) -> dict | None:
    """
    Deserializes a packet and validates its checksum.
    Returns the packet dictionary if valid, or None if corrupt.
    """
    log.debug(f"Validating packet of size {len(packet_bytes)} bytes.")
    try:
        pkt_dict = pickle.loads(packet_bytes)

        # Verify all required fields exist
        if not all(key in pkt_dict for key in ["is_ack", "seq", "data", "checksum"]):
            log.warning("Packet validation failed: Missing required fields.")
            return None

        received_checksum = pkt_dict["checksum"]

        # Create a temporary copy without the checksum to re-calculate it
        data_to_check = pkt_dict.copy()
        del data_to_check["checksum"]

        calculated_checksum = calculate_checksum(pickle.dumps(data_to_check))

        if received_checksum == calculated_checksum:
            log.debug("Packet checksum is valid.")
            return pkt_dict
        else:
            log.warning(
                f"Packet validation failed: Checksum mismatch. Got {received_checksum}, expected {calculated_checksum}."
            )
            return None

    except (pickle.UnpicklingError, Exception):
        log.exception("Packet validation failed with an exception.")
        return None
