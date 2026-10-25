#!/usr/bin/env python3
"""Local-only DE Lab control panel. Python stdlib; no external dependencies."""
import ast
import json
import os
import sqlite3
import subprocess
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
HOST = "127.0.0.1"
PORT = int(os.environ.get("DE_LAB_PORT", "8765"))
OLLAMA = os.environ.get("DE_LAB_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
PROFILES = {"core": ["postgres"], "analytics": ["postgres", "clickhouse"], "batch": ["minio"], "lakehouse": ["minio"], "streaming": ["postgres", "kafka"]}
ACTIVE = set()
LOCK = threading.Lock()
MAX_REQUEST = 24000
SQL_TASKS = [
    {"id": "sql-001", "title": "Revenue per customer", "prompt": "Return customer and total revenue, grouped by customer and sorted by total descending.", "hint": "Use SUM(amount), GROUP BY and ORDER BY.", "answer": [["B", 200], ["A", 150]]},
    {"id": "sql-002", "title": "Large orders", "prompt": "Return id and amount for orders of at least 100, sorted by id.", "hint": "Filter with WHERE and sort with ORDER BY.", "answer": [[1, 100], [2, 200]]},
]
SYS_RUBRIC = ["requirements", "data model", "data ingestion", "scalability", "consistency", "fault tolerance", "observability", "security", "cost and tradeoffs"]
def call(cmd, timeout=75):
    try:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout, check=False)
        return {"ok": p.returncode == 0, "output": (p.stdout + p.stderr)[-5000:]}
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"ok": False, "output": str(e)}
def services_running(profile):
    return [service for service in PROFILES[profile] if any(service in PROFILES[other] for other in ACTIVE if other != profile)]
def switch_profile(name, action):
    if name not in PROFILES or action not in ("start", "stop"):
        return {"ok": False, "message": "Unknown profile or action"}
    if not LOCK.acquire(blocking=False):
        return {"ok": False, "message": "Another operation is in progress"}
    try:
        if action == "start":
            result = call(["docker", "compose", "--profile", name, "up", "-d", "--remove-orphans"], 180)
            if result["ok"]:
                ACTIVE.add(name)
            return result
        keep = services_running(name)
        stop = [x for x in PROFILES[name] if x not in keep]
        result = call(["docker", "compose", "stop", *stop], 90) if stop else {"ok": True, "output": "Only shared services were active"}
        if result["ok"]:
            ACTIVE.discard(name)
        return {**result, "kept_shared": keep}
    finally:
        LOCK.release()
def grade_sql(task_id, sql):
    task = next((t for t in SQL_TASKS if t["id"] == task_id), None)
    if task is None or len(sql) > 10000:
        return {"ok": False, "message": "Unknown task or source too long"}
    if not sql.lstrip().upper().startswith(("SELECT ", "WITH ")):
        return {"ok": False, "message": "Only SELECT and WITH queries are supported"}
    if ";" in sql.strip().rstrip(";"):
        return {"ok": False, "message": "Only one statement is allowed"}
    db = sqlite3.connect(":memory:")
    try:
        db.executescript("CREATE TABLE orders(id INTEGER,customer TEXT,amount INTEGER); INSERT INTO orders VALUES(1,'A',100),(2,'B',200),(3,'A',50);")
        allowed = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION}
        db.set_authorizer(lambda action, *args: sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY)
        db.set_progress_handler(lambda: 1 if time.monotonic() > deadline else 0, 1000)
        deadline = time.monotonic() + 2
        rows = db.execute(sql).fetchmany(101)
        passed = [list(r) for r in rows] == task["answer"]
        return {"ok": passed, "message": "Passed" if passed else "Incorrect result", "actual": rows[:10]}
    except sqlite3.Error as e:
        return {"ok": False, "message": str(e)}
    finally:
        db.close()
def ollama(path, payload=None):
    if not OLLAMA.startswith(("http://127.0.0.1:", "http://localhost:")):
        return {"error": "Only loopback Ollama endpoints are permitted"}
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(OLLAMA + path, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=90 if payload else 4) as response:
            return json.loads(response.read(200000).decode())
    except (OSError, ValueError) as e:
        return {"error": str(e)}
def ai_answer(body):
    kind = body.get("mode", "tutor")
    question = str(body.get("question", ""))[:10000]
    model = str(body.get("model", ""))[:100]
    if kind not in ("tutor", "system-design", "algorithm") or not question or not model:
        return {"error": "Invalid question, mode or model"}
    available = ollama("/api/tags")
    names = {m.get("name") for m in available.get("models", [])}
    if model not in names:
        return {"error": "Model not found in local Ollama"}
    prompt = {
        "tutor": "Explain technically, provide grounded assumptions, hints before solutions and validate claims.",
        "system-design": "Assess architecture with evidence, explicitly score each rubric dimension 0–5, request missing requirements and highlight tradeoffs. Rubric: " + ", ".join(SYS_RUBRIC),
        "algorithm": "Explain invariant, alternatives, time/space complexity, edge cases, and Python 3 reference implementation when asked."
    }[kind]
    response = ollama("/api/chat", {"model": model, "stream": False, "options": {"num_ctx": 8192}, "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": question}]})
    return {"answer": response.get("message", {}).get("content", ""), "error": response.get("error")}
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass
    def reply(self, obj, code=200):
        data = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def allowed(self):
        return self.client_address[0] in ("127.0.0.1", "::1") and self.headers.get("Host", "").split(":")[0] in ("localhost", "127.0.0.1")
    def do_GET(self):
        if not self.allowed(): return self.reply({"error": "local access only"}, 403)
        path = urlparse(self.path).path
        if path == "/":
            data = (ROOT / "web" / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            return self.wfile.write(data)
        if path == "/api/info": return self.reply({"profiles": PROFILES, "active": sorted(ACTIVE), "tasks": [{k: v for k,v in t.items() if k != "answer"} for t in SQL_TASKS]})
        if path == "/api/models": return self.reply(ollama("/api/tags"))
        if path == "/api/status": return self.reply(call(["docker", "compose", "ps", "--format", "json"], 10))
        return self.reply({"error": "Not found"}, 404)
    def do_POST(self):
        if not self.allowed() or self.headers.get("Origin", "") not in ("", f"http://localhost:{PORT}", f"http://127.0.0.1:{PORT}"):
            return self.reply({"error": "forbidden"}, 403)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > MAX_REQUEST: return self.reply({"error": "Invalid body size"}, 413)
            body = json.loads(self.rfile.read(length))
        except (ValueError, UnicodeDecodeError):
            return self.reply({"error": "Invalid JSON"}, 400)
        path = urlparse(self.path).path
        if path == "/api/profile": return self.reply(switch_profile(str(body.get("profile", "")), str(body.get("action", ""))))
        if path == "/api/grade": return self.reply(grade_sql(str(body.get("id", "")), str(body.get("sql", ""))))
        if path == "/api/ai": return self.reply(ai_answer(body))
        return self.reply({"error": "Not found"}, 404)
if __name__ == "__main__":
    print(f"DE Lab Studio: http://{HOST}:{PORT}")
    webbrowser.open(f"http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
