#!/usr/bin/env python3
"""
Task Hierarchy UI — IV-2-2 kernel module (src/kmod)-ийн /proc/pid, /proc/pid_tree-ийг вэбээр харуулах сервер.
Module-тай тохирох интерфейсийг src/ui/README.md-ээс харна уу.

Зөвхөн Python 3 стандарт сан ашиглана (нэмэлт суулгац шаардлагагүй).

    python3 src/ui/server.py                 # http://localhost:8000
    python3 src/ui/server.py --port 9000
    python3 src/ui/server.py --fallback      # module байхгүй үед /proc/<pid>/stat-аас (UI-д тодорхой тэмдэглэнэ)

API:
    GET  /api/status                 — backend, module ачаалагдсан эсэх, кернел
    GET  /api/task?pid=N&depth=D     — task, өвөг эцгүүд, D түвшний хүү процессын мод, номын мөр
    GET  /api/processes              — сонгоход зориулсан бүх процессын жагсаалт
    POST /api/demo                   — туршилтын процессын мод үүсгэнэ (src/ui/demo_tree.py)
    POST /api/demo/stop              — туршилтын модыг зогсооно
"""
import argparse
import json
import os
import platform
import re
import signal
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

PROC_PID = "/proc/pid"
PROC_TREE = "/proc/pid_tree"
PID_MAX_LIMIT = 4194304                  # кернелийн PID_MAX_LIMIT (64-бит)
MAX_DEPTH = 6
MAX_NODES = 400

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
DEMO_SCRIPT = ROOT / "demo_tree.py"

STATE_NAMES = {
    "R": "running", "S": "sleeping", "D": "disk sleep (uninterruptible)",
    "T": "stopped", "t": "tracing stop", "Z": "zombie", "X": "dead",
    "I": "idle", "P": "parked", "W": "waking", "K": "wakekill",
}

# Module нэг л ГЛОБАЛ PID хадгалдаг. Хоёр хүсэлт зэрэг "бичих → унших" хийвэл
# нэг нь нөгөөгийн PID-ийг уншина (уралдааны нөхцөл). Тиймээс бичих+унших
# хоёрыг энэ мутексээр нэг эгзэгтэй мужид оруулна.
_module_lock = threading.Lock()


class TaskError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def parse_pid(text):
    """Хэрэглэгчийн оролтыг шалгана: зөвхөн цифр, 0..PID_MAX_LIMIT."""
    if text is None or text.strip() == "":
        raise TaskError(400, "PID оруулаагүй байна")
    text = text.strip()
    if not text.isdigit():
        raise TaskError(400, f"Буруу оролт '{text}': эерэг бүхэл тоо оруулна уу")
    pid = int(text)
    if pid > PID_MAX_LIMIT:
        raise TaskError(400, f"PID {pid} нь хязгаараас (0..{PID_MAX_LIMIT}) хэтэрсэн")
    return pid


def parse_depth(text):
    if text in (None, ""):
        return 2
    if not text.isdigit() or not 0 <= int(text) <= MAX_DEPTH:
        raise TaskError(400, f"depth 0..{MAX_DEPTH} хооронд байна")
    return int(text)


_LINE = re.compile(r"^(\w+) (.*?)(?: comm=(.*))?$")


def parse_tree_output(raw):
    """/proc/pid_tree-ийн текстийг бүтэц болгоно."""
    task, ancestors, children, summary = None, [], [], {}
    for line in raw.splitlines():
        m = _LINE.match(line)
        if not m:
            continue
        tag, rest, comm = m.groups()
        fields = dict(kv.split("=", 1) for kv in rest.split() if "=" in kv)
        if tag == "summary":
            summary = {k: int(v) for k, v in fields.items()}
            continue
        node = {
            "pid": int(fields["pid"]), "tgid": int(fields["tgid"]), "ppid": int(fields["ppid"]),
            "state": int(fields["state"]), "state_char": fields["state_char"],
            "state_name": STATE_NAMES.get(fields["state_char"], "?"),
            "uid": int(fields["uid"]), "threads": int(fields["threads"]), "comm": comm or "",
        }
        if tag == "task":
            task = node
        elif tag == "ancestor":
            ancestors.append(node)
        elif tag == "child":
            children.append(node)
    return task, ancestors, children, summary


