# src/ui — Task Hierarchy UI

**Хариуцагч:** B190910014 · `docs/TASKS.md`-ийн дагуу: PID оруулах/сонгох, task hierarchy мод зурах, state-ийг өнгөөр ялгах, refresh/reset, алдааны мэдэгдэл. Kernel module-тай `/proc/pid`-ээр холбогдоно.

Зөвхөн **Python 3 стандарт сан** + браузер (HTML/CSS/JS, гадны санггүй) — нэмэлт суулгац шаардлагагүй.

## Ажиллуулах

```bash
sudo insmod src/kmod/pid.ko            # kernel module (src/kmod — B242270047)
python3 src/ui/server.py               # → http://localhost:8000
python3 src/ui/server.py --port 9000   # өөр порт
python3 src/ui/server.py --fallback    # module хараахан бэлэн биш үед (доорхыг үз)
```
WSL2 дээр Windows-ийн браузераас шууд `http://localhost:8000` нээгдэнэ. Зогсоох: `Ctrl+C`.

## Боломжууд

| Боломж | Хаана |
|---|---|
| PID оруулах (талбар + Enter), процессын жагсаалтаас сонгох/шүүх, модны зангилаа дээр дарах | зүүн самбар, мод |
| Номын интерфейс: `echo N > /proc/pid; cat /proc/pid`-ийн бодит гаралт | "Номын интерфейс" карт |
| Task мэдээлэл: command, PID, TGID, PPID, state (тэмдэгт + `__state`), UID, урсгалын тоо | "Task мэдээлэл" карт |
| **Task hierarchy мод** (SVG): өвөг эцгийн гинж (PID 1 хүртэл) → сонгосон task → хүү процессууд (гүн 0–4) | "Шатлал" |
| State-ийн өнгө: R ногоон, S цэнхэр, D улбар шар, T саарал, Z улаан, I цайвар + legend | мод, жагсаалт |
| Refresh: автомат шинэчлэх (1/2/5 с) — жнь R↔S өөрчлөлт харагдана | зүүн самбар |
| Reset: бүх төлөвийг цэвэрлэнэ | зүүн самбар |
| Demo мод: мэдэгдэж буй бүтэцтэй туршилтын процессууд (S, R/S, T, Z, 5 урсгалтай) — `demo_tree.py` | "Demo мод үүсгэх / зогсоох" |
| Алдааны мэдэгдэл: буруу оролт (`abc`, `-5`, хэт том), байхгүй PID, module ачаалагдаагүй | улаан banner |
| Module-ийн түүхий гаралт (`cat /proc/pid_tree`) — дүрслэл бодит өгөгдөлтэй нийцэхийг шалгах | доод хэсэг |
| URL параметр: `?pid=1&depth=2&auto=1&raw=1&demo=1` — шууд холбоос, screenshot | |

## Kernel module-тай тохирох интерфейс (санал — `src/kmod`-тай тохиролцоно)

UI нь **номын интерфейс** `/proc/pid`-ийг яг номын дагуу ашиглана. Модыг зурахын тулд parent болон children хэрэгтэй тул (TASKS.md: *"Parent болон children жагсаалтыг гаргадаг өргөтгөл"*) нэмэлт **`/proc/pid_tree`**-ийг доорх форматаар уншина:

```
$ echo 1395 > /proc/pid          # PID-ийг /proc/pid эсвэл /proc/pid_tree руу бичнэ
$ cat /proc/pid
command = [bash] pid = [1395] state = [1]
$ cat /proc/pid_tree
task     pid=1395 tgid=1395 ppid=1300 state=1 state_char=S uid=1000 threads=1 comm=bash
ancestor pid=1300 tgid=1300 ppid=1 state=1 state_char=S uid=0 threads=1 comm=sshd
ancestor pid=1 tgid=1 ppid=0 state=1 state_char=S uid=0 threads=1 comm=systemd
child    pid=1400 tgid=1400 ppid=1395 state=0 state_char=R uid=1000 threads=1 comm=ls
summary  ancestors=2 children=1 truncated=0
```

