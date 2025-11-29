# import threading
# import time

# from src.rdt.rdt_receiver import RDTReceiver
# from src.rdt.rdt_sender import RDTSender

# MAX_CLIENTS = 8
# STARTING_PORT = 47129
# shutdown_event = threading.Event()


# def main():
#     connections = {}
#     for i in range(MAX_CLIENTS):
#         curr_port = STARTING_PORT + i
#         receiver = RDTReceiver(curr_port)
#         connections[curr_port] = (
#             threading.Thread(target=receiver_thread, args=(receiver,)),
#             receiver,
#         )

#         connections[curr_port][0].start()

#     sender1 = RDTSender(STARTING_PORT)
#     sender2 = RDTSender(STARTING_PORT + 1)
#     sender1.connect_to_receiver()
#     sender2.connect_to_receiver()

#     sender1.send_data([b"Cool Ranch", b"Doritos"])
#     sender2.send_data([b"Are Better", b"Than Nacho Cheese"])

#     sender1.terminate_connection()
#     sender2.terminate_connection()

#     time.sleep(2)
#     shutdown(connections)


# def shutdown(connections: dict):
#     print("SHUTTING DOWN SERVER")
#     shutdown_event.set()
#     for i in range(MAX_CLIENTS):
#         curr_port = STARTING_PORT + i
#         print(f"Server: Attempting to close: {STARTING_PORT + i}")
#         connections[curr_port][1].terminate_connection()
#         connections[curr_port][0].join()


# def receiver_thread(receiver: RDTReceiver):
#     while not shutdown_event.is_set():
#         try:
#             if not receiver.conn:
#                 result = receiver.start_accepting()
#                 if not result:
#                     continue
#         except OSError:
#             break
#         messages = receiver.receive_messages()
#         if len(messages) > 0:
#             print(f"Server: Received {messages} from {receiver.port}")
#         else:
#             receiver.cleanup()


# if __name__ == "__main__":
#     main()