class ModuleBackend:
    """Жинхэнэ kernel module: PID-ийг /proc/pid руу бичиж, /proc/pid ба /proc/pid_tree-ийг уншина."""
    name = "kernel module (/proc/pid, /proc/pid_tree)"

    @staticmethod
    def available():
        return os.path.exists(PROC_PID) and os.path.exists(PROC_TREE)

    def query(self, pid):
        with _module_lock:
            try:
                with open(PROC_PID, "w") as f:
                    f.write(f"{pid}\n")
            except OSError as e:
                raise TaskError(400, f"Module оролтыг татгалзлаа: {e.strerror}")
            with open(PROC_PID) as f:
                book_line = f.read().strip()
            with open(PROC_TREE) as f:
                raw = f.read()
        if not raw.strip():
            raise TaskError(404, f"PID {pid} олдсонгүй — module 0 байт буцаалаа (номын шаардлага)")
        task, ancestors, children, summary = parse_tree_output(raw)
        return {"book_line": book_line, "task": task, "ancestors": ancestors,
                "children": children, "summary": summary, "raw": raw}


class ProcfsBackend:
    """Нөөц горим: module байхгүй үед /proc/<pid>/stat-аас ижил бүтэц үүсгэнэ (UI-д тодорхой тэмдэглэнэ)."""
    name = "procfs fallback (/proc/<pid>/stat) — kernel module БИШ"

    @staticmethod
    def _stat(pid):
        try:
            with open(f"/proc/{pid}/stat") as f:
                data = f.read()
            with open(f"/proc/{pid}/status") as f:
                status = f.read()
        except OSError:
            return None
        comm = data[data.index("(") + 1:data.rindex(")")]
        rest = data[data.rindex(")") + 2:].split()
        uid = int(re.search(r"^Uid:\s+(\d+)", status, re.M).group(1))
        return {"pid": pid, "tgid": pid, "ppid": int(rest[1]), "state": -1, "state_char": rest[0],
                "state_name": STATE_NAMES.get(rest[0], "?"), "uid": uid,
                "threads": int(rest[17]), "comm": comm}

    def query(self, pid):
        task = self._stat(pid)
        if task is None:
            raise TaskError(404, f"PID {pid} олдсонгүй (/proc/{pid} байхгүй)")
        ancestors, p = [], task["ppid"]
        while p > 0 and len(ancestors) < 64:
            a = self._stat(p)
            if a is None:
                break
            ancestors.append(a)
            if p == 1:
                break
            p = a["ppid"]
        children = [s for s in (self._stat(int(d)) for d in os.listdir("/proc") if d.isdigit())
                    if s and s["ppid"] == pid]
        children.sort(key=lambda n: n["pid"])
        book = f"command = [{task['comm']}] pid = [{pid}] state = [{task['state_char']}]"
        return {"book_line": book + "   (fallback)", "task": task, "ancestors": ancestors,
                "children": children,
                "summary": {"ancestors": len(ancestors), "children": len(children), "truncated": 0},
                "raw": "(procfs fallback — module ачаалагдаагүй)\n"}


def build_tree(backend, pid, depth):
    """Сонгосон PID-ээс доош depth түвшний мод. Хүү бүрийн хүүхдүүдийг мөн module-ээс асууна."""
    root = backend.query(pid)
    counter = {"nodes": 1, "queries": 1}

    def expand(info, level):
        node = dict(info["task"])
        node["truncated"] = bool(info["summary"].get("truncated"))
        node["child_count"] = len(info["children"])
        node["children"] = []
        for child in info["children"]:
            if level < depth and counter["nodes"] < MAX_NODES:
                try:
                    sub = backend.query(child["pid"])
                    counter["queries"] += 1
                except TaskError:          # хүү процесс энэ хооронд дууссан
                    continue
                counter["nodes"] += 1
                node["children"].append(expand(sub, level + 1))
            else:
                leaf = dict(child)
                leaf["children"], leaf["unexpanded"] = [], True
                node["children"].append(leaf)
        return node

    tree = expand(root, 1)
    return root, tree, counter


def list_processes():
    procs = []
    for d in os.listdir("/proc"):
        if not d.isdigit():
            continue
        s = ProcfsBackend._stat(int(d))
        if s:
            procs.append({k: s[k] for k in ("pid", "ppid", "comm", "state_char")})
    return sorted(procs, key=lambda p: p["pid"])


