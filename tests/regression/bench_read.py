#!/usr/bin/env python3
"""/proc/pid-ийн нэг "бичих + унших"-ын хугацааг хэмжинэ (медиан, мкс).

    python3 tests/regression/bench_read.py [PID] [N]

PID 1 (олон хүүхэдтэй) болон өөрийн PID (хүүхэдгүй) дээр нэг fd-ээр хэмжинэ.
v2 module хүүхдийг бүх процессыг гүйж олдог тул процессын тоо (N_proc)-г хамт хэвлэнэ.
"""
import os
import statistics
import sys
import time

N = int(sys.argv[2]) if len(sys.argv) > 2 else 3000


def one(pid):
    t = time.perf_counter_ns()
    fd = os.open("/proc/pid", os.O_RDWR)
    os.write(fd, f"{pid}\n".encode())
    os.lseek(fd, 0, os.SEEK_SET)
    while os.read(fd, 65536):
        pass
    os.close(fd)
    return (time.perf_counter_ns() - t) / 1000


nproc = sum(d.isdigit() for d in os.listdir("/proc"))
for pid in ([int(sys.argv[1])] if len(sys.argv) > 1 else [1, os.getpid()]):
    for _ in range(200):
        one(pid)
    xs = sorted(one(pid) for _ in range(N))
    print(f"N_proc={nproc} pid={pid} median={statistics.median(xs):.1f}us "
          f"p95={xs[int(len(xs) * .95)]:.1f}us n={N}")
