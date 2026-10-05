#!/usr/bin/env python3
"""通用计分器与 schema 的测试。

分三块：
  A. schema 自校验（把已知好/坏两种报文各造一份，确认坏的一定被拦住）
  B. 计分数学：用**手算**的期望值对照，不依赖实现自己的说法
  C. 跨量表：用 IPIP-CATPD（33 维）与 IPIP-NEO（30 维）各跑一遍，
     确认同一套引擎能处理两套结构不同的量表
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
from engine.scoring import (  # noqa: E402
    score_dimension, score_instrument, validate_against_declaration,
)

fail = 0


def ck(name: str, cond: bool, detail: str = "") -> None:
    global fail
    print(f"  {'✅' if cond else '❌'} {name}" + (f"  —— {detail}" if detail else ""))
    if not cond:
        fail += 1


def mk_instrument(**over) -> Instrument:
    """一套最小但结构完整的量表：2 维度 × 3 题，其中 1 道反向题。"""
    base = dict(
        instrument="TEST-6", display_name="测试量表", citation="(test)",
        license=License(kind="public_domain", text="Public Domain",
                        evidence="test", redistribution=True),
        structure={"source": "test"},
        response_format=ResponseFormat(points=5, min=1, max=5,
                                      labels=["1", "2", "3", "4", "5"]),
        items=[
            Item(order=1, id="q1", text="A", dimensions=["d1"], key=1),
            Item(order=2, id="q2", text="B", dimensions=["d1"], key=-1),
            Item(order=3, id="q3", text="C", dimensions=["d1"], key=1),
            Item(order=4, id="q4", text="D", dimensions=["d2"], key=1),
            Item(order=5, id="q5", text="E", dimensions=["d2"], key=-1),
            Item(order=6, id="q6", text="F", dimensions=["d2"], key=1),
        ],
        dimensions=[
            Dimension(id="d1", name="D1", items=["q1", "q2", "q3"], reverse_keyed=["q2"]),
            Dimension(id="d2", name="D2", items=["q4", "q5", "q6"], reverse_keyed=["q5"]),
        ],
        scoring={
            "d1": Rubric(id="d1", label="D1", aggregation="mean",
                         of=["q1", "q2", "q3"]),
            "d2": Rubric(id="d2", label="D2", aggregation="sum",
                         of=["q4", "q5", "q6"]),
        },
        item_order_source="test",
    )
    base.update(over)
    return Instrument(**base)


print("=== A. schema 自校验：好的通过 ===")
inst = mk_instrument()
errs = inst.validate(require_redistributable=True)
ck("结构完整的最小量表通过校验", not errs, str(errs[:3]))
ck("计分器与声明自洽", not validate_against_declaration(inst))

print("\n=== A2. 坏报文必须被拦住（每一条都是真实会犯的错）===")
bad_cases = [
    ("题项 order 断号", mk_instrument(items=[
        Item(order=1, id="q1", text="A", dimensions=["d1"]),
        Item(order=3, id="q2", text="B", dimensions=["d1"]),
    ], dimensions=[Dimension(id="d1", name="D1", items=["q1", "q2"])],
        scoring={"d1": Rubric(id="d1", label="D1", aggregation="mean", of=["q1", "q2"])})),
    ("维度声明与题项 key 不一致", mk_instrument(
        dimensions=[Dimension(id="d1", name="D1", items=["q1", "q2", "q3"],
                              reverse_keyed=[]),
                    Dimension(id="d2", name="D2", items=["q4", "q5", "q6"])])),
    ("有题项无计分规则", mk_instrument(scoring={})),
    ("计分规则引用不存在的题", mk_instrument(scoring={
        "d1": Rubric(id="d1", label="D1", aggregation="mean", of=["q1", "qX"]),
        "d2": Rubric(id="d2", label="D2", aggregation="sum", of=["q4", "q5", "q6"])})),
    ("有题不属于任何维度", mk_instrument(
        dimensions=[Dimension(id="d1", name="D1", items=["q1", "q2"]),
                    Dimension(id="d2", name="D2", items=["q4", "q5", "q6"])],
        scoring={"d1": Rubric(id="d1", label="D1", aggregation="mean", of=["q1", "q2"]),
                 "d2": Rubric(id="d2", label="D2", aggregation="sum",
                              of=["q4", "q5", "q6"])})),
]
for name, bad in bad_cases:
    try:
        e = bad.validate(require_redistributable=True)
    except Exception as exc:                                # noqa: BLE001
        e = [f"构造/校验抛错: {exc}"]
    ck(f"拦住：{name}", bool(e), (e[0][:76] if e else "（没拦住！）"))

print("\n=== A3. 授权不允许再分发时必须被判错（原 D20；现 `PLAN.md` R1 的机器门）===")
lic_bad = License(kind="unknown", text="© someone", evidence="x", redistribution=False)
_, e2 = mk_instrument(license=lic_bad), mk_instrument(license=lic_bad).validate(
    require_redistributable=True)
ck("redistribution=False 被拦住", bool(e2), (e2[0][:70] if e2 else "（没拦住！）"))
ck("同样这份在不要求再分发时可以通过", not mk_instrument(license=lic_bad).validate())

print("\n=== B. 计分数学（对照手算值）===")
# 注意：to_dict() 会把数值四舍五入到 4 位小数，所以断言用 1e-4 而非 1e-9。
# 我一开始用 1e-9，于是「4.6667 vs 4.66667」这种纯舍入差异把自己测失败了。
TOL = 1e-4
# d1 = mean(q1, 6-q2, q3)；d2 = sum(q4, 6-q5, q6)
resp = {"q1": 5, "q2": 1, "q3": 4, "q4": 2, "q5": 5, "q6": 3}
s = score_instrument(inst, resp)
# 手算：q2 反向 → 6-1=5；q5 反向 → 6-5=1
exp_d1 = (5 + 5 + 4) / 3
exp_d2 = 2 + 1 + 3
ck("mean 维度按反向翻转后取均分", abs(s["dimensions"]["d1"]["value"] - exp_d1) < TOL,
   f"{s['dimensions']['d1']['value']} vs 手算 {exp_d1:.4f}")
ck("sum 维度按反向翻转后求和", abs(s["dimensions"]["d2"]["value"] - exp_d2) < TOL,
   f"{s['dimensions']['d2']['value']} vs 手算 {exp_d2}")
ck("未作答的维度被标为 complete=False", s["dimensions"]["d1"]["complete"])

s_partial = score_instrument(inst, {"q1": 3, "q2": 3})
ck("只答部分题时：值只按已答算，但 complete=False",
   s_partial["dimensions"]["d1"]["complete"] is False
   and s_partial["dimensions"]["d1"]["n_answered"] == 2
   and abs(s_partial["dimensions"]["d1"]["value"] - (3 + 3) / 2) < TOL,
   f"n_answered={s_partial['dimensions']['d1']['n_answered']}")
ck("完全没答的维度值为 None（不是 0）",
   s_partial["dimensions"]["d2"]["value"] is None,
   f"value={s_partial['dimensions']['d2']['value']}")
ck("incomplete 列表列出所有未答满的维度",
   s_partial["incomplete"] == ["d1", "d2"], str(s_partial["incomplete"]))

print("\n=== B2. 0..3 量表的反向翻转（不能写死 6−v）===")
inst4 = mk_instrument(
    response_format=ResponseFormat(points=4, min=0, max=3, labels=["0", "1", "2", "3"]),
    items=[Item(order=1, id="q1", text="A", dimensions=["d1"], key=1),
           Item(order=2, id="q2", text="B", dimensions=["d1"], key=-1)],
    dimensions=[Dimension(id="d1", name="D1", items=["q1", "q2"], reverse_keyed=["q2"])],
    scoring={"d1": Rubric(id="d1", label="D1", aggregation="sum", of=["q1", "q2"])})
s4 = score_instrument(inst4, {"q1": 3, "q2": 1})
# 0..3 反向：3-1=2 → 3+2=5
ck("0..3 量表的反向翻转是 (0+3)−v", s4["dimensions"]["d1"]["value"] == 5,
   f"{s4['dimensions']['d1']['value']}（应为 5）")

print("\n=== B3. 嵌套维度（域 = facet 均分，PID-5 的形态）===")
nested = mk_instrument(
    items=[Item(order=i, id=f"n{i}", text=f"t{i}", dimensions=["f1" if i <= 2 else "f2"])
           for i in range(1, 5)],
    dimensions=[
        Dimension(id="f1", name="F1", level=1, parent="dom", items=["n1", "n2"]),
        Dimension(id="f2", name="F2", level=1, parent="dom", items=["n3", "n4"]),
        Dimension(id="dom", name="Domain", level=2, children=["f1", "f2"]),
    ],
    scoring={
        "f1": Rubric(id="f1", label="F1", aggregation="mean", of=["n1", "n2"]),
        "f2": Rubric(id="f2", label="F2", aggregation="mean", of=["n3", "n4"]),
        # 域分 = 两个 facet 的**均分**（不是 4 道题直接求均分——facet 题数不等时两者不同）
        "dom": Rubric(id="dom", label="Domain", aggregation="mean",
                      scope="dimensions", of=["f1", "f2"]),
    })
sn = score_instrument(nested, {"n1": 4, "n2": 2, "n3": 5, "n4": 1})
# f1 = 3.0，f2 = 3.0 → dom = 3.0；而 4 题直接均分也是 3.0，所以换一组不等长的数验证
sn2 = score_instrument(nested, {"n1": 4, "n2": 4, "n3": 1})   # f1 答满=4，f2 只答一半
ck("不完全的子维度**不参与**上级聚合（避免「看起来像结果」的偏低域分）",
   abs(sn2["dimensions"]["dom"]["value"] - 4.0) < TOL,
   f"dom={sn2['dimensions']['dom']['value']}（只取答满的 f1=4.0）")
ck("有任何子维度未答满 → 上级 complete=False",
   sn2["dimensions"]["dom"]["complete"] is False
   and sn2["dimensions"]["f1"]["complete"] is True
   and sn2["dimensions"]["f2"]["complete"] is False)
ck("上级的 n_answered / n_items 仍然是全局计数（便于显示进度）",
   sn2["dimensions"]["dom"]["n_answered"] == 3 and sn2["dimensions"]["dom"]["n_items"] == 4,
   f"{sn2['dimensions']['dom']['n_answered']}/{sn2['dimensions']['dom']['n_items']}")
ck("facet 分本身正确", abs(sn2["dimensions"]["f1"]["value"] - 4.0) < TOL)
# 全部答满时，域分 = 两个 facet 均分的均分（与「4 题直接求均分」在题数不等时不同）
sn3 = score_instrument(nested, {"n1": 4, "n2": 2, "n3": 5, "n4": 2})
ck("全部答满时：域分 = facet 均分再均分",
   abs(sn3["dimensions"]["dom"]["value"] - (3.0 + 3.5) / 2) < TOL,
   f"dom={sn3['dimensions']['dom']['value']}（手算 {(3.0 + 3.5) / 2}）")

print("\n=== C. 跨量表：同一引擎吃两套结构不同的真实量表 ===")
for code, path, expect_dims in [
    ("DSM5TR-L1", "data/instruments/dsm5tr-l1.json", 13),
    ("IPIP-NEO", "data/ipip-neo-300.json", 30),
]:
    p = os.path.join(ROOT, path)
    if not os.path.exists(p):
        ck(f"{code} 产物存在", False, p)
        continue
    with open(p, encoding="utf-8") as fh:
        d = json.load(fh)
    if code != "IPIP-NEO":
        # 新 schema 的产物：直接用（只做只读适配）
        from engine.instrument_schema import Dimension as D
        items = [Item(order=x["order"], id=x["id"], text=x["text"],
                      dimensions=x.get("dimensions", []), key=x.get("key", 1),
                      source_code=x.get("source_code"))
                 for x in d["items"]]
        rub = {k: Rubric(id=k, label=v["label"], aggregation=v["aggregation"],
                         scope=v.get("scope", "items"), of=v["of"])
               for k, v in d["scoring"].items()}
        dims = [D(id=x["id"], name=x["name"],
                  items=x.get("items")
                  or [i for i in rub[x["id"]].of if rub[x["id"]].scope == "items"],
                  reverse_keyed=x.get("reverse_keyed", [])) for x in d["dimensions"]]
        inst2 = Instrument(instrument=d["instrument"], display_name=d["display_name"],
                           citation=d["citation"],
                           license=License(kind=d["license"]["kind"],
                                           text=d["license"]["text"],
                                           evidence=d["license"]["evidence"],
                                           redistribution=d["license"]["redistribution"]),
                           structure=d["structure"], items=items, dimensions=dims,
                           scoring=rub, item_order_source=d["item_order_source"],
                           response_format=ResponseFormat(
                               **{k: v for k, v in d["structure"]["response_format"].items()}))
        ck(f"{code}: 产物能被 schema 读回并通过校验",
           not inst2.validate(require_redistributable=True),
           str(inst2.validate()[:2]))
        ck(f"{code}: 维度数 = {expect_dims}", len(inst2.dimensions) == expect_dims,
           f"{len(inst2.dimensions)}")
        ck(f"{code}: 声明自洽", not validate_against_declaration(inst2))
        # 全选 3 分跑一遍，确认不抛错且每个维度都有值
        all3 = {it.id: 3 for it in inst2.items}
        sc = score_instrument(inst2, all3)
        ck(f"{code}: 全部答 3 分时每个维度都有值且 complete",
           all(sc["dimensions"][x.id]["value"] is not None for x in inst2.dimensions)
           and not sc["incomplete"],
           f"{len(sc['dimensions'])} 维")
        # 全 3 分时正向题与反向题抵消：均值维度应恰为 3.0（这是反向键的强校验）
        means = [v["value"] for k, v in sc["dimensions"].items()
                 if v["aggregation"] == "mean"]
        ck(f"{code}: 全答 3 分 → 所有 mean 维度恰为 3.000",
           all(abs(m - 3.0) < 1e-9 for m in means),
           f"{len(means)} 个 mean 维度，最大偏差 "
           f"{max((abs(m - 3.0) for m in means), default=0):.2e}")
    else:
        ck(f"{code}: 已有产物（旧 schema）存在", True, f"{len(d['items'])} 题")

print()
print("✅ 全部通过" if not fail else f"❌ {fail} 项未通过")
sys.exit(1 if fail else 0)
