#!/usr/bin/env python3
"""测绘：哪些注释在**大量重复**（应该提到更高级别），以及界面上的「研究性措辞」。

用户的判据
==========
> **不要在每个选项中都注明某些完全相同的注释**。应该做好**提醒的分级**内容，
> 不应该把高级内容放进低级选项里**大量重复**。以及进一步清理没有必要写出来的注释，
> 你要以一个**仅仅是来参与量表测评的用户**的角度出发，而非一个**专业的心理学工作者
> 来做量表文本本身研究**的态度出发。诸如「｜与 Level 1「Personality Functioning」域
> 相接（推论，非手册原文）」、「判据模型算式口径」、「本条提醒的出处」这些，
> **全部都不要提**。

本脚本量化两件事
================
① **选项级重复**：同一个句子/后缀在多少个选项里重复出现（→ 应提到册级/量表级）
② **研究性措辞**：界面上「做研究」才会说的话（→ 应删）
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
D = os.path.join(ROOT, "data", "items-structured")

print("=" * 80)
print("① 选项级「整句重复」——同一个 meaning_zh 出现在多少个选项里")
print("=" * 80)
cnt = Counter()
samples = {}
for fn in sorted(os.listdir(D)):
    if not fn.endswith(".json") or fn == "index.json":
        continue
    d = json.load(io.open(os.path.join(D, fn), encoding="utf-8"))
    code = d.get("instrument") or fn[:-5]
    for it in d.get("items") or []:
        for o in ((it.get("response") or {}).get("options") or []):
            m = (o.get("meaning_zh") or "").strip()
            if len(m) > 8:
                cnt[m] += 1
                samples.setdefault(m, code)
print(f"  不同说明句 {len(cnt)} 种；总选项 {sum(cnt.values())}")
print(f"\n  重复最多的 12 句：")
for m, n in cnt.most_common(12):
    print(f"    ×{n:4}  [{samples[m]}] {m[:88]}")

print()
print("=" * 80)
print("② 「后缀重复」——把说明按标点切碎，看哪一段在多选项里重复")
print("=" * 80)
frag = Counter()
for fn in sorted(os.listdir(D)):
    if not fn.endswith(".json") or fn == "index.json":
        continue
    d = json.load(io.open(os.path.join(D, fn), encoding="utf-8"))
    for it in d.get("items") or []:
        for o in ((it.get("response") or {}).get("options") or []):
            m = (o.get("meaning_zh") or "")
            for part in re.split(r"[—–\-—。；;\n]+", m):
                p = part.strip()
                if len(p) >= 12:
                    frag[p] += 1
for p, n in frag.most_common(14):
    print(f"    ×{n:4}  {p[:96]}")

print()
print("=" * 80)
print("③ 界面上的「研究性措辞」（用户在答题页看到的）")
print("=" * 80)
UI = os.path.join(ROOT, "ui", "index.html")
if os.path.exists(UI):
    s = io.open(UI, encoding="utf-8").read()
    lines = s.split("\n")
    PAT = {
        "推论/非手册原文": r"推论|非手册原文|手册原文",
        "判据/模型/算式/口径": r"判据模型|算式|口径|判据",
        "出处/来源": r"本条提醒的出处|出处|来源[:：]",
        "元说明（手册没给…）": r"手册没有给出|手册未|手册只给|没有统一标准",
        "专业术语（维度/域/构念）": r"构念|因子|载荷|信度|效度|常模来源",
    }
    for label, pat in PAT.items():
        hits = [(i + 1, ln.strip()) for i, ln in enumerate(lines) if re.search(pat, ln)]
        print(f"\n  【{label}】{len(hits)} 行")
        for i, ln in hits[:6]:
            print(f"    L{i:5}: {ln[:92]}")
