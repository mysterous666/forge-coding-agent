# 2-minute demo script

**0:00-0:15 — What it is.** Show the terminal and say: “Forge is a coding agent I wrote without an agent framework. The model only proposes text or structured tool calls; my code owns execution and safety.”

**0:15-0:35 — Task.** Run: `forge-agent --workspace examples/calculator_buggy --yes "Inspect this project, fix the failing tests, run the full test suite, and summarize the verified change"`. Briefly show the system prompt's inspect-before-edit rule.

**0:35-1:20 — Loop.** The model calls `list_files`, `read_file`, `replace_text`, then `run_command`. Point out that each result is returned as a tool message and that writes/commands are inside the workspace. Show pytest changing from red to green.

**1:20-1:45 — Safety.** Demonstrate a denied write without `--yes`, then try `git reset --hard`; the registry returns “Blocked critical destructive command” before the shell runs.

**1:45-2:00 — Close.** Open `.forge-agent/runs/*.jsonl` and say: “The transcript is append-only and redacts credentials. The run ends on a final model message or a bounded step limit; repeated identical calls are stopped.”
