#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""计分方向的回归测试。

## 为什么需要它

IPIP-NEO-300 有 148 道反向题。「分析时要不要翻转反向题」取决于**数据源
已经处于哪种编码状态**——这不是可以想当然的事。

**我在这上面栽过一次**：在没有验证数据源状态的情况下，给三个分析脚本
统一加了「还原反向题」，理由是「必须先还原」。但 Johnson 的 `ipip20993.dat`
**本来就是反向重编码的**，于是双重翻转：

    第 1 层的维度相关：正确的 0.888 → 错误的 0.560

我一度把 0.560 当成了「修正后的诚实数字」，还准备据此推翻结论。
判据其实只有一行：**看反向题与面向总分的相关符号**。

本测试把这条判据固化，防止再犯。
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
sys.path.insert(0, ROOT)

from tools.item_coding import as_construct_direction, detect_coding  # noqa: E402

FAIL = []


def ck(name, cond, detail=""):
    print(f"  {'✅' if cond else '❌'} {name}" + (f"  —— {detail}" if detail else ""))
    if not cond:
        FAIL.append(name)


def load():
    canon = json.load(open(os.path.join(ROOT, "data/ipip-neo-300.json"), encoding="utf-8"))
    items = sorted(canon["items"], key=lambda x: x["order"])
    dfr = pd.read_csv(os.path.join(ROOT, "archive/datasets/osf-johnson/validity/ipip20993.dat"),
                      sep="\t", dtype=str, keep_default_na=False)
    X = (dfr[[f"I{i}" for i in range(1, 301)]]
         .replace({"": np.nan, " ": np.nan, "0": np.nan})
         .apply(pd.to_numeric, errors="coerce").to_numpy(float))
    return items, X[~np.isnan(X).any(axis=1)]


def main() -> int:
    items, X = load()

    print("=== B1 数据源已被反向重编码 ===")
    info = detect_coding(X, items)
    ck("判定为「已重编码」", info["recoded"], info["verdict"])
    ck("30/30 个面向的反向题都正相关",
       info["facets_where_reverse_items_corr_positively"] == info["facets_total"],
       f"{info['facets_where_reverse_items_corr_positively']}/{info['facets_total']}")
    ck("正反向题的题总相关同号且都为正",
       info["forward_item_r_mean"] > 0 and info["reverse_item_r_mean"] > 0,
       f"正向 {info['forward_item_r_mean']}，反向 {info['reverse_item_r_mean']}")

    print("\n=== B2 expect_recoded 不符时必须报错，不得静默照做 ===")
    try:
        as_construct_direction(X, items, expect_recoded=False)
        ck("声明 expect_recoded=False 时报错", False, "没有报错——静默照做正是上次出错的原因")
    except RuntimeError as e:
        ck("声明 expect_recoded=False 时报错", True, str(e)[:60] + "…")

    print("\n=== B3 正确调用下不改变矩阵 ===")
    Y, info2 = as_construct_direction(X, items, expect_recoded=True)
    ck("已重编码的数据不应被改动", np.array_equal(Y, X))

    print("\n=== B4 若数据是原始作答，则应翻转 ===")
    key = np.array([it["key"] for it in items], float)
    Z = X.copy()
    Z[:, key < 0] = 6 - Z[:, key < 0]          # 人为造一份「原始作答」
    info3 = detect_coding(Z, items)
    ck("人造的原始作答被判为未重编码", not info3["recoded"], info3["verdict"])
    W, _ = as_construct_direction(Z, items, expect_recoded=False)
    ck("未重编码的数据会被翻回同向", np.array_equal(W, X))

    print("\n=== B5 与已知结论对齐 ===")
    # 未翻转时（正确口径），第 1 层自然序的维度相关应为 0.815 量级
    from collections import defaultdict
    from content.facet_definitions import FACETS  # noqa: E402
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
    rs = []
    for d in sorted(df):
        fs = sorted(df[d])
        sel = [fo[f][0] for f in fs]
        fullc = [o - 1 for f in fs for o in fo[f]]
        part = X[:, [o - 1 for o in sel]].sum(axis=1)
        full = X[:, fullc].sum(axis=1)
        rs.append(float(np.corrcoef(part, full)[0, 1]))
    m = float(np.mean(rs))
    ck("第 1 层自然序的维度相关在 0.80–0.83 之间", 0.80 <= m <= 0.83, f"{m:.3f}")

    print("\n" + "=" * 60)
    if FAIL:
        print(f"❌ {len(FAIL)} 项未通过：{FAIL}")
        return 1
    print("✅ 全部 5 组计分方向回归测试通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
