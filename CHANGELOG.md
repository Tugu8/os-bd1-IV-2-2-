# Өөрчлөлтийн түүх (CHANGELOG)

Хувилбар бүрийн гол өөрчлөлт. Формат: [Keep a Changelog](https://keepachangelog.com/), дугаарлалт: [Semantic Versioning](https://semver.org/lang/mn/) — дэлгэрэнгүйг [CONTRIBUTING.md](CONTRIBUTING.md) §6-аас харна уу.

## [Unreleased]

### Нэмсэн
- **kmod** (B242270047, PR #1): `/proc/pid` module.
  - Write хэсэг: `kmalloc`, `copy_from_user`, `kstrtol`; хязгаараас гадуурх PID-ийг татгалзана.
  - Read хэсэг: `seq_file`-ээр номын мөр (`command = [..] pid = [..] state = [..]`), дараа нь `parent` ба `child` мөрүүд.
- **docs**: README Quick Start, орчин, тест; CONTRIBUTING (ажлын урсгал, semantic commit, review, хувилбар); CHANGELOG.
- **docs** (B241940099): `docs/Manual.md` хэрэглэгчийн хэсэг: дүрслэлийн тэмдэг, өнгө, 5 жишээ, түгээмэл алдаа, гарын товч.
- **review** (B241940099): `review/README.md` IV-2-5-ийн шүүмжийн зохион байгуулалт, checklist, Review.pdf-ийн бүтэц.

### Засвар
- **docs**: шүүмжлэх багийн код II-4-5 → **IV-2-5** (Topic and Peer Review Allocation хүснэгтийн дагуу).

<!--
Хувилбар гаргахдаа:
## [1.0.0] - 2026-MM-DD
### Нэмсэн / Өөрчилсөн / Засвар / Хассан
[Unreleased]: https://github.com/Tugu8/os-bd1-IV-2-2-/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/Tugu8/os-bd1-IV-2-2-/releases/tag/v1.0.0
-->