| Мөр | Утга |
|---|---|
| `task` | Сонгосон task (яг 1 мөр) |
| `ancestor` | `real_parent`-ээр дээш — эцэг эхэнд, PID 1 сүүлд |
| `child` | `task->children` (`sibling` холбоос) — шууд хүү процессууд |
| `summary` | тоо, `truncated=1` бол хүүхдийн жагсаалт хязгаараас хэтэрсэн |

Талбарууд: `pid`/`tgid`/`ppid` — **бичсэн процессын namespace**-ийн дугаар (`task_pid_vnr`, WSL/контейнер дотор `ps`-тэй таарахын тулд), `state` — `__state`, `state_char` — `task_state_to_char()`, `uid`, `threads` — `signal->nr_threads`, `comm` — **мөрийн төгсгөлд** (нэр зай агуулж болно). Хүчингүй PID бол хоёр файл хоёулаа **0 байт** (номын шаардлага).

> Формат өөр байвал зөвхөн `server.py`-ийн `parse_tree_output()`-ийг өөрчилнө — UI-ийн бусад хэсэг JSON дээр ажилладаг.

**Синхрончлол:** module нэг *глобал* PID хадгалдаг тул хоёр хүсэлт зэрэг "бичих → унших" хийвэл нэг нь нөгөөгийнхийг уншиж болно. Сервер `threading.Lock()`-оор бичих+уншихыг нэг эгзэгтэй мужид оруулна (`src/ui/tests/test_api.py::test_10`).

## `--fallback` горим

Kernel module бэлэн болохоос өмнө UI-г хөгжүүлэх/турших зориулалттай: `/proc/<pid>/stat`-аас ижил бүтэц үүсгэнэ. UI-д **"⚠ Нөөц горим … kernel module биш"** гэж тодорхой харагдана, номын мөрөнд `(fallback)` гэж бичигдэнэ. Эцсийн туршилт, screenshot-ыг module ачаалсан үед хийнэ.

## API (server.py)

| Endpoint | Хариу |
|---|---|
| `GET /api/status` | `module_loaded`, backend, кернел, demo root |
| `GET /api/task?pid=N&depth=D` | `book_line`, `task`, `ancestors[]`, `tree` (D түвшин), `raw`, `nodes`, `queries`, `elapsed_ms` · алдаа: 400 (буруу оролт), 404 (байхгүй PID), 503 (module байхгүй) |
| `GET /api/processes` | `[{pid, ppid, comm, state_char}]` — сонгох жагсаалт |
| `POST /api/demo`, `POST /api/demo/stop` | туршилтын процессын мод |

## Тест

```bash
python3 -m unittest -v src/ui/tests/test_api.py    # 10 тест; module байхгүй бол fallback горимоор
```
Статус, PID 1, demo модны бүтэц (5 хүүхэд, Z/T, 5 урсгал), depth=0, буруу оролт → 400, байхгүй PID → 404, буруу depth, процессын жагсаалт, static/path traversal, зэрэг хүсэлтийн тууштай байдал.

## Файлууд

| Файл | Агуулга |
|---|---|
| `server.py` | HTTP сервер, JSON API, `/proc/pid_tree` задлагч, мутекс, demo удирдлага |
| `static/index.html`, `app.js`, `style.css` | UI, SVG модны байрлал (tidy tree), legend, автомат шинэчлэлт |
| `demo_tree.py` | Туршилтын процессын мод (`demo_root` → sleeper/busy/stopped/threads/zombie) |
| `tests/test_api.py` | API тест (unittest) |

## AI ашиглалт

UI-ийн код болон энэ баримтыг боловсруулахад Claude (Anthropic) AI туслахыг ашигласан; B190910014 уншиж, ажиллуулж, туршиж шалгасан.
