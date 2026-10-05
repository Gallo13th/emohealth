#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""情景模式 —— 把「生活情景」变成可交付的作答流程与结果。

对应 `research/phase3_interaction_design.md`。四条硬约束：

1. **答题过程中只展示完成度，不展示分值**（原 D30；现 `PLAN.md` §2.5）。
   规避「实时分数加剧反刍」——那正是本项目要解决的问题本身。
2. **情景结果只能是题目级位置比较，不得称 facet 分数**（原 D31；现 `PLAN.md` §2.5）。
   一个情景每 facet 通常只有 1–2 题，单题与完整测量的相关最差仅 0.51。
3. **面向的解锁按实际题集查精度表**，不按「完成 N 个情景」线性承诺。
   因为部分面向被单一情景门控（cooperation 8/10 在「冲突与竞争」）。
4. **k≤2 一律不展示分数**——此时相关最差只有 0.507，给数字就是用噪音冒充测量。

数据来源：
  data/scene-taxonomy.json    8 个情景与每题归属
  data/scene-precision.json   每个 facet 全部 1023 个子集的精度
  data/item-norms.json        每题的参照分布（题目级位置比较的原料）
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# 精度 → 展示层级。阈值取自 `data/partial-administration.json` 的实测曲线。
TIERS = [
    (0.95, "完整", "可以按完整测量的精度看待"),
    (0.90, "较可靠", "误差很小，结论稳"),
    (0.80, "初步倾向", "方向大致可信，细节别当真"),
    (0.70, "仅供参考", "只能看大致方向"),
]


def _load(name: str) -> dict:
    with open(os.path.join(ROOT, "data", name), encoding="utf-8") as fh:
        return json.load(fh)


@dataclass
class SceneReference:
    """情景模式所需的全部参照物。"""
    taxonomy: dict = field(default_factory=lambda: _load("scene-taxonomy.json"))
    precision: dict = field(default_factory=lambda: _load("scene-precision.json"))
    item_norms: dict = field(default_factory=lambda: _load("item-norms.json"))
    canonical: dict = field(default_factory=lambda: _load("ipip-neo-300.json"))

    def __post_init__(self) -> None:
        self.items = {int(k): v for k, v in self.taxonomy["items"].items()}
        self.by_scene: dict[str, list[int]] = {}
        for o, v in sorted(self.items.items()):
            self.by_scene.setdefault(v["scene"], []).append(o)
        # 每个 facet 的题序（用于子集掩码）
        self.facet_orders: dict[str, list[int]] = {}
        for o in sorted(self.items):
            self.facet_orders.setdefault(self.items[o]["facet"], []).append(o)
        for f in self.facet_orders:
            self.facet_orders[f].sort()
        self.by_order = {i["order"]: i for i in self.canonical["items"]}

    # ───────────────────────────────────────────── 基本查询
    def scenes(self) -> list[str]:
        """按题数降序；主干（题最多）在最前。"""
        return sorted(self.by_scene, key=lambda s: -len(self.by_scene[s]))

    def scene_name_zh(self, scene: str) -> str:
        return self.taxonomy["scene_names_zh"].get(scene, scene)

    def mask_of(self, facet: str, answered: set[int]) -> int | None:
        """该 facet 已答题集对应的掩码（精度表的键）。"""
        orders = self.facet_orders[facet]
        sel = [o for o in orders if o in answered]
        if not sel:
            return None
        return sum(1 << orders.index(o) for o in sel)

    def precision_of(self, facet: str, answered: set[int]) -> float | None:
        m = self.mask_of(facet, answered)
        if m is None:
            return None
        return self.precision["precision_table"][facet].get(str(m))

    def norm(self, order: int) -> dict:
        return self.item_norms["items"][str(order)]


# --------------------------------------------------------------------------- 作答过程
def progress(ref: SceneReference, answered: set[int]) -> dict:
    """**答题过程中**唯一该展示的东西：完成度。不含任何分值。"""
    scenes = []
    for s in ref.scenes():
        orders = ref.by_scene[s]
        done = sum(1 for o in orders if o in answered)
        scenes.append({
            "scene": s, "name_zh": ref.scene_name_zh(s),
            "total": len(orders), "answered": done,
            "pct": round(done / len(orders) * 100, 1),
            "complete": done == len(orders),
        })
    # 面向层只给 k（题数），**不给分数**
    facets = []
    for f, orders in sorted(ref.facet_orders.items()):
        k = sum(1 for o in orders if o in answered)
        facets.append({"facet": f, "k": k, "total": len(orders),
                       "unlockable": k >= 3})
    return {
        "items_answered": len(answered), "items_total": len(ref.items),
        "pct": round(len(answered) / len(ref.items) * 100, 1),
        "scenes": scenes,
        "scenes_complete": sum(1 for x in scenes if x["complete"]),
        "facets": facets,
        "facets_unlocked": sum(1 for x in facets if x["unlockable"]),
        "note": "答题过程只展示完成度，不展示分值",
    }


