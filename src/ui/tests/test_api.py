#!/usr/bin/env python3
"""
UI серверийн API тест (Python unittest, нэмэлт сан шаардлагагүй).

    python3 -m unittest -v src/ui/tests/test_api.py

Module ачаалагдсан бол жинхэнэ module-ээр, үгүй бол --fallback горимоор шалгана
(module-ийн номын форматын тест зөвхөн module ачаалагдсан үед). ModeTest нь
/proc/pid, /proc/pid_tree замыг түр сольж module / book / fallback горим бүрийг шалгана.
"""
import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import server  # noqa: E402

MODE = server.select_backend(True).mode      # module | book | fallback
MODULE = MODE == "module"


def call(base, path, method="GET"):
    req = urllib.request.Request(base + path, method=method, data=b"" if method == "POST" else None)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


class ApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        server.Handler.quiet = True
        cls.srv = server.make_server("127.0.0.1", 0, fallback=not MODULE)
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        status, body = call(cls.base, "/api/demo", "POST")
        assert status == 200, body
        cls.root = body["root_pid"]
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        call(cls.base, "/api/demo/stop", "POST")
        cls.srv.shutdown()
        cls.srv.server_close()

    def test_01_status(self):
        s, b = call(self.base, "/api/status")
        self.assertEqual(s, 200)
        self.assertEqual(b["mode"], MODE)
        self.assertEqual(b["module_loaded"], MODE != "fallback")
        self.assertEqual(b["demo_root"], self.root)

    def test_02_pid1(self):
        s, b = call(self.base, "/api/task?pid=1&depth=0")
        self.assertEqual(s, 200)
        self.assertEqual(b["task"]["pid"], 1)
        self.assertEqual(b["ancestors"], [])
        if MODE != "fallback":
            self.assertRegex(b["book_line"], r"^command = \[.+\] pid = \[1\] state = \[\d+\]$")

    def test_03_demo_tree_structure(self):
        s, b = call(self.base, f"/api/task?pid={self.root}&depth=2")
        self.assertEqual(s, 200)
        kids = {c["comm"]: c for c in b["tree"]["children"]}
        self.assertEqual(set(kids), {"demo_sleeper", "demo_busy", "demo_stopped", "demo_threads", "demo_zombie"})
        self.assertEqual(kids["demo_zombie"]["state_char"], "Z")
        self.assertEqual(kids["demo_stopped"]["state_char"], "T")
        self.assertEqual(kids["demo_threads"]["threads"], 5)
        leaves = {c["comm"] for c in kids["demo_sleeper"]["children"]}
        self.assertEqual(leaves, {"demo_leaf_1", "demo_leaf_2"})
        self.assertEqual(b["ancestors"][-1]["pid"], 1)

    def test_04_depth_zero_unexpanded(self):
        s, b = call(self.base, f"/api/task?pid={self.root}&depth=0")
        self.assertEqual(s, 200)
        self.assertTrue(all(c.get("unexpanded") for c in b["tree"]["children"]))
        self.assertEqual(b["queries"], 1)

    def test_05_invalid_input(self):
        for bad in ["abc", "-5", "1.5", "", "99999999"]:
            with self.subTest(pid=bad):
                s, b = call(self.base, f"/api/task?pid={urllib.request.quote(bad)}")
                self.assertEqual(s, 400, b)
                self.assertIn("error", b)

    def test_06_not_found(self):
        s, b = call(self.base, "/api/task?pid=4000000")
        self.assertEqual(s, 404)

    def test_07_bad_depth(self):
        s, _ = call(self.base, "/api/task?pid=1&depth=99")
        self.assertEqual(s, 400)

    def test_08_processes(self):
        s, b = call(self.base, "/api/processes")
        self.assertEqual(s, 200)
        pids = {p["pid"] for p in b}
        self.assertIn(1, pids)
        self.assertIn(self.root, pids)

    def test_09_static_and_traversal(self):
        with urllib.request.urlopen(self.base + "/", timeout=5) as r:
            self.assertIn(b"Task Hierarchy", r.read())
        s, _ = call(self.base, "/static/../server.py")
        self.assertEqual(s, 404)

    def test_10_parallel_requests_consistent(self):
        """Module нэг глобал PID хадгалдаг — серверийн mutex зэрэг хүсэлтэд зөв хариу баталгаажуулна."""
        results = {}

        def worker(pid):
            ok = 0
            for _ in range(15):
                s, b = call(self.base, f"/api/task?pid={pid}&depth=0")
                ok += s == 200 and b["task"]["pid"] == pid
            results[pid] = ok

        ts = [threading.Thread(target=worker, args=(p,)) for p in (1, self.root)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(results, {1: 15, self.root: 15})

    # ---- шинэ боломжууд: гүн, лог, туршилт удирдах ----------------------
    # (11-ээс хойшх тест demo модыг өөрчилдөг тул бүтцийн тестүүдийн дараа ажиллана)

    def children(self, depth=0):
        s, b = call(self.base, f"/api/task?pid={self.root}&depth={depth}")
        self.assertEqual(s, 200, b)
        return {c["comm"]: c for c in b["tree"]["children"]}, b

    def test_11_depth_levels(self):
        kids, _ = self.children(depth=1)
        sleeper = kids["demo_sleeper"]
        self.assertFalse(sleeper.get("unexpanded"))               # depth=1 → хүүхдүүд асуугдсан
        self.assertTrue(all(c.get("unexpanded") for c in sleeper["children"]))  # ач нар — навч

    def test_12_calls_log(self):
        _, b = self.children()
        if MODULE:
            self.assertEqual([(c["op"], c["path"]) for c in b["calls"]],
                             [("write", "/proc/pid"), ("read", "/proc/pid"), ("read", "/proc/pid_tree")])
            self.assertEqual(b["calls"][0]["data"], f"{self.root}\\n")
        elif MODE == "book":
            self.assertEqual([(c["op"], c["path"]) for c in b["calls"]][:2],
                             [("write", "/proc/pid"), ("read", "/proc/pid")])
            self.assertEqual(len(b["calls"]), 3)                   # + procfs-оос шатлал
        else:
            self.assertEqual(len(b["calls"]), 1)

    def test_13_demo_flags(self):
        kids, b = self.children()
        self.assertTrue(b["tree"]["demo"])
        self.assertTrue(all(c["demo"] for c in kids.values()))
        _, pid1 = call(self.base, "/api/task?pid=1&depth=0")
        self.assertFalse(pid1["tree"]["demo"])

    def test_14_spawn_and_zombie(self):
        before, _ = self.children()
        self.assertEqual(call(self.base, "/api/demo/spawn", "POST")[0], 200)
        self.assertEqual(call(self.base, "/api/demo/zombie", "POST")[0], 200)
        after, _ = self.children()
        new = set(after) - set(before)
        self.assertTrue(any(n.startswith("demo_new_") for n in new), new)
        zomb = [after[n] for n in new if n.startswith("demo_zomb_")]
        self.assertEqual(len(zomb), 1)
        self.assertEqual(zomb[0]["state_char"], "Z")

    def test_15_signal_lifecycle(self):
        call(self.base, "/api/demo/spawn", "POST")
        kids, _ = self.children()
        pid = max(c["pid"] for n, c in kids.items() if n.startswith("demo_new_"))

        def state_of(p):
            return {c["pid"]: c["state_char"] for c in self.children()[0].values()}.get(p)

        self.assertEqual(call(self.base, f"/api/demo/signal?pid={pid}&sig=STOP", "POST")[0], 200)
        self.assertEqual(state_of(pid), "T")
        self.assertEqual(call(self.base, f"/api/demo/signal?pid={pid}&sig=CONT", "POST")[0], 200)
        self.assertIn(state_of(pid), ("S", "R"))
        self.assertEqual(call(self.base, f"/api/demo/signal?pid={pid}&sig=TERM", "POST")[0], 200)
        self.assertEqual(state_of(pid), "Z")                       # эцэг wait() хийгээгүй → zombie
        self.assertEqual(call(self.base, "/api/demo/reap", "POST")[0], 200)
        self.assertIsNone(state_of(pid))                           # wait() → zombie арилсан
        zombies = [c for c in self.children()[0].values() if c["state_char"] == "Z"]
        self.assertEqual(zombies, [])

    def test_16_signal_security(self):
        s, b = call(self.base, "/api/demo/signal?pid=1&sig=TERM", "POST")
        self.assertEqual(s, 403, b)                                # demo биш процесс
        s, _ = call(self.base, f"/api/demo/signal?pid={self.root}&sig=STOP", "POST")
        self.assertEqual(s, 400)                                   # demo_root
        kids, _ = self.children()
        s, _ = call(self.base, f"/api/demo/signal?pid={kids['demo_sleeper']['pid']}&sig=KILL", "POST")
        self.assertEqual(s, 400)                                   # зөвшөөрөгдөөгүй signal
        s, _ = call(self.base, "/api/demo/signal?pid=abc&sig=STOP", "POST")
        self.assertEqual(s, 400)

    def test_23_expand_in_place(self):
        """expand=PID: depth=0 байхад ч тэр зангилааг нэг түвшнээр нээнэ, бусад нь навч хэвээр."""
        kids, _ = self.children(depth=0)
        sleeper = kids["demo_sleeper"]["pid"]
        s, b = call(self.base, f"/api/task?pid={self.root}&depth=0&expand={sleeper}")
        self.assertEqual(s, 200, b)
        self.assertEqual(b["expand"], [sleeper])
        self.assertEqual(b["queries"], 2)                          # root + sleeper
        opened = {c["comm"]: c for c in b["tree"]["children"]}
        self.assertFalse(opened["demo_sleeper"].get("unexpanded"))
        leaves = opened["demo_sleeper"]["children"]
        self.assertEqual({c["comm"] for c in leaves}, {"demo_leaf_1", "demo_leaf_2"})
        self.assertTrue(all(c.get("unexpanded") for c in leaves))  # нэг л түвшин
        self.assertTrue(opened["demo_busy"].get("unexpanded"))
        s, b = call(self.base, f"/api/task?pid={self.root}&depth=0&expand=999999,{sleeper}")
        self.assertEqual((s, b["queries"]), (200, 2))              # модонд байхгүй PID — үл тооно

    def test_24_expand_invalid(self):
        for bad in ["abc", "1,,2", "-3", ",".join(["1"] * 65)]:
            with self.subTest(expand=bad[:20]):
                s, b = call(self.base, f"/api/task?pid=1&depth=0&expand={bad}")
                self.assertEqual(s, 400, b)
                self.assertIn("expand", b["error"])


class ParserTest(unittest.TestCase):
    """Module-ийн гаралтыг задлах цэвэр функцууд (сервер шаардлагагүй)."""

    def test_17_book_line(self):
        p = server.parse_book_line
        self.assertEqual(p("command = [bash] pid = [1395] state = [1]\n"),
                         {"comm": "bash", "pid": 1395, "state": 1, "state_char": None})
        self.assertEqual(p("command=[kworker/0:1 x] pid=[7]  state=[8193]")["state"], 8193)
        self.assertEqual(p("command = [a] b] pid = [2] state = [S]"),      # state үсгээр, comm-д ']'
                         {"comm": "a] b", "pid": 2, "state": -1, "state_char": "S"})
        for bad in ("", "1395", "command = [bash] pid = [x] state = [1]", "pid = [1] state = [1]"):
            with self.subTest(line=bad):
                self.assertIsNone(p(bad))

    def test_18a_team_format(self):
        """Багийн src/kmod/pid.c: номын мөр + parent/child мөрүүд."""
        out = ("command = [bash] pid = [1395] state = [1]\n"
               "parent = [Relay(294)] ppid = [1300]\n"
               "child = [vim x] pid = [1400] state = [1]\n"
               "child = [cat] pid = [1401] state = [0]\n")
        self.assertEqual(server.parse_book_line(out)["pid"], 1395)          # эхний мөр
        parent, kids, unknown = server.parse_relation_lines(out.splitlines()[1:])
        self.assertEqual(parent, {"comm": "Relay(294)", "pid": 1300})
        self.assertEqual([(c["comm"], c["pid"], c["state"]) for c in kids],
                         [("vim x", 1400, 1), ("cat", 1401, 0)])
        self.assertEqual(unknown, [])
        self.assertEqual(server.parse_relation_lines(["sibling = [x]"])[2], ["sibling = [x]"])

    def test_18_tree_comm_with_spaces(self):
        raw = ("task pid=5 tgid=5 ppid=1 state=1 state_char=S uid=0 threads=1 comm=Web Content\n"
               "ancestor pid=1 tgid=1 ppid=0 state=1 state_char=S uid=0 threads=1 comm=init\n"
               "child pid=6 tgid=6 ppid=5 state=0 state_char=R uid=0 threads=1 comm=a=b|c d\n"
               "summary ancestors=1 children=1 truncated=0\n")
        task, anc, kids, summ = server.parse_tree_output(raw)
        self.assertEqual(task["comm"], "Web Content")
        self.assertEqual((kids[0]["comm"], kids[0]["state_name"]), ("a=b|c d", "running"))
        self.assertEqual([a["pid"] for a in anc], [1])
        self.assertEqual(summ, {"ancestors": 1, "children": 1, "truncated": 0})


class ModeTest(unittest.TestCase):
    """Backend-ийн горимууд: PROC_PID / PROC_TREE замыг түр сольж сервер асаана."""
    NOWHERE = "/proc/nonexistent_iv_2_2"

    def serve(self, proc_pid, proc_tree, fallback=False):
        saved = server.PROC_PID, server.PROC_TREE
        server.PROC_PID, server.PROC_TREE = proc_pid, proc_tree

        def restore():
            server.PROC_PID, server.PROC_TREE = saved
        self.addCleanup(restore)
        srv = server.make_server("127.0.0.1", 0, fallback=fallback)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        return f"http://127.0.0.1:{srv.server_address[1]}"

    def test_19_fallback_mode(self):
        base = self.serve(self.NOWHERE, self.NOWHERE, fallback=True)
        b = call(base, "/api/status")[1]
        self.assertEqual((b["mode"], b["module_loaded"]), ("fallback", False))
        s, b = call(base, "/api/task?pid=1&depth=0")
        self.assertEqual((s, b["mode"]), (200, "fallback"))
        self.assertTrue(b["book_line"].endswith("(fallback)"))

    def test_20_no_module_503(self):
        base = self.serve(self.NOWHERE, self.NOWHERE)
        self.assertIsNone(call(base, "/api/status")[1]["mode"])
        self.assertEqual(call(base, "/api/task?pid=1")[0], 503)

    def test_21_book_format_mismatch_502(self):
        """/proc/pid номын формат биш мөр буцаавал UI буруу дүрслэхгүй — 502 + шалгагчийн заавар."""
        with tempfile.TemporaryDirectory() as d:
            fake = Path(d) / "pid"                 # энгийн файл: бичсэн "1\n"-ээ буцааж уншина
            fake.touch()
            base = self.serve(str(fake), self.NOWHERE)
            self.assertEqual(call(base, "/api/status")[1]["mode"], "book")
            s, b = call(base, "/api/task?pid=1")
            self.assertEqual(s, 502, b)
            self.assertIn("contract_check", b["error"])

    @unittest.skipUnless(MODULE, "/proc/pid + /proc/pid_tree-тэй module шаардлагатай")
    def test_22_book_mode_matches_module(self):
        """/proc/pid_tree-гүй module-ийг дуурайна: task нь module-ээс, шатлал procfs-оос — module-тэй ижил."""
        m1 = server.ModuleBackend().query(1)
        me = server.ModuleBackend().query(os.getpid())
        base = self.serve(server.PROC_PID, self.NOWHERE)
        s, b = call(base, "/api/task?pid=1&depth=0")
        self.assertEqual((s, b["mode"]), (200, "book"), b)
        self.assertEqual(b["book_line"], m1["book_line"])
        for k in ("pid", "tgid", "ppid", "uid", "comm", "state", "state_char", "threads"):
            self.assertEqual(b["task"][k], m1["task"][k], k)
        self.assertEqual({c["pid"] for c in b["tree"]["children"]}, {c["pid"] for c in m1["children"]})
        self.assertEqual([c["path"] for c in b["calls"]][:2], ["/proc/pid", "/proc/pid"])
        s, b = call(base, f"/api/task?pid={os.getpid()}&depth=0")
        self.assertEqual([a["pid"] for a in b["ancestors"]], [a["pid"] for a in me["ancestors"]])


if __name__ == "__main__":
    print("backend:", MODE)
    unittest.main(verbosity=2)
