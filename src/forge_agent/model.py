"""Model-neutral request and response types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: str


@dataclass(frozen=True)
class ModelReply:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)


class ModelProvider(Protocol):
    def complete(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> ModelReply:
        """Return one assistant turn."""


class OpenAIProvider:
    """Thin adapter around the model vendor's native tool-calling API."""

    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        base_url: str | None = None,
        timeout: float = 90.0,
    ) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - installation concern
            raise RuntimeError("Install the project first: pip install -e .") from exc
        kwargs: dict[str, Any] = {"api_key": api_key, "timeout": timeout}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = OpenAI(**kwargs)
        self._model = model

    def complete(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> ModelReply:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        message = response.choices[0].message
        calls = [
            ToolCall(
                id=call.id,
                name=call.function.name,
                arguments=call.function.arguments or "{}",
            )
            for call in (message.tool_calls or [])
        ]
        return ModelReply(content=message.content or "", tool_calls=calls)

