import json
from pathlib import Path

from forge_agent.transcript import Transcript


def test_transcript_redacts_credentials(tmp_path: Path) -> None:
    transcript = Transcript(tmp_path)
    transcript.record(
        "tool",
        {
            "api_key": "sk-example-secret-123456",
            "authorization": "Bearer hidden-value",
            "output": "OPENAI_API_KEY=plain-example-secret",
        },
    )
    written = transcript.path.read_text(encoding="utf-8")
    assert "sk-example-secret-123456" not in written
    assert "hidden-value" not in written
    assert "plain-example-secret" not in written
    assert "[REDACTED]" in written
    assert json.loads(written)["event"] == "tool"
