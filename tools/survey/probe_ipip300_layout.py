#!/usr/bin/env python3
"""探明 IPIP300.dat 的定宽字段布局。

背景：归档里 ``raw/IPIP300.dat``（98 MB）是 Johnson (2005) 的 **IPIP-NEO-300
全量作答**（N=20,993），正是「20 万人常模」这一说法的真实出处。
要把它算成常模，必须先能可靠地切开每题。

格式线索（来自 ``DAT300_codebook.doc`` 抽出的可读片段）：
  · 字段定宽；开头是 CASE、若干人口学字段、国家名，然后是 **300 道题**
  · 每题 1 位（作答 1–5）
  · codebook 有一处**已勘误**：CASE 字段原记为 F6，实际是 F8；数据文件里
    「前两个空列已被去掉」，文档已按新格式描述

所以本脚本不猜：把同一时刻不同行的**同一列位置**对齐，看哪些列恒为 0–5 的
数字（题项列），再核对「连续 300 个这样的列」出现在哪一段。
"""

from __future__ import annotations

import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
DATA = os.path.join(ROOT, "archive", "datasets", "osf-johnson", "raw", "IPIP300.dat")

N_SAMPLE = 300


def main() -> int:
    with open(DATA, encoding="latin-1") as fh:
        lines = [ln.rstrip("\r\n") for ln in fh]
    print(f"读入 {len(lines)} 行")
    lens = Counter(len(x) for x in lines)
    print(f"行长分布（前 5）：{lens.most_common(5)}")
    sample = [x for x in lines if len(x) == lens.most_common(1)[0][0]][:N_SAMPLE]
    print(f"用众数长度的 {len(sample)} 行做逐列统计\n")

    width = max(len(x) for x in sample)
    digit_cols = []
    for c in range(width):
        vals = [x[c] for x in sample if c < len(x)]
        if vals and all(v.isdigit() for v in vals) and set(vals) <= set("012345"):
            digit_cols.append(c)
    print(f"恒为 0–5 数字的列共 {len(digit_cols)} 个")
    # 找最长的连续段
    best = cur = []
    for c in digit_cols:
        if cur and c == cur[-1] + 1:
            cur.append(c)
        else:
            cur = [c]
        if len(cur) > len(best):
            best = list(cur)
    print(f"最长连续数字段：列 {best[0]}–{best[-1]}（{len(best)} 列）"
          if best else "没找到连续段")
    print(f"→ 题项数 {len(best)}（期望 300）")
    print(f"\n前 3 行的前 90 列（▁ 代表非数字列）：")
    for x in sample[:3]:
        vis = "".join(ch if ch.isdigit() else "·" for ch in x[:90])
        print("  ", vis)
    return 0 if len(best) == 300 else 1


if __name__ == "__main__":
    sys.exit(main())
