"""Workspace boundary and local coding tools."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


class ToolError(RuntimeError):
    """An expected, model-correctable tool failure."""


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., dict[str, Any]]
    mutating: bool = False

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class Workspace:
    def __init__(self, root: Path, *, max_output_chars: int = 20_000) -> None:
        self.root = root.expanduser().resolve()
        if not self.root.is_dir():
            raise ValueError(f"Workspace is not a directory: {self.root}")
        self.max_output_chars = max_output_chars

    def resolve(self, user_path: str) -> Path:
        candidate = (self.root / user_path).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise ToolError(f"Path escapes workspace: {user_path}") from exc
        return candidate

    def display(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    def list_files(self, pattern: str = "**/*", limit: int = 200) -> dict[str, Any]:
        if not 1 <= limit <= 1000:
            raise ToolError("limit must be between 1 and 1000")
        files = []
        for path in sorted(self.root.glob(pattern)):
            if path.is_file() and ".git" not in path.parts:
                files.append(self.display(path))
                if len(files) >= limit:
                    break
        return {"files": files, "count": len(files), "truncated": len(files) == limit}

    def read_file(
        self, path: str, start_line: int = 1, end_line: int | None = None
    ) -> dict[str, Any]:
        target = self.resolve(path)
        if not target.is_file():
            raise ToolError(f"File not found: {path}")
        if start_line < 1 or (end_line is not None and end_line < start_line):
            raise ToolError("Invalid line range")
        try:
            lines = target.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError as exc:
            raise ToolError(f"Not a UTF-8 text file: {path}") from exc
        selected = lines[start_line - 1 : end_line]
        numbered = "\n".join(
            f"{number:>5} | {line}"
            for number, line in enumerate(selected, start=start_line)
        )
        truncated = len(numbered) > self.max_output_chars
        return {
            "path": self.display(target),
            "content": numbered[: self.max_output_chars],
            "total_lines": len(lines),
            "truncated": truncated,
        }

    def search_text(
        self, query: str, pattern: str = "**/*", limit: int = 100
    ) -> dict[str, Any]:
        if len(query) > 500:
            raise ToolError("query is too long")
        try:
            regex = re.compile(query)
        except re.error as exc:
            raise ToolError(f"Invalid regular expression: {exc}") from exc
        matches: list[dict[str, Any]] = []
        for path in sorted(self.root.glob(pattern)):
            if not path.is_file() or ".git" in path.parts:
                continue
            try:
                for number, line in enumerate(
                    path.read_text(encoding="utf-8").splitlines(), 1
                ):
                    if regex.search(line):
                        matches.append(
                            {"path": self.display(path), "line": number, "text": line[:500]}
                        )
                        if len(matches) >= limit:
                            return {"matches": matches, "truncated": True}
            except (UnicodeDecodeError, OSError):
                continue
        return {"matches": matches, "truncated": False}

    def write_file(self, path: str, content: str, overwrite: bool = False) -> dict[str, Any]:
        target = self.resolve(path)
        if target.exists() and not overwrite:
            raise ToolError("File exists; set overwrite=true only after reading it")
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
                handle.write(content)
            os.replace(temp_name, target)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
        return {"path": self.display(target), "bytes": len(content.encode("utf-8"))}

    def replace_text(
        self, path: str, old: str, new: str, expected_count: int = 1
    ) -> dict[str, Any]:
        target = self.resolve(path)
        if not target.is_file():
            raise ToolError(f"File not found: {path}")
        text = target.read_text(encoding="utf-8")
        actual = text.count(old)
        if actual != expected_count:
            raise ToolError(f"Expected {expected_count} matches, found {actual}; no changes made")
        updated = text.replace(old, new)
        return self.write_file(path, updated, overwrite=True) | {"replacements": actual}

    def run_command(self, command: str, timeout_seconds: int = 60) -> dict[str, Any]:
        if not 1 <= timeout_seconds <= 300:
            raise ToolError("timeout_seconds must be between 1 and 300")
        completed = subprocess.run(
            command,
            cwd=self.root,
            shell=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=timeout_seconds,
        )
        combined = (completed.stdout + completed.stderr)[: self.max_output_chars]
        return {
            "command": command,
            "exit_code": completed.returncode,
            "output": combined,
            "truncated": len(completed.stdout) + len(completed.stderr) > len(combined),
        }


class ToolRegistry:
    CRITICAL_COMMANDS = (
        re.compile(r"\brm\s+-rf\s+[/~](?:\s|$)", re.I),
        re.compile(r"\bgit\s+reset\s+--hard\b", re.I),
        re.compile(r"\bformat(?:\.com)?\s+[a-z]:", re.I),
        re.compile(r"\bRemove-Item\b.*\b-Recurse\b.*(?:\\|/|\$HOME|~)", re.I),
        re.compile(r"\b(?:del|erase|rd|rmdir)\b.*(?:/s|/q|-recurse)", re.I),
    )

    def __init__(
        self,
        workspace: Workspace,
        *,
        approve: Callable[[str], bool],
    ) -> None:
        self.workspace = workspace
        self.approve = approve
        obj = {"type": "object", "additionalProperties": False}
        self._tools = {
            "list_files": ToolSpec(
                "list_files", "List workspace files matching a glob.",
                obj | {"properties": {"pattern": {"type": "string"}, "limit": {"type": "integer"}}},
                workspace.list_files,
            ),
            "read_file": ToolSpec(
                "read_file", "Read a UTF-8 file with line numbers.",
                obj | {"properties": {"path": {"type": "string"}, "start_line": {"type": "integer"}, "end_line": {"type": ["integer", "null"]}}, "required": ["path"]},
                workspace.read_file,
            ),
            "search_text": ToolSpec(
                "search_text", "Regex-search UTF-8 files in the workspace.",
                obj | {"properties": {"query": {"type": "string"}, "pattern": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["query"]},
                workspace.search_text,
            ),
            "write_file": ToolSpec(
                "write_file", "Atomically create or overwrite a UTF-8 file.",
                obj | {"properties": {"path": {"type": "string"}, "content": {"type": "string"}, "overwrite": {"type": "boolean"}}, "required": ["path", "content"]},
                workspace.write_file, True,
            ),
            "replace_text": ToolSpec(
                "replace_text", "Replace an exact string only when its match count is as expected.",
                obj | {"properties": {"path": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"}, "expected_count": {"type": "integer"}}, "required": ["path", "old", "new"]},
                workspace.replace_text, True,
            ),
            "run_command": ToolSpec(
                "run_command", "Run a shell command inside the workspace with a timeout.",
                obj | {"properties": {"command": {"type": "string"}, "timeout_seconds": {"type": "integer"}}, "required": ["command"]},
                workspace.run_command, True,
            ),
        }

    @property
    def schemas(self) -> list[dict[str, Any]]:
        return [tool.schema() for tool in self._tools.values()]

    def execute(self, name: str, raw_arguments: str) -> str:
        tool = self._tools.get(name)
        if tool is None:
            return self._result(False, error=f"Unknown tool: {name}")
        try:
            arguments = json.loads(raw_arguments or "{}")
            if not isinstance(arguments, dict):
                raise ToolError("Tool arguments must be a JSON object")
            if name == "run_command":
                command = str(arguments.get("command", ""))
                if any(rule.search(command) for rule in self.CRITICAL_COMMANDS):
                    raise ToolError("Blocked critical destructive command")
            if tool.mutating and not self.approve(self._approval_text(name, arguments)):
                raise ToolError("User denied this operation")
            return self._result(True, data=tool.handler(**arguments))
        except json.JSONDecodeError as exc:
            return self._result(False, error=f"Invalid JSON arguments: {exc.msg}")
        except subprocess.TimeoutExpired:
            return self._result(False, error="Command timed out")
        except (ToolError, TypeError, OSError) as exc:
            return self._result(False, error=str(exc))

    @staticmethod
    def _approval_text(name: str, arguments: dict[str, Any]) -> str:
        preview = json.dumps(arguments, ensure_ascii=False)
        return f"Allow {name}: {preview[:500]}"

    @staticmethod
    def _result(ok: bool, **payload: Any) -> str:
        return json.dumps({"ok": ok, **payload}, ensure_ascii=False)
