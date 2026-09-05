"""A local web dashboard - lighter and faster than the old tkinter GUI.

One page lists every problem in problems/; clicking one shows its question
and solution and lets you run the judge without leaving the browser. No
external files, no build step, no third-party packages - just the stdlib
serving one embedded HTML/CSS/JS page and a tiny JSON API.
"""
from __future__ import annotations

import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional
from urllib.parse import unquote, urlsplit

from . import theme as T
from .discovery import Problem, discover, find
from .runner import CaseResult, DEFAULT_TIMEOUT, Submission, submit

API_PREFIX = "/api/problems/"


def _problem_summary(problem: Problem) -> dict:
    return {"slug": problem.slug, "title": problem.title, "ready": problem.tests is not None}


def _read_text(path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path and path.exists() else ""


def _problem_detail(problem: Problem) -> dict:
    return {
        "slug": problem.slug,
        "title": problem.title,
        "ready": problem.tests is not None,
        "question": _read_text(problem.question),
        "solution": _read_text(problem.solution),
    }


def _case_to_dict(case_result: CaseResult) -> dict:
    return {
        "number": case_result.number,
        "name": case_result.name,
        "status": case_result.status,
        "ok": case_result.ok,
        "args_repr": case_result.args_repr,
        "expected_repr": case_result.expected_repr,
        "output_repr": case_result.output_repr,
        "stdout": case_result.stdout,
        "error": case_result.error,
        "runtime_ms": case_result.runtime_ms,
    }


def _submission_to_dict(sub: Submission) -> dict:
    return {
        "verdict": sub.verdict,
        "accepted": sub.accepted,
        "passed": sub.passed,
        "total": sub.total,
        "runtime_ms": sub.runtime_ms,
        "peak_kb": sub.peak_kb,
        "load_error": sub.load_error,
        "scaling": sub.scaling,
        "cases": [_case_to_dict(c) for c in sub.cases],
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "DSAPractice/1.0"
    timeout_s = DEFAULT_TIMEOUT
    last_verdict: dict = {"accepted": None}

    def log_message(self, fmt, *args) -> None:  # keep the terminal quiet
        pass

    def _send_bytes(self, body: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload, status: int = 200) -> None:
        self._send_bytes(json.dumps(payload).encode("utf-8"),
                         "application/json; charset=utf-8", status)

    def _send_html(self, html: str) -> None:
        self._send_bytes(html.encode("utf-8"), "text/html; charset=utf-8")

    def do_GET(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        if path == "/":
            self._send_html(INDEX_HTML)
            return
        if path == "/api/problems":
            self._send_json([_problem_summary(p) for p in discover()])
            return
        if path.startswith(API_PREFIX):
            slug = unquote(path[len(API_PREFIX):])
            problem = find(slug)
            if problem is None:
                self._send_json({"error": f"No problem matching '{slug}'."}, status=404)
                return
            self._send_json(_problem_detail(problem))
            return
        self._send_json({"error": "not found"}, status=404)

    def do_POST(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        if path.startswith(API_PREFIX) and path.endswith("/run"):
            slug = unquote(path[len(API_PREFIX):-len("/run")])
            problem = find(slug)
            if problem is None:
                self._send_json({"error": f"No problem matching '{slug}'."}, status=404)
                return
            try:
                sub = submit(problem, timeout=self.timeout_s, with_scaling=True)
            except Exception as exc:  # keep the server alive no matter what
                self._send_json({"error": f"{type(exc).__name__}: {exc}"}, status=500)
                return
            Handler.last_verdict["accepted"] = sub.accepted
            self._send_json(_submission_to_dict(sub))
            return
        self._send_json({"error": "not found"}, status=404)


def launch(focus_slug: Optional[str] = None, timeout: float = DEFAULT_TIMEOUT,
           auto_run: bool = False, open_browser: bool = True) -> int:
    """Serve the dashboard until Ctrl-C. Returns 0/1 like the old GUI did,
    based on the last verdict seen, so scripts calling `-g` still get a
    meaningful exit code."""
    Handler.timeout_s = timeout
    Handler.last_verdict = {"accepted": None}

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}/"
    if auto_run:
        url += "?run=1"
    if focus_slug:
        url += f"#{focus_slug}"

    print()
    print("  " + T.paint(f"Serving the practice dashboard at {url}", T.GREEN))
    print("  " + T.paint("Ctrl-C here stops it.", T.MUTED))
    print()

    if open_browser:
        threading.Timer(0.3, webbrowser.open, args=(url,)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        server.shutdown()
        server.server_close()

    accepted = Handler.last_verdict["accepted"]
    return 0 if accepted or accepted is None else 1


INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DSA Practice</title>
<link rel="icon" href="data:,">
<style>
:root{
  --bg:#1a1a1a; --panel:#262626; --inset:#1e1e1e; --border:#3a3a3a;
  --fg:#e6e6e6; --muted:#8a8a8a; --green:#00b8a3; --red:#ef4743;
  --yellow:#ffa116; --blue:#3884ff;
}
*{box-sizing:border-box;}
html,body{margin:0;padding:0;}
body{
  background:var(--bg); color:var(--fg);
  font-family:"Segoe UI", -apple-system, BlinkMacSystemFont, sans-serif;
  font-size:14px; line-height:1.5;
}
code, pre, .mono{font-family:Consolas, "Cascadia Mono", Menlo, monospace;}
a{color:inherit;}
button{
  font-family:inherit; font-size:13px; cursor:pointer;
  background:var(--inset); color:var(--fg); border:1px solid var(--border);
  border-radius:6px; padding:8px 14px; transition:background .15s, border-color .15s;
}
button:hover{background:var(--border);}
button:disabled{opacity:.55; cursor:default;}
button.primary{background:var(--green); border-color:var(--green); color:#04231f; font-weight:600;}
button.primary:hover{filter:brightness(1.08);}
input[type=text]{
  font-family:inherit; font-size:13px; background:var(--inset); color:var(--fg);
  border:1px solid var(--border); border-radius:6px; padding:8px 12px; outline:none;
}
input[type=text]:focus{border-color:var(--blue);}

.topbar{
  position:sticky; top:0; z-index:10; background:var(--panel);
  border-bottom:1px solid var(--border);
  display:flex; align-items:center; gap:14px;
  padding:14px 24px;
}
.topbar .brand{font-weight:700; font-size:16px; letter-spacing:.2px;}
.topbar .brand .dot{color:var(--muted); font-weight:400; margin:0 8px;}
.topbar .spacer{flex:1;}
.topbar .crumb{color:var(--muted); cursor:pointer;}
.topbar .crumb:hover{color:var(--fg);}

main{max-width:1040px; margin:0 auto; padding:24px;}

.grid{
  display:grid; grid-template-columns:repeat(auto-fill, minmax(230px, 1fr));
  gap:14px; margin-top:18px;
}
.card{
  background:var(--panel); border:1px solid var(--border); border-radius:10px;
  padding:16px; cursor:pointer; transition:transform .12s, border-color .12s, box-shadow .12s;
}
.card:hover{
  transform:translateY(-2px); border-color:var(--blue);
  box-shadow:0 6px 18px rgba(0,0,0,.35);
}
.card .title{font-weight:600; font-size:15px; margin-bottom:6px;}
.card .slug{color:var(--muted); font-size:12px; margin-bottom:10px;}
.badge{
  display:inline-block; font-size:11px; font-weight:600; letter-spacing:.3px;
  padding:3px 8px; border-radius:999px; text-transform:uppercase;
}
.badge.ready{background:rgba(0,184,163,.15); color:var(--green);}
.badge.missing{background:rgba(255,161,22,.15); color:var(--yellow);}
.badge.accepted{background:rgba(0,184,163,.15); color:var(--green);}
.badge.failed{background:rgba(239,71,67,.15); color:var(--red);}

.empty{color:var(--muted); text-align:center; padding:60px 0;}
.empty code{background:var(--inset); padding:2px 6px; border-radius:4px;}

.count{color:var(--muted); font-size:13px; margin-top:2px;}

h1{font-size:22px; margin:0 0 4px;}
h2{font-size:16px; margin:22px 0 10px;}

.section{
  background:var(--panel); border:1px solid var(--border); border-radius:10px;
  padding:18px 20px; margin-bottom:18px;
}
.section .heading{display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;}
.section .heading h2{margin:0;}

.markdown h1, .markdown h2, .markdown h3{margin-top:18px; margin-bottom:8px;}
.markdown h1:first-child, .markdown h2:first-child, .markdown h3:first-child{margin-top:0;}
.markdown p{margin:8px 0;}
.markdown ul{margin:8px 0; padding-left:22px;}
.markdown code{background:var(--inset); padding:1px 5px; border-radius:4px;}
.markdown pre.code-block{
  background:var(--inset); border:1px solid var(--border); border-radius:8px;
  padding:12px 14px; overflow-x:auto;
}
.markdown pre.code-block code{background:none; padding:0;}

.code-viewer{
  display:flex; background:var(--inset); border:1px solid var(--border);
  border-radius:8px; overflow-x:auto; font-size:12.5px;
}
.code-viewer .lines{
  color:var(--muted); text-align:right; user-select:none;
  padding:12px 10px 12px 14px; border-right:1px solid var(--border); flex-shrink:0;
}
.code-viewer .code{padding:12px 14px; white-space:pre; flex:1;}
.tok-k{color:var(--blue);}
.tok-s{color:var(--green);}
.tok-c{color:var(--muted); font-style:italic;}
.tok-n{color:var(--yellow);}

.verdict-banner{
  border:1px solid var(--border); border-left:4px solid var(--muted);
  border-radius:8px; padding:14px 18px; margin-bottom:16px;
}
.verdict-banner .v-title{font-size:19px; font-weight:700;}
.verdict-banner .v-tally{color:var(--muted); font-size:13px; margin-top:2px;}

.tiles{display:flex; gap:10px; margin:10px 0;}
.tile{
  flex:1; background:var(--inset); border-radius:8px; padding:10px 14px;
}
.tile .t-label{color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.3px;}
.tile .t-value{font-size:17px; font-weight:700; color:var(--green); margin:2px 0;}
.tile .t-note{color:var(--muted); font-size:11.5px;}

.case-row{
  display:flex; align-items:center; gap:10px; padding:5px 4px;
  border-bottom:1px solid var(--border);
}
.case-row:last-child{border-bottom:none;}
.case-row .glyph{width:16px; text-align:center; font-weight:700;}
.case-row .cname{flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;}
.case-row .bar-wrap{width:140px; flex-shrink:0;}
.case-row .bar-bg{background:rgba(255,255,255,.06); border-radius:3px; height:6px; overflow:hidden;}
.case-row .bar-fill{height:100%; border-radius:3px;}
.case-row .note{width:88px; text-align:right; flex-shrink:0; font-size:12px;}

.fail-card{
  border:1px solid var(--border); border-radius:8px; padding:14px 16px; margin-top:10px;
  background:var(--inset);
}
.fail-card .fc-head{font-weight:700; margin-bottom:6px;}
.field-label{color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.3px; margin-top:10px;}
.field-value{white-space:pre-wrap; word-break:break-word; margin-top:2px;}

.scaling-table{width:100%; border-collapse:collapse; margin-top:8px; font-size:12.5px;}
.scaling-table th, .scaling-table td{text-align:right; padding:4px 8px;}
.scaling-table th{color:var(--muted); font-weight:600; border-bottom:1px solid var(--border);}
.scaling-table td:first-child, .scaling-table th:first-child{text-align:left;}

.spinner{
  display:inline-block; width:14px; height:14px; border-radius:50%;
  border:2px solid rgba(255,255,255,.25); border-top-color:var(--fg);
  animation:spin .7s linear infinite; vertical-align:-2px; margin-right:6px;
}
@keyframes spin{to{transform:rotate(360deg);}}
</style>
</head>
<body>
<div id="app"></div>
<script>
"use strict";

const state = { problems: null, lastVerdict: {} };

function esc(s){
  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

function fmtMs(ms){
  if (ms == null) return "-";
  if (ms < 1) return ms.toFixed(2) + " ms";
  if (ms < 1000) return Math.round(ms) + " ms";
  return (ms/1000).toFixed(2) + " s";
}
function fmtKb(kb){
  if (kb == null) return "-";
  if (kb < 1024) return kb.toFixed(1) + " KB";
  return (kb/1024).toFixed(2) + " MB";
}

/* ---------------------------------------------------------- markdown-lite */

function inlineMd(s){
  return s
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>");
}

function mdToHtml(src){
  const lines = esc(src).split("\n");
  let html = "", inList = false, i = 0;
  const closeList = () => { if (inList) { html += "</ul>"; inList = false; } };
  while (i < lines.length) {
    const line = lines[i];
    if (line.startsWith("```")) {
      closeList();
      const buf = []; i++;
      while (i < lines.length && !lines[i].startsWith("```")) { buf.push(lines[i]); i++; }
      i++;
      html += `<pre class="code-block"><code>${buf.join("\n")}</code></pre>`;
      continue;
    }
    const heading = line.match(/^(#{1,6})\s+(.*)$/);
    if (heading) {
      closeList();
      const level = heading[1].length;
      html += `<h${level}>${inlineMd(heading[2])}</h${level}>`;
      i++; continue;
    }
    if (/^[-*]\s+/.test(line)) {
      if (!inList) { html += "<ul>"; inList = true; }
      html += `<li>${inlineMd(line.replace(/^[-*]\s+/, ""))}</li>`;
      i++; continue;
    }
    closeList();
    if (line.trim() === "") { i++; continue; }
    const buf = [line]; i++;
    while (i < lines.length && lines[i].trim() !== "" &&
           !lines[i].startsWith("```") && !/^#{1,6}\s+/.test(lines[i]) &&
           !/^[-*]\s+/.test(lines[i])) {
      buf.push(lines[i]); i++;
    }
    html += `<p>${inlineMd(buf.join(" "))}</p>`;
  }
  closeList();
  return html || '<p class="field-value" style="color:var(--muted)">No question file in this folder.</p>';
}

/* ------------------------------------------------------- python highlight */

const PY_KEYWORDS = new Set(["def","return","if","elif","else","for","while","in",
  "import","from","class","try","except","finally","with","as","pass","break",
  "continue","lambda","None","True","False","and","or","not","is","yield",
  "global","nonlocal","raise","assert","del","async","await","self"]);

function highlightPython(src){
  const escaped = esc(src);
  const tokenRe = /(#.*$)|('{3}[\s\S]*?'{3}|"{3}[\s\S]*?"{3}|'(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*")|(\b\d+\.?\d*\b)|(\b[A-Za-z_][A-Za-z0-9_]*\b)/gm;
  return escaped.replace(tokenRe, (m, comment, string, number, ident) => {
    if (comment) return `<span class="tok-c">${comment}</span>`;
    if (string) return `<span class="tok-s">${string}</span>`;
    if (number) return `<span class="tok-n">${number}</span>`;
    if (ident) return PY_KEYWORDS.has(ident) ? `<span class="tok-k">${ident}</span>` : ident;
    return m;
  });
}

function codeViewer(src){
  if (!src.trim()) return '<p style="color:var(--muted)">No solution.py in this folder.</p>';
  const lines = src.replace(/\n$/, "").split("\n");
  const numbers = lines.map((_, idx) => idx + 1).join("\n");
  return `<div class="code-viewer"><div class="lines">${numbers}</div>` +
         `<div class="code">${highlightPython(lines.join("\n"))}</div></div>`;
}

/* --------------------------------------------------------------- routing */

async function loadProblems(){
  if (!state.problems) {
    const res = await fetch("/api/problems");
    state.problems = await res.json();
  }
  return state.problems;
}

window.addEventListener("hashchange", route);
window.addEventListener("DOMContentLoaded", route);

async function route(){
  const slug = decodeURIComponent(location.hash.slice(1));
  if (!slug) await renderList();
  else await renderDetail(slug);
}

/* ------------------------------------------------------------ list view */

async function renderList(){
  const app = document.getElementById("app");
  app.innerHTML = `
    <div class="topbar">
      <div class="brand">DSA Practice<span class="dot">&middot;</span><span style="color:var(--muted);font-weight:400;font-size:13px">local judge</span></div>
      <div class="spacer"></div>
      <input type="text" id="search" placeholder="Filter problems...">
    </div>
    <main>
      <h1>Problems</h1>
      <div class="count" id="count"></div>
      <div class="grid" id="grid"></div>
    </main>`;

  const problems = await loadProblems();
  document.getElementById("search").addEventListener("input", (e) => paint(e.target.value));
  paint("");

  function paint(filter){
    const f = filter.trim().toLowerCase();
    const shown = problems.filter(p =>
      !f || p.slug.toLowerCase().includes(f) || p.title.toLowerCase().includes(f));

    const readyCount = problems.filter(p => p.ready).length;
    document.getElementById("count").textContent =
      `${problems.length} problem${problems.length===1?"":"s"} · ${readyCount} ready`;

    const grid = document.getElementById("grid");
    if (problems.length === 0) {
      grid.outerHTML = `<div class="empty">No problems yet.<br><br>Create one with <code>python practice.py new "two sum"</code></div>`;
      return;
    }
    if (shown.length === 0) {
      grid.innerHTML = `<div class="empty" style="grid-column:1/-1">No problems match that filter.</div>`;
      return;
    }
    grid.innerHTML = shown.map(cardHtml).join("");
    grid.querySelectorAll(".card").forEach(el => {
      el.addEventListener("click", () => { location.hash = el.dataset.slug; });
    });
  }
}

function cardHtml(p){
  const last = state.lastVerdict[p.slug];
  let badge;
  if (last) {
    badge = `<span class="badge ${last.accepted ? "accepted" : "failed"}">${esc(last.verdict)}</span>`;
  } else {
    badge = p.ready
      ? '<span class="badge ready">Ready</span>'
      : '<span class="badge missing">No tests</span>';
  }
  return `<div class="card" data-slug="${esc(p.slug)}">
    <div class="title">${esc(p.title)}</div>
    <div class="slug mono">${esc(p.slug)}</div>
    ${badge}
  </div>`;
}

/* ---------------------------------------------------------- detail view */

async function renderDetail(slug){
  const app = document.getElementById("app");
  app.innerHTML = `
    <div class="topbar">
      <div class="crumb" id="back">&larr; All problems</div>
      <div class="spacer"></div>
      <button class="primary" id="runBtn">Run</button>
    </div>
    <main id="detailMain">
      <div class="empty"><span class="spinner"></span>Loading...</div>
    </main>`;
  document.getElementById("back").addEventListener("click", () => { location.hash = ""; });

  let detail;
  try {
    const res = await fetch("/api/problems/" + encodeURIComponent(slug));
    if (!res.ok) throw new Error((await res.json()).error || "not found");
    detail = await res.json();
  } catch (err) {
    document.getElementById("detailMain").innerHTML =
      `<div class="empty">${esc(err.message)}</div>`;
    return;
  }

  const main = document.getElementById("detailMain");
  main.innerHTML = `
    <h1>${esc(detail.title)}</h1>
    <div class="count mono">${esc(detail.slug)}</div>
    <div id="results"></div>
    <div class="section">
      <div class="heading"><h2>Question</h2></div>
      <div class="markdown">${mdToHtml(detail.question)}</div>
    </div>
    <div class="section">
      <div class="heading"><h2>Solution</h2></div>
      ${codeViewer(detail.solution)}
    </div>`;

  const runBtn = document.getElementById("runBtn");
  runBtn.addEventListener("click", () => runProblem(slug));

  const params = new URLSearchParams(location.search);
  if (params.get("run") === "1") {
    history.replaceState(null, "", location.pathname + location.hash);
    runProblem(slug);
  }
}

async function runProblem(slug){
  const runBtn = document.getElementById("runBtn");
  const results = document.getElementById("results");
  if (!runBtn || !results) return;
  runBtn.disabled = true;
  runBtn.innerHTML = '<span class="spinner"></span>Judging...';
  results.innerHTML = `<div class="empty" style="padding:30px 0"><span class="spinner"></span>Running testcases...</div>`;

  try {
    const res = await fetch(`/api/problems/${encodeURIComponent(slug)}/run`, { method: "POST" });
    const sub = await res.json();
    if (!res.ok) throw new Error(sub.error || "run failed");
    state.lastVerdict[slug] = { verdict: sub.verdict, accepted: sub.accepted };
    results.innerHTML = resultsHtml(sub);
  } catch (err) {
    results.innerHTML = `<div class="section" style="border-color:var(--red)">${esc(err.message)}</div>`;
  } finally {
    runBtn.disabled = false;
    runBtn.textContent = "Run";
  }
}

const VERDICT_COLOR = {
  "Accepted": "var(--green)",
  "Wrong Answer": "var(--red)",
  "Runtime Error": "var(--red)",
  "Compile Error": "var(--red)",
  "Time Limit Exceeded": "var(--yellow)",
  "Harness Error": "var(--yellow)",
};

function resultsHtml(sub){
  const color = VERDICT_COLOR[sub.verdict] || "var(--yellow)";
  const glyph = sub.accepted ? "✓" : "✗";
  let html = `<div class="verdict-banner" style="border-left-color:${color}">
    <div class="v-title" style="color:${color}">${glyph} ${esc(sub.verdict)}</div>
    <div class="v-tally">${sub.total ? sub.passed + " / " + sub.total + " testcases passed" : ""}</div>
  </div>`;

  if (sub.load_error && (!sub.cases || sub.cases.length === 0)) {
    html += loadErrorHtml(sub);
  } else if (sub.accepted) {
    html += analysisHtml(sub);
    html += caseListHtml(sub);
  } else {
    html += caseListHtml(sub);
    html += failuresHtml(sub);
  }
  return html;
}

function loadErrorHtml(sub){
  const err = sub.load_error || {};
  const origin = {solution: "solution.py", tests: "tests.py", harness: "the harness"}[err.phase] || "your code";
  const title = sub.verdict === "Time Limit Exceeded" ? "Execution stopped" : `Raised while loading ${origin}`;
  let msg = err.message || "";
  if (sub.verdict !== "Time Limit Exceeded") msg = `${err.type}: ${msg}`;
  let where = "";
  if (err.line) {
    where = `<div class="field-label">Location</div><div class="field-value mono">Line ${err.line} in ${esc(err.func || "<module>")} (${esc(err.file || "")})</div>`;
    if (err.code) where += `<div class="field-value mono" style="color:var(--muted)">${esc(err.code)}</div>`;
  }
  return `<div class="section">
    <h2>${esc(title)}</h2>
    <div class="field-value mono" style="color:var(--red)">${esc(msg)}</div>
    ${where}
  </div>`;
}

function analysisHtml(sub){
  const slowest = Math.max(0, ...sub.cases.map(c => c.runtime_ms));
  let html = `<div class="section">
    <h2>Runtime and space</h2>
    <div class="tiles">
      <div class="tile"><div class="t-label">Runtime</div><div class="t-value">${fmtMs(sub.runtime_ms)}</div><div class="t-note">${sub.total} testcases, slowest ${fmtMs(slowest)}</div></div>
      <div class="tile"><div class="t-label">Memory</div><div class="t-value">${fmtKb(sub.peak_kb || 0)}</div><div class="t-note">peak tracked allocation</div></div>
    </div>`;
  html += scalingHtml(sub.scaling);
  html += `</div>`;
  return html;
}

function scalingHtml(scaling){
  if (!scaling) {
    return `<div class="field-label" style="margin-top:14px">Add scaling_input(n) to tests.py to measure how this scales.</div>`;
  }
  if (scaling.error) {
    return `<div class="field-value" style="color:var(--yellow)">Complexity: ${esc(scaling.error)}</div>`;
  }
  const rows = scaling.rows || [];
  if (rows.length === 0) return "";
  let html = `<div class="field-label" style="margin-top:14px">Measured complexity</div><div class="tiles">`;
  for (const [key, title] of [["time","Time"],["space","Space"]]) {
    const block = scaling[key] || {};
    let detail = `fit ${(block.fit || 0).toFixed(3)}`;
    if (block.exponent != null) detail += `   log-log slope ${block.exponent.toFixed(2)}`;
    html += `<div class="tile"><div class="t-label">${title}</div><div class="t-value">${esc(block.label || "?")}</div><div class="t-note">${esc(detail)}</div></div>`;
  }
  html += `</div><table class="scaling-table"><thead><tr><th>n</th><th>time</th><th>space</th></tr></thead><tbody>`;
  for (const row of rows) {
    html += `<tr><td>${row.n}</td><td>${fmtMs(row.ms)}</td><td>${fmtKb(row.kb)}</td></tr>`;
  }
  html += `</tbody></table>
    <div class="field-value" style="color:var(--muted);font-size:12px;margin-top:8px">
      Measured on this machine, from your own runs - not a comparison against other people's submissions.
    </div>`;
  return html;
}

function caseListHtml(sub){
  const peak = Math.max(1, ...sub.cases.map(c => c.runtime_ms));
  const title = sub.accepted ? "Testcases" : `Testcases · ${sub.cases.filter(c=>!c.ok).length} failing`;
  let html = `<div class="section"><h2>${esc(title)}</h2>`;
  for (const c of sub.cases) {
    let glyph, color, note, noteColor;
    if (c.ok) { glyph = "✓"; color = "var(--green)"; note = fmtMs(c.runtime_ms); noteColor = "var(--muted)"; }
    else if (c.status === "error") { glyph = "✗"; color = "var(--red)"; note = (c.error||{}).type || "Error"; noteColor = "var(--red)"; }
    else { glyph = "✗"; color = "var(--red)"; note = "Wrong Answer"; noteColor = "var(--red)"; }
    const width = Math.max(2, Math.round(100 * c.runtime_ms / peak));
    html += `<div class="case-row">
      <span class="glyph" style="color:${color}">${glyph}</span>
      <span class="mono" style="width:64px;color:var(--muted);flex-shrink:0">Case ${c.number}</span>
      <span class="cname">${esc(c.name)}</span>
      <span class="bar-wrap"><div class="bar-bg"><div class="bar-fill" style="width:${width}%;background:${color}"></div></div></span>
      <span class="note" style="color:${noteColor}">${esc(note)}</span>
    </div>`;
  }
  html += `</div>`;
  return html;
}

function failuresHtml(sub){
  let html = "";
  for (const c of sub.cases.filter(c => !c.ok)) {
    html += `<div class="fail-card">
      <div class="fc-head">Case ${c.number} &nbsp; <span style="color:var(--muted);font-weight:400">${esc(c.name)}</span></div>`;
    const entries = Object.entries(c.args_repr || {});
    if (entries.length) {
      entries.forEach(([k, v], idx) => {
        html += `<div class="field-label">${idx===0?"Input":""}</div><div class="field-value mono">${esc(k)} = ${esc(v)}</div>`;
      });
    } else {
      html += `<div class="field-label">Input</div><div class="field-value mono">(no arguments)</div>`;
    }
    if (c.stdout && c.stdout.trim()) {
      html += `<div class="field-label">Stdout</div><div class="field-value mono" style="color:var(--muted)">${esc(c.stdout.trimEnd())}</div>`;
    }
    if (c.status === "error") {
      const err = c.error || {};
      html += `<div class="field-label">Output</div><div class="field-value mono" style="color:var(--red)">${esc(err.type)}: ${esc(err.message)}</div>`;
      if (err.line) {
        html += `<div class="field-value mono" style="color:var(--muted)">Line ${err.line} in ${esc(err.func || "<module>")} (${esc(err.file || "")})</div>`;
        if (err.code) html += `<div class="field-value mono" style="color:var(--muted)">${esc(err.code)}</div>`;
      }
    } else {
      html += `<div class="field-label">Output</div><div class="field-value mono" style="color:var(--red)">${esc(c.output_repr || "None")}</div>`;
    }
    html += `<div class="field-label">Expected</div><div class="field-value mono" style="color:var(--green)">${esc(c.expected_repr)}</div>`;
    html += `</div>`;
  }
  return html;
}
</script>
</body>
</html>
"""
