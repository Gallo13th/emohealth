#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""作答数据的**计分方向自动判定**。

## 为什么需要它

IPIP-NEO-300 有 148 道反向题。分析时到底要不要把反向题翻转成同向，
取决于**数据源已经处于哪种编码状态**：

  · 若数据是**原始作答**（1=很不符合，5=很符合，按题面字面）
    → 必须翻转反向题，否则「面向分」不是面向分
  · 若数据**已经被反向重编码**（反向题的高分已代表该面向的高端）
    → **不能翻转**，翻了就是双重翻转

**Johnson (2005) 的 `ipip20993.dat` 属于后者：已经重编码。**

## 一个我犯过的错

我在三个分析脚本里统一加了「翻转反向题」，理由是「必须先还原」——
但没先验证数据源的实际状态。结果是双重翻转，第 1 层的维度相关
从正确的 **0.888** 掉到错误的 **0.560**，我一度把错的那个当成了修正。

判据其实很简单：**看反向题与面向总分的相关符号**。

  · 正的 → 数据已重编码 → 不要翻
  · 负的 → 数据是原始作答 → 要翻

本模块把这条判据自动化，并在判定与调用方预期不符时报错，
而不是静默照做。
"""
from __future__ import annotations

import numpy as np


def detect_coding(X: np.ndarray, items: list[dict],
                  min_facets: int = 5) -> dict:
    """判定数据源的计分方向。

    参数
      X      形状 (n, 300) 的作答矩阵，列顺序与 items 一致
      items  长度为 300 的题目列表，需含 "key" 与 "facet"

    返回
      {"recoded": bool, "evidence": {...}}
      recoded=True 表示反向题**已经**重编码，**不要**再翻转。
    """
    from collections import defaultdict
    key = np.array([it["key"] for it in items], float)
    fo: dict[str, list[int]] = defaultdict(list)
    for i, it in enumerate(items):
        fo[it["facet"]].append(i)

    # ⚠️ 锚点必须**只用正向题**。
    # 初版用「该面向全部题的加总」做锚——但那个加总本身就依赖编码方向，
    # 于是判据变成循环的：把数据翻错之后，判据仍会说「已重编码」。
    # 用正向题的加总做锚则没有这个问题：正向题的方向是确定的。
    pos_r, neg_r, per_facet = [], [], {}
    for f, cols in fo.items():
        fwd = [c for c in cols if key[c] > 0]
        rev = [c for c in cols if key[c] < 0]
        if not fwd or not rev:
            continue
        anchor = X[:, fwd].sum(axis=1)
        p = [float(np.corrcoef(X[:, c], anchor)[0, 1]) for c in fwd]
        n = [float(np.corrcoef(X[:, c], anchor)[0, 1]) for c in rev]
        pos_r.append(float(np.mean(p)))
        neg_r.append(float(np.mean(n)))
        per_facet[f] = round(float(np.mean(n)), 3)

    m_pos = float(np.mean(pos_r)) if pos_r else float("nan")
    m_neg = float(np.mean(neg_r)) if neg_r else float("nan")
    n_facets_neg_positive = sum(1 for v in per_facet.values() if v > 0)
    recoded = (m_neg > 0) and (n_facets_neg_positive >= min_facets)
    return {
        "recoded": bool(recoded),
        "forward_item_r_mean": round(m_pos, 4),
        "reverse_item_r_mean": round(m_neg, 4),
        "facets_where_reverse_items_corr_positively": n_facets_neg_positive,
        "facets_total": len(fo),
        "verdict": ("数据**已**反向重编码 —— 不要再翻转"
                    if recoded else
                    "数据是原始作答 —— 需要翻转反向题"),
    }


def as_construct_direction(X: np.ndarray, items: list[dict],
                           expect_recoded: bool | None = None) -> tuple[np.ndarray, dict]:
    """返回「已对齐到构念方向」的矩阵（高分 = 该面向的高端）。

    expect_recoded 用于显式声明调用方的预期；若与实际不符则**报错**，
    而不是静默照做——静默照做正是上次出错的原因。
    """
    info = detect_coding(X, items)
    if expect_recoded is not None and info["recoded"] != expect_recoded:
        raise RuntimeError(
            f"计分方向与预期不符：{info['verdict']}；"
            f"证据 正向题 r 均={info['forward_item_r_mean']}，"
            f"反向题 r 均={info['reverse_item_r_mean']}，"
            f"反向题相关为正的面向 {info['facets_where_reverse_items_corr_positively']}"
            f"/{info['facets_total']}")
    if info["recoded"]:
        return X, info
    key = np.array([it["key"] for it in items], float)
    Y = X.copy()
    Y[:, key < 0] = 6 - Y[:, key < 0]
    return Y, info


if __name__ == "__main__":
    import json
    import os
    import pandas as pd

    ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    canon = json.load(open(os.path.join(ROOT, "data/ipip-neo-300.json"), encoding="utf-8"))
    items = sorted(canon["items"], key=lambda x: x["order"])
    dfr = pd.read_csv(os.path.join(ROOT, "archive/datasets/osf-johnson/validity/ipip20993.dat"),
                      sep="\t", dtype=str, keep_default_na=False)
    X = (dfr[[f"I{i}" for i in range(1, 301)]]
         .replace({"": np.nan, " ": np.nan, "0": np.nan})
         .apply(pd.to_numeric, errors="coerce").to_numpy(float))
    Xc = X[~np.isnan(X).any(axis=1)]
    info = detect_coding(Xc, items)
    print(f"参照样本 {Xc.shape[0]} 条")
    for k, v in info.items():
        print(f"  {k}: {v}")