# --------------------------------------------------------------------------- 解锁
def unlock_status(ref: SceneReference, answered: set[int]) -> dict:
    """逐 facet 判定：能展示到什么精度。按**实际题集**查表，不按情景数量线性外推。"""
    out = {}
    for f, orders in sorted(ref.facet_orders.items()):
        k = sum(1 for o in orders if o in answered)
        r = ref.precision_of(f, answered)
        if k <= 2:
            tier, advice = "未解锁", "题量不足——单题与完整测量的相关最差只有 0.51，此时不给分数"
        elif r is None:
            tier, advice = "未解锁", "该题集在参照样本中无法计算"
        else:
            tier, advice = "仅供参考", "只能看大致方向"
            for th, name, adv in TIERS:
                if r >= th:
                    tier, advice = name, adv
                    break
        out[f] = {"k": k, "total": len(orders), "r": r,
                  "tier": tier, "advice": advice,
                  "show_score": tier != "未解锁"}
    return out


# --------------------------------------------------------------------------- 情景结果
def _aligned(order: int, resp: int, ref: SceneReference) -> int:
    """把作答按计分键对齐到「高分 = 该面向高端」。"""
    return resp if ref.items[order]["key"] > 0 else 6 - resp


def scene_result(scene: str, responses: dict[int, int],
                 ref: SceneReference, answered_all: set[int] | None = None) -> dict:
    """情景完成后的结果：面板 A（对比人群）+ 面板 B（对比自己）。

    ⚠️ 这里**没有任何 facet 分数**——每项只基于 1 题。见 D31。
    """
    orders = ref.by_scene[scene]
    got = {o: responses[o] for o in orders if o in responses}
    if not got:
        return {"scene": scene, "status": "EMPTY"}

    # ── 面板 A：题目级位置（对比参照样本）
    # ⚠️ 两个关键点：
    # 1. 百分位是按**对齐到面向方向后**算的，而题面是**原始方向**。
    #    反向题（如「不喜欢改变」）若直接配原始题面展示百分位，用户会读反。
    #    故显式给出「原始作答」并打 ⟲ 标记。
    # 2. **分组必须用相对百分位，不能用绝对选项值。**
    #    在某题上选 2（绝对偏低），但 84% 的人都选了 1，则此人在这题上
    #    其实是**相对偏高**的。面向的构念分数本来就是相对人群的，
    #    所以「偏向高端/低端」应以百分位为准。
    panel_a = []
    for o in orders:
        if o not in got:
            continue
        a = _aligned(o, got[o], ref)
        n = ref.norm(o)
        pct = n["option_pct"][a - 1]
        panel_a.append({
            "order": o, "facet": ref.items[o]["facet"],
            "text_zh": ref.items[o]["text_zh"],
            "response": got[o], "aligned": a,
            "direction": "high" if pct > 50 else ("low" if pct < 50 else "neutral"),
            "reverse": ref.items[o]["key"] < 0,
            "percentile": pct,
            "resolution_pct": n["max_adjacent_span_pct"],
        })
    # 越极端排越前：按偏离人群中间水平的程度
    panel_a.sort(key=lambda x: -abs(x["percentile"] - 50))
    high = [x for x in panel_a if x["direction"] == "high"]
    low = [x for x in panel_a if x["direction"] == "low"]

    # ── 面板 B：与自己的基线对比（需先完成 ≥3 个情景）
    panel_b = None
    base = answered_all if answered_all is not None else set(responses)
    scenes_done = {ref.items[o]["scene"] for o in base if o in responses}
    if len(scenes_done) >= 3 and len(base) >= 30:
        own = [_aligned(o, responses[o], ref) for o in base if o in responses]
        own_mean = sum(own) / len(own)
        deltas = []
        for o in orders:
            if o not in got:
                continue
            d = _aligned(o, got[o], ref) - own_mean
            deltas.append({
                "order": o, "facet": ref.items[o]["facet"],
                "text_zh": ref.items[o]["text_zh"],
                "response": got[o], "delta": round(d, 2),
                "reverse": ref.items[o]["key"] < 0,
            })
        deltas.sort(key=lambda x: -x["delta"])
        panel_b = {"own_mean_aligned": round(own_mean, 2),
                   "scenes_used": len(scenes_done),
                   "above_own": [d for d in deltas if d["delta"] > 0.5][:6],
                   "below_own": [d for d in deltas if d["delta"] < -0.5][-6:]}
    else:
        panel_b = {"status": "NEEDS_MORE",
                   "need_scenes": 3, "have_scenes": len(scenes_done),
                   "why": "要比较「情景中的你」与「平时的你」，先得有「平时的你」"}

    return {
        "scene": scene, "name_zh": ref.scene_name_zh(scene),
        "n_items": len(orders), "n_answered": len(got),
        "complete": len(got) == len(orders),
        "panel_a": panel_a,
        "panel_a_high": high, "panel_a_low": low,
        "panel_a_neutral": sum(1 for x in panel_a if x["direction"] == "neutral"),
        "panel_b": panel_b,
        "must_say": "每一项仅基于 1 道题。这是**作答位置的描述**，"
                    "不是该面向的测量结果——单题与完整测量的相关最差只有 0.51。",
    }


