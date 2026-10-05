#!/usr/bin/env python3
"""测绘：选项锚点里有多少是**无定量的模糊程度词**。

用户的问题
==========
> 在填表的时候有一个很大的问题就是**不知道什么是少数情况，什么是若干情况，
> 什么是平常or经常**。这些情景你应当结合**文献的具体描述，给出：定量，
> 或者**说明完全凭借自知**。

即：每个程度词要么有**可核对的定量**（天数/次数/比例），要么**明确告诉用户
「凭你自己的判断」**（因为量表/手册没给量化标准）。最坏的是给一个看起来专业
但无法操作的模糊说法（「若干天」「经常」）。

本脚本统计三态分布
==================
  D. **有定量**：说明里含数字/天数/次数/比例（如「≥7 天」「每天 2 次」）
  V. **凭自知（已声明）**：说明里明确写了「凭你自己的判断/没有统一标准」之类
  X. **模糊无据**：只有程度词，既无定量也未声明凭自知 ← **要修的就是这一类**
"""

from __future__ import annotations

import io
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, r"C:\Codes\emohealth-20260930-full\emohealth\tools")
from _root import find_root  # noqa: E402
ROOT = str(find_root())
#: 用整名而不是 `D`——单字母名 `D` 会与下面的统计字典键 `"D 有定量"` / `["D"]` 撞名，
#: 让 tools/check_architecture.py 把它当成「路径变量用在既非读也非写的上下文」（假阳性）。
ITEMS_DIR = os.path.join(ROOT, "data", "items-structured")

# 模糊程度词（中英）
VAGUE = r"少数|若干|有时|经常|平常|偶尔|时常|常常|多半|大都|通常|一般|frequently|" \
        r"often|sometimes|occasionally|rarely|usually|seldom|a few|several"
# 定量信号：**数字+单位**，或本身表示「半数/平均」这类可运算的量。
# ⚠️ 2026-10-05 修订（task-21）：原先把「每天/每日/每周/每月」当作无条件定量信号，
# 结果把手册标签「nearly every day（几乎每天）」也算成定量——而它恰恰是**没有定义**的锚点。
# 现加负向断言：被「几乎 / 接近 / 近乎 / 差不多」修饰的频率词**不算定量**。
QUANT = r"\d+\s*(?:天|日|次|周|月|年|小时|分钟|%|百分比)|" \
        r"(?<!几乎)(?<!接近)(?<!近乎)(?<!差不多)(?:每天|每日|每周|每月)|" \
        r"至少|超过|少于|不足|一半|半数|平均|" \
        r"\d+\s*(?:day|days|time|times|week|month|hour|minute)"
# 「凭自知」声明信号
SELF = r"凭你自己的|自行判断|自己判断|没有统一标准|无统一标准|按你自己的感觉|" \
       r"依你自己的|你个人的标准|无量化|未给.{0,6}量化|未提供.{0,6}标准|" \
       r"主观判断|取决于你自己"

print(f"目录 {ITEMS_DIR}\n")
tri = Counter()
by_scale = defaultdict(Counter)
vague_no_quant = []
for fn in sorted(os.listdir(ITEMS_DIR)):
    if not fn.endswith(".json") or fn == "index.json":
        continue
    d = json.load(io.open(os.path.join(ITEMS_DIR, fn), encoding="utf-8"))
    code = d.get("instrument") or fn[:-5]
    for it in d.get("items") or []:
        for o in ((it.get("response") or {}).get("options") or []):
            lab = (o.get("label_zh") or "") + " " + (o.get("label_en") or "")
            mean = o.get("meaning_zh") or ""
            blob = lab + " " + mean
            has_q = bool(re.search(QUANT, blob))
            has_s = bool(re.search(SELF, mean))
            has_v = bool(re.search(VAGUE, blob, re.I))
            if has_q:
                tri["D 有定量"] += 1
                by_scale[code]["D"] += 1
            elif has_s:
                tri["V 凭自知(已声明)"] += 1
                by_scale[code]["V"] += 1
            elif has_v:
                tri["X 模糊无据"] += 1
                by_scale[code]["X"] += 1
                if len(vague_no_quant) < 26:
                    vague_no_quant.append((code, lab.strip()[:40], mean[:88]))
            else:
                tri["其他"] += 1
                by_scale[code]["O"] += 1

print("=== 总分布 ===")
for k, v in tri.most_common():
    print(f"  {k:18}{v:5}")
print(f"  合计 {sum(tri.values())} 个选项")

print("\n=== 各量表 ===")
print(f"  {'量表':26}{'有定量':>7}{'凭自知':>7}{'模糊无据':>9}{'其他':>6}")
for code in sorted(by_scale):
    c = by_scale[code]
    print(f"  {code:26}{c['D']:>7}{c['V']:>7}{c['X']:>9}{c['O']:>6}")

print(f"\n=== 「模糊无据」样例（共 {tri['X 模糊无据']} 个，示 26）===")
for code, lab, mean in vague_no_quant:
    print(f"  [{code}] {lab}")
    print(f"        {mean}")
