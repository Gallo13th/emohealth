#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""回答两个问题：

  一、**按维度分块解锁**是否成立？
      现在要答满整环（30 题）才出结果。但每个维度在一环里只有 6 题——
      若某个维度的一环答完（6 题）就能给出**该维度**的分带，体验会细得多。
      本脚本算：某维度答了 R×6 题时，它的估计与完整 60 题分的相关。

  二、**跨面向的连接真的可以忽略吗？**
      我之前说「网络 ≈ 维度结构本身」——那是**平均**而言（跨面向 R² 0.0154 vs
      本面向 0.171）。但用户要的是**略微非线性的连接**，即最强的那些跨面向边。
      本脚本算：
        · 每道题对**其他**面向的信息量排名（谁最能细化谁）
        · 用**全部已答题**（含跨面向）估计某面向时，比只用本面向的题强多少
          —— 这是「网络」在功能上的真实价值

输出：`data/network-edges.json`
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
sys.path.insert(0, ROOT)
from tools.item_coding import as_construct_direction  # noqa: E402

DATA = os.path.join(ROOT, "archive/datasets/osf-johnson/validity/ipip20993.dat")
CANON = os.path.join(ROOT, "data/ipip-neo-300.json")
OUT = os.path.join(ROOT, "data/network-edges.json")


