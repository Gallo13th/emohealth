#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""情景结构的可用性分析。

回答一个问题：**用户按情景作答时，各 facet 的估计精度如何变化？**

关键点：因为情景划分是**预先确定的**，用户每一种完成状态都是已知的。
所以可以对每个 facet 的**每一个可能子集**，算出「该子集小分与完整 10 题总分的相关」——
不需要近似，运行时直接查表即可。

输出：`data/scene-precision.json`（全部 2^10 子集的精度表 + 完成情景的累计分析）
"""
from __future__ import annotations

import itertools
import json
import os
import sys
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
DATA = os.path.join(ROOT, "archive/datasets/osf-johnson/validity/ipip20993.dat")
CANON = os.path.join(ROOT, "data/ipip-neo-300.json")
TAX = os.path.join(ROOT, "data/scene-taxonomy.json")
OUT = os.path.join(ROOT, "data/scene-precision.json")


def main() -> int:
    canon = json.load(open(CANON, encoding="utf-8"))
    tax = json.load(open(TAX, encoding="utf-8"))
    scene_of = {int(k): v["scene"] for k, v in tax["items"].items()}
    facet_of = {i["order"]: i["facet"] for i in canon["items"]}
    key_of = {i["order"]: i["key"] for i in canon["items"]}

    df = pd.read_csv(DATA, sep="\t", dtype=str, keep_default_na=False)
    ic = [f"I{i}" for i in range(1, 301)]
    X = (df[ic].replace({"": np.nan, " ": np.nan, "0": np.nan})
         .apply(pd.to_numeric, errors="coerce").to_numpy(float))
    Xc = X[~np.isnan(X).any(axis=1)]
    n = Xc.shape[0]

    facets: dict[str, list[int]] = defaultdict(list)
    for o, f in facet_of.items():
        facets[f].append(o)
    for f in facets:
        facets[f].sort()

    # ---- 全 2^10 子集精度表（对每个 facet）
    table: dict[str, dict[str, float]] = {}
    for facet, orders in facets.items():
        cols = [o - 1 for o in orders]
        keys = np.array([key_of[o] for o in orders], float)
        full = Xc[:, cols].sum(axis=1)
        sub = Xc[:, cols]
        d = {}
        for mask in range(1, 1024):
            sel = [i for i in range(10) if mask >> i & 1]
            part = sub[:, sel].sum(axis=1)
            if part.std() == 0:
                continue
            d[str(mask)] = round(float(np.corrcoef(part, full)[0, 1]), 4)
        table[facet] = d

    # ---- 完成情景的累计分析（按题数降序）
    scene_sizes = Counter(scene_of.values())
    order_scenes = [s for s, _ in scene_sizes.most_common()]
    facets_sorted = sorted(facets)

    steps = []
    done: set[str] = set()
    for sc in order_scenes:
        done.add(sc)
        answered = {o for o, s in scene_of.items() if s in done}
        per_facet = {}
        for facet, orders in facets.items():
            sel = [o for o in orders if o in answered]
            if not sel:
                per_facet[facet] = None
                continue
            mask = sum(1 << orders.index(o) for o in sel)
            per_facet[facet] = table[facet].get(str(mask))
        vals = [v for v in per_facet.values() if v is not None]
        steps.append({
            "after_scene": sc,
            "scene_items": scene_sizes[sc],
            "cum_items": len(answered),
            "facets_touched": len(vals),
            "r_mean": round(float(np.mean(vals)), 4) if vals else None,
            "r_min": round(float(np.min(vals)), 4) if vals else None,
            "facets_r_ge_080": sum(1 for v in vals if v >= 0.80),
            "facets_r_ge_085": sum(1 for v in vals if v >= 0.85),
            "facets_r_ge_090": sum(1 for v in vals if v >= 0.90),
            "per_facet": {k: v for k, v in per_facet.items()},
        })

    # ---- 单情景：完成一个情景能解锁什么
    single = {}
    for sc in order_scenes:
        per = {}
        for facet, orders in facets.items():
            sel = [o for o in orders if scene_of[o] == sc]
            if not sel:
                continue
            mask = sum(1 << orders.index(o) for o in sel)
            per[facet] = {"k": len(sel), "r": table[facet].get(str(mask))}
        strong = {k: v for k, v in per.items() if v["r"] and v["r"] >= 0.90}
        single[sc] = {
            "items": scene_sizes[sc], "facets_touched": len(per),
            "facets_r_ge_090": len(strong), "detail": per,
        }

    payload = {
        "source": f"Johnson (2005) 完整作答 {n} 条",
        "key_point": "情景划分预先确定 → 每种完成状态都已知 → 可对每个 facet 的"
                     "**每个可能子集**离线算出精度，运行时直接查表，无需近似",
        "precision_table": table,
        "cumulative_by_completing_largest_first": steps,
        "single_scene_unlock": single,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)

    print(f"精度表：{len(table)} 个 facet × 各 {len(next(iter(table.values())))} 个子集")
    print("\n=== 按「先做最大的情景」累计，facet 精度如何增长 ===")
    print(f"{'完成到':<12}{'累计题数':>8}{'触及facet':>10}{'r均值':>8}{'r最差':>8}"
          f"{'≥.80':>7}{'≥.85':>7}{'≥.90':>7}")
    print("-" * 72)
    for s in steps:
        if s["cum_items"] < 300 and s["scene_items"] < 3:
            continue
        print(f"{s['after_scene']:<12}{s['cum_items']:>8}{s['facets_touched']:>10}"
              f"{s['r_mean']:>8.3f}{s['r_min']:>8.3f}{s['facets_r_ge_080']:>7}"
              f"{s['facets_r_ge_085']:>7}{s['facets_r_ge_090']:>7}")

    print("\n=== 只完成一个情景，能解锁什么 ===")
    print(f"{'情景':<14}{'题数':>5}{'触及facet':>10}{'r≥.90 的facet':>14}")
    print("-" * 46)
    for sc in order_scenes:
        d = single[sc]
        print(f"{sc:<14}{d['items']:>5}{d['facets_touched']:>10}{d['facets_r_ge_090']:>14}")

    print(f"\nwrote {os.path.relpath(OUT, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
