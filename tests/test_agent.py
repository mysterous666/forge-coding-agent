from pathlib import Path
from copy import deepcopy

import pytest

from forge_agent.agent import Agent, AgentError
from forge_agent.model import ModelReply, ToolCall
from forge_agent.workspace import ToolRegistry, Workspace


class ScriptedProvider:
    def __init__(self, replies: list[ModelReply]) -> None:
        self.replies = iter(replies)
        self.requests = []

    def complete(self, messages, tools):
        self.requests.append((deepcopy(messages), deepcopy(tools)))
        return next(self.replies)


def test_end_to_end_tool_loop_without_network(tmp_path: Path) -> None:
    provider = ScriptedProvider([
        ModelReply(tool_calls=[ToolCall("1", "write_file", '{"path":"hello.py","content":"print(42)"}')]),
        ModelReply(tool_calls=[ToolCall("2", "run_command", '{"command":"python hello.py"}')]),
        ModelReply(content="Created hello.py and verified that it prints 42."),
    ])
    workspace = Workspace(tmp_path)
    result = Agent(
        provider=provider,
        tools=ToolRegistry(workspace, approve=lambda _: True),
        workspace=tmp_path,
    ).run("Create a Python program that prints 42")
    assert result.endswith("prints 42.")
    assert (tmp_path / "hello.py").read_text(encoding="utf-8") == "print(42)"
    second_request_messages = provider.requests[1][0]
    assert any(message.get("role") == "tool" for message in second_request_messages)


def test_repeated_identical_calls_are_blocked(tmp_path: Path) -> None:
    call = ToolCall("same", "read_file", '{"path":"missing.txt"}')
    provider = ScriptedProvider([
        ModelReply(tool_calls=[call]),
        ModelReply(tool_calls=[call]),
        ModelReply(tool_calls=[call]),
        ModelReply(content="Stopped retrying after the guard response."),
    ])
    Agent(
        provider=provider,
        tools=ToolRegistry(Workspace(tmp_path), approve=lambda _: True),
        workspace=tmp_path,
    ).run("Read a missing file")
    last_tool_result = provider.requests[-1][0][-1]["content"]
    assert "Repeated identical call blocked" in last_tool_result


def test_max_steps_is_a_hard_stop(tmp_path: Path) -> None:
    provider = ScriptedProvider([
        ModelReply(tool_calls=[ToolCall("1", "list_files", "{}")]),
    ])
    with pytest.raises(AgentError, match="Stopped after 1 steps"):
        Agent(
            provider=provider,
            tools=ToolRegistry(Workspace(tmp_path), approve=lambda _: True),
            workspace=tmp_path,
            max_steps=1,
        ).run("Keep working forever")
