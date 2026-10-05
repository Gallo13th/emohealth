#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""情景模式的不变量测试。

固定住四条硬约束，防止后续改动悄悄破坏它们：
  T1  反向题的**方向语义**：在反向题上选低分 = 该面向的高端
  T2  **k≤2 一律不给分数**（单题相关最差 0.507）
  T3  **答题过程不含任何分值字段**（D30）
  T4  **面板 B 需要 ≥3 个情景**（否则没有「平时的你」做基线）
  T5  精度查表与实际题集一致
  T6  8 个情景恰好覆盖 300 题，不重不漏
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
sys.path.insert(0, ROOT)

from engine.scene import (  # noqa: E402
    SceneReference, _aligned, progress, scene_result, unlock_status,
)

FAIL = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'✅' if cond else '❌'} {name}" + (f"  —— {detail}" if detail else ""))
    if not cond:
        FAIL.append(name)


def main() -> int:
    ref = SceneReference()
    print("=== T1 反向题的方向语义 ===")
    rev = next(o for o in ref.items if ref.items[o]["key"] < 0)
    fwd = next(o for o in ref.items if ref.items[o]["key"] > 0)
    check("反向题选 1 → 对齐后为 5（该面向高端）", _aligned(rev, 1, ref) == 5,
          f"#{rev} {ref.items[rev]['text_zh']}")
    check("反向题选 5 → 对齐后为 1（该面向低端）", _aligned(rev, 5, ref) == 1)
    check("正向题选 5 → 对齐后为 5", _aligned(fwd, 5, ref) == 5)

    # 用一道真实反向题跑通完整面板，确认方向不被写反
    r = scene_result(ref.items[rev]["scene"],
                     {rev: 1}, ref, {rev})
    hit = next(x for x in r["panel_a"] if x["order"] == rev)
    check("在反向题上选 1，面板判定为 high", hit["direction"] == "high",
          f"位置 {hit['percentile']}")

    print("\n=== T2 k≤2 不给分数 ===")
    two = [o for o in ref.facet_orders["liberalism"]][:2]
    u = unlock_status(ref, set(two))
    check("k=2 时 liberalism 未解锁", u["liberalism"]["tier"] == "未解锁")
    check("k=2 时不展示分数", u["liberalism"]["show_score"] is False)
    three = [o for o in ref.facet_orders["liberalism"]][:3]
    u3 = unlock_status(ref, set(three))
    check("k=3 时给出精度", u3["liberalism"]["r"] is not None,
          f"r={u3['liberalism']['r']}")

    print("\n=== T3 答题过程不含分值 ===")
    p = progress(ref, set(two))
    blob = repr(p)
    bad = [k for k in ("score", "r\":", "percentile", "tier")
           if k in blob]
    check("progress() 无分值字段", not bad, f"发现 {bad}" if bad else "")
    check("progress() 有 note 说明只展示完成度", "完成度" in p["note"])

    print("\n=== T4 面板 B 需要 ≥3 个情景 ===")
    one_scene = set(ref.by_scene[ref.scenes()[0]])
    r1 = scene_result(ref.scenes()[0], {o: 4 for o in one_scene}, ref, one_scene)
    check("只完成 1 个情景时面板 B 不给结果",
          r1["panel_b"].get("status") == "NEEDS_MORE")
    multi = set()
    for s in ref.scenes()[:3]:
        multi |= set(ref.by_scene[s])
    r3 = scene_result(ref.scenes()[0], {o: 4 for o in multi}, ref, multi)
    check("完成 3 个情景后面板 B 给出结果",
          r3["panel_b"].get("status") != "NEEDS_MORE")

    print("\n=== T5 精度查表与实际题集一致 ===")
    orders = ref.facet_orders["anxiety"]
    for k in (3, 5, 8, 10):
        sel = set(orders[:k])
        m = ref.mask_of("anxiety", sel)
        expect = sum(1 << i for i in range(k))
        check(f"anxiety 取前 {k} 题的掩码正确", m == expect, f"{m} vs {expect}")
        r_tab = ref.precision_of("anxiety", sel)
        check(f"anxiety k={k} 能查到精度", r_tab is not None, f"r={r_tab}")
    check("空集时掩码为 None", ref.mask_of("anxiety", set()) is None)

    print("\n=== T7 分组与显示的百分位必须自洽（回归测试）===")
    # 曾经的 bug：分组用「绝对选项值」，显示用「相对百分位」，导致
    # 「偏向低端」那一组里混进了 84.2 这种高分位。两者含义不同：
    # 选 2 分但 84% 的人选 1，此人在这题上其实是相对偏高的。
    all_items = {o: 3 for o in ref.items}
    for sc in ref.scenes():
        r = scene_result(sc, all_items, ref, set(all_items))
        for grp, want in (("panel_a_high", "high"), ("panel_a_low", "low")):
            for x in r[grp]:
                ok = (x["percentile"] > 50) if want == "high" else (x["percentile"] < 50)
                if not ok:
                    check(f"{sc} 分组自洽", False,
                          f"#{x['order']} 在 {grp} 但百分位 {x['percentile']}")
                    break
            else:
                continue
            break
        else:
            continue
        break
    else:
        check("所有情景的分组都与百分位自洽", True)

    # 边界：选 2 分但人群多数选 1 → 应判为 high
    flipped = None
    for o in ref.items:
        n = ref.norm(o)
        if n["option_pct"][1] > 50 and ref.items[o]["key"] > 0:
            flipped = o
            break
    if flipped:
        r = scene_result(ref.items[flipped]["scene"], {flipped: 2}, ref, {flipped})
        x = next(y for y in r["panel_a"] if y["order"] == flipped)
        check("选 2 分但人群多数选 1 → 判为 high",
              x["direction"] == "high",
              f"#{flipped} 百分位 {x['percentile']}")

    print("\n=== T6 情景划分恰好覆盖 300 题 ===")
    all_orders = [o for s in ref.by_scene for o in ref.by_scene[s]]
    check("情景覆盖 300 题", len(all_orders) == 300, f"{len(all_orders)}")
    check("无重复", len(set(all_orders)) == 300)
    check("情景数 = 8", len(ref.by_scene) == 8, f"{len(ref.by_scene)}")
    check("每题都有 facet", all(ref.items[o]["facet"] in ref.facet_orders
                                for o in all_orders))

    print("\n" + "=" * 60)
    if FAIL:
        print(f"❌ {len(FAIL)} 项未通过：{FAIL}")
        return 1
    print(f"✅ 全部 {7} 组不变量通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