class Demo:
    """demo_tree.py-г тусдаа процессын бүлэгт ажиллуулна."""
    proc = None
    root_pid = None

    @classmethod
    def start(cls):
        cls.stop()
        cls.proc = subprocess.Popen([sys.executable, str(DEMO_SCRIPT)], stdout=subprocess.PIPE,
                                    text=True, start_new_session=True)
        line = cls.proc.stdout.readline().strip()        # эхний мөр: root PID
        if not line.isdigit():
            raise TaskError(500, "demo_tree.py эхлүүлж чадсангүй")
        cls.root_pid = int(line)
        time.sleep(0.5)                                   # хүү процессууд үүсэх хугацаа
        return cls.root_pid

    @classmethod
    def stop(cls):
        if cls.proc and cls.proc.poll() is None:
            try:
                os.killpg(cls.proc.pid, signal.SIGTERM)
                cls.proc.wait(timeout=3)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                os.killpg(cls.proc.pid, signal.SIGKILL)
        if cls.proc and cls.proc.stdout:
            cls.proc.stdout.close()
        cls.proc, cls.root_pid = None, None


class Handler(BaseHTTPRequestHandler):
    fallback_allowed = False
    quiet = False

    def log_message(self, fmt, *args):            # консолд товч лог
        if not self.quiet:
            sys.stderr.write("[%s] %s\n" % (time.strftime("%H:%M:%S"), fmt % args))

    def _send(self, status, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _error(self, err):
        self._send(err.status, {"error": err.message, "status": err.status})

    def _current_backend(self):
        if ModuleBackend.available():
            return ModuleBackend()
        if self.fallback_allowed:
            return ProcfsBackend()
        raise TaskError(503, "Kernel module ачаалагдаагүй байна (/proc/pid алга). "
                             "Ачаалах: sudo insmod src/kmod/pid.ko — эсвэл --fallback горимоор асаана уу")

    def do_GET(self):
        url = urlparse(self.path)
        q = parse_qs(url.query)
        try:
            if url.path == "/api/status":
                loaded = ModuleBackend.available()
                self._send(200, {
                    "module_loaded": loaded,
                    "backend": ModuleBackend.name if loaded else
                               (ProcfsBackend.name if self.fallback_allowed else None),
                    "fallback_allowed": self.fallback_allowed,
                    "kernel": platform.release(),
                    "server_pid": os.getpid(),
                    "demo_root": Demo.root_pid,
                })
            elif url.path == "/api/task":
                pid = parse_pid(q.get("pid", [None])[0])
                depth = parse_depth(q.get("depth", [None])[0])
                backend = self._current_backend()
                t0 = time.perf_counter()
                root, tree, counter = build_tree(backend, pid, depth)
                self._send(200, {
                    "backend": backend.name, "book_line": root["book_line"],
                    "task": root["task"], "ancestors": root["ancestors"], "tree": tree,
                    "summary": root["summary"], "raw": root["raw"], "depth": depth,
                    "nodes": counter["nodes"], "queries": counter["queries"],
                    "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
                })
            elif url.path == "/api/processes":
                self._send(200, list_processes())
            else:
                self._static(url.path)
        except TaskError as e:
            self._error(e)

    def do_POST(self):
        try:
            if self.path == "/api/demo":
                self._send(200, {"root_pid": Demo.start()})
            elif self.path == "/api/demo/stop":
                Demo.stop()
                self._send(200, {"stopped": True})
            else:
                raise TaskError(404, "unknown endpoint")
        except TaskError as e:
            self._error(e)

    def _static(self, path):
        name = "index.html" if path in ("/", "/index.html") else path.removeprefix("/static/")
        target = (STATIC / name).resolve()
        if STATIC not in target.parents or not target.is_file():
            raise TaskError(404, "not found")
        ctype = {".html": "text/html", ".js": "text/javascript", ".css": "text/css",
                 ".svg": "image/svg+xml"}.get(target.suffix, "application/octet-stream")
        self._send(200, target.read_bytes(), ctype + "; charset=utf-8")


def make_server(host="127.0.0.1", port=8000, fallback=False):
    Handler.fallback_allowed = fallback
    return ThreadingHTTPServer((host, port), Handler)


def main():
    ap = argparse.ArgumentParser(description="Task Hierarchy UI for the IV-2-2 kernel module (/proc/pid)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--fallback", action="store_true",
                    help="module байхгүй үед /proc/<pid>/stat-аас унших (тэмдэглэгээтэй)")
    args = ap.parse_args()

    srv = make_server(args.host, args.port, args.fallback)
    state = "loaded" if ModuleBackend.available() else ("NOT loaded → fallback" if args.fallback
                                                        else "NOT loaded")
    print(f"kernel module (/proc/pid): {state}")
    print(f"Task Hierarchy UI: http://localhost:{args.port}   (Ctrl+C — зогсоох)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        Demo.stop()
        srv.server_close()


if __name__ == "__main__":
    main()
