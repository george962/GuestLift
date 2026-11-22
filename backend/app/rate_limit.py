"""Per-user limit on AI questions to cap model spend and abuse.

In-memory sliding window: correct for one API process. If you run several
replicas, move this to Redis or put a limit at the gateway too.
"""
from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException

from .local_auth import authenticated_subject

_WINDOW_SECONDS = 3600
_hits: dict[str, deque] = defaultdict(deque)
_lock = threading.Lock()


def _limit() -> int:
    try:
        return int(os.getenv('GUESTLIFT_AI_QUESTIONS_PER_HOUR', '60'))
    except ValueError:
        return 60


def check(subject: str, now: float | None = None) -> None:
    limit = _limit()
    if limit <= 0:
        return
    now = time.monotonic() if now is None else now
    with _lock:
        q = _hits[subject]
        while q and q[0] <= now - _WINDOW_SECONDS:
            q.popleft()
        if len(q) >= limit:
            retry = int(q[0] + _WINDOW_SECONDS - now) + 1
            raise HTTPException(status_code=429, detail='Too many AI questions; try again later.',
                                headers={'Retry-After': str(retry)})
        q.append(now)


def reset() -> None:
    with _lock:
        _hits.clear()


def ai_question_subject(sub: str = Depends(authenticated_subject)) -> str:
    check(sub)
    return sub
