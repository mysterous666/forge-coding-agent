from forge_agent.context import ContextManager


def test_compaction_keeps_assistant_tool_pairs_together() -> None:
    messages = [
        {"role": "system", "content": "s"},
        {"role": "user", "content": "task"},
    ]
    for index in range(12):
        messages.extend([
            {"role": "assistant", "content": "", "tool_calls": [{"id": str(index)}]},
            {"role": "tool", "tool_call_id": str(index), "content": "x" * 1000},
        ])
    compacted = ContextManager(max_chars=4000, max_tool_chars=500).compact(messages)
    for index, message in enumerate(compacted):
        if message.get("role") == "tool":
            assert compacted[index - 1].get("role") in {"assistant", "tool"}

