#!/usr/bin/env python3
"""核清「大五 min_own 口径不一致」到底是什么，以及差异的实际后果。

背景：前端有两条「某维度答够几题才算可靠」的来源：
  · legacy（大五分级模式）读 `data/unlock-network.json` 的 `min_own` → 写死的 2
  · 新的推断数据 `data/inference/<code>.json` 的 `min_own` → 从 partial 曲线推
两者对同一件事给了不同值，需要说清：
  ① 各自的值是多少、怎么算出来的
  ② 为什么会不同（它们回答的其实是**不同的问题**吗？）
  ③ 实际后果：用户会看到什么差别
"""

from __future__ import annotations

import json
import os
import sys

ROOT = r"C:\Codes\emohealth-20260930-full\emohealth"

un = json.load(open(os.path.join(ROOT, "data", "unlock-network.json"),
                    encoding="utf-8"))
inf = json.load(open(os.path.join(ROOT, "data", "inference", "ipip-neo.json"),
                     encoding="utf-8"))
pa = json.load(open(os.path.join(ROOT, "data", "partial-administration.json"),
                    encoding="utf-8"))
net = json.load(open(os.path.join(ROOT, "data", "correlation-network.json"),
                     encoding="utf-8"))

print("=== ① unlock-network.json（legacy 用的）===")
print(f"  顶层键：{list(un.keys())}")
print(f"  min_own = {un.get('min_own')!r}")
if un.get("note"):
    print(f"  note：{un['note']}")
if un.get("threshold_r") is not None:
    print(f"  threshold_r = {un['threshold_r']}")

print("\n=== ② inference/ipip-neo.json（新推断数据用的）===")
mo = inf.get("min_own") or {}
vals = sorted(set(mo.values())) if mo else []
print(f"  条目数 {len(mo)}｜取值 {vals}")
sample = list(mo.items())[:5]
print(f"  样例：{sample}")
print(f"  quality：{json.dumps(inf.get('quality') or {}, ensure_ascii=False)[:200]}")

print("\n=== ③ partial-administration.json（min_own 的推算依据）===")
print(f"  question：{pa.get('question')}")
print(f"  key_metric：{pa.get('key_metric')}")
th = pa.get("thresholds") or {}
print(f"  thresholds 键：{list(th)}")
for k, v in list(th.items())[:8]:
    print(f"    {k}: {v}")
pf = pa.get("per_facet") or {}
one = list(pf.items())[:1]
if one:
    f, row = one[0]
    print(f"  per_facet[{f}] 类型 {type(row).__name__}"
          + (f" 键 {list(row)[:6]}" if isinstance(row, dict) else ""))
    if isinstance(row, dict):
        print(f"    内容样例：{json.dumps(row, ensure_ascii=False)[:260]}")
