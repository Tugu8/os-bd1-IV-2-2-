# Шүүмж: IV-2-2 багийн хийсэн харилцан шүүмжүүд

| Шүүмжилсэн баг | Төсөл | Үндэслэл | Review PDF |
|---|---|---|---|
| V-1-13 | Banker's Algorithm | Хуваарилалтын PDF §3, 13-р мөр (Гүйцэтгэх V-1-13, Шүүмжлэх IV-2-2) | `IV-2-2_Review_V-1-13.pdf` |
| IV-2-5 | Sudoku Solution Validator | Багшийн өгсөн нэмэлт даалгавар | `IV-2-2_Review_IV-2-5.pdf` |

Манай ажлыг IV-2-5 шүүмжилнэ (хуваарилалтын §3, 2-р мөр).

## Файлууд

| Файл | Агуулга |
|---|---|
| `IV-2-2_Review_<код>.pdf` | Илгээх Review PDF (Нүүр + 9 хэсэг + Хавсралт A) |
| `IV-2-2_Review_<код>.md` | PDF-ийн эх текст |
| `<код>_make_test_log.txt` | `make` ба `make test`-ийн гаралт |
| `images/v113_*.png`, `images/iv25_*.png` | UI-аас авсан screenshot |
| `build_review.py` | Markdown-ийг LaTeX болгоно (`report/md2tex.py`-г ашиглана) |

PDF-ийг дахин үүсгэх:

```
python3 review/build_review.py V-1-13      # эсвэл IV-2-5
cd review && xelatex IV-2-2_Review_V-1-13.tex && xelatex IV-2-2_Review_V-1-13.tex
```

## Reply: V-1-13

```
Шүүмжлэгч код: IV-2-2
Шүүмжилсэн код: V-1-13
Manual-ийн дагуу WSL2 (Debian 13, gcc 14.2, Python 3.13)-д Build/Run хийв. make test 62/62, 25/25, 8/8 давж, номын §8.6.3.3, §8.6.1, §8.7.2 жишээнүүд бүгд давтагдсан. Нэмэлт 10 тестээс 9 нь тэнцсэн; UI-ийн Apply товч алдаа өгсөн үед төлөвийг хэсэгчлэн өөрчилж, thread-ийн Allocation устдаг асуудал илэрсэн. Мөн Release tag байхгүй, илгээсэн PDF репоны одоогийн кодтой таарахгүй байна. Дэлгэрэнгүйг Review PDF-ээс үзнэ үү.
Хавсралт: IV-2-2_Review_V-1-13.pdf
```

## Reply: IV-2-5

```
Шүүмжлэгч код: IV-2-2
Шүүмжилсэн код: IV-2-5
Manual-ийн дагуу WSL2 (Debian 13, gcc 14.2, Python 3.13)-д Build/Run хийв. make test нь TSan-ийн "unexpected memory mapping" алдаагаар унасан ч setarch -R-ээр ASLR унтраахад 2170/2170 давсан. main дээрх нэмэлт 12 тест (латин квадрат, хоосон самбар, буруу файл, API хамгаалалт) бүгд тэнцсэн, Dashboard C-ийн үр дүнтэй таарч байна. Гол асуудал: v1.0.0 Release main-аас 69 commit хоцорсон бөгөөд тэнд -b горимд буруу Sudoku-д код 0 буцаах, -s 1,1,6junk-ийг хүлээн авах алдаа үлдсэн; репоны docs/ PDF нь 2 хуудас ноорог. Дэлгэрэнгүйг Review PDF-ээс үзнэ үү.
Хавсралт: IV-2-2_Review_IV-2-5.pdf
```
