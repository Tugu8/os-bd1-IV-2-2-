#!/usr/bin/env bash
# БД2-ын бүх тестийг нэг дор ажиллуулж, үр дүнг tests/bd2_<нэр>/ хавтсанд хадгална.
#
#   bash tests/run_bd2.sh baremetal          # Ubuntu bare-metal дээр
#   INSMOD="insmod -f" bash tests/run_bd2.sh wsl   # WSL2: өөрөө хөрвүүлсэн kernel-ийн CRC зөрвөл (kernel F taint)
#
# Хийх зүйл: v1.0.1 (засвараас өмнөх) module-ийг хөрвүүлж regression тестийг ажиллуулна,
# дараа нь v2 module-оор бүх тестийг (basic, boundary, regression, UI API, contract) ажиллуулна.
# sudo нууц үг асууж болно (insmod, rmmod, dmesg).
set -u
cd "$(dirname "$0")/.."
NAME=${1:-baremetal}
shift || true
MAKEARGS=("$@")
INSMOD=${INSMOD:-insmod}
OUT="tests/bd2_$NAME"
mkdir -p "$OUT"

log() { echo; echo "##### $*"; }

unload() { sudo rmmod pid 2>/dev/null || true; }

{
  echo "date: $(date -Is)"
  echo "kernel: $(uname -r)"
  grep PRETTY_NAME /etc/os-release
  echo "cpu: $(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2)"
  echo "gcc: $(gcc --version | head -n1)"
  echo "python: $(python3 --version)"
  echo "git: $(git rev-parse --short HEAD) $(git describe --tags --always 2>/dev/null)"
  if command -v mokutil >/dev/null; then mokutil --sb-state 2>/dev/null; fi
} > "$OUT/env.txt"
cat "$OUT/env.txt"

# --- 1. Засвараас өмнөх v1.0.1 module ----------------------------------------
log "v1.0.1 module (before)"
OLD=$(mktemp -d)
git show v1.0.1:src/kmod/pid.c > "$OLD/pid.c"
cp src/kmod/Makefile "$OLD/"
( cd "$OLD" && make "${MAKEARGS[@]}" >/dev/null ) || { echo "v1 build failed"; exit 1; }
unload
sudo $INSMOD "$OLD/pid.ko"
bash tests/regression/test_regression.sh 2>&1 | tee "$OUT/regression_before_v1.txt"
unload
rm -rf "$OLD"

# --- 2. v2 module -----------------------------------------------------------
log "v2 module (after)"
( cd src/kmod && make clean >/dev/null && make "${MAKEARGS[@]}" 2>&1 ) | tee "$OUT/build_v2.txt"
sudo $INSMOD src/kmod/pid.ko || exit 1
echo "insmod: $INSMOD" >> "$OUT/env.txt"
modinfo src/kmod/pid.ko | grep -E "^(version|vermagic)" | tee -a "$OUT/build_v2.txt"

log "basic";      bash tests/basic/test_basic.sh            2>&1 | tee "$OUT/basic.txt"
log "boundary";   bash tests/boundary/test_boundary.sh      2>&1 | tee "$OUT/boundary.txt"
log "regression"; bash tests/regression/test_regression.sh  2>&1 | tee "$OUT/regression_after_v2.txt"
log "UI API";     python3 -m unittest -v src/ui/tests/test_api.py 2>&1 | tee "$OUT/ui_api.txt"
log "contract";   python3 src/ui/contract_check.py          2>&1 | tee "$OUT/contract.txt"
if command -v node >/dev/null; then
  log "UI tree (node)"; node src/ui/tests/test_tree.mjs 2>&1 | tee "$OUT/ui_tree.txt"
fi
log "dmesg (pid module)"
sudo dmesg | grep -E "/proc/pid|BUG|WARNING|Oops" | tail -n 20 | tee "$OUT/dmesg.txt"

echo
echo "Үр дүн: $OUT/"
grep -h -E "^Нийт|PASS=|^Ran |^OK|^FAILED|^OK [0-9]" "$OUT"/*.txt
echo "UI-г туршихдаа: python3 src/ui/server.py  (module ачаалагдсан хэвээр). Дуусгах: sudo rmmod pid"
