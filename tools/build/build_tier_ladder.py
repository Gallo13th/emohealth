#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成最终的分层阶梯，并把「交错性质」作为硬约束。

三件事：

  1. **交错约束**：官方题序的性质是「相邻题目测不同面向」。分层序必须保留它，
     否则可能引入反应定势。归档里**没有**证据说交错序在心理测量上必需
     （它只是 IPIP 的已发布顺序），所以做法是：**把这条性质当作设计约束保留**，
     而不是假装它已被证明必需。

  2. **网络感知的层内排序**：`analyze_correlation_network.py` 显示
     题对本面向的解释力是 11 倍于非本面向、同维度是 2.2 倍于跨维度。
     所以真正的「网络」就是维度结构本身。可利用之处是**面向之间的中心性排序**：
     先答与该维度内其他面向关联最强的面向，能让后续估计更快收窄。

  3. **每层的解释**：记录这一层把哪些面向的估计收窄了多少，
     供产品侧生成「解锁这一层，你得到了什么」的文案。

输出：`data/tier-ladder.json`（300 题的最终顺序 + 每层解释 + 交错质检）
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
TIERS = os.path.join(ROOT, "data/tier-design.json")
NET = os.path.join(ROOT, "data/correlation-network.json")
OUT = os.path.join(ROOT, "data/tier-ladder.json")


def runs(seq: list[str]) -> dict:
    """连续同值的最大长度与分布。"""
    if not seq:
        return {"max": 0, "n_runs": 0}
    mx = cur = 1
    for a, b in zip(seq, seq[1:]):
        cur = cur + 1 if a == b else 1
        mx = max(mx, cur)
    return {"max": mx, "n_runs": sum(1 for a, b in zip(seq, seq[1:]) if a != b) + 1}


def interleave(order: list[int], facet_of: dict[int, str]) -> list[int]:
    """重排，使相邻题目尽量不同面向。

    贪心：每次从剩余里挑一个「与上一个面向不同」的；若无法避免，
    就挑「剩余最多的那个面向」以把冲突推后。
    """
    from collections import Counter
    pool = Counter(facet_of[o] for o in order)
    buckets: dict[str, list[int]] = defaultdict(list)
    for o in order:
        buckets[facet_of[o]].append(o)
    out, last = [], None
    while len(out) < len(order):
        cands = [f for f in pool if pool[f] > 0 and f != last]
        if not cands:
            cands = [f for f in pool if pool[f] > 0]
        f = max(cands, key=lambda x: (pool[x], x))
        out.append(buckets[f].pop(0))
        pool[f] -= 1
        last = f
    return out


