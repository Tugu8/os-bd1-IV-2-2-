#!/bin/bash
# report/IV-2-2_BD1_Report.pdf ба docs/IV-2-2_Manual.pdf-ийг дахин үүсгэнэ.
#   bash report/build_pdfs.sh
# Шаардлага: sudo apt install texlive-xetex texlive-latex-extra fonts-dejavu python3
set -euo pipefail
cd "$(dirname "$0")"

python3 md2tex.py ../docs/Manual.md IV-2-2_Manual.tex
for doc in IV-2-2_BD1_Report IV-2-2_Manual; do
  for _ in 1 2; do                     # 2 удаа — агуулгын хуудасны дугаар
    xelatex -interaction=nonstopmode -halt-on-error "$doc.tex" > /dev/null \
      || { tail -30 "$doc.log"; exit 1; }
  done
  echo "$doc.pdf: $(pdfinfo "$doc.pdf" 2>/dev/null | awk '/^Pages/ {print $2}') хуудас"
done
mv IV-2-2_Manual.pdf ../docs/IV-2-2_Manual.pdf
rm -f ./*.aux ./*.log ./*.out ./*.toc IV-2-2_Manual.tex
echo "→ report/IV-2-2_BD1_Report.pdf, docs/IV-2-2_Manual.pdf"
