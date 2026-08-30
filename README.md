# Forge Coding Agent

Forge is a small coding agent implemented from first principles. It uses an OpenAI-compatible chat client only; the agent loop, message history, tool schemas, local execution, safety checks, compaction, retry guard, and audit transcript are project code.

## Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
$env:OPENAI_API_KEY = "..."
forge-agent --workspace . --yes "Create hello.py that prints 42 and run it"
```

For a visual local desktop interface, run `forge-agent --gui`. It provides task/workspace fields, live model/tool events, approval dialogs, and the final answer while reusing the same agent core.

Run the deterministic integration tests with `python -m pytest`; they do not call a network API.
For a live-model acceptance run, use the intentionally failing project in `examples/calculator_buggy`.
The latest reproducible offline and live-model results are documented in `VALIDATION.md`.

Without `--yes`, every write and command asks for approval. Credentials are read only from the environment and redacted in `.forge-agent/runs/*.jsonl`.

## Tools

`list_files`, `read_file`, `search_text`, `write_file`, `replace_text`, and `run_command` form a deliberately small tool surface. Paths are resolved beneath the workspace; writes are atomic; replacements require an exact match count; commands have timeouts and output limits; critical destructive command patterns are blocked.

## Design

Each model turn either yields a final answer or structured tool calls. Tool results are appended as `tool` messages, then context is compacted without separating assistant/tool pairs. A repeated identical call is blocked after two attempts, and the run stops at a configurable step limit. The transcript makes the run inspectable and supports a short demo video.

## Test

```powershell
$env:PYTHONPATH = "src"
python -m pytest
```
