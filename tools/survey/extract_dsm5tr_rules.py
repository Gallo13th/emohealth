#!/usr/bin/env python3
"""提取 DSM-5-TR 各册的**判读口径与门槛规则**（不是常模分数）。

为什么先做这一步
================
用户的澄清改变了这件事的性质：DSM-5-TR 的 Level 1/2 量表册**不是**与 PID-5
平级的独立量表，而是 **PID-5 的配套筛查工具**。所以「给 DSM-5-TR 做常模」的
正确理解是三件事，而不是一件事：

  ① **Level 1 的门槛规则**：它不是常模分数，而是「某一域任一项 ≥2 即提示
     需要就该域做进一步评估」——这是**触发条件**，必须从手册原文取出；
  ② **Level 2 的口径**：PROMIS 类量表给的是 T 分（美国一般人群 M=50, SD=10），
     另有分界值；躯体等册是 0–2/0–4 的求和；
  ③ **链路**：哪个域触发哪一份 Level 2、何时该转向 PID-5。

本脚本只**读原文并打印**，不做判断——判断要看着原文做。
来源：``archive/scales/DSM5TR-*/manual.pdf``（已归档，含 SHA256）。
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

KEYS = [
    (r"Scoring and Interpretation", 700),
    (r"Instructions to Clinicians", 900),
    (r"[Ii]nterpretation [Tt]able", 500),
    (r"raw score", 300),
    (r"T-?score", 260),
    (r"cut[- ]?off|threshold|refer|further assessment", 300),
]


def text_of(pdf: str) -> str:
    doc = PdfDoc.load(pdf)
    parts = []
    for runs in doc.text_runs():
        parts.extend(r["text"] for r in layout_lines(runs))
    t = " ".join(parts)
    t = re.sub(r"([a-z])([A-Z])", r"\1 \2", t)      # 拆开粘连的大小写边界
    return re.sub(r"\s+", " ", t)


def main() -> int:
    dirs = sorted(glob.glob(os.path.join(ROOT, "archive", "scales", "DSM5TR-*")))
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
        print(f"{code}（{os.path.getsize(pdf)} 字节，正文 {len(t)} 字符）")
        seen = set()
        for pat, span in KEYS:
            for m in re.finditer(pat, t):
                seg = t[m.start():m.start() + span].strip()
                # 去掉重复与太短的
                k = seg[:64]
                if k in seen or len(seg) < 40:
                    continue
                seen.add(k)
                print(f"\n  [{pat}]")
                print("   ", seg[:span].replace("  ", " ")[:span])
                break
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
