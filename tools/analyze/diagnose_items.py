#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""题目级诊断：用 Johnson (2005) 的 20,993 人网络样本，找出**最需要脚手架**的题目。

动机（D24 与用户的排序判断）：
  认知访谈应该在我们有了标准化使用之后，用真实数据挑访谈目标，而不是凭空选。
  铺量同理——300 题的脚手架不该按题号顺序写，而应按**题目实际有多容易出问题**排序。

诊断指标（都在 facet 内计算，因为 facet 是被测构念）：

  1. `item_total_r`  —— 该题与所属 facet 其余 9 题之和的相关。
                        低 = 这题可能在测量别的东西，或表述被误解。
  2. `missing_rate`  —— 该题的空答率。异常高 = 题目让人不愿答或看不懂。
  3. `extreme_rate`  —— 选两端（1 或 5）的比例。过高 = 题目过于绝对，缺少中间态。
  4. `neutral_rate`  —— 选 3 的比例。过高 = 题目模糊，答不出方向。
  5. `reverse_flag_mismatch` —— 反向题在还原前后的表现差异（仅诊断用）。

综合成 `priority_score`：分数越高越该优先撰写脚手架。

输出：`data/item-diagnostics.json`
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
OUT = os.path.join(ROOT, "data/item-diagnostics.json")


def main() -> int:
    canon = json.load(open(CANON, encoding="utf-8"))
    by_order = {i["order"]: i for i in canon["items"]}

    df = pd.read_csv(DATA, sep="\t", dtype=str, keep_default_na=False)
    ic = [f"I{i}" for i in range(1, 301)]
    raw = df[ic].replace({"": np.nan, " ": np.nan, "0": np.nan})
    items = raw.apply(pd.to_numeric, errors="coerce").to_numpy(float)
    n_total = items.shape[0]

    log = [f"样本 {n_total} 条 × 300 题"]

    facet_of = np.array([by_order[n]["facet"] for n in range(1, 301)])
    key = np.array([by_order[n]["key"] for n in range(1, 301)], dtype=float)

    rows = []
    for n in range(1, 301):
        it = by_order[n]
        col = items[:, n - 1]
        obs = col[~np.isnan(col)]
        same = np.where(facet_of == it["facet"])[0]
        others = [c for c in same if c != n - 1]
        # 所属 facet 其余题之和（缺失按行处理）
        rest = np.nansum(items[:, others], axis=1)
        ok = ~np.isnan(col) & ~np.isnan(rest)
        r = float(np.corrcoef(col[ok], rest[ok])[0, 1]) if ok.sum() > 30 else float("nan")

        miss = float(np.isnan(col).sum()) / n_total
        total = max(obs.size, 1)
        extreme = float(((obs == 1) | (obs == 5)).sum()) / total
        neutral = float((obs == 3).sum()) / total
        rows.append({
            "order": n, "id": it["id"], "facet": it["facet"], "key": it["key"],
            "text": it["text"],
            "item_total_r": round(r, 4),
            "missing_rate": round(miss, 4),
            "extreme_rate": round(extreme, 4),
            "neutral_rate": round(neutral, 4),
            "mean": round(float(obs.mean()), 3),
            "sd": round(float(obs.std()), 3),
        })

    # ---- 综合优先级 ----
    r_all = np.array([x["item_total_r"] for x in rows])
    med = np.nanmedian(r_all)
    for x in rows:
        score = 0.0
        # 1) 与 facet 其余题相关偏低
        if not np.isnan(x["item_total_r"]):
            score += max(0.0, med - x["item_total_r"]) * 10
        # 2) 空答异常
        score += x["missing_rate"] * 20
        # 3) 过于两极化（缺少中间态）
        score += max(0.0, x["extreme_rate"] - 0.5) * 2
        # 4) 中立选项过高（题目模糊）
        score += max(0.0, x["neutral_rate"] - 0.35) * 3
        x["priority_score"] = round(score, 3)

    rows.sort(key=lambda x: -x["priority_score"])

    # ---- 按 facet 汇总，给出铺量顺序 ----
    facets: dict[str, list[dict]] = {}
    for x in rows:
        facets.setdefault(x["facet"], []).append(x)
    facet_rank = sorted(
        ({"facet": f, "mean_priority": round(float(np.mean([i["priority_score"] for i in v])), 3),
          "worst_item_priority": v[0]["priority_score"],
          "n_items": len(v)}
         for f, v in facets.items()),
        key=lambda x: -x["mean_priority"],
    )
    log.append(f"facet 诊断完成，共 {len(facets)} 个")
    log.append("优先级最高的 5 个 facet：" +
               ", ".join(f"{f['facet']}({f['mean_priority']})" for f in facet_rank[:5]))

    payload = {
        "source": "Johnson, J. A. (2005) 网络样本，N=20,993",
        "data_file": "archive/datasets/osf-johnson/validity/ipip20993.dat",
        "purpose": "为脚手架铺量排序——按题目实际有多容易出问题，而不是按题号顺序",
        "metrics": {
            "item_total_r": "该题与所属 facet 其余 9 题之和的相关；低 = 可能在测别的东西或表述被误解",
            "missing_rate": "空答率；异常高 = 不愿答或看不懂",
            "extreme_rate": "选 1 或 5 的比例；过高 = 题目过于绝对",
            "neutral_rate": "选 3 的比例；过高 = 题目模糊",
            "priority_score": "综合分，越高越该优先",
        },
        "caveat": "这些指标是**代理指标**，不能直接证明某题被误解——"
                  "它们只提示哪里值得优先投入人力。真正的判定仍需认知访谈。",
        "facet_priority_order": facet_rank,
        "items_priority_order": [x["order"] for x in rows],
        "items": {str(x["order"]): x for x in rows},
        "build_log": log,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)

    print("\n".join(log))
    print(f"\n=== 优先级最高的 12 道题 ===")
    print(f"{'序':>4} {'facet':<18}{'key':>4}{'r':>8}{'空答':>7}{'极端':>7}{'中立':>7}{'分':>7}  题面")
    for x in rows[:12]:
        print(f"{x['order']:>4} {x['facet']:<18}{x['key']:>+4}{x['item_total_r']:>8.3f}"
              f"{x['missing_rate']:>7.3f}{x['extreme_rate']:>7.3f}{x['neutral_rate']:>7.3f}"
              f"{x['priority_score']:>7.2f}  {x['text'][:34]}")
    print(f"\n=== facet 铺量顺序（前 12）===")
    for f in facet_rank[:12]:
        print(f"  {f['facet']:<34}{f['mean_priority']:>7.3f}")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
