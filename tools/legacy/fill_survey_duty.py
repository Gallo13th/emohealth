#!/usr/bin/env python3
"""补 `survey_structured_text.py` 的索引职责（收口）。"""

from __future__ import annotations

import io
import os
import sys

sys.path.insert(0, r"C:\Codes\emohealth-20260930-full\emohealth\tools")
from _root import find_root  # noqa: E402
MD = os.path.join(str(find_root()), "tools", "README.md")

P = "（**待补写职责**——自动录入，请打开脚本读 docstring 后改这里）"
DUTIES = {
    "survey_structured_text.py":
        ("测绘结构化文本的支撑度：606 题的字段现状、选项缺口（当时 585 题无 options）、"
         "推断参数齐备度 —— 为「四字段结构化文本 + 事实预测」定范围"),
    # 本脚本自己那条也在这里覆盖（否则自动录入会留占位）
    "fill_survey_duty.py": "补写索引里指定脚本的占位职责（收口用；本脚本自己那条也由它补）",
}

s = io.open(MD, encoding="utf-8").read()
n = 0
for NAME, DUTY in DUTIES.items():
    i = s.find(f"| `{NAME}` | {P} |")
    if i < 0:
        print(f"  · {NAME} 未找到占位（可能已补）")
        continue
    end = s.find("\n", i)
    s = s[:i] + f"| `{NAME}` | {DUTY} | 见脚本 docstring | 见脚本 docstring |" + s[end:]
    n += 1
    print(f"  ✓ {NAME}")
io.open(MD, "w", encoding="utf-8").write(s)
print(f"  补 {n} 条；剩余占位 {sum(1 for ln in s.split(chr(10)) if P in ln)} 处")
