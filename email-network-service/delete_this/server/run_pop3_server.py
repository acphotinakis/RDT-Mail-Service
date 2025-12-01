# import sys
# import time
# from src.config import Config
# from pop3.pop3_server import POP3Server


# def main():
#     """
#     Initializes and starts the POP3 server.
#     """
#     print("Starting POP3 server...")
#     server = POP3Server(Config.POP3_SERVER_HOST, Config.POP3_SERVER_PORT)
#     server.start()
#     print(f"POP3 Server running on {Config.POP3_SERVER_HOST}:{Config.POP3_SERVER_PORT}")

#     try:
#         while True:
#             time.sleep(1)
#     except KeyboardInterrupt:
#         print("\nStopping POP3 server...")
#         server.stop()
#         print("POP3 server stopped.")
#         sys.exit(0)


# if __name__ == "__main__":
#     main()
