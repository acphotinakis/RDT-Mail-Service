from rich.console import Console
from rich.logging import RichHandler
import logging

logging.basicConfig(level="DEBUG", handlers=[RichHandler()])
log = logging.getLogger("RDT")

log.info("Handshake started")
log.debug("SEQ=12 ACK=11 OK")
