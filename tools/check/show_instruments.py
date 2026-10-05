#!/usr/bin/env python3
"""汇总 data/instruments/ 下所有量表包的关键指标。"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
tot_items = tot_dims = 0
rows = []
for p in sorted(glob.glob(os.path.join(ROOT, "data", "instruments", "*.json"))):
    if os.path.basename(p) == "catalog.json":
        continue                     # 目录是元信息，不是量表包
    with open(p, encoding="utf-8") as fh:
        d = json.load(fh)
    if "items" not in d:
        continue
    n = len(d["items"])
    facets = len([x for x in d["dimensions"] if x.get("level", 1) == 1])
    rev = len([x for x in d["items"] if x.get("key", 1) == -1])
    tot_items += n
    tot_dims += facets
    rows.append((os.path.basename(p), n, facets, rev, d["license"]["kind"],
                 d.get("display_name", "")[:34]))
print(f"{'文件':30} {'题数':>4} {'维度':>4} {'反向':>4}  授权                 名称")
print("-" * 104)
for r in rows:
    print(f"{r[0]:30} {r[1]:4} {r[2]:4} {r[3]:4}  {r[4]:20} {r[5]}")
print("-" * 104)
print(f"{'合计 ' + str(len(rows)) + ' 套':30} {tot_items:4} {tot_dims:4}")
