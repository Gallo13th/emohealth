#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为「分级解锁」打包界面数据。

分层阶梯度已经把 300 题排成了 10 层。界面要能：

  1. 按**阶梯顺序**呈现题目（不再是官方 1..300 序）
  2. 第 1 层答完就给 **5 个维度的分带**（每面向仅 1 题，不能给面向分）
  3. 第 3 层起**逐层解锁 30 个面向**
  4. 每一步都按**实际已答题集**查精度，不做线性外推

关键点：**面向级的精度表不需要重算**——`r(子集, 完整分)` 是「题目集合」的属性，
与施测先后无关。变的是「某个前缀覆盖了每个面向的哪几题」，这是可以预先算好的：
阶梯固定 → 可达状态只有 301 个前缀。

所以本脚本预计算：
  · `prefixFacetR[p][f]`  —— 答完前 p 题时，面向 f 的估计与完整分的相关
  · `prefixFacetK[p][f]`  —— 答完前 p 题时，面向 f 答了几题
  · `prefixDomainR2[p][d]` —— 答完前 p 题时，维度 d 的估计对完整分的 R²

301 × (30 + 30 + 5) ≈ 20,000 个数，可完整嵌入。

输出：`data/tier-prefix.json`（**数据层只到这里**）。

前端包 `ui/tier-data.js`（`window.EMOHEALTH_TIER`）由前端层的
`tools/ui/pack_ui_data.py` 从这份 JSON 打包——数据层不再写 `ui/`（契约 C3）。
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
LADDER = os.path.join(ROOT, "data/tier-ladder.json")
DESIGN = os.path.join(ROOT, "data/tier-design.json")
UK = os.path.join(ROOT, "data/uk-norms.json")
OUT_JSON = os.path.join(ROOT, "data/tier-prefix.json")   # 引擎读这份；前端包由它打包


