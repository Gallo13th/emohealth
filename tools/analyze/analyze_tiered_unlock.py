#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分级解锁的可行性分析 —— 粗粒度题库能否近似完整版？

用户的命题：**用户一开始只答一部分题，就能得到初步评估；答完某些题后解锁下一批，
逐步细化。** 关键的验证要求是：

> 计算分级后的题库得分与最后 300 题完整版得分之间的相关性，
> **确保最粗粒度的问卷也足够近似其最后的结果。**

本脚本回答这个问题。三个层次，越往下越贴近用户实际看到的：

  层次 1  单个面向内：k 题小分 vs 该面向 10 题总分         （已有，见 fullPrec）
  层次 2  维度层：12 题维度分 vs 该维度 60 题总分          （**新增**）
  层次 3  **分带一致率**：只答前 N 题给的分带，与答满 300 题给的分带
          在多少比例上相同                                   （**这才是用户看到的**）

为什么层次 3 最重要：用户看到的是「中等」「偏高」，不是原始分。
原始分相关 0.9 但分带只有七成对得上，产品上就不成立。

输出：`data/tiered-unlock.json`
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
OUT = os.path.join(ROOT, "data/tiered-unlock.json")

BANDS = ["Very Low", "Low", "Average", "High", "Very High"]
BAND_ZH = {"Very High": "很高", "High": "偏高", "Average": "中等",
           "Low": "偏低", "Very Low": "很低"}

# 候选分级：每轮 30 题（官方交错序的一轮 = 每个面向各 1 题）
TIERS = [1, 2, 3, 4, 5, 6, 8, 10]


