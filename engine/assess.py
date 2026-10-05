#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测评引擎 —— 把量表档案 + 一组作答，变成可交付的结果。

对应 `PLAN.md` §2.6 的引擎七步中的后四步：

    质量门 → 计分 → 解读 → （陪伴 agent 的输入）

设计约束（全部来自 Phase 1 的实测结论）：

1. **质量门只声明能算的。** 题量不足时（如只答了一个 facet 的 10 题），
   反义题指标无法计算——此时必须明说"无法计算"，不得给出一个基于残缺数据的数。
2. **反向题先还原再算 longstring。** 数据源的作答可能已被反向重编码
   （IPIP-NEO-300 即是）。实测最大 longstring 在两种口径下差 3 题。
3. **分数变化要对着噪音底解释。** SEM 给出 95% 置信区间；小于区间的变化不是变化。
4. **不给分型、不给诊断。** 输出只有：分数、带、精度、以及"这不意味着什么"。
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field, asdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
BANDS = ["Very Low", "Low", "Average", "High", "Very High"]


# --------------------------------------------------------------------------- 载入
def _load_record(facet: str) -> dict | None:
    """优先取 content/facets/，回退到 content/pilot/（早期切片）。"""
    for sub in ("facets", "pilot"):
        p = os.path.join(ROOT, "content", sub, f"{facet}.record.json")
        if os.path.exists(p):
            return json.load(open(p, encoding="utf-8"))
    return None


def _load(name: str) -> dict:
    with open(os.path.join(ROOT, "data", name), encoding="utf-8") as fh:
        return json.load(fh)


@dataclass
class Reference:
    """引擎所需的全部参照物。"""
    canonical: dict = field(default_factory=lambda: _load("ipip-neo-300.json"))
    norms: dict = field(default_factory=lambda: _load("uk-norms.json"))
    antonyms: dict = field(default_factory=lambda: _load("antonym-pairs.json"))
    quality: dict = field(default_factory=lambda: _load("quality-gate-calibration.json"))

    def __post_init__(self) -> None:
        self.by_id = {i["id"]: i for i in self.canonical["items"]}
        self.by_order = {i["order"]: i for i in self.canonical["items"]}
        self.antonym_pairs = [(p["a_order"] - 1, p["b_order"] - 1) for p in self.antonyms["pairs"]]

    def facet_alpha(self, facet: str) -> float | None:
        return self.canonical["facet_alphas"].get(facet)

    def norm_bands(self, facet: str, age: str) -> dict | None:
        table = self.norms["levels"]["facets"].get(age, {})
        for key, bands in table.items():
            if key.lower().replace("-", "").replace(" ", "") == facet.replace("_", ""):
                return bands
        return None

    def longstring_ref(self) -> dict:
        for s in self.quality["statistics"]:
            if s["name"].startswith("longstring_raw"):
                return s["pct"]
        return {}

    def antonym_ref(self) -> dict:
        best = self.antonyms["best_candidate"]
        return self.antonyms["candidate_indices"][best]


