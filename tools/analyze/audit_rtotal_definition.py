#!/usr/bin/env python3
"""审计 `r_total` 的定义缺陷：给出「预测能力」的正确度量。

用户的质疑（原话）
==================
> 不同的回答题量带来的预测值和最终分的相关性是不一样的，**如果只答一题就有 0.99 的
> 相关性，反而回答更多题容易偏离的话，这最多只能说明你的统计样本相对稀缺**。

要审的点
========
现有 `r_total` 把「已答本维度题」当作**已知量**混进预测里：
    预测 = 已答部分的真实值（已知） + 未答部分的条件期望（预测）
    r_total = corr(预测, 完整真实分)

于是 **k 越大 → 已知真实值占比越高 → 与完整分的相关反而下降**。
「答 1 题 0.99、答 6 题 0.90」在这种定义下是**必然**，不代表预测能力变差。

三个口径一起算（经验 OLS，无理论推导歧义）
==========================================
  A. r_total     = corr(已知部分 + 预测的未知部分, 完整真实分)   ← 现状（混入已知量）
  B. r_unknown   = corr(预测的未知部分, 未知部分真实值)          ← **纯预测能力**
  C. r_single    = corr(用其余题预测某一道题, 该题真实值)        ← 单题留一

判据：若 A 随 k **下降**、而 B 随 k **上升** → 用户质疑成立，
      A 不能当「预测准确度」用，应改用 B（必要时辅以 C）。
"""

from __future__ import annotations

import io
import json
import os
import sys
from itertools import combinations

import numpy as np
import pandas as pd

ROOT = r"C:\Codes\emohealth-20260930-full\emohealth"
sys.path.insert(0, os.path.join(ROOT, "tools"))
from _root import find_root  # noqa: E402
ROOT = str(find_root())

inst = json.load(io.open(os.path.join(ROOT, "data", "instruments", "ipip-neo.json"),
                         encoding="utf-8"))
canon = json.load(io.open(os.path.join(ROOT, "data", "ipip-neo-300.json"),
                          encoding="utf-8"))
dfr = pd.read_csv(os.path.join(ROOT, "archive", "datasets", "osf-johnson",
                               "validity", "ipip20993.dat"),
                  sep="\t", dtype=str, keep_default_na=False)
X = (dfr[[f"I{i}" for i in range(1, 301)]]
     .replace({"": np.nan, " ": np.nan, "0": np.nan})
     .apply(pd.to_numeric, errors="coerce").to_numpy(float))
X = X[~np.isnan(X).any(axis=1)]
N = X.shape[0]
print(f"完整作答 {N} 份；每题按 canon 序取列\n")


def norm(s):
    return "".join(c for c in (s or "").lower() if c.isalnum())


by_text = {norm(it["text"]): it["order"] for it in canon["items"]}
order_of = {it["id"]: it["order"] for it in inst["items"]}
pkg2canon = {}
for iid, o in order_of.items():
    it = next(it for it in inst["items"] if it["id"] == iid)
    co = by_text.get(norm(it["text"]))
    if co:
        pkg2canon[o] = co
by_dim = {}
for d in inst["dimensions"]:
    if d.get("items"):
        by_dim[d["id"]] = sorted(order_of[i] for i in d["items"])


def std(v):
    s = v.std()
    return (v - v.mean()) / (s if s > 1e-12 else 1.0)


print("=" * 84)
print(f"{'维度':>26}{'k':>3}{'A. r_total':>12}{'B. r_unknown':>14}"
      f"{'C. r_single':>13}{'A−B':>9}")
print("=" * 84)

rows = []
for f in ["anxiety", "depression", "activitylevel", "openness",
          "friendliness", "selfdiscipline"]:
    orders = by_dim.get(f) or []
    if len(orders) != 10:
        continue
    cols = [pkg2canon[o] - 1 for o in orders]
    Z = X[:, cols]
    Zs = np.column_stack([std(Z[:, j]) for j in range(10)])
    y_total = std(Z.sum(1))
    for k in (1, 2, 3, 5, 8):
        A_l, B_l, C_l = [], [], []
        for sub in combinations(range(10), k):
            rest = [j for j in range(10) if j not in sub]
            if len(rest) < 2:
                continue
            Xa = Zs[:, list(sub)]
            y_un = std(Z[:, rest].sum(1))
            # 经验 OLS：用已答题预测「未答部分之和」
            beta, *_ = np.linalg.lstsq(Xa, y_un, rcond=None)
            pred_un = Xa @ beta
            # A：已知真实值 + 预测的未知部分 → 对完整分
            known = std(Z[:, list(sub)].sum(1))
            # 把两部分按各自与完整分的尺度简单相加（same units: 标准化）
            A_l.append(abs(np.corrcoef(known + pred_un, y_total)[0, 1]))
            # B：纯预测 → 对未答部分真实值
            B_l.append(abs(np.corrcoef(pred_un, y_un)[0, 1]))
            # C：留一 —— 用其余 9 题预测被留出的那一题
            j0 = sub[0]
            others = [j for j in range(10) if j != j0]
            bo, *_ = np.linalg.lstsq(Zs[:, others], Zs[:, j0], rcond=None)
            C_l.append(abs(np.corrcoef(Zs[:, others] @ bo, Zs[:, j0])[0, 1]))
        if A_l:
            r = (f, k, float(np.mean(A_l)), float(np.mean(B_l)), float(np.mean(C_l)))
            rows.append(r)
            print(f"{f:>26}{k:>3}{r[2]:>12.4f}{r[3]:>14.4f}{r[4]:>13.4f}"
                  f"{r[2] - r[3]:>9.4f}")

print()
tr = [r for r in rows if r[1] == 1]
hi = [r for r in rows if r[1] == 8]
print("=== 结论 ===")
if tr and hi:
    print(f"  A. r_total   ：k=1 均值 {np.mean([r[2] for r in tr]):.4f}"
          f" → k=8 均值 {np.mean([r[2] for r in hi]):.4f}"
          f"（{'下降 ✅ 与用户质疑一致' if np.mean([r[2] for r in hi]) < np.mean([r[2] for r in tr]) else '上升'}）")
    print(f"  B. r_unknown ：k=1 均值 {np.mean([r[3] for r in tr]):.4f}"
          f" → k=8 均值 {np.mean([r[3] for r in hi]):.4f}"
          f"（{'上升 ✅ 符合直觉' if np.mean([r[3] for r in hi]) > np.mean([r[3] for r in tr]) else '下降'}）")
print("\n若 A 下降而 B 上升：A 的定义使「答得越多相关越低」，不能当预测准确度；"
      "B 才是「答得越多越准」的正确度量。")
