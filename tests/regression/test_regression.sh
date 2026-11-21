#!/usr/bin/env bash
# БД2 regression тест: v2 module-ийн засваруудыг шалгана.
#
#   sudo insmod src/kmod/pid.ko
#   bash tests/regression/test_regression.sh
#
# R1  номын формат хэвээр (echo/cat)
# R2  module-ийн хувилбар 2.0
# R3  нэг fd-ээр бичиж уншихад олон процесс зэрэг ажилласан ч хариу холилдохгүй
# R4  олон урсгалтай процесс: үндсэн бус урсгалын fork хийсэн хүүхэд жагсаалтад гарна
# R5  хүүхдийн ppid = эцгийн TGID (/proc/<pid>/stat-тай ижил)
# R6  fork/exit ачааллын үед 3000 удаа уншихад кернелийн BUG/WARNING гарахгүй
set -u
cd "$(dirname "$0")"

PASS=0
FAIL=0
ok()   { echo "[PASS] $1"; PASS=$((PASS + 1)); }
bad()  { echo "[FAIL] $1"; FAIL=$((FAIL + 1)); }
check() { if [ "$1" -eq 0 ]; then ok "$2"; else bad "$2"; fi; }

if [ ! -e /proc/pid ]; then
    echo "[ERROR] /proc/pid алга. Эхлээд: sudo insmod src/kmod/pid.ko"
    exit 1
fi
make -s >/dev/null || { echo "[ERROR] тестийн C программ хөрвүүлэгдсэнгүй"; exit 1; }

DMESG_OK=0
if dmesg >/dev/null 2>&1; then DMESG="dmesg"; DMESG_OK=1
elif sudo -n dmesg >/dev/null 2>&1; then DMESG="sudo -n dmesg"; DMESG_OK=1
fi
[ $DMESG_OK -eq 1 ] && BEFORE=$($DMESG | wc -l)

echo "=== R1 номын формат ==="
echo $$ > /proc/pid
first=$(head -n1 /proc/pid)
echo "$first"
[[ "$first" =~ ^command\ =\ \[.*\]\ pid\ =\ \[$$\]\ state\ =\ \[[0-9]+\]$ ]]
check $? "R1 echo/cat номын формат, pid = [$$]"

echo "=== R2 хувилбар ==="
ver=$(cat /sys/module/pid/version 2>/dev/null || echo "?")
echo "module version: $ver"
[ "$ver" = "2.0" ]; check $? "R2 /sys/module/pid/version = 2.0"

echo "=== R3 зэрэг хандалт (4 процесс x 5000) ==="
./fd_isolation 4 5000 | tee /tmp/iv22_fd.txt
check "${PIPESTATUS[0]}" "R3 нэг fd-ээр: mismatch 0"

echo "=== R4/R5 олон урсгалтай процесс ==="
coproc MT { ./mt_fork; }
read -r TGID TID CHILD <&"${MT[0]}"
echo "tgid=$TGID thread_tid=$TID child=$CHILD"
echo "$TGID" > /proc/pid
cat /proc/pid
grep -q "^child = \[.*\] pid = \[$CHILD\]" /proc/pid
check $? "R4 урсгалын fork хийсэн хүүхэд ($CHILD) эцгийн жагсаалтад гарсан"
echo "$CHILD" > /proc/pid
mod_ppid=$(sed -n 's/^parent = \[.*\] ppid = \[\([0-9]*\)\]$/\1/p' /proc/pid)
stat_ppid=$(awk '{print $4}' "/proc/$CHILD/stat")
echo "module ppid=$mod_ppid  /proc/$CHILD/stat ppid=$stat_ppid  (thread tid=$TID)"
[ "$mod_ppid" = "$TGID" ] && [ "$mod_ppid" = "$stat_ppid" ]
check $? "R5 хүүхдийн ppid = TGID ($TGID), /proc/stat-тай ижил"
eval "exec ${MT[1]}>&-"
wait "$MT_PID" 2>/dev/null

echo "=== R6 fork/exit ачаалал ==="
( while :; do /bin/true & /bin/true & /bin/true & wait; done ) &
STORM=$!
okreads=0
for i in $(seq 1 3000); do
    echo "$STORM" > /proc/pid
    head -n1 /proc/pid | grep -q "^command = " && okreads=$((okreads + 1))
done
kill "$STORM" 2>/dev/null; wait "$STORM" 2>/dev/null
echo "амжилттай уншилт: $okreads / 3000"
if [ $DMESG_OK -eq 1 ]; then
    new=$($DMESG | tail -n +"$((BEFORE + 1))" | grep -E "BUG|WARNING|Oops|RCU|general protection" || true)
    [ -n "$new" ] && echo "$new"
    [ "$okreads" -eq 3000 ] && [ -z "$new" ]
    check $? "R6 3000 уншилт, dmesg-д BUG/WARNING алга"
else
    [ "$okreads" -eq 3000 ]
    check $? "R6 3000 уншилт (dmesg уншиж чадсангүй: sudo-гоор ажиллуулбал шалгана)"
fi

echo
echo "Нийт: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
