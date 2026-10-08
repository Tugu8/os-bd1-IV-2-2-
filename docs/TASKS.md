# Ажлын төлөвлөгөө ба хуваарилалт (Хавсралт A)

| Талбар | Мэдээлэл |
|---|---|
| Хуваарилалтын код | IV-2-2 |
| Төсөл | Linux Kernel Module for Task Information |
| Repository | _GitHub холбоос_ |
| Хэл/сан/орчин | C (Linux kernel module), UI: _сонгоно_; Ubuntu/Debian bare-metal |
| Үндсэн дүрслэл | Task hierarchy (parent – task – children мод) |
| Шүүмжлэх баг | II-4-5 (Sudoku Solution Validator) |

## Гишүүдийн хариуцах ажил

| Гишүүн | Хариуцах ажил | Commit/file |
|---|---|---|
| **B242270047** (багийн ахлагч) | **Үндсэн kernel module.** `/proc/pid`-ийн write (`kmalloc`, `copy_from_user`, `kstrtol`), read (`find_vpid`, `pid_task`, command/pid/state), алдаа шалгах (NULL PID → 0). Parent болон children жагсаалтыг гаргадаг өргөтгөл. Шинэ kernel-ийн API (`proc_ops`, `__state`). Code review болон merge хийнэ. | `src/kmod/` |
| B190910014 | **Interactive UI.** PID оруулах, сонгох; task hierarchy модыг зурах; state-ийг өнгөөр ялгах; refresh/reset хийх; алдааны мэдэгдэл харуулах. Kernel module-тай `/proc/pid`-ээр холбогдоно. | `src/ui/` |
| B210930842 | **2-р бүлгийн бэлтгэл module ба build орчин.** Hello/jiffies маягийн `/proc` module, `Makefile`, суулгах заавар. Kernel version, dependency-г баримтжуулна. **Operational manual** бичнэ. | `src/prereq/`, `docs/Manual.md` (operational хэсэг) |
| B231910003 | **Туршилт.** Номын жишээ (bash, init PID 1 гэх мэт) болон нэмэлт тестүүд. Boundary/error тест: байхгүй PID, сөрөг тоо, үсэг, хоосон оролт, маш том тоо, kernel thread. Тест бүрийн хүлээгдсэн ба бодит үр дүнг screenshot-той хадгална. | `tests/` |
| B232270108 | **Үндсэн тайлан.** Онолын үндэс (PCB, `task_struct`, process state, `/proc`), системийн зохиомж (компонент ба өгөгдлийн урсгалын диаграм), үр дүн ба хэлэлцүүлгийг нэгтгэж **Report.pdf** гаргана. | `report/` |
| B241940099 | **Хэрэглэгчийн manual ба танилцуулга.** User manual (дүрслэлийн тэмдэг, өнгө, 2+ жишээ, түгээмэл алдаа), README Quick Start, MS Teams БД1 пост. **II-4-5-ийн шүүмжийг** зохион байгуулна (бүх гишүүн оролцоно). | `docs/Manual.md` (хэрэглэгчийн хэсэг), `review/` |

> Тайлангийн "Хэрэгжилт" хэсгийг kernel module болон UI хариуцсан гишүүд өөрсдөө бичиж өгнө.

## Хуваарь

| Долоо хоног | Ажил | Хариуцагч |
|---|---|---|
| 5 | Repo үүсгэх, ажил хуваарилах, Linux орчин бэлдэх | Бүгд |
| 6 | Бэлтгэл module → үндсэн kernel module | B210930842 → B242270047 |
| 7 | UI-г module-тай холбох, тест эхлэх | B190910014, B231910003 |
| 8 | Тест, тайлан, Manual нэгтгэх | B231910003, B232270108, B241940099 |
| 9 | Release/Tag, Report.pdf, Manual.pdf, БД1 пост | B242270047, B241940099 |
| 10 | II-4-5-ийн ажлыг build/run/тест хийж Review.pdf гаргах | Бүгд |

## Үндсэн тестүүд

| Тест | Оролт/нөхцөл | Хүлээгдсэн үр дүн |
|---|---|---|
| 1 | Ажиллаж буй bash-ийн PID | `command = [bash] pid = [...] state = [...]` |
| 2 | PID 1 (systemd/init) | Мэдээлэл гарч, children олон байна |
| 3 | Байхгүй PID (жишээ 999999) | Read 0 буцаана, UI ойлгомжтой алдаа харуулна |
| 4 | Тоо биш оролт (`abc`), сөрөг тоо | Write алдаа буцаана, kernel crash гарахгүй |
| 5 | Child process үүсгээд түүний parent-ийн PID | Мод дээр шинэ child харагдана |

## Git ажлын дүрэм

1. `main` руу шууд push хийхгүй. Гишүүн бүр өөрийн branch дээр ажиллана (`kmod`, `ui`, `tests`, `docs`, `report`).
2. Pull Request нээж, ахлагч review хийгээд merge хийнэ.
3. Commit мессежийг ойлгомжтой бичнэ, жишээ нь `ui: add tree rendering`.
4. Нууц үг, хувийн өгөгдөл оруулахгүй. Build-ийн файлуудыг (`*.ko`, `*.o`) commit хийхгүй.
