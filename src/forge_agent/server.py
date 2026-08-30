"""Optional local web UI server.

Exposes the agent over a tiny HTTP server with Server-Sent Events so a browser
can render the observe-think-act timeline from *real* agent events. The agent
core is untouched; this module only wires its ``on_event`` callback to an
in-memory queue that the SSE stream drains.

Run with::

    python -m forge_agent.server            # serves the UI on http://127.0.0.1:8765
    forge-agent --serve --workspace <path>   # same, via the CLI entry point
"""

from __future__ import annotations

import json
import queue
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

from .agent import Agent, AgentError
from .model import OpenAIProvider
from .workspace import ToolRegistry, Workspace

WEB_DIR = Path(__file__).resolve().parent / "web"
DEFAULT_PORT = 8765
DEFAULT_WORKSPACE = "examples/calculator_buggy"
DEFAULT_TASK = (
    "修复当前项目中的失败测试，先阅读源码，修改实现但不要改测试文件，"
    "然后运行测试直到全部通过，最后总结。"
)


class RunBroker:
    """Single-flight bridge between the agent worker thread and SSE clients."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: list[dict[str, Any]] = []
        self._next = 0
        self._cond = threading.Condition()
        self._running = False
        self._cancel: threading.Event | None = None
        self._worker: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self._running

    def start(self, task: str, workspace: Path, model: str, api_key: str, base_url: str | None) -> bool:
        with self._lock:
            if self._running:
                return False
            self._reset_locked()
            self._running = True
            self._cancel = threading.Event()
        self._worker = threading.Thread(
            target=self._run,
            args=(task, workspace, model, api_key, base_url, self._cancel),
            daemon=True,
        )
        self._worker.start()
        return True

    def stop(self) -> bool:
        with self._lock:
            if not self._running or self._cancel is None:
                return False
            self._cancel.set()
            return True

    def clear(self) -> None:
        with self._lock:
            self._reset_locked()

    def publish(self, event: dict[str, Any]) -> None:
        with self._cond:
            self._events.append(event)
            self._cond.notify_all()

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._events)

    def wait_for(self, after: int, timeout: float = 30.0) -> list[dict[str, Any]] | None:
        """Block until at least one event past index ``after`` exists, or timeout."""
        deadline = time.monotonic() + timeout
        with self._cond:
            while len(self._events) <= after:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                self._cond.wait(remaining)
            return self._events[after:]

    def _reset_locked(self) -> None:
        self._events = []
        self._next = 0
        self._running = False
        self._cancel = None

    def _run(self, task: str, workspace_root: Path, model: str, api_key: str, base_url: str | None, cancel: threading.Event) -> None:
        try:
            workspace = Workspace(workspace_root)
            tools = ToolRegistry(workspace, approve=lambda _prompt: True)
            provider = OpenAIProvider(model=model, api_key=api_key, base_url=base_url)
            agent = Agent(
                provider=provider,
                tools=tools,
                workspace=workspace.root,
                on_event=self.publish,
                cancel_event=cancel,
            )
            agent.run(task)
        except (AgentError, ValueError, RuntimeError) as exc:
            self.publish({"type": "failed", "error": str(exc)})
        except Exception as exc:  # pragma: no cover - defensive
            self.publish({"type": "failed", "error": f"Unexpected server error: {exc}"})
        finally:
            with self._lock:
                self._running = False


_broker = RunBroker()

# Callbacks that must run on a dedicated tkinter thread (folder picker).
_PICK_QUEUE: "queue.Queue[Callable[[], None]]" = queue.Queue()


def _tk_worker() -> None:
    """Drain the pick queue on a single thread so tkinter stays happy."""
    while True:
        callback = _PICK_QUEUE.get()
        try:
            callback()
        except Exception:
            pass  # never crash the picker thread


def _content_type(path: Path) -> str:
    if path.suffix == ".html":
        return "text/html; charset=utf-8"
    if path.suffix == ".js":
        return "application/javascript; charset=utf-8"
    if path.suffix == ".css":
        return "text/css; charset=utf-8"
    return "application/octet-stream"


class Handler(BaseHTTPRequestHandler):
    # Quiet logging keeps the demo terminal readable.
    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def _send_file(self, path: Path, status: int = 200) -> None:
        if not path.is_file():
            self._send_json({"error": "not found"}, status=404)
            return
        data = path.read_bytes()
        self.send_response(status)
        self.send_header("Content-Type", _content_type(path))
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    @staticmethod
    def _pick_folder() -> str:
        """Open the OS folder picker from the server's main thread.

        The HTTP handler runs in a worker thread, but tkinter requires the
        main thread. We marshal the request onto the main loop via a callback
        queue and block until the answer is ready.
        """
        import queue as _q
        import tkinter as tk
        from tkinter import filedialog

        result: _q.Queue = _q.Queue()

        def _ask() -> None:
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            chosen = filedialog.askdirectory(parent=root, title="选择工作文件夹")
            root.destroy()
            result.put(chosen or "")

        _PICK_QUEUE.put(_ask)
        return result.get()

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        path = self.path.split("?", 1)[0]
        if path == "/events":
            return self._handle_sse()
        if path == "/state":
            return self._send_json({"running": _broker.running, "events": _broker.snapshot()})
        if path == "/config":
            import os
            return self._send_json({
                "workspace": DEFAULT_WORKSPACE,
                "model": os.getenv("AGENT_MODEL", "gpt-5-mini"),
                "default_task": DEFAULT_TASK,
            })
        if path == "/pick-folder":
            return self._send_json({"path": self._pick_folder()})
        if path == "/" or path == "/index.html":
            return self._send_file(WEB_DIR / "index.html")
        # Static assets under /web/ (or bare names)
        name = path.lstrip("/")
        if "/" in name:
            return self._send_json({"error": "not found"}, 404)
        candidate = WEB_DIR / name
        if candidate.is_file():
            return self._send_file(candidate)
        return self._send_json({"error": "not found"}, 404)

    def do_POST(self) -> None:  # noqa: N802 - http.server API
        path = self.path.split("?", 1)[0]
        if path == "/run":
            return self._handle_run()
        if path == "/stop":
            return self._send_json({"stopped": _broker.stop()})
        if path == "/clear":
            _broker.clear()
            return self._send_json({"cleared": True})
        self._send_json({"error": "not found"}, 404)

    def _handle_run(self) -> None:
        import os

        body = self._read_json()
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            self._send_json({"error": "OPENAI_API_KEY is not set in the environment"}, 503)
            return
        task = str(body.get("task", "")).strip()
        if not task:
            self._send_json({"error": "task is empty"}, 400)
            return
        workspace = Path(str(body.get("workspace", DEFAULT_WORKSPACE))).expanduser()
        model = str(body.get("model") or os.getenv("AGENT_MODEL", "gpt-5-mini")).strip()
        base_url = body.get("base_url") or os.getenv("AGENT_BASE_URL")
        base_url = str(base_url) if base_url else None
        if not workspace.is_dir():
            self._send_json({"error": f"workspace not found: {workspace}"}, 400)
            return
        ok = _broker.start(task, workspace.resolve(), model, api_key, base_url)
        if not ok:
            self._send_json({"error": "an agent run is already in progress"}, 409)
            return
        self._send_json({"ok": True, "task": task, "workspace": str(workspace)})

    def _handle_sse(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        # First flush any events already buffered before the client connected.
        index = 0
        try:
            while True:
                new = _broker.wait_for(index, timeout=25.0)
                if new is None:
                    # Keep the connection alive with a comment heartbeat.
                    try:
                        self.wfile.write(b": ping\n\n")
                        self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError):
                        return
                    continue
                for event in new:
                    payload = json.dumps(event, ensure_ascii=False)
                    chunk = f"data: {payload}\n\n".encode("utf-8")
                    self.wfile.write(chunk)
                self.wfile.flush()
                index += len(new)
        except (BrokenPipeError, ConnectionResetError):
            return


def serve(port: int = DEFAULT_PORT, workspace: str | Path = DEFAULT_WORKSPACE) -> None:
    global DEFAULT_WORKSPACE  # noqa: PLW0603 - set the demo default at startup
    DEFAULT_WORKSPACE = str(workspace)
    # Start the tkinter folder-picker thread once (it must own its own tk root).
    if not getattr(serve, "_tk_started", False):
        threading.Thread(target=_tk_worker, daemon=True, name="forge-tk-picker").start()
        serve._tk_started = True
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}"
    print(f"Forge Agent UI → {url}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Forge Agent web UI server")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--workspace", type=Path, default=Path(DEFAULT_WORKSPACE))
    args = parser.parse_args(argv)
    serve(port=args.port, workspace=str(args.workspace))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())