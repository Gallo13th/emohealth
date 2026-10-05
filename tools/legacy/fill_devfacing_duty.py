#!/usr/bin/env python3
"""补掉索引里剩余的占位职责（收口用）。"""

from __future__ import annotations

import io
import os
import sys

sys.path.insert(0, r"C:\Codes\emohealth-20260930-full\emohealth\tools")
from _root import find_root  # noqa: E402
MD = os.path.join(str(find_root()), "tools", "README.md")

P = "（**待补写职责**——自动录入，请打开脚本读 docstring 后改这里）"
DUTIES = {
    "survey_devfacing_copy.py":
        "测绘界面里「开发者/审阅者向」的文案（溯源依据/工程术语/开发者指标/免责声明），"
        "为「用户端产品化隐藏」定范围",
    "fill_survey_duty.py": "补写索引里指定脚本的占位职责（收口用；本脚本自己那条也由它补）",
    "fill_last_duties.py": "补写索引最后几条占位职责（收口用）",
    # 本脚本自己那条也在这里覆盖（否则自动录入会留占位）
    "fill_devfacing_duty.py": "补写索引里指定脚本的占位职责（收口用；本脚本自己那条也由它补）",
}

s = io.open(MD, encoding="utf-8").read()
n = 0
for NAME, DUTY in DUTIES.items():
    i = s.find(f"| `{NAME}` | {P} |")
    if i < 0:
        continue
    end = s.find("\n", i)
    s = s[:i] + f"| `{NAME}` | {DUTY} | 见脚本 docstring | 见脚本 docstring |" + s[end:]
    n += 1
    print(f"  ✓ {NAME}")
io.open(MD, "w", encoding="utf-8").write(s)
print(f"  补 {n} 条；剩余占位 {sum(1 for ln in s.split(chr(10)) if P in ln)} 处")
