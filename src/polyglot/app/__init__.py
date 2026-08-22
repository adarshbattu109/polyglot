import logging
from datetime import UTC, datetime
from pathlib import Path

import uvicorn

from polyglot.constants.filepaths import LOG_DIR

prefix = "polyglot"
timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
log_filename = f"{prefix}_{timestamp}.log"


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    filename=Path(LOG_DIR, log_filename),
)


logger = logging.getLogger(__name__)


def main(host: str = "127.0.0.1", port: int = 8000, reload: bool = True):
    """Starts the API server.

    Binds loopback by default: /translate accepts caller-supplied LLM connection details,
    so a server reachable from the network lets anyone on it aim those at arbitrary
    addresses. Pass host="0.0.0.0" only on a network you trust.
    """
    logger.info("Starting server at %s:%s", host, port)
    uvicorn.run("polyglot.app.main:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    main()
