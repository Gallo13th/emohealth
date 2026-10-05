#!/usr/bin/env python3
"""列出需要天赋树作答的量表（题量 > 60）。

用户规则（D114 修订）：**只有 >60 题的量表**做天赋树；短量表用经典逐题即可。
理由：短表全答一遍本来就快，天赋树的「挑下一题」价值主要体现在长表上。
"""

import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
THRESHOLD = 60

rows = []
for p in sorted(glob.glob(os.path.join(ROOT, "data", "instruments", "*.json"))):
    if os.path.basename(p) == "catalog.json":
        continue
    d = json.load(open(p, encoding="utf-8"))
    dims = [x for x in d["dimensions"] if x.get("level", 1) == 1]
    rows.append((d["instrument"], len(d["items"]), len(dims),
                 d["license"]["kind"]))

big = [r for r in rows if r[1] > THRESHOLD]
small = [r for r in rows if r[1] <= THRESHOLD]
print(f"量表 {len(rows)} 套：> {THRESHOLD} 题 {len(big)} 套，"
      f"≤ {THRESHOLD} 题 {len(small)} 套\n")
print(f"{'量表（需天赋树）':30} {'题数':>5} {'维度':>5}  授权")
for c, n, dm, lic in sorted(big, key=lambda x: -x[1]):
    print(f"{c:30} {n:5} {dm:5}  {lic}")

print(f"\n小表题量分布（前 12）：")
for c, n, dm, lic in sorted(small, key=lambda x: -x[1])[:12]:
    print(f"  {c:26} {n:4} 题")

# 维度规模：天赋树要有「面向」可展示，太少的量表图形意义不大
print("\n大表的维度数（决定天赋树有几个可点亮的面向）：")
for c, n, dm, lic in sorted(big, key=lambda x: -x[1]):
    print(f"  {c:30} {n:4} 题 / {dm:3} 维")