def main() -> int:
    canon = json.load(open(CANON, encoding="utf-8"))
    uk = json.load(open(UK, encoding="utf-8"))
    items = sorted(canon["items"], key=lambda x: x["order"])

    df = pd.read_csv(DATA, sep="\t", dtype=str, keep_default_na=False)
    ic = [f"I{i}" for i in range(1, 301)]
    X = (df[ic].replace({"": np.nan, " ": np.nan, "0": np.nan})
         .apply(pd.to_numeric, errors="coerce").to_numpy(float))
    Xc = X[~np.isnan(X).any(axis=1)]
    n = Xc.shape[0]

    # 计分方向由数据自动判定，不靠假设。
    # ⚠️ 我在这里犯过错：想当然地「还原反向题」，结果 Johnson 数据**本来就是
    # 反向重编码的**，于是双重翻转——第 1 层维度相关从正确的 0.888
    # 掉到错误的 0.560，我一度把错的那个当成了修正。
    from tools.item_coding import as_construct_direction
    Xc, _coding = as_construct_direction(Xc, items, expect_recoded=True)

    # 结构（域信息在 facet_definitions，规范数据集里没有）
    from content.facet_definitions import FACETS, NORM_COLUMN  # noqa: E402
    facet_orders: dict[str, list[int]] = defaultdict(list)
    domain_facets: dict[str, list[str]] = defaultdict(list)
    for it in items:
        facet_orders[it["facet"]].append(it["order"])
    for f in FACETS:
        d = FACETS[f]["domain"]
        if f not in domain_facets[d]:
            domain_facets[d].append(f)
    for f in facet_orders:
        facet_orders[f].sort()
    for d in domain_facets:
        domain_facets[d].sort()

    def _norm(x: str) -> str:
        return "".join(ch for ch in x.lower() if ch.isalnum())

    def uk_bands(facet: str) -> dict:
        tab = uk["levels"]["facets"]["18-29"]
        want = NORM_COLUMN.get(facet, facet)
        key = want if want in tab else next(
            (k for k in tab if _norm(k) == _norm(want)), None)
        return tab.get(key, {}) if key else {}

    def uk_domain_bands(domain: str) -> dict:
        return uk["levels"]["domains"]["18-29"].get(domain.upper(), {})

    # ── 分带口径（这是本分析最关键的一处）
    #
    # 完整分带（UK 表）只对**完整分**成立。把部分分「按题数折算」再套完整版的带，
    # 会额外引入折算误差——实测那样做的话，答 40% 的题只有 59% 的分带对得上。
    #
    # 正确做法：**让每一层有自己的切割点**。
    # 取完整分带边界在完整分分布上的百分位，再把这个百分位套到该层分数的分布上。
    # 这样比较的是「同样的相对位置」，而不是「同样的绝对分数」。
    def boundaries(bands: dict) -> list[tuple[float, str]]:
        """返回 [(边界值, 上侧带名), ...]，共至多 4 个。"""
        order = ["Very Low", "Low", "Average", "High", "Very High"]
        out = []
        for a, b in zip(order, order[1:]):
            ra, rb = bands.get(a), bands.get(b)
            if not ra or not rb:
                continue
            out.append(((ra[-1] + rb[0]) / 2, b))
        return out

    ORDER = ["Very Low", "Low", "Average", "High", "Very High"]

    def tier_band_fn(full: np.ndarray, part: np.ndarray, bands: dict):
        """构造把部分分判带的函数（用百分位等价的切割点）。

        ⚠️ boundaries() 返回的是切割点的**上侧**带名。小于切割点时应取**下侧**那一档。
        初版把上侧带名直接返回，于是整档错位——答满 300 题反而只有 8% 一致。
        """
        bs = boundaries(bands)
        if not bs:
            return None
        cuts = []
        for val, upper in bs:
            pct = float((full < val).mean() * 100)
            lower = ORDER[ORDER.index(upper) - 1]
            cuts.append((float(np.percentile(part, pct)), lower))
        def f(v):
            for c, lower in cuts:
                if v < c:
                    return lower
            return "Very High"
        return f

    def plain_band_fn(bands: dict):
        order = ["Very High", "High", "Average", "Low", "Very Low"]
        def f(v):
            for name in order:
                rng = bands.get(name)
                if rng and rng[0] <= v <= rng[-1]:
                    return name
            return None
        return f

    domain_full = {}
    for d, fs in domain_facets.items():
        cols = [o - 1 for f in fs for o in facet_orders[f]]
        domain_full[d] = Xc[:, cols].sum(axis=1)

    facet_full = {f: Xc[:, [o - 1 for o in facet_orders[f]]].sum(axis=1)
                  for f in facet_orders}

    def agree_stats(bf, bp):
        """返回 (完全相同, 相差≤1档, 相差≥2档)。「同带」太苛刻——差一档与差两档是两回事。"""
        idx = {b: i for i, b in enumerate(ORDER)}
        d = [abs(idx[x] - idx[y]) for x, y in zip(bf, bp)
             if x is not None and y is not None]
        if not d:
            return None
        d = np.array(d)
        return (float((d == 0).mean()), float((d <= 1).mean()), float((d >= 2).mean()))

    # ── 贪心挑题：为每个维度挑出与「该维度 60 题总分」相关最高的 k 题。
    # 自然分级（按官方交错序取前 k 轮）不一定是最优的；
    # 这一步回答的是「挑得好能好多少」。
    def greedy_pick(cols: list[int], k: int, full: np.ndarray) -> list[int]:
        chosen: list[int] = []
        pool = list(cols)
        for _ in range(k):
            best, bi = -2.0, None
            for c in pool:
                cand = chosen + [c]
                part = Xc[:, cand].sum(axis=1)
                if part.std() == 0:
                    continue
                r = float(np.corrcoef(part, full)[0, 1])
                if r > best:
                    best, bi = r, c
            chosen.append(bi)
            pool.remove(bi)
        return chosen

    print("  正在为每个维度做贪心挑题（最优 k 题子集）…", flush=True)
    opt = {}
    for d, fs in domain_facets.items():
        cols = [o - 1 for f in fs for o in facet_orders[f]]
        opt[d] = {}
        for k in (6, 12, 18, 24, 36):
            opt[d][k] = greedy_pick(cols, k, domain_full[d])

    rows = []
    for R in TIERS:
        # 前 R 轮 = 官方交错序的前 30R 题 = 每个面向各 R 题
        sel = {f: facet_orders[f][:R] for f in facet_orders}
        # 面向层
        fr, fagree, fnear = [], [], []
        for f in facet_orders:
            cols_full = [o - 1 for o in facet_orders[f]]
            cols_part = [o - 1 for o in sel[f]]
            part = Xc[:, cols_part].sum(axis=1)
            full = Xc[:, cols_full].sum(axis=1)
            fr.append(float(np.corrcoef(part, full)[0, 1]))
            # 与完整分带的一致率：把部分分按题数折算后，用同一套常模带判带
            b = uk_bands(f)
            # 完整分用原表判带；部分分用「百分位等价」的该层切割点
            band_full = plain_band_fn(b)
            band_part = tier_band_fn(full, part, b) or band_full
            bf = np.array([band_full(v) for v in full], dtype=object)
            bp = np.array([band_part(v) for v in part], dtype=object)
            st = agree_stats(bf, bp)
            fagree.append(st[0] if st else np.nan)
            fnear.append(st[1] if st else np.nan)
        # 维度层
        dr, dagree, dnear, dfar = [], [], [], []
        dopt_r, dopt_a = [], []
        for d, fs in domain_facets.items():
            cf = [o - 1 for f in fs for o in facet_orders[f]]
            cp = [o - 1 for f in fs for o in sel[f]]
            part = Xc[:, cp].sum(axis=1)
            full = Xc[:, cf].sum(axis=1)
            dr.append(float(np.corrcoef(part, full)[0, 1]))
            b = uk_domain_bands(d)
            band_full = plain_band_fn(b)
            band_part = tier_band_fn(full, part, b) or band_full
            bf = np.array([band_full(v) for v in full], dtype=object)
            bp = np.array([band_part(v) for v in part], dtype=object)
            st = agree_stats(bf, bp)
            dagree.append(st[0] if st else np.nan)
            dnear.append(st[1] if st else np.nan)
            dfar.append(st[2] if st else np.nan)
            # 优化版：用贪心挑出的题
            oc = opt[d].get(R * len(fs))
            if oc:
                opart = Xc[:, oc].sum(axis=1)
                orr = float(np.corrcoef(opart, full)[0, 1])
                oband = tier_band_fn(full, opart, b) or band_full
                ost = agree_stats(bf, np.array([oband(v) for v in opart], dtype=object))
                dopt_r.append(orr)
                dopt_a.append(ost[0] if ost else np.nan)
        rows.append({
            "rounds": R, "items": R * 30, "pct_of_300": round(R * 30 / 300 * 100, 1),
            "per_facet_k": R,
            "facet_r_mean": round(float(np.mean(fr)), 4),
            "facet_r_min": round(float(np.min(fr)), 4),
            "facet_band_agree_mean": round(float(np.nanmean(fagree)), 4),
            "facet_band_agree_min": round(float(np.nanmin(fagree)), 4),
            "facet_band_near_mean": round(float(np.nanmean(fnear)), 4),
            "domain_r_mean": round(float(np.mean(dr)), 4),
            "domain_r_min": round(float(np.min(dr)), 4),
            "domain_band_agree_mean": round(float(np.nanmean(dagree)), 4),
            "domain_band_near_mean": round(float(np.nanmean(dnear)), 4),
            "domain_band_far_mean": round(float(np.nanmean(dfar)), 4),
            "domain_band_agree_min": round(float(np.nanmin(dagree)), 4),
            "domain_r_opt_mean": round(float(np.mean(dopt_r)), 4) if dopt_r else None,
            "domain_band_agree_opt": round(float(np.nanmean(dopt_a)), 4) if dopt_a else None,
            "facets_showable": sum(1 for R2 in [R] if R2 >= 3) * len(facet_orders),
        })

    payload = {
        "source": f"Johnson (2005) 完整作答 {n} 条；常模分带取自 UK 表（反推）",
        "question": "只答前 N 题时给出的结果，能在多大程度上近似答满 300 题的结果？",
        "why_band_agreement": "用户看到的是分带（中等/偏高），不是原始分。"
                              "原始分相关高但分带对不上，产品上就不成立。",
        "method": "前 R 轮 = 官方交错序前 30R 题 = 每个面向各 R 题；"
                  "部分分按题数折算后套用同一套常模带",
        "tiers": rows,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)

    print(f"参照样本 {n} 条｜30 个面向｜5 个维度\n")
    print("=== 分级解锁：粗粒度 vs 完整版 ===")
    print(f"{'层':>3}{'题数':>6}{'占比':>6}"
          f"{'面向r':>8}{'面向同带':>9}{'面向±1档':>10}"
          f"{'维度r':>8}{'维度同带':>9}{'维度±1档':>10}{'维度差≥2档':>11}")
    print("-" * 88)
    for r in rows:
        print(f"{r['rounds']:>3}{r['items']:>6}{r['pct_of_300']:>5.0f}%"
              f"{r['facet_r_mean']:>8.3f}{r['facet_band_agree_mean']*100:>8.1f}%"
              f"{r['facet_band_near_mean']*100:>9.1f}%"
              f"{r['domain_r_mean']:>8.3f}{r['domain_band_agree_mean']*100:>8.1f}%"
              f"{r['domain_band_near_mean']*100:>9.1f}%"
              f"{r['domain_band_far_mean']*100:>10.1f}%")
    print()
    print("=== 挑题优化：若不用自然顺序、而是贪心挑最优子集 ===")
    print(f"{'每维度题数':>10}{'自然 r':>10}{'最优 r':>10}{'自然同带':>10}{'最优同带':>10}")
    for r, k in zip(rows, [6, 12, 18, 24, 36, None, None, None]):
        if k is None or r["domain_r_opt_mean"] is None:
            continue
        print(f"{k:>10}{r['domain_r_mean']:>10.3f}{r['domain_r_opt_mean']:>10.3f}"
              f"{r['domain_band_agree_mean']*100:>9.1f}%"
              f"{r['domain_band_agree_opt']*100:>9.1f}%")
    print(f"\nwrote {os.path.relpath(OUT, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
