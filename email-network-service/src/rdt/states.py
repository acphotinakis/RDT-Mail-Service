# Path: src/rdt/states.py
from enum import Enum


class SenderState(Enum):
    WAIT_FOR_CALL_0 = 0  # Waiting for data from app to send with SEQ 0
    WAIT_FOR_ACK_0 = 1  # Waiting for ACK 0 from network
    WAIT_FOR_CALL_1 = 2  # Waiting for data from app to send with SEQ 1
    WAIT_FOR_ACK_1 = 3  # Waiting for ACK 1 from network


class ReceiverState(Enum):
    WAIT_FOR_0 = 0  # Waiting for packet SEQ 0 from below
    WAIT_FOR_1 = 1  # Waiting for packet SEQ 1 from below
