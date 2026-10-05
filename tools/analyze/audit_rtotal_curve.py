#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用「**答题数 n**」直跑引擎：消除 k 的歧义，并核对 `conf_r` / `r_total` 的区别。

为什么有它
==========
用户质疑「只答一题就有 0.99，答更多反而偏离」。审计结论：验证报告里的 `k` 是
**遮住的题数**（`combinations(own, k)`），`k=1` 实为**答 9 题**，趋势本来就对；
是报告与字段名没写清（`validate_inference_holdout.py` 已改为 `k_masked` +
显式 `n_answered`，并加了「答题数 n 曲线」）。

本脚本用 n（**答了几题**）直接跑引擎，给出无歧义的曲线，并顺带核对：
  · `r_total`（估计准确度；把已答的本维度题当已知真值）应随 n 上升、答满 = 1；
  · `conf_r`（判据/可信度；**不把已答项当已知**）应随 n 上升但**始终 < r_total**；
  · 本维度答 1 题时，**别的维度**的作答会把 `conf_r` 抬高（task-17 起的跨维度借用）。

⚠️ 曾经的一个坑：本脚本原来读 `borrowed_ratio`，而引擎的字段名是
`borrowed_from_cross_dim`（task-17 起改名为 `cross_dim_share_of_prediction`），
于是打印恒为 0.00，被误读成「跨维借用恒为 0」。**字段名要对齐**。

用法：`python tools/analyze/audit_rtotal_curve.py`
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = str(find_root())
sys.path.insert(0, ROOT)

from engine import inference as EI  # noqa: E402

CASES = {
    "IPIP-NEO": ["anxiety", "depression", "activitylevel"],
    "PID-5": ["pid5_anhedonia", "pid5_depressivity", "pid5_irresponsibility"],
}


def curve(code: str) -> None:
    m = EI.load(code)
    print("=" * 104)
    print(f"【{code}】按「答题数 n」的曲线（本维度只答 n 题，无跨维度）")
    print(f"{'维度':>22}{'答 n 题':>8}{'官方分':>9}{'预测':>9}{'conf_r':>9}"
          f"{'旧口径':>9}{'r_total':>9}{'跨维借用(预测)':>16}")
    print("=" * 104)
    for dim in CASES[code]:
        own = m.dim_items[dim]
        for n in (1, 2, 3, 5, 8, len(own)):
            resp = {own[i]: 3 for i in range(min(n, len(own)))}
            r = EI.predict(m, resp)
            b = r["inferred"][dim]
            off = r["official"][dim]["value"]
            pred = b["predicted_score"]
            print(f"{m.dim_name[dim]:>22}{n:>8}"
                  f"{('—' if off is None else f'{off:.3f}'):>9}"
                  f"{('—' if pred is None else f'{pred:.3f}'):>9}"
                  f"{b['confidence_r']:>9.3f}{b['confidence_r_own_only']:>9.3f}"
                  f"{b['confidence_r_total']:>9.3f}"
                  f"{b['cross_dim_share_of_prediction'] * 100:>15.1f}%")
        print("-" * 104)

    print(f"\n【{code}】本维度 1 题 + 别的维度 k 题：conf_r 的跨维度增益")
    print(f"{'维度':>22}{'跨维 k':>8}{'conf_r':>9}{'旧口径':>9}{'增益':>9}")
    print("-" * 104)
    for dim in CASES[code][:2]:
        own = m.dim_items[dim]
        others = [i for i in m.ids if i not in set(own)]
        for k in (0, 5, 10, 30, len(others)):
            resp = {own[0]: 3}
            for i in others[:k]:
                resp[i] = 3
            b = EI.predict(m, resp)["inferred"][dim]
            print(f"{m.dim_name[dim]:>22}{k:>8}{b['confidence_r']:>9.3f}"
                  f"{b['confidence_r_own_only']:>9.3f}"
                  f"{b['cross_dim_borrow_gain']:>+9.4f}")
        print("-" * 104)


def main() -> int:
    for code in CASES:
        curve(code)
        print()
    print("判读：")
    print("  · `r_total` 随答题数【上升】，答满时 = 1（预测精确等于官方分）；")
    print("  · `conf_r`（判据/可信度）也随答题数上升，但**始终低于 `r_total`**")
    print("    —— 它不把已答项当真值，是保守下界；")
    print("  · 两者含义不同，界面文案必须分别标名，不能混用；")
    print("  · 「本维度未答题时禁止展示」是硬规则（引擎/JS 都返回 "
          "NO_OWN_ITEM_ANSWERED 且不给数值）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
