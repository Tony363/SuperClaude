"""Telemetry helpers for recording plan-only command outcomes."""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .paths import get_metrics_dir

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_PLAN_ONLY_PATH: Optional[Path] = None


def _plan_only_file() -> Path:
    global _PLAN_ONLY_PATH
    if _PLAN_ONLY_PATH is None:
        _PLAN_ONLY_PATH = get_metrics_dir() / "plan_only.jsonl"
    return _PLAN_ONLY_PATH


def _sanitize(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, datetime):
        return value.isoformat() + "Z"

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, dict):
        return {str(key): _sanitize(val) for key, val in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [_sanitize(item) for item in value]

    return str(value)


def record_plan_only_event(event: Dict[str, Any]) -> None:
    payload = dict(event)
    payload.setdefault("timestamp", datetime.utcnow().isoformat() + "Z")
    payload = _sanitize(payload)

    path = _plan_only_file()
    try:
        with _LOCK:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception as exc:
        logger.debug("Failed to append plan-only telemetry: %s", exc, exc_info=True)
