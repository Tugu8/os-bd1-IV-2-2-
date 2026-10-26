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
| OS | Ubuntu 22.04 LTS (туршсан: WSL2 kernel `6.6.87.2-microsoft-standard-WSL2`) |
| Kernel API | `proc_ops` (≥ 5.6), `task_struct->__state` (≥ 5.14), `seq_file` |
| Хөрвүүлэгч | gcc 11.4, GNU make |
| UI | Python ≥ 3.8, орчин үеийн браузер (Edge, Chrome, Firefox) |
| Тест | bash, Python `unittest`; Node ≥ 18 (UI-ийн модны тест, заавал биш) |

## Repository бүтэц

| Хавтас | Агуулга | Хариуцагч |
|---|---|---|
| `src/prereq/` | 2-р бүлгийн бэлтгэл kernel module (`/proc` entry үүсгэх), build орчин | B210930842 |
| `src/kmod/` | Үндсэн kernel module (`pid.c`, `Makefile`) | B242270047 |
| `src/ui/` | Task hierarchy дүрслэлтэй interactive UI | B190910014 |
| `tests/basic/` | Номын жишээ болон үндсэн тестүүд | B231910003 |
| `tests/boundary/` | Захын болон буруу оролтын тестүүд | B231910003 |
| `docs/` | Manual (хэрэглэгчийн + operational), зургууд, [TASKS.md](docs/TASKS.md) | B241940099, B210930842 |
| `report/` | Үндсэн тайлан (Report.pdf) | B232270108 |
| `review/` | IV-2-5 багийн ажилд бичих шүүмж (Review.pdf) | B241940099 (бүгд) |

## Тест

```bash
bash tests/basic/test_basic.sh            # номын жишээ, PID 1, байхгүй PID, child
bash tests/boundary/test_boundary.sh      # abc, -5, хоосон, маш том тоо, kernel thread
python3 -m unittest src/ui/tests/test_api.py
python3 src/ui/contract_check.py          # module ↔ UI интерфейс (✔ / ⚠ / ✖)
```

`tests/`, `src/ui/` нь тус тусын PR merge хийгдсэний дараа ажиллана. Тест бүрийн хүлээгдсэн ба бодит үр дүнг `tests/`-ийн README-д screenshot-той хадгална.

## Хувилбар ба ажлын заавар

- Хувилбарыг [Semantic Versioning](https://semver.org/lang/mn/) (`vMAJOR.MINOR.PATCH`)-ээр дугаарлана. БД1-ийн илгээлт → `v1.0.0`, БД2 → `v2.0.0`. Өөрчлөлтийг [CHANGELOG.md](CHANGELOG.md)-д бичнэ.
- Branch, commit, Pull Request, review, release хийх дүрэм: [CONTRIBUTING.md](CONTRIBUTING.md).

## Багийн гишүүд

B242270047 · B190910014 · B210930842 · B231910003 · B232270108 · B241940099. Ажлын хуваарилалтыг [docs/TASKS.md](docs/TASKS.md)-ээс харна уу.

## Бэлэн код, сан, AI ашиглалт

- Kernel module нь номын Programming Project 2-ын skeleton (`proc_ops`, `kmalloc`, `copy_from_user`, `kstrtol`, `pid_task`, `find_vpid`) дээр суурилсан.
- UI (`src/ui/`): кодыг Claude (Anthropic) AI туслахын тусламжтай боловсруулсан. B190910014 уншиж, ажиллуулж, туршиж шалгасан. Гадны сан ашиглаагүй.
- Хэрэглэгчийн manual (`docs/Manual.md`) болон шүүмжийн төлөвлөгөө (`review/README.md`): ноорогийг Claude (Anthropic) AI туслахын тусламжтай боловсруулсан. B241940099 уншиж, UI-ийн код болон README-тэй тулгаж шалгасан.
- Бусад хэсэгт AI ашигласан бол хариуцагч нь энд нэмж бичнэ.
