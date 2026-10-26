#!/bin/bash
# Энгийн Ubuntu/Debian (VirtualBox, native) дээр kernel module хөрвүүлэх орчин бэлдэнэ.
#
#   sudo bash src/prereq/setup_ubuntu_headers.sh
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "sudo-гоор ажиллуулна уу: sudo bash $0"; exit 1; }

case "$(uname -r)" in
  *microsoft-standard-WSL2*) echo "WSL2 илэрлээ → sudo bash src/prereq/setup_wsl_kernel.sh"; exit 1 ;;
esac

apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq build-essential "linux-headers-$(uname -r)" python3
ls -d "/lib/modules/$(uname -r)/build" && echo "Бэлэн. Одоо: make -s -C src/prereq test, дараа нь cd src/kmod && make && sudo insmod pid.ko"
