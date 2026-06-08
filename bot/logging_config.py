"""
Structured logging configuration for the trading bot.
Outputs to both console (INFO+) and a rotating log file (DEBUG+).
"""

import logging
import logging.handlers
import os
from pathlib import Path

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_FILE = LOG_DIR / "trading_bot.log"

_CONSOLE_FORMAT = "%(asctime)s  %(levelname)-8s  %(message)s"
_FILE_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
)
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: str = "DEBUG") -> None:
    """
    Call once at startup. Safe to call multiple times (idempotent).

    Args:
        level: Root logger level string (DEBUG / INFO / WARNING / ERROR).
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    if root.handlers:
        # Already configured — skip to avoid duplicate handlers.
        return

    root.setLevel(logging.DEBUG)

    # ── Console handler ──────────────────────────────────────────────────────
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    console_handler.setFormatter(logging.Formatter(_CONSOLE_FORMAT, _DATE_FORMAT))

    # ── File handler (rotating, max 5 MB × 3 backups) ────────────────────────
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(_FILE_FORMAT, _DATE_FORMAT))

    root.addHandler(console_handler)
    root.addHandler(file_handler)

    logging.getLogger("urllib3").setLevel(logging.WARNING)  # reduce HTTP noise
    logging.getLogger("requests").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Convenience wrapper so modules don't import `logging` directly."""
    return logging.getLogger(name)