# --------------------------------------------------------------------------- 质量门
def quality_gate(responses: dict[str, int], ref: Reference) -> dict:
    """responses: {item_id: 1..5}，可以是整卷也可以只是一个 facet 的子集。"""
    out: dict = {"n_answered": len(responses), "flags": [], "notes": []}

    # --- 完整度 ---
    facet_items = None
    facets_present = {ref.by_id[i]["facet"] for i in responses if i in ref.by_id}
    if len(facets_present) == 1:
        facet_items = [i["id"] for i in ref.canonical["items"]
                       if i["facet"] == next(iter(facets_present))]
        n_missing = len(facet_items) - len(responses)
        out["completeness"] = {"answered": len(responses), "expected": len(facet_items),
                               "missing": max(n_missing, 0)}
        if n_missing > 0:
            out["flags"].append(f"COMPLETENESS: 少答 {n_missing} 题")
    else:
        out["completeness"] = {"answered": len(responses), "expected": 300,
                               "missing": 300 - len(responses)}

    # --- longstring：必须先把反向题还原为原始作答类别 ---
    seq = sorted((ref.by_id[i]["order"], i) for i in responses if i in ref.by_id)
    # 只在**连续施测位置**上统计，避免把不连续作答误判为连续
    runs = []
    cur = 0
    prev_order = None
    prev_raw = None
    for order, iid in seq:
        it = ref.by_id[iid]
        raw = responses[iid] if it["key"] > 0 else 6 - responses[iid]   # 还原
        if prev_order is not None and order == prev_order + 1 and raw == prev_raw:
            cur += 1
        else:
            if cur:
                runs.append(cur)
            cur = 1
        prev_order, prev_raw = order, raw
    if cur:
        runs.append(cur)
    ls_raw = max(runs) if runs else 0
    pct = ref.longstring_ref()
    # 施测顺序是 30-facet 交错循环，因此只答单个 facet 时题目两两不相邻，
    # longstring 恒为 1。那是**无法计算**，不是"作答质量很好"。
    consecutive_pairs = sum(1 for i in range(1, len(seq)) if seq[i][0] == seq[i - 1][0] + 1)
    if consecutive_pairs == 0:
        out["longstring"] = {
            "value": None, "status": "NOT_COMPUTABLE",
            "blocker": "作答题目在施测顺序中两两不相邻（交错循环下只答单个 facet 即如此），"
                       "无法统计连续同答。",
            "reference": {"p95": pct.get("95"), "p99": pct.get("99")},
        }
        out["notes"].append("连续同答无法计算——同样是作答范围限制。")
    else:
        out["longstring"] = {
            "value": ls_raw,
            "p95_reference": pct.get("95"),
            "p99_reference": pct.get("99"),
            "consecutive_pairs": consecutive_pairs,
            "note": "已把反向题还原为原始作答类别后统计",
        }
        if ls_raw >= (pct.get("99") or 999):
            out["flags"].append(f"LONGSTRING: {ls_raw} 连题同答（高于参照样本 p99={pct.get('99')}）")
        elif ls_raw >= (pct.get("95") or 999):
            out["flags"].append(f"LONGSTRING: {ls_raw} 连题同答（高于参照样本 p95={pct.get('95')}）")

    # --- 反义题一致性：需要覆盖足够多的题对 ---
    have = set(responses)
    usable = [(a, b) for a, b in ref.antonym_pairs
              if ref.by_order[a + 1]["id"] in have and ref.by_order[b + 1]["id"] in have]
    if len(usable) >= 10:
        a = [responses[ref.by_order[a + 1]["id"]] for a, _ in usable]
        b = [responses[ref.by_order[b + 1]["id"]] for _, b in usable]
        am = sum(a) / len(a)
        bm = sum(b) / len(b)
        num = sum((x - am) * (-(y - bm)) for x, y in zip(a, b))
        den = math.sqrt(sum((x - am) ** 2 for x in a) * sum((y - bm) ** 2 for y in b))
        r = num / den if den else float("nan")
        refv = ref.antonym_ref()
        p5 = refv.get("percentiles", {}).get("5")
        out["antonyms"] = {"value": round(r, 4), "n_pairs": len(usable),
                           "p5_reference": p5, "verdict": ref.antonyms["verdict"]}
        if p5 is not None and r < p5:
            out["flags"].append(f"ANTONYMS: 反义题一致性 {r:.2f} 低于参照样本 p5={p5}")
    else:
        out["antonyms"] = {
            "value": None, "n_pairs": len(usable),
            "status": "NOT_COMPUTABLE",
            "blocker": f"仅覆盖 {len(usable)} 对反义题（需 ≥10 对）。"
                       "反义题对为跨 facet 题对，只答单个 facet 时无法计算。",
        }
        out["notes"].append("反义题一致性无法计算——这是作答范围限制，不是作答质量问题。")

    # --- 可靠性折扣（多指标，概率化，非一刀切） ---
    discount = 0.0
    if any(f.startswith("LONGSTRING") for f in out["flags"]):
        discount += 0.35
    if any(f.startswith("ANTONYMS") for f in out["flags"]):
        discount += 0.35
    if any(f.startswith("COMPLETENESS") for f in out["flags"]):
        discount += 0.15
    out["reliability_discount"] = round(min(discount, 0.8), 2)
    out["policy"] = ("PLAN.md §2.5：多指标筛查 + 概率化降权，不删除、不下单一硬阈值。"
                     "折扣作用于**解读的强度**，不改变分数本身。")
    return out


