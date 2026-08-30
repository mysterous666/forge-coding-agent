from types import SimpleNamespace

from forge_agent.model import OpenAIProvider


def test_openai_adapter_uses_native_tool_calling(monkeypatch) -> None:
    captured = {}
    native_call = SimpleNamespace(
        id="call-1",
        function=SimpleNamespace(name="read_file", arguments='{"path":"a.py"}'),
    )
    native_response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="", tool_calls=[native_call]))]
    )

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return native_response

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr("openai.OpenAI", FakeOpenAI)
    provider = OpenAIProvider(
        model="test-model",
        api_key="not-a-real-key",
        base_url="https://example.invalid/v1",
    )
    reply = provider.complete(
        [{"role": "user", "content": "inspect"}],
        [{"type": "function", "function": {"name": "read_file"}}],
    )

    assert captured["model"] == "test-model"
    assert captured["tool_choice"] == "auto"
    assert captured["tools"][0]["function"]["name"] == "read_file"
    assert reply.tool_calls[0].name == "read_file"
    assert reply.tool_calls[0].arguments == '{"path":"a.py"}'
