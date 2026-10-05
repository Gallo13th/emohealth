#!/usr/bin/env python3
"""核对 L2 各册在**重新生成之后**仍保有 linkage 与 criteria 两个字段。

这是「重新生成覆盖后加字段」这个坑的守卫：build_l2_instruments.py 每次重跑
都会重写量表包，而 linkage 是 tools/build/attach_linkage.py 单独挂的。
若不继承，链路条就会消失（表现为「回不到 Level 1」）——已经踩过一次。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
codes = ["dsm5tr-l2-" + x for x in
         ("anger", "anxiety", "depression", "mania", "repetitive",
          "sleep", "somatic", "substance")]
bad = []
print(f"{'量表':24}{'linkage.role':>14}{'上游域':>26}{'criteria':>14}")
for c in codes:
    d = json.load(open(os.path.join(ROOT, "data", "instruments", c + ".json"),
                       encoding="utf-8"))
    L = d.get("linkage") or {}
    cr = d.get("criteria") or {}
    up = (L.get("upstream") or {}).get("domain", "—")
    print(f"{d['instrument']:24}{str(L.get('role')):>14}{up:>26}"
          f"{str(cr.get('kind')):>14}")
    if L.get("role") != "level2":
        bad.append(f"{d['instrument']} 缺 linkage.upstream")
    if not cr.get("kind"):
        bad.append(f"{d['instrument']} 缺 criteria")
print()
print("❌ " + "；".join(bad) if bad else
      "✅ 八册在重新生成后仍保有 linkage 与 criteria")
sys.exit(1 if bad else 0)
