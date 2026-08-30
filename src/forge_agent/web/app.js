// Forge Agent — timeline renderer. Subscribes to real backend events via SSE.
// No mock data: every card is built from an event the agent loop emitted.

const ICONS = {
  list_files: "📁", read_file: "📄", search_text: "🔍",
  write_file: "✎", replace_text: "✎", run_command: "⌨", git_diff: "✎",
};

const el = (id) => document.getElementById(id);
const timelineEl = el("timeline");
const scrollEl = el("scroll");

let stepCount = 0, toolCount = 0, modifiedFiles = new Set();
let running = false, lastTestPassed = null, lastStep = 0, maxSteps = 0;
let pendingCards = new Map(); // call_id -> card element awaiting tool_result
// Internals tracking
let msgStack = ["system", "user"]; // role sequence, starts with system+user
let ctxLimit = 80000;

function setStatus(state, label) {
  el("dot").className = "dot " + state;
  el("status").textContent = label;
}
function setStep(n, max) { el("step").textContent = max ? `${n} / ${max}` : `${n}`; }
function setTools(n) { el("tools").textContent = n; }

function scrollBottom() { scrollEl.scrollTop = scrollEl.scrollHeight; }

// ---------- internals rendering ----------
const ROLE_CLASS = { system: "role-system", user: "role-user", assistant: "role-assistant", tool: "role-tool" };

function renderMsgStack() {
  const el = document.getElementById("msgStack");
  el.innerHTML = "";
  for (const role of msgStack) {
    const seg = document.createElement("span");
    seg.className = "seg " + (ROLE_CLASS[role] || "role-system");
    el.appendChild(seg);
  }
}

function updateCtxMetrics(msgs, chars, limit) {
  document.getElementById("ctxMsgs").textContent = msgs;
  document.getElementById("ctxChars").textContent = chars;
  if (limit) { ctxLimit = limit; document.getElementById("ctxLimit").textContent = limit; }
  const pct = Math.min(100, Math.round((chars / ctxLimit) * 100));
  const bar = document.getElementById("ctxBar");
  bar.style.width = pct + "%";
  bar.className = "ctx-bar-fill" + (pct >= 100 ? " over" : pct >= 70 ? " warn" : "");
}

function showCtxNote(text) {
  const n = document.getElementById("ctxNote");
  n.textContent = text;
  n.classList.add("show");
}

function addErrorLog(tag, what, feed) {
  document.getElementById("errEmpty").style.display = "none";
  const log = document.getElementById("errLog");
  const item = document.createElement("div");
  item.className = "err-item";
  item.innerHTML = `<div class="tag">${esc(tag)}</div><div class="what">${esc(what)}</div><div class="feed">→ ${esc(feed)}</div>`;
  log.appendChild(item);
}