# --------------------------------------------------------------------------- 计分
def score_facet(facet: str, responses: dict[str, int], ref: Reference, age: str = "18-29") -> dict:
    items = [i for i in ref.canonical["items"] if i["facet"] == facet]
    answered = [i for i in items if i["id"] in responses]
    if len(answered) < len(items):
        return {"status": "INCOMPLETE",
                "answered": len(answered), "expected": len(items),
                "blocker": "部分作答不产生剖面——本产品强制声明部分剖面（PLAN.md §2.5 分层施测）"}

    raw = sum(responses[i["id"]] if i["key"] > 0 else 6 - responses[i["id"]] for i in items)
    lo, hi = len(items), len(items) * 5

    bands = ref.norm_bands(facet, age)
    band = None
    for name in reversed(BANDS):
        rng = bands.get(name) if bands else None
        if rng and rng[0] <= raw <= rng[-1]:
            band = name
            break

    alpha = ref.facet_alpha(facet)
    # SEM 的 SD：优先用常模带反推（见 phase1_findings §4.4），否则留空
    sd = _sd_from_bands(bands) if bands else None
    sem = round(sd * math.sqrt(1 - alpha), 2) if (sd and alpha) else None
    ci = [round(raw - 1.96 * sem, 1), round(raw + 1.96 * sem, 1)] if sem else None

    return {
        "status": "OK",
        "raw_score": raw,
        "possible_range": [lo, hi],
        "band": band,
        "band_unassigned": band is None,
        "reference_age_band": age,
        "cronbach_alpha": alpha,
        "sd_from_bands": sd,
        "sem": sem,
        "ci95": ci,
        "noise_floor_note": (f"小于约 {round(1.96 * sem, 1)} 分的变化不应被解读为真实变化"
                             if sem else None),
    }


def _sd_from_bands(bands: dict) -> float | None:
    """由 σ 分带边界反推 SD（见 phase1_findings §4.4）。"""
    try:
        avg, high, vh, low = bands["Average"], bands["High"], bands["Very High"], bands["Low"]
        p05 = (avg[-1] + high[0]) / 2
        p15 = (high[-1] + vh[0]) / 2
        n05 = (avg[0] + low[-1]) / 2
        est = [p05 - n05, p15 - p05]
        return round(sum(est) / len(est), 2)
    except (KeyError, IndexError):
        return None


# --------------------------------------------------------------------------- 解读
def interpret(facet: str, scored: dict, quality: dict, record: dict) -> dict:
    """组装解读。**表达层可润色，结论层不可改动**（PLAN.md §2.5）。"""
    if scored.get("status") != "OK":
        return {"status": "WITHHELD", "reason": scored.get("blocker")}

    band = scored["band"]
    lines: list[str] = []

    if band:
        lines.append(f"你在「{record['identity']['facet_name_zh']}」上的原始分是 "
                     f"{scored['raw_score']}（范围 {scored['possible_range'][0]}–"
                     f"{scored['possible_range'][1]}），落在 **{band}** 带。")
    else:
        lines.append(f"你的原始分是 {scored['raw_score']}。"
                     f"⚠️ 该分数**不落在任何已发布分带内**——源常模表存在覆盖空洞"
                     f"（见 phase1_findings §4.3），这是一个已知的源数据缺陷。")

    if scored.get("ci95"):
        lines.append(f"考虑到测量误差（SEM {scored['sem']}），你的真实水平有 95% 可能落在 "
                     f"{scored['ci95'][0]}–{scored['ci95'][1]} 之间。")

    # 常模适用性（强制）
    lines.append("⚠️ 参照人群为**英国**样本，非中国人群；源文件未提供样本量、"
                 "招募方式与采集年份。")

    # 质量门如实汇报
    if quality["flags"]:
        lines.append("作答质量提示：" + "；".join(quality["flags"]) + "。"
                     f"（可靠性折扣 {quality['reliability_discount']}，"
                     f"作用于解读强度，不改变分数）")
    if quality.get("notes"):
        # 各条注释自身以「。」结尾，拼接前去掉，避免出现「。；」
        clean = [n.rstrip("。；") for n in quality["notes"]]
        lines.append("说明：" + "；".join(clean) + "。")

    # "这不意味着什么"——来自档案
    does_not_mean = record["construct"]["does_not_measure"]
    lines.append("**这个分数不意味着：**" + "；".join(does_not_mean) + "。")

    # 面向自身的内容局限——必须到达用户，不能只躺在档案元数据里。
    # 区分两级：known_critiques 是研究记录；interpretation_caveats 是**用户可见义务**。
    caveats = (record.get("evidence", {}) or {}).get("interpretation_caveats", [])
    if caveats:
        lines.append("**读这个分数时需要注意：**\n\n" +
                     "\n\n".join(f"- {c}" for c in caveats))

    return {
        "status": "OK",
        "narrative": "\n\n".join(lines),
        "polish_scope": {
            "may_rewrite": ["narrative 的措辞、语气、详略"],
            "must_not_change": ["raw_score", "band", "ci95", "sem",
                                "quality.flags", "does_not_mean 的内容",
                                "interpretation_caveats 的内容（内容局限不可删）"],
        },
    }


