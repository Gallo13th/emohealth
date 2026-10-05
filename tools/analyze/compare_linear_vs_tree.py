#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""线性 vs 非线性：预测面向完整分时，树模型到底有没有用？

## 为什么要先问这个

用户提出「用决策树 + 博弈论的重要性/相关性来构建节点连接，并得到任意答题状态的结果」。
这条路线在文献里有先例——Gonzalez (2021, *Multivariate Behavioral Research*) 把
回归树列为与 CAT 并列的「定制化施测」方法之一，并指出：

> 树容易不稳定、难以泛化；通常用集成方法改善预测，**但集成不再提供确定施测顺序
> 所需的树状结构**。

同一篇还警告了一个退化陷阱：

> **和分是完全由题目作答决定的**——只最小化预测误差的算法会倾向于把所有题都纳进来。

所以在投入实现之前，必须先回答一个更基本的问题：

> **预测「面向的完整分」这件事，本身有多少非线性可挖？**

若非线性增益可忽略，那么：
  · 树的价值就只在**结构**（哪些题重要、谁连接谁），不在预测
  · 「任意答题状态的结果」用**已经验证过的线性回归**即可，不必换模型

## 做法

对每个面向，用前 R 环的题预测它的完整分，比较四种模型在**留出集**上的表现：

  · OLS          线性，当前引擎用的
  · Ridge        线性 + 正则
  · 梯度提升树    非线性
  · 随机森林      非线性

**全部用 5 折交叉验证**，绝不在训练集上比——那是自欺。

输出：`data/model-comparison.json`
"""
from __future__ import annotations

import json
import os
import sys
import time
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
OUT = os.path.join(ROOT, "data/model-comparison.json")


def main() -> int:
    from content.facet_definitions import FACETS  # noqa: E402
    from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
    from sklearn.linear_model import LinearRegression, Ridge
    from sklearn.model_selection import KFold
    from sklearn.metrics import r2_score

    canon = json.load(open(CANON, encoding="utf-8"))
    items = sorted(canon["items"], key=lambda x: x["order"])
    by_order = {it["order"]: it for it in items}
    ladder = json.load(open(os.path.join(ROOT, "data/tier-ladder.json"), encoding="utf-8"))
    order = ladder["order"]
    rings, prev = [], 0
    for t in ladder["tiers"]:
        rings.append(order[prev:t["items"]]); prev = t["items"]

    fo: dict[str, list[int]] = defaultdict(list)
    for it in items:
        fo[it["facet"]].append(it["order"])
    for f in fo:
        fo[f].sort()
    facets = [f for dk in ("neuroticism", "extraversion", "openness",
                           "agreeableness", "conscientiousness")
              for f in FACETS if FACETS[f]["domain"] == dk]

    dfr = pd.read_csv(DATA, sep="\t", dtype=str, keep_default_na=False)
    X = (dfr[[f"I{i}" for i in range(1, 301)]]
         .replace({"": np.nan, " ": np.nan, "0": np.nan})
         .apply(pd.to_numeric, errors="coerce").to_numpy(float))
    Xc = X[~np.isnan(X).any(axis=1)]
    R, coding = as_construct_direction(Xc, items, expect_recoded=True)
    facet_full = {f: R[:, [o - 1 for o in fo[f]]].sum(axis=1) for f in facets}

    kf = KFold(n_splits=5, shuffle=True, random_state=20260930)
    MODELS = {
        "ols": lambda: LinearRegression(),
        "ridge": lambda: Ridge(alpha=1.0),
        "gbt": lambda: GradientBoostingRegressor(
            n_estimators=200, max_depth=3, learning_rate=0.05, random_state=0),
        "rf": lambda: RandomForestRegressor(
            n_estimators=100, min_samples_leaf=10, n_jobs=-1, random_state=0),
    }

    rows = []
    for Rt in (1, 2, 3):
        feats = [o for t in range(Rt) for o in rings[t]]
        F = R[:, [o - 1 for o in feats]]
        print(f"\n=== 第 {Rt} 环（{len(feats)} 题）→ 预测 30 个面向的完整分 ===",
              flush=True)
        print(f"  {'模型':<8}{'平均 R²':>10}{'最差 R²':>10}{'耗时':>8}")
        for name, mk in MODELS.items():
            t0 = time.time()
            scores = []
            for f in facets:
                y = facet_full[f]
                pred = np.zeros_like(y)
                for tr, te in kf.split(F):
                    m = mk(); m.fit(F[tr], y[tr])
                    pred[te] = m.predict(F[te])
                scores.append(r2_score(y, pred))
            dt = time.time() - t0
            rows.append({"ring": Rt, "items": len(feats), "model": name,
                         "r2_mean": round(float(np.mean(scores)), 4),
                         "r2_min": round(float(np.min(scores)), 4),
                         "seconds": round(dt, 1)})
            print(f"  {name:<8}{np.mean(scores):>10.4f}{np.min(scores):>10.4f}{dt:>7.1f}s",
                  flush=True)

    # ── 非线性增益
    gains = []
    for Rt in (1, 2, 3):
        sub = {r["model"]: r for r in rows if r["ring"] == Rt}
        gains.append({
            "ring": Rt, "items": sub["ols"]["items"],
            "ols": sub["ols"]["r2_mean"],
            "best_nonlinear": max(sub["gbt"]["r2_mean"], sub["rf"]["r2_mean"]),
            "gain": round(max(sub["gbt"]["r2_mean"], sub["rf"]["r2_mean"])
                          - sub["ols"]["r2_mean"], 4),
        })

    payload = {
        "source": f"Johnson (2005) N={len(R)}；{coding['verdict']}",
        "question": "预测面向完整分时，非线性（树模型）比线性好多少？",
        "method": "5 折交叉验证；全部指标取自留出折，不用训练集",
        "citation": "Gonzalez, O. (2021). Psychometric and Machine Learning "
                    "Approaches to Reduce the Length of Scales. "
                    "Multivariate Behavioral Research, 56(6), 903-919.",
        "caveat_from_literature": "和分完全由题目作答决定，"
                                  "只最小化预测误差的算法会把所有题都纳进来",
        "results": rows,
        "nonlinear_gain": gains,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)

    print("\n=== 非线性增益（树 − 线性）===")
    print(f"  {'环':>3}{'题数':>6}{'OLS R²':>10}{'最佳非线性':>12}{'增益':>10}")
    for g in gains:
        print(f"  {g['ring']:>3}{g['items']:>6}{g['ols']:>10.4f}"
              f"{g['best_nonlinear']:>12.4f}{g['gain']:>+10.4f}")
    print(f"\nwrote {os.path.relpath(OUT, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
