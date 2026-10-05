#!/usr/bin/env python3
"""逐册提取 DSM-5-TR Level 2 的**判读口径**，看哪些自足、哪些需外部来源。

为什么先做这一步
================
用户要求「逐页对 L2 做常模」。但 L2 八册的计分口径**互不相同**，不能套同一个方法：

  册              题数  量表      手册可能自带
  ────────────────────────────────────────────────
  Depression       8   1–5       PROMIS：T 分（需转换表）
  Anger            5   1–5       PROMIS：T 分
  Anxiety          7   1–5       PROMIS：T 分
  Sleep            8   1–5       PROMIS：T 分
  Somatic         15   0–2       PHQ-15：求和 + 严重度分带
  Mania            5   0–4       ASRM：求和 + **Interpretation Table**
  Repetitive       5   0–4       求和 + 分界值（手册提过 ≥8）
  Substance       10   0–4       求和 + 风险分级

按项目原则：**归档里有的口径就用归档的**，只有归档确实没有才去外部取。
所以先逐册把原文里的 scoring/interpretation 段抽出来看清。

⚠️ 这些 PDF 的文本版式混乱（词间粘连、表格错位），所以只**打印原文供人判断**，
   不自动解析成数值——解析错了会变成界面上一个看不出错的假常模。
"""

from __future__ import annotations

import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
sys.path.insert(0, os.path.join(ROOT, "tools"))
from pdftext import PdfDoc, layout_lines  # noqa: E402

PATS = [
    (r"Scoring and Interpretation", 800),
    (r"[Ii]nterpretation [Tt]able", 700),
    (r"raw score", 420),
    (r"T-?\s?Score", 300),
    (r"8 or higher|score of \d+ or (?:higher|greater)", 260),
    (r"cut[- ]?off|severity|threshold", 300),
]


def text_of(pdf: str) -> str:
    doc = PdfDoc.load(pdf)
    parts = []
    for runs in doc.text_runs():
        parts.extend(r["text"] for r in layout_lines(runs))
    t = " ".join(parts)
    t = re.sub(r"([a-z])([A-Z])", r"\1 \2", t)
    return re.sub(r"\s+", " ", t)


def main() -> int:
    dirs = sorted(glob.glob(os.path.join(ROOT, "archive", "scales", "DSM5TR-L2-*")))
    only = sys.argv[1:] or None
    for d in dirs:
        code = os.path.basename(d)
        if only and code not in only:
            continue
        pdf = os.path.join(d, "manual.pdf")
        if not os.path.exists(pdf):
            continue
        t = text_of(pdf)
        print("=" * 78)
        print(f"── {code}")
        seen = set()
        for pat, span in PATS:
            for m in re.finditer(pat, t):
                seg = re.sub(r"\s+", " ", t[m.start():m.start() + span]).strip()
                k = seg[:56]
                if k in seen or len(seg) < 50:
                    continue
                seen.add(k)
                print(f"\n  [{pat}]")
                print("   ", seg[:span])
                break
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
