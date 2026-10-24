#!/usr/bin/env python3
"""
Kernel module ↔ UI интерфейсийн шалгагч — src/kmod-ийн хөгжүүлэгчид зориулав.

    sudo insmod src/kmod/pid.ko
    python3 src/ui/contract_check.py        # ✔ / ⚠ / ✖ хүснэгт; ✖ байвал exit 1

Module нь src/ui/README.md-ийн "Kernel module-тай тохирох интерфейс"-ийг хангаж буйг
жинхэнэ процессуудаар шалгана: энэ скрипт өөрөө, түүний хүү `sleep` (S ба T),
zombie хүү, нэмэлт урсгал. /proc/pid_tree байхгүй бол ⚠ — UI "book" горимоор
(эцэг/хүүгийн холбоог procfs-оос) ажиллана.

Module нэг глобал PID хадгалдаг тул UI сервер зэрэг ажиллаж байвал үр дүн
холилдож болно — серверийг зогсоогоод ажиллуулна уу.
"""
import ctypes
import errno
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import server  # noqa: E402  (parse_book_line, parse_tree_output — UI яг эдгээрээр уншдаг)

PROC_PID, PROC_TREE = server.PROC_PID, server.PROC_TREE
results = []


def check(name, ok, detail="", soft=False):
    """soft=True → тохирохгүй бол ⚠ (UI ажиллана), үгүй бол ✖."""
    results.append(("✔" if ok else ("⚠" if soft else "✖"), name, detail))
    return ok


def write(path, text):
    """Амжилттай бол None, үгүй бол errno-ийн нэр (EINVAL ...)."""
    try:
        with open(path, "w") as f:
            f.write(text)
        return None
    except OSError as e:
        return errno.errorcode.get(e.errno, str(e.errno))


def read(path):
    with open(path) as f:
        return f.read()


def comm_of(pid):
    return Path(f"/proc/{pid}/comm").read_text().rstrip("\n")


def stat_char(pid):
    data = Path(f"/proc/{pid}/stat").read_text()
    return data[data.rindex(")") + 2]


def ppid_of(pid):
    try:
        return int(Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[1])
    except (OSError, IndexError, ValueError):     # процесс энэ хооронд дууссан
        return None


def wait_state(pid, ch, timeout=2.0):
    end = time.time() + timeout
    while time.time() < end:
        if stat_char(pid) == ch:
            return True
        time.sleep(0.02)
    return False


def unused_pid():
    pid_max = int(Path("/proc/sys/kernel/pid_max").read_text())
    return next(p for p in range(pid_max - 1, 1, -1) if not os.path.exists(f"/proc/{p}"))


def small_reads(path, chunk=8):
    """read(fd, buf, 8)-аар хэсэгчлэн уншина. Буфер 4096 байт тул module count-оос их
    хуулсан ч (copy_to_user алдаа) энэ процесс эвдрэхгүй, харин илрүүлнэ."""
    libc = ctypes.CDLL(None, use_errno=True)
    buf = ctypes.create_string_buffer(4096)
    fd = os.open(path, os.O_RDONLY)
    out, over = b"", 0
    try:
        for _ in range(512):
            n = libc.read(fd, buf, chunk)
            if n <= 0:
                break
            over = max(over, n - chunk)
            out += buf.raw[:n]
    finally:
        os.close(fd)
    return out.decode(errors="replace"), over


