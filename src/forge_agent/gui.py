"""Optional local desktop UI; the agent core remains UI-independent."""
from __future__ import annotations
import os, queue, threading, tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable
from .agent import Agent, AgentError
from .model import ModelProvider, OpenAIProvider
from .workspace import ToolRegistry, Workspace

@dataclass
class ApprovalRequest:
    prompt: str
    answer: bool | None = None
    done: threading.Event | None = None

class ApprovalGate:
    def __init__(self, root: tk.Tk, log: Callable[[str], None]) -> None:
        self.root, self.log, self.pending = root, log, queue.Queue(); root.after(150, self._poll)
    def ask(self, prompt: str) -> bool:
        req = ApprovalRequest(prompt, done=threading.Event()); self.pending.put(req); req.done.wait(); return bool(req.answer)
    def _poll(self) -> None:
        try: req = self.pending.get_nowait()
        except queue.Empty: self.root.after(150, self._poll); return
        req.answer = messagebox.askyesno("Forge 操作审批", req.prompt, parent=self.root)
        self.log(("已批准" if req.answer else "已拒绝") + " · " + req.prompt); req.done.set(); self.root.after(150, self._poll)

class LoggingProvider:
    def __init__(self, provider: ModelProvider, log: Callable[[str], None]) -> None: self.provider, self.log = provider, log
    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]):
        self.log(f"● 模型请求  · 上下文 {len(messages)} 条  · 工具 {len(tools)} 个")
        reply = self.provider.complete(messages, tools)
        self.log("◆ 工具计划  · " + "  ·  ".join(c.name for c in reply.tool_calls) if reply.tool_calls else "✓ 模型返回最终答复")
        return reply

