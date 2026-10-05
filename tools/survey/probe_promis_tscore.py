#!/usr/bin/env python3
"""确认 PROMIS 四册里到底有没有 raw → T 的对照表。

手册的 Scoring 段写着「Next, the T-score table should be used to identify the
T-score associated with the raw score」——但这句可能指**别的文档**里的表。
所以要逐流查：有没有一个流里同时出现「多个 raw 值 + 对应 T 值」的成对结构。

判据：同一流里出现 ≥6 个形如「整数后面跟 2 位小数」的成对数字，
或明确含 "T-score table" 标题且紧随成排数字。
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

CODES = ["DSM5TR-L2-Depression", "DSM5TR-L2-Anger",
         "DSM5TR-L2-Anxiety", "DSM5TR-L2-Sleep"]


def main() -> int:
    for code in CODES:
        p = os.path.join(ROOT, "archive", "scales", code, "manual.pdf")
        doc = PdfDoc.load(p)
        streams = []
        for runs in doc.text_runs():
            t = re.sub(r"\s+", " ", " ".join(r["text"] for r in layout_lines(runs)))
            streams.append(t)
        # 判据一：明确标题
        titled = [i for i, t in enumerate(streams)
                  if re.search(r"T-?score\s*table|T\s?Score\s*Table", t, re.I)]
        # 判据二：成对数字（raw 整数 + T 两位小数）≥6 组
        pairs = []
        for i, t in enumerate(streams):
            found = re.findall(r"\b\d{1,2}\s+\d{2}\.\d\b", t)
            if len(found) >= 6:
                pairs.append((i, len(found)))
        # 判据三：T 值区间 20–80 的密集出现
        tvals = []
        for i, t in enumerate(streams):
            v = [float(x) for x in re.findall(r"\b([2-7]\d\.\d)\b", t)]
            if len(v) >= 8:
                tvals.append((i, len(v)))
        print(f"── {code}")
        print(f"   流数 {len(streams)}")
        print(f"   含『T-score table』字样的流：{titled or '无'}")
        print(f"   含 ≥6 组「raw T」成对数字的流：{pairs or '无'}")
        print(f"   含 ≥8 个 20–79 区间小数的流：{tvals or '无'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
