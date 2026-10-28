# IV-2-2 – Linux Kernel Module for Task Information

**Хичээл:** F.CSM302 Үйлдлийн систем • Бие даалт 1
**Хуваарилалтын код:** IV-2-2 · **Шүүмжлэх баг:** IV-2-5 (Sudoku Solution Validator)
**Сурах бичиг:** Operating System Concepts (2018), 3-р бүлэг, Programming Project 2
**UI дүрслэл:** Task hierarchy

## Зорилго

`/proc/pid` файлаар дамжуулан PID хүлээн авч, тухайн task-ийн мэдээллийг (command, pid, state) буцаадаг Linux kernel module бичих. Мөн сонгосон процессын parent болон child-уудыг шатлалтай мод хэлбэрээр харуулдаг interactive UI хийх.

```bash
echo "1395" > /proc/pid
cat /proc/pid
command = [bash] pid = [1395] state = [1]
parent = [sshd] ppid = [1300]
child = [vim] pid = [1400] state = [1]
```

Эхний мөр нь номын яг формат. `parent`, `child` мөрүүд нь task hierarchy-д зориулсан өргөтгөл.

## Quick Start

Ubuntu 22.04 / Debian (bare-metal эсвэл VM) дээр:

```bash
# 1. Хэрэгцээт сан
sudo apt install build-essential linux-headers-$(uname -r) python3

# 2. Kernel module-ийг хөрвүүлж ачаалах
cd src/kmod && make && cd ../..      # Makefile нь $(PWD)-г ашигладаг тул хавтсандаа орж make хийнэ
sudo insmod src/kmod/pid.ko
ls -l /proc/pid                      # -rw-rw-rw- ... /proc/pid

# 3. Номын жишээ
echo $$ > /proc/pid && cat /proc/pid # одоогийн bash
echo 1  > /proc/pid && cat /proc/pid # systemd / init

# 4. Task hierarchy UI
python3 src/ui/server.py             # → http://localhost:8000

# 5. Дуусгах
sudo rmmod pid
(cd src/kmod && make clean)
```

UI нь зөвхөн Python 3 стандарт сан, браузер ашиглана. Нэмэлт суулгац хэрэггүй. Дэлгэрэнгүйг [src/ui/README.md](src/ui/README.md)-ээс харна уу.

> **WSL2:** Microsoft-ын кернелд `linux-headers` багц байдаггүй. Кернелийн эх кодыг ажиллаж буй хувилбартай тааруулж бэлдэнэ (`src/prereq/` — B210930842). WSL-д PID namespace өөр тул module `task_pid_vnr()` ашиглаж байж `ps`-тэй ижил PID хэвлэнэ.

## Орчин

| | Хувилбар |
|---|---|
| OS | Ubuntu 22.04 / 24.04 LTS, Debian — bare-metal эсвэл VM (туршсан: Ubuntu 24.04.5 bare-metal, kernel `7.0.0-34-generic`; Kubuntu 26.04.1, kernel `7.0.0-38-generic`; хөгжүүлэлт: WSL2 `6.6.87.2`) |
| Kernel API | `proc_ops` (≥ 5.6), `task_struct->__state` (≥ 5.14), `seq_file` |
| Хөрвүүлэгч | gcc 13.3 (Ubuntu 24.04), gcc 15.2 (Kubuntu 26.04), gcc 11.4 (WSL2), GNU make |
| UI | Python ≥ 3.8, орчин үеийн браузер (Edge, Chrome, Firefox) |
| Тест | bash, Python `unittest`; Node ≥ 18 (UI-ийн модны тест, заавал биш) |

## Repository бүтэц

| Хавтас | Агуулга | Хариуцагч |
|---|---|---|
| `src/prereq/` | 2-р бүлгийн бэлтгэл kernel module (`/proc` entry үүсгэх), build орчин | B210930842 (гүйцэтгэсэн: B190910014) |
| `src/kmod/` | Үндсэн kernel module (`pid.c`, `Makefile`) | B242270047 |
| `src/ui/` | Task hierarchy дүрслэлтэй interactive UI | B190910014 |
| `tests/basic/` | Номын жишээ болон үндсэн тестүүд | B231910003 |
| `tests/boundary/` | Захын болон буруу оролтын тестүүд | B231910003 |
| `docs/` | Manual ([Manual.md](docs/Manual.md), [IV-2-2_Manual.pdf](docs/IV-2-2_Manual.pdf)), зургууд, [TASKS.md](docs/TASKS.md) | B241940099, B210930842 |
| `report/` | Үндсэн тайлан [IV-2-2_BD1_Report.pdf](report/IV-2-2_BD1_Report.pdf) (+ `.tex`, `build_pdfs.sh`) | B232270108 (гүйцэтгэсэн: B190910014, B242270047) |
| `review/` | IV-2-5 багийн ажилд бичих шүүмж (Review.pdf) | B241940099 (бүгд) |

## Тест

```bash
bash tests/basic/test_basic.sh            # номын жишээ, PID 1, байхгүй PID, child, kernel thread
bash tests/boundary/test_boundary.sh      # abc, -5, хоосон, 0, маш том тоо, overflow, урт мөр
python3 -m unittest src/ui/tests/test_api.py
python3 src/ui/contract_check.py          # module ↔ UI интерфейс (✔ / ⚠ / ✖)
```

Бодит үр дүн: `tests/*/result_baremetal.txt` (Ubuntu 24.04), `tests/*/result_acer_kubuntu.txt` (Kubuntu 26.04), орчны мэдээлэл `tests/env_*.txt`-д байна. Нэгтгэсэн хүснэгтийг [Manual](docs/Manual.md)-ийн A7 болон тайлангийн §8.1-ээс харна уу.

## Хувилбар ба ажлын заавар

- Хувилбарыг [Semantic Versioning](https://semver.org/lang/mn/) (`vMAJOR.MINOR.PATCH`)-ээр дугаарлана. БД1-ийн илгээлт → `v1.0.0` (засвар: `v1.0.1`), БД2 → `v2.0.0`. Өөрчлөлтийг [CHANGELOG.md](CHANGELOG.md)-д бичнэ.
- Branch, commit, Pull Request, review, release хийх дүрэм: [CONTRIBUTING.md](CONTRIBUTING.md).

## Багийн гишүүд

B242270047 · B190910014 · B210930842 · B231910003 · B232270108 · B241940099. Ажлын хуваарилалтыг [docs/TASKS.md](docs/TASKS.md)-ээс харна уу.

## Бэлэн код, сан, AI ашиглалт

- Kernel module нь номын Programming Project 2-ын skeleton (`proc_ops`, `kmalloc`, `copy_from_user`, `kstrtol`, `pid_task`, `find_vpid`) дээр суурилсан.
- Код болон баримт бичгийг боловсруулахад AI туслах (Claude) ашигласан; хариуцсан гишүүд уншиж, ажиллуулж, туршиж шалгасан. Гадны программын сан ашиглаагүй.
