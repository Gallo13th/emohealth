#!/usr/bin/env python3
"""收口：补掉索引里最后几条占位职责（复核工作留下的脚本）。"""

from __future__ import annotations

import io
import os
import sys

sys.path.insert(0, r"C:\Codes\emohealth-20260930-full\emohealth\tools")
from _root import find_root  # noqa: E402
MD = os.path.join(str(find_root()), "tools", "README.md")

P = "（**待补写职责**——自动录入，请打开脚本读 docstring 后改这里）"
DUTIES = {
    "fill_last_duties.py": "补写索引最后几条占位职责（收口用）",
    "survey_translation_review.py":
        "测绘**待复核的中译**：按 `zh_source` 分档、列逐条清单（供 workflow 逐条审核）",
    "inspect_text_review.py":
        "查文本库的 `zh` 赋值机制（累积/继承/上游）与指定条目现状，判断该改源还是改产物",
}

s = io.open(MD, encoding="utf-8").read()
n = 0
for name, duty in DUTIES.items():
    i = s.find(f"| `{name}` | {P} |")
    if i < 0:
        continue
    end = s.find("\n", i)
    s = s[:i] + f"| `{name}` | {duty} | 见脚本 docstring | 见脚本 docstring |" + s[end:]
    n += 1
    print(f"  ✓ {name}")
io.open(MD, "w", encoding="utf-8").write(s)
print(f"补 {n} 条；剩余占位 {sum(1 for ln in s.split(chr(10)) if P in ln)} 处")
