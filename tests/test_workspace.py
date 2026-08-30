from pathlib import Path

import pytest

from forge_agent.workspace import ToolError, ToolRegistry, Workspace


def test_path_cannot_escape_workspace(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    with pytest.raises(ToolError, match="escapes workspace"):
        workspace.resolve("../secret.txt")


def test_atomic_write_requires_explicit_overwrite(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    workspace.write_file("a.txt", "first")
    with pytest.raises(ToolError, match="File exists"):
        workspace.write_file("a.txt", "second")
    workspace.write_file("a.txt", "second", overwrite=True)
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "second"


def test_replace_text_is_guarded_by_match_count(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("x x", encoding="utf-8")
    workspace = Workspace(tmp_path)
    with pytest.raises(ToolError, match="Expected 1 matches, found 2"):
        workspace.replace_text("a.txt", "x", "y")
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "x x"


def test_registry_rejects_invalid_json_and_critical_command(tmp_path: Path) -> None:
    registry = ToolRegistry(Workspace(tmp_path), approve=lambda _: True)
    assert '"ok": false' in registry.execute("read_file", "{")
    result = registry.execute("run_command", '{"command":"git reset --hard"}')
    assert "Blocked critical destructive command" in result
    result = registry.execute("run_command", '{"command":"rmdir /s /q important"}')
    assert "Blocked critical destructive command" in result


def test_mutation_needs_approval(tmp_path: Path) -> None:
    registry = ToolRegistry(Workspace(tmp_path), approve=lambda _: False)
    result = registry.execute("write_file", '{"path":"a.txt","content":"x"}')
    assert "User denied" in result
    assert not (tmp_path / "a.txt").exists()
