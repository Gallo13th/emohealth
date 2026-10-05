#!/usr/bin/env python3
"""逐册建立 DSM-5-TR Level 2 的判读口径（``data/criteria/dsm5tr-l2.json``）。

八册的口径**互不相同**，来源与形态分三类：

**A. 归档自足（口径在手册原文里）——5 册**
  · Mania (ASRM，5 题 0–4，0–20)：Interpretation Table ——
      ≥6 提示高度可能躁狂/轻躁狂；≥6 可能需要治疗与进一步诊断性检查；≤5 不太可能
  · Somatic (PHQ-15，15 题 0–2，0–30)：严重度分带 ——
      Minimal 0–4 / Low 5–9 / Medium 10–14 / High 15–30
  · Repetitive (5 题 0–4，0–20)：≥8 可考虑对强迫症做更详细评估
  · Substance (10 项 0–4)：**不求和**——原文明确「Scores on the individual items
      should be interpreted independently because each item inquires about the use of
      a distinct substance」；>0 的项数表示严重度/复杂度
  · （Sleep 属 PROMIS，见 B）

**B. 需外部 T 分表——4 册 PROMIS**
  Depression / Anger / Anxiety / Sleep 的 Scoring 段写着「Next, the T-score table
  should be used」，但**表本身不在册子里**（已核查：无 raw→T 成对数字、
  无密集 T 值区间）。所以这 4 册的 T 分要另取 PROMIS 官方 scoring manual。
  在取到之前，**如实标注为待补**，界面只给原始分——不能编转换表。

**C. 缺项规则（各册原文一致）**
  缺答 > 25% 时不得使用分数；个别册允许按比例推算（prorated）。
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
OUT = os.path.join(ROOT, "data", "criteria", "dsm5tr-l2.json")
EVID = "archive/scales/{code}/manual.pdf 的 Scoring and Interpretation 段"

SELF_CONTAINED = {
    "DSM5TR-L2-Mania": {
        "kind": "cutoff",
        "scale": "ASRM（Altman Self-Rating Mania Scale）",
        "sum_range": [0, 20],
        "bands": [
            {"label": "不太可能与显著躁狂症状相关", "lo": 0, "hi": 5},
            {"label": "高度可能是躁狂或轻躁狂；可能需要治疗与／或进一步诊断性检查",
             "lo": 6, "hi": 20},
        ],
        "cutoff": 6,
        "notes": "原文同时给出两条 ≥6 的表述（高概率、可能需治疗/进一步检查）",
    },
    "DSM5TR-L2-Somatic": {
        "kind": "severity_bands",
        "scale": "PHQ-15（躯体症状）",
        "sum_range": [0, 30],
        "bands": [
            {"label": "Minimal（极轻）", "lo": 0, "hi": 4},
            {"label": "Low（轻）", "lo": 5, "hi": 9},
            {"label": "Medium（中）", "lo": 10, "hi": 14},
            {"label": "High（重）", "lo": 15, "hi": 30},
        ],
        "cutoff": None,
    },
    "DSM5TR-L2-Repetitive": {
        "kind": "cutoff",
        "scale": "改编自 FOCI（Florida Obsessive-Compulsive Inventory）",
        "sum_range": [0, 20],
        "bands": [
            {"label": "低于分界", "lo": 0, "hi": 7},
            {"label": "可考虑对强迫症做更详细的评估", "lo": 8, "hi": 20},
        ],
        "cutoff": 8,
        "notes": "原文另有『average total score』口径",
    },
    "DSM5TR-L2-Substance": {
        "kind": "per_item",
        # ⚠️ 这一册**没有总分**。原文：Scores on the individual items should be
        #    interpreted independently because each item inquires about the use of a
        #    distinct substance. The rating of multiple items at scores greater than 0
        #    indicates greater severity and complexity of substance use.
        "scale": "改编自 NIDA-Modified ASSIST",
        "sum_range": None,
        "aggregate": "count_positive",
        "aggregate_label": ">0 的项数（严重度／复杂度指标，**不是总分**）",
        "bands": [],
        "cutoff": None,
        "notes": "逐项独立解释：每一一面对应一种物质；多项 >0 表示更严重、更复杂",
    },
}

PROMIS_PENDING = {
    "DSM5TR-L2-Depression": ("PROMIS Depression Short Form", 8, [8, 40]),
    "DSM5TR-L2-Anger": ("PROMIS Anger Short Form", 5, [5, 25]),
    "DSM5TR-L2-Anxiety": ("PROMIS Anxiety Short Form", 7, [7, 35]),
    "DSM5TR-L2-Sleep": ("PROMIS Sleep Disturbance Short Form", 8, [8, 40]),
}


def main() -> int:
    out = {
        "source": "DSM-5-TR Online Assessment Measures（APA 官方公开）",
        "note": "逐册判读口径。**八册口径互不相同，不可互相套用。**",
        "missing_rule": ("缺答超过 25% 时不得使用分数；个别册允许按比例推算"
                         "（prorated）。各册原文均有此说明。"),
        "instruments": {},
    }
    for code, c in SELF_CONTAINED.items():
        out["instruments"][code] = {**c, "source_of_criteria": "manual",
                                    "evidence": EVID.format(code=code)}
    for code, (scale, n, rng) in PROMIS_PENDING.items():
        out["instruments"][code] = {
            "kind": "t_score",
            "scale": scale,
            "items": n,
            "sum_range": rng,
            "bands": [],
            "cutoff": None,
            "tscore_table": None,
            "source_of_criteria": "pending_external",
            "pending_reason": ("手册 Scoring 段要求使用 T-score table，但**表不在册子里**"
                               "（已核查：无 raw→T 成对数字）。需另取 PROMIS 官方 "
                               "scoring manual 才能给 T 分；在取到之前只给原始分。"),
            "evidence": EVID.format(code=code),
        }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
        fh.write("\n")

    ok = [c for c, v in out["instruments"].items()
          if v["source_of_criteria"] == "manual"]
    pend = [c for c, v in out["instruments"].items()
            if v["source_of_criteria"] == "pending_external"]
    print(f"口径就绪（归档自足）{len(ok)} 册：")
    for c in sorted(ok):
        v = out["instruments"][c]
        b = "  ".join(f"{x['lo']}–{x['hi']} {x['label'][:14]}" for x in v["bands"])
        print(f"  {c:26} {v['kind']:16} {b[:70]}")
    print(f"\n待外部来源 {len(pend)} 册：")
    for c in sorted(pend):
        v = out["instruments"][c]
        print(f"  {c:26} {v['scale']}  原始分 {v['sum_range']}")
    print(f"\n✓ 已写出 {os.path.relpath(OUT, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
