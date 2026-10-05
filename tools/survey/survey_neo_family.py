#!/usr/bin/env python3
"""看归档里有哪些 IPIP-NEO 系列量表，以及项目里已有哪些。"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
print("项目 data/instruments 里的 NEO 相关：")
for p in sorted(glob.glob(os.path.join(ROOT, "data", "instruments", "*neo*.json"))):
    print("  ", os.path.basename(p))
print()

print("归档 OpenScales 里的 IPIP-NEO 系列：")
for p in sorted(glob.glob(os.path.join(ROOT, "archive", "ipip", "data",
                                       "OpenScales", "**", "*.osd"), recursive=True)):
    base = os.path.basename(p).lower()
    if not base.startswith("ipip-neo"):
        continue
    j = json.load(open(p, encoding="utf-8"))
    d = j.get("definition") or {}
    si = d.get("scale_info") or {}
    items = d.get("items") or {}
    print(f"  {os.path.basename(p):34} 题 {len(items):4}  | "
          f"{str(si.get('description', ''))[:64]}")
