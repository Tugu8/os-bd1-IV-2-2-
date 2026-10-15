#!/usr/bin/env python3
"""
UI серверийн API тест (Python unittest, нэмэлт сан шаардлагагүй).

    python3 -m unittest -v src/ui/tests/test_api.py

Module ачаалагдсан бол жинхэнэ module-ээр, үгүй бол --fallback горимоор шалгана
(module-ийн номын форматын тест зөвхөн module ачаалагдсан үед).
"""
import json
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import server  # noqa: E402

MODULE = server.ModuleBackend.available()


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
        self.assertEqual(b["module_loaded"], MODULE)
        self.assertEqual(b["demo_root"], self.root)

    def test_02_pid1(self):
        s, b = call(self.base, "/api/task?pid=1&depth=0")
        self.assertEqual(s, 200)
        self.assertEqual(b["task"]["pid"], 1)
        self.assertEqual(b["ancestors"], [])
        if MODULE:
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


if __name__ == "__main__":
    print("backend:", "kernel module" if MODULE else "procfs fallback")
    unittest.main(verbosity=2)
