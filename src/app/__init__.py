import uvicorn
import logging

logger = logging.getLogger(__name__)


def main(host: str = "0.0.0.0", port: int = 8000):
    logger.info(f"Starting server at {host}:{port}")
    uvicorn.run("app.main:app", host=host, port=port, reload=True)


if __name__ == "__main__":
    main()