def check_book():
    me, book_re = os.getpid(), server._BOOK.pattern
    write(PROC_PID, f"{me}\n")
    line = read(PROC_PID)
    b = server.parse_book_line(line)
    check("Номын формат: command = [..] pid = [..] state = [..]", b is not None, line.partition(chr(10))[0] or "(хоосон)")
    if b is None:
        check("UI-ийн regex", False, book_re)
        return
    rest = line.splitlines()[1:]
    if rest:                       # багийн kmod: номын мөрийн дараа parent/child мөрүүд
        _, _, unknown = server.parse_relation_lines(rest)
        check("Нэмэлт мөр бүр parent = [..] ppid = [..] / child = [..] pid = [..] state = [..]",
              not unknown, unknown[0][:60] if unknown else f"{len(rest)} мөр — UI module-ээс хүүхдүүдийг уншина")
    else:
        check("Нэг мөр, '\\n'-ээр төгсөнө", line.count("\n") == 1 and line.endswith("\n"), repr(line[-12:]))
    check("pid = бичсэн PID (namespace: task_pid_vnr)", b["pid"] == me,
          f"{b['pid']} ≠ {me} — global PID хэвлэж байж магадгүй" if b["pid"] != me else str(me))
    check("command = /proc/self/comm", b["comm"] == comm_of(me), f"[{b['comm']}]")
    check("Дахин нээж уншихад ижил мөр (төлөв 'дуусаагүй')", read(PROC_PID) == line)
    if rest:
        kid = subprocess.Popen(["sleep", "30"])
        try:
            wait_state(kid.pid, "S")
            write(PROC_PID, f"{me}\n")
            parent, kids, _ = server.parse_relation_lines(read(PROC_PID).splitlines()[1:])
            check("parent ppid = getppid() (namespace)", bool(parent) and parent["pid"] == os.getppid(),
                  f"{parent and parent['pid']} vs {os.getppid()}")
            check(f"child жагсаалтад хүү sleep ({kid.pid})", any(c["pid"] == kid.pid for c in kids),
                  str([c["pid"] for c in kids]))
        finally:
            kid.kill()
            kid.wait()
        write(PROC_PID, f"{me}\n")
        line = read(PROC_PID)
    text, over = small_reads(PROC_PID)
    check("8 байтаар хэсэгчлэн уншихад бүтэн мөр (count, *pos-ыг хүндэтгэнэ)",
          over == 0 and text == line,
          f"count-оос {over} байт илүү хуулсан (copy_to_user!)" if over else repr(text[:50]))

    write(PROC_PID, "1\n")
    b1 = server.parse_book_line(read(PROC_PID))
    check("PID 1 → init/systemd", bool(b1) and b1["comm"] == comm_of(1), b1 and f"[{b1['comm']}]")

    # state: __state тоо (S → TASK_INTERRUPTIBLE бит 1, T → __TASK_STOPPED бит 4)
    child = subprocess.Popen(["sleep", "30"])
    try:
        wait_state(child.pid, "S")
        write(PROC_PID, f"{child.pid}\n")
        bs = server.parse_book_line(read(PROC_PID)) or {}
        os.kill(child.pid, signal.SIGSTOP)
        wait_state(child.pid, "T")
        write(PROC_PID, f"{child.pid}\n")
        bt = server.parse_book_line(read(PROC_PID)) or {}
        if bs.get("state_char") or bt.get("state_char"):
            check("state нь үсгээр (номд __state тоо)", False,
                  f"S→[{bs.get('state_char')}] T→[{bt.get('state_char')}]", soft=True)
        else:
            # __state нь битийн маск: sleep → TASK_INTERRUPTIBLE (1) | TASK_FREEZABLE (0x2000) = 8193
            check("state: унтаж буй (S) → TASK_INTERRUPTIBLE (1) бит", (bs.get("state", 0) & 1) != 0,
                  str(bs.get("state")))
            check("state: зогсоосон (T) → __TASK_STOPPED (4) бит", (bt.get("state", 0) & 4) != 0,
                  str(bt.get("state")))
    finally:
        child.kill()
        child.wait()

    free = unused_pid()
    write(PROC_PID, f"{free}\n")
    out = read(PROC_PID)
    check(f"Байхгүй PID ({free}) → 0 байт", out == "", repr(out[:50]))

    write(PROC_PID, f"{me}\n")
    for bad in ("abc", "-5", "12abc", "99999999999999999999", " "):
        err = write(PROC_PID, bad + "\n")
        if err:
            check(f"Буруу оролт {bad!r} → write алдаа", True, err)
        else:
            out = read(PROC_PID)
            check(f"Буруу оролт {bad!r} → хүлээн авсан бол 0 байт", out == "",
                  f"write амжилттай, '{out.strip()[:40]}' уншигдлаа")


