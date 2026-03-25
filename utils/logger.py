"""
utils/logger.py
───────────────
Structured colour logging factory.
All modules call get_logger(__name__) to obtain a named logger.
"""
from __future__ import annotations

import logging
import os
import sys

try:
    import colorlog

    _HAS_COLORLOG = True
except ImportError:
    _HAS_COLORLOG = False

_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
_CONFIGURED: set[str] = set()


def get_logger(name: str) -> logging.Logger:
    """Return (and lazily configure) a named logger."""
    logger = logging.getLogger(name)

    if name in _CONFIGURED:
        return logger

    logger.setLevel(getattr(logging, _LOG_LEVEL, logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, _LOG_LEVEL, logging.INFO))

        if _HAS_COLORLOG:
            formatter = colorlog.ColoredFormatter(
                "%(log_color)s%(asctime)s [%(levelname)-8s]%(reset)s "
                "%(cyan)s%(name)s%(reset)s – %(message)s",
                datefmt="%H:%M:%S",
                log_colors={
                    "DEBUG": "white",
                    "INFO": "green",
                    "WARNING": "yellow",
                    "ERROR": "red",
                    "CRITICAL": "bold_red",
                },
            )
        else:
            formatter = logging.Formatter(
                "%(asctime)s [%(levelname)-8s] %(name)s – %(message)s",
                datefmt="%H:%M:%S",
            )

        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False

    _CONFIGURED.add(name)
    return logger
