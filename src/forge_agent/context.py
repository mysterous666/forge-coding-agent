"""Deterministic context compaction that preserves tool-call structure."""

from __future__ import annotations

import json
from typing import Any


class ContextManager:
    def __init__(self, *, max_chars: int = 80_000, max_tool_chars: int = 12_000) -> None:
        if max_chars < 4_000:
            raise ValueError("max_chars must be at least 4000")
        self.max_chars = max_chars
        self.max_tool_chars = max_tool_chars
        self.last_removed: int = 0
        self.max_chars_limit = max_chars

    @staticmethod
    def _size(message: dict[str, Any]) -> int:
        return len(json.dumps(message, ensure_ascii=False))

    def compact(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized = [dict(message) for message in messages]
        for message in normalized:
            if message.get("role") == "tool" and len(str(message.get("content", ""))) > self.max_tool_chars:
                content = str(message["content"])
                message["content"] = content[: self.max_tool_chars] + "\n...[tool output truncated]"
        if sum(map(self._size, normalized)) <= self.max_chars or len(normalized) <= 3:
            self.last_removed = 0
            return normalized

        prefix = normalized[:2]
        tail = normalized[2:]
        blocks: list[list[dict[str, Any]]] = []
        index = 0
        while index < len(tail):
            block = [tail[index]]
            index += 1
            if block[0].get("role") == "assistant" and block[0].get("tool_calls"):
                while index < len(tail) and tail[index].get("role") == "tool":
                    block.append(tail[index])
                    index += 1
            blocks.append(block)

        budget = int(self.max_chars * 0.65)
        kept: list[list[dict[str, Any]]] = []
        used = 0
        for block in reversed(blocks):
            block_size = sum(map(self._size, block))
            if kept and used + block_size > budget:
                break
            kept.append(block)
            used += block_size
        kept.reverse()
        removed = len(blocks) - len(kept)
        self.last_removed = removed
        summary = {
            "role": "system",
            "content": f"Context manager removed {removed} older interaction blocks. Re-inspect files before editing; do not assume omitted tool results.",
        }
        return prefix + [summary] + [message for block in kept for message in block]

