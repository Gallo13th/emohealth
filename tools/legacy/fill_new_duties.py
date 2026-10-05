#!/usr/bin/env python3
"""补写 README 索引里 4 条自动录入的占位职责。"""
import os
import sys

sys.path.insert(0, r"C:\Codes\emohealth-20260930-full\emohealth\tools")
from _root import find_root  # noqa: E402
ROOT = str(find_root())
MD = os.path.join(ROOT, "tools", "README.md")

REAL = {
    "survey_inference_deps.py":
        "测绘前端推断/推荐逻辑对**大五专属数据**的依赖：函数清单、硬编码常量"
        "（MIN_OWN/UNLOCK_R/RIDGE）、全局包读取点——为通用化定边界",
    "diagnose_ipip_recoding.py":
        "裁决 `ipip20993.dat` 是否**已预编码**反向题：148 道反向题在未翻转时与"
        "同 facet 其余题的相关符号（实测 148/148 为正，中位 +0.536）",
    "diagnose_itemfacetr.py":
        "比对 `AD.itemFacetR` 与 `NET.item_facet_corr` 是否一致（按名字对齐逐格 + "
        "argmax 判据），用于定位列序/口径错位",
    "fix_placeholder_duties.py":
        "把 `autofill_readme_index.py` 留下的「待补写职责」占位文字替换成真实职责",
    # 本脚本自己那条也在这里覆盖（否则自动录入时会留占位）
    "fill_new_duties.py":
        "补写索引里**新录入条目**的占位职责（本脚本自己那条也由它补）",
}

P = "（**待补写职责**——自动录入，请打开脚本读 docstring 后改这里）"
md = open(MD, encoding="utf-8").read()
n = 0
for name, duty in REAL.items():
    old = f"| `{name}` | {P} | 见脚本 | 见脚本 |"
    new = f"| `{name}` | {duty} | 见脚本 docstring | 见脚本 docstring |"
    if old in md:
        md = md.replace(old, new)
        n += 1
        print(f"  ✓ {name}")
    else:
        print(f"  · {name}（未找到，可能已补）")
open(MD, "w", encoding="utf-8").write(md)
print(f"\n替换 {n} 条")
