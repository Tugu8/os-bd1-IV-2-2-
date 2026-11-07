#!/usr/bin/env python3
"""
review/IV-2-2_Review_<код>.md -> .tex (report/md2tex.py-ийн хөрвүүлэгчийг ашиглана).

    python3 review/build_review.py V-1-13
    python3 review/build_review.py IV-2-5
    cd review && xelatex IV-2-2_Review_<код>.tex && xelatex IV-2-2_Review_<код>.tex
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "report"))
import md2tex  # noqa: E402

TARGETS = {
    "V-1-13": ("Banker's Algorithm (Бүлэг 8, Deadlocks), Resource graph",
               "https://github.com/Energyshifter8/V-1-13-Bankers-Algorithm",
               "2026 оны 11 дүгээр сарын 1"),
    "IV-2-5": ("Sudoku Solution Validator (Бүлэг 4, Threads), Sudoku board",
               "https://github.com/sumya4748-afk/Sudoku-Thread-Validator",
               "2026 оны 11 дүгээр сарын 2"),
}

COVER = r"""\begin{titlepage}\centering\vspace*{0.4cm}
{\large\bfseries ШИНЖЛЭХ УХААН ТЕХНОЛОГИЙН ИХ СУРГУУЛЬ\\ МЭДЭЭЛЭЛ, ХОЛБООНЫ ТЕХНОЛОГИЙН СУРГУУЛЬ\par}
\vspace{1.4cm}\includegraphics[height=3.4cm]{LOGO}\par\vspace{1.6cm}
{\Huge\bfseries БИЕ ДААЛТ 1\\[4pt] ХАРИЛЦАН ШҮҮМЖ\par}\vspace{0.5cm}
{\large\bfseries Үйлдлийн систем /F.CSM302/\par}\vspace{2cm}
\begin{flushleft}\renewcommand{\arraystretch}{1.3}
\begin{tabular}{@{}>{\raggedright\arraybackslash}p{5.2cm} >{\raggedright\arraybackslash}p{11cm}@{}}
\textbf{Шүүмжлэгч баг:} & IV-2-2\\
\textbf{Шүүмжилсэн баг:} & CODE\\
\textbf{Төсөл:} & PROJECT\\
\textbf{Шүүмжилсэн репо:} & \url{REPO}\\
\textbf{Хичээл заасан багш:} & Г.Ганбат /F.CS10/\\
\textbf{Шүүмжлэгч гишүүд:} & Б.Төгөлдөр /B242270047/\\
 & С.Пүрэвтулга /B241940099/\\
 & Б.Билгүүн /B190910014/\\
 & Л.Тэмүүлэн /B210930842/\\
 & Ч.Алтангэрэл /B231910003/\\
 & Л.Пүрэв-очир /B232270108/\\
\end{tabular}\end{flushleft}\vfill
\begin{flushleft}\begin{tabular}{@{}p{5.2cm} l@{}}\textbf{Огноо:} & DATE\\\end{tabular}\end{flushleft}
\end{titlepage}
\tableofcontents
\newpage
"""


def main(code):
    project, repo, date = TARGETS[code]
    src = HERE / f"IV-2-2_Review_{code}.md"
    dst = HERE / f"IV-2-2_Review_{code}.tex"
    _, body = md2tex.convert(src.read_text(encoding="utf-8"), HERE, HERE)
    logo = os.path.relpath(HERE.parent / "docs" / "images" / "must_logo.png", HERE).replace(os.sep, "/")
    cover = (COVER.replace("LOGO", logo).replace("CODE", code).replace("PROJECT", md2tex.inline(project))
             .replace("REPO", repo).replace("DATE", date))
    dst.write_text(md2tex.PREAMBLE + cover + body + "\n\\end{document}\n", encoding="utf-8")
    print(f"{src.name} -> {dst.name}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "V-1-13")
