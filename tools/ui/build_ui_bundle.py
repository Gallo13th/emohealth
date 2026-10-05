#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为界面打包自包含数据。

**关键优化**：不必嵌入全部 30×1023 个子集的精度表。用户实际能走到的状态远少于此：

  情景模式  只能整块完成情景 → 2^8 = 256 种状态
  经典模式  只能按序推进     → 301 种前缀

两者合起来只有 30×(256+301) ≈ 16,700 个值，可完整嵌入，**无需在浏览器里近似**。

输出：`ui/emohealth-data.js`（挂到 window.EMOHEALTH，供自包含 HTML 直接引用）
"""
from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
sys.path.insert(0, ROOT)
OUT = os.path.join(ROOT, "ui/emohealth-data.js")

CANON = os.path.join(ROOT, "data/ipip-neo-300.json")
TAX = os.path.join(ROOT, "data/scene-taxonomy.json")
PREC = os.path.join(ROOT, "data/scene-precision.json")
NORMS = os.path.join(ROOT, "data/item-norms.json")
UK = os.path.join(ROOT, "data/uk-norms.json")

DOMAINS = ["Neuroticism", "Extraversion", "Openness",
           "Agreeableness", "Conscientiousness"]


def r3(x):
    return None if x is None else round(x, 3)


def main() -> int:
    canon = json.load(open(CANON, encoding="utf-8"))
    tax = json.load(open(TAX, encoding="utf-8"))
    prec = json.load(open(PREC, encoding="utf-8"))["precision_table"]
    norms = json.load(open(NORMS, encoding="utf-8"))
    uk = json.load(open(UK, encoding="utf-8"))

    scenes = sorted({v["scene"] for v in tax["items"].values()},
                    key=lambda s: -sum(1 for v in tax["items"].values() if v["scene"] == s))
    s_idx = {s: i for i, s in enumerate(scenes)}

    # facet 顺序：按维度分组，便于界面呈现（域信息在 facet_definitions）
    from content.facet_definitions import FACETS, NORM_COLUMN  # noqa: E402
    # domain 字段是小写英文；界面按「神经质→外向性→开放性→宜人性→尽责性」呈现
    DOM_KEY = ["neuroticism", "extraversion", "openness",
               "agreeableness", "conscientiousness"]
    f_order = []
    for dk in DOM_KEY:
        for f, v in FACETS.items():
            if v["domain"] == dk:
                f_order.append(f)
    assert len(f_order) == 30, f"facet 数应为 30，得到 {len(f_order)}"
    f_idx = {f: i for i, f in enumerate(f_order)}

    by_order = {i["order"]: i for i in canon["items"]}

    # ── 题目（紧凑数组：[order, facetIdx, sceneIdx, key, zh, en]）
    items = []
    for o in sorted(by_order):
        it = by_order[o]
        items.append([o, f_idx[it["facet"]], s_idx[tax["items"][str(o)]["scene"]],
                      it["key"], tax["items"][str(o)]["text_zh"], it["text"]])

    # ── 每题 5 个选项的百分位（对齐到面向方向）
    opt = [[norms["items"][str(o)]["option_pct"][i] for i in range(5)]
           for o in sorted(by_order)]

    # ── 情景模式的精度：每个 facet × 256 个情景子集
    scene_of = {o: s_idx[tax["items"][str(o)]["scene"]] for o in by_order}
    facet_orders = {f: [] for f in f_order}
    for o in sorted(by_order):
        facet_orders[by_order[o]["facet"]].append(o)

    scene_prec = {}
    for f in f_order:
        orders = facet_orders[f]
        row = []
        for mask in range(256):
            # 该情景子集下，这个 facet 答了哪些题
            sel = [o for o in orders if mask >> scene_of[o] & 1]
            if not sel:
                row.append(None)
                continue
            sub = sum(1 << orders.index(o) for o in sel)
            row.append(r3(prec[f].get(str(sub))))
        scene_prec[f_idx[f]] = row

    # ── 经典模式的精度：每个 facet × 前缀长度 0..300
    classic_prec = {}
    for f in f_order:
        orders = facet_orders[f]
        row = []
        for n in range(301):
            sel = [o for o in orders if o <= n]
            if not sel:
                row.append(None)
                continue
            sub = sum(1 << orders.index(o) for o in sel)
            row.append(r3(prec[f].get(str(sub))))
        classic_prec[f_idx[f]] = row

    # ── 完整 1023 子集表（index = mask-1；mask 为 0 表示未答，用 null）
    # 有了它，情景中途退出、跨情景零散作答都能正确算精度，不必限定「整块完成」
    full_prec = {}
    for f in f_order:
        row = [None] * 1024
        for k, v in prec[f].items():
            row[int(k)] = r3(v)
        full_prec[f_idx[f]] = row

    # ── facet 档案（用户可见的那部分）
    # 这些内容本来就有，只是先前没上界面。主要框架里它们是「出结果」的主体。
    recs = []
    scaf: dict[str, dict] = {}
    for f in f_order:
        r = json.load(open(os.path.join(ROOT, "content/facets", f"{f}.record.json"),
                           encoding="utf-8"))
        c = r["construct"]
        recs.append({
            "zh": r["identity"]["facet_name_zh"],
            "domain": r["identity"]["domain_zh"],
            "alpha": r["reliability"]["cronbach_alpha"],
            # definition 是对象（text/basis/provenance），不是字符串——
            # 直接塞进界面会渲染成 [object Object]（实测踩过）。
            # provenance 必须一并带上：PLAN §3.7 要求产品对自己的内容做溯源标注。
            "definition": (c.get("definition") or {}).get("text"),
            "definition_basis": (c.get("definition") or {}).get("basis"),
            "definition_provenance": (c.get("definition") or {}).get("provenance"),
            "does_not_measure": c.get("does_not_measure", []),
            # boundaries 是「与相邻面向的区别」列表，是用户最容易用错的边界
            "boundaries": [{"against": b.get("against_facet_zh") or b.get("against_facet"),
                            "distinction": b.get("distinction")}
                           for b in (c.get("boundaries") or [])],

            "caveats": (r.get("evidence", {}) or {}).get("interpretation_caveats", []),
            "critiques": (r.get("evidence", {}) or {}).get("known_critiques", []),
        })
        # 逐题脚手架——300 题逐题写的作者级内容，主要框架的核心资产
        for it in r["items"]:
            sc = it.get("scaffolding") or {}
            if sc.get("status") == "PENDING" or not sc.get("asks"):
                continue
            scaf[str(it["administration_order"])] = {
                "asks": sc["asks"],
                "term": sc["key_term"]["term"],
                "sense": sc["key_term"]["sense_here"],
                "not_this": sc["key_term"]["not_this"],
                "mis": [[m["misreading"], m["correction"]]
                        for m in sc.get("common_misreadings", [])],
                "counts": sc.get("counts_as", []),
                "notcount": sc.get("does_not_count_as", []),
                "edge": sc.get("edge_cases"),
                "loc": sc.get("localization_note"),
            }

    # ── 常模带（用于经典模式的分数落带）
    bands = {}
    for age, tab in uk["levels"]["facets"].items():
        for col, rng in tab.items():
            bands.setdefault(col, {})[age] = rng
    # 常模表的键是「首字母大写 + 空格」形式（如 Anxiety、"Artistic Interests"），
    # 而 NORM_COLUMN 只覆盖了少数特例。必须像 build_all_facets.py 那样做
    # 大小写/空格不敏感的回退，否则界面上永远查不到分带（实测踩过这个坑）。
    def _norm(x: str) -> str:
        return re.sub(r"[\s_\-]+", "", x.lower())

    sample_age = next(iter(bands and uk["levels"]["facets"]))
    tab_keys = list(uk["levels"]["facets"][sample_age].keys())
    col_of = {}
    for f in f_order:
        want = NORM_COLUMN.get(f, f)
        hit = want if want in tab_keys else next(
            (k for k in tab_keys if _norm(k) == _norm(want)), None)
        if hit is None:
            raise SystemExit(f"❌ {f} 在常模表里找不到对应列（want={want!r}）")
        col_of[f_idx[f]] = hit

    bundle = {
        "meta": {
            "built_from": "IPIP-NEO-300 + Johnson(2005) N=20,993 + UK 常模",
            "n_items": len(items), "n_facets": len(f_order), "n_scenes": len(scenes),
            "gating_rule": "k≤2 一律不展示；否则按实际题集查精度表",
        },
        "domains": [FACETS[f_order[i * 6]]["domain_zh"] for i in range(5)],
        "facets": f_order,
        "recs": recs,
        "scenes": scenes,
        "sceneNames": [tax["scene_names_zh"][s] for s in scenes],
        "items": items,
        "scaf": scaf,
        "optionPct": opt,
        "scenePrec": scene_prec,
        "classicPrec": classic_prec,
        "fullPrec": full_prec,
        "normBands": bands,   # 键是常模表的列名；normCol 已解析成同名
        "normCol": col_of,
        "conversion": uk.get("conversion") or [],
        "sceneOf": scene_of,
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("window.EMOHEALTH = ")
        json.dump(bundle, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write(";\n")

    size = os.path.getsize(OUT)
    print(f"数据包 → {os.path.relpath(OUT, ROOT)}  ({size/1024:.0f} KB)")
    print(f"  题目 {len(items)}｜facet {len(f_order)}｜情景 {len(scenes)}")
    print(f"  情景精度表 {len(scene_prec)}×256｜经典精度表 {len(classic_prec)}×301"
          f"｜完整子集表 {len(full_prec)}×1024")
    print(f"  逐题脚手架 {len(scaf)} 题"
          f"（本地化说明 {sum(1 for v in scaf.values() if v['loc'])} 条）")
    print(f"  维度：{'、'.join(DOMAINS)}")
    print(f"  情景：{'、'.join(tax['scene_names_zh'][s] for s in scenes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
