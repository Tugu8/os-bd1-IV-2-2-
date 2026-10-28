#!/usr/bin/env python3
"""
docs/Manual.md → LaTeX (XeLaTeX) — нэмэлт сангүй, энэ repo-ийн Markdown-д хангалттай.

    python3 report/md2tex.py docs/Manual.md report/IV-2-2_Manual.tex

Дэмждэг: #–####, ``` блок, | хүснэгт |, - / 1. жагсаалт, > ишлэл, ![зураг](зам),
**тод**, `код`, [текст](url), <url>, <kbd>, <!-- тайлбар -->, ---.
"""
import os
import re
import sys
from pathlib import Path

SPECIAL = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
           "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}


def esc(t):
    return "".join(SPECIAL.get(c, c) for c in t)


def inline(t):
    """Markdown inline → LaTeX. Кодыг эхэлж хамгаалж, бусдыг escape хийнэ."""
    t = re.sub(r"<kbd>(.*?)</kbd>", lambda m: "\x00K" + m.group(1) + "\x00", t)
    # **тод** нь `код`-ийг агуулж болох тул тэмдэглэгээг эхэлж \x02 болгоно
    parts = re.split(r"(`[^`]+`)", t)
    parts = [x if x.startswith("`") else x.replace("**", "\x02") for x in parts]
    # *налуу* мөн `код` агуулж болно — ганц *-ийг \x03 болгоно
    parts = [x if x.startswith("`") else re.sub(r"(?<![\w*])\*(?=\S)|(?<=\S)\*(?![\w*])", "\x03", x) for x in parts]
    out = []
    for p in parts:
        if p.startswith("`") and p.endswith("`") and len(p) > 1:
            body = p[1:-1].replace("}", ")").replace("{", "(").replace("⤓", "↓")
            # урт зам, нэрийг хүснэгтийн нарийн нүдэнд / _ - дараа таслах боломжтой болгоно
            pieces = re.split(r"(?<=[/_\-.])", body) if len(body) > 16 else [body]
            out.append(r"\allowbreak{}".join(r"\code{" + x + "}" for x in pieces if x))
            continue
        p = re.sub(r"<(https?://[^>]+)>", r"[\1](\1)", p)
        links = []

        def keep(m):
            links.append(m)
            return f"\x01{len(links) - 1}\x01"
        p = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", keep, p)
        p = esc(p)
        p = re.sub(r"\x00K(.*?)\x00", r"\\kbd{\1}", p)

        def link(m):
            g = links[int(m.group(1))]
            text, url = g.group(1), g.group(2)
            if url.startswith("http"):
                return r"\href{" + url.replace("%", r"\%").replace("#", r"\#") + "}{" + esc(text) + "}"
            return esc(text)
        p = re.sub(r"\x01(\d+)\x01", link, p)
        out.append(p)
    t = re.sub("\x02(.*?)\x02", r"\\textbf{\1}", "".join(out), flags=re.S).replace("\x02", "")
    return re.sub("\x03(.*?)\x03", r"\\emph{\1}", t, flags=re.S).replace("\x03", "*")


