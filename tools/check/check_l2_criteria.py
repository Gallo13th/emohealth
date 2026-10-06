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
    if kind == "t_score":
        # ⚠️ 2026-10-06：T 分型册**必须优先显示它自己的 T 分状态**——不能再显示
        #    过时的「待补T表」，也不能只显示「N 带」而把表的情况吞掉。
        #    按该册 `source_of_criteria` 如实报：有表就报行数与表源，pending 才说待补；
        #    后面再追加 T 分单位分带的档数。
        rows = (cr.get("tscore_table") or {}).get("rows") or []
        src = cr.get("source_of_criteria") or ""
        if rows:
            tag = "官方man" if src == "archived_scoring_manual" else "册内"
            info = f"T表{len(rows)}行/{tag}"
        elif src == "pending_external":
            info = "待补T表"
        else:
            info = "—"
        if bands:
            info += f"+{len(bands)}带"
    elif bands:
        info = f"{len(bands)} 带"
    elif cr.get("cutoff"):
        info = f"分界 {cr.get('cutoff')}"
    elif cr.get("aggregate_label"):
        info = cr["aggregate_label"][:10]
    else:
        info = "—"
    print(f"{d['instrument']:24}{agg:>12}{kind:>16}{info:>18}")
    # 断言①：T 分册若声称表已入库，就必须真有逐行数据（防「标了有表其实是空」）
    if kind == "t_score" and cr.get("source_of_criteria") in (
            "manual", "archived_scoring_manual") and not (cr.get("tscore_table") or {}).get("rows"):
        bad.append(f"{d['instrument']} 声称 source_of_criteria={cr['source_of_criteria']} "
                   f"但 tscore_table 没有 rows")
    # 断言②：T 分单位的分带必须**铺满且不重叠**（0.1 分辨率），且带溯源
    if kind == "t_score" and bands:
        if bands[0].get("lo") is not None or bands[-1].get("hi") is not None:
            bad.append(f"{d['instrument']} T 分分带首/末档未开区间（会留下 −∞/+∞ 的洞）")
        for a, b in zip(bands, bands[1:]):
            want = a["hi"] if not a.get("hi_inclusive") else round(a["hi"] + 0.1, 1)
            if b.get("lo") is None or abs(b["lo"] - want) > 1e-9:
                bad.append(f"{d['instrument']} T 分分带边界不闭合："
                           f"{a['label']}→{b['label']} 期望 {want}，实为 {b.get('lo')}")
        if not (cr.get("bands_source") or {}).get("page"):
            bad.append(f"{d['instrument']} T 分分带缺溯源（bands_source.page）")
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
