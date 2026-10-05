#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分层设计的**过拟合检验**。

挑题是在参照样本上做的（从 60 题里挑 6 题，使与完整分的相关最大）。
若在同一批样本上评估，相关性会被高估——**这是典型的选择性过拟合**。

所以必须拆半：**在一半样本上挑题，在另一半上评估**。
若两半的指标接近，说明这套选法能泛化；若差很多，说明只是把噪音拟合了。

用法：python3 tools/check/validate_tier_design.py
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
DATA = os.path.join(ROOT, "archive/datasets/osf-johnson/validity/ipip20993.dat")
CANON = os.path.join(ROOT, "data/ipip-neo-300.json")
UK = os.path.join(ROOT, "data/uk-norms.json")

ORDER = ["Very Low", "Low", "Average", "High", "Very High"]


def main() -> int:
    from content.facet_definitions import FACETS  # noqa: E402
    canon = json.load(open(CANON, encoding="utf-8"))
    uk = json.load(open(UK, encoding="utf-8"))
    items = sorted(canon["items"], key=lambda x: x["order"])
    fo: dict[str, list[int]] = defaultdict(list)
    df: dict[str, list[str]] = defaultdict(list)
    for it in items:
        fo[it["facet"]].append(it["order"])
    for f in FACETS:
        if f not in df[FACETS[f]["domain"]]:
            df[FACETS[f]["domain"]].append(f)
    for f in fo:
        fo[f].sort()
    for d in df:
        df[d].sort()

    dfr = pd.read_csv(DATA, sep="\t", dtype=str, keep_default_na=False)
    X = (dfr[[f"I{i}" for i in range(1, 301)]]
         .replace({"": np.nan, " ": np.nan, "0": np.nan})
         .apply(pd.to_numeric, errors="coerce").to_numpy(float))
    Xc = X[~np.isnan(X).any(axis=1)]
    # 计分方向由数据自动判定，不靠假设。
    # ⚠️ 我在这里犯过错：想当然地「还原反向题」，结果 Johnson 数据**本来就是
    # 反向重编码的**，于是双重翻转——第 1 层维度相关从正确的 0.888
    # 掉到错误的 0.560，我一度把错的那个当成了修正。
    from tools.item_coding import as_construct_direction
    Xc, _coding = as_construct_direction(Xc, items, expect_recoded=True)

    rng = np.random.default_rng(20260930)
    idx = rng.permutation(Xc.shape[0])
    A, B = Xc[idx[:len(idx) // 2]], Xc[idx[len(idx) // 2:]]

    def bands_of(d):
        return uk["levels"]["domains"]["18-29"].get(d.upper(), {})

    def boundaries(b):
        return [((b[a][-1] + b[c][0]) / 2, c) for a, c in zip(ORDER, ORDER[1:])
                if b.get(a) and b.get(c)]

    def plain(b):
        def f(v):
            for name in reversed(ORDER):
                r = b.get(name)
                if r and r[0] <= v <= r[-1]:
                    return name
            return None
        return f

    def tier_fn(full, part, b):
        cuts = []
        for val, up in boundaries(b):
            pct = float((full < val).mean() * 100)
            cuts.append((float(np.percentile(part, pct)), ORDER[ORDER.index(up) - 1]))
        def f(v):
            for c, lo in cuts:
                if v < c:
                    return lo
            return "Very High"
        return f

    def agree(bf, bp):
        ix = {x: i for i, x in enumerate(ORDER)}
        d = np.array([abs(ix[x] - ix[y]) for x, y in zip(bf, bp)
                      if x is not None and y is not None])
        return None if not d.size else (float((d == 0).mean()),
                                        float((d <= 1).mean()),
                                        float((d >= 2).mean()))

    def greedy(cols, k, full, XX):
        chosen, pool = [], list(cols)
        for _ in range(k):
            best, bi = -2.0, None
            for c in pool:
                p = XX[:, chosen + [c]].sum(axis=1)
                if p.std() == 0:
                    continue
                r = float(np.corrcoef(p, full)[0, 1])
                if r > best:
                    best, bi = r, c
            chosen.append(bi); pool.remove(bi)
        return chosen

    def balanced(fs, XX, full, k):
        """平衡嵌套：每个面向恰好 k 题。"""
        chosen = {f: [] for f in fs}
        for _ in range(k):
            pending = set(fs)
            while pending:
                best = (-2.0, None, None)
                for f in pending:
                    for o in fo[f]:
                        if o in chosen[f]:
                            continue
                        sel = [c - 1 for g in fs
                               for c in (chosen[g] + ([o] if g == f else []))]
                        p = XX[:, sel].sum(axis=1)
                        if p.std() == 0:
                            continue
                        r = float(np.corrcoef(p, full)[0, 1])
                        if r > best[0]:
                            best = (r, f, o)
                _, f, o = best
                chosen[f].append(o); pending.discard(f)
        return chosen

    def evaluate(sel_by_domain, XX, tag):
        dr, dsame, dnear, dfar = [], [], [], []
        for d in sorted(df):
            fs = df[d]
            cols = [o - 1 for f in fs for o in fo[f]]
            full = XX[:, cols].sum(axis=1)
            sel = [c - 1 for f in fs for c in sel_by_domain[d][f]]
            part = XX[:, sel].sum(axis=1)
            dr.append(float(np.corrcoef(part, full)[0, 1]))
            b = bands_of(d)
            st = agree(np.array([plain(b)(v) for v in full], dtype=object),
                       np.array([tier_fn(full, part, b)(v) for v in part], dtype=object))
            if st:
                dsame.append(st[0]); dnear.append(st[1]); dfar.append(st[2])
        return {"r": float(np.mean(dr)), "r_min": float(np.min(dr)),
                "same": float(np.mean(dsame)) * 100,
                "near": float(np.mean(dnear)) * 100,
                "far": float(np.mean(dfar)) * 100}

    print(f"拆半：A 半 {A.shape[0]} 条用于**挑题**，B 半 {B.shape[0]} 条用于**评估**\n")
    # k = **每个面向**的题数（一个面向只有 10 题，故 k≤10）；总题数 = 30k
    print(f"{'层':>3}{'题数':>6}{'A挑A评':>10}{'A挑B评':>10}"
          f"{'B挑A评':>10}{'自然顺序':>10}")
    print("-" * 52)
    result = {}
    for k in (1, 2, 3, 5, 8, 10):
        sa, sb = {}, {}
        for d in sorted(df):
            fs = df[d]
            cols = [o - 1 for f in fs for o in fo[f]]
            sa[d] = balanced(fs, A, A[:, cols].sum(axis=1), k)
            sb[d] = balanced(fs, B, B[:, cols].sum(axis=1), k)
        inA = evaluate(sa, A, "A")
        outB = evaluate(sa, B, "B")          # 挑题在 A，评估在 B —— 这才是诚实的数
        inB = evaluate(sb, B, "B")
        outA = evaluate(sb, A, "A")
        # 自然顺序（每面向取前 k/6 题）作为对照
        nat = {d: {f: fo[f][:k] for f in df[d]} for d in sorted(df)}
        natr = evaluate(nat, B, "nat")
        print(f"{k:>3}{k*30:>6}{inA['r']:>10.3f}{outB['r']:>10.3f}"
              f"{outA['r']:>10.3f}{natr['r']:>10.3f}")
        result[k] = {"items": k * 30, "fit_in_sample": round(inA["r"], 4),
                     "holdout_A_to_B": round(outB["r"], 4),
                     "holdout_B_to_A": round(outA["r"], 4),
                     "natural_order": round(natr["r"], 4),
                     "holdout_same_band": round(outB["same"], 1),
                     "holdout_within_1": round(outB["near"], 1),
                     "holdout_off_2plus": round(outB["far"], 1)}
    print()
    print("\n=== 分带一致率（**留出集**上的诚实数字）===")
    print(f"{'层':>3}{'题数':>6}{'同带':>9}{'±1档':>9}{'差≥2档':>10}")
    print("-" * 40)
    for k, v in result.items():
        print(f"{k:>3}{k*30:>6}{v['holdout_same_band']:>8.1f}%"
              f"{v['holdout_within_1']:>8.1f}%{v['holdout_off_2plus']:>9.1f}%")

    out = os.path.join(ROOT, "data/tier-validation.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"method": "拆半交叉验证：一半挑题、另一半评估",
                   "results": result}, fh, ensure_ascii=False, indent=1)
    print(f"\nwrote {os.path.relpath(out, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