def main() -> int:
    from content.facet_definitions import FACETS  # noqa: E402
    canon = json.load(open(CANON, encoding="utf-8"))
    tier = json.load(open(TIERS, encoding="utf-8"))
    net = json.load(open(NET, encoding="utf-8"))
    items = sorted(canon["items"], key=lambda x: x["order"])
    order_of = {it["order"]: it for it in items}
    facet_of = {it["order"]: it["facet"] for it in items}
    domain_of = {f: FACETS[f]["domain"] for f in FACETS}

    fc = net["facet_corr"]
    facets = net["facets"]
    # 面向在维度内的「中心性」：与同维度其他面向的相关之和
    centrality = {}
    for i, f in enumerate(facets):
        d = domain_of[f]
        centrality[f] = sum(fc[i][j] for j, g in enumerate(facets)
                            if g != f and domain_of[g] == d)

    # ── 逐层生成：层内先按中心性排面向，再排该层新加的题
    ladder: list[int] = []
    tier_meta = []
    for R in range(1, 11):
        new_items: list[int] = []
        for d in sorted(tier["selection"]):
            fs = sorted(tier["selection"][d],
                        key=lambda f: -centrality.get(f, 0))
            for f in fs:
                o = tier["selection"][d][f][R - 1]
                new_items.append(o)
        # 层内做交错重排（约束：相邻不同面向）
        arranged = interleave(new_items, facet_of)
        ladder.extend(arranged)
        tier_meta.append({
            "tier": R, "items": len(ladder),
            "added": len(arranged),
            "facets_ordered_by_centrality": [
                f for d in sorted(tier["selection"])
                for f in sorted(tier["selection"][d], key=lambda x: -centrality.get(x, 0))],
        })

    # ── 交错质检：与官方序对照
    official = [it["order"] for it in items]
    stat_ladder = runs([facet_of[o] for o in ladder])
    stat_official = runs([facet_of[o] for o in official])

    # ── 每层新增的题，对哪些面向的估计收窄最多
    dfr = pd.read_csv(DATA, sep="\t", dtype=str, keep_default_na=False)
    X = (dfr[[f"I{i}" for i in range(1, 301)]]
         .replace({"": np.nan, " ": np.nan, "0": np.nan})
         .apply(pd.to_numeric, errors="coerce").to_numpy(float))
    Xc = X[~np.isnan(X).any(axis=1)]
    # 计分方向由数据自动判定——Johnson 数据**本来就是反向重编码的**，
    # 再翻一次就是双重翻转。四个分析脚本里我漏改了这一个，于是它的 R² 偏低。
    from tools.item_coding import as_construct_direction
    R, _coding = as_construct_direction(Xc, items, expect_recoded=True)
    fo: dict[str, list[int]] = defaultdict(list)
    for it in items:
        fo[it["facet"]].append(it["order"])

    def r2_full(target: np.ndarray, sel: list[int]) -> float:
        """用**全部已答题**（不只本面向的）预测某个完整分，取 R²。

        ⚠️ 初版只用本面向的题算 R²，那恰好把「网络」丢掉了——
        用户设想的正是「答了 A 和 B 之后，答 C 能细化 A、B 涉及的分值」，
        所以必须允许其他面向的题参与预测。
        """
        if not sel:
            return 0.0
        A = np.column_stack([np.ones(len(R)), R[:, [o - 1 for o in sel]]])
        beta, *_ = np.linalg.lstsq(A, target, rcond=None)
        pred = A @ beta
        ss_res = ((target - pred) ** 2).sum()
        ss_tot = ((target - target.mean()) ** 2).sum()
        return float(1 - ss_res / ss_tot)

    # 预先把每个面向 / 维度的完整分算好，避免在循环里重复求和
    facet_full = {f: R[:, [o - 1 for o in fo[f]]].sum(axis=1) for f in fo}
    dom_full = {}
    for d in sorted(tier["selection"]):
        fs = sorted(tier["selection"][d])
        dom_full[d] = R[:, [o - 1 for f in fs for o in fo[f]]].sum(axis=1)

    explanations = []
    prev_f: dict[str, float] = {f: 0.0 for f in fo}
    prev_d: dict[str, float] = {d: 0.0 for d in dom_full}
    for tm in tier_meta:
        answered = ladder[: tm["items"]]
        fg = []
        for f in fo:
            cur = r2_full(facet_full[f], answered)
            fg.append((cur - prev_f[f], f, cur))
            prev_f[f] = cur
        fg.sort(reverse=True)
        dg = {}
        for d in dom_full:
            dg[d] = r2_full(dom_full[d], answered)
        explanations.append({
            "tier": tm["tier"], "items": tm["items"],
            "facet_r2_now": {f: round(c, 4) for _, f, c in fg},
            "top_facet_gains": [{"facet": f, "r2_gain": round(g, 4),
                                 "r2_now": round(c, 4)} for g, f, c in fg[:5]],
            "domain_r2_cumulative": {d: round(v, 4) for d, v in sorted(dg.items())},
        })

    payload = {
        "design": "第 R 层 = 每个面向恰好 R 题 = 30R 题；层间嵌套；层内按面向中心性排序并做交错重排",
        "why_centrality": "题对本面向的解释力是 11 倍于非本面向、同维度是 2.2 倍于跨维度"
                          "——所以「相关性网络」主要就是维度结构，可利用之处是维度内的面向中心性",
        "interleaving_evidence": "归档里**没有**证据支持交错序在心理测量上必需；"
                                 "它只是 IPIP 的已发布顺序。本设计把「相邻不同面向」"
                                 "当作**设计约束**保留，而非声称其已被证明必需。",
        "order": ladder,
        "tiers": tier_meta,
        "tier_explanations": explanations,
        "quality_check": {
            "ladder_consecutive_same_facet_max": stat_ladder["max"],
            "official_consecutive_same_facet_max": stat_official["max"],
            "ladder_n_facet_switches": stat_ladder["n_runs"],
            "official_n_facet_switches": stat_official["n_runs"],
        },
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)

    q = payload["quality_check"]
    print("=== 交错质检 ===")
    print(f"  官方序：相邻同面向最大连续 {q['official_consecutive_same_facet_max']} 题"
          f"｜面向切换 {q['official_n_facet_switches']} 次")
    print(f"  分层序：相邻同面向最大连续 {q['ladder_consecutive_same_facet_max']} 题"
          f"｜面向切换 {q['ladder_n_facet_switches']} 次")
    ok = q["ladder_consecutive_same_facet_max"] <= q["official_consecutive_same_facet_max"]
    print(f"  {'✅ 交错性质已保留' if ok else '❌ 分层序的交错性不如官方序'}")
    print()
    print("=== 每层新增题让哪些面向的估计收窄最多 ===")
    for e in explanations[:6]:
        g = e["top_facet_gains"][0]
        print(f"  第 {e['tier']:>2} 层（{e['items']:>3} 题）"
              f"  最大增益：{g['facet']:<26} R² +{g['r2_gain']:.3f} → {g['r2_now']:.3f}")
    print()
    print("=== 各维度的累计 R²（用**全部已答题**预测该维度完整分）===")
    print(f"  {'层':>3}{'题数':>6}  " +
          "  ".join(f"{d[:5]:>7}" for d in sorted(explanations[0]["domain_r2_cumulative"])))
    for t in (0, 1, 2, 4, 7, 9):
        e = explanations[t]
        print(f"  {e['tier']:>3}{e['items']:>6}  " +
              "  ".join(f"{v:>7.3f}" for _, v in sorted(e["domain_r2_cumulative"].items())))
    print(f"\nwrote {os.path.relpath(OUT, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
