#!/bin/bash
# WSL2 дээр kernel module хөрвүүлэх build орчныг бэлдэнэ (нэг удаа, ~20–30 минут, ~6 GB).
#
#   sudo bash src/prereq/setup_wsl_kernel.sh
#
# Яагаад хэрэгтэй вэ: WSL2-ийн Microsoft кернелд linux-headers багц байхгүй, мөн
# CONFIG_MODVERSIONS=y тул symbol-ийн CRC (Module.symvers) ажиллаж буй кернелтэй
# яг таарах ёстой. Тиймээс ижил tag-ийн эх кодыг ажиллаж буй кернелийн тохиргоогоор
# (/proc/config.gz) хөрвүүлнэ. Энгийн Ubuntu-д энэ скрипт ХЭРЭГГҮЙ —
# src/prereq/setup_ubuntu_headers.sh-ийг ашигла.
set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "sudo-гоор ажиллуулна уу: sudo bash $0"; exit 1; }

REL=$(uname -r)                                   # жнь 6.6.87.2-microsoft-standard-WSL2
case "$REL" in
  *microsoft-standard-WSL2*) ;;
  *) echo "Энэ WSL2 кернел биш ($REL). Энгийн Linux-д: sudo bash src/prereq/setup_ubuntu_headers.sh"; exit 1 ;;
esac
VER=${REL%%-*}                                    # 6.6.87.2
TAG="linux-msft-wsl-$VER"
SRC=/usr/src/WSL2-Linux-Kernel

echo "==> 1/6 build хэрэгслүүд"
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq build-essential flex bison libssl-dev libelf-dev bc dwarves git

echo "==> 2/6 эх код ($TAG)"
if [ ! -f "$SRC/Makefile" ]; then
  git clone --depth 1 --branch "$TAG" https://github.com/microsoft/WSL2-Linux-Kernel.git "$SRC"
fi
cd "$SRC"
# git мэдээлэл байвал kernelrelease-д "+" нэмэгдэж, module-ийн vermagic таарахгүй
rm -rf .git

echo "==> 3/6 ажиллаж буй кернелийн тохиргоо"
zcat /proc/config.gz > .config
make -s olddefconfig
BUILT=$(make -s kernelrelease)
[ "$BUILT" = "$REL" ] || { echo "kernelrelease таарсангүй: $BUILT != $REL"; exit 1; }

echo "==> 4/6 vmlinux (Module.symvers-ийн CRC-д) — хэдэн арван минут"
if [ ! -f vmlinux.symvers ]; then
  make -j"$(nproc)" vmlinux
fi

echo "==> 5/6 modules_prepare"
make -s modules_prepare
cp vmlinux.symvers Module.symvers
# Өөрийн хөрвүүлсэн vmlinux-ийн BTF ажиллаж буй кернелийнхээс ялгаатай байж болох тул
# module-д BTF үүсгэхгүй (Makefile.modfinal vmlinux байхгүй бол алгасдаг).
[ -f vmlinux ] && mv vmlinux vmlinux.unused

echo "==> 6/6 /lib/modules/$REL/build холбоос"
mkdir -p "/lib/modules/$REL"
ln -sfn "$SRC" "/lib/modules/$REL/build"
echo "Бэлэн: /lib/modules/$REL/build -> $SRC"
echo "Одоо: cd src/kmod && make KDIR=$SRC && sudo insmod pid.ko"
