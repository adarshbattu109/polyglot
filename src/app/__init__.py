import logging
from datetime import datetime
from pathlib import Path

import uvicorn

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


logger = logging.getLogger(__name__)


def main(host: str = "0.0.0.0", port: int = 8000):
    logger.info(f"Starting server at {host}:{port}")
    uvicorn.run("app.main:app", host=host, port=port, reload=True)


if __name__ == "__main__":
    main()
