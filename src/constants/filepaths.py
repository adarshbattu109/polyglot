"""File to house all file paths for the project."""

from pathlib import Path

LOG_DIR = Path("logs")
ARTIFACTS_DIR = Path("artifacts")

LOG_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
