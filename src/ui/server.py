#!/usr/bin/env python3
"""
Task Hierarchy UI — IV-2-2 kernel module (src/kmod)-ийн /proc/pid, /proc/pid_tree-ийг вэбээр харуулах сервер.
Module-тай тохирох интерфейсийг src/ui/README.md-ээс харна уу.

Зөвхөн Python 3 стандарт сан ашиглана (нэмэлт суулгац шаардлагагүй).

    python3 src/ui/server.py                 # http://localhost:8000
    python3 src/ui/server.py --port 9000
    python3 src/ui/server.py --fallback      # module байхгүй үед /proc/<pid>/stat-аас (UI-д тодорхой тэмдэглэнэ)

Backend-ийг автоматаар сонгоно:
    module   — /proc/pid + /proc/pid_tree (бүх өгөгдөл module-ээс)
    book     — зөвхөн номын /proc/pid: command/pid/state module-ээс, эцэг/хүүгийн холбоо procfs-оос
    fallback — module огт байхгүй, --fallback өгсөн үед

API:
    GET  /api/status                 — backend, module ачаалагдсан эсэх, кернел
    GET  /api/task?pid=N&depth=D     — task, өвөг эцгүүд, D түвшний хүү процессын мод, номын мөр
         [&expand=A,B]               — D-ээс гадна A, B зангилааг нэмж нээнэ (UI: газар дээр нь нээх)
    GET  /api/processes              — сонгоход зориулсан бүх процессын жагсаалт
    POST /api/demo                   — туршилтын процессын мод үүсгэнэ (src/ui/demo_tree.py)
    POST /api/demo/stop              — туршилтын модыг зогсооно
    POST /api/demo/spawn             — demo_root шинэ хүү процесс үүсгэнэ (SIGUSR1)
    POST /api/demo/zombie            — demo_root шууд дуусах хүү → zombie (SIGUSR2)
    POST /api/demo/reap              — demo_root wait() хийж zombie цэвэрлэнэ (SIGHUP)
    POST /api/demo/signal?pid=N&sig=STOP|CONT|TERM
                                     — demo процесст signal (зөвхөн demo процессын бүлэгт; бусад → 403)
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
MAX_EXPAND = 64

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


def _call(op, path, data, nbytes, t0):
    """Module-тэй хийсэн нэг бичих/унших үйлдлийн бүртгэл."""
    preview = data if len(data) <= 70 else data[:67] + "..."
    return {"op": op, "path": path, "data": preview, "bytes": nbytes,
            "us": round((time.perf_counter() - t0) * 1e6)}


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


def parse_expand(text):
    """expand=12,34 → {12, 34}: depth-ээс гадна нээх зангилаанууд (хамгийн ихдээ MAX_EXPAND)."""
    if text in (None, ""):
        return frozenset()
    parts = text.split(",")
    if len(parts) > MAX_EXPAND:
        raise TaskError(400, f"expand нь хамгийн ихдээ {MAX_EXPAND} PID")
    try:
        return frozenset(parse_pid(x) for x in parts)
    except TaskError as e:
        raise TaskError(400, f"expand: {e.message}")


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


# Номын формат: "command = [bash] pid = [1395] state = [1]" (state нь __state тоо;
# зарим хэрэгжүүлэлт үсгээр бичдэг тул тэрийг ч хүлээн авна)
_BOOK = re.compile(r"^command\s*=\s*\[(.*)\]\s*pid\s*=\s*\[(\d+)\]\s*state\s*=\s*\[(-?\d+|[A-Za-z])\]$")


def parse_book_line(line):
    """/proc/pid-ийн нэг мөр → {comm, pid, state, state_char} эсвэл формат таарахгүй бол None."""
    m = _BOOK.match(line.strip())
    if not m:
        return None
    comm, pid, st = m.groups()
    if st.lstrip("-").isdigit():
        return {"comm": comm, "pid": int(pid), "state": int(st), "state_char": None}
    return {"comm": comm, "pid": int(pid), "state": -1, "state_char": st}


def _write_read_book(pid, calls):
    """PID-ийг /proc/pid руу бичээд номын мөрийг уншина. _module_lock дотор дуудна."""
    t = time.perf_counter()
    try:
        with open(PROC_PID, "w") as f:
            f.write(f"{pid}\n")
    except OSError as e:
        raise TaskError(400, f"Module оролтыг татгалзлаа: {e.strerror}")
    calls.append(_call("write", PROC_PID, f"{pid}\\n", len(f"{pid}\n"), t))
    t = time.perf_counter()
    with open(PROC_PID) as f:
        book_line = f.read().strip()
    calls.append(_call("read", PROC_PID, book_line, len(book_line), t))
    return book_line


class ModuleBackend:
    """Жинхэнэ kernel module: PID-ийг /proc/pid руу бичиж, /proc/pid ба /proc/pid_tree-ийг уншина."""
    name = "kernel module (/proc/pid, /proc/pid_tree)"
    mode = "module"

    @staticmethod
    def available():
        return os.path.exists(PROC_PID) and os.path.exists(PROC_TREE)

    def query(self, pid):
        calls = []                                # UI-ийн "Module дуудлагын лог"-д
        with _module_lock:
            book_line = _write_read_book(pid, calls)
            t = time.perf_counter()
            with open(PROC_TREE) as f:
                raw = f.read()
            calls.append(_call("read", PROC_TREE, raw.split("\n", 1)[0], len(raw), t))
        if not raw.strip():
            raise TaskError(404, f"PID {pid} олдсонгүй — module 0 байт буцаалаа (номын шаардлага)")
        task, ancestors, children, summary = parse_tree_output(raw)
        return {"book_line": book_line, "task": task, "ancestors": ancestors,
                "children": children, "summary": summary, "raw": raw, "calls": calls}


class ProcfsBackend:
    """Нөөц горим: module байхгүй үед /proc/<pid>/stat-аас ижил бүтэц үүсгэнэ (UI-д тодорхой тэмдэглэнэ)."""
    name = "procfs fallback (/proc/<pid>/stat) — kernel module БИШ"
    mode = "fallback"

    def __init__(self):
        # Хүсэлт бүрт шинэ объект → /proc-ийг нэг л удаа уншина (мод нэг агшны, тогтвортой).
        self._snapshot = None

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
        tgid = int(re.search(r"^Tgid:\s+(\d+)", status, re.M).group(1))
        return {"pid": pid, "tgid": tgid, "ppid": int(rest[1]), "state": -1, "state_char": rest[0],
                "state_name": STATE_NAMES.get(rest[0], "?"), "uid": uid,
                "threads": int(rest[17]), "comm": comm}

    def _relations(self, pid):
        """task, өвөг эцгүүд (эцэг эхэнд), шууд хүүхдүүд — /proc/<pid>/stat-аас."""
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
        if self._snapshot is None:
            self._snapshot = [s for s in (self._stat(int(d)) for d in os.listdir("/proc")
                                          if d.isdigit()) if s]
        children = sorted((s for s in self._snapshot if s["ppid"] == pid), key=lambda n: n["pid"])
        return task, ancestors, children

    def query(self, pid):
        task, ancestors, children = self._relations(pid)
        book = f"command = [{task['comm']}] pid = [{pid}] state = [{task['state_char']}]"
        return {"book_line": book + "   (fallback)", "task": task, "ancestors": ancestors,
                "children": children,
                "summary": {"ancestors": len(ancestors), "children": len(children), "truncated": 0},
                "raw": "(procfs fallback — module ачаалагдаагүй)\n",
                "calls": [{"op": "read", "path": f"/proc/{pid}/stat (fallback)", "data": "",
                           "bytes": 0, "us": 0}]}


class BookBackend(ProcfsBackend):
    """Module зөвхөн номын /proc/pid-тэй (/proc/pid_tree-гүй) үед.

    Task-ийн command, pid, state-ийг module-ээс; эцэг/хүүгийн холбоо, uid, урсгалын тоог
    /proc/<pid>/stat-аас авна. UI-д хаанаас ирснийг тодорхой тэмдэглэнэ.
    """
    name = "kernel module (/proc/pid) + procfs шатлал (/proc/pid_tree алга)"
    mode = "book"

    @staticmethod
    def available():
        return os.path.exists(PROC_PID) and not os.path.exists(PROC_TREE)

    def query(self, pid):
        calls = []
        with _module_lock:
            book_line = _write_read_book(pid, calls)
        if not book_line:
            raise TaskError(404, f"PID {pid} олдсонгүй — module 0 байт буцаалаа (номын шаардлага)")
        book = parse_book_line(book_line)
        if book is None:
            raise TaskError(502, f"/proc/pid-ийн гаралт номын форматтай таарахгүй: '{book_line[:80]}' "
                                 "(хүлээгдэх: command = [..] pid = [..] state = [..]) — "
                                 "python3 src/ui/contract_check.py-оор шалгана уу")
        t = time.perf_counter()
        task, ancestors, children = self._relations(pid)
        task = dict(task, comm=book["comm"], state=book["state"])
        if book["state_char"]:
            task["state_char"] = book["state_char"]
            task["state_name"] = STATE_NAMES.get(book["state_char"], "?")
        calls.append(_call("read", f"/proc/{pid}/stat (шатлал, procfs)",
                           f"ppid={task['ppid']} хүүхэд={len(children)}", 0, t))
        return {"book_line": book_line, "task": task, "ancestors": ancestors,
                "children": children,
                "summary": {"ancestors": len(ancestors), "children": len(children), "truncated": 0},
                "raw": book_line + "\n# /proc/pid_tree алга — эцэг/хүүгийн холбоог /proc/<pid>/stat-аас уншив\n",
                "calls": calls}


def select_backend(fallback_allowed):
    """Хамгийн их өгөгдлийг module-ээс авах backend-ийг сонгоно (байхгүй бол None)."""
    for cls in (ModuleBackend, BookBackend):
        if cls.available():
            return cls
    return ProcfsBackend if fallback_allowed else None


def build_tree(backend, pid, depth, extra=frozenset()):
    """Сонгосон PID-ээс доош depth түвшний мод. Хүү бүрийн хүүхдүүдийг мөн module-ээс асууна.

    extra (?expand=) дахь PID-ийг depth-ээс гүн байсан ч асууж, хүүхдүүдийг нь (навч болгон) харуулна —
    UI-д зангилааг газар дээр нь нэг түвшнээр нээхэд.
    """
    root = backend.query(pid)
    counter = {"nodes": 1, "queries": 1}

    def expand(info, level):
        node = dict(info["task"])
        node["demo"] = Demo.is_member(node["pid"])
        node["truncated"] = bool(info["summary"].get("truncated"))
        node["child_count"] = len(info["children"])
        node["children"] = []
        for child in info["children"]:
            # depth=0: зөвхөн шууд хүүхдүүд (асуухгүй), depth=1: тэдний хүүхдүүд ч гэх мэт
            if (level <= depth or child["pid"] in extra) and counter["nodes"] < MAX_NODES:
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
                leaf["demo"] = Demo.is_member(leaf["pid"])
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

    # --- ажиллаж буй туршилтыг удирдах ---------------------------------
    SIGNALS = {"STOP": signal.SIGSTOP, "CONT": signal.SIGCONT, "TERM": signal.SIGTERM}

    @classmethod
    def _require_running(cls):
        if not cls.root_pid or not cls.proc or cls.proc.poll() is not None:
            raise TaskError(409, "Demo мод ажиллаагүй байна — эхлээд 'Demo мод үүсгэх' дарна уу")

    @classmethod
    def is_member(cls, pid):
        """PID нь demo модны процессын бүлэгт (pgid = demo_root) хамаарах эсэх."""
        if not cls.root_pid:
            return False
        try:
            return os.getpgid(pid) == cls.root_pid
        except OSError:
            return False

    @classmethod
    def signal_root(cls, sig):
        cls._require_running()
        os.kill(cls.root_pid, sig)
        time.sleep(0.25)                                  # кернел төлөвөө шинэчлэх хугацаа
        return cls.root_pid

    @classmethod
    def signal_member(cls, pid, name):
        """Зөвхөн demo процесст signal илгээнэ — системийн бусад процесст хүрэхгүй."""
        cls._require_running()
        if name not in cls.SIGNALS:
            raise TaskError(400, "sig нь STOP, CONT, TERM-ийн аль нэг байна")
        if pid == cls.root_pid:
            raise TaskError(400, "demo_root-ийг 'Demo зогсоох' товчоор зогсооно")
        if not cls.is_member(pid):
            raise TaskError(403, f"PID {pid} нь demo модны процесс биш — signal зөвхөн demo процесст илгээгдэнэ")
        os.kill(pid, cls.SIGNALS[name])
        time.sleep(0.25)


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
        cls = select_backend(self.fallback_allowed)
        if cls:
            return cls()
        raise TaskError(503, "Kernel module ачаалагдаагүй байна (/proc/pid алга). "
                             "Ачаалах: sudo insmod src/kmod/pid.ko — эсвэл --fallback горимоор асаана уу")

    def do_GET(self):
        url = urlparse(self.path)
        q = parse_qs(url.query)
        try:
            if url.path == "/api/status":
                cls = select_backend(self.fallback_allowed)
                self._send(200, {
                    "module_loaded": os.path.exists(PROC_PID),
                    "tree_file": os.path.exists(PROC_TREE),
                    "mode": cls.mode if cls else None,
                    "backend": cls.name if cls else None,
                    "fallback_allowed": self.fallback_allowed,
                    "kernel": platform.release(),
                    "server_pid": os.getpid(),
                    "demo_root": Demo.root_pid,
                })
            elif url.path == "/api/task":
                pid = parse_pid(q.get("pid", [None])[0])
                depth = parse_depth(q.get("depth", [None])[0])
                expand = parse_expand(q.get("expand", [None])[0])
                backend = self._current_backend()
                t0 = time.perf_counter()
                root, tree, counter = build_tree(backend, pid, depth, expand)
                self._send(200, {
                    "backend": backend.name, "mode": backend.mode, "book_line": root["book_line"],
                    "task": root["task"], "ancestors": root["ancestors"], "tree": tree,
                    "summary": root["summary"], "raw": root["raw"], "depth": depth,
                    "expand": sorted(expand),
                    "nodes": counter["nodes"], "queries": counter["queries"],
                    "calls": root["calls"], "demo_root": Demo.root_pid,
                    "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
                })
            elif url.path == "/api/processes":
                self._send(200, list_processes())
            else:
                self._static(url.path)
        except TaskError as e:
            self._error(e)

    def do_POST(self):
        url = urlparse(self.path)
        q = parse_qs(url.query)
        root_signals = {"/api/demo/spawn": signal.SIGUSR1, "/api/demo/zombie": signal.SIGUSR2,
                        "/api/demo/reap": signal.SIGHUP}
        try:
            if url.path == "/api/demo":
                self._send(200, {"root_pid": Demo.start()})
            elif url.path == "/api/demo/stop":
                Demo.stop()
                self._send(200, {"stopped": True})
            elif url.path in root_signals:
                self._send(200, {"root_pid": Demo.signal_root(root_signals[url.path])})
            elif url.path == "/api/demo/signal":
                pid = parse_pid(q.get("pid", [None])[0])
                sig = (q.get("sig", [""])[0]).upper()
                Demo.signal_member(pid, sig)
                self._send(200, {"pid": pid, "sig": sig})
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
    cls = select_backend(args.fallback)
    state = {"module": "loaded (/proc/pid + /proc/pid_tree)",
             "book": "loaded, /proc/pid only → hierarchy from procfs",
             "fallback": "NOT loaded → fallback"}.get(cls.mode if cls else None, "NOT loaded")
    # flush — гаралтыг файл руу чиглүүлсэн үед ч (жнь > server.log) шууд харагдана
    print(f"kernel module (/proc/pid): {state}", flush=True)
    print(f"Task Hierarchy UI: http://localhost:{args.port}   (Ctrl+C — зогсоох)", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        Demo.stop()
        srv.server_close()


if __name__ == "__main__":
    main()