// ---------- minimal line diff (LCS) ----------
function diffLines(a, b) {
  const A = a.split("\n"), B = b.split("\n");
  const n = A.length, m = B.length;
  const dp = Array.from({ length: n + 1 }, () => new Int32Array(m + 1));
  for (let i = n - 1; i >= 0; i--)
    for (let j = m - 1; j >= 0; j--)
      dp[i][j] = A[i] === B[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
  const out = [];
  let i = 0, j = 0;
  while (i < n && j < m) {
    if (A[i] === B[j]) { out.push({ t: "ctx", s: A[i] }); i++; j++; }
    else if (dp[i + 1][j] >= dp[i][j + 1]) { out.push({ t: "del", s: A[i] }); i++; }
    else { out.push({ t: "add", s: B[j] }); j++; }
  }
  while (i < n) { out.push({ t: "del", s: A[i] }); i++; }
  while (j < m) { out.push({ t: "add", s: B[j] }); j++; }
  return out;
}

function esc(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// ---------- parse run_command test summary ----------
function parseTestSummary(output) {
  // unittest: "Ran N tests in T s" + "OK" or "FAILED (failures=..)"
  // pytest:   "N passed", "N failed", "N error"
  const m = output.match(/(\d+)\s+passed/);
  const f = output.match(/(\d+)\s+failed/);
  const e = output.match(/(\d+)\s+error/);
  const ran = output.match(/Ran\s+(\d+)\s+tests?/);
  const total = ran ? +ran[1] : (m ? +m[1] : 0) + (f ? +f[1] : 0) + (e ? +e[1] : 0);
  return {
    passed: m ? +m[1] : (ran && /OK/.test(output) ? +ran[1] : 0),
    failed: (f ? +f[1] : 0) + (e ? +e[1] : 0),
    total,
  };
}

// ---------- card construction ----------
function makeCard(step, callId, name) {
  const card = document.createElement("div");
  card.className = "card";
  card.dataset.callId = callId;
  card.innerHTML = `
    <div class="card-head">
      <span class="step-tag">STEP ${step}</span>
      <span class="tool-name"><span class="tool-ico">${ICONS[name] || "•"}</span>${esc(name)}</span>
      <span class="status-pill running">Running</span>
    </div>
    <div class="body"></div>`;
  return card;
}

function argsBlock(args) {
  if (!args || Object.keys(args).length === 0) return "";
  const parts = Object.entries(args).map(([k, v]) => {
    let sv = typeof v === "string" ? v : JSON.stringify(v);
    if (sv.length > 240) sv = sv.slice(0, 240) + " …";
    return `<span class="k">${esc(k)}:</span> <span class="v">${esc(sv)}</span>`;
  });
  return `<div class="row-label">INPUT</div><div class="args mono">${parts.join(" &nbsp; ")}</div>`;
}

function setCardResult(card, name, ok, result) {
  const pill = card.querySelector(".status-pill");
  pill.className = "status-pill " + (ok ? "success" : "failed");
  pill.textContent = ok ? "Success" : "Failed";
  card.classList.add(ok ? "ok" : "fail");
  const body = card.querySelector(".body");
  body.insertAdjacentHTML("beforeend", renderResult(name, ok, result));
  scrollBottom();
}

// ---------- per-tool result renderers ----------
function renderResult(name, ok, result) {
  if (!ok) {
    const err = (result && (result.error || JSON.stringify(result))) || "failed";
    return `<div class="row-label">RESULT</div><div class="errtext">${esc(err)}</div>`;
  }
  const d = (result && result.data) || result;
  switch (name) {
    case "list_files": return renderFileList(d);
    case "read_file": return renderReadFile(d);
    case "search_text": return renderSearch(d);
    case "write_file": return renderWrite(d);
    case "replace_text": return renderReplace(d);
    case "run_command": return renderCommand(d);
    default: return `<div class="row-label">RESULT</div><pre class="codeblock">${esc(JSON.stringify(d, null, 2))}</pre>`;
  }
}

function renderFileList(d) {
  const files = (d.files || []).slice(0, 40).map((f) => `<div class="f">${esc(f)}</div>`).join("");
  return `<div class="row-label">FILES (${d.count || 0}${d.truncated ? ", truncated" : ""})</div><div class="filelist">${files}</div>`;
}

function renderReadFile(d) {
  const total = d.total_lines != null ? ` · ${d.total_lines} lines` : "";
  return `<div class="row-label">${esc(d.path || "")}${total}</div><pre class="codeblock">${esc(d.content || "")}</pre>`;
}

function renderSearch(d) {
  const ms = (d.matches || []).slice(0, 50).map((m) =>
    `<div class="m"><span class="loc">${esc(m.path)}:${m.line}</span> ${esc(m.text)}</div>`).join("");
  return `<div class="row-label">MATCHES${d.truncated ? " (truncated)" : ""}</div><div class="matches">${ms}</div>`;
}

function renderWrite(d) {
  return `<div class="meta-line">✓ wrote <span style="color:var(--accent)">${esc(d.path || "")}</span> · ${d.bytes || 0} bytes</div>`;
}

// renderReplace uses the call's input args (old/new) to show a real diff.
// The result itself only confirms success; the visual diff comes from input.
function renderReplace(d) {
  return `<div class="meta-line">✓ modified <span style="color:var(--accent)">${esc(d.path || "")}</span> · ${d.replacements || 1} replacement(s)</div>`;
}

function renderCommand(d) {
  const cmd = d.command || "";
  const out = d.output || "";
  const code = d.exit_code != null ? d.exit_code : "";
  const ts = parseTestSummary(out);
  const isTest = /pytest|unittest|\.py test|-m unittest/.test(cmd);
  let lines = out.split("\n");
  const html = lines.map((ln) => {
    if (/^\s*FAILED/i.test(ln) || /failed/i.test(ln) && /\d+\s+failed/.test(ln)) {
      if (/\d+\s+failed/i.test(ln)) return `<div class="failed-line">${esc(ln)}</div>`;
    }
    if (/\d+\s+passed/i.test(ln)) return `<div class="passed">${esc(ln)}</div>`;
    return esc(ln);
  }).join("\n");
  let extra = "";
  if (isTest && ts.total) {
    lastTestPassed = ts.failed === 0 && code === 0;
    const cls = lastTestPassed ? "hl-pass" : "hl-fail";
    extra = `<div class="meta-line">Tests: <span class="${cls}">${ts.passed}/${ts.total} passed</span>${ts.failed ? `, ${ts.failed} failed` : ""}</div>`;
  } else if (isTest) {
    extra = `<div class="meta-line">Tests: <span class="${code === 0 ? "hl-pass" : "hl-fail"}">${code === 0 ? "Verification Passed" : "Failed"}</span></div>`;
  }
  return `<div class="row-label">OUTPUT</div>
    <div class="terminal"><span class="prompt">$ ${esc(cmd)}</span>
${html}
<span class="${code === 0 ? "exit0" : "exitnz"}">exit code: ${esc(code)}</span></div>${d.truncated ? '<div class="meta-line">output truncated</div>' : ""}${extra}`;
}

// ---------- arrow between cards ----------
function arrow() {
  const a = document.createElement("div");
  a.className = "arrow"; a.textContent = "↓";
  return a;
}

// ---------- diff renderer for replace_text (from input args) ----------
function renderDiffCard(step, name, args, ok) {
  const card = document.createElement("div");
  card.className = "card " + (ok ? "ok" : "fail");
  const old = args.old != null ? String(args.old) : "";
  const neu = args.new != null ? String(args.new) : "";
  const diff = diffLines(old, neu);
  let adds = 0, dels = 0;
  for (const l of diff) { if (l.t === "add") adds++; if (l.t === "del") dels++; }
  const body = diff.map((l) => {
    const cls = l.t === "add" ? "add" : l.t === "del" ? "del" : "ctx";
    const sign = l.t === "add" ? "+" : l.t === "del" ? "-" : " ";
    return `<div class="diff-line ${cls}">${sign} ${esc(l.s)}</div>`;
  }).join("");
  const path = args.path || "";
  card.innerHTML = `
    <div class="card-head">
      <span class="step-tag">STEP ${step}</span>
      <span class="tool-name"><span class="tool-ico">${ICONS[name]}</span>${esc(name)}</span>
      <span class="status-pill ${ok ? "success" : "failed"}">${ok ? "Success" : "Failed"}</span>
    </div>
    <div class="row-label">CODE CHANGE</div>
    <div class="diff">
      <div class="diff-head"><span class="path">${esc(path)}</span><span class="adds">+${adds}</span><span class="dels">-${dels}</span></div>
      <div class="diff-body">${body}</div>
    </div>`;
  return card;
}

// ---------- finish card ----------
function renderFinish(event) {
  const ok = event.type === "finished";
  const card = document.createElement("div");
  card.className = "finish " + (ok ? "ok" : "fail");
  const tests = lastTestPassed === true
    ? `<div class="kv"><div class="k">TESTS</div><div class="v pass">PASSED</div></div>`
    : lastTestPassed === false ? `<div class="kv"><div class="k">TESTS</div><div class="v" style="color:var(--failed)">FAILED</div></div>` : "";
  const mfiles = [...modifiedFiles].map((f) => `<div class="f">${esc(f)}</div>`).join("");
  card.innerHTML = `
    <div class="finish-title ${ok ? "ok" : "fail"}">${ok ? "✓ Task Completed" : "✕ Task Failed"}</div>
    <div class="finish-grid">
      <div class="kv"><div class="k">STEPS</div><div class="v">${event.steps || lastStep || stepCount}</div></div>
      <div class="kv"><div class="k">TOOL CALLS</div><div class="v">${toolCount}</div></div>
      <div class="kv"><div class="k">FILES MODIFIED</div><div class="v">${modifiedFiles.size}</div></div>
      ${tests}
    </div>
    ${mfiles ? `<div class="row-label">MODIFIED FILES</div><div class="mfiles">${mfiles}</div>` : ""}
    ${event.summary ? `<div class="summary">${esc(event.summary)}</div>` : (event.error ? `<div class="summary" style="color:var(--failed)">${esc(event.error)}</div>` : "")}`;
  return card;
}

// ---------- event dispatch ----------
function handleEvent(ev) {
  switch (ev.type) {
    case "task_started":
      running = true; stepCount = 0; toolCount = 0;
      modifiedFiles = new Set(); lastTestPassed = null; pendingCards.clear();
      timelineEl.innerHTML = "";
      el("empty").style.display = "none";
      setStatus("running", "Running");
      maxSteps = ev.max_steps || 0; setStep(0, maxSteps); setTools(0);
      // reset internals
      msgStack = ["system", "user"]; renderMsgStack();
      updateCtxMetrics(2, 0, 0);
      document.getElementById("ctxNote").classList.remove("show");
      document.getElementById("errLog").innerHTML = "";
      document.getElementById("errEmpty").style.display = "block";
      break;
    case "step":
      lastStep = ev.step; setStep(ev.step, ev.max_steps || maxSteps);
      if (ev.messages != null) updateCtxMetrics(ev.messages, ev.context_chars || 0, ev.context_limit);
      break;
    case "assistant":
      msgStack.push("assistant"); renderMsgStack();
      break;
    case "tool_call": {
      toolCount++; setTools(toolCount);
      let args = {};
      try { args = JSON.parse(ev.arguments || "{}"); } catch (_) {}
      // replace_text / write_file get a diff-style card filled at result time.
      if (ev.name === "replace_text" || ev.name === "write_file") {
        // placeholder; diff drawn at result (we need ok status). Store args.
        const card = makeCard(ev.step, ev.call_id, ev.name);
        card.querySelector(".body").innerHTML = argsBlock(args);
        pendingCards.set(ev.call_id, { el: card, name: ev.name, args });
        appendCard(card);
      } else {
        const card = makeCard(ev.step, ev.call_id, ev.name);
        card.querySelector(".body").innerHTML = argsBlock(args);
        pendingCards.set(ev.call_id, { el: card, name: ev.name, args });
        appendCard(card);
      }
      break;
    }
    case "tool_result": {
      let parsed = {};
      try { parsed = JSON.parse(ev.result || "{}"); } catch (_) {}
      const ok = parsed.ok !== false;
      // internals: each tool_result is a tool message in the conversation
      msgStack.push("tool"); renderMsgStack();
      // internals: surface the error-handling mechanism when a tool fails
      if (!ok) {
        const errmsg = parsed.error || "tool failed";
        if (/Repeated identical call blocked/.test(errmsg)) {
          addErrorLog("重复调用守卫", errmsg, "阻止重复，要求模型改变策略");
        } else if (/Blocked critical destructive/.test(errmsg)) {
          addErrorLog("高危命令阻断", errmsg, "危险命令被拦截，不执行");
        } else {
          addErrorLog("工具失败 → observation", `${ev.name}: ${errmsg}`, "错误已作为观察返回模型，Agent 继续");
        }
      }
      const entry = pendingCards.get(ev.call_id);
      if (entry) {
        if (entry.name === "replace_text") {
          // swap in the diff card using stored args + ok status
          const diffCard = renderDiffCard(ev.step, entry.name, entry.args, ok);
          entry.el.replaceWith(diffCard);
          if (ok && entry.args.path) modifiedFiles.add(entry.args.path);
        } else if (entry.name === "write_file") {
          // show as a diff if creating/overwriting with content
          if (entry.args.content != null && ok) {
            const diffCard = renderDiffCard(ev.step, entry.name, { path: entry.args.path, old: "", new: entry.args.content }, ok);
            diffCard.querySelector(".status-pill").textContent = "Success";
            entry.el.replaceWith(diffCard);
            if (entry.args.path) modifiedFiles.add(entry.args.path);
          } else {
            setCardResult(entry.el, entry.name, ok, parsed);
            if (ok && entry.args.path) modifiedFiles.add(entry.args.path);
          }
        } else {
          setCardResult(entry.el, entry.name, ok, parsed);
        }
        pendingCards.delete(ev.call_id);
      }
      break;
    }
    case "context_compacted":
      showCtxNote(`上下文已压缩：移除 ${ev.removed_blocks} 个早期交互块（消息数 ${ev.messages}）`);
      updateCtxMetrics(ev.messages, ev.context_chars || 0, 0);
      break;
    case "finished":
      running = false; setStatus("completed", "Completed");
      timelineEl.appendChild(arrow());
      timelineEl.appendChild(renderFinish(ev));
      setButtons(false);
      scrollBottom();
      break;
    case "failed":
      running = false; setStatus("failed", "Failed");
      if (/Model request failed/.test(ev.error || "")) {
        addErrorLog("模型请求失败 → 受控终止", ev.error || "", "AgentError 抛出，未崩溃");
      }
      timelineEl.appendChild(arrow());
      timelineEl.appendChild(renderFinish({ type: "failed", error: ev.error, steps: ev.step || lastStep }));
      setButtons(false);
      scrollBottom();
      break;
    case "stopped":
      running = false;
      setStatus("failed", ev.reason === "cancelled" ? "Stopped" : "Stopped");
      addErrorLog("循环终止", ev.reason === "cancelled" ? "用户取消 (cancel_event)" : `达到 max_steps=${ev.max_steps}`, ev.reason === "cancelled" ? "受控 AgentError 退出" : "硬上限停止，防死循环");
      timelineEl.appendChild(arrow());
      timelineEl.appendChild(renderFinish({ type: "failed", error: ev.reason === "cancelled" ? "Stopped by user." : `Stopped after ${ev.max_steps} steps.`, steps: ev.step || lastStep }));
      setButtons(false);
      scrollBottom();
      break;
  }
}

function appendCard(card) {
  if (timelineEl.lastElementChild && !timelineEl.lastElementChild.classList.contains("card") && !timelineEl.lastElementChild.classList.contains("finish")) {
    timelineEl.appendChild(arrow());
  } else if (timelineEl.children.length > 0) {
    timelineEl.appendChild(arrow());
  }
  timelineEl.appendChild(card);
  scrollBottom();
}

function setButtons(isRunning) {
  el("runBtn").disabled = isRunning;
  el("stopBtn").disabled = !isRunning;
}

// ---------- controls ----------
async function post(path, body) {
  try {
    const r = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
    return r.json();
  } catch (e) { return { error: String(e) }; }
}

el("runBtn").addEventListener("click", async () => {
  const task = el("task").value.trim();
  if (!task) return;
  const workspace = el("workspace").value.trim();
  const model = el("model").value.trim();
  const body = { task };
  if (workspace) body.workspace = workspace;
  if (model) body.model = model;
  const res = await post("/run", body);
  if (res.error) { alert(res.error); return; }
  setButtons(true);
  // connect SSE if not already
  connectSSE();
});

el("stopBtn").addEventListener("click", async () => {
  await post("/stop", {});
});
el("clearBtn").addEventListener("click", async () => {
  await post("/clear", {});
  timelineEl.innerHTML = "";
  el("empty").style.display = "block";
  setStatus("", "Ready");
  setStep(0, 0); setTools(0); stepCount = 0; toolCount = 0; modifiedFiles = new Set();
  setButtons(false);
});
el("pickBtn").addEventListener("click", async () => {
  const btn = el("pickBtn");
  btn.disabled = true;
  const orig = btn.textContent;
  btn.textContent = "⏳ 选择中…";
  try {
    const res = await fetch("/pick-folder");
    const data = await res.json();
    if (data.path) el("workspace").value = data.path;
  } finally {
    btn.disabled = false;
    btn.textContent = orig;
  }
});

let es = null;
function connectSSE() {
  if (es) es.close();
  es = new EventSource("/events");
  es.onmessage = (m) => {
    try { handleEvent(JSON.parse(m.data)); } catch (_) {}
  };
  es.onerror = () => { /* keep; browser auto-reconnects */ };
}
connectSSE();
setButtons(false);

// populate default workspace hint if provided by the page
window.addEventListener("DOMContentLoaded", () => {
  if (window.FORGE_DEFAULT_TASK) el("task").value = window.FORGE_DEFAULT_TASK;
  // fetch server config to prefill workspace + model
  fetch("/config").then((r) => r.json()).then((cfg) => {
    if (cfg.workspace) el("workspace").value = cfg.workspace;
    if (cfg.model) el("model").value = cfg.model;
    if (cfg.default_task) el("task").value = cfg.default_task;
  }).catch(() => {});
});