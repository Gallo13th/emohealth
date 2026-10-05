#!/usr/bin/env python3
"""看清 `UN.rel` 的结构与取值，判断「去掉 MIN_OWN 后第 1 环会不会误解锁」。

机制（`ui/index.html` 的 netR2 legacy 路径）
============================================
  R²_f = bᵀ A⁻¹ b
    A = 已答题之间的题间相关（m×m）
    b = 已答题与面向 f 的相关（取自 `UN.rel[f].r`，按 `rel[f].items` 的下标）
只答 1 题时 m=1：A=[1]、b=[r] → R² = r²  → 置信度 = |r|。
所以「只答 1 题能不能达标」完全由 `rel.r` 的最大值决定。

checklist
  · rel 里每个面向留了几题（是不是只留 34 题的子集）
  · rel.r 的取值范围（最大多少）→ 单题置信度上限
  · min_own_rationale 说「M=1 时第 1 环能解锁 8 个」是否与此矛盾
"""

from __future__ import annotations

import json
import os
import sys

ROOT = r"C:\Codes\emohealth-20260930-full\emohealth"
un = json.load(open(os.path.join(ROOT, "data", "unlock-network.json"),
                    encoding="utf-8"))
rel = un["rel"]
facets = un["facets"]
thr = un["threshold_r"]
print(f"facets 数 {len(facets)}｜threshold_r {thr}｜min_own {un['min_own']}\n")

tot_items = 0
allr = []
print(f"{'面向':>20}{'题数':>5}{'r 最小':>9}{'r 最大':>9}{'单题置信度上限':>16}")
for f in facets:
    r = rel.get(f)
    if not r:
        print(f"{f:>20}   （无 rel）")
        continue
    rs = r.get("r") or []
    tot_items += len(r.get("items") or [])
    if rs:
        allr.extend(rs)
    print(f"{f:>20}{len(rs):>5}{min(rs):>9.3f}{max(rs):>9.3f}{max(rs):>16.3f}")

print(f"\nrel 覆盖题次合计 {tot_items}（去重后 {len(set(t for f in facets for t in (rel.get(f, {}).get('items') or [])))}）")
print(f"全部 rel.r：最小 {min(allr):.3f}｜中位 {sorted(allr)[len(allr)//2]:.3f}｜最大 {max(allr):.3f}")
print(f"\n单题置信度上限 = max|r| = {max(allr):.3f}")
print(f"门槛 = {thr}")
if max(allr) < thr:
    print("  → 只答 1 题时**不可能**达标（r² < 门槛²）")
    print("     ⇒ 去掉 MIN_OWN 也不会在第 1 环误解锁（单题路径本身就过不了门槛）")
else:
    print("  → 存在单题即可达标的面向 ⇒ MIN_OWN 确有拦截作用")
    hits = [(f, max(rel[f]['r'])) for f in facets if rel.get(f, {}).get('r')
            and max(rel[f]['r']) >= thr]
    for f, v in sorted(hits, key=lambda x: -x[1])[:12]:
        print(f"      {f:>20}  max r = {v:.3f} ≥ {thr}")

print("\n=== 第 1 环（每面向第 1 题）答完时的情形 ===")
print("  第 1 环每题属不同面向；答 k 题时，各面向的已答题数 = 0 或 1。")
print("  · 对**已答**的面向：m=1（只有自己那 1 题）→ 置信度 = |rel.r[该题]|")
print("  · 对**未答**的面向：m=0 → netR2 返回 0 → 不解锁")
print("  所以第 1 环能解锁的，只能是「自己那道题的 |r| ≥ 门槛」的面向。")
print(f"  按上面数据：最多 {sum(1 for f in facets if rel.get(f, {}).get('r') and max(rel[f]['r']) >= thr)} 个面向可能达标。")
