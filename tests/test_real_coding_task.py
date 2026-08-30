"""A realistic, deterministic coding-task acceptance test.

The scripted model keeps the test offline and reproducible, while every file read,
edit, and test command is performed by the production Agent and ToolRegistry.
"""

import json
import sys
from pathlib import Path

from forge_agent.agent import Agent
from forge_agent.model import ModelReply, ToolCall
from forge_agent.workspace import ToolRegistry, Workspace


class InspectingRepairProvider:
    """Drive a genuine inspect-fail-edit-verify workflow and validate observations."""

    def __init__(self) -> None:
        self.turn = 0

    def complete(self, messages, tools):
        tool_names = {item["function"]["name"] for item in tools}
        assert {"read_file", "replace_text", "run_command"} <= tool_names
        tool_results = [
            json.loads(message["content"])
            for message in messages
            if message.get("role") == "tool"
        ]

        if self.turn == 0:
            reply = ModelReply(tool_calls=[
                ToolCall("read", "read_file", '{"path":"calculator.py"}')
            ])
        elif self.turn == 1:
            assert "return a - b" in tool_results[-1]["data"]["content"]
            reply = ModelReply(tool_calls=[
                ToolCall(
                    "red",
                    "run_command",
                    json.dumps({"command": f'"{sys.executable}" -m unittest -q'}),
                )
            ])
        elif self.turn == 2:
            assert tool_results[-1]["data"]["exit_code"] != 0
            assert "FAIL" in tool_results[-1]["data"]["output"]
            reply = ModelReply(tool_calls=[
                ToolCall(
                    "fix",
                    "replace_text",
                    json.dumps({
                        "path": "calculator.py",
                        "old": "return a - b",
                        "new": "return a + b",
                    }),
                )
            ])
        elif self.turn == 3:
            assert tool_results[-1]["ok"] is True
            reply = ModelReply(tool_calls=[
                ToolCall(
                    "green",
                    "run_command",
                    json.dumps({"command": f'"{sys.executable}" -m unittest -q'}),
                )
            ])
        else:
            assert tool_results[-1]["data"]["exit_code"] == 0
            assert "OK" in tool_results[-1]["data"]["output"]
            reply = ModelReply(content="Fixed add() and verified the full unittest suite passes.")
        self.turn += 1
        return reply


def test_agent_repairs_a_real_failing_project(tmp_path: Path) -> None:
    (tmp_path / "calculator.py").write_text(
        "def add(a, b):\n    return a - b\n", encoding="utf-8"
    )
    (tmp_path / "test_calculator.py").write_text(
        "import unittest\n"
        "from calculator import add\n\n"
        "class CalculatorTests(unittest.TestCase):\n"
        "    def test_adds_positive_and_negative_values(self):\n"
        "        self.assertEqual(add(7, -2), 5)\n\n"
        "if __name__ == '__main__':\n"
        "    unittest.main()\n",
        encoding="utf-8",
    )

    workspace = Workspace(tmp_path)
    result = Agent(
        provider=InspectingRepairProvider(),
        tools=ToolRegistry(workspace, approve=lambda _: True),
        workspace=tmp_path,
    ).run("Fix the failing calculator test. Inspect first and verify the fix.")

    assert "verified" in result
    assert "return a + b" in (tmp_path / "calculator.py").read_text(encoding="utf-8")
    transcript = next((tmp_path / ".forge-agent" / "runs").glob("*.jsonl"))
    events = [json.loads(line)["event"] for line in transcript.read_text(encoding="utf-8").splitlines()]
    assert events == [
        "task", "assistant", "tool", "assistant", "tool", "assistant",
        "tool", "assistant", "tool", "assistant", "finished",
    ]
