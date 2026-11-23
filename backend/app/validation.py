"""Shared input validation for API parameters."""
from __future__ import annotations

import re
from datetime import date

from fastapi import HTTPException

_ISO_DATE = re.compile(r'\d{4}-\d{2}-\d{2}')
# Restaurant data never predates 2000, and keeping dates in this range means date arithmetic
# (baselines, last year's weeks) can't overflow.
EARLIEST_DATE, LATEST_DATE = date(2000, 1, 1), date(2099, 12, 31)


def parse_date(value: str, label: str) -> date:
    """A real calendar date written as YYYY-MM-DD, or HTTP 422 with a message the UI can show."""
    if not isinstance(value, str) or not _ISO_DATE.fullmatch(value):
        raise HTTPException(422, f'{label} must be a date written like 2026-11-16.')
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise HTTPException(422, f'{label} {value} is not a real calendar date.') from None
    if not EARLIEST_DATE <= parsed <= LATEST_DATE:
        raise HTTPException(422, f'{label} must be between {EARLIEST_DATE.year} and {LATEST_DATE.year}.')
    return parsed
