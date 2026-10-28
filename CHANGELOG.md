# Өөрчлөлтийн түүх (CHANGELOG)

Хувилбар бүрийн гол өөрчлөлт. Формат: [Keep a Changelog](https://keepachangelog.com/), дугаарлалт: [Semantic Versioning](https://semver.org/lang/mn/) — дэлгэрэнгүйг [CONTRIBUTING.md](CONTRIBUTING.md) §6-аас харна уу.

## [Unreleased]

## [1.0.1] - 2026-10-28

> PR #22-ын засвар (тэмдэгт хассан тайлан, Manual) нь `v1.0.1` tag-д ороогүй; Release-ийн хавсралт PDF-үүдийг 2026-10-28-нд PR #22-ын дараах хувилбараар сольсон.

### Нэмсэн
- **tests** (B231910003, PR #19): хоёр дахь компьютер (Acer Nitro, Kubuntu 26.04.1, kernel 7.0.0-38, gcc 15.2, Secure Boot асаалттай, гарын үсэгтэй module) дээрх үр дүн: basic 5/5, boundary 7/7 (`tests/*/result_acer_kubuntu.txt`, `tests/env_acer_kubuntu.txt`).

### Өөрчилсөн
- **docs, report** (B242270047, PR #20): PR #19-ийн үр дүнг тайлан (§5.5 PR #15–#19, §7, §8.1, §9, §10, Хавсралт A), Manual (A1, A3, A6, A7, A8, B1), README-д нэмж, PDF-үүдийг дахин үүсгэсэн. Manual A3-д Secure Boot-той үед module-д гарын үсэг зурах алхмыг нэмсэн. Тайлангийн нүүрийн огноо 10-28.
- **report** (B242270047, PR #20): хүснэгтийн нүдийг зүүн тийш тэгшилсэн (үгсийн хоорондох зай сунадаг байсан); §9-д `\filbreak`-ээс болж хуудас хоосон үлддэг байсныг зассан. E6-ийн оролтыг скрипттэй тааруулсан (30 оронтой тоо).
- **tests** (B242270047, PR #20): `tests/env_acer_kubuntu.txt`-ийн эхний мөрөнд үлдсэн VS Code терминалын escape тэмдэгтийг (`]633;...`) цэвэрлэсэн.
- **docs** (B242270047, PR #20): README-ийн тестийн тайлбарыг зассан (kernel thread нь basic тестэд байдаг), байхгүй `tests/` README-ийн тухай хуучирсан мөрийг сольсон; `REPORT_KMOD.md`-ийн screenshot-ын замыг зассан.
- **report, docs** (B242270047, PR #17, #18): тайлангийн нүүрийг энгийн болгосон — сэдэв, хуваарилалтын код, багш, гишүүдийн нэр ба оюутны код, огноо. §5.5 ба Хавсралт A-д B210930842-ийн бэлтгэсэн ноорогийг (`prereq-manual.docx`) тэмдэглэсэн, TASKS.md-д мөн нэмсэн.
- **report** (B242270047, PR #22): тайлангаас ✔/⚠/✖ тэмдэг, сум (→, ↔ гэх мэт), UI-ийн товчны дүрс, урт зураасыг (—) хасаж, энгийн үг, цэг таслалаар сольсон. PASS-ийн өнгийг хассан. Агуулгыг шинэ хуудаснаас эхлүүлсэн.
- **docs** (B242270047, PR #22): Manual-аас мөн ✔/⚠/✖, сум, ⊕/⊖/▶/◀ дүрс, урт зураасыг хасаж, UI-ийн товчийг нэрээр нь тайлбарласан; Manual-ийн нүүрний бичвэрийг (`md2tex.py`) мөн зассан. Manual A2-д `v1.0.1`.

## [1.0.0] - 2026-10-27

### Нэмсэн
- **kmod** (B242270047, PR #1): `/proc/pid` module.
  - Write хэсэг: `kmalloc`, `copy_from_user`, `kstrtol`; хязгаараас гадуурх PID-ийг татгалзана.
  - Read хэсэг: `seq_file`-ээр номын мөр (`command = [..] pid = [..] state = [..]`), дараа нь `parent` ба `child` мөрүүд.
- **docs** (B190910014, PR #3): README Quick Start, орчин, тест; CONTRIBUTING (ажлын урсгал, semantic commit, review, хувилбар); CHANGELOG.
- **docs** (B241940099): `docs/Manual.md` хэрэглэгчийн хэсэг: дүрслэлийн тэмдэг, өнгө, 5 жишээ, түгээмэл алдаа, гарын товч.
- **review** (B241940099): `review/README.md` IV-2-5-ийн шүүмжийн зохион байгуулалт, checklist, Review.pdf-ийн бүтэц.
- **ui** (B190910014, PR #2): Task hierarchy вэб UI (`src/ui/`): PID сонгох, SVG мод, төлөвийн өнгө, өөрчлөлтийн тодруулга, түүх, туршилтын процессын мод (fork/STOP/CONT/TERM/wait), газар дээр нь нээх, JSON/SVG/PNG экспорт; `contract_check.py`; 24 API + 12 Node тест.
- **kmod** (B242270047): bare-metal туршилтын үр дүн (`tests/kmod_baremetal.txt`), тайлангийн хэсэг (`src/kmod/REPORT_KMOD.md`), UI-ийн bare-metal screenshot.
- **tests** (B231910003, PR #11): `tests/basic/test_basic.sh` (5), `tests/boundary/test_boundary.sh` (7).
- **tests** (B242270047): bare-metal Ubuntu 24.04.5 (kernel 7.0.0-34) дээрх автомат тестийн үр дүн (`*/result_baremetal.txt`, `tests/env_baremetal.txt`): basic 5/5, boundary 7/7, prereq 9/9, UI API 24 OK (1 алгассан), contract_check 17 ✔ 1 ⚠. Тайлан §8.1, Manual A7-д бөглөж, 3 screenshot нэмсэн (`term_book_example.png`, `term_tests_pass.png`, `ui_invalid_input.png`).
- **prereq** (бэлтгэсэн B190910014, хариуцагч B210930842 — ноорог `prereq-manual.docx`): 2-р бүлгийн бэлтгэл module-ууд (`simple`, `/proc/hello`, `/proc/jiffies`, `/proc/seconds`), `sudo make test` (9), Ubuntu/WSL2 build орчны скрипт; `docs/Manual.md` §A Operational.
- **report** (бэлтгэсэн B190910014, хариуцагч B232270108 — гүйцэтгээгүй): `report/IV-2-2_BD1_Report.pdf` (17 х.) ба `docs/IV-2-2_Manual.pdf` (17 х.); `report/build_pdfs.sh` дахин үүсгэнэ.

### Засвар
- **docs** (B242270047, PR #14): README, Manual, prereq README-ийн дэмжих орчныг "bare-metal эсвэл VM" болгосон (VM-ийг хориглосон нь лабын дүрэм, БД-ийнх биш); туршсан орчныг Ubuntu 24.04 bare-metal болгож шинэчилсэн. TASKS.md-ийн UI-ийн хэлийг нөхсөн.
- **report** (B242270047, PR #14): нүүр болон Хавсралт A-д гишүүдийн бодит гүйцэтгэлийг тэмдэглэсэн (B232270108 — гүйцэтгээгүй); §5.5 "GitHub дээрх ажиллагаа" (PR #1–#14), §5.6 AI ашиглалт, §2 шаардлагын хангалтын хүснэгт нэмсэн (OS_BD1_Guide §2, §6). Нүүрэнд ШУТИС лого; зураг 4 → 8 (UI бүтэц, шинэ хүү процесс, module дуудлагын лог).
- **docs** (B242270047, PR #14): Manual-д 3 зураг нэмсэн (bare-metal дэлгэцийн бүтэц, bare-metal түүх, газар дээр нь нээх), нүүрэнд лого. `md2tex.py`: код блокийг `listings` → `fvextra` (XeLaTeX дээр кирилл үсгийн дараалал эвдэрч "БД1-ийн" → "БДийн1-" болдог байсан); тайлангийн кирилл тайлбартай кодыг мөн зассан.
- **review** (B242270047, PR #14): Review PDF-ийн бүтэц, рубрик, priority, Reply-ийн загварыг албан ёсны Peer Review Guide-тэй тааруулсан; файлын нэр `IV-2-2_Review_IV-2-5.pdf`.
- **docs** (B242270047): `term_book_example.png`-ийн дээд талд буулгалтаас үлдсэн `^[[200~cd` мөрийг хасаж, PDF-үүдийг дахин үүсгэсэн.
- **report** (B242270047): `md2tex.py` — `*налуу*` дотор `код` байхад Manual-ийн зургийн тайлбарт `*` тэмдэг шууд хэвлэгддэг байсныг зассан.
- **docs**: шүүмжлэх багийн код II-4-5 → **IV-2-5** (Topic and Peer Review Allocation хүснэгтийн дагуу).
- **kmod** (B190910014, PR #4): `task->pid` → `task_pid_vnr()` — PID namespace (WSL2, контейнер)-д бичсэн PID-тэй ижил дугаар хэвлэнэ.

[Unreleased]: https://github.com/Tugu8/os-bd1-IV-2-2-/compare/v1.0.1...HEAD
[1.0.1]: https://github.com/Tugu8/os-bd1-IV-2-2-/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/Tugu8/os-bd1-IV-2-2-/releases/tag/v1.0.0