def main() -> int:
    from content.facet_definitions import FACETS  # noqa: E402
    canon = json.load(open(CANON, encoding="utf-8"))
    items = sorted(canon["items"], key=lambda x: x["order"])
    by_order = {it["order"]: it for it in items}
    ladder = json.load(open(os.path.join(ROOT, "data/tier-ladder.json"), encoding="utf-8"))
    order = ladder["order"]
    rings = []
    prev = 0
    for t in ladder["tiers"]:
        rings.append(order[prev:t["items"]]); prev = t["items"]

    fo: dict[str, list[int]] = defaultdict(list)
    df: dict[str, list[str]] = defaultdict(list)
    for it in items:
        fo[it["facet"]].append(it["order"])
    for f in FACETS:
        d = FACETS[f]["domain"]
        if f not in df[d]:
            df[d].append(f)
    for f in fo:
        fo[f].sort()
    for d in df:
        df[d].sort()

    dfr = pd.read_csv(DATA, sep="\t", dtype=str, keep_default_na=False)
    X = (dfr[[f"I{i}" for i in range(1, 301)]]
         .replace({"": np.nan, " ": np.nan, "0": np.nan})
         .apply(pd.to_numeric, errors="coerce").to_numpy(float))
    Xc = X[~np.isnan(X).any(axis=1)]
    R, coding = as_construct_direction(Xc, items, expect_recoded=True)
    n = R.shape[0]

    facets = sorted(fo)
    domains = sorted(df)
    facet_full = {f: R[:, [o - 1 for o in fo[f]]].sum(axis=1) for f in facets}
    dom_full = {d: R[:, [o - 1 for f in df[d] for o in fo[f]]].sum(axis=1) for d in domains}

    def corr(a, b):
        return float(np.corrcoef(a, b)[0, 1])

    def r2_all(target, cols):
        """用给定列回归 target 的 R²（含截距）。"""
        if not cols:
            return 0.0
        A = np.column_stack([np.ones(n), R[:, cols]])
        beta, *_ = np.linalg.lstsq(A, target, rcond=None)
        pred = A @ beta
        return float(1 - ((target - pred) ** 2).sum()
                     / ((target - target.mean()) ** 2).sum())

    # ── 一、按维度分块：某维度答了 R×6 题时的相关
    print("正在算「按维度分块解锁」…", flush=True)
    block = {}
    for d in domains:
        rows = []
        for Rt in range(1, 11):
            # 该维度在第 1..Rt 环里的题
            sel = [o for t in range(Rt) for o in rings[t]
                   if by_order[o]["facet"] in df[d]]
            part = R[:, [o - 1 for o in sel]].sum(axis=1)
            rows.append({"ring": Rt, "items": len(sel),
                         "r": round(corr(part, dom_full[d]), 4),
                         "r2_all": round(r2_all(dom_full[d], [o - 1 for o in sel]), 4)})
        block[d] = rows
    print(f"{'维度':<18}" + "".join(f"{r['items']:>7}" for r in block[domains[0]]))
    print("-" * 88)
    for d in domains:
        print(f"{d:<18}" + "".join(f"{r['r']:>7.3f}" for r in block[d]))
    print("（列＝该维度已答题数 6/12/…/60，行＝维度，值＝与完整 60 题分的相关）")

    # ── 二、跨面向的边
    print("\n正在算跨面向连接…", flush=True)
    # item → 各面向的相关
    IF = np.zeros((300, len(facets)))
    for j, f in enumerate(facets):
        full = facet_full[f]
        for i in range(300):
            IF[i, j] = corr(R[:, i], full)

    edges = []
    for i, it in enumerate(items):
        j = facets.index(it["facet"])
        others = [(float(IF[i, b] ** 2), facets[b]) for b in range(len(facets)) if b != j]
        others.sort(reverse=True)
        top = others[0]
        edges.append({
            "order": it["order"], "facet": it["facet"],
            "to_facet": top[1], "r2": round(top[0], 4),
            "own_r2": round(float(IF[i, j] ** 2), 4),
            "ratio": round(top[0] / max(float(IF[i, j] ** 2), 1e-9), 3),
            "same_domain": FACETS[top[1]]["domain"] == FACETS[it["facet"]]["domain"],
        })
    stronger_elsewhere = [e for e in edges if e["ratio"] > 1.0]
    same_dom_edges = [e for e in edges if e["same_domain"]]

    # ── 三、网络的功能价值：用全部已答题 vs 只用本面向的题
    print("正在算网络的功能价值…", flush=True)
    net_gain = []
    for Rt in (1, 2, 3, 5, 8, 10):
        answered = [o for t in range(Rt) for o in rings[t]]
        own_only, with_net = [], []
        for f in facets:
            own = [o for o in answered if by_order[o]["facet"] == f]
            own_only.append(np.sqrt(r2_all(facet_full[f], [o - 1 for o in own])))
            with_net.append(np.sqrt(r2_all(facet_full[f], [o - 1 for o in answered])))
        net_gain.append({
            "ring": Rt, "items": len(answered),
            "own_only_mean": round(float(np.mean(own_only)), 4),
            "with_network_mean": round(float(np.mean(with_net)), 4),
            "gain": round(float(np.mean(with_net) - np.mean(own_only)), 4),
        })

    payload = {
        "source": f"Johnson (2005) 完整作答 {n} 条；{coding['verdict']}",
        "q1_domain_block": {
            "question": "某维度答了 R×6 题时，它的估计与完整 60 题分有多一致？",
            "by_domain": block,
            "reading": "若第 1 环（6 题）就有 0.8 以上，则「按维度分块解锁」成立",
        },
        "q2_cross_edges": {
            "question": "跨面向的连接可以忽略吗？",
            "n_items_whose_strongest_link_is_another_facet": len(stronger_elsewhere),
            "n_items": 300,
            "strongest": sorted(edges, key=lambda e: -e["r2"])[:25],
            "edges": edges,
        },
        "q3_network_value": {
            "question": "把跨面向的信息用起来，能提升多少？",
            "rows": net_gain,
        },
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)

    print(f"\n=== 跨面向连接 ===")
    print(f"  最强的跨面向边（该题最能细化哪个别的面向）：")
    for e in payload["q2_cross_edges"]["strongest"][:8]:
        print(f"    #{e['order']:>3} {e['facet'][:22]:<24}→ {e['to_facet'][:22]:<24}"
              f" R²={e['r2']:.3f}（本面向 {e['own_r2']:.3f}）"
              f"{'  同维度' if e['same_domain'] else ''}")
    print(f"\n  该题对本面向的解释力弱于对某个别的面向的："
          f"{len(stronger_elsewhere)}/300 道")
    print(f"  最强的跨面向边落在**同维度**内的比例："
          f"{sum(1 for e in payload['q2_cross_edges']['strongest'] if e['same_domain'])}"
          f"/25")

    print(f"\n=== 网络的功能价值：用全部已答题 vs 只用本面向 ===")
    print(f"{'环':>3}{'题数':>6}{'只用本面向':>12}{'含跨面向':>10}{'增益':>9}")
    for r in net_gain:
        print(f"{r['ring']:>3}{r['items']:>6}{r['own_only_mean']:>12.3f}"
              f"{r['with_network_mean']:>10.3f}{r['gain']:>+9.3f}")
    print(f"\nwrote {os.path.relpath(OUT, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
