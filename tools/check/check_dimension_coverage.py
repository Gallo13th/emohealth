#!/usr/bin/env python3
"""核对：每套量表的**每道题都归属某个维度**。

为什么关键：结果页按维度计分。若某题不属于任何维度，它答了也**算不出结果**，
而界面不会报错——用户只是发现「我答了但分数没变」。这类问题必须逐套查。
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
bad = []
for p in sorted(glob.glob(os.path.join(ROOT, "data", "instruments", "*.json"))):
    if os.path.basename(p) == "catalog.json":
        continue
    d = json.load(open(p, encoding="utf-8"))
    ids = {it["id"] for it in d["items"]}
    covered = set()
    for dim in d["dimensions"]:
        covered |= set(dim.get("items") or [])
    orphan = sorted(ids - covered)
    if orphan:
        bad.append((d["instrument"], len(orphan), len(ids), orphan[:3]))

print(f"量表 {len(glob.glob(os.path.join(ROOT, 'data/instruments/*.json'))) - 1} 套")
if bad:
    print(f"\n❌ {len(bad)} 套有游离题（答了算不出结果）：")
    for c, n, t, ex in bad[:12]:
        print(f"  {c:26} {n}/{t} 游离  例 {ex}")
    sys.exit(1)
print("✅ 每道题都归属某个维度（无游离题）")
