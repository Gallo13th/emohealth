#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""决策树能不能用来定义「解锁路径」？

## 用户的设想

> 细的节点可以早解锁，解锁的连接关系应该是**问题节点级**的。
> 不需要实时预测，而是依靠**可靠的决策树**在某些特定问题都回答完之后更新一次——
> **不同的已回答组合会解锁不同的拟实时反馈**。

这正是 Gonzalez (2021) 描述的回归树用法：*future respondents would receive items
depending on the hierarchy of splits in the decision tree, similar to a CAT.*

## 与「用树做预测」的区别

我先前测过：用树**预测**面向分不优于线性（目标本身就是题目的和，没有非线性可挖）。
但这里要的是**结构**——树的分裂定义「下一步问哪题」「答成什么样走哪条路」。
预测用线性，结构用树，两者各司其职。

## 但树有个致命弱点，必须先验

Gonzalez 的警告：**树容易不稳定、难以泛化**。若换个样本树形就变，
那「解锁路径」就是随机的，不能给用户看。

本脚本回答三件事：

  1. **稳定性**：拆半训练，两半的根分裂/前两层分裂一致吗？
  2. **区分度**：不同的作答组合，真的会走到不同的后续题目吗？
     （若所有路径的第一个分裂项都一样，就没有「自适应」可言）
  3. **覆盖面**：一棵浅树只用几个分裂项？剩下的题怎么安排？

输出：`data/decision-paths.json`
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
sys.path.insert(0, ROOT)
from tools.item_coding import as_construct_direction  # noqa: E402

DATA = os.path.join(ROOT, "archive/datasets/osf-johnson/validity/ipip20993.dat")
CANON = os.path.join(ROOT, "data/ipip-neo-300.json")
OUT = os.path.join(ROOT, "data/decision-paths.json")


def main() -> int:
    from content.facet_definitions import FACETS  # noqa: E402
    from sklearn.tree import DecisionTreeRegressor, _tree

    canon = json.load(open(CANON, encoding="utf-8"))
    items = sorted(canon["items"], key=lambda x: x["order"])
    by_order = {it["order"]: it for it in items}

    df_f: dict[str, list[str]] = defaultdict(list)
    for f in FACETS:
        df_f[FACETS[f]["domain"]].append(f)
    for d in df_f:
        df_f[d].sort()

    dfr = pd.read_csv(DATA, sep="\t", dtype=str, keep_default_na=False)
    X = (dfr[[f"I{i}" for i in range(1, 301)]]
         .replace({"": np.nan, " ": np.nan, "0": np.nan})
         .apply(pd.to_numeric, errors="coerce").to_numpy(float))
    Xc = X[~np.isnan(X).any(axis=1)]
    R, coding = as_construct_direction(Xc, items, expect_recoded=True)
    n = R.shape[0]

    dom_full = {d: R[:, [o - 1 for f in df_f[d]
                         for o in sorted(o2["order"] for o2 in items
                                         if o2["facet"] == f)]].sum(axis=1)
                for d in df_f}

    def fit_tree(XX, y, depth):
        t = DecisionTreeRegressor(max_depth=depth, min_samples_leaf=200,
                                  random_state=0)
        t.fit(XX, y)
        return t

    def top_splits(t, k=8):
        """返回树里用到的分裂变量（按出现顺序，去重）。"""
        feat = t.tree_.feature
        out, seen = [], set()
        for v in feat:
            if v >= 0 and v not in seen:
                seen.add(v); out.append(int(v))
            if len(out) >= k:
                break
        return out

    rng = np.random.default_rng(20260930)
    idx = rng.permutation(n)
    A, B = R[idx[:n // 2]], R[idx[n // 2:]]

    results = {}
    print(f"参照样本 {n} 条；{coding['verdict']}\n")
    print("=== 一、稳定性：拆半训练，分裂变量一致吗 ===")
    print(f"{'维度':<18}{'深度':>4}{'A 半前 5 个分裂项':<34}{'B 半前 5 个分裂项':<34}{'重合':>6}")
    print("-" * 100)
    for depth in (2, 3, 4):
        agree = []
        for d in sorted(df_f):
            yA = dom_full[d][idx[:n // 2]]
            yB = dom_full[d][idx[n // 2:]]
            tA = fit_tree(A, yA, depth)
            tB = fit_tree(B, yB, depth)
            sA, sB = top_splits(tA, 5), top_splits(tB, 5)
            ov = len(set(sA) & set(sB)) / max(1, len(set(sA) | set(sB)))
            agree.append(ov)
            if d in ("neuroticism", "openness"):
                fA = " ".join(by_order[s + 1]["facet"][:12] for s in sA)
                fB = " ".join(by_order[s + 1]["facet"][:12] for s in sB)
                print(f"{d:<18}{depth:>4}  {fA:<32}  {fB:<32}{ov:>6.2f}")
        print(f"{'  → 平均重合度':<18}{depth:>4}  {np.mean(agree):.3f}")
        results[f"stability_depth{depth}"] = round(float(np.mean(agree)), 4)

    # ── 二、区分度：不同作答组合走到不同题吗
    print("\n=== 二、区分度：不同作答组合会解锁不同题目吗 ===")
    depth = 3
    paths = {}
    for d in sorted(df_f):
        t = fit_tree(A, dom_full[d][idx[:n // 2]], depth)
        tree = t.tree_
        nodes = []
        def walk(i, cond):
            if tree.feature[i] >= 0:
                f = int(tree.feature[i]); th = float(tree.threshold[i])
                walk(tree.children_left[i], cond + [(f, th, "<=")])
                walk(tree.children_right[i], cond + [(f, th, ">")])
            else:
                nodes.append(cond)
        walk(0, [])
        first_items = {c[0][0] for c in nodes if c}
        paths[d] = {"n_leaves": len(nodes),
                    "first_split_items": sorted(first_items),
                    "n_distinct_first_items": len(first_items)}
    for d in sorted(dfs := sorted(df_f)):
        p = paths[d]
        print(f"  {d:<18} 叶节点 {p['n_leaves']:>2} 个"
              f"  根分裂项 {len(p['first_split_items'])} 个"
              + (f"（{p['first_split_items'][:3]}…）" if p['first_split_items'] else ""))

    # 同一维度内，不同叶节点的路径是否用不同题
    distinct_ok = sum(1 for d in paths if paths[d]["n_leaves"] > 1)
    print(f"\n  {distinct_ok}/5 个维度有多个叶节点（即作答会分流）")

    # ── 三、覆盖面
    print("\n=== 三、覆盖面：一棵浅树用到几道题 ===")
    t = fit_tree(A, dom_full["neuroticism"][idx[:n // 2]], 4)
    used = top_splits(t, 99)
    print(f"  深度 4 的神经质树用到 {len(used)} 道题；"
          f"叶节点 {(t.tree_.n_leaves)} 个")
    print(f"  → 树只能覆盖少数题；剩下的仍需按分层阶梯补齐")

    payload = {
        "source": f"Johnson (2005) N={n}",
        "citations": [
            "Gonzalez, O. (2021). Psychometric and Machine Learning Approaches to "
            "Reduce the Length of Scales. Multivariate Behavioral Research, 56(6), 903-919.",
        ],
        "question": "决策树能否用来定义「解锁路径」？",
        "role_split": "预测用线性（已验证最优）；**结构**用树（本脚本验证对象）",
        "stability": {k: v for k, v in results.items()},
        "paths": paths,
        "coverage": {"depth": 4, "facet": "neuroticism",
                     "items_used": len(used), "leaves": int(t.tree_.n_leaves)},
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
    print(f"\nwrote {os.path.relpath(OUT, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
