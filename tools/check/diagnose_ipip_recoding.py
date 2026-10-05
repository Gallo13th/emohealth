#!/usr/bin/env python3
"""裁决：Johnson 的 `ipip20993.dat` 到底**有没有**预先重编码反向题？

为什么必须裁清
==============
两个脚本对同一份数据做了**相反**的处理：
  · `build_adaptive_data.py`：`as_construct_direction(..., expect_recoded=True)`
    —— 认定数据**已**重编码，不再翻转（其 note 也写「数据**已**反向重编码 —— 不要再翻转」）
  · `analyze_correlation_network.py`：`R[:, key<0] = 6 - R[:, key<0]` —— **又翻了一次**
实测两个产物由此产生系统性差异（`AD.itemFacetR` 与 `NET.item_facet_corr` 按名字对齐后
中位 |Δ|=0.118、最大 1.389），且 `AD` 的 argmax 正确指向题目自己的面（anxiety 0.712），
而 `NET` 指向 depression —— 说明**多翻的那次是错的**。

判据（与裁 PID-5 反向键同一手法，用数据说话）
============================================
取 canon 里 `key < 0`（反向题），算它与**同 facet 其余题之和**的相关：
  · 若**未翻转时为负、翻转后为正** → 数据**未**预编码，`analyze_correlation_network` 对
  · 若**未翻转时为正** → 数据**已**预编码，`build_adaptive_data` 对，前者多翻了
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
print(f"数据：{DATA.split('/')[-1]}  {X.shape[0]} 行 → 完整作答 {Xc.shape[0]} 行")

rev = [it for it in items if it["key"] < 0]
print(f"canon 标了 {len(rev)} 道反向题\n")
print(f"{'题号':>5}{'facet':>16}{'未翻转 r':>12}{'翻转后 r':>12}  判定")


def corr(a, b):
    return float(np.corrcoef(a, b)[0, 1])


verdict = {"raw_pos": 0, "raw_neg": 0}
for it in rev[:12] + rev[-3:]:
    o = it["order"]
    others = [x for x in fo[it["facet"]] if x != o]
    comp = Xc[:, [x - 1 for x in others]].sum(axis=1)
    r_raw = corr(Xc[:, o - 1], comp)
    r_flip = corr(6 - Xc[:, o - 1], comp)
    v = ("数据**已**预编码" if r_raw > 0 else "数据**未**预编码，需翻转")
    verdict["raw_pos" if r_raw > 0 else "raw_neg"] += 1
    print(f"{o:>5}{it['facet']:>16}{r_raw:>12.3f}{r_flip:>12.3f}  {v}")

# 全量裁决
raw_r = []
for it in rev:
    o = it["order"]
    others = [x for x in fo[it["facet"]] if x != o]
    comp = Xc[:, [x - 1 for x in others]].sum(axis=1)
    raw_r.append(corr(Xc[:, o - 1], comp))
pos = sum(1 for r in raw_r if r > 0)
print(f"\n全部 {len(rev)} 道反向题：未翻转时与同 facet 其余题**正相关**的有 {pos} 道"
      f"（{pos / len(rev):.0%}）")
print(f"中位 r（未翻转）= {np.median(raw_r):+.3f}")
print()
if pos / len(rev) > 0.8:
    print("结论：数据【已】预编码 → `build_adaptive_data` 对；")
    print("      `analyze_correlation_network` 多翻了一次 → data/correlation-network.json 错了。")
else:
    print("结论：数据【未】预编码，需要翻转 → `analyze_correlation_network` 对；")
    print("      则 `build_adaptive_data` 少了翻转 → data/adaptive-network.json 错了。")
