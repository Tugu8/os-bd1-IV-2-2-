#!/usr/bin/env python3
"""
Туршилтын процессын мод үүсгэнэ — Task hierarchy UI болон тестэд мэдэгдэж буй бүтэц өгнө.

    python3 src/ui/demo_tree.py            # эхний мөрөнд root PID хэвлээд Ctrl+C хүртэл ажиллана

Бүтэц (comm нэр — төлөв):
    demo_root                 S   (энэ скрипт)
    ├── demo_sleeper          S
    │   ├── demo_leaf_1       S
    │   └── demo_leaf_2       S
    ├── demo_busy             R/S (0.3 с CPU ачаалал, 0.7 с унтана — төлөв ээлжилнэ)
    ├── demo_stopped          T   (SIGSTOP)
    ├── demo_threads          S   (threads=5: үндсэн + 4 урсгал)
    └── demo_zombie           Z   (шууд дуусна, эцэг нь wait() хийхгүй)

Бүх процесс нэг процессын бүлэгт байх тул root-д SIGTERM/SIGINT ирэхэд бүгдийг устгана.
"""
import os
import signal
import sys
import threading
import time


def set_comm(name):
    """Процессын нэрийг (task->comm) өөрчилнө — /proc/self/comm руу бичих нь prctl(PR_SET_NAME)-тэй адил."""
    with open("/proc/self/comm", "w") as f:
        f.write(name[:15])


def child(name, body):
    pid = os.fork()
    if pid == 0:
        try:
            set_comm(name)
            body()
        finally:
            os._exit(0)
    return pid


def sleep_forever():
    while True:
        time.sleep(3600)


def sleeper():
    child("demo_leaf_1", sleep_forever)
    child("demo_leaf_2", sleep_forever)
    sleep_forever()


def busy():
    while True:
        end = time.time() + 0.3
        while time.time() < end:
            pass
        time.sleep(0.7)


def threads():
    for _ in range(4):
        threading.Thread(target=sleep_forever, daemon=True).start()
    sleep_forever()


def main():
    try:
        os.setpgrp()                          # шинэ процессын бүлэг — нэг дор устгахад
    except OSError:
        pass                                  # server.py аль хэдийн шинэ session-д эхлүүлсэн
    set_comm("demo_root")

    child("demo_sleeper", sleeper)
    child("demo_busy", busy)
    stopped = child("demo_stopped", sleep_forever)
    child("demo_threads", threads)
    child("demo_zombie", lambda: None)        # шууд дуусна → wait() хийхгүй тул zombie

    time.sleep(0.2)
    os.kill(stopped, signal.SIGSTOP)

    print(os.getpid(), flush=True)            # эхний мөр: root PID (server.py уншина)
    print("demo tree ready — Ctrl+C to stop", file=sys.stderr, flush=True)

    def cleanup(*_):
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        os.killpg(0, signal.SIGCONT)          # зогсоосон процессыг сэрээж байж устгана
        os.killpg(0, signal.SIGTERM)
        os._exit(0)

    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)
    sleep_forever()


if __name__ == "__main__":
    main()
