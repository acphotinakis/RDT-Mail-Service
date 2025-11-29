import socket
import threading
import time
import logging
from src.config import SMTP_SERVER_HOST, SMTP_SERVER_PORT, CLIENT_IP, CLIENT_LISTENING_PORT
from src.smtp.smtp_server import SMTPServer
from src.smtp.smtp_client import SMTPClient

# Configure Logging to see what's happening
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
)
log = logging.getLogger("ReproductionScript")


def run_server(server_instance):
    try:
        server_instance.start()
        # Keep main thread alive until stopped
        while server_instance._running:
            time.sleep(0.5)
    except Exception as e:
        log.error(f"Server crashed: {e}")


def run_client_session(session_name):
    log.info(f"--- STARTING CLIENT SESSION: {session_name} ---")
    client = SMTPClient()

    # We must enforce the SAME port to reproduce the bug
    # Note: SMTPClient __init__ already binds to CLIENT_LISTENING_PORT (2526)
    # We just need to make sure the previous one is closed properly.

    try:
        success = client.send_email(
            "test@localhost", "recipient@localhost", f"Subject {session_name}", "Body content"
        )
        if success:
            log.info(f"--- SESSION {session_name} SUCCESS ---")
        else:
            log.error(f"--- SESSION {session_name} FAILED ---")
    except Exception as e:
        log.exception(f"--- SESSION {session_name} EXCEPTION ---")
    finally:
        # Ensure socket is closed so we can reuse the port
        if client.sock:
            client.sock.close()
        # Stop dispatcher to kill threads
        if client.dispatcher:
            client.dispatcher.stop()


def main():
    log.info("=== REPRODUCTION SCRIPT STARTED ===")

    # 1. Start Server
    server = SMTPServer(SMTP_SERVER_HOST, SMTP_SERVER_PORT)
    server_thread = threading.Thread(target=run_server, args=(server,), daemon=True)
    server_thread.start()

    # Give server a moment to spin up
    time.sleep(1)

    # 2. Run Session 1
    run_client_session("ONE")

    # 3. INSPECT SERVER STATE
    # This is the critical check. After Session 1, the state for the client should be GONE.
    client_addr = (CLIENT_IP, CLIENT_LISTENING_PORT)

    log.info("--- INSPECTING SERVER STATE ---")
    keys = list(server.rdt_receiver.expected_seqs.keys())
    log.info(f"Server RDT Known Clients: {keys}")

    if client_addr in keys:
        log.critical(
            f"FAILURE: Server still remembers {client_addr} with SEQ {server.rdt_receiver.expected_seqs[client_addr]}"
        )
        log.critical("The reset_state() fix did NOT work.")
    else:
        log.info("SUCCESS: Server has forgotten the client. State was reset.")

    time.sleep(2)  # Wait a bit to ensure sockets are free

    # 4. Run Session 2 (Same Port)
    # If the state wasn't cleared, this will hang.
    run_client_session("TWO")

    log.info("=== SCRIPT FINISHED ===")
    server.stop()


if __name__ == "__main__":
    main()
