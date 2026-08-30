# Validation record

Validated on 2026-08-27 with the `gpt-5.6-sol` model through an OpenAI-compatible API. No credential is stored in this repository.

## Live-model acceptance task

The intentionally buggy calculator example was copied to an ignored temporary workspace. Forge received only this task:

> Inspect this project, run the full test suite, fix the failing implementation without weakening tests, rerun the full test suite, and summarize the verified change.

The audit transcript showed this sequence:

1. `list_files` and `read_file` inspected the project.
2. `python -m unittest discover -v` failed with exit code 1.
3. `replace_text` changed `return a - b` to `return a + b`.
4. The same test command passed with exit code 0.
5. Forge returned a final summary and stopped.

An independent post-run check reran both tests successfully. The source and temporary test files had identical SHA-256 hashes, confirming that the model fixed the implementation rather than weakening the tests.

## Deterministic regression suite

`python -m pytest` passes 12 tests covering the agent loop, a realistic inspect-fail-edit-verify task, native tool-call adaptation, context compaction, workspace escape prevention, approval gates, destructive-command blocking, repeated-call guards, maximum-step termination, atomic writes, exact replacements, and credential redaction.

## Five-case live coding benchmark

A second live evaluation used five fresh workspaces with hidden tests unavailable to the agent: precise monetary pricing, Unicode slug generation, strict duration parsing, immutable recursive dictionary merging, and cross-platform safe path joining. All 10 visible and 19 hidden assertions passed, visible tests were unchanged, and the 12-test Forge regression suite remained green. See `evaluation/README.md` for the methodology and per-case results.
