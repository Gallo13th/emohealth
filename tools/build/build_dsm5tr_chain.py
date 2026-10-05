#!/usr/bin/env python3
"""构建 DSM-5-TR 评估链路：Level 1 → Level 2 → PID-5。

链路是什么，以及它的证据强度
============================
用户的澄清改变了这件事的性质：DSM-5-TR 的 Level 1/2 量表册**不是**与 PID-5
平级的独立量表，而是**配套的筛查与细评工具**。所以要把关系定义清楚。

**可溯源的部分（手册原文，Table 1）**
  Level 1 的 13 个域各有「进一步询问的门槛」，多数域对应一份 Level 2：
    · 抑郁/愤怒/躁狂/焦虑/躯体/睡眠/重复思维 → ≥2（mild or greater）→ 对应 Level 2
    · **自杀意念/精神病性/物质使用 → ≥1（slight or greater）**（比其余更敏感，因为漏报代价高）
    · 记忆/解离/人格功能 → 门槛 ≥2，但**没有对应的 Level 2**（Table 1 写 None）
  Level 1 的域分口径：**域内任一题的最高分**（"the highest score on any item within a domain"）。

**推论的部分（必须标注，不能混进原文）**
  Table 1 里「XII 人格功能」的 Level 2 是 None。而在 DSM-5 体系里，人格功能的
  详细评估工具正是 **AMPD 的 PID-5**（Criterion A 人格功能 + Criterion B 适应不良特质）。
  所以「L1 的人格功能域 → PID-5」是**依架构推出的接口，不是手册原文**。
  已核查：9 册手册的正文里**一次都没提到 PID-5，也没提到 personality disorder**——
  所以这个衔接只能标为推论，并写明依据。

产出 ``data/linkage/dsm5tr-chain.json``，界面与文档都读它。
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
OUT = os.path.join(ROOT, "data", "linkage", "dsm5tr-chain.json")

# Table 1 的 13 行（自 archive/scales/DSM5TR-L1/manual.pdf 提取，工具
# tools/survey/extract_l1_table1.py；阈值用分值表示：mild=2、slight=1）
DOMAINS = [
    (1, "I", "Depression", 2, "DSM5TR-L2-Depression"),
    (2, "II", "Anger", 2, "DSM5TR-L2-Anger"),
    (3, "III", "Mania", 2, "DSM5TR-L2-Mania"),
    (4, "IV", "Anxiety", 2, "DSM5TR-L2-Anxiety"),
    (5, "V", "Somatic Symptoms", 2, "DSM5TR-L2-Somatic"),
    (6, "VI", "Suicidal Ideation", 1, None),
    (7, "VII", "Psychosis", 1, None),
    (8, "VIII", "Sleep Problems", 2, "DSM5TR-L2-Sleep"),
    (9, "IX", "Memory", 2, None),
    (10, "X", "Repetitive Thoughts and Behaviors", 2, "DSM5TR-L2-Repetitive"),
    (11, "XI", "Dissociation", 2, None),
    (12, "XII", "Personality Functioning", 2, None),
    (13, "XIII", "Substance Use", 1, "DSM5TR-L2-Substance"),
]


def main() -> int:
    inst_l1 = json.load(open(os.path.join(
        ROOT, "data", "instruments", "dsm5tr-l1.json"), encoding="utf-8"))
    dim_by_name = {d["name"]: d for d in inst_l1["dimensions"]}

    domains = []
    for idx, roman, name, thr, l2 in DOMAINS:
        d = dim_by_name.get(name)
        domains.append({
            "index": idx, "roman": roman, "name": name,
            "items": d["items"] if d else [],
            "threshold": thr,
            "threshold_label": "Slight or greater" if thr == 1 else "Mild or greater",
            "level2": l2,
            "note": ("门槛较低（≥1）：漏报代价高于误报" if thr == 1 else ""),
        })

    out = {
        "chain": "DSM-5-TR 精神状态评估链路",
        "direction": "筛查 → 细评 → （人格障碍）特质评估",
        "level1": {
            "instrument": "DSM5TR-L1",
            "display_name": "DSM-5-TR Level 1 跨切面症状量表（成人）",
            "purpose": "跨诊断的症状域筛查；**不给常模分数**，给的是「是否需要就该域做更细评估」的门槛",
            "scoring": "域分 = 该域内**任一题的最高分**（手册原文：the highest score on any item within a domain）",
            "response_scale": {"min": 0, "max": 4,
                               "labels": ["None or not at all",
                                          "Slight or rare, less than a day or two",
                                          "Mild or several days",
                                          "Moderate or more than half the days",
                                          "Severe or nearly every day"]},
            "window": "past TWO (2) WEEKS",
            "domains": domains,
            "evidence": {
                "file": "archive/scales/DSM5TR-L1/manual.pdf",
                "section": "Instructions to Clinicians — Scoring and Interpretation；Table 1",
                "extractor": "tools/survey/extract_l1_table1.py",
            },
        },
        "level2": {
            "maps_from": {d["name"]: d["level2"] for d in domains if d["level2"]},
            "note": "Level 2 用于对已触发域做更细的症状评估；各册口径不同（PROMIS 给 T 分、"
                    "躯体册为 0–2 求和、躁狂册为选项组求和）——**不能互相套用**",
            "norms_status": ("待逐册核实。PROMIS 类给 T 分（美国一般人群 M=50, SD=10），"
                             "与 PID-5 的百分位口径不同，需单独取来源"),
        },
        "pid5_interface": {
            "status": "inferred",
            "from_domain": "Personality Functioning",
            "to_instrument": "PID-5",
            "evidence": ("Table 1 里 XII「Personality Functioning」的对应 Level 2 列为 "
                         "**None**——即手册没有为该域指定 Level 2 细评工具"),
            "basis": ("DSM-5 体系的 Section III（AMPD）里，人格功能的详细评估由 "
                      "PID-5 承担：Criterion A 为人格功能（自我/人际），Criterion B 为 "
                      "适应不良特质，PID-5 即 Criterion B 的操作化工具"),
            "caveat": ("**已核查：9 册 DSM-5-TR 量表手册的正文一次都没提到 PID-5，"
                       "也没提到 personality disorder**。所以这条衔接是依 DSM-5 架构"
                       "推出的接口，不是这些册子的原文。界面呈现时必须如实区分。"),
            "how_to_verify": ("要升格为「原文明确」，需查阅 DSM-5-TR 正文 Section III"
                              "（Emerging Measures and Models → Personality Disorders）"
                              "中 AMPD 与 PID-5 的表述"),
        },
        "presentation_rules": [
            "Level 1 的结果**不显示为分数带或百分位**——它不是常模量表，只显示「哪些域达到/超过门槛」",
            "达到门槛的域给出「建议进一步评估」与对应的 Level 2 名称；未达到门槛的域不给结论",
            "自杀意念/精神病性/物质使用三个域门槛为 ≥1，界面必须如实说明「门槛更低」及其原因",
            "人格功能域达到门槛时，可提示「该域的细评工具为 PID-5（依 DSM-5 架构，非本册原文）」",
            "**不得**由 Level 1 或 Level 2 的结果推出任何诊断结论",
        ],
        "disclaimer": ("DSM-5-TR 手册原文：「These patient assessment measures were "
                       "developed to be administered at the initial patient interview and "
                       "to monitor treatment progress. They should be used in research and "
                       "evaluation as potentially useful tools to enhance clinical "
                       "decision-making and **not as the sole basis for making a clinical "
                       "diagnosis**.」"),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
        fh.write("\n")

    thr1 = [d["name"] for d in domains if d["threshold"] == 1]
    mapped = [d["name"] for d in domains if d["level2"]]
    print(f"域 {len(domains)} 个（应为 13）")
    print(f"  门槛 ≥1 的域 {len(thr1)} 个：{', '.join(thr1)}")
    print(f"  有对应 Level 2 的域 {len(mapped)} 个：{', '.join(mapped)}")
    print(f"  无 Level 2 的域："
          f"{', '.join(d['name'] for d in domains if not d['level2'])}")
    print(f"\n✓ 已写出 {os.path.relpath(OUT, ROOT)}")
    return 0 if len(domains) == 13 else 1


if __name__ == "__main__":
    sys.exit(main())