class ForgeWindow:
    BG, PANEL, TEXT, MUTED, ACCENT = "#0f172a", "#111c31", "#e5edf8", "#8da2c0", "#61d9c3"
    def __init__(self, root: tk.Tk) -> None:
        self.root, self.events, self.running = root, queue.Queue(), False
        root.title("Forge · Coding Agent"); root.geometry("1180x760"); root.minsize(980, 640); root.configure(bg=self.BG)
        # Tk's default scaling is tiny on many Windows displays; use a crisp, readable baseline.
        try: root.tk.call("tk", "scaling", 1.25)
        except tk.TclError: pass
        ui_font, mono_font = "Segoe UI", "Cascadia Mono"
        style = ttk.Style(); style.theme_use("clam")
        style.configure("TFrame", background=self.BG); style.configure("Panel.TFrame", background=self.PANEL)
        style.configure("TLabel", background=self.BG, foreground=self.TEXT, font=(ui_font, 10))
        style.configure("Muted.TLabel", background=self.BG, foreground=self.MUTED, font=(ui_font, 9))
        style.configure("Title.TLabel", background=self.BG, foreground=self.TEXT, font=(ui_font, 24, "bold"))
        style.configure("TButton", background="#1d2a45", foreground=self.TEXT, borderwidth=0, relief="flat", padding=(14, 9), font=(ui_font, 10))
        style.map("TButton", background=[("active", "#2b4169"), ("pressed", "#16253f")])
        style.configure("Accent.TButton", background=self.ACCENT, foreground="#09221f", font=(ui_font, 10, "bold"), padding=(16, 10))
        style.map("Accent.TButton", background=[("active", "#8af0dc"), ("disabled", "#34534f")])
        style.configure("TEntry", fieldbackground="#0b1425", foreground=self.TEXT, insertcolor=self.ACCENT, bordercolor="#30425f", lightcolor="#30425f", darkcolor="#30425f", padding=(9, 8), font=(ui_font, 10))
        style.configure("TCheckbutton", background=self.PANEL, foreground=self.TEXT, font=(ui_font, 10), padding=4)
        style.map("TCheckbutton", background=[("active", self.PANEL)], foreground=[("active", self.TEXT)])
        style.configure("TLabelframe", background=self.PANEL, foreground=self.MUTED, bordercolor="#263653", relief="flat")
        style.configure("TLabelframe.Label", background=self.PANEL, foreground=self.MUTED, font=(ui_font, 9, "bold"))
        outer = ttk.Frame(root, padding=18); outer.pack(fill="both", expand=True); header = ttk.Frame(outer); header.pack(fill="x", pady=(0, 14)); ttk.Label(header, text="Forge", style="Title.TLabel").pack(side="left"); ttk.Label(header, text="  CODING AGENT  /  LOCAL & AUDITABLE", style="Muted.TLabel").pack(side="left", pady=(8, 0)); self.status = ttk.Label(header, text="● 就绪", foreground=self.ACCENT); self.status.pack(side="right", pady=(8, 0))
        panes = ttk.Panedwindow(outer, orient="horizontal"); panes.pack(fill="both", expand=True); left = ttk.Frame(panes, style="Panel.TFrame", padding=14); center = ttk.Frame(panes, style="Panel.TFrame", padding=16); right = ttk.Frame(panes, style="Panel.TFrame", padding=14); panes.add(left, weight=1); panes.add(center, weight=4); panes.add(right, weight=1)
        ttk.Label(left, text="WORKSPACE", style="Muted.TLabel").pack(anchor="w"); self.workspace = tk.StringVar(value=str(Path.cwd())); ttk.Entry(left, textvariable=self.workspace).pack(fill="x", pady=(7, 6)); ttk.Button(left, text="选择文件夹", command=self.choose_workspace).pack(fill="x"); ttk.Separator(left).pack(fill="x", pady=18); ttk.Label(left, text="SESSION", style="Muted.TLabel").pack(anchor="w"); ttk.Label(left, text="◉  当前任务", foreground=self.ACCENT).pack(anchor="w", pady=(10, 3)); ttk.Label(left, text="  新建任务", style="Muted.TLabel").pack(anchor="w"); ttk.Label(left, text="  审计记录", style="Muted.TLabel").pack(anchor="w", pady=3); ttk.Separator(left).pack(fill="x", pady=18); ttk.Label(left, text="MODEL", style="Muted.TLabel").pack(anchor="w"); self.model = tk.StringVar(value=os.getenv("AGENT_MODEL", "gpt-5-mini")); ttk.Entry(left, textvariable=self.model).pack(fill="x", pady=(7, 0))
        ttk.Label(center, text="新建编程任务", font=(ui_font, 16, "bold")).pack(anchor="w"); ttk.Label(center, text="Describe the change. Forge will inspect, edit, verify, and report.", style="Muted.TLabel").pack(anchor="w", pady=(3, 12)); self.task = tk.Text(center, height=5, wrap="word", bg="#0b1425", fg=self.TEXT, insertbackground=self.ACCENT, relief="flat", padx=14, pady=12, font=(ui_font, 11)); self.task.pack(fill="x"); self.task.insert("1.0", "检查项目中的失败测试，修复实现但不要修改测试文件，然后重新运行完整测试并总结。"); controls = ttk.Frame(center); controls.pack(fill="x", pady=12); self.run_button = ttk.Button(controls, text="▶  开始运行", style="Accent.TButton", command=self.start); self.run_button.pack(side="left"); ttk.Button(controls, text="清空事件", command=self.clear_log).pack(side="left", padx=8); self.auto_approve = tk.BooleanVar(value=False); ttk.Checkbutton(controls, text="自动批准普通操作", variable=self.auto_approve).pack(side="right"); ttk.Label(center, text="EVENT STREAM", style="Muted.TLabel").pack(anchor="w", pady=(6, 5)); self.log_view = tk.Text(center, state="disabled", wrap="word", bg="#0b1425", fg=self.TEXT, relief="flat", padx=14, pady=12, font=(mono_font, 10)); self.log_view.tag_configure("success", foreground="#7ee8c6"); self.log_view.tag_configure("warning", foreground="#f4c96b"); self.log_view.tag_configure("error", foreground="#ff8b9d"); self.log_view.tag_configure("muted", foreground=self.MUTED); self.log_view.pack(fill="both", expand=True)
        ttk.Label(right, text="RUN SUMMARY", style="Muted.TLabel").pack(anchor="w"); self.summary = tk.StringVar(value="等待运行"); ttk.Label(right, textvariable=self.summary, wraplength=180, justify="left").pack(anchor="w", pady=(10, 18)); ttk.Label(right, text="SAFETY", style="Muted.TLabel").pack(anchor="w"); [ttk.Label(right, text=x, foreground=self.ACCENT).pack(anchor="w", pady=4) for x in ("✓ 工作区路径隔离", "✓ 普通操作需审批", "✓ 高危命令阻断", "✓ 命令超时保护", "✓ 审计日志脱敏")]; ttk.Separator(right).pack(fill="x", pady=18); ttk.Label(right, text="CURRENT WORKSPACE", style="Muted.TLabel").pack(anchor="w"); ttk.Label(right, textvariable=self.workspace, wraplength=180, foreground=self.MUTED).pack(anchor="w", pady=(8, 0)); self.gate = ApprovalGate(root, self.log); root.after(100, self.flush_events)
    def choose_workspace(self) -> None:
        chosen = filedialog.askdirectory(parent=self.root)
        if chosen: self.workspace.set(chosen)
    def log(self, text: str) -> None: self.events.put(text)
    def flush_events(self) -> None:
        try:
            while True:
                text = self.events.get_nowait()
                if text in {"__DONE__", "__FAILED__"}: self.running = False; self.run_button.configure(state="normal"); self.status.configure(text="● 完成" if text == "__DONE__" else "● 失败", foreground=self.ACCENT if text == "__DONE__" else "#ff7b8b"); self.summary.set("任务已完成，可查看事件流与审计记录。" if text == "__DONE__" else "任务失败，请检查事件流中的错误信息。"); continue
                tag = "error" if text.startswith("错误") else "warning" if "等待" in text or "审批" in text else "success" if text.startswith(("✓", "◆")) else "muted" if text.startswith("●") else "normal"
                self.log_view.configure(state="normal"); self.log_view.insert("end", text + "\n", tag); self.log_view.see("end"); self.log_view.configure(state="disabled")
        except queue.Empty: pass
        self.root.after(100, self.flush_events)
    def clear_log(self) -> None:
        self.log_view.configure(state="normal"); self.log_view.delete("1.0", "end"); self.log_view.configure(state="disabled")
    def start(self) -> None:
        if self.running: return
        task = self.task.get("1.0", "end").strip()
        if not task: messagebox.showwarning("缺少任务", "请输入要完成的编程任务。", parent=self.root); return
        if not os.getenv("OPENAI_API_KEY"): messagebox.showerror("缺少配置", "请先在系统环境变量中设置 OPENAI_API_KEY。", parent=self.root); return
        self.running = True; self.run_button.configure(state="disabled"); self.status.configure(text="● 运行中...", foreground="#f4c96b"); self.summary.set("Agent 正在分析任务并等待模型工具调用..."); self.clear_log(); threading.Thread(target=self.run_worker, args=(task,), daemon=True).start()
    def run_worker(self, task: str) -> None:
        try:
            workspace = Workspace(Path(self.workspace.get())); approve = (lambda _: True) if self.auto_approve.get() else self.gate.ask; tools = ToolRegistry(workspace, approve=approve); provider = LoggingProvider(OpenAIProvider(model=self.model.get().strip(), api_key=os.environ["OPENAI_API_KEY"], base_url=os.getenv("AGENT_BASE_URL")), self.log); result = Agent(provider=provider, tools=tools, workspace=workspace.root).run(task); self.log("\n===== FINAL ANSWER =====\n" + result); self.events.put("__DONE__")
        except (AgentError, ValueError, RuntimeError) as exc: self.log("错误：" + str(exc)); self.events.put("__FAILED__")

def main() -> None:
    root = tk.Tk(); ForgeWindow(root); root.mainloop()
