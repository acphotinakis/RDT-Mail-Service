# import sys
# import time
# from src.config import Config
# from smtp.smtp_server import SMTPServer


# def main():
#     """
#     Initializes and starts the SMTP server.
#     """
#     print("Starting SMTP server...")
#     server = SMTPServer(Config.SMTP_SERVER_HOST, Config.SMTP_SERVER_PORT)
#     server.start()
#     print(f"SMTP Server running on {Config.SMTP_SERVER_HOST}:{Config.SMTP_SERVER_PORT}")

#     try:
#         while True:
#             time.sleep(1)
#     except KeyboardInterrupt:
#         print("\nStopping SMTP server...")
#         server.stop()
#         print("SMTP server stopped.")
#         sys.exit(0)


# if __name__ == "__main__":
#     main()