def table(rows):
    # "\|" нь нүдний доторх | тэмдэгт, хуваагч биш
    cells = [[c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", r.strip().strip("|"))]
             for r in rows]
    cells = [r for r in cells if not all(re.fullmatch(r":?-{2,}:?", c) for c in r)]
    n = max(len(r) for r in cells)
    widths = [max(len(r[i]) if i < len(r) else 0 for r in cells) for i in range(n)]
    total = sum(min(w, 60) for w in widths) or 1
    fr = [max(0.12, min(w, 60) / total) for w in widths]
    fr = [f / sum(fr) for f in fr]                 # нийлбэр 1, баганын зай (2·tabcolsep)-ийг хасна
    cols = " ".join(f">{{\\raggedright\\arraybackslash}}p{{\\dimexpr {f:.3f}\\linewidth - 2\\tabcolsep\\relax}}" for f in fr)
    lines = [r"{\small\begin{longtable}{" + cols + "}", r"\toprule"]
    for k, r in enumerate(cells):
        r = r + [""] * (n - len(r))
        row = " & ".join((r"\textbf{" + inline(c) + "}") if k == 0 else inline(c) for c in r) + r" \\"
        lines.append(row)
        if k == 0:
            lines += [r"\midrule", r"\endhead"]
    lines += [r"\bottomrule", r"\end{longtable}}"]
    return "\n".join(lines)


def convert(md, base, outdir):
    out, i = [], 0
    lines = re.sub(r"<!--.*?-->", "", md, flags=re.S).splitlines()
    title = None
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            # listings XeLaTeX дээр кирилл үсгийн дарааллыг эвддэг ("БД1-ийн" → "БДийн1-") тул fvextra
            out.append(r"\begin{Verbatim}" + "\n" + "\n".join(lines[i + 1:j]) + "\n" + r"\end{Verbatim}")
            i = j + 1
            continue
        if ln.lstrip().startswith("|"):
            j = i
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                j += 1
            out.append(table(lines[i:j]))
            i = j
            continue
        m = re.match(r"^(#{1,4})\s+(.*)", ln)
        if m:
            lvl, text = len(m.group(1)), m.group(2)
            if lvl == 1 and title is None:
                title = text
            else:
                cmd = {1: "section", 2: "section", 3: "subsection", 4: "subsubsection"}[lvl]
                out.append(f"\\{cmd}*{{{inline(text)}}}\\addcontentsline{{toc}}{{{cmd}}}{{{inline(text)}}}")
            i += 1
            continue
        m = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)", ln.strip())
        if m:
            path = (base / m.group(2)).resolve()
            out.append(r"\begin{center}\includegraphics[width=0.92\linewidth,height=0.42\textheight,keepaspectratio]{"
                       + os.path.relpath(path, outdir).replace(os.sep, '/') + r"}\\[2pt]{\small " + inline(m.group(1)) + r"}\end{center}")
            i += 1
            continue
        if re.match(r"^\s*([-*]|\d+\.)\s+", ln):
            kind = "enumerate" if re.match(r"^\s*\d+\.", ln) else "itemize"
            items = []
            while i < len(lines) and (re.match(r"^\s*([-*]|\d+\.)\s+", lines[i]) or
                                      (lines[i].startswith("   ") and lines[i].strip() and items)):
                if re.match(r"^\s*([-*]|\d+\.)\s+", lines[i]):
                    items.append(re.sub(r"^\s*([-*]|\d+\.)\s+", "", lines[i]))
                else:
                    items[-1] += " " + lines[i].strip()
                i += 1
            out.append(f"\\begin{{{kind}}}[nosep]\n" + "\n".join(r"\item " + inline(t) for t in items)
                       + f"\n\\end{{{kind}}}")
            continue
        if ln.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].startswith(">"):
                buf.append(lines[i].lstrip("> ").rstrip())
                i += 1
            out.append(r"\begin{note}" + inline(" ".join(buf)) + r"\end{note}")
            continue
        if re.fullmatch(r"\s*-{3,}\s*", ln):
            out.append(r"\medskip\hrule\medskip")
            i += 1
            continue
        buf = []
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#|```|\||>|!\[|\s*([-*]|\d+\.)\s)", lines[i]):
            # мөрийн төгсгөлийн 2 зай = Markdown-ийн мөр таслалт
            buf.append(lines[i].strip() + ("\x03" if lines[i].endswith("  ") else ""))
            i += 1
        if buf:
            out.append(inline(" ".join(buf)).replace("\x03", r"\\"))
        else:
            i += 1
    return title or "Manual", "\n\n".join(out)


