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

Туршилтыг ажиллаж байхад нь удирдах signal-ууд (UI-ийн товчнууд эдгээрийг илгээнэ):
    kill -USR1 <root>   шинэ хүү процесс demo_new_N (S) үүсгэнэ
    kill -USR2 <root>   шинэ хүү demo_zomb_N үүсгэнэ — шууд дуусч zombie (Z) болно
    kill -HUP  <root>   root wait() хийж zombie хүүхдүүдээ цэвэрлэнэ (reap)
    kill -STOP/-CONT/-TERM <хүү>   хүү процессыг зогсоох / сэргээх / дуусгах
                                   (дуусгасан хүү root wait() хийх хүртэл zombie болно)
"""
import itertools
import os
import signal
import sys
import threading
import time

CONTROL_SIGNALS = (signal.SIGTERM, signal.SIGINT, signal.SIGUSR1, signal.SIGUSR2, signal.SIGHUP)


def set_comm(name):
    """Процессын нэрийг (task->comm) өөрчилнө — /proc/self/comm руу бичих нь prctl(PR_SET_NAME)-тэй адил."""
    with open("/proc/self/comm", "w") as f:
        f.write(name[:15])


def child(name, body):
    pid = os.fork()
    if pid == 0:
        try:
            # fork() нь signal handler-уудыг өвлүүлдэг — хүүд root-ийн cleanup
            # (бүх бүлгийг устгах) үлдвэл аюултай тул анхдагч руу буцаана
            for sig in CONTROL_SIGNALS:
                signal.signal(sig, signal.SIG_DFL)
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

    counter = itertools.count(1)

    def cleanup(*_):
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        os.killpg(0, signal.SIGCONT)          # зогсоосон процессыг сэрээж байж устгана
        os.killpg(0, signal.SIGTERM)
        os._exit(0)

    def spawn(*_):                            # SIGUSR1 → шинэ унтаж буй хүү
        child(f"demo_new_{next(counter)}", sleep_forever)

    def spawn_zombie(*_):                     # SIGUSR2 → шууд дуусах хүү → zombie
        child(f"demo_zomb_{next(counter)}", lambda: None)

    def reap(*_):                             # SIGHUP → wait() — zombie-уудыг цэвэрлэнэ
        while True:
            try:
                pid, _ = os.waitpid(-1, os.WNOHANG)
            except ChildProcessError:
                break
            if pid == 0:
                break

    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGUSR1, spawn)
    signal.signal(signal.SIGUSR2, spawn_zombie)
    signal.signal(signal.SIGHUP, reap)

    # Эцэг (server.py эсвэл shell) дуусвал бид өнчин болж init үрчилнэ — тэр үед
    # бүх demo модыг цэвэрлэнэ (сервер kill хийгдсэн ч demo процессууд үлдэхгүй).
    # PR_SET_PDEATHSIG ашиглахгүй: сервер хүсэлт бүрийг тусдаа урсгалд ажиллуулдаг
    # тул тэр урсгал дуусахад л signal ирчихнэ.
    parent = os.getppid()
    while True:
        time.sleep(1)
        if os.getppid() != parent:
            cleanup()


if __name__ == "__main__":
    main()
