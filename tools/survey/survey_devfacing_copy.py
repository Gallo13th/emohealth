#!/usr/bin/env python3
"""测绘界面里的「开发者/审阅者向」文案 —— 这些不该出现在用户端。

用户的判据
==========
> 现在应该真正适合用户端使用。文本中有大量的文案是你展示给我，或者说展示给
> 开发者看的**解释文本、依据**等等，这些内容应该**隐藏**。

分类
====
A. **溯源/依据**：meaning_basis、meaning_source、zh_source、出处、手册原文、项目自撰
B. **工程术语**：缺失不猜、推断徽章、conf_r、维度 id、ceilings
C. **开发者指标**：门槛数值、已达上限 %、耗时 ms、n_slow、候选池
D. **方法论免责**：结构性排布、非实证、不是…相关
E. **调试标记**：data-* 属性（不可见但会进源码/截图）

本脚本把 `ui/index.html` 里**会渲染成文字**的这类内容列出来，供逐个决定
「隐藏 / 移到关于页 / 改成用户语言 / 保留」。
"""

from __future__ import annotations

import io
import os
import re
import sys

ROOT = r"C:\Codes\emohealth-20260930-full\emohealth"
P = os.path.join(ROOT, "ui", "index.html")
s = io.open(P, encoding="utf-8").read()
lines = s.split("\n")

PATTERNS = {
    "A 溯源/依据": r"meaning_basis|meaning_source|zh_source|手册原文|项目自撰|"
                   r"manual_verbatim|manual_labels|project_editorial|出处|来源：|依据",
    "B 工程术语": r"缺失不猜|推断」|官方分|conf_r|confidence_r|dim_ceiling|"
                  r"ceiling_ratio|cross_dim|borrowed|n_answered|ansVer",
    "C 开发者指标": r"门槛|已达上限|ceiling_pct|耗时|ms\b|n_slow|候选池|utility|"
                    r"增益|信息增益|跨维|r=|r_total",
    "D 方法论免责": r"结构性排布|非实证|不是实证|题间相关|免责|不构成诊断|"
                    r"不是诊断|仅供参考|本量表不",
    "E 调试标记": r"data-f=|data-basis|data-dim|data-unlock|data-r\b|data-pred|"
                  r"data-status|data-display|data-reco",
}

print(f"ui/index.html：{len(lines)} 行 / {len(s)} 字符\n")
tot = {}
for label, pat in PATTERNS.items():
    hits = [(i + 1, ln.strip()) for i, ln in enumerate(lines) if re.search(pat, ln)]
    tot[label] = len(hits)
    print("=" * 78)
    print(f"{label} —— 命中 {len(hits)} 行")
    print("=" * 78)
    for i, ln in hits[:14]:
        # 只看像「会渲染成文字」的：含中文或字符串字面量
        print(f"  L{i:5}: {ln[:104]}")
    if len(hits) > 14:
        print(f"  … 另 {len(hits) - 14} 行")
    print()

print("=" * 78)
print("汇总")
print("=" * 78)
for k, v in tot.items():
    print(f"  {k:14}{v:5} 行")

# 额外：找出所有会被拼进 innerHTML 的中文长句（可能是解释性文案）
print()
print("=" * 78)
print("会被渲染的中文解释性长句（含「的」「说明」「解释」等，≥18 字）")
print("=" * 78)
n = 0
for i, ln in enumerate(lines):
    for m in re.finditer(r"['\"`]([^'\"`]{18,})['\"`]", ln):
        t = m.group(1)
        if re.search(r"[\u4e00-\u9fff]", t) and re.search(
                r"依据|来源|说明|解释|标注|不是|非|手册|统计|置信|推断|上限|门槛|耗时", t):
            print(f"  L{i + 1:5}: {t[:96]}")
            n += 1
            if n > 18:
                break
    if n > 18:
        print("  …")
        break
