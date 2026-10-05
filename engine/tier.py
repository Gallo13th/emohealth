#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分级解锁引擎 —— 从粗类到细类。

## 结构

第 R 层 = 每个面向恰好 R 题 = 30R 题，层间嵌套（`data/tier-ladder.json`）。

| 层 | 题数 | 能给什么 |
|---:|---:|---|
| 1 | 30 | **只有 5 个大类的分带**（每面向仅 1 题，给不出面向分） |
| 2 | 60 | 大类更准（r 0.944） |
| 3 | 90 | **30 个细类解锁**（每面向 3 题，r 中位 0.870） |
| … | … | 逐层收窄 |
| 10 | 300 | 完整 |

## 三条硬约束

1. **第 1–2 层不给面向分。** 每面向只有 1–2 题，`r(子集,完整分)` 最差仅 0.507。
   这不是保守，是「给数字等于用噪音冒充测量」。
2. **每个数都按实际已答题集查精度**，不按「完成 N 层」线性外推。
3. **大类的承诺是「±1 档」**：第 1 层有 99.0% 落在相邻一档内，差 ≥2 档只有 1.0%。
   用「同带率」（63.3%）作承诺会严重低估，说「足够近似」又太含糊。
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

BAND_ZH = {"Very High": "很高", "High": "偏高", "Average": "中等",
           "Low": "偏低", "Very Low": "很低"}
BAND_ORDER = ["Very High", "High", "Average", "Low", "Very Low"]

# 面向要跨过的精度门槛（与情景模式一致：k≤2 一律不给）
FACET_MIN_K = 3


def _load(name: str) -> dict:
    with open(os.path.join(ROOT, "data", name), encoding="utf-8") as fh:
        return json.load(fh)


@dataclass
class TierReference:
    tier: dict = field(default_factory=lambda: _load("tier-prefix.json"))
    design: dict = field(default_factory=lambda: _load("tier-design.json"))
    canonical: dict = field(default_factory=lambda: _load("ipip-neo-300.json"))

    def __post_init__(self) -> None:
        self.by_order = {i["order"]: i for i in self.canonical["items"]}
        order = self.tier["order"]
        self.pos_of = {o: i + 1 for i, o in enumerate(order)}     # 1-based 座次
        self.order = order
        # JSON 里的键名是 tierItems（累计题数列表）与 tierDomainR（每层元数据）
        self.tier_items = [{"tier": i + 1, "items": n}
                           for i, n in enumerate(self.tier["tierItems"])]
        self.tier_meta = {x["tier"]: x for x in self.tier["tierDomainR"]}
        # 位置 → 层
        self.tier_of_pos: dict[int, int] = {}
        prev = 0
        for t in self.tier_items:
            for p in range(prev + 1, t["items"] + 1):
                self.tier_of_pos[p] = t["tier"]
            prev = t["items"]
        self.facet_orders: dict[str, list[int]] = {}
        for it in self.canonical["items"]:
            self.facet_orders.setdefault(it["facet"], []).append(it["order"])
        self.facets = sorted(self.facet_orders)

    # ── 位置与层
    def tier_of(self, order: int) -> int:
        return self.tier_of_pos[self.pos_of[order]]

    def tier_at(self, answered: set[int]) -> int:
        """当前处在第几层（已完成的最大层）。"""
        p = len(answered)
        t = 1
        for x in self.tier_items:
            if p >= x["items"]:
                t = x["tier"]
        return t

    def next_tier_at(self, answered: set[int]) -> dict | None:
        p = len(answered)
        for x in self.tier_items:
            if p < x["items"]:
                return x
        return None

    # ── 面向精度（按实际已答题集）
    def facet_status(self, facet: str, answered: set[int]) -> dict:
        orders = self.facet_orders[facet]
        sel = [o for o in orders if o in answered]
        k = len(sel)
        p = min(len(answered), 300)
        r = self.tier["prefixFacetR"][p][self.facets.index(facet)]
        if k < FACET_MIN_K:
            tier, lvl = "未解锁", 0
        elif r is None:
            tier, lvl = "未解锁", 0
        elif r >= 0.95:
            tier, lvl = "完整", 3
        elif r >= 0.90:
            tier, lvl = "较可靠", 2
        elif r >= 0.85:
            tier, lvl = "初步倾向", 1
        else:
            tier, lvl = "仅供参考", 1
        return {"facet": facet, "k": k, "of": len(orders), "r": r,
                "tier": tier, "lvl": lvl, "showable": lvl > 0}

    def facets_status(self, answered: set[int]) -> dict:
        return {f: self.facet_status(f, answered) for f in self.facets}

    # ── 维度精度与分带
    def domain_status(self, domain: str, answered: set[int]) -> dict:
        p = min(len(answered), 300)
        i = self.tier["domains"].index(domain)
        r2 = self.tier["prefixDomainR2"][p][i]
        r = r2 ** 0.5 if r2 is not None else None
        return {"domain": domain, "r2": r2, "r": round(r, 4) if r else None,
                "showable": bool(r and r >= 0.80)}

    def domain_band(self, domain: str, responses: dict[int, int]) -> dict:
        """算该维度的分带。**只有跨过门槛才给。**"""
        st = self.domain_status(domain, set(responses))
        if not st["showable"]:
            return {**st, "status": "WITHHELD",
                    "blocker": f"该维度的估计与完整分的相关只有 "
                               f"{st['r']:.3f}，尚不足以给出分带"}
        bands = self.tier["domainBands"].get(domain) or {}
        fs = [f for f in self.facets if f in DESIGN_DOMAIN.get(domain, [])]
        sel = [o for f in fs for o in self.facet_orders[f] if o in responses]
        if not sel:
            return {**st, "status": "EMPTY"}
        raw = sum(responses[o] if self.by_order[o]["key"] > 0 else 6 - responses[o]
                  for o in sel)
        # 折算到完整 60 题的当量
        est = round(raw / len(sel) * 60)
        band = None
        for name in BAND_ORDER:
            rng = bands.get(name)
            if rng and rng[0] <= est <= rng[-1]:
                band = name
                break
        return {**st, "status": "OK", "raw": raw, "n_answered": len(sel),
                "estimate_full_scale": est, "band": band,
                "band_zh": BAND_ZH.get(band) if band else None,
                "band_unassigned": band is None}


# 维度的面向清单（从 facet_definitions 取，避免与规范数据集混淆）
from content.facet_definitions import FACETS  # noqa: E402

DESIGN_DOMAIN: dict[str, list[str]] = {}
for _f, _v in FACETS.items():
    DESIGN_DOMAIN.setdefault(_v["domain"], []).append(_f)


# ───────────────────────────────────────────── 进度（答题中唯一该展示的）
def progress(ref: TierReference, answered: set[int]) -> dict:
    p = len(answered)
    cur = ref.tier_at(answered)
    nxt = ref.next_tier_at(answered)
    fs = ref.facets_status(answered)
    ds = {d: ref.domain_status(d, answered) for d in ref.tier["domains"]}
    return {
        "items_answered": p,
        "items_total": 300,
        "pct": round(p / 300 * 100, 1),
        "tier_current": cur,
        "tier_total": 10,
        "tier_next": nxt,
        "items_to_next": (nxt["items"] - p) if nxt else 0,
        "domains_showable": sum(1 for v in ds.values() if v["showable"]),
        "facets_showable": sum(1 for v in fs.values() if v["showable"]),
        "note": "答题过程只展示完成度，不展示分值",
    }
