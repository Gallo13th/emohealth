#!/usr/bin/env python3
"""查交叉核对来源（Glasgow 学位论文）里印出了哪些 PROMIS 转换表。

来源：https://theses.gla.ac.uk/86182/1/2026BrockPhD.pdf
（第三方文献，用于**独立复核**官方手册的转换表，不单独作为权威来源）
"""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
sys.path.insert(0, os.path.join(ROOT, "tools"))
from pdftext import PdfDoc, layout_lines  # noqa: E402

pdf = os.path.join(ROOT, "archive", "norms", "promis",
                   "crosscheck-gla-2026-brock-phd.pdf")


def main() -> int:
    doc = PdfDoc.load(pdf)
    pages = []
    for i, runs in enumerate(doc.text_runs()):
        t = re.sub(r"\s+", " ", " ".join(r["text"] for r in layout_lines(runs)))
        pages.append(t)
    print(f"流数 {len(pages)}")
    print("\n=== 含『Conversion Table』的流 ===")
    for i, t in enumerate(pages):
        for m in re.finditer(r"[A-Z][A-Za-z \-]{2,40}(?:Short Form )?Conversion Table", t):
            print(f"  [流{i}] {m.group(0)}")
    print("\n=== 含 T-Score 且有成排数字的流 ===")
    for i, t in enumerate(pages):
        if not re.search(r"T-?\s?Score", t, re.I):
            continue
        nums = re.findall(r"\b\d{1,2}\s+\d{2}\.\d\b", t)
        if len(nums) >= 5:
            print(f"  [流{i}] {len(nums)} 组成对数字，前 6 组：{nums[:6]}")
            j = t.find("T-Score")
            print(f"      片段：{t[max(0,j-120):j+300]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
