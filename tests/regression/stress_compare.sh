#!/usr/bin/env bash
# fork/exit ачааллын үед /proc/pid-ийг SECS секунд тасралтгүй уншина.
# Kernel-ийн мэдэгдлийг (dmesg -w) LOG файлд шууд бичнэ (VM унасан ч үлдэнэ).
#
#   sudo bash tests/regression/stress_compare.sh <pid.ko> <LOG> [SECS]
#
# v1.0.1 ба v2 module-ийг ээлжлэн ачаалж ижил ачааллаар харьцуулахад хэрэглэнэ.
set -u
KO=$1
LOG=$2
SECS=${3:-90}
INSMOD=${INSMOD:-insmod}

rmmod pid 2>/dev/null
$INSMOD "$KO" || { echo "insmod failed"; exit 1; }
[ -e /proc/pid ] || { echo "/proc/pid алга"; exit 1; }
echo "module: $KO ($(cat /sys/module/pid/version 2>/dev/null || echo v1))" | tee "$LOG"
dmesg -w >> "$LOG" 2>&1 &
DM=$!
sleep 1

( while :; do /bin/true & /bin/true & /bin/true & wait; done ) &
STORM=$!

n=0
end=$((SECONDS + SECS))
while [ $SECONDS -lt $end ]; do
    echo "$STORM" > /proc/pid
    head -n1 /proc/pid > /dev/null && n=$((n + 1))
    if [ $((n % 1000)) -eq 0 ] && [ $n -gt 0 ]; then echo "reads=$n t=$SECONDS" >> "$LOG"; sync; fi
done
kill "$STORM"
wait "$STORM" 2>/dev/null
echo "survived ${SECS}s, reads=$n" | tee -a "$LOG"
kill "$DM"
rmmod pid
