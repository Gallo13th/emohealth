#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分级解锁的**约束优化** —— 设计可用的分层题库。

前一版分析（`analyze_tiered_unlock.py`）发现两件事：

  1. 「同带」太苛刻，真正的判据是「差 ≥2 档的比例」。30 题时差 ≥2 档只有 2.9%。
  2. **纯贪心挑题会牺牲广度**——神经质的前 6 题只覆盖 3/6 个面向
     （抑郁 3 题、焦虑 2 题）。而「逐步细化」的故事恰恰要求广度。

所以本脚本做**带约束的优化**：

  · 每个维度含 6 个面向，每个面向 10 题
  · 第 R 层 = 每个面向恰好 R 题 = 30R 题
  · 层与层是**嵌套**的（第 R 层包含第 R−1 层的题）
  · 在同一层内，选哪 R 题要**联合优化**，使该维度分与完整 60 题总分的相关最大

这是一个平衡嵌套设计：广度由约束保证，精度由优化争取。

输出：`data/tier-design.json`（每层每面向选哪几题 + 精度指标）
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
OUT = os.path.join(ROOT, "data/tier-design.json")

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
    # 计分方向由数据自动判定，不靠假设。
    # ⚠️ 我在这里犯过错：想当然地「还原反向题」，结果 Johnson 数据**本来就是
    # 反向重编码的**，于是双重翻转——第 1 层维度相关从正确的 0.888
    # 掉到错误的 0.560，我一度把错的那个当成了修正。
    from tools.item_coding import as_construct_direction
    Xc, _coding = as_construct_direction(Xc, items, expect_recoded=True)

    n = Xc.shape[0]

    def domain_bands(d: str) -> dict:
        return uk["levels"]["domains"]["18-29"].get(d.upper(), {})

    def boundaries(bands: dict):
        out = []
        for a, b in zip(ORDER, ORDER[1:]):
            ra, rb = bands.get(a), bands.get(b)
            if ra and rb:
                out.append(((ra[-1] + rb[0]) / 2, b))
        return out

    def plain_fn(bands):
        def f(v):
            for name in reversed(ORDER):
                rng = bands.get(name)
                if rng and rng[0] <= v <= rng[-1]:
                    return name
            return None
        return f

    def tier_fn(full, part, bands):
        bs = boundaries(bands)
        if not bs:
            return None
        cuts = []
        for val, upper in bs:
            pct = float((full < val).mean() * 100)
            cuts.append((float(np.percentile(part, pct)), ORDER[ORDER.index(upper) - 1]))
        def f(v):
            for c, lower in cuts:
                if v < c:
                    return lower
            return "Very High"
        return f

    def agree(bf, bp):
        ix = {b: i for i, b in enumerate(ORDER)}
        d = np.array([abs(ix[x] - ix[y]) for x, y in zip(bf, bp)
                      if x is not None and y is not None])
        if not d.size:
            return None
        return (float((d == 0).mean()), float((d <= 1).mean()), float((d >= 2).mean()))

    # ── 平衡嵌套贪心：第 R 层每个面向恰好 R 题，逐层加题
    design: dict[str, dict[str, list[int]]] = {}
    for d in sorted(df):
        fs = df[d]
        cols = [o - 1 for f in fs for o in fo[f]]
        full = Xc[:, cols].sum(axis=1)
        chosen: dict[str, list[int]] = {f: [] for f in fs}
        for R in range(1, 11):
            # 本轮每个面向各加 1 题；面向之间轮流贪心，取全局最优的那一步
            pending = set(fs)
            while pending:
                best = (-2.0, None, None)
                for f in pending:
                    for o in fo[f]:
                        if o in chosen[f]:
                            continue
                        # 增量构建时各面向题数会短暂相差 1，这是正常的——
                        # 初版在这里加了个「必须已凑满整层」的长度检查，导致永远无候选。
                        sel = [c - 1 for g in fs
                               for c in (chosen[g] + ([o] if g == f else []))]
                        part = Xc[:, sel].sum(axis=1)
                        if part.std() == 0:
                            continue
                        r = float(np.corrcoef(part, full)[0, 1])
                        if r > best[0]:
                            best = (r, f, o)
                _, f, o = best
                chosen[f].append(o)
                pending.discard(f)
        design[d] = chosen

    # ── 评估每一层
    tiers = []
    for R in range(1, 11):
        dr, dagree, dnear, dfar = [], [], [], []
        fr, fagree, fnear = [], [], []
        for d in sorted(df):
            fs = df[d]
            cols = [o - 1 for f in fs for o in fo[f]]
            full = Xc[:, cols].sum(axis=1)
            sel = [c - 1 for f in fs for c in design[d][f][:R]]
            part = Xc[:, sel].sum(axis=1)
            dr.append(float(np.corrcoef(part, full)[0, 1]))
            b = domain_bands(d)
            st = agree(np.array([plain_fn(b)(v) for v in full], dtype=object),
                       np.array([(tier_fn(full, part, b) or plain_fn(b))(v)
                                 for v in part], dtype=object))
            if st:
                dagree.append(st[0]); dnear.append(st[1]); dfar.append(st[2])
            # 面向层：这一层每个面向恰好 R 题
            for f in fs:
                cf = [o - 1 for o in fo[f]]
                cp = [o - 1 for o in design[d][f][:R]]
                pf = Xc[:, cf].sum(axis=1)
                pp = Xc[:, cp].sum(axis=1)
                if pp.std() == 0:
                    continue
                fr.append(float(np.corrcoef(pp, pf)[0, 1]))
                fb = uk["levels"]["facets"]["18-29"]
                key = next((k for k in fb if k.lower().startswith(f[:5])), None)
                if key:
                    st2 = agree(np.array([plain_fn(fb[key])(v) for v in pf], dtype=object),
                                np.array([(tier_fn(pf, pp, fb[key]) or plain_fn(fb[key]))(v)
                                          for v in pp], dtype=object))
                    if st2:
                        fagree.append(st2[0]); fnear.append(st2[1])
        tiers.append({
            "tier": R, "items": R * 30, "pct": round(R * 30 / 300 * 100, 1),
            "per_facet": R,
            "domain_r_mean": round(float(np.mean(dr)), 4),
            "domain_r_min": round(float(np.min(dr)), 4),
            "domain_same_band": round(float(np.mean(dagree)) * 100, 1) if dagree else None,
            "domain_within_1": round(float(np.mean(dnear)) * 100, 1) if dnear else None,
            "domain_off_2plus": round(float(np.mean(dfar)) * 100, 1) if dfar else None,
            "facet_r_mean": round(float(np.mean(fr)), 4) if fr else None,
            "facet_same_band": round(float(np.mean(fagree)) * 100, 1) if fagree else None,
            "facet_within_1": round(float(np.mean(fnear)) * 100, 1) if fnear else None,
        })

    payload = {
        "source": f"Johnson (2005) 完整作答 {n} 条；常模分带取自 UK 表",
        "design": "平衡嵌套：第 R 层 = 每个面向恰好 R 题 = 30R 题；层与层嵌套；"
                  "层内选哪几题经联合优化以最大化维度分与完整分的相关",
        "constraint_note": "纯贪心会牺牲广度（神经质前 6 题只覆盖 3/6 个面向），"
                           "所以强制每面向每层各 1 题",
        "selection": {d: {f: v for f, v in design[d].items()} for d in sorted(design)},
        "tiers": tiers,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)

    print(f"参照样本 {n} 条\n")
    print("=== 优化后的平衡嵌套分层（每层每面向各 1 题）===")
    print(f"{'层':>3}{'题数':>6}{'占比':>6}"
          f"{'维度r均':>9}{'维度r最差':>10}{'维度同带':>9}{'±1档':>8}{'差≥2档':>9}"
          f"{'面向r均':>9}{'面向同带':>9}")
    print("-" * 84)
    for t in tiers:
        print(f"{t['tier']:>3}{t['items']:>6}{t['pct']:>5.0f}%"
              f"{t['domain_r_mean']:>9.3f}{t['domain_r_min']:>10.3f}"
              f"{(t['domain_same_band'] or 0):>8.1f}%{(t['domain_within_1'] or 0):>7.1f}%"
              f"{(t['domain_off_2plus'] or 0):>8.1f}%"
              f"{(t['facet_r_mean'] or 0):>9.3f}{(t['facet_same_band'] or 0):>8.1f}%")
    print(f"\nwrote {os.path.relpath(OUT, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
