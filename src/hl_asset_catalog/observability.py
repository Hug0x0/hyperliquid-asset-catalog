from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import UTC, datetime

_SENSITIVE = re.compile(r"(?i)(api[_-]?key|token|secret|password)=([^&\s]+)")


def redact_log(value: object) -> str:
    return _SENSITIVE.sub(lambda match: f"{match.group(1)}=<redacted>", str(value))


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "component": record.name,
            "operation": getattr(record, "operation", "log"),
            "correlation_id": getattr(record, "correlation_id", "unknown"),
            "message": redact_log(record.getMessage()),
        }
        return json.dumps(payload, sort_keys=True)


def configure_logging(level: str, *, json_logs: bool = False) -> str:
    correlation_id = uuid.uuid4().hex
    handler = logging.StreamHandler()
    handler.setFormatter(
        JsonFormatter() if json_logs else logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    return correlation_id


def log_summary(
    logger: logging.Logger,
    *,
    operation: str,
    correlation_id: str,
    counts: dict[str, int | float],
) -> None:
    logger.info(
        "run summary %s",
        json.dumps(counts, sort_keys=True),
        extra={"operation": operation, "correlation_id": correlation_id},
    )
