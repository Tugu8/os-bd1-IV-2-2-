# src/prereq — 2-р бүлгийн бэлтгэл module ба build орчин

**Хариуцагч:** B210930842 ([docs/TASKS.md](../../docs/TASKS.md)) · **Бэлтгэсэн:** B190910014. OSC (2018) 2-р бүлгийн Programming Project "Linux Kernel Modules" — `src/kmod/pid.c`-ийн (3-р бүлэг) өмнөх бэлтгэл: module ачаалах/буулгах, kernel log, `/proc` файл үүсгэх.

## Агуулга

| Файл | Номын хэсэг | Юу хийдэг |
|---|---|---|
| `simple.c` | I хэсэг + даалгавар | Ачаалах/буулгахад `dmesg`-д: `GOLDEN_RATIO_PRIME`, `gcd(3300, 24)`, `jiffies`, `HZ` |
| `hello.c` | II хэсэг | `/proc/hello` → `Hello World` |
| `jiffies.c` | Assignment 1 | `/proc/jiffies` → одоогийн `jiffies` |
| `seconds.c` | Assignment 2 | `/proc/seconds` → module ачаалснаас хойших секунд |
| `Makefile` | | `make`, `sudo make test`, `make clean` |
| `test_prereq.sh` | | 9 шалгалт (PASS/FAIL) |
| `setup_ubuntu_headers.sh` | | Ubuntu/Debian: `build-essential`, `linux-headers-$(uname -r)` суулгана |
| `setup_wsl_kernel.sh` | | Зөвхөн WSL2 (хөгжүүлэлтэд): kernel эх кодыг ажиллаж буй хувилбартай тааруулж бэлдэнэ |

Номын skeleton нь `file_operations`, `proc_read` + `completed` туг ашигладаг. Энд kernel ≥ 5.6-ийн `struct proc_ops` болон `seq_file` (`single_open`)-ийг ашигласан тул `src/kmod/pid.c`-тэй ижил загвартай бөгөөд жижиг буфероор уншсан ч гаралт бүтэн гарна.

## Ажиллуулах

```bash
sudo bash src/prereq/setup_ubuntu_headers.sh   # нэг удаа: build-essential, linux-headers
cd src/prereq
make
sudo make test                                 # 9 PASS
```

Гараар:

```bash
sudo insmod simple.ko && sudo rmmod simple && sudo dmesg | tail -6
sudo insmod hello.ko   && cat /proc/hello   && sudo rmmod hello
sudo insmod jiffies.ko && cat /proc/jiffies && sudo rmmod jiffies
sudo insmod seconds.ko && sleep 3 && cat /proc/seconds && sudo rmmod seconds
make clean
```

Бодит `dmesg` (simple, WSL2 6.6.87.2, `sleep 1`-ийн дараа `rmmod`):

```
simple: Loading Kernel Module
simple: GOLDEN_RATIO_PRIME = 7046029254386353131
simple: jiffies = 4301417230, HZ = 250
simple: gcd(3300, 24) = 12
simple: jiffies = 4301417495, 1060 ms since load
simple: Removing Kernel Module
```

`HZ` нь kernel-ийн `CONFIG_HZ`-оос хамаарна (WSL2: 250; Ubuntu generic ихэвчлэн 250 — `grep CONFIG_HZ= /boot/config-$(uname -r)`). `jiffies` нь `HZ` удаа/секунд нэмэгддэг тул `/proc/jiffies`-ийг 1 секундын зайтай уншихад ойролцоогоор `HZ`-аар өснө.

## Build орчин

| | Хувилбар |
|---|---|
| OS | Ubuntu 22.04 / 24.04 LTS, Debian 12 — bare-metal эсвэл VM |
| Kernel | ≥ 5.14 (`proc_ops` ≥ 5.6, `task_struct->__state` ≥ 5.14); туршсан: `7.0.0-34-generic` (Ubuntu 24.04, bare-metal), `6.6.87.2-microsoft-standard-WSL2` |
| Багц | `build-essential` (gcc, make), `linux-headers-$(uname -r)`, `python3` (UI) |
| Эрх | `insmod` / `rmmod` — `sudo` |

**Secure Boot:** асаалттай бол гарын үсэггүй module-ийг kernel татгалзана (`Key was rejected by service`). BIOS-оос Secure Boot-ийг унтраах эсвэл `mokutil`-оор module-д гарын үсэг зурна. Унтраасан үед `insmod` хийхэд `module verification failed ... tainting kernel` анхааруулга гарна — ажиллагаанд нөлөөлөхгүй.

**WSL2** нь хөгжүүлэлтэд л зориулагдсан: Microsoft-ын kernel-д `linux-headers` багц байхгүй тул `sudo bash src/prereq/setup_wsl_kernel.sh` (≈ 20–30 мин, 6 GB) эх кодыг бэлдэж `/lib/modules/$(uname -r)/build` холбоосыг үүсгэнэ. WSL дахин асахад холбоос алга болбол скриптийг дахин ажиллуулна.
