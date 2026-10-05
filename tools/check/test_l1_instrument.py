#!/usr/bin/env python3
"""DSM-5-TR Level 1 量表包的端到端测试。

重点验证 **max 聚合**：Level 1 的域分是「域内题目最高分」，不是求和也不是均分。
这是最容易写错的一处（写成 sum 时，2 题域的最高分 3 会变成 5，看起来还挺像分数）。
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from test_pid5_instrument import load_instrument  # noqa: E402
from engine.scoring import score_instrument  # noqa: E402

fail = 0


def ck(name: str, cond: bool, detail: str = "") -> None:
    global fail
    print(f"  {'✅' if cond else '❌'} {name}" + (f"  —— {detail}" if detail else ""))
    if not cond:
        fail += 1


def main() -> int:
    inst = load_instrument(os.path.join(ROOT, "data", "instruments", "dsm5tr-l1.json"))
    print(f"读回：{inst.instrument}，{len(inst.items)} 题，{len(inst.dimensions)} 域")

    ck("schema 校验通过（含再分发门）", not inst.validate(require_redistributable=True))
    ck("题数 = 23", len(inst.items) == 23, str(len(inst.items)))
    ck("域数 = 13", len(inst.dimensions) == 13, str(len(inst.dimensions)))
    ck("作答区间 0..4",
       inst.response_format.min == 0 and inst.response_format.max == 4)
    ck("授权注明「不得修改」",
       "不得修改" in inst.license.notes and "may not be modified" in inst.license.notes)
    ck("授权允许再分发", inst.license.redistribution is True)

    # 全部答 0 → 所有域 0
    s0 = score_instrument(inst, {x.id: 0 for x in inst.items})
    ck("全答 0 → 所有域 = 0",
       all(v["value"] == 0 for v in s0["dimensions"].values())
       and not s0["incomplete"])

    # 全部答 4 → 所有域 4
    s4 = score_instrument(inst, {x.id: 4 for x in inst.items})
    ck("全答 4 → 所有域 = 4",
       all(v["value"] == 4 for v in s4["dimensions"].values()))

    # max 聚合的关键判别：2 题域里一题 1、一题 4 → 域分应为 4（sum 会得 5）
    two_item = next(d for d in inst.dimensions if len(d.items) == 2)
    resp = {x.id: 0 for x in inst.items}
    resp[two_item.items[0]] = 1
    resp[two_item.items[1]] = 4
    s = score_instrument(inst, resp)
    v = s["dimensions"][two_item.id]["value"]
    ck(f"2 题域（{two_item.name}）答 1 与 4 → 域分 = 4（max，不是 sum 的 5）",
       v == 4, f"得到 {v}")

    # 3 题域同样验证
    three = next(d for d in inst.dimensions if len(d.items) == 3)
    resp2 = {x.id: 1 for x in inst.items}
    resp2[three.items[-1]] = 3
    s2 = score_instrument(inst, resp2)
    v2 = s2["dimensions"][three.id]["value"]
    ck(f"3 题域（{three.name}）一题 3、其余 1 → 域分 = 3",
       v2 == 3, f"得到 {v2}")

    # 未作答 → 该域 complete=False，值为已答部分的最高分
    partial = {inst.items[0].id: 2}
    sp = score_instrument(inst, partial)
    first_dom = next(d for d in inst.dimensions if inst.items[0].id in d.items)
    ck("部分作答 → 该域 complete=False",
       sp["dimensions"][first_dom.id]["complete"] is False)
    ck("完全没答的域值为 None（不是 0）",
       sp["dimensions"]["l1_anger"]["value"] is None)

    print()
    print("✅ 全部通过" if not fail else f"❌ {fail} 项未通过")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
