"""Logging setup. GUESTLIFT_LOG_LEVEL (default INFO); GUESTLIFT_LOG_FORMAT=json for log shippers."""
from __future__ import annotations

import contextvars
import json
import logging
import os

logger = logging.getLogger('guestlift')
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar('request_id', default='-')


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {'ts': self.formatTime(record), 'level': record.levelname, 'logger': record.name,
                 'request_id': getattr(record, 'request_id', '-'), 'msg': record.getMessage()}
        if record.exc_info:
            entry['exc'] = self.formatException(record.exc_info)
        return json.dumps(entry)


def setup_logging() -> None:
    level = os.getenv('GUESTLIFT_LOG_LEVEL', 'INFO').upper()
    handler = logging.StreamHandler()
    if os.getenv('GUESTLIFT_LOG_FORMAT', '').lower() == 'json':
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s'))
    handler.addFilter(_RequestIdFilter())
    logging.basicConfig(level=getattr(logging, level, logging.INFO), handlers=[handler], force=True)
