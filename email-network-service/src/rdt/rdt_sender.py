"""
File: sender.py
----------------------------------------
Description:
    Provides Selective Repeat functionality in the UDP protocol for sending packets.

Author:
    Caleb Talbott

Last Edited:
    2025-11-1
"""

import datetime
import pickle
import socket
import threading
import time
from src.rdt.rdt_util import calculate_checksum
from src.common.logger import get_class_logger


class RDTSender:
    """
    Provides Selective Repeat functionality in the UDP protocol for sending packets.
    """

    def __init__(
        self,
        port: int,
        timeout=5,
        src_address="127.0.0.1",
        dst_address="127.0.0.1",
        window_size=8,
    ):
        """
        Constructor for an RDT packet sender.

        Args:
            port (int): The base port for the RDT sender is configured accordingly. The receiving port is set to the
                        specified port, while the sending port is set to one increment above the specified port.
            timeout (int):  The amount of time the sender will wait before retransmitting unACKed packets. Default: 4
            src_address (str):  The address of the sender's host. Default: 127.0.0.1
            dst_address (str):  The address of the receiver's host. Default: 127.0.0.1
            window_size (int):  The size of the window including sequence number that can be sent in the protocol. Default: 8
        """
        self.log = get_class_logger(self)
        self.src_address = src_address
        self.dst_address = dst_address
        self.port = port
        self.log.debug(f"Sender Port: {self.port}")

        self.socket = None

        # A protocol must implement the same window size in sender and receiver
        self.window_size = window_size
        self.seq_num = 0
        self.seq_base = 0
        self.window = {}
        self.received_acks = {}
        self.listener = None
        self.timeout = timeout

        # Lock prevents multiple threads accessing and overwriting shared memory
        self.lock = threading.Lock()

        # Sender status booleans
        self.is_sending = False
        self.is_terminated = False

    def connect_to_receiver(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.dst_address, self.port))
        self.is_terminated = False

    def send_data(self, data: list[bytes]):
        self.log.debug(f"{self.socket}, {self.listener}")
        if not self.socket:
            self.log.error(
                "Sender: Connection must be established before sending!"
            )

        # Start our ACK listener thread to receive new ACKs
        if not self.listener:
            self.listener = threading.Thread(target=self.receive_acks)
            self.listener.start()

        self.is_sending = True  # Indicate the sending process started
        data_list = (
            data.copy()
        )  # Create a copy of the data to ensure original data is not overwritten
        starting_seq = (
            self.seq_num
        )  # Important for checking if a packet is the last one
        self.log.debug(
            f"Sender: Starting Seq - {starting_seq} | Seq Base: {self.seq_base}"
        )

        try:
            # Loop until all data has been sent once or if an ACK has not been verified AND if the sender is still
            # sending
            while (
                len(data_list) > 0
                or any(not ack for ack in self.received_acks.values())
            ) and self.is_sending:
                # Loop if the current seq num is in the window, and we still have data to send when the sender is
                # sending
                while (
                    self.seq_base <= self.seq_num < self.seq_base + self.window_size
                    and len(data_list) > 0
                    and self.is_sending
                ):
                    # Pop the next chunk and send the packet with the current seq num
                    chunk = data_list.pop(0)
                    self.send_packet(
                        self.seq_num,
                        chunk,
                        self.seq_num == starting_seq + len(data) - 1,
                    )
                    self.log.debug(f"Sender: Sent {self.seq_num}")

                    # Wait until resource window/ACK resources are available and place the current packet in the window
                    with self.lock:
                        self.window[self.seq_num] = (chunk, datetime.datetime.now())
                        self.received_acks[self.seq_num] = False
                    self.seq_num += 1  # Move to next seq num in window

                with self.lock:
                    # If the seq num at the base of the window has been ACKed, then remove it and shift window by 1
                    while (
                        self.seq_base in self.window
                        and self.received_acks.get(self.seq_base, False)
                        and self.is_sending
                    ):
                        del self.received_acks[self.seq_base]
                        del self.window[self.seq_base]
                        self.seq_base += 1
                        self.log.debug(f"Sender: {self.seq_base}")

                # The "is_sending" checks are important because at any time the sender can be terminated
                if self.is_sending:
                    with self.lock:
                        current_time = datetime.datetime.now()
                        # Iterate through all packets in the window
                        for seq in list(self.window.keys()):
                            # If a packet has not received and ACK and a timeout has occurred, resend the packet
                            if (
                                (
                                    seq in self.received_acks
                                    and not self.received_acks[seq]
                                )
                                and current_time - self.window[seq][1]
                                > datetime.timedelta(seconds=self.timeout)
                                and self.is_sending
                            ):
                                self.log.debug(
                                    f"Sender: Retransmitting {seq}"
                                )
                                # Update the window with the new sending time
                                self.window[seq] = (
                                    self.window[seq][0],
                                    datetime.datetime.now(),
                                )
                                # Retransmit the packet
                                self.send_packet(seq, self.window[seq][0])

                # Wait a brief time until the next iteration, allows other threads to access shared resources
                time.sleep(0.1)

            self.is_sending = False
            self.log.info(
                f"Sender: All data sent and acknowledged or connection terminated. | is_sending {self.is_sending}"
            )

        except Exception as e:
            self.log.error(f"Sender Error: {str(e)}")

    def send_packet(self, seq_num: int, data: bytes, final_pkt=False):
        """
        Send a packet of data with an associated sequence number to the destination host over the sending port.
        The termination flag indicates whether to terminate the connection with the receiver.

        Args:
            seq_num (int): The sequence number of a packet.
            data (bytes): The payload of data to send in bytes.
            terminate (bool): A flag that indicates whether a connection should be terminated. Default: False
        """
        self.log.debug(f"Sender: Final Packet {final_pkt}")
        payload = {
            "final": final_pkt,
            "seq": seq_num,
            "data": data,
        }
        # Calculate the checksum of the data payload and store it in the packet
        initial_payload = pickle.dumps(payload)
        payload["checksum"] = calculate_checksum(initial_payload)
        final_payload = pickle.dumps(payload)

        try:
            # Send the packet to the destination host using the sending port
            pkt_len = len(final_payload).to_bytes(4, "big")
            final_pkt = pkt_len + final_payload
            self.log.debug(f"Sender: Sending {final_pkt}")
            self.socket.sendall(pkt_len + final_payload)
        except OSError:
            self.log.info(
                "Sender: End host socket was closed or an error occurred on the OS, terminating socket..."
            )
            self.is_sending = False
            self.is_terminated = True
        except Exception as e:
            self.log.error(f"Failed to send packet: {e}")

    def receive_acks(self):
        """
        The target function for the receiving thread that listens for incoming ACK messages entering
        through the receiving port. First it binds the receiving socket to the receiving port.
        After an ACK is received, the corresponding packet with the related sequence number is marked as received.
        Finally, if a FIN ACK is received, the termination sequence ends and the thread is closed.

        Returns:
            Will return early if there is an error binding the reception port.
        """
        # Receive ACKs on the receiving port if the sender is still sending and is not terminated
        while self.is_sending or not self.is_terminated:
            try:
                data = self.socket.recv(2048)
                if len(data) == 0:
                    break

                pkt = pickle.loads(data)

                # If a pure ACK packet is received, indicate that a packet was ACKed
                if "ack" in pkt:
                    self.received_acks[pkt["ack"]] = True
                    self.log.debug(f"Sender: Received ACK {pkt['ack']}")

            except (
                socket.timeout
            ):  # Timeouts prevent the shared resources from being blocked by the thread
                continue
            except OSError as e:
                self.log.info(f"Sender: Socket closed or error: {str(e)}")
                break
            except Exception as e:
                self.log.error(
                    f"Sender: Exception in receive_acks: {str(e)}"
                )
                break

    def terminate_connection(self):
        """
        Closes the sender's sending and receiving sockets and sets the sender's sending and termination statuses.
        """
        self.log.info("Sender: Closing connection!")
        self.is_sending = False

        # Attempt to close the sockets
        try:
            self.socket.close()
        except:
            pass

        # Join our listening thread if it is alive and it is not called in the receiving thread
        if self.listener.is_alive() and threading.current_thread() is not self.listener:
            self.log.info("Sender: Joining receiving thread!")
            self.listener.join()
            self.listener = None

        self.is_terminated = True
