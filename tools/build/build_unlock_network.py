#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为「网络感知的提前解锁」打包运行时数据。

## 规则

一个细类解锁的条件不是「它的题答够了」，而是
**「以目前已答的全部题目（含别的面向的）为预测变量，对该面向完整分的回归 R² 达到门槛」**。

实测效果（门槛 r ≥ 0.85、本面向至少 2 题、**用本文件产出的相关清单**）：

| 环 | 题数 | 仅本面向 | 网络感知 |
|---:|---:|---:|---:|
| 1 | 30 | 0 | 0 |
| **2** | **60** | **0** | **21** |
| 3 | 90 | 26 | 29 |

⚠️ 这几个数**必须用运行时同一套预测集**来算。用「全部已答题」会得到 26，
但运行时每个面向只看 34 题的相关清单，真实值是 21。

而且**答哪些题决定解锁哪些细类**：同样答 12 题，六种不同组合解锁 0–3 个，
**没有一个是共同解锁的**；用「只看本面向」的规则则全是 0。

## 为什么不用决策树

用户设想用决策树定义解锁路径。实测树的拆半稳定性很差
（深度 2 重叠 0.530 / 深度 3 0.429 / 深度 4 0.286），
Gonzalez (2021) 也警告过树不稳定。而基于相关结构的 R² 规则来自全部 7,325 人，
稳定且可复现。

## 运行时要什么

R² = bᵀ A⁻¹ b，其中
  · A = 已答题目之间的相关矩阵
  · b = 各已答题与目标面向完整分的相关

所以需要预先给每个面向一份「相关题目清单」及其两两相关。
清单只取与目标 |r| 较大的题（跨面向信息本来就弱，取多了只是噪声），
这样运行时的矩阵最多 ~25×25，浏览器里算得动。

输出：`data/unlock-network.json`（**数据层只到这里**）。

前端包 `ui/unlock-data.js`（`window.EMOHEALTH_UNLOCK`）由前端层的
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
OUT_JSON = os.path.join(ROOT, "data/unlock-network.json")

# 相关清单的规模上限：跨面向信息弱，取多了只是噪声且拖慢运行时
TOPN = 24
MIN_ABS_R = 0.12


def main() -> int:
    from content.facet_definitions import FACETS  # noqa: E402
    canon = json.load(open(CANON, encoding="utf-8"))
    items = sorted(canon["items"], key=lambda x: x["order"])
    by_order = {it["order"]: it for it in items}

    fo: dict[str, list[int]] = defaultdict(list)
    for it in items:
        fo[it["facet"]].append(it["order"])
    for f in fo:
        fo[f].sort()
    DOM_KEY = ["neuroticism", "extraversion", "openness",
               "agreeableness", "conscientiousness"]
    facets = [f for dk in DOM_KEY for f in FACETS if FACETS[f]["domain"] == dk]

    dfr = pd.read_csv(DATA, sep="\t", dtype=str, keep_default_na=False)
    X = (dfr[[f"I{i}" for i in range(1, 301)]]
         .replace({"": np.nan, " ": np.nan, "0": np.nan})
         .apply(pd.to_numeric, errors="coerce").to_numpy(float))
    Xc = X[~np.isnan(X).any(axis=1)]
    R, coding = as_construct_direction(Xc, items, expect_recoded=True)
    n = R.shape[0]

    # 全库相关矩阵（只用来挑「相关清单」，不整体下发）
    C = np.corrcoef(R, rowvar=False)            # 300×300
    facet_full = {f: R[:, [o - 1 for o in fo[f]]].sum(axis=1) for f in facets}
    # 每题与每个面向完整分的相关
    IF = np.zeros((300, len(facets)))
    for j, f in enumerate(facets):
        y = facet_full[f]
        for i in range(300):
            IF[i, j] = float(np.corrcoef(R[:, i], y)[0, 1])

    rel: dict[str, dict] = {}
    for j, f in enumerate(facets):
        # 自己的题必进（它们是最强的预测变量）
        own = [o - 1 for o in fo[f]]
        others = sorted((i for i in range(300) if i not in own),
                        key=lambda i: -abs(IF[i, j]))
        pick = own + [i for i in others[:TOPN] if abs(IF[i, j]) >= MIN_ABS_R]
        pick = sorted(set(pick))
        rel[f] = {
            "items": [i + 1 for i in pick],                  # 1-based 题号
            "r": [round(float(IF[i, j]), 4) for i in pick],  # 与目标面向的相关
            "own": sorted(o for o in fo[f]),
            # 这些题两两之间的相关（下三角，按 pick 的顺序）
            "pair": [[round(float(C[pick[a], pick[b]]), 4) for b in range(a)]
                     for a in range(len(pick))],
        }
        n_cross = sum(1 for i in pick if by_order[i + 1]["facet"] != f)
        print(f"  {f:<34} 相关清单 {len(pick):>2} 题"
              f"（其中跨面向 {n_cross:>2}）")

    payload = {
        "source": f"Johnson (2005) N={n}；{coding['verdict']}",
        "rule": "细类解锁 = 以**目前已答的全部题目**为预测变量，对该面向完整分的"
                "回归 R² 达到门槛。不是「本面向的题答够了」。",
        "threshold_r": 0.85,
        "min_own": 2,
        "min_own_rationale": "M=1 时第 1 环（30 题）就能「解锁」8 个，但消融显示"
                              "8 个里 0 个能仅靠跨面向达标——是**一道题**撑起来的，"
                              "太薄。M=2 时第 1 环 0 个、第 2 环（60 题）26 个，"
                              "把等待从 90 题缩到 60 题。",
        "why_not_decision_tree": "树拆半稳定性差（深度 2 重叠 0.530 / 3 为 0.429 / "
                                 "4 为 0.286）；本规则取自全部样本，稳定可复现。",
        "topn": TOPN, "min_abs_r": MIN_ABS_R,
        "facets": facets,
        "rel": rel,
    }
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"\n数据包 → {os.path.relpath(OUT_JSON, ROOT)}  "
          f"({os.path.getsize(OUT_JSON)/1024:.0f} KB)"
          f"（前端包 ui/unlock-data.js 由 tools/ui/pack_ui_data.py 打包）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
