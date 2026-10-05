#!/usr/bin/env python3
"""测绘前端「推断/推荐」逻辑对**大五专属数据**的依赖，为通用化定边界。

要解耦的三件事（用户要求「向大五人格靠齐」）
==========================================
① **推断数据来源**：现在读 `ui/adaptive-data.js`（AD）与 `ui/emohealth-data.js`（D），
   两者都是大五专属。目标改为读 `ui/inference/<code>.js`（已建好，两套都是
   `item_level`，格式统一）。
② **按需加载**：`ui/inference/*.js` 各 240–280 KB，必须像量表包那样 `<script>`
   注入，不能一进首页就加载。
③ **可调参数**：`MIN_OWN`（题量下限）等硬编码值应来自数据（`partial` 的 k-曲线），
   而不是写死。

本脚本只**测绘**：列出每个推断相关函数读哪些外部数据、哪些常量是硬编码的。
"""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, r"C:\Codes\emohealth-20260930-full\emohealth\tools")
from _root import find_root  # noqa: E402
ROOT = str(find_root())
HTML = os.path.join(ROOT, "ui", "index.html")

src = open(HTML, encoding="utf-8").read()
lines = src.split("\n")

# 推断/推荐相关的关键标识
KEYS = ["adaptCtx", "gainOf", "netR2", "unlockOf", "recommendTreeItem",
        "instAggregate", "instScores", "MIN_OWN", "UNLOCK_R", "pairR",
        "itemFacetR", "AD.", "D.facets", "D.items", "TIERS", "RIDGE"]

print("=== 每个标识的出现位置 ===")
seen: dict[str, list[int]] = {}
for i, l in enumerate(lines, 1):
    for k in KEYS:
        if k in l:
            seen.setdefault(k, []).append(i)

for k in KEYS:
    pos = seen.get(k, [])
    print(f"  {k:20} {len(pos):3} 处"
          + (f"  行 {pos[:8]}" if pos else "  （未出现）"))

print("\n=== 硬编码常量（需改为从数据来）===")
for i, l in enumerate(lines, 1):
    if re.search(r"const\s+(MIN_OWN|UNLOCK_R|MIN_RESID|RIDGE|TIERS)\s*=", l):
        print(f"  行 {i:5}: {l.strip()[:90]}")

print("\n=== 全局数据包的读取点（要改成按需加载）===")
for i, l in enumerate(lines, 1):
    if re.search(r"window\.EMOHEALTH(_[A-Z]+)?\b|const\s+(D|AD|TIER|UN|CORR)\s*=\s*window", l):
        print(f"  行 {i:5}: {l.strip()[:96]}")

print("\n=== 推断函数清单（含定义行）===")
for i, l in enumerate(lines, 1):
    if re.match(r"\s*function\s+(adaptCtx|gainOf|netR2|pairR|unlockOf|"
                r"recommendTreeItem|instAggregate|instScores|instPercentile)", l):
        print(f"  行 {i:5}: {l.strip()[:96]}")

print("\n=== ui/inference 是否已被界面引用 ===")
print(f"  index.html 提到 inference：{src.count('inference')} 处")
print(f"  EMOHEALTH_INFER_ 出现：{src.count('EMOHEALTH_INFER_')} 处")
