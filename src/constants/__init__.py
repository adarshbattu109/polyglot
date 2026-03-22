import logging
from datetime import datetime
from pathlib import Path

from constants.filepaths import LOG_DIR

prefix = "polyglot"
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = f"{prefix}_{timestamp}.log"


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    filename=Path(LOG_DIR, log_filename),
)
