#!/usr/bin/env python3
"""测绘「保留 4 个核心模型、其余全删」的**影响面**——删之前必须先知道删多少。

保留清单（用户指定）
====================
  1. IPIP 大五（大五人格）         → data/instruments/ipip-neo.json
  2. MMPI-2                       → ⚠️ **项目里没有**（见报告）
  3. PID-5                        → data/instruments/pid-5.json
  4. DSM-5-TR（L1 + L2×8）         → data/instruments/dsm5tr-*.json

本脚本只**统计**：哪些要留、哪些要删、各占多少体积、涉及哪些 tools/content/archive。
"""

from __future__ import annotations

import json
import os
import sys

ROOT = r"C:\Codes\emohealth-20260930-full\emohealth"

# 4 个核心对应的量表代码（MMPI-2 无）
KEEP = {"IPIP-NEO", "PID-5", "DSM5TR-L1",
        "DSM5TR-L2-Depression", "DSM5TR-L2-Anger", "DSM5TR-L2-Anxiety",
        "DSM5TR-L2-Mania", "DSM5TR-L2-Repetitive", "DSM5TR-L2-Sleep",
        "DSM5TR-L2-Somatic", "DSM5TR-L2-Substance"}

INST = os.path.join(ROOT, "data", "instruments")
kept, dropped = [], []
for fn in sorted(os.listdir(INST)):
    if not fn.endswith(".json") or fn == "catalog.json":
        continue
    d = json.load(open(os.path.join(INST, fn), encoding="utf-8"))
    code = d["instrument"]
    entry = (code, fn, len(d["items"]), os.path.getsize(os.path.join(INST, fn)))
    (kept if code in KEEP else dropped).append(entry)

print("=" * 74)
print(f"一、量表：留 {len(kept)} 套 / 删 {len(dropped)} 套（共 {len(kept) + len(dropped)}）")
print("=" * 74)
print("【保留】")
for c, fn, n, sz in kept:
    print(f"  {c:26}{n:5} 题  {sz / 1024:8.0f} KB")
ks = sum(e[3] for e in kept)
ds = sum(e[3] for e in dropped)
print(f"  合计 {ks / 1024 / 1024:.1f} MB")
print(f"\n【删除】{len(dropped)} 套，合计 {ds / 1024 / 1024:.1f} MB")
print("  前 12 个：" + "、".join(e[0] for e in dropped[:12]) + " …")

print()
print("=" * 74)
print("二、顶层目录规模（判断删什么）")
print("=" * 74)
for d in ("archive", "data", "content", "tools", "ui", "research", "engine"):
    p = os.path.join(ROOT, d)
    if not os.path.isdir(p):
        continue
    n = sz = 0
    for base, _dd, files in os.walk(p):
        for f in files:
            n += 1
            try:
                sz += os.path.getsize(os.path.join(base, f))
            except OSError:
                pass
    print(f"  {d:10}{n:6} 文件  {sz / 1024 / 1024:9.1f} MB")

print()
print("=" * 74)
print("三、随量表一起被删的**数据产物**（按是否只服务被删量表判断）")
print("=" * 74)
DATA = os.path.join(ROOT, "data")
for f in sorted(os.listdir(DATA)):
    p = os.path.join(DATA, f)
    if os.path.isfile(p):
        print(f"  {f:38}{os.path.getsize(p) / 1024:8.1f} KB")
    else:
        n = sum(len(fs) for _b, _d, fs in os.walk(p))
        print(f"  {f + '/':38}{n:6} 文件")

print()
print("=" * 74)
print("四、MMPI-2 在项目里是否存在")
print("=" * 74)
hits = []
for base, _dd, files in os.walk(ROOT):
    if any(x in base for x in ("MANIFEST", ".git", "__pycache__")):
        continue
    for f in files:
        if "mmpi" in f.lower():
            hits.append(os.path.relpath(os.path.join(base, f), ROOT))
print(f"  文件名含 mmpi 的：{len(hits)} 个")
for h in hits[:10]:
    print(f"    {h}")
print("  （另行检查 archive 内文提及，见报告）")
