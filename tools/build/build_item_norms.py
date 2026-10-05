#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""题目级常模分布 —— 为「情景完成后的基线比较」提供原料。

**为什么需要它**：一个情景含 30 题、每个 facet 恰好 1 题，
因此**算不出任何 facet 分数**（单题与完整 facet 测量的相关最差仅 0.51，
见 `data/partial-administration.json`）。

但可以做的、且站得住的是：**题目级的位置比较**——
把用户在某一题上的作答，换算成它在参照样本分布中的位置。

本脚本为 300 道题各算出：
  · 参照样本的作答分布（选 1/2/3/4/5 的比例）
  · 均值与标准差
  · **每个选项对应的百分位**——UI 可直接把一次作答映射成一个位置
  · 单题分辨力的诚实指标：相邻选项之间的百分位跨度
    （跨度越大，说明"1 题"能把人分得越开；越小则越说明这题区分力弱）

输出：`data/item-norms.json`

⚠️ 使用边界（必须随数据一同传递）：
  这些是**题目级**分布，用于情景内的位置比较。
  **不得**把单题百分位当作该 facet 的测量结果。
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
DATA = os.path.join(ROOT, "archive/datasets/osf-johnson/validity/ipip20993.dat")
CANON = os.path.join(ROOT, "data/ipip-neo-300.json")
OUT = os.path.join(ROOT, "data/item-norms.json")


def main() -> int:
    canon = json.load(open(CANON, encoding="utf-8"))
    by_order = {i["order"]: i for i in canon["items"]}

    df = pd.read_csv(DATA, sep="\t", dtype=str, keep_default_na=False)
    ic = [f"I{i}" for i in range(1, 301)]
    X = (df[ic].replace({"": np.nan, " ": np.nan, "0": np.nan})
         .apply(pd.to_numeric, errors="coerce").to_numpy(float))

    items = {}
    weak = []
    for n in range(1, 301):
        it = by_order[n]
        col = X[:, n - 1]
        obs = col[~np.isnan(col)]
        cnt = np.array([(obs == v).sum() for v in (1, 2, 3, 4, 5)], dtype=float)
        total = cnt.sum()
        prop = cnt / total if total else np.zeros(5)
        # 累计分布（选 1..v 的比例）——用于把一次作答映射成百分位
        cum = np.cumsum(prop)
        # 相邻选项间的百分位跨度：越大 = 单题把人分得越开
        spans = np.diff(cum)
        # 方向对齐：反向题按 6-x 翻转，使「高分 = 该 facet 高端」
        if it["key"] < 0:
            prop = prop[::-1]
            cum = np.cumsum(prop)
            spans = np.diff(cum)
        items[str(n)] = {
            "id": it["id"], "facet": it["facet"], "key": it["key"],
            "text": it["text"], "n": int(total),
            "mean": round(float(obs.mean()), 3),
            "sd": round(float(obs.std()), 3),
            "prop_1_to_5": [round(float(p), 4) for p in prop],
            "cum_prop": [round(float(c), 4) for c in cum],
            "option_pct": [round(float(c) * 100, 1) for c in cum],
            "max_adjacent_span_pct": round(float(spans.max()) * 100, 1) if len(spans) else None,
            "min_adjacent_span_pct": round(float(spans.min()) * 100, 1) if len(spans) else None,
        }
        if len(spans) and spans.max() < 0.15:
            weak.append((n, it["facet"], round(float(spans.max()) * 100, 1), it["text"]))

    payload = {
        "source": "Johnson (2005) 网络样本，N=20,993",
        "purpose": "情景完成后的**题目级**位置比较（不是 facet 分数）",
        "direction": "已按计分键对齐：数值越高 = 越靠该 facet 的高端",
        "usage_boundary": "⚠️ 这是题目级分布。不得把单题百分位当作该 facet 的测量结果——"
                          "单题与完整 facet 测量的相关最差仅 0.51（见 partial-administration.json）。",
        "option_pct_meaning": "在该题上选到该选项或更靠高端的人所占百分比",
        "resolution_note": "单题只有 5 个选项，位置分辨率天然很粗。"
                           "max_adjacent_span_pct 越小，说明该题的相邻选项在人群中越挤，"
                           "单题越不能把人分开。",
        "items": items,
        "weak_items": [{"order": o, "facet": f, "max_span_pct": s, "text": t}
                       for o, f, s, t in sorted(weak, key=lambda x: x[2])[:20]],
        "build_log": [f"计算 {len(items)} 道题的分布"],
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)

    print(f"计算 {len(items)} 道题的常模分布 → {os.path.relpath(OUT, ROOT)}")
    print(f"\n=== 单题分辨力最弱的 10 题（相邻选项百分位跨度最小）===")
    print(f"{'序':>4} {'facet':<40}{'最大跨度%':>10}  题面")
    for o, f, s, t in sorted(weak, key=lambda x: x[2])[:10]:
        print(f"{o:>4} {f:<40}{s:>10.1f}  {t[:36]}")
    allspans = [v["max_adjacent_span_pct"] for v in items.values()]
    print(f"\n全部 300 题的相邻选项最大跨度：中位 {np.median(allspans):.1f}%  "
          f"范围 {min(allspans):.1f}%–{max(allspans):.1f}%")
    print(f"跨度 < 15% 的题（单题几乎分不开人）：{len(weak)} 题")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
