"""Append-only local audit log with basic credential redaction."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class Transcript:
    SECRET_KEY = re.compile(r"(?i)(api[_-]?key|token|authorization|password|secret)")
    SECRET_VALUES = (
        re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
        re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}"),
        re.compile(
            r"(?i)\b[A-Z0-9_-]*(?:api[_-]?key|token|authorization|password|secret)"
            r"\s*[:=]\s*[^\s,;]+"
        ),
    )

    def __init__(self, workspace: Path) -> None:
        run_dir = workspace / ".forge-agent" / "runs"
        run_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        self.path = run_dir / f"{stamp}.jsonl"

    @classmethod
    def _redact(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: "[REDACTED]" if cls.SECRET_KEY.search(str(key)) else cls._redact(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [cls._redact(item) for item in value]
        if isinstance(value, tuple):
            return [cls._redact(item) for item in value]
        if isinstance(value, str):
            for pattern in cls.SECRET_VALUES:
                value = pattern.sub("[REDACTED]", value)
        return value

    def record(self, event: str, payload: Any) -> None:
        row = {
            "time": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "payload": self._redact(payload),
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
