#!/usr/bin/env python3
"""修 tools/README.md：①同小节内去重 ②把 patch_readme_index.py 归到 legacy 节。

背景：`patch_readme_index.py` 没有幂等检查，我连跑两次，把 5 个条目插了两遍。
另外它已从 `tools/build/` 移到 `tools/legacy/`，索引里还留在 build 节。

判重口径：**只在同一小节内**判重（`### 3.x` 之间）。同一文件名出现在不同小节
是正常的（叙述性引用），不算重复条目。
"""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, r"C:\Codes\emohealth-20260930-full\emohealth\tools")
from _root import find_root  # noqa: E402
ROOT = str(find_root())
MD = os.path.join(ROOT, "tools", "README.md")

lines = open(MD, encoding="utf-8").read().split("\n")
H3 = re.compile(r"^### ([0-9.]+)\s")
ITEM = re.compile(r"^\|\s*`(?:tools/)?([^`/\\]+\.(?:py|js|sh|json|md))`\s*\|")


def section_span(lines, sec):
    start = next((i for i, l in enumerate(lines)
                  if H3.match(l) and H3.match(l).group(1) == sec), None)
    if start is None:
        return None, None
    end = next((i for i in range(start + 1, len(lines)) if H3.match(lines[i])),
               len(lines))
    return start, end


# ── ① 同小节内去重 ─────────────────────────────────────────
removed = 0
for sec in ("3.1", "3.2", "3.3", "3.4", "3.5", "3.6", "3.7"):
    start, end = section_span(lines, sec)
    if start is None:
        continue
    seen, drop = set(), []
    for i in range(start, end):
        m = ITEM.match(lines[i])
        if not m:
            continue
        if m.group(1) in seen:
            drop.append(i)
        else:
            seen.add(m.group(1))
    for i in reversed(drop):
        print(f"  ✂ 去重 §{sec}: {lines[i][:58]}…")
        del lines[i:i + 1]
        removed += 1

# ── ② patch_readme_index.py 归到 legacy 节 ─────────────────
idx = [i for i, l in enumerate(lines)
       if ITEM.match(l) and ITEM.match(l).group(1) == "patch_readme_index.py"]
if not idx:
    print("  · patch_readme_index.py 无索引条目")
elif len(idx) > 1:
    for i in reversed(idx[1:]):
        del lines[i:i + 1]
        removed += 1
    print(f"  ✂ patch_readme_index.py 重复 {len(idx)} 次 → 保留 1 次")

# 判断它当前在哪个小节
cur = None
for i, l in enumerate(lines):
    m = H3.match(l)
    if m:
        cur = m.group(1)
    if ITEM.match(l) and ITEM.match(l).group(1) == "patch_readme_index.py":
        row, row_sec, row_i = l, cur, i
        break
else:
    row = row_sec = row_i = None

if row and row_sec != "3.6":
    del lines[row_i]
    start, end = section_span(lines, "3.6")
    if start is not None:
        # 插到 legacy 表末尾（表体最后一行之后）
        body = [i for i in range(start, end) if ITEM.match(lines[i])]
        pos = (body[-1] + 1) if body else end
        lines.insert(pos, row)
        print(f"  → patch_readme_index.py：§{row_sec} → §3.6")

open(MD, "w", encoding="utf-8").write("\n".join(lines))
print(f"已写回（删除 {removed} 行）")
