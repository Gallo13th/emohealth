#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""相关性网络：一道题能细化哪些分值？

用户的设想：
> 存在某种相关性网络，使得回答了 A 题和 B 题之后，回答 C 题可以对 AB 涉及的分值
> 有一个更细化的能力。

本脚本把这个设想量化成三张表：

  1. **题 → 面向**：每道题与 30 个完整面向分的相关（300×30）
     ——这是「这道题能细化什么」的直接答案
  2. **面向 ↔ 面向**：30 个完整面向分之间的相关（30×30）
     ——这是「细化会不会溢出到别的面向」
  3. **题 → 维度**：每道题与 5 个完整维度分的相关（300×5）

第 2 张表决定了「网络」到底有多强：
  · 若跨面向相关很低，则每道题只细化自己的面向，
    「网络」实际上就是**维度分组**，分层的正确做法就是均匀覆盖
  · 若跨面向相关很高，则存在真正的网络，可以用一题细化多个面向

输出：`data/correlation-network.json`
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
OUT = os.path.join(ROOT, "data/correlation-network.json")


def main() -> int:
    from content.facet_definitions import FACETS  # noqa: E402
    canon = json.load(open(CANON, encoding="utf-8"))
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
    n = Xc.shape[0]

    # ⚠️ 反向题**不要在这里翻转**。本脚本原先写 `R[:, key < 0] = 6 - R[...]`，
    #    认为数据是「题面方向」的；但实证证明 **Johnson 的 ipip20993.dat 已把反向题
    #    重编码为同向**——`build_adaptive_data.py` 的 note 也早写着「数据**已**反向
    #    重编码 —— 不要再翻转」，两处矛盾了很久。
    #
    #    裁决证据（tools/check/diagnose_ipip_recoding.py，可复跑）：
    #      148 道反向题**全部（100%）**在**未**翻转时与「同 facet 其余题之和」呈
    #      **正**相关（中位 +0.536），翻转后变负。若数据其实是题面方向，未翻转应当
    #      为负。所以多翻的那次是错的。
    #    后果（修前）：本文件与 `adaptive-network.json` 对同一量给出不同值
    #      （按名字对齐后中位 |Δ|=0.118、最大 1.389），且本题集第 1 题
    #      （Worry about things.，属 anxiety）在本文件里 argmax 指向 depression，
    #      而在 adaptive 文件里正确指向 anxiety。
    #
    #    改为**断言验证**而不是静默通过：数据若被换成未编码版本，这里立刻失败。
    key = np.array([it["key"] for it in items], float)
    R = Xc.copy()
    _sample = [it for it in items if it["key"] < 0][:20]
    _pos = 0
    for it in _sample:
        _o = it["order"]
        _others = [x for x in fo[it["facet"]] if x != _o]
        if _others and np.corrcoef(R[:, _o - 1],
                                   R[:, [x - 1 for x in _others]].sum(axis=1))[0, 1] > 0:
            _pos += 1
    if _pos < len(_sample) * 0.8:
        raise SystemExit(
            f"✗ 反向题方向校验失败：抽样的 {len(_sample)} 道反向题里只有 {_pos} 道"
            f"在未翻转时与同 facet 正相关。数据可能**未**预编码——"
            f"此时才需要 `R[:, key < 0] = 6 - R[:, key < 0]`。请先复核数据来源。")
    print(f"✓ 反向题方向校验通过：抽样 {len(_sample)} 道反向题，{_pos} 道未翻转即正相关"
          f"（数据已预编码，不做翻转）")

    facets = sorted(fo)
    domains = sorted(df)
    facet_full = {f: R[:, [o - 1 for o in fo[f]]].sum(axis=1) for f in facets}
    domain_full = {d: R[:, [o - 1 for f in df[d] for o in fo[f]]].sum(axis=1)
                   for d in domains}

    def corr(a, b):
        return float(np.corrcoef(a, b)[0, 1])

    # ── 1. 题 → 面向
    item_facet = np.zeros((300, len(facets)))
    for j, f in enumerate(facets):
        full = facet_full[f]
        for i in range(300):
            item_facet[i, j] = corr(R[:, i], full)
    # 表内对角（该题与自己面向的相关）应最高
    own_best = 0
    for i, it in enumerate(items):
        f = it["facet"]
        j = facets.index(f)
        if item_facet[i, j] == item_facet[i].max():
            own_best += 1

    # ── 2. 面向 ↔ 面向
    fcorr = np.zeros((len(facets), len(facets)))
    for a, fa in enumerate(facets):
        for b, fb in enumerate(facets):
            fcorr[a, b] = 1.0 if a == b else corr(facet_full[fa], facet_full[fb])
    off = fcorr[~np.eye(len(facets), dtype=bool)]

    # 同维度 vs 跨维度
    same_dom, cross_dom = [], []
    for a, fa in enumerate(facets):
        for b, fb in enumerate(facets):
            if a >= b:
                continue
            v = fcorr[a, b]
            (same_dom if FACETS[fa]["domain"] == FACETS[fb]["domain"]
             else cross_dom).append(v)

    # ── 3. 题 → 维度
    item_domain = np.zeros((300, len(domains)))
    for j, d in enumerate(domains):
        full = domain_full[d]
        for i in range(300):
            item_domain[i, j] = corr(R[:, i], full)

    # ── 4. 网络强度：一道题对它「非本面向」的信息量有多大？
    cross_info = []
    for i, it in enumerate(items):
        j = facets.index(it["facet"])
        others = np.delete(item_facet[i], j)
        cross_info.append(float((others ** 2).mean()))
    cross_info = np.array(cross_info)
    own_info = np.array([item_facet[i, facets.index(items[i]["facet"])] ** 2
                         for i in range(300)])

    # 每个面向的题，对**同维度其他面向**的平均解释力 vs **跨维度**
    within, across = [], []
    for i, it in enumerate(items):
        dom = FACETS[it["facet"]]["domain"]
        j = facets.index(it["facet"])
        for b, fb in enumerate(facets):
            if b == j:
                continue
            (within if FACETS[fb]["domain"] == dom else across).append(
                item_facet[i, b] ** 2)
    within, across = np.array(within), np.array(across)

    payload = {
        "source": f"Johnson (2005) 完整作答 {n} 条（反向题已还原为同向）",
        "question": "一道题能细化哪些分值？跨面向的信息溢出有多大？",
        "headline": {
            "题与自己面向的相关（中位）": round(float(np.median(
                [item_facet[i, facets.index(items[i]["facet"])] for i in range(300)])), 4),
            "题对非本面向的平均 R²": round(float(cross_info.mean()), 4),
            "题对本面向的 R²": round(float(own_info.mean()), 4),
            "面向间相关（全部，中位）": round(float(np.median(off)), 4),
            "面向间相关（同维度，中位）": round(float(np.median(same_dom)), 4),
            "面向间相关（跨维度，中位）": round(float(np.median(cross_dom)), 4),
            "题对同维度其他面向的平均 R²": round(float(within.mean()), 4),
            "题对跨维度面向的平均 R²": round(float(across.mean()), 4),
        },
        "facets": facets,
        "domains": domains,
        "facet_corr": [[round(float(v), 4) for v in row] for row in fcorr],
        "item_facet_corr": [[round(float(v), 4) for v in row] for row in item_facet],
        "item_domain_corr": [[round(float(v), 4) for v in row] for row in item_domain],
        "build_log": [f"{own_best}/300 道题与自己面向的相关是它 30 个相关里最高的"],
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)

    h = payload["headline"]
    print(f"参照样本 {n} 条\n")
    print("=== 相关性网络：一道题能细化什么 ===")
    print(f"  题与自己面向的相关（中位）      {h['题与自己面向的相关（中位）']}")
    print(f"  题对本面向的 R²（平均）          {h['题对本面向的 R²']}")
    print(f"  题对非本面向的 R²（平均）        {h['题对非本面向的平均 R²']}")
    print(f"  → 自己面向解释力是非自己面向的 "
          f"{h['题对本面向的 R²'] / max(h['题对非本面向的平均 R²'], 1e-9):.0f} 倍")
    print()
    print(f"  题对**同维度**其他面向的 R²      {h['题对同维度其他面向的平均 R²']}")
    print(f"  题对**跨维度**面向的 R²          {h['题对跨维度面向的平均 R²']}")
    print(f"  → 同维度 / 跨维度 = "
          f"{h['题对同维度其他面向的平均 R²'] / max(h['题对跨维度面向的平均 R²'], 1e-9):.1f} 倍")
    print()
    print("=== 面向之间的相关 ===")
    print(f"  全部（中位）      {h['面向间相关（全部，中位）']}")
    print(f"  同维度（中位）    {h['面向间相关（同维度，中位）']}")
    print(f"  跨维度（中位）    {h['面向间相关（跨维度，中位）']}")
    print()
    print(f"  {payload['build_log'][0]}")
    print(f"\nwrote {os.path.relpath(OUT, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
