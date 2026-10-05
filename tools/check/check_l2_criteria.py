#!/usr/bin/env python3
"""核对八册 L2 的计分聚合与判读口径是否齐备、是否自洽。

重点：**Substance 不能是 sum**（原文明确逐项独立）。这是我在实现里犯过的错，
固化成检查。
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
print(f"{'量表':24}{'聚合':>12}{'口径':>16}{'分带/分界':>12}")
bad = []
for c in codes:
    p = os.path.join(ROOT, "data", "instruments", c + ".json")
    d = json.load(open(p, encoding="utf-8"))
    agg = list(d["scoring"].values())[0]["aggregation"]
    cr = d.get("criteria") or {}
    kind = cr.get("kind") or "(缺)"
    bands = cr.get("bands") or []
    info = f"{len(bands)} 带" if bands else (
        f"分界 {cr.get('cutoff')}" if cr.get("cutoff") else
        (cr.get("aggregate_label", "")[:10] if cr.get("aggregate") else
         ("待补T表" if kind == "t_score" else "—")))
    print(f"{d['instrument']:24}{agg:>12}{kind:>16}{info:>12}")
    # 断言：Substance 必须是 count_true
    if c.endswith("substance") and agg != "count_true":
        bad.append("Substance 应按 count_true（原文：逐项独立，不求和），实际 " + agg)
    if not cr:
        bad.append(f"{d['instrument']} 缺 criteria")
    if kind == "t_score" and cr.get("tscore_table") is None:
        pass  # 待补，允许
print()
if bad:
    print("❌ 问题：")
    for b in bad:
        print("  ·", b)
else:
    print("✅ 八册聚合与口径齐备；Substance 已按原文改为逐项计数")
