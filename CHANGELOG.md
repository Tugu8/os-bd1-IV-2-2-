# Өөрчлөлтийн түүх (CHANGELOG)

Хувилбар бүрийн гол өөрчлөлт. Формат: [Keep a Changelog](https://keepachangelog.com/), дугаарлалт: [Semantic Versioning](https://semver.org/lang/mn/) — дэлгэрэнгүйг [CONTRIBUTING.md](CONTRIBUTING.md) §6-аас харна уу.

## [Unreleased]

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
- **prereq** (бэлтгэсэн B190910014, хариуцагч B210930842): 2-р бүлгийн бэлтгэл module-ууд (`simple`, `/proc/hello`, `/proc/jiffies`, `/proc/seconds`), `sudo make test` (9), Ubuntu/WSL2 build орчны скрипт; `docs/Manual.md` §A Operational.
- **report** (бэлтгэсэн B190910014, хариуцагч B232270108): `report/IV-2-2_BD1_Report.pdf` (13 х.) ба `docs/IV-2-2_Manual.pdf` (14 х.); `report/build_pdfs.sh` дахин үүсгэнэ.

### Засвар
- **docs**: шүүмжлэх багийн код II-4-5 → **IV-2-5** (Topic and Peer Review Allocation хүснэгтийн дагуу).
- **kmod** (B190910014, PR #4): `task->pid` → `task_pid_vnr()` — PID namespace (WSL2, контейнер)-д бичсэн PID-тэй ижил дугаар хэвлэнэ.

<!--
Хувилбар гаргахдаа:
## [1.0.0] - 2026-MM-DD
### Нэмсэн / Өөрчилсөн / Засвар / Хассан
[Unreleased]: https://github.com/Tugu8/os-bd1-IV-2-2-/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/Tugu8/os-bd1-IV-2-2-/releases/tag/v1.0.0
-->
