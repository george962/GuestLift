"""Logging setup. Level comes from GUESTLIFT_LOG_LEVEL (default INFO)."""
from __future__ import annotations

import logging
import os

logger = logging.getLogger('guestlift')


def setup_logging() -> None:
    level = os.getenv('GUESTLIFT_LOG_LEVEL', 'INFO').upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format='%(asctime)s %(levelname)s %(name)s %(message)s',
    )
