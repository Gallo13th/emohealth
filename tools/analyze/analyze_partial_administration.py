#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""部分施测的精度分析 —— 为「天赋树 / 渐进解锁」交互方案提供测量学约束。

要回答的问题：
  一个 facet 有 10 题。若用户只答了其中 k 题，「解锁」出来的评估有多准？

分析三件事（全部基于 Johnson 2005 的 20,993 人网络样本）：

  1. **精度 vs k**：k 题小分与完整 10 题总分的相关。
     考察**全部 C(10,k) 个子集**，给出均值与**最差情况**——
     因为交互设计决定了用户会走到哪个子集，最差情况才是要靠设计避免的。

  2. **计分键平衡约束**：每个子集的正/反向题数。
     全正向的子集对默许倾向（acquiescence）毫无防御，是需要排除的。

  3. **覆盖成本**：若要求 30 个 facet 都达到 k 题，最少要答多少题。

输出：`data/partial-administration.json`
"""
from __future__ import annotations

import itertools
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
DATA = os.path.join(ROOT, "archive/datasets/osf-johnson/validity/ipip20993.dat")
CANON = os.path.join(ROOT, "data/ipip-neo-300.json")
OUT = os.path.join(ROOT, "data/partial-administration.json")


def main() -> int:
    canon = json.load(open(CANON, encoding="utf-8"))
    by_order = {i["order"]: i for i in canon["items"]}

    df = pd.read_csv(DATA, sep="\t", dtype=str, keep_default_na=False)
    ic = [f"I{i}" for i in range(1, 301)]
    X = (df[ic].replace({"": np.nan, " ": np.nan, "0": np.nan})
         .apply(pd.to_numeric, errors="coerce").to_numpy(float))
    cplt = ~np.isnan(X).any(axis=1)
    Xc = X[cplt]
    n = Xc.shape[0]

    facets: dict[str, list[int]] = {}
    for i in canon["items"]:
        facets.setdefault(i["facet"], []).append(i["order"] - 1)
    for f in facets:
        facets[f].sort()

    log = [f"完整记录 {n} 条；{len(facets)} 个 facet"]

    per_facet: dict[str, dict] = {}
    for facet, cols in facets.items():
        keys = np.array([by_order[c + 1]["key"] for c in cols], dtype=float)
        full = Xc[:, cols].sum(axis=1)
        rows = {}
        for k in range(1, 10):
            rs, balances, alphas = [], [], []
            for sub in itertools.combinations(range(10), k):
                idx = list(sub)
                part = Xc[:, [cols[i] for i in idx]].sum(axis=1)
                # 若某子集在某人身上全同分，相关仍可算（只要不是全体无方差）
                if part.std() == 0:
                    continue
                rs.append(float(np.corrcoef(part, full)[0, 1]))
                pos = int((keys[idx] > 0).sum())
                balances.append(pos)
                # Spearman-Brown：由该子集的平均题间相关估计 alpha
                sub = Xc[:, [cols[i] for i in idx]]
                if k >= 2:
                    c = np.corrcoef(sub, rowvar=False)
                    rbar = (c.sum() - k) / (k * (k - 1))
                    a = (k * rbar) / (1 + (k - 1) * rbar) if rbar > -1 / (k - 1) else 0.0
                    alphas.append(float(a))
            rs = np.array(rs)
            bal = np.array(balances)
            all_pos = int((bal == k).sum())
            all_neg = int((bal == 0).sum())
            rows[k] = {
                "n_subsets": int(rs.size),
                "r_mean": round(float(rs.mean()), 4),
                "r_min": round(float(rs.min()), 4),
                "r_max": round(float(rs.max()), 4),
                "r_p05": round(float(np.percentile(rs, 5)), 4),
                "alpha_mean": round(float(np.mean(alphas)), 4) if alphas else None,
                "forward_only_subsets": all_pos,
                "reverse_only_subsets": all_neg,
                "balanced_subsets": int(((bal >= k // 3) & (bal <= k - k // 3)).sum()),
            }
        per_facet[facet] = {
            "alpha_full": canon["facet_alphas"][facet],
            "by_k": rows,
        }

    # ---- 汇总：达到某精度所需的最小 k ----
    def min_k_for(threshold: float, use_worst: bool) -> dict:
        out = {}
        for facet, d in per_facet.items():
            key = "r_min" if use_worst else "r_mean"
            for k in range(1, 10):
                if d["by_k"][k][key] >= threshold:
                    out[facet] = k
                    break
            else:
                out[facet] = None
        return out

    thresholds = {}
    for th in (0.80, 0.85, 0.90, 0.95):
        for use_worst in (False, True):
            lab = ("最差子集" if use_worst else "平均子集") + f" r≥{th}"
            ks = min_k_for(th, use_worst)
            vals = [v for v in ks.values() if v]
            thresholds[lab] = {
                "median_k": int(np.median(vals)) if vals else None,
                "max_k": int(max(vals)) if vals else None,
                "unreachable": sum(1 for v in ks.values() if v is None),
                "by_facet": ks,
            }

    # ---- 覆盖成本：30 个 facet 各达 k 题所需的最少答题数 ----
    cover = {}
    for k in (3, 4, 5, 6, 7, 8):
        need = min(300, 30 * k)   # 下界：至少要答 30k 题
        cover[str(k)] = {"ideal_min_items": need,
                         "pct_of_300": round(need / 300 * 100, 1)}

    payload = {
        "source": "Johnson (2005) 网络样本，N=20,993（完整作答 %d 条）" % n,
        "question": "一个 facet 只答 k 题时，与完整 10 题总分有多一致？",
        "method": "枚举每个 facet 的全部 C(10,k) 子集，逐一与完整总分求相关",
        "key_metric": "r_min（最差子集）——交互设计决定了用户会走到的子集，最差情况才是要靠设计避免的",
        "per_facet": per_facet,
        "thresholds": thresholds,
        "coverage_cost": cover,
        "build_log": log,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)

    # ---- 打印摘要 ----
    print(f"完整记录 {n}；facet {len(facets)}")

    print("\n=== 全部 facet 汇总：k 题子集与完整总分的相关 ===")
    print(f"{'k':>3} {'平均':>7} {'p05':>7} {'最差':>7} {'全正向子集':>10} {'计数':>6}")
    for k in range(1, 10):
        ms = [d["by_k"][k]["r_mean"] for d in per_facet.values()]
        p5 = [d["by_k"][k]["r_p05"] for d in per_facet.values()]
        mn = [d["by_k"][k]["r_min"] for d in per_facet.values()]
        fo = sum(d["by_k"][k]["forward_only_subsets"] for d in per_facet.values())
        ns = sum(d["by_k"][k]["n_subsets"] for d in per_facet.values())
        print(f"{k:>3} {np.mean(ms):>7.3f} {np.mean(p5):>7.3f} {np.mean(mn):>7.3f} "
              f"{fo:>10} {ns:>6}")

    print("\n=== 达到某精度所需的最小 k（跨 30 个 facet）===")
    print(f"{'判据':<26}{'中位 k':>7}{'最大 k':>7}{'达不到':>8}")
    for lab, d in thresholds.items():
        print(f"{lab:<26}{str(d['median_k']):>7}{str(d['max_k']):>7}{d['unreachable']:>8}")

    print("\n=== 覆盖成本（30 facet 各达 k 题）===")
    for k, d in cover.items():
        print(f"  k={k}: 最少 {d['ideal_min_items']} 题（占全卷 {d['pct_of_300']}%）")

    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
