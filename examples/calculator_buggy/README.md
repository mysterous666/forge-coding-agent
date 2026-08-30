# Buggy calculator acceptance task

Ask Forge to fix the failing tests without telling it which line is wrong:

```powershell
forge-agent --workspace examples/calculator_buggy --yes "Inspect this project, fix the failing tests, run the full test suite, and summarize the verified change."
```

The intentionally incorrect `add` implementation makes this a small but genuine inspect-test-edit-verify task.