def main() -> int:
    from content.facet_definitions import FACETS  # noqa: E402
    canon = json.load(open(CANON, encoding="utf-8"))
    ladder = json.load(open(LADDER, encoding="utf-8"))
    design = json.load(open(DESIGN, encoding="utf-8"))
    uk = json.load(open(UK, encoding="utf-8"))
    items = sorted(canon["items"], key=lambda x: x["order"])
    by_order = {it["order"]: it for it in items}

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

    order = ladder["order"]
    assert sorted(order) == list(range(1, 301)), "阶梯必须是 300 题的一个排列"

    # 每题属于第几层
    tier_of_pos = {}
    for t in ladder["tiers"]:
        start = 0 if t["tier"] == 1 else ladder["tiers"][t["tier"] - 2]["items"]
        for p in range(start, t["items"]):
            tier_of_pos[p] = t["tier"]

    # ── 参照样本
    dfr = pd.read_csv(DATA, sep="\t", dtype=str, keep_default_na=False)
    X = (dfr[[f"I{i}" for i in range(1, 301)]]
         .replace({"": np.nan, " ": np.nan, "0": np.nan})
         .apply(pd.to_numeric, errors="coerce").to_numpy(float))
    Xc = X[~np.isnan(X).any(axis=1)]
    R, coding = as_construct_direction(Xc, items, expect_recoded=True)

    facet_full = {f: R[:, [o - 1 for o in fo[f]]].sum(axis=1) for f in fo}
    dom_full = {d: R[:, [o - 1 for f in df[d] for o in fo[f]]].sum(axis=1)
                for d in df}
    # 目标分的总平方和只算一次，避免每个前缀重算
    _sst = {d: float(((dom_full[d] - dom_full[d].mean()) ** 2).sum()) for d in dom_full}

    def corr(a, b):
        return float(np.corrcoef(a, b)[0, 1])

    def r2(target, sel, sst=None):
        """用全部已答题回归 target 的 R²。

        ⚠️ 性能：每个前缀都做一次最多 301 个预测变量的最小二乘，太慢
        （实测 301×5 次 ≈ 37 分钟）。所以**每 STEP 题算一个点，其余线性插值**——
        R² 随题量是平滑单调的，插值误差可忽略（见下方 build_log 的自检）。
        """
        if not sel:
            return 0.0
        A = np.column_stack([np.ones(len(R)), R[:, [o - 1 for o in sel]]])
        beta, *_ = np.linalg.lstsq(A, target, rcond=None)
        pred = A @ beta
        ss = sst if sst is not None else float(((target - target.mean()) ** 2).sum())
        return float(1 - ((target - pred) ** 2).sum() / ss)

    # ⚠️ 面向顺序必须与 `build_ui_bundle.py` 完全一致。
    # 界面数据包按「维度分组」排（神经质→外向性→开放性→宜人性→尽责性），
    # 这里初版用了 sorted()（字母序），两个包的面向索引错位——
    # 结果是 domainBlock 在 6 题里只找到 2 题，且不报错。
    DOM_KEY = ["neuroticism", "extraversion", "openness",
               "agreeableness", "conscientiousness"]
    facets = [f for dk in DOM_KEY for f in FACETS if FACETS[f]["domain"] == dk]
    assert len(facets) == 30, f"面向数应为 30，得到 {len(facets)}"
    domains = sorted(df, key=lambda d: DOM_KEY.index(d))

    # ── 按维度分块：某维度答了 R×6 题时，与完整 60 题分的相关
    # （实测 6 题就有 0.85–0.92，所以「某维度一环答完就出该维度结果」站得住）
    block = {}
    for d in domains:
        fs_d = df[d]
        rows = []
        for Rt in range(1, 11):
            sel = [o for t in range(Rt) for o in order[
                    0 if t == 0 else ladder["tiers"][t - 1]["items"]:
                    ladder["tiers"][t]["items"]]
                   if by_order[o]["facet"] in fs_d]
            rows.append(round(float(np.corrcoef(
                R[:, [o - 1 for o in sel]].sum(axis=1),
                R[:, [o - 1 for f in fs_d for o in fo[f]]].sum(axis=1))[0, 1]), 4))
        block[d] = rows

    # ── 面向级连接网络
    #
    # 为什么画在**面向级**而不是题目级：
    #   · 题目级：每道题对**本面向**的解释力是 11 倍于别的面向（0.171 vs 0.0154），
    #     所以够格的题目级边又稀又噪，画出来「只有一两条」，反而难看
    #   · 面向级：相关矩阵稳定、可解释，且**确实有跨维度的强边**
    #     （最强的一条：审慎—追求刺激 +0.579，跨维度）
    #
    # 这也正是决策树能给出的东西——实测树在预测上不优于线性
    # （见 `data/model-comparison.json`），所以「结构」就是相关结构本身。
    net = json.load(open(os.path.join(ROOT, "data/correlation-network.json"),
                         encoding="utf-8"))
    fc = net["facet_corr"]
    # ⚠️ `facet_corr` 是按 **correlation-network.json 自己的面向顺序**索引的，
    # 与本文件的 `facets` 顺序**不同**。直接拿矩阵下标当本文件下标，
    # 会把边接到错误的面向名上——矩阵没错，标签错了，而且**不报错**。
    # 实测踩过：真实最强对是 cautiousness—excitementseeking (+0.579)，
    # 被贴成了 assertiveness—emotionality。
    _src = net["facets"]
    assert set(_src) == set(facets), "两个数据文件的面向集合不一致"
    _perm = [_src.index(f) for f in facets]        # 本文件下标 → 矩阵下标
    fpair = []
    for a in range(len(facets)):
        for b in range(a + 1, len(facets)):
            v = fc[_perm[a]][_perm[b]]
            if abs(v) >= 0.25:
                fpair.append({"a": a, "b": b, "r": round(float(v), 4),
                              "same_domain": FACETS[facets[a]]["domain"]
                                             == FACETS[facets[b]]["domain"]})
    fpair.sort(key=lambda x: -abs(x["r"]))
    print(f"  面向级连接：|r|≥0.25 的有 {len(fpair)} 对"
          f"（其中跨维度 {sum(1 for x in fpair if not x['same_domain'])} 对）")
    # 自检：与直接遍历矩阵得到的最强对必须一致
    _best_raw = max(((abs(fc[i][j]), _src[i], _src[j])
                     for i in range(30) for j in range(i + 1, 30)))
    _top = fpair[0]
    assert {facets[_top["a"]], facets[_top["b"]]} == {_best_raw[1], _best_raw[2]}, (
        f"面向级连接的自检失败：得到 {facets[_top['a']]}—{facets[_top['b']]}，"
        f"矩阵直接算出的最强对是 {_best_raw[1]}—{_best_raw[2]}")
    print(f"  自检通过：最强对 {_best_raw[1]}—{_best_raw[2]} |r|={_best_raw[0]:.3f}")

    # ── 跨面向连接：每题最能细化哪个别的面向
    edges = {}
    IF = np.zeros((300, len(facets)))
    for j, f in enumerate(facets):
        full = R[:, [o - 1 for o in fo[f]]].sum(axis=1)
        for i in range(300):
            IF[i, j] = float(np.corrcoef(R[:, i], full)[0, 1])
    for o in order:
        i = o - 1
        j = facets.index(by_order[o]["facet"])
        cand = [(float(IF[i, b] ** 2), b) for b in range(len(facets)) if b != j]
        cand.sort(reverse=True)
        strong = [(round(v, 4), facets[b]) for v, b in cand[:3] if v >= 0.20]
        edges[str(o)] = {"own": round(float(IF[i, j] ** 2), 4), "links": strong}

    # ── 每环每面向的题号（天赋树节点）
    ring_nodes = [[None] * len(facets) for _ in range(10)]
    for t in range(1, 11):
        start = 0 if t == 1 else ladder["tiers"][t - 2]["items"]
        end = ladder["tiers"][t - 1]["items"]
        for o in order[start:end]:
            ring_nodes[t - 1][facets.index(by_order[o]["facet"])] = o
    for t in range(10):
        assert all(x is not None for x in ring_nodes[t]), f"第 {t+1} 环有面向缺题"
        assert len(set(ring_nodes[t])) == 30, f"第 {t+1} 环题数不是 30"



    # ── 预计算 301 个前缀
    # 面向级的 r 便宜（只是相关），逐题算；维度级的 R² 贵（最小二乘），每 STEP 题算一次
    STEP = 2
    print("预计算 301 个前缀的精度（维度 R² 低段每 2 题、高段每 10 题取锚点，其余插值）…",
          flush=True)
    p_facet_r: list[list[float | None]] = []
    p_facet_k: list[list[int]] = []
    for p in range(301):
        answered = order[:p]
        aset = set(answered)
        kr, kk = [], []
        for f in facets:
            sel = [o for o in fo[f] if o in aset]
            kk.append(len(sel))
            kr.append(round(corr(R[:, [o - 1 for o in sel]].sum(axis=1),
                                 facet_full[f]), 4) if len(sel) >= 1 else None)
        p_facet_r.append(kr)
        p_facet_k.append(kk)

    # 自适应步长：R² 在低题量处上升快、高题量处趋于平缓。
    # 统一用 STEP=5 时插值最大偏差 0.043（R² 尺度），会影响临界判带；
    # 低段加密后偏差显著下降，而锚点数几乎不变。
    anchors = sorted(set(
        list(range(0, 61, 2)) + list(range(60, 301, 10)) + [300]))
    node_r2 = {p: [r2(dom_full[d], order[:p], _sst[d]) for d in domains]
               for p in anchors}
    print(f"  {len(anchors)} 个锚点算完，插值到 301 个前缀", flush=True)
    p_domain_r2: list[list[float]] = []
    for p in range(301):
        lo = max(a for a in anchors if a <= p)
        hi = min(a for a in anchors if a >= p)
        if lo == hi:
            row = node_r2[lo]
        else:
            w = (p - lo) / (hi - lo)
            row = [node_r2[lo][i] * (1 - w) + node_r2[hi][i] * w
                   for i in range(len(domains))]
        p_domain_r2.append([round(v, 4) for v in row])

    # ── 插值自检：拿几个非锚点跟真值比
    _chk = []
    for p in (17, 43, 128, 217):
        if p in node_r2:
            continue
        true = [r2(dom_full[d], order[:p], _sst[d]) for d in domains]
        interp = p_domain_r2[p]
        _chk.append(max(abs(a - b) for a, b in zip(true, interp)))
    if _chk:
        print(f"  插值自检：最大偏差 {max(_chk):.5f}", flush=True)

    # ── 维度分带（UK 表）
    dom_bands = {}
    for d in domains:
        dom_bands[d] = uk["levels"]["domains"]["18-29"].get(d.upper(), {})

    # ── 每层的维度 r（直接取自设计文件，供界面显示「这一层能说什么」）
    tier_domain_r = [{"tier": t["tier"], "items": t["items"],
                      "r_mean": t["domain_r_mean"], "r_min": t["domain_r_min"],
                      "same_band": t["domain_same_band"],
                      "within_1": t["domain_within_1"],
                      "off_2plus": t["domain_off_2plus"]}
                     for t in design["tiers"]]

    payload = {
        "meta": {
            "coding": coding["verdict"],
            "design": ladder["design"],
            "n_items": 300, "n_tiers": 10, "n_facets": len(facets),
            "n_domains": len(domains),
            "interpolation": f"维度 R² 低段每 {STEP} 题、高段每 10 题取锚点，其余线性插值"
                             + (f"；自检最大偏差 {max(_chk):.5f}" if _chk else ""),
            "note": "面向级精度表无需重算——r(子集,完整分) 与施测先后无关；"
                    "变的只是「某个前缀覆盖了每个面向的哪几题」",
        },
        "order": order,
        # tierRingNodes[t-1][f] = 第 t 层、面向 f 的题号（天赋树的节点）
        "tierRingNodes": ring_nodes,
        "blockDomainR": block,      # 维度 → 各环答完时的相关（10 个值）
        "edges": edges,             # 题号 → 它细化得最多的其他面向（题级，备用）
        "facetPairs": fpair,        # 面向级连接网络（界面上画的就是这个）
        "tierOfPos": [tier_of_pos[p] for p in range(300)],
        "tierItems": [t["items"] for t in ladder["tiers"]],
        "facets": facets,
        "domains": domains,
        "domainNamesZh": [FACETS[df[d][0]]["domain_zh"] for d in domains],
        "domainBands": dom_bands,
        # 域 → 面向索引（界面算维度分带要用）
        "domainFacetIdx": {d: [facets.index(f) for f in df[d]] for d in domains},
        "domainFacetCount": {d: len(df[d]) for d in domains},
        "tierDomainR": tier_domain_r,
        "prefixFacetR": p_facet_r,
        "prefixFacetK": p_facet_k,
        "prefixDomainR2": p_domain_r2,
    }

    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))

    size = os.path.getsize(OUT_JSON)
    print(f"数据包 → {os.path.relpath(OUT_JSON, ROOT)}  ({size/1024:.0f} KB)"
          f"（前端包 ui/tier-data.js 由 tools/ui/pack_ui_data.py 打包）")
    print(f"  {coding['verdict']}")
    print(f"  阶梯 {len(order)} 题 / {len(ladder['tiers'])} 层")
    print()
    print("=== 各层：题数、维度精度、面向解锁数 ===")
    print(f"{'层':>3}{'累计题':>7}{'维度r均':>9}{'±1档':>8}"
          f"{'可给面向数':>11}{'面向 r 中位':>12}")
    print("-" * 54)
    for t in ladder["tiers"]:
        p = t["items"]
        ks = p_facet_k[p]
        rs = [r for r, k in zip(p_facet_r[p], ks) if k >= 3 and r is not None]
        td = next(x for x in tier_domain_r if x["tier"] == t["tier"])
        med = float(np.median(rs)) if rs else 0.0
        print(f"{t['tier']:>3}{p:>7}{td['r_mean']:>9.3f}"
              f"{(td['within_1'] or 0):>7.1f}%{len(rs):>11}{med:>12.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
