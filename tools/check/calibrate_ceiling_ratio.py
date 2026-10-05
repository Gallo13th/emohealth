#!/usr/bin/env python3
"""标定「相对该面向上限的比例」门槛：算每个面向的置信度上限，及达各比例所需题量。

方案 (b) 的定义
===============
  · **置信度上限** `ceiling_f` = 答满该面向全部题时的 corrected 置信度
    （这是**面向自身的属性**，衡量「这个面向用这套题最好能测多准」）
  · **可以给结果** = 当前置信度 ≥ `ceiling_f × ratio`
    —— 完全由当前答题组合决定，**没有题量门槛**

本脚本给出标定依据：
  ① 每个面向的 ceiling（corrected / inflated 两种口径）
  ② ratio ∈ {0.80, 0.85, 0.90, 0.95} 时，各面向「达门槛所需的最小 k」
  ③ 选一个在「解锁时机」与「诚实」之间平衡的 ratio

⚠️ 置信度算式（与前端一致）：R² = bᵀ A⁻¹ b
     A = 已答题的题间相关；b = 已答题与**完整面向分**的相关
     corrected 口径下 b 用「题与其余题之和」的相关（去本题，避免自解释虚高）
"""

from __future__ import annotations

import json
import os
import sys
from itertools import combinations

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
C = np.corrcoef(Xc, rowvar=False)


def conf(orders, sub, corrected=True):
    """答 sub（题号元组）时，对该面向完整分的置信度 r。"""
    idx = [o - 1 for o in sub]
    A = C[np.ix_(idx, idx)]
    total = Xc[:, [o - 1 for o in orders]].sum(axis=1)
    b = np.array([np.corrcoef(Xc[:, i],
                              total - (Xc[:, i] if corrected else 0))[0, 1]
                  for i in idx])
    try:
        x = np.linalg.solve(A, b)
    except np.linalg.LinAlgError:
        return 0.0
    return max(0.0, min(1.0, float(b @ x))) ** 0.5


CURVE = {}
for f, orders in fo.items():
    cv = {}
    for k in range(1, len(orders) + 1):
        rs = [conf(orders, sub) for sub in combinations(orders, k)]
        cv[k] = float(np.mean(rs))
    CURVE[f] = cv

ceil = {f: CURVE[f][len(fo[f])] for f in fo}
print("=== ① 各面向的置信度上限（答满 10 题，corrected 口径）===")
print(f"{'面向':>20}{'ceiling':>10}{'k=1':>8}{'k=2':>8}{'k=3':>8}{'k=4':>8}{'k=6':>8}")
for f in sorted(fo, key=lambda x: ceil[x]):
    cv = CURVE[f]
    print(f"{f:>20}{ceil[f]:>10.3f}" + "".join(f"{cv[k]:>8.3f}" for k in (1, 2, 3, 4, 6)))
cs = sorted(ceil.values())
print(f"\nceilings：最低 {cs[0]:.3f}｜中位 {cs[len(cs)//2]:.3f}｜最高 {cs[-1]:.3f}")

print("\n=== ② 各 ratio 下「达门槛所需的最小 k」 ===")
print(f"{'ratio':>7}{'中位 k':>8}{'最大 k':>8}{'永不达标面向数':>16}  分布")
for ratio in (0.80, 0.85, 0.90, 0.95):
    ks = []
    never = 0
    for f, cv in CURVE.items():
        thr = ceil[f] * ratio
        need = next((k for k in sorted(cv) if cv[k] >= thr), None)
        if need is None:
            never += 1
        else:
            ks.append(need)
    dist = {k: ks.count(k) for k in sorted(set(ks))}
    print(f"{ratio:>7}{sorted(ks)[len(ks)//2]:>8}{max(ks):>8}{never:>16}  {dist}")
