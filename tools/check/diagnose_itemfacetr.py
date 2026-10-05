#!/usr/bin/env python3
"""查清 `AD.itemFacetR` 与 `INF.item_dim_corr` 为何对不上（0.712 vs 0.371）。

线索：两处生成代码的**公式相同**：
  adaptive-network:      IF[i,j] = corr(R[:, i], facet_full[f])
  correlation-network:   item_facet_corr[i][j] = corr(R[:, i], facet_full[facets[j]])
且都用 `fo[f]`（1-based 题号）。那差异只可能来自：
  ① **列序不同**：adaptive 的 facets 是**主题序**（anxiety, anger, …），
     correlation-network 的 facets 是**字母序**（achievementstriving, …）
  ② 或某个环节取错了列/行

本脚本按**名字**对齐两边的列，逐题比较同一 (题, facet) 格的值。
若按名字对齐后一致 → 差异纯属列序，数据本身没问题（前端只需正确按名字取列）。
若按名字对齐后仍不一致 → 两个文件对同一个量给了不同值，需要查生成过程。
"""

from __future__ import annotations

import json
import os
import statistics as st
import sys

ROOT = r"C:\Codes\emohealth-20260930-full\emohealth"
ad = json.load(open(os.path.join(ROOT, "data", "adaptive-network.json"),
                    encoding="utf-8"))
net = json.load(open(os.path.join(ROOT, "data", "correlation-network.json"),
                     encoding="utf-8"))
inf = json.load(open(os.path.join(ROOT, "data", "inference", "ipip-neo.json"),
                     encoding="utf-8"))
inst = json.load(open(os.path.join(ROOT, "data", "instruments", "ipip-neo.json"),
                      encoding="utf-8"))

ad_f = ad["facets"]            # 主题序
net_f = net["facets"]          # 字母序
print(f"AD  facets（前 6）：{ad_f[:6]}")
print(f"NET facets（前 6）：{net_f[:6]}")
print(f"两者集合相同：{set(ad_f) == set(net_f)}")

IF = ad["itemFacetR"]          # 300 × 30
IFC = net["item_facet_corr"]   # 300 × 30

# 按名字对齐后逐题比较
diffs = []
for i in range(300):
    for j, f in enumerate(ad_f):
        if f in net_f:
            k = net_f.index(f)
            diffs.append(abs(IF[i][j] - IFC[i][k]))
print(f"\nAD vs NET（按名字对齐）逐格 |Δ|："
      f"中位 {st.median(diffs):.4f}  最大 {max(diffs):.4f}")
if max(diffs) < 0.01:
    print("  → ✅ 两文件对同一个量给出一致值；差异纯属**列序**")
else:
    print("  → ❌ 按名字对齐后仍不一致，两个文件对同一量给了不同值")

# AD 的行序是否 = 题号？
print(f"\nAD.itemFacetR[0] 的 argmax（主题序）= {max(range(len(ad_f)), key=lambda j: IF[0][j])}"
      f" → {ad_f[max(range(len(ad_f)), key=lambda j: IF[0][j])]}")
print(f"NET.item_facet_corr[0] 的 argmax（字母序）= "
      f"{net_f[max(range(len(net_f)), key=lambda j: IFC[0][j])]}")
print(f"量表包第 1 题：{inst['items'][0]['text'][:40]}")
own = {}
for d in inst["dimensions"]:
    for iid in d.get("items") or []:
        own[iid] = d["id"]
print(f"  其归属 facet = {own[inst['items'][0]['id']]}")

# INF 的第 1 题
iid0 = inst["items"][0]["id"]
row = inf["item_dim_corr"][iid0]
top = sorted(row.items(), key=lambda kv: -kv[1])[:3]
print(f"\nINF.item_dim_corr[{iid0}] 前三：{[(k, v) for k, v in top]}")
print(f"AD 第 1 题对自己 facet 的值："
      f"{IF[0][ad_f.index(own[iid0])] if own[iid0] in ad_f else '（该 facet 不在 AD）'}")
print(f"NET 第 1 题对自己 facet 的值："
      f"{IFC[0][net_f.index(own[iid0])] if own[iid0] in net_f else '（对该 facet 名不匹配）'}")
