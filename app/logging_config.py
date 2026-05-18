"""Standard logging setup. Imported once from `main.py` at import time."""
import logging
import sys


def configure(level: str = "INFO") -> None:
    """Configure root logger with a dev-friendly format."""
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter(
        fmt="%(asctime)s [%(levelname)-7s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    ))
    root = logging.getLogger()
    # Drop pre-existing handlers (e.g. uvicorn's reload duplicates them)
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))