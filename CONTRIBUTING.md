# Ажлын заавар (CONTRIBUTING)

IV-2-2 багийн гишүүд энэ repo дээр хэрхэн хамтран ажиллах дүрэм. [docs/TASKS.md](docs/TASKS.md)-ийн "Git ажлын дүрэм"-ийг дэлгэрүүлсэн.

## 1. Ажлын урсгал

```
main ──●───────────●──────────●── (зөвхөн PR-оор, хамгаалагдсан)
        \         /          /
 kmod    ●──●──●─┘          /
 ui          ●──●──●──●────┘
```

1. `main`-аас өөрийн branch-ийг үүсгэнэ: `git switch -c ui origin/main`
2. Жижиг, утга бүхий commit-ууд хийнэ (§3).
3. PR нээхийн өмнө `main`-ийг өөрийн branch руу нэгтгэж, тестийг ажиллуулна (§5):
   `git fetch origin && git merge origin/main`
4. `git push -u origin <branch>` → GitHub дээр **Pull Request** (`<branch>` → `main`).
5. Өөр **нэг гишүүн** review хийж approve дарсны дараа merge хийнэ (§4). Өөрийнхөө PR-ыг өөрөө merge хийхгүй.
6. Merge хийсний дараа branch-аа устгаж болно. Дараагийн ажлыг `main`-аас шинэ branch-аар эхлүүлнэ.

`main` руу шууд push хийхгүй.

## 2. Branch-ийн нэр

| Branch | Хэн | Хавтас |
|---|---|---|
| `kmod` | B242270047 | `src/kmod/` |
| `ui` | B190910014 | `src/ui/` |
| `prereq` | B210930842 | `src/prereq/`, `docs/Manual.md` (operational) |
| `tests` | B231910003 | `tests/` |
| `report` | B232270108 | `report/` |
| `docs` | B241940099 | `docs/Manual.md` (хэрэглэгчийн), README Quick Start, `review/` |

Түр, жижиг засварт `<хэсэг>-<товч-тайлбар>` нэр өгнө: `kmod-pid-vnr`, `ui-fix-depth`.
Бусдын хавтсанд өөрчлөлт санал болговол тусдаа branch-аар PR нээж, хариуцагчаар review хийлгэнэ.

## 3. Commit мессеж (semantic commit)

```
<хэсэг>: <юу хийснийг тушаах хэлбэрээр, ≤ 72 тэмдэгт>

<яагаад — шаардлагатай бол, 72 тэмдэгтээр мөр таслана>
```

| `<хэсэг>` | Хэзээ |
|---|---|
| `kmod` | `src/kmod/` |
| `ui` | `src/ui/` |
| `prereq` | `src/prereq/`, build орчин |
| `tests` | `tests/` |
| `docs` | README, Manual, TASKS, CONTRIBUTING |
| `report` | `report/` |
| `review` | `review/` |
| `release` | хувилбар гаргах (CHANGELOG, tag) |

Жишээ:

```
kmod: reject out-of-range PIDs
ui: add task hierarchy tree view
tests: add boundary tests for empty and negative input
docs: fill in Quick Start
```

- Тушаах хэлбэр: `add`, `fix`, `remove` гэж бичнэ, `added`, `fixes` гэж бичихгүй. Нэг commit-д нэг утга.
- Build-ийн файл (`*.ko`, `*.o`, `*.mod*`, `Module.symvers`), нууц үг, хувийн өгөгдлийг commit хийхгүй. `.gitignore`-д байгаа.
- AI эсвэл бэлэн код ашигласан бол README-ийн "Бэлэн код, сан, AI ашиглалт" хэсэгт тэмдэглэнэ.

## 4. Pull Request ба review

PR-ийн тайлбарт:
- **Юу:** юу өөрчлөгдсөн, аль хэсэг.
- **Яаж шалгасан:** ажиллуулсан команд, үр дүн (тестийн тоо, screenshot).
- **Нөлөө:** бусад хэсэгт нөлөөлөх эсэх (жнь `/proc/pid`-ийн формат өөрчлөгдвөл UI, тестэд).

Review хийгч шалгах зүйлс:
- [ ] Цэвэр хуулбар дээр build болж ажиллаж байна (`make`, `insmod`, `rmmod`).
- [ ] Тест давж байна (§5).
- [ ] Kernel код: `copy_from_user`, `kmalloc` алдааг шалгасан, `kfree` хийсэн; NULL task → 0 байт; RCU/lock зөв.
- [ ] Бусад хэсгийн интерфейсийг эвдээгүй. `/proc/pid`-ийн формат өөрчлөгдвөл `src/ui/README.md`-ийн гэрээ ба `contract_check.py`-тэй тулгасан.
- [ ] Commit мессеж §3-ийн дагуу бичигдсэн, илүү файл ороогүй.

Санал байвал GitHub-ийн "Request changes" эсвэл мөрийн comment ашиглана. Засвараа мөн тэр branch-д push хийнэ.

## 5. PR-ийн өмнө ажиллуулах тест

```bash
(cd src/kmod && make) && sudo insmod src/kmod/pid.ko
bash tests/basic/test_basic.sh
bash tests/boundary/test_boundary.sh
python3 -m unittest src/ui/tests/test_api.py
python3 src/ui/contract_check.py
sudo rmmod pid
```

## 6. Хувилбар гаргах (Semantic Versioning)

Хувилбарын дугаар `vMAJOR.MINOR.PATCH` ([semver.org](https://semver.org/lang/mn/)):

| Нэмэх | Хэзээ | Жишээ |
|---|---|---|
| MAJOR | Илгээлт, эсвэл `/proc/pid`-ийн формат нийцгүй өөрчлөгдөх | `v1.0.0` — БД1, `v2.0.0` — БД2 |
| MINOR | Шинэ боломж, хуучныг эвдэхгүй | `v1.1.0` — UI-д шинэ дүрслэл |
| PATCH | Алдааны засвар | `v1.0.1` — review-ийн засвар |

БД1-ийн өмнөх туршилтын хувилбарт `v0.x.y` эсвэл `v1.0.0-rc.1` ашиглана.

Гаргах алхам (B242270047, B241940099 — 9-р долоо хоног):
1. Бүх PR merge хийгдэж, `main` дээр §5-ийн тест давна.
2. `CHANGELOG.md`-ийн `[Unreleased]` хэсгийг `[1.0.0] - YYYY-MM-DD` болгож PR (`release: v1.0.0`) нээнэ.
3. Merge хийсний дараа tag тавина:
   ```bash
   git switch main && git pull
   git tag -a v1.0.0 -m "BD1 submission"
   git push origin v1.0.0
   ```
4. GitHub → **Releases → Draft a new release** → `v1.0.0` tag, CHANGELOG-ийн хэсгийг тайлбарт хуулж, `Report.pdf`, `Manual.pdf`-ийг хавсаргана.
5. Release-ийн холбоосыг Teams-ийн "БД1 - Submissions and Reviews" пост-д оруулна.

## 7. Тайлан ба manual-д оруулах хэсэг

Хэрэгжилтийн хэсгийг тухайн кодыг бичсэн гишүүн өөрөө бичиж, `report/` (B232270108), `docs/Manual.md` (B241940099, B210930842)-д өгнө. Жишээ нь UI-ийнх: [src/ui/REPORT_UI.md](src/ui/REPORT_UI.md).
