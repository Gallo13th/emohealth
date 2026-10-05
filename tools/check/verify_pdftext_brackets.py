#!/usr/bin/env python3
"""守卫：`tools/pdftext.py` 必须能取出**含方括号的 TJ 数组**里的文字。

为什么要这条守卫
================
2026-10-04 发现：DSM-5-TR L1 第 23 题的题面在数据层里被截断成
`…inhalants or solvents (like glue), or m`，而**原文是完整的**：

    23. Using any of the following medicines ON YOUR OWN, that is, without a
    doctor's prescription, in greater amounts or longer than prescribed
    [e.g., … or methamphetamine (like speed)]?

根因**不在提取脚本的业务逻辑**，在共享库 `tools/pdftext.py` 的词法层：
它的 TJ 正则写的是

    \\[((?:\\\\.|[^\\\\\\[\\]])*)\\]\\s*TJ

字符类把 `[` `]` 排除在外，所以当**字面串内部出现未转义的方括号**
（本题的 `[e.g., …]?`）时，整个 `[…]TJ` 匹配失败——`re.finditer` 随后
从串内的 `[` 处重新起步，只匹配到后半截。结果是**静默丢字**：不报错、
不产生 `\\ufffd`、不计数。这类缺陷最危险，因为它长得像「原文就这么短」。

这条守卫把「已知含方括号字面串的题面」钉死，任何词法层回退都会立刻失败。

用法：
    python tools/check/verify_pdftext_brackets.py          # 断言 + 摘要
    python tools/check/verify_pdftext_brackets.py --stats  # 只打统计（不判退出码）
"""

from __future__ import annotations

import os
import sys

import io
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
sys.path.insert(0, os.path.join(ROOT, "tools"))
from pdftext import PdfDoc, layout_lines  # noqa: E402

# 已知含「字面串内未转义方括号」的题面：抽取结果必须逐字包含这些片段
CASES = [
    {
        "pdf": "archive/scales/DSM5TR-L1/manual.pdf",
        "must_contain": [
            # 方括号（字面串内未转义）——曾经整段被丢，题面截断成 "…or m"
            "in greater amounts or longer than prescribed [e.g.,",
            "or methamphetamine (like speed)]?",
            # 空白段——曾经被丢，词被粘起来
            "23. Using any of the following medicines ON YOUR OWN",
            "22. Smoking any cigarettes",
        ],
        "why": "L1 第 22/23 题：题面含 [e.g., … ]? 与独立的空格段",
    },
]

# 只打统计、不做断言的历史 PDF（用于人工比较抽取规模有无回退）
STATS = [
    "archive/scales/DSM5TR-L1/manual.pdf",
    "archive/scales/DSM5TR-L2-Sleep/manual.pdf",
    "archive/scales/DSM5TR-L2-Mania/manual.pdf",
    "archive/scales/DSM5TR-L2-Depression/manual.pdf",
    "archive/scales/PID-5/manual.pdf",
    "archive/norms/promis/crosscheck-rimed-2021-appendix-a.pdf",
]


def extract_text(rel: str) -> str:
    doc = PdfDoc.load(os.path.join(ROOT, rel))
    out = []
    for runs in doc.text_runs():
        for row in layout_lines(runs):
            out.append(row["text"])
    return "\n".join(out)


def main() -> int:
    stats_only = "--stats" in sys.argv

    print("── 抽取规模（用于比较词法层改动前后有无回退）──")
    for rel in STATS:
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            print(f"  (缺) {rel}")
            continue
        txt = extract_text(rel)
        print(f"  {len(txt):7d} 字  {rel}")

    if stats_only:
        return 0

    print("\n── 断言：字面串内的方括号必须被取出 ──")
    bad = 0
    for c in CASES:
        txt = extract_text(c["pdf"])
        for needle in c["must_contain"]:
            if needle in txt:
                print(f"  ✅ {c['pdf']}  含 {needle[:56]!r}")
            else:
                print(f"  ❌ {c['pdf']}  缺 {needle[:56]!r}   （{c['why']}）")
                bad += 1
    print(f"\n{'✅ 通过' if not bad else f'❌ {bad} 条失败'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
