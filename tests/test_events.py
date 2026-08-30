"""Verify the live event stream mirrors the agent loop without a network."""

import json
import threading
from copy import deepcopy
from pathlib import Path

import pytest

from forge_agent.agent import Agent
from forge_agent.model import ModelReply, ToolCall
from forge_agent.workspace import ToolRegistry, Workspace


@pytest.fixture
def tmp_path() -> Path:
    path = Path.cwd() / ".test_tmp" / "events"
    path.mkdir(parents=True, exist_ok=True)
    return path


class ScriptedProvider:
    def __init__(self, replies: list[ModelReply]) -> None:
        self.replies = iter(replies)

    def complete(self, messages, tools):
        return next(self.replies)


def test_event_sequence_matches_tool_loop(tmp_path: Path) -> None:
    events: list[dict] = []
    provider = ScriptedProvider([
        ModelReply(tool_calls=[ToolCall("1", "write_file", '{"path":"hello.py","content":"print(42)"}')]),
        ModelReply(tool_calls=[ToolCall("2", "run_command", '{"command":"python hello.py"}')]),
        ModelReply(content="Created hello.py and verified it prints 42."),
    ])
    Agent(
        provider=provider,
        tools=ToolRegistry(Workspace(tmp_path), approve=lambda _: True),
        workspace=tmp_path,
        on_event=events.append,
    ).run("Create a program that prints 42")

    types = [e["type"] for e in events]
    assert types[0] == "task_started"
    assert events[0]["max_steps"] == 24
    # Each step emits: step, assistant, tool_call(s), tool_result(s)
    assert types == [
        "task_started",
        "step", "assistant", "tool_call", "tool_result",
        "step", "assistant", "tool_call", "tool_result",
        "step", "assistant", "finished",
    ]

    # tool_call carries parsed-able arguments; tool_result carries the ok flag.
    write_call = next(e for e in events if e["type"] == "tool_call" and e["name"] == "write_file")
    assert write_call["step"] == 1
    assert json.loads(write_call["arguments"])["path"] == "hello.py"
    write_res = next(e for e in events if e["type"] == "tool_result" and e["name"] == "write_file")
    assert json.loads(write_res["result"])["ok"] is True

    finished = events[-1]
    assert finished["summary"].endswith("prints 42.")
    assert finished["steps"] == 3
    assert finished["tool_calls"] == 2


def test_failed_tool_result_is_emitted_with_ok_false(tmp_path: Path) -> None:
    events: list[dict] = []
    provider = ScriptedProvider([
        ModelReply(tool_calls=[ToolCall("1", "read_file", '{"path":"missing.txt"}')]),
        ModelReply(content="Cannot read missing file."),
    ])
    Agent(
        provider=provider,
        tools=ToolRegistry(Workspace(tmp_path), approve=lambda _: True),
        workspace=tmp_path,
        on_event=events.append,
    ).run("Read a missing file")

    res = next(e for e in events if e["type"] == "tool_result")
    parsed = json.loads(res["result"])
    assert parsed["ok"] is False
    assert "File not found" in parsed["error"]


def test_cancel_event_stops_the_loop(tmp_path: Path) -> None:
    events: list[dict] = []
    cancel = threading.Event()
    provider = ScriptedProvider([ModelReply(tool_calls=[ToolCall("1", "list_files", "{}")])])
    agent = Agent(
        provider=provider,
        tools=ToolRegistry(Workspace(tmp_path), approve=lambda _: True),
        workspace=tmp_path,
        max_steps=10,
        on_event=events.append,
        cancel_event=cancel,
    )
    cancel.set()
    with pytest.raises(Exception, match="Stopped by user"):
        agent.run("anything")
    assert any(e["type"] == "stopped" and e["reason"] == "cancelled" for e in events)


def test_event_sink_failure_does_not_break_loop(tmp_path: Path) -> None:
    def bad_sink(_event: dict) -> None:
        raise RuntimeError("sink broken")
    provider = ScriptedProvider([ModelReply(content="ok")])
    result = Agent(
        provider=provider,
        tools=ToolRegistry(Workspace(tmp_path), approve=lambda _: True),
        workspace=tmp_path,
        on_event=bad_sink,
    ).run("survive a broken sink")
    assert result == "ok"