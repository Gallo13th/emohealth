#!/usr/bin/env python3
"""统计归档里带多语言变体（variants.sets）的量表，以及它们当前的处理情况。"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
OSD = os.path.join(ROOT, "archive", "ipip", "data", "OpenScales")
INST = os.path.join(ROOT, "data", "instruments")

have = {}
for p in glob.glob(os.path.join(OSD, "**", "*.osd"), recursive=True):
    try:
        j = json.load(open(p, encoding="utf-8"))
    except Exception:
        continue
    d = j.get("definition") or {}
    v = d.get("variants")
    if not isinstance(v, dict) or not v.get("sets"):
        continue
    code = os.path.basename(p)[:-4]
    sets = v["sets"]
    total = len(d.get("items") or [])
    detail = {k: len((s or {}).get("items") or []) for k, s in sets.items()}
    have[code] = {"default": v.get("default"), "sets": detail, "total": total}

print(f"归档里带多语言变体的量表：{len(have)} 套\n")
print(f"{'量表':28} {'题表':>5} {'默认':>5}  各变体题数")
inc, out = [], []
for c, d in sorted(have.items()):
    f = os.path.join(INST, c.lower() + ".json")
    in_inst = os.path.exists(f)
    (inc if in_inst else out).append(c)
    n = len(json.load(open(f, encoding="utf-8"))["items"]) if in_inst else 0
    print(f"{c:28} {d['total']:5} {str(d['default']):>5}  "
          f"{ {k: v for k, v in d['sets'].items()} }"
          + (f"  → 已收录 {n} 题" if in_inst else "  → 未收录"))

print(f"\n已收录 {len(inc)} 套，未收录 {len(out)} 套")
if out:
    print("未收录：", ", ".join(out[:20]))
