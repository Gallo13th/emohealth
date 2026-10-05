#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""情景模式演示：模拟一个用户分几次完成情景，打印每一步该看到什么。

演示三件事：
  1. 答题过程中**只有完成度，没有分值**（D30）
  2. 情景答完后给出**题目级位置比较**（面板 A）与**与自己的基线对比**（面板 B）
  3. 面向解锁按**实际题集**查精度表——可以看到被情景门控的面向（如 cooperation）
     在做到「冲突与竞争」之前一直不解锁

用法：python3 tools/legacy/demo_scene.py [--seed 7]
"""
from __future__ import annotations

import argparse
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
sys.path.insert(0, ROOT)

from engine.scene import (  # noqa: E402
    SceneReference, progress, render_progress, render_scene_result,
    render_unlock, scene_result, unlock_status,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--effort", type=float, default=0.85,
                    help="模拟作答的「努力程度」，用于观察质量门与精度的反应")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    ref = SceneReference()
    scenes = ref.scenes()

    print("=" * 74)
    print(f"情景模式演示 —— 共 {len(scenes)} 个情景，{len(ref.items)} 题")
    print("=" * 74)
    print("\n情景清单（按题数）：")
    for s in scenes:
        o = ref.by_scene[s]
        fc = len({ref.items[x]["facet"] for x in o})
        print(f"  {ref.scene_name_zh(s):<18} {len(o):>4} 题   覆盖 {fc:>2} 个面向")

    # 模拟：一个中等偏高、略有情景差异的作答者
    responses: dict[int, int] = {}
    answered: set[int] = set()
    # 每个人格面向一个「基线倾向」，让作答内部相关
    facet_base = {f: rng.gauss(0, 0.7) for f in ref.facet_orders}
    # 每个情景一个「情境偏移」，用于观察面板 B
    scene_shift = {s: rng.gauss(0, 0.35) for s in scenes}

    def answer(o: int) -> int:
        f = ref.items[o]["facet"]
        s = ref.items[o]["scene"]
        z = facet_base[f] + scene_shift[s] + rng.gauss(0, 0.9)
        v = 3 + z * args.effort
        return max(1, min(5, int(round(v))))

    # ── 按题数从大到小完成情景
    for i, s in enumerate(scenes):
        for o in ref.by_scene[s]:
            responses[o] = answer(o)
            answered.add(o)

        print("\n" + "─" * 74)
        print(f"▶ 完成第 {i+1} 个情景：{ref.scene_name_zh(s)}")
        print("─" * 74)

        # 1) 答题过程中的进度（只有完成度）
        print()
        print(render_progress(progress(ref, answered)))

        # 2) 情景结果（答完才给）
        print()
        print(render_scene_result(scene_result(s, responses, ref, answered), full=False))

        # 3) 解锁状态
        print()
        print(render_unlock(unlock_status(ref, answered)))

        if i >= 3 and i < len(scenes) - 1:
            print("\n（演示至此已足够；后续情景省略，直接跳到全卷完成）")
            break

    # ── 补齐全卷
    for s in scenes:
        for o in ref.by_scene[s]:
            if o not in responses:
                responses[o] = answer(o)
                answered.add(o)

    print("\n" + "=" * 74)
    print("全卷完成（300 题）")
    print("=" * 74)
    print()
    print(render_unlock(unlock_status(ref, answered), only_showable=False))
    print()
    print(render_scene_result(scene_result(scenes[0], responses, ref, answered)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