# --------------------------------------------------------------------------- 主入口
def assess(facet: str, responses: dict[str, int], ref: Reference | None = None,
           age: str = "18-29", record: dict | None = None) -> dict:
    ref = ref or Reference()
    quality = quality_gate(responses, ref)
    scored = score_facet(facet, responses, ref, age)
    if record is None:
        record = _load_record(facet) or {
            "identity": {"facet_name_zh": facet},
            "construct": {"does_not_measure": []},
        }
    return {
        "facet": facet,
        "quality_gate": quality,
        "score": scored,
        "interpretation": interpret(facet, scored, quality, record),
    }


# --------------------------------------------------------------------------- 剖面
def assess_profile(facets: list[str], responses: dict[str, int],
                   ref: Reference | None = None, age: str = "18-29") -> dict:
    """多 facet 剖面。

    质量门**只算一次**——它衡量的是整份作答的质量，不是某一题的。
    这一点很重要：把质量门摊到每个 facet 上会让人误以为"某个 facet 答得不好"。
    """
    ref = ref or Reference()
    quality = quality_gate(responses, ref)

    rows = []
    for facet in facets:
        record = _load_record(facet)
        scored = score_facet(facet, responses, ref, age)
        if record is None:
            name_zh = facet
        else:
            name_zh = record["identity"]["facet_name_zh"]
        rows.append({
            "facet": facet,
            "name_zh": name_zh,
            "domain": record["identity"]["domain"] if record else None,
            "domain_zh": record["identity"].get("domain_zh") if record else None,
            "score": scored,
            "interpretation": (interpret(facet, scored, quality, record)
                               if record else {"status": "NO_RECORD"}),
        })

    return {
        "age_band": age,
        "n_responded_items": len(responses),
        "quality_gate": quality,
        "facets": rows,
        "profile_note": ("本剖面仅覆盖 %d 个 facet，属于**部分剖面**——"
                         "未测量的面向不得据此推断。" % len(facets)),
    }


def render_profile(profile: dict) -> str:
    """把剖面渲染成可读文本。不facet型、不给诊断。"""
    out: list[str] = []
    out.append(f"年龄段 {profile['age_band']} ｜ 作答 {profile['n_responded_items']} 题")
    out.append("")
    out.append(f"{'面向':<16}{'维度':<12}{'原始分':>7}  {'带':<11}{'95% 区间':<18}")
    out.append("-" * 68)
    for r in profile["facets"]:
        s = r["score"]
        if s.get("status") != "OK":
            out.append(f"{r['name_zh']:<16}{r.get('domain_zh') or '':<12}"
                       f"{'—':>7}  {s['status']:<11}")
            continue
        band = s["band"] or "无对应带"
        ci = f"{s['ci95'][0]}–{s['ci95'][1]}" if s.get("ci95") else "—"
        out.append(f"{r['name_zh']:<16}{r.get('domain_zh') or '':<12}"
                   f"{s['raw_score']:>7}  {band:<11}{ci:<18}")

    # 可视化：以带为行，展示各 facet 所处位置
    order = ["Very Low", "Low", "Average", "High", "Very High"]
    out.append("")
    out.append("按带定位：")
    for band in reversed(order):
        marks = [r["name_zh"] for r in profile["facets"]
                 if r["score"].get("band") == band]
        if marks:
            out.append(f"  {band:<11} {'、'.join(marks)}")
    unassigned = [r["name_zh"] for r in profile["facets"]
                  if r["score"].get("status") == "OK" and not r["score"].get("band")]
    if unassigned:
        out.append(f"  {'无对应带':<11} {'、'.join(unassigned)}"
                   f"   ⚠️ 源常模存在覆盖空洞")

    q = profile["quality_gate"]
    out.append("")
    out.append(f"作答质量：折扣 {q['reliability_discount']}")
    for f in q["flags"]:
        out.append(f"  🚩 {f}")
    for n in q["notes"]:
        out.append(f"  ℹ️  {n}")
    out.append("")
    out.append(profile["profile_note"])
    return "\n".join(out)
