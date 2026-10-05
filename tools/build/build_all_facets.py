#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 30 个 facet 组装成完整档案记录。

数据来源与分工（**自动化部分与人工撰写部分严格分离**）：

  自动取自 `data/`：
    · ipip-neo-300.json          —— id / order / key / 英文题面 / α
    · ipip-neo-120-mandarin.json —— 官方法定中文（每 facet 4 题，共 117 题）
    · uk-norms.json              —— 分带常模（3 个年龄段）
    · item-diagnostics.json      —— 题目优先级（决定铺量顺序）

  人工撰写：
    · content/facet_definitions.py —— 30 个 facet 的面向级内容
    · content/translations.py      —— 183 题自译中文
    · content/item_scaffolding.py  —— 题目级脚手架（**按优先级逐步补齐**）

**未撰写脚手架的题目标记为 `PENDING` 并写明 blocker**，
而不是批量生成看似完整、实为套话的文本（`instrument-record.schema.md` §6.1）。

输出：`content/facets/<facet>.record.json`
"""
from __future__ import annotations

import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
sys.path.insert(0, ROOT)

from content.facet_definitions import (  # noqa: E402
    FACETS, NORM_COLUMN, validate as validate_facets,
)
from content.item_scaffolding import SCAFFOLDING  # noqa: E402
from content.translation_overrides import OVERRIDES  # noqa: E402
from content.translations import TRANSLATIONS  # noqa: E402

OUT_DIR = os.path.join(ROOT, "content/facets")
BANDS = ["Very High", "High", "Average", "Low", "Very Low"]


def load(name: str) -> dict:
    with open(os.path.join(ROOT, "data", name), encoding="utf-8") as fh:
        return json.load(fh)


def norm(s: str) -> str:
    return s.lower().replace(" ", "").replace("-", "").replace("_", "")


def sd_from_bands(bands: dict) -> float | None:
    """由 σ 分带边界反推 SD（phase1_findings §4.4）。"""
    try:
        avg, high, vh, low = bands["Average"], bands["High"], bands["Very High"], bands["Low"]
        p05 = (int(avg.split("-")[-1]) + int(high.split("-")[0])) / 2
        p15 = (int(high.split("-")[-1]) + int(vh.split("-")[0])) / 2
        n05 = (int(avg.split("-")[0]) + int(low.split("-")[-1])) / 2
        return round(((p05 - n05) + (p15 - p05)) / 2, 2)
    except (KeyError, ValueError, IndexError):
        return None


def band_str(v: list[int]) -> str:
    return f"{v[0]}-{v[-1]}" if len(v) > 1 else str(v[0])


def build(facet: str, meta: dict, canon: dict, base: dict, norms: dict, diag: dict) -> dict:
    items = sorted([i for i in canon["items"] if i["facet"] == facet], key=lambda x: x["order"])
    base_zh = {norm(i["en"]): i["zh"] for i in base["items"] if i["facet"] == facet}

    # ---- 中文 ----
    zh: dict[int, tuple[str, str]] = {}
    official_ref: dict[int, str] = {}
    for it in items:
        o = it["order"]
        if norm(it["text"]) in base_zh:
            zh[o] = (base_zh[norm(it["text"])], "mandarin_baseline")
        elif o in TRANSLATIONS:
            zh[o] = (TRANSLATIONS[o], "project_translation")
        else:
            zh[o] = (None, "PENDING")
        # D27：译文覆盖——含英文原文，并保留官方原译以供溯源
        if o in OVERRIDES:
            if zh[o][1] == "mandarin_baseline":
                official_ref[o] = zh[o][0]      # 保留官方原译，不丢溯源
            zh[o] = (OVERRIDES[o]["zh"], "project_translation_override")

    # ---- 常模 ----
    bands, domain_bands, band_anomalies = {}, {}, []
    for age in norms["levels"]["facets"]:
        tab = norms["levels"]["facets"][age]
        col = NORM_COLUMN.get(facet, facet)
        key = col if col in tab else [k for k in tab if norm(k) == norm(col)][0]
        bands[age] = {b: band_str(tab[key][b]) for b in BANDS if tab[key].get(b)}
        missing_bands = [b for b in BANDS if not tab[key].get(b)]
        if missing_bands:
            band_anomalies.append(f"{age}: 源常模表中该带为空 {missing_bands}")
        ov = f"{meta['domain'].upper()} (OVERALL)"
        if ov in tab:
            domain_bands[age] = {b: band_str(tab[ov][b]) for b in BANDS if tab[ov].get(b)}

    alpha = canon["facet_alphas"][facet]
    sds = {a: sd_from_bands(bands[a]) for a in bands}
    sems = {a: (round(sds[a] * math.sqrt(1 - alpha), 2) if sds[a] else None) for a in bands}
    ref_age = "18-29"

    # ---- 题目 ----
    out_items, pending = [], []
    for it in items:
        o = it["order"]
        text_zh, zh_src = zh[o]
        sc = SCAFFOLDING.get(o)
        d = diag["items"].get(str(o), {})
        entry = {
            "administration_order": o,
            "id": it["id"],
            "facet": facet,
            "key": it["key"],
            "text_en": it["text"],
            "text_master": it.get("text_master"),
            "text_zh": text_zh,
            "text_zh_source": zh_src,
            **({"text_zh_official_ref": official_ref[o]} if o in official_ref else {}),
            **({"translation_note": {
                "defect": OVERRIDES[o]["defect"],
                "reason": OVERRIDES[o]["reason"],
            }} if o in OVERRIDES else {}),
            "diagnostics": {
                "priority_score": d.get("priority_score"),
                "item_total_r": d.get("item_total_r"),
                "missing_rate": d.get("missing_rate"),
                "neutral_rate": d.get("neutral_rate"),
            },
        }
        if sc is None:
            pending.append(o)
            entry["scaffolding"] = {
                "status": "PENDING",
                "blocker": "题目级脚手架尚未撰写。铺量按 data/item-diagnostics.json 的 "
                           "priority_score 排序推进——本项的 priority_score 见上。",
                "provenance": None,
            }
        else:
            term, sense, not_this = sc["key_term"]
            s = {
                "status": "AUTHORED",
                "asks": sc["asks"],
                "key_term": {"term": term, "sense_here": sense, "not_this": not_this},
                "common_misreadings": [{"misreading": m, "correction": c}
                                       for m, c in sc["mis"]],
                "counts_as": sc["counts"],
                "does_not_count_as": sc["notcount"],
                "edge_cases": sc["edge"],
                "localization_note": sc.get("loc"),
                "provenance": "editorial_clarification",
                "evidence_anchor": f"题干承重词为「{term}」"
                                   + ("；本题为反向计分" if it["key"] < 0 else ""),
            }
            if sc.get("rev"):
                s["reverse_item_note"] = ("反向题。题干表述的是本面向的**低**端。"
                                          "照实作答即可，系统会反向计分。")
            entry["scaffolding"] = s
        out_items.append(entry)

    n_auth = len(out_items) - len(pending)
    n_off = sum(1 for v in zh.values() if v[1] == "mandarin_baseline")

    return {
        "_note": f"{meta['name_zh']}（{meta['name_en']} / {meta['code']}）。"
                 f"由 tools/build/build_all_facets.py 从 data/ 与 content/ 组装。",
        "identity": {
            "id": f"ipip-neo-300.{facet}", "instrument": "IPIP-NEO-300",
            "facet_name_zh": meta["name_zh"], "facet_name_en": meta["name_en"],
            "facet_code": meta["code"], "domain": meta["domain"], "domain_zh": meta["domain_zh"],
        },
        "license": {
            "status": "public_domain", "show_items": True, "translate": True,
            "redistribute": True,
            "evidence": "https://www.ipip.ori.org/newPermission.htm — "
                        "'permission has already been automatically granted for any person to use "
                        "IPIP items, scales, and inventories for any purpose, commercial or "
                        "non-commercial'",
        },
        "construct": {
            "definition": {"text": meta["definition"], "basis": "改述自 Costa & McCrae (1992) "
                                                                  "NEO-PI-R 专业手册中该面向的定义",
                           "provenance": "published_definition"},
            "does_not_measure": meta["does_not_measure"],
            "boundaries": [{"against_facet": f, "against_facet_zh": z, "distinction": d,
                            "basis": "NEO-PI-R 面向定义"}
                           for f, z, d in meta["boundaries"]],
            "applicable_population": "成年一般人群",
            "inapplicable_population": ["无法理解中文题面者",
                                        "处于急性危机状态者（应先处理危机，而非测评）"],
        },
        "administration": {
            "recall_window": {"value": "typical",
                              "instruction_quote": "Describe yourself as you generally are now, "
                                                   "not as you wish to be in the future.",
                              "source": "IPIP-NEO-300 官方问卷指导语",
                              "plain_zh": "请描述你平时一贯的样子，而不是今天的样子，"
                                          "也不是你希望成为的样子。"},
            "item_count": len(items),
            "item_order_in_full_instrument": "interleaved_30_facet_cycle",
            "order_style": "interleaved_facet_cycle",
            "estimated_duration_min": 35,
            "response_format": {"points": 5,
                                "labels_zh": ["非常不符合", "比较不符合", "中立",
                                              "比较符合", "非常符合"]},
            "anchor_semantics": dict(meta["anchors"], provenance="editorial_clarification"),
        },
        "scoring": {
            "algorithm": "10 题求和（反向题先做 6 − x 转换）。范围 10–50。",
            "reverse_items": [i["id"] for i in out_items if i["key"] < 0],
            "forward_items": [i["id"] for i in out_items if i["key"] > 0],
            "key_balance": f"{sum(1 for i in out_items if i['key'] > 0)} 正向 / "
                           f"{sum(1 for i in out_items if i['key'] < 0)} 反向",
            "reverse_keyed_count": sum(1 for i in out_items if i["key"] < 0),
            "reference_system": "norm_percentile",
        },
        "reliability": {
            "cronbach_alpha": alpha,
            "alpha_source": "OpenScales IPIP-NEO.osd（源自 Goldberg 的 ESCS 数据）",
            "sem": {"formula": "SEM = SD × sqrt(1 − α)", "status": "DERIVED",
                    "value": sems.get(ref_age), "reference_age_band": ref_age,
                    "sd_used": sds.get(ref_age), "alpha_used": alpha,
                    "by_age_band": {a: {"sd": sds[a], "sem": sems[a]} for a in bands},
                    "derivation": "源文件未直接给出 SD；分带按 σ 定义，由带边界反推。",
                    "caveat": "⚠️ 由整数化带边界反推，约 ±0.5 分舍入不确定性，"
                              "不是源文件直接给出的 SD。"},
            "noise_floor": {
                "basis": "Kohút et al. (2020)，facet 层 6 个月重测 r ≈ .70",
                "source_file": "archive/literature/interpretation/"
                               "kohut2020_bfi2-slovak-6month-retest.pdf",
                "user_facing_rule": "facet 分数在约 0.15–0.2 SD 以内的变动属测量噪音。",
                "interpretation_with_sem": (
                    f"95% 置信区间约 ±{round(1.96 * sems[ref_age], 1)} 分；"
                    f"小于该幅度的变化不应被解读为真实变化。" if sems.get(ref_age) else None),
                "provenance": "published_definition"},
        },
        "norms": {
            "status": "AVAILABLE", "parser": "tools/build/parse_uk_norms.py",
            "bands_values": bands, "domain_bands_values": domain_bands,
            "source_anomalies": band_anomalies,
            "bands_scheme": norms["bands_scheme"],
            "applicability_caveat": "**UK 人群，非中国人群。** 源文件未提供样本量、招募方式与"
                                    "采集年份。年龄段划分较粗（14-17 / 18-29 / 30+）。",
            "cross_file_discrepancy_note": "同一 OSF 目录下的 TRAITS 与 FACETS 文件在 "
                                           "CONSCIENTIOUSNESS/14-17 边界上不一致；"
                                           "本档案统一采用 FACETS 文件，以保证 facet 与维度同源。",
        },
        "evidence": {
            "validated_in_chinese": False,
            "chinese_note": "IPIP-NEO-300 无任何中文译本。官方标记的普通话译本仅覆盖 120 题版"
                            "（每 facet 4 题），且 IPIP 官方声明该译本未经其验证。"
                            "其余题目为本项目自译。",
            "known_critiques": meta["critiques"],
            "interpretation_caveats": meta["caveats"],
        },
        "item_status": {
            "total": len(out_items),
            "chinese_official": n_off,
            "chinese_project_translation": sum(1 for v in zh.values()
                                               if v[1] == "project_translation"),
            "chinese_overridden": sum(1 for v in zh.values()
                                      if v[1] == "project_translation_override"),
            "scaffolding_authored": n_auth,
            "scaffolding_pending": len(pending),
            "pending_orders": sorted(pending),
        },
        "items": out_items,
    }


def main() -> int:
    probs = validate_facets()
    if probs:
        print("❌ facet 定义有问题：")
        for p in probs:
            print("  -", p)
        return 1

    canon, base = load("ipip-neo-300.json"), load("ipip-neo-120-mandarin.json")
    norms, diag = load("uk-norms.json"), load("item-diagnostics.json")
    os.makedirs(OUT_DIR, exist_ok=True)

    tot_auth = tot_pend = 0
    rows = []
    for facet, meta in FACETS.items():
        rec = build(facet, meta, canon, base, norms, diag)
        with open(os.path.join(OUT_DIR, f"{facet}.record.json"), "w", encoding="utf-8") as fh:
            json.dump(rec, fh, ensure_ascii=False, indent=1)
        st = rec["item_status"]
        tot_auth += st["scaffolding_authored"]
        tot_pend += st["scaffolding_pending"]
        rows.append((facet, meta["name_zh"], st))

    print(f"生成 {len(rows)} 个档案 → {os.path.relpath(OUT_DIR, ROOT)}/")
    print(f"\n{'facet':<46}{'中文(官/自)':>12}{'脚手架(已/待)':>16}")
    print("-" * 76)
    for f, zh, st in rows:
        print(f"{f:<46}{st['chinese_official']:>5}/{st['chinese_project_translation']:<6}"
              f"{st['scaffolding_authored']:>8}/{st['scaffolding_pending']:<7}")
    print("-" * 76)
    print(f"{'合计':<46}{117:>5}/{183:<6}{tot_auth:>8}/{tot_pend:<7}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
