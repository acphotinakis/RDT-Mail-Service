# src/rdt/rdt_config.py
RDT_TIMEOUT = 1.0  # Seconds to wait before retransmission
RDT_WINDOW_SIZE = 10  # GBN Window size
RDT_RECV_BUFSIZE = 4096  # Max UDP packet size to receive
# Max size for payload chunks to ensure the resulting JSON fits into UDP buffer
# Adjust based on PACKET_BUFFER_SIZE in config
MAX_PAYLOAD_SIZE = 1024