PREAMBLE = r"""\documentclass[11pt,a4paper]{article}
\usepackage{fontspec}
\setmainfont{DejaVu Serif}
\setsansfont{DejaVu Sans}
\setmonofont{DejaVu Sans Mono}[Scale=0.82]
\newfontfamily\symfont{DejaVu Sans}
\usepackage[margin=2cm]{geometry}
\usepackage{tikz,graphicx,xcolor,enumitem,booktabs,longtable,array,listings,hyperref,titlesec}
\usepackage[most]{tcolorbox}
\titleformat{\section}{\Large\bfseries}{}{0em}{}
\titleformat{\subsection}{\large\bfseries}{}{0em}{}
\setlength{\parskip}{0.4em}\setlength{\parindent}{0pt}\sloppy\setlength{\emergencystretch}{3em}
\hypersetup{colorlinks, linkcolor=blue!50!black, urlcolor=blue!50!black}
\renewcommand{\contentsname}{Агуулга}
\lstset{basicstyle=\ttfamily\small, frame=single, framerule=0.3pt, rulecolor=\color{gray!60},
  backgroundcolor=\color{gray!6}, columns=fullflexible, keepspaces=true, breaklines=true,
  extendedchars=true, literate={→}{{$\rightarrow$}}1}
\usepackage{fvextra}
\fvset{frame=single, framerule=0.3pt, rulecolor=\color{gray!60}, fontsize=\small, breaklines=true, breaksymbolleft={}}
\DeclareRobustCommand{\code}[1]{{\ttfamily\detokenize{#1}}}
\newcommand{\kbd}[1]{\tikz[baseline=(k.base)]\node[draw,rounded corners=1.5pt,inner sep=1.5pt,font=\small\ttfamily](k){#1};}
\newtcolorbox{note}{colback=blue!3, colframe=blue!30!black, boxrule=0.3pt, left=4pt, right=4pt, top=2pt, bottom=2pt}
% DejaVu Serif-д байхгүй тэмдэгтүүдийг DejaVu Sans-аас
\catcode`⚠=\active \def⚠{{\symfont\char"26A0}}
\catcode`✔=\active \def✔{{\symfont\char"2714}}
\catcode`✖=\active \def✖{{\symfont\char"2716}}
\catcode`ℹ=\active \defℹ{{\symfont\char"2139}}
\catcode`●=\active \def●{{\symfont\char"25CF}}
\catcode`⤓=\active \def⤓{{\rmfamily\char"2913}}
\begin{document}
"""


def main(src, dst):
    src, dst = Path(src), Path(dst)
    title, body = convert(src.read_text(encoding="utf-8"), src.parent, dst.parent.resolve())
    logo = os.path.relpath((src.parent / "images" / "must_logo.png").resolve(), dst.parent.resolve()).replace(os.sep, '/')
    head = (r"\begin{titlepage}\centering\vspace*{0.4cm}"
            r"{\large ШИНЖЛЭХ УХААН ТЕХНОЛОГИЙН ИХ СУРГУУЛЬ\\ Мэдээлэл, Холбооны Технологийн Сургууль\par}\vspace{0.6cm}"
            r"\includegraphics[height=2.8cm]{" + logo + r"}\par\vspace{0.8cm}"
            r"{\large F.CSM302 Үйлдлийн систем, Бие даалт 1\par}\vspace{1cm}"
            r"{\Huge\bfseries " + inline(title) + r"\par}\vspace{0.8cm}{\Large IV-2-2: Linux Kernel Module for Task Information\par}"
            r"\vspace{1cm}{\large Хэрэглэгчийн ба operational заавар\par}\vfill"
            r"\url{https://github.com/Tugu8/os-bd1-IV-2-2-}\par\vspace{0.5cm}{2026 оны 10-р сар\par}\end{titlepage}"
            "\n\\tableofcontents\n\\newpage\n")
    dst.write_text(PREAMBLE + head + body + "\n\\end{document}\n", encoding="utf-8")
    print(f"{src} → {dst}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
