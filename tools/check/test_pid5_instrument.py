#!/usr/bin/env python3
"""验证 PID-5 量表包能端到端计分。

检查：
  · 读回量表包 → schema 校验通过、声明自洽
  · 全答 0 / 全答 3 → facet 与域分符合数学期望（含 16 道翻转题的效应）
  · 不完整作答 → 只按已答算、且标 complete=False（不静默充当完整分）
  · 域分 = 三个 facet 均分的均分（与「域下所有题直接求均分」可能不同）
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
sys.path.insert(0, ROOT)

from engine.instrument_schema import (  # noqa: E402
    Dimension, Instrument, Item, License, ResponseFormat, Rubric,
)
from engine.scoring import score_instrument, validate_against_declaration  # noqa: E402

fail = 0


def ck(name: str, cond: bool, detail: str = "") -> None:
    global fail
    print(f"  {'✅' if cond else '❌'} {name}" + (f"  —— {detail}" if detail else ""))
    if not cond:
        fail += 1


def load_instrument(path: str) -> Instrument:
    with open(path, encoding="utf-8") as fh:
        d = json.load(fh)
    return Instrument(
        instrument=d["instrument"], display_name=d["display_name"],
        citation=d["citation"],
        license=License(kind=d["license"]["kind"], holder=d["license"]["holder"],
                        text=d["license"]["text"], url=d["license"]["url"],
                        evidence=d["license"]["evidence"],
                        redistribution=d["license"]["redistribution"],
                        notes=d["license"].get("notes", "")),
        structure=d["structure"],
        items=[Item(order=x["order"], id=x["id"], text=x["text"],
                    dimensions=x.get("dimensions", []), key=x.get("key", 1),
                    source_code=x.get("source_code"), text_source=x.get("text_source"))
               for x in d["items"]],
        dimensions=[Dimension(id=x["id"], name=x["name"], level=x.get("level", 1),
                              parent=x.get("parent"),
                              children=x.get("children", []),
                              items=x.get("items", []),
                              reverse_keyed=x.get("reverse_keyed", []))
                    for x in d["dimensions"]],
        scoring={k: Rubric(id=k, label=v["label"], aggregation=v["aggregation"],
                           scope=v.get("scope", "items"), of=v["of"],
                           notes=v.get("notes", ""))
                 for k, v in d["scoring"].items()},
        item_order_source=d["item_order_source"],
        response_format=ResponseFormat(**d["structure"]["response_format"]),
        version=d["version"], provenance=d.get("provenance", {}))


def main() -> int:
    p = os.path.join(ROOT, "data", "instruments", "pid-5.json")
    inst = load_instrument(p)
    print(f"读回量表包：{inst.instrument}，{len(inst.items)} 题，"
          f"{len(inst.dimensions)} 维度，{len(inst.scoring)} 计分规则")

    ck("schema 校验通过（含再分发门）", not inst.validate(require_redistributable=True))
    ck("计分规则与维度声明自洽", not validate_against_declaration(inst))
    ck("维度数 = 25 facet + 5 域", len(inst.dimensions) == 30,
       str(len(inst.dimensions)))
    ck("反向题 = 16", sum(1 for x in inst.items if x.key == -1) == 16,
       str(sum(1 for x in inst.items if x.key == -1)))
    ck("每道题恰好属于一个 facet",
       all(len(x.dimensions) == 1 for x in inst.items if x.dimensions))

    # 全答 0：翻转题翻成 3。
    # ⚠️ 期望值必须以**手册 facet 表的 R 标记（16 题）**为准，不是 Step 1 正文清单（14 题）。
    #    手册两处原文互相矛盾，2026-10-04 用数据裁决：第 7、30 题**确实该翻转**
    #    （不翻转时与同面向相关为 −0.6 / −0.5，翻转后转正；两份独立样本一致，
    #     对照组无此效应）。详见 data/pid5-reverse-keys.json 的 evidence 字段。
    #    本测试原先按 Step 1 清单写，还断言过「第 30 题不翻转」——那条断言已被数据否掉。
    # ⚠️ 容差用 1e-4 而不是 1e-6：``to_dict()`` 会把数值四舍五入到 4 位小数，
    #    18/14 = 1.2857… 变成 1.2857，与精确值差 2.9e-5。用 1e-6 会把自己
    #    的舍入当成错误（我在 tools/check/test_scoring.py 里就犯过同样的错）。
    TOL = 1e-4
    s0 = score_instrument(inst, {x.id: 0 for x in inst.items})
    ck("全答 0 时所有维度都有值且 complete",
       not s0["incomplete"] and all(v["value"] is not None
                                    for v in s0["dimensions"].values()))
    anhedonia = s0["dimensions"]["pid5_anhedonia"]
    # Anhedonia 8 题，翻转的是 30、155 → 2 个 3 + 6 个 0 = 6 → 0.75
    ck("Anhedonia（8 题，2 道翻转）全答 0 → 均分 6/8",
       abs(anhedonia["value"] - 6 / 8) < TOL, str(anhedonia["value"]))
    rt = s0["dimensions"]["pid5_risk_taking"]
    # Risk Taking 14 题，翻转的是 7、35、87、98、164、215 → 6 个 3 = 18 → 18/14
    ck("Risk Taking（14 题，6 道翻转）全答 0 → 均分 18/14",
       abs(rt["value"] - 18 / 14) < TOL, str(rt["value"]))

    # 全答 3：翻转题变 0
    s3 = score_instrument(inst, {x.id: 3 for x in inst.items})
    ck("Anhedonia 全答 3 → 均分 (6*3+2*0)/8 = 2.25",
       abs(s3["dimensions"]["pid5_anhedonia"]["value"] - 18 / 8) < TOL,
       str(s3["dimensions"]["pid5_anhedonia"]["value"]))
    # 第 30 题：手册 Step 1 未列、但 facet 表标了 R；数据裁决为**应翻转**
    ck("表格标 R 且数据支持的题要翻转（如第 30 题）",
       next(x for x in inst.items if x.id == "pid5_030").key == -1)

    # 域分 = 三个 facet 均分的均分
    neg = s0["dimensions"]["pid5_negative_affect"]
    parts = [s0["dimensions"]["pid5_emotional_lability"]["value"],
             s0["dimensions"]["pid5_anxiousness"]["value"],
             s0["dimensions"]["pid5_separation_insecurity"]["value"]]
    ck("域分 = 三个 facet 均分的均分",
       abs(neg["value"] - sum(parts) / 3) < 1e-6,
       f"域 {neg['value']}，facet 均分 {sum(parts) / 3:.4f}")
    ck("域 complete 反映子维度完整性", neg["complete"] is True)

    # 不完整作答：只答 Anhedonia 的前 3 题
    partial = {inst.items[i].id: 2 for i in range(3)}
    sp = score_instrument(inst, partial)
    ck("不完整作答：Anhedonia 标 complete=False",
       sp["dimensions"]["pid5_anhedonia"]["complete"] is False)
    ck("不完整作答：域也标 complete=False（不完全的子维度不参与域聚合）",
       sp["dimensions"]["pid5_negative_affect"]["complete"] is False)
    ck("完全没答的维度值为 None（不是 0）",
       sp["dimensions"]["pid5_depressivity"]["value"] is None)

    print()
    print("✅ 全部通过" if not fail else f"❌ {fail} 项未通过")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
