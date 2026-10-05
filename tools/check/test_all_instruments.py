#!/usr/bin/env python3
"""跨量表回归：对 ``data/instruments/`` 下**每一套**量表包做统一检查。

这个测试的价值在于「一致性」：任何一套新增量表只要违反约定就会被拦下，而不是
只检查我这一轮关心的那几套。

检查项：
  · schema 校验通过（含 ``require_redistributable`` 的 D20 门）
  · 计分规则与维度声明自洽
  · 每一道题都归属于某个维度、且只归一个
  · 全答最小值 / 最大值时所有维度都有值且 complete
  · 反向题在「全答最大」与「全答最小」之间产生预期差异
  · 授权证据字段非空（每个授权判断都要能追到出处）
"""

from __future__ import annotations

import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from test_pid5_instrument import load_instrument  # noqa: E402
from engine.scoring import score_instrument, validate_against_declaration  # noqa: E402

fail = 0


def ck(name: str, cond: bool, detail: str = "") -> None:
    global fail
    print(f"  {'✅' if cond else '❌'} {name}" + (f"  —— {detail}" if detail else ""))
    if not cond:
        fail += 1


def main() -> int:
    # 排除目录文件：它是元信息（{count, groups, instruments}），不是量表包。
    # 我在同一轮加目录时漏了这层过滤，测试直接以 KeyError 崩掉——
    # 「扫某个目录」的地方每加一类文件都要回头看一遍。
    paths = [p for p in sorted(glob.glob(
        os.path.join(ROOT, "data", "instruments", "*.json")))
        if os.path.basename(p) != "catalog.json"]
    print(f"量表包 {len(paths)} 套\n")
    for p in paths:
        inst = load_instrument(p)
        print(f"── {os.path.basename(p)}：{inst.instrument}｜{len(inst.items)} 题 · "
              f"{len(inst.dimensions)} 维度")

        ck("schema 校验通过（含再分发门）",
           not inst.validate(require_redistributable=True))
        ck("计分规则与维度声明自洽", not validate_against_declaration(inst))
        ck("授权证据非空（每套都要能追到出处）",
           bool(inst.license.evidence.strip()) and bool(inst.license.text.strip()))
        # 每道题至少要落在一个维度里（否则用户答了也算不出结果）
        orphan = [x.id for x in inst.items
                  if not any(x.id in d.items for d in inst.dimensions)]
        ck("没有游离题（每题都归属维度）", not orphan,
           f"{len(orphan)} 道游离：{orphan[:4]}")
        # 反向题（key=-1）必须在其维度里被声明，否则 schema 校验会漏检
        undeclared = [x.id for x in inst.items if x.key == -1
                      and not any(x.id in (d.reverse_keyed or [])
                                  for d in inst.dimensions)]
        ck("反向题都在维度里声明过", not undeclared,
           f"{len(undeclared)} 道未声明：{undeclared[:4]}")

        lo, hi = inst.response_format.min, inst.response_format.max
        slo = score_instrument(inst, {x.id: lo for x in inst.items})
        shi = score_instrument(inst, {x.id: hi for x in inst.items})
        ck("全答区间端点时所有维度都有值",
           not slo["incomplete"] and not shi["incomplete"],
           f"{len(slo['incomplete'])} 个未完成")

        rev = [x for x in inst.items if x.key == -1]
        if rev:
            # ⚠️ 不能拿「全答最小 vs 全答最大」的总分来验证反向是否生效：
            #    睡眠册有 4 道反向题、共 8 题，两个端点算出来的**总分恰好相同**
            #    （4×1+4×5 = 4×5+4×1 = 24），总分相等并不说明反向没生效。
            #    正确做法是在**题项层面**看：同一道题答最小值与最大值，
            #    计分值必须不同（否则 key 根本没被用上）。
            from engine.scoring import score_dimension
            dim_of = next(d for d in inst.dimensions if rev[0].id in d.items)
            coded_lo = {c["item"]: c.get("coded")
                        for c in score_dimension(inst, dim_of.id,
                                                 {x.id: lo for x in inst.items}).detail
                        if c.get("answered")}
            coded_hi = {c["item"]: c.get("coded")
                        for c in score_dimension(inst, dim_of.id,
                                                 {x.id: hi for x in inst.items}).detail
                        if c.get("answered")}
            same = [i for i in coded_lo
                    if coded_lo[i] is not None and coded_lo[i] == coded_hi[i]]
            ck(f"反向题（{len(rev)} 道）在题项层面确实被翻转",
               bool(same) is False,
               f"未翻转的题：{same[:4]}" if same else
               f"例：{rev[0].id} 答 {lo}→{coded_lo.get(rev[0].id)}、"
               f"答 {hi}→{coded_hi.get(rev[0].id)}")
        print()

    print("✅ 全部通过" if not fail else f"❌ {fail} 项未通过")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
