"""Command-line entry point."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .agent import Agent, AgentError
from .model import OpenAIProvider
from .workspace import ToolRegistry, Workspace


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Forge: an auditable coding agent")
    parser.add_argument("task", nargs="*", help="Programming task; omit to read one line from stdin")
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--model", default=os.getenv("AGENT_MODEL", "gpt-5-mini"))
    parser.add_argument("--base-url", default=os.getenv("AGENT_BASE_URL"))
    parser.add_argument("--max-steps", type=int, default=24)
    parser.add_argument("--yes", action="store_true", help="Approve ordinary writes and commands; critical commands remain blocked")
    parser.add_argument("--gui", action="store_true", help="Open the optional local desktop interface")
    parser.add_argument("--serve", action="store_true", help="Serve the web UI (timeline) over HTTP instead of running one task")
    parser.add_argument("--port", type=int, default=8765, help="Port for the web UI server (with --serve)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.serve:
        from .server import serve
        serve(port=args.port, workspace=str(args.workspace))
        return 0
    if args.gui:
        from .gui import main as gui_main
        gui_main()
        return 0
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: set OPENAI_API_KEY in the environment.", file=sys.stderr)
        return 2
    task = " ".join(args.task).strip()
    if not task:
        task = input("Task> ").strip()

    def approve(prompt: str) -> bool:
        if args.yes:
            return True
        answer = input(f"\n{prompt}\nApprove? [y/N] ").strip().lower()
        return answer in {"y", "yes"}

    try:
        workspace = Workspace(args.workspace)
        tools = ToolRegistry(workspace, approve=approve)
        provider = OpenAIProvider(
            model=args.model, api_key=api_key, base_url=args.base_url
        )
        result = Agent(
            provider=provider,
            tools=tools,
            workspace=workspace.root,
            max_steps=args.max_steps,
        ).run(task)
    except (AgentError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"\n{result}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
