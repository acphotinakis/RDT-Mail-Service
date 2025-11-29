import pytest
from src.rdt.rdt_packet import make_data_packet, unpack_and_validate

def test_make_and_validate_data_packet():
    """
    Tests that a created data packet can be successfully validated.
    This directly tests the checksum logic.
    """
    seq_num = 1
    data = b"This is a test."
    
    # 1. Create a packet
    packet_bytes = make_data_packet(seq_num, data)
    
    # 2. Validate the packet
    validated_packet = unpack_and_validate(packet_bytes)
    
    # 3. Assert the packet is valid and correct
    assert validated_packet is not None
    assert not validated_packet["is_ack"]
    assert validated_packet["seq"] == seq_num
    assert validated_packet["data"] == data

def test_invalid_checksum_is_rejected():
    """
    Tests that a packet with a manipulated checksum is rejected.
    """
    seq_num = 0
    data = b"Another test."
    
    # Create a valid packet
    packet_bytes = make_data_packet(seq_num, data)
    
    # Manipulate the packet to invalidate the checksum.
    # A simple way is to flip a bit in the byte string.
    # Let's flip a bit in the data part, which is less likely to break unpickling.
    # This is a bit brittle, but effective for a test.
    # A more robust way would be to unpickle, change checksum, and repack.
    import pickle
    pkt_dict = pickle.loads(packet_bytes)
    pkt_dict['checksum'] += 1 # Invalidate the checksum
    corrupted_packet_bytes = pickle.dumps(pkt_dict)

    # Try to validate the corrupted packet
    validated_packet = unpack_and_validate(corrupted_packet_bytes)
    
    # Assert that the packet is rejected
    assert validated_packet is None
