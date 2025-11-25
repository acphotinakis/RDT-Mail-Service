import logging

log = logging.getLogger(__name__)
log.debug("Initializing rdt package...")

from .rdt_sender import RDTSender
from .rdt_receiver import RDTReceiver

log.debug("rdt package initialized.")