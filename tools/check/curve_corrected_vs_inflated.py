#!/usr/bin/env python3
"""算「用 corrected 相关」后的部分施测置信度曲线，评估改动影响。

要回答的问题
============
把题↔面向相关从 **inflated（含本题）** 换成 **corrected（去本题）** 后：
  · 答 k 题时的置信度 R² = bᵀ A⁻¹ b 会降多少？
  · 达到门槛 0.85 需要几题？（会不会难到不可用）
  · 与现在的口径相比，解锁会推迟多少？

这才是「实时动态算置信度」的正确算式：
  · A = 已答题之间的**题间相关**（实测）
  · b = 已答题与**完整面向分**的相关 → 必须用 **corrected**，否则「自己那道题」
    自解释、置信度虚高（现有实现即如此，再用 MIN_OWN 去堵，属治标）
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
THR = 0.85

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
C = np.corrcoef(Xc, rowvar=False)          # 300×300 题间相关


def curve(facet: str, corrected: bool):
    """返回 {k: (r_mean, r_min, r_max)}——答 k 题时预测完整面向分的置信度。"""
    orders = fo[facet]
    total = Xc[:, [o - 1 for o in orders]].sum(axis=1)
    out = {}
    for k in range(1, min(len(orders), 8) + 1):
        rs = []
        for sub in combinations(orders, k):
            idx = [o - 1 for o in sub]
            A = C[np.ix_(idx, idx)]
            b = np.array([
                np.corrcoef(Xc[:, i],
                            total - (Xc[:, i] if corrected else 0))[0, 1]
                for i in idx])
            try:
                x = np.linalg.solve(A, b)
            except np.linalg.LinAlgError:
                continue
            r2 = float(b @ x)
            rs.append(max(0.0, min(1.0, r2)) ** 0.5)
        if rs:
            out[k] = (float(np.mean(rs)), float(np.min(rs)), float(np.max(rs)))
    return out


print(f"门槛 r ≥ {THR}\n")
print(f"{'面向':>20}{'口径':>10}" + "".join(f"{'k=' + str(k):>9}" for k in range(1, 7)))
for facet in ("anxiety", "depression", "activitylevel"):
    for corrected in (False, True):
        cv = curve(facet, corrected)
        label = "corrected" if corrected else "inflated"
        row = "".join(f"{cv[k][0]:>9.3f}" if k in cv else f"{'-':>9}"
                      for k in range(1, 7))
        print(f"{facet:>20}{label:>10}{row}")
    print()

print("=== 「达到门槛所需的最小 k」（按平均置信度）===")
print(f"{'面向':>20}{'inflated':>10}{'corrected':>11}{'推迟':>7}")
delay = []
for facet in sorted(fo):
    row = []
    for corrected in (False, True):
        cv = curve(facet, corrected)
        need = next((k for k in sorted(cv) if cv[k][0] >= THR), None)
        row.append(need)
    if row[0] and row[1]:
        delay.append(row[1] - row[0])
    print(f"{facet:>20}{str(row[0]):>10}{str(row[1]):>11}"
          f"{('+' + str(row[1] - row[0])) if row[0] and row[1] else '':>7}")
print(f"\n平均推迟 {np.mean(delay):.2f} 题（{len(delay)} 个面向可比）"
      if delay else "\n（无可比项）")
