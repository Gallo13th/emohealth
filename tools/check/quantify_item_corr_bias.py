#!/usr/bin/env python3
"""算「含本题」与「去本题」两种题↔面向相关的差距——决定置信度该怎么算。

背景（用户的纠正）
==================
用户指出：**不存在「可靠题量」，应该是实时动态计算当前答题结果的置信度。**

追根因发现：现有推断用的题↔面向相关是 **含本题** 的部分-整体相关
（`ui/index.html` 里 `dimRNote` 自己写着「题↔面向总分（**含本题**）相关」）。
含本题会让「自己那一道题」对面向估计的贡献被高估 → 第 1 环（每面向 1 题）就可能
算出很高的 r。现有实现用一个**静态补丁** `MIN_OWN=2` 去堵它
（`unlock-network.json` 的 rationale：「M=1 时…是一道题撑起来的，太薄」）。

而正确的做法是**把这个虚高修掉**——置信度算准了，补丁就不需要了。

本脚本量化差距
==============
对每道题算两个相关：
  · inflated  = corr(题, 面向总分**含**本题)     ← 现有实现用的
  · corrected = corr(题, 面向总分**去**本题)     ← 应该用的
并看：**只答 1 题时**，用两种口径算出的面向估计置信度各是多少。
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = r"C:\Codes\emohealth-20260930-full\emohealth"
DATA = os.path.join(ROOT, "archive/datasets/osf-johnson/validity/ipip20993.dat")
CANON = os.path.join(ROOT, "data", "ipip-neo-300.json")

canon = json.load(open(CANON, encoding="utf-8"))
items = sorted(canon["items"], key=lambda x: x["order"])
fo: dict[str, list[int]] = {}
for it in items:
    fo.setdefault(it["facet"], []).append(it["order"])

dfr = pd.read_csv(DATA, sep="\t", dtype=str, keep_default_na=False)
X = (dfr[[f"I{i}" for i in range(1, 301)]]
     .replace({"": np.nan, " ": np.nan, "0": np.nan})
     .apply(pd.to_numeric, errors="coerce").to_numpy(float))
Xc = X[~np.isnan(X).any(axis=1)]
n = Xc.shape[0]
print(f"完整作答 {n} 行；148 道反向题已预编码（见 diagnose_ipip_recoding.py）\n")


def corr(a, b):
    return float(np.corrcoef(a, b)[0, 1])


print(f"{'面向':>22}{'题数':>5}{'inflated 中位':>14}{'corrected 中位':>15}{'差':>8}")
rows = []
for f, orders in sorted(fo.items()):
    inf_l, cor_l = [], []
    for o in orders:
        others = [x for x in orders if x != o]
        total_all = Xc[:, [x - 1 for x in orders]].sum(axis=1)
        total_wo = Xc[:, [x - 1 for x in others]].sum(axis=1)
        inf_l.append(corr(Xc[:, o - 1], total_all))
        cor_l.append(corr(Xc[:, o - 1], total_wo))
    rows.append((f, len(orders), float(np.median(inf_l)), float(np.median(cor_l))))
rows.sort(key=lambda r: r[3] - r[2])          # 差最大的排前
for f, k, a, b in rows[:10]:
    print(f"{f:>22}{k:>5}{a:>14.3f}{b:>15.3f}{b - a:>8.3f}")
print("  …")
ia = float(np.mean([r[2] for r in rows]))
ca = float(np.mean([r[3] for r in rows]))
print(f"\n30 个面向平均：inflated {ia:.3f} → corrected {ca:.3f}（降 {ia - ca:.3f}）")

# 只答 1 题时，面向估计的置信度（单题预测 → 与完整分相关）
print("\n=== 只答 1 题时的置信度 r（该题预测完整面向分的相关）===")
print("  即 partial-administration 的 k=1；两种口径分别算：")
for f in ("anxiety", "friendliness", "activitylevel"):
    orders = fo[f]
    inf_l, cor_l = [], []
    for o in orders:
        others = [x for x in orders if x != o]
        total_all = Xc[:, [x - 1 for x in orders]].sum(axis=1)
        total_wo = Xc[:, [x - 1 for x in others]].sum(axis=1)
        inf_l.append(corr(Xc[:, o - 1], total_all))
        cor_l.append(corr(Xc[:, o - 1], total_wo))
    print(f"  {f:>18}: inflated 平均 {np.mean(inf_l):.3f}（最低 {min(inf_l):.3f}）"
          f" | corrected 平均 {np.mean(cor_l):.3f}（最低 {min(cor_l):.3f}）")

print("\n结论提示：若 corrected 明显低于 0.85 门槛，则**用修正后的相关算置信度**")
print("          自然就不会在「只答 1 题」时达标 —— MIN_OWN=2 这个静态补丁就不必要了。")
