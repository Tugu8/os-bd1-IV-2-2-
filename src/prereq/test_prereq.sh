#!/bin/bash
# 2-р бүлгийн бэлтгэл module-уудыг шалгана:  sudo make -C src/prereq test
# Module бүрийг insmod → /proc-оос унших / dmesg шалгах → rmmod. FAIL байвал exit 1.
cd "$(dirname "$0")"
[ "$(id -u)" -eq 0 ] || { echo "sudo-гоор ажиллуулна уу: sudo make test"; exit 1; }
pass=0; fail=0

check() {  # check "<нэр>" <нөхцөл-команд...>
  local name=$1; shift
  if "$@"; then echo "PASS  $name"; pass=$((pass + 1)); else echo "FAIL  $name"; fail=$((fail + 1)); fi
}

for m in simple hello jiffies seconds; do rmmod "$m" 2>/dev/null; done
dmesg -C 2>/dev/null

insmod simple.ko && rmmod simple
log=$(dmesg | grep "simple:")
check "simple: Loading/Removing мөр dmesg-д"  grep -q "Removing Kernel Module" <<<"$log"
check "simple: gcd(3300, 24) = 12"            grep -q "gcd(3300, 24) = 12" <<<"$log"
check "simple: GOLDEN_RATIO_PRIME хэвлэсэн"   grep -q "GOLDEN_RATIO_PRIME = [0-9]" <<<"$log"

insmod hello.ko
check "hello: cat /proc/hello = Hello World"  test "$(cat /proc/hello)" = "Hello World"
check "hello: 1 байтаар уншихад бүтэн"        test "$(dd if=/proc/hello bs=1 status=none)" = "Hello World"
rmmod hello
check "hello: rmmod → /proc/hello алга"       test ! -e /proc/hello

insmod jiffies.ko
a=$(cat /proc/jiffies); sleep 1; b=$(cat /proc/jiffies)
check "jiffies: тоо, 1 с-д өснө ($a → $b)"    test "$b" -gt "$a"
rmmod jiffies

insmod seconds.ko
s0=$(cat /proc/seconds); sleep 2; s2=$(cat /proc/seconds)
check "seconds: эхэндээ 0 ($s0)"              test "$s0" -eq 0
check "seconds: 2 с-ийн дараа ≥ 2 ($s2)"      test "$s2" -ge 2
rmmod seconds

echo
echo "Нийт: $pass PASS, $fail FAIL"
exit $((fail > 0))