def check_tree():
    if not os.path.exists(PROC_TREE):
        check("/proc/pid_tree байгаа эсэх", False,
              "алга — UI 'book' горимоор (хүүхдүүд /proc/pid-ийн child мөрөөс эсвэл procfs-оос) ажиллана", soft=True)
        return
    me = os.getpid()
    zpid = os.fork()                       # wait() хийхгүй → Z
    if zpid == 0:
        os._exit(0)
    sleeper = subprocess.Popen(["sleep", "30"])
    stopped = subprocess.Popen(["sleep", "30"])
    gate = threading.Event()
    th = threading.Thread(target=gate.wait, daemon=True)
    th.start()
    try:
        os.kill(stopped.pid, signal.SIGSTOP)
        wait_state(stopped.pid, "T")
        wait_state(sleeper.pid, "S")
        wait_state(zpid, "Z")
        write(PROC_PID, f"{me}\n")
        raw = read(PROC_TREE)
        lines = [ln for ln in raw.splitlines() if ln.strip()]
        bad = [ln for ln in lines if not server._LINE.match(ln)
               or ln.split()[0] not in ("task", "ancestor", "child", "summary")]
        check("Мөр бүр: task|ancestor|child|summary key=value ... comm=", not bad, bad[0][:60] if bad else
              f"{len(lines)} мөр")
        try:
            task, anc, kids, summ = server.parse_tree_output(raw)
        except (KeyError, ValueError) as e:
            check("UI-ийн parse_tree_output() уншина", False, f"{type(e).__name__}: {e}")
            return
        check("UI-ийн parse_tree_output() уншина", task is not None)
        if task is None:
            return
        check("task мөр яг нэг", sum(ln.startswith("task ") for ln in lines) == 1)
        check("task.pid = бичсэн PID", task["pid"] == me, str(task["pid"]))
        check("task.ppid = getppid()", task["ppid"] == os.getppid(), str(task["ppid"]))
        check("task.comm", task["comm"] == comm_of(me), task["comm"])
        check("task.uid = getuid()", task["uid"] == os.getuid(), str(task["uid"]))
        n_threads = len(os.listdir("/proc/self/task"))
        check("task.threads = /proc/self/task (энд 2+)", task["threads"] == n_threads,
              f"{task['threads']} vs {n_threads}")
        check("ancestor[0] = эцэг", bool(anc) and anc[0]["pid"] == os.getppid())
        check("ancestor сүүлийнх = PID 1", bool(anc) and anc[-1]["pid"] == 1,
              " → ".join(str(a["pid"]) for a in anc))
        check("ancestor гинж тасралтгүй (ppid → дараагийн pid)",
              all(a["ppid"] == b["pid"] for a, b in zip(anc, anc[1:])))
        want = {sleeper.pid: "S", stopped.pid: "T", zpid: "Z"}
        got = {c["pid"]: c["state_char"] for c in kids}
        for pid, ch in want.items():
            check(f"child {pid} state_char = {ch}", got.get(pid) == ch, str(got.get(pid)))
        procfs = {int(d) for d in os.listdir("/proc") if d.isdigit() and ppid_of(int(d)) == me}
        check("child жагсаалт = procfs-ийн хүүхдүүд", set(got) == procfs,
              f"{sorted(got)} vs {sorted(procfs)}")
        check("summary тоо таарна", summ.get("ancestors") == len(anc) and
              (summ.get("children") == len(kids) or summ.get("truncated")), str(summ))
        text, over = small_reads(PROC_TREE)
        check("pid_tree-г 8 байтаар уншихад бүтэн", over == 0 and text == raw,
              f"count-оос {over} байт илүү" if over else f"{len(text)}/{len(raw)} байт")

        free = unused_pid()
        write(PROC_PID, f"{free}\n")
        out = read(PROC_TREE)
        check(f"Байхгүй PID ({free}) → pid_tree 0 байт", out == "", repr(out[:50]))
        err = write(PROC_TREE, "1\n")
        t1 = server.parse_tree_output(read(PROC_TREE))[0] if not err else None
        check("/proc/pid_tree руу бичиж PID тохируулах (сонголттой)", bool(t1) and t1["pid"] == 1,
              err or "", soft=True)
    finally:
        gate.set()
        for c in (sleeper, stopped):
            c.kill()
            c.wait()
        os.waitpid(zpid, 0)


def main():
    if not os.path.exists(PROC_PID):
        print("✖ /proc/pid алга — module ачаалагдаагүй (sudo insmod src/kmod/pid.ko)")
        return 2
    check_book()
    check_tree()
    w = max(len(n) for _, n, _ in results)
    for mark, name, detail in results:
        print(f"{mark} {name.ljust(w)}  {detail or ''}")
    n = {m: sum(r[0] == m for r in results) for m in "✔⚠✖"}
    print(f"\n{n['✔']} ✔   {n['⚠']} ⚠   {n['✖']} ✖   — "
          + ("UI-тай бүрэн нийцнэ" if not n["✖"] and not n["⚠"] else
             "UI ажиллана (⚠-г харна уу)" if not n["✖"] else "✖-г засна уу (src/ui/README.md)"))
    mode = server.select_backend(False)
    print(f"UI-ийн сонгох горим: {mode.mode if mode else '—'}")
    return 1 if n["✖"] else 0


if __name__ == "__main__":
    sys.exit(main())
