#!/usr/bin/env python3
"""测绘所有**待复核**的中译，为「继续复核」定范围与判据。

背景：按 R1（判据是内容是否正确），中译的**复核状态**必须如实标注。
现状里存在几档标记：
  · 「已人工核对」（如 IPIP-NEO 300 条）
  · 「subagent 初译（待人工复核）」（PID-5 220 + DSM 22）
  · 「subagent 重译（待人工复核）」（L1 第 23 题）

本脚本列出分档与逐条清单，供逐条复核使用。
"""

from __future__ import annotations

import io
import json
import os
import sys
from collections import Counter

sys.path.insert(0, r"C:\Codes\emohealth-20260930-full\emohealth\tools")
from _root import find_root  # noqa: E402
ROOT = str(find_root())

db = json.load(io.open(os.path.join(ROOT, "data", "text-db", "text-db.json"),
                       encoding="utf-8"))
entries = db["entries"]
print(f"文本库条目 {len(entries)}\n")

src = Counter()
for k, e in entries.items():
    s = (e.get("zh_source") or "").strip() or "（无 zh_source）"
    # 归一化：去掉括号里的细节
    src[s] += 1

print("=== zh_source 分档 ===")
for s, n in src.most_common(30):
    print(f"  {n:5}  {s[:96]}")

# 待复核清单
pend = {k: e for k, e in entries.items()
        if "待人工复核" in (e.get("zh_source") or "")
        or "待复核" in (e.get("zh_source") or "")
        or "初译" in (e.get("zh_source") or "")}
print(f"\n=== 待复核条目：{len(pend)} 条 ===")

# 按所属量表分组
inst_of = {}
for k, e in entries.items():
    for c in (e.get("codes") or []):
        inst_of.setdefault(k, set()).add(c)


def which(k, e):
    ins = e.get("instruments") or []
    return ins[0] if ins else "（未关联量表）"


by = Counter(which(k, e) for k, e in pend.items())
for inst, n in by.most_common():
    print(f"  {inst:28}{n:5} 条")

out = os.path.join(ROOT, "research", "text-review-queue.json")
json.dump({k: {"en": pend[k].get("en"), "zh": pend[k].get("zh"),
               "zh_source": pend[k].get("zh_source"),
               "instruments": pend[k].get("instruments")}
           for k in pend}, io.open(out, "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(f"\n清单已写出：{out}（{os.path.getsize(out)} B）")

# 抽样看几条
print("\n=== 抽样（前 5 条）===")
for k in list(pend)[:5]:
    e = pend[k]
    print(f"  EN: {str(e.get('en'))[:88]}")
    print(f"  ZH: {str(e.get('zh'))[:88]}")
    print(f"  源: {e.get('zh_source')}")
    print()
