# IV-2-2 – Linux Kernel Module for Task Information

**Хичээл:** F.CSM302 Үйлдлийн систем • Бие даалт 1
**Хуваарилалтын код:** IV-2-2
**Сурах бичиг:** Operating System Concepts (2018), 3-р бүлэг, Programming Project 2
**UI дүрслэл:** Task hierarchy

## Зорилго

`/proc/pid` файлаар дамжуулан PID хүлээн авч, тухайн task-ийн мэдээллийг (command, pid, state) буцаадаг Linux kernel module бичих. Мөн сонгосон процессын parent болон child-уудыг шатлалтай мод хэлбэрээр харуулдаг interactive UI хийх.

```bash
echo "1395" > /proc/pid
cat /proc/pid
command = [bash] pid = [1395] state = [1]
```

## Repository бүтэц

| Хавтас | Агуулга |
|---|---|
| `src/prereq/` | 2-р бүлгийн бэлтгэл kernel module (`/proc` entry үүсгэх) |
| `src/kmod/` | Үндсэн kernel module (`pid.c`, `Makefile`) |
| `src/ui/` | Task hierarchy дүрслэлтэй interactive UI |
| `tests/basic/` | Номын жишээ болон үндсэн тестүүд |
| `tests/boundary/` | Захын болон буруу оролтын тестүүд |
| `docs/` | Manual (хэрэглэгчийн + operational), зургууд |
| `report/` | Үндсэн тайлан (Report.pdf) |
| `review/` | II-4-5 багийн ажилд бичих шүүмж (Review.pdf) |

## Quick Start

> Код бичигдсэний дараа энд бөглөнө. Үүнд build, insmod, UI ажиллуулах, rmmod хийх командууд орно.

## Орчин

- Linux (bare-metal, Ubuntu/Debian), kernel version: _бөглөнө_
- `build-essential`, `linux-headers-$(uname -r)`

## Багийн гишүүд

Ажлын хуваарилалтыг [docs/TASKS.md](docs/TASKS.md) файлаас харна уу.

## Бэлэн код, сан, AI ашиглалт

> Ашигласан бол энд тэмдэглэнэ (шаардлагын дагуу).