# --------------------------------------------------------------------------- 渲染
def render_progress(p: dict) -> str:
    L = [f"完成度  {p['items_answered']}/{p['items_total']} 题"
         f"（{p['pct']}%）｜已完成情景 {p['scenes_complete']}/{len(p['scenes'])}"
         f"｜可解锁面向 {p['facets_unlocked']}/30", ""]
    for s in p["scenes"]:
        bar = "█" * int(s["pct"] / 5) + "·" * (20 - int(s["pct"] / 5))
        L.append(f"  {s['name_zh']:<16} {bar} {s['answered']:>3}/{s['total']:<3}"
                 + ("  ✓" if s["complete"] else ""))
    L += ["", f"  （{p['note']}）"]
    return "\n".join(L)


def render_scene_result(r: dict, full: bool = True) -> str:
    if r.get("status") == "EMPTY":
        return f"「{r['scene']}」尚无作答"
    L = [f"{'=' * 74}",
         f"情景：{r['name_zh']}   已答 {r['n_answered']}/{r['n_items']} 题",
         f"{'=' * 74}", ""]

    lim = 10 if full else 6
    L.append("【在这个情景里，你偏向这些面向的高端】")
    L.append("   「位置」＝你的作答对齐到该面向方向后的百分位，越高越靠这一端。")
    L.append("   ⟲ 表示该题反向计分：选得越低，越靠该面向的高端。")
    L.append("")
    if r["panel_a_high"]:
        for x in r["panel_a_high"][:lim]:
            mk = "⟲" if x.get("reverse") else " "
            L.append(f"     {x['facet']:<26} 位置 {x['percentile']:>5.1f}"
                     f"   {mk}选了 {x['response']}　{x['text_zh']}")
    else:
        L.append("     （无）")
    L.append("")
    L.append("【在这个情景里，你偏向这些面向的低端】")
    L.append("")
    if r["panel_a_low"]:
        for x in r["panel_a_low"][:lim]:
            mk = "⟲" if x.get("reverse") else " "
            L.append(f"     {x['facet']:<26} 位置 {x['percentile']:>5.1f}"
                     f"   {mk}选了 {x['response']}　{x['text_zh']}")
    else:
        L.append("     （无）")
    if r["panel_a_neutral"]:
        L.append("")
        L.append(f"   另有 {r['panel_a_neutral']} 题选了中间档，不指示方向，未列出。")
    L.append("")

    b = r["panel_b"]
    L.append("【在这个情景里，你和平时的自己有什么不同】")
    if b.get("status") == "NEEDS_MORE":
        L.append(f"   还不够——需要先完成 {b['need_scenes']} 个情景"
                 f"（当前 {b['have_scenes']} 个）")
        L.append(f"   {b['why']}")
    else:
        L.append(f"   （你在全部已答题上的平均位置：{b['own_mean_aligned']}／5，"
                 f"基于 {b['scenes_used']} 个情景）")
        L.append("")
        if b["above_own"]:
            L.append("   比平时更靠高端的：（⟲ 为反向计分题）")
            for d in b["above_own"]:
                mk = "⟲" if d.get("reverse") else " "
                L.append(f"     +{d['delta']:<5} {d['facet']:<24}"
                         f"{mk}选了 {d['response']}　{d['text_zh']}")
        if b["below_own"]:
            L.append("   比平时更靠低端的：")
            for d in b["below_own"]:
                mk = "⟲" if d.get("reverse") else " "
                L.append(f"     {d['delta']:<6} {d['facet']:<24}"
                         f"{mk}选了 {d['response']}　{d['text_zh']}")
        if not b["above_own"] and not b["below_own"]:
            L.append("   没有明显偏离你平时水平的地方。")
    L += ["", f"⚠️  {r['must_say']}"]
    return "\n".join(L)


def render_unlock(u: dict, only_showable: bool = True) -> str:
    L = ["面向解锁状态（按实际题集查精度表，不按情景数量线性外推）", ""]
    items = [(f, v) for f, v in u.items() if v["show_score"]] if only_showable \
        else list(u.items())
    items.sort(key=lambda x: (-(x[1]["r"] or 0)))
    if not items:
        return "\n".join(L + ["  （暂无任何面向达到可展示精度）"])
    L.append(f"  {'面向':<30}{'题数':>5}{'r':>7}  {'层级':<10}")
    for f, v in items:
        L.append(f"  {f:<30}{v['k']:>3}/{v['total']:<2}"
                 f"{(v['r'] or 0):>7.3f}  {v['tier']:<10}")
    locked = [f for f, v in u.items() if not v["show_score"]]
    if locked:
        L += ["", f"  尚未解锁（题量不足）：{len(locked)} 个面向",
              f"    {'、'.join(locked[:8])}{' …' if len(locked) > 8 else ''}"]
    return "\n".join(L)
