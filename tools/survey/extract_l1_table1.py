#!/usr/bin/env python3
"""提取 DSM-5-TR Level 1 手册的 **Table 1**：13 个域 → 门槛 → 对应 Level 2 量表。

这张表就是**链路的定义**：Level 1 是筛查，触发后转对应 Level 2 做细评；
而 PID-5 与之并行（人格障碍特质维度）。必须从原文逐行取，不能凭印象写。
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


def main() -> int:
    pdf = os.path.join(ROOT, "archive", "scales", "DSM5TR-L1", "manual.pdf")
    doc = PdfDoc.load(pdf)
    joined = ""
    for runs in doc.text_runs():
        joined += " " + " ".join(r["text"] for r in layout_lines(runs))
    t = re.sub(r"([a-z])([A-Z])", r"\1 \2", joined)
    t = re.sub(r"\s+", " ", t)

    i = t.find("Table 1:")
    if i < 0:
        print("✗ 找不到 Table 1")
        return 1
    seg = t[i:i + 3000]
    print("=== Table 1 原文（截断 3000 字）===")
    print(seg)
    print()
    print("=== 逐域抽取 ===")
    # 罗马数字 + 域名 + 门槛 + LEVEL 2 名称
    pat = re.compile(
        r"(XIII|XII|XI|IX|VIII|VII|VI|IV|V|III|II|X|I)\.\s*"
        r"([A-Z][A-Za-z ,\-]{2,40}?)\s+"
        # ⚠️ 原文里有 `Mildor greater`（缺空格）与 `LEVEL2—`（缺空格）这类排版粘连，
        #    严格匹配会漏掉 IX.Memory 与 XIII.Substance Use 两行。
        r"(Mild\s*or greater|Slight\s*or greater|Severe\s*or greater|Moderate\s*or greater)\s+"
        r"(.{0,160}?)(?=(?:XIII|XII|XI|IX|VIII|VII|VI|IV|V|III|II|X|I)\.\s*[A-Z]|The PROMIS|$)")
    n = 0
    for m in pat.finditer(seg):
        n += 1
        dom, thr, l2 = m.group(2).strip(), m.group(3), m.group(4).strip()
        l2 = re.sub(r"\s+", " ", l2)
        l2 = re.sub(r"(\d)\s*$", "", l2)      # 去掉行末的表格脚注编号
        print(f"  {m.group(1):5} {dom:26} {thr:18} {l2[:110]}")
    print(f"\n共抽到 {n} 个域（应为 13）")
    return 0 if n == 13 else 1


if __name__ == "__main__":
    sys.exit(main())
