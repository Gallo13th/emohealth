#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""量表档案校验器 —— 实现 instrument-record.schema.md §10 的 V1–V7 规则。

Phase 1 的教训：**肉眼不可见的错误会污染计分。**
切片初稿把 `ipip_neo_031` 当成「第 31 题的 id」，而实际 id 是 `ipip_neo_002`
（`.osd` 的 id 反映分组顺序，与施测顺序无关）。10 个 id 全错，肉眼看不出，
被校验器捕获。本工具就是那次教训的固化。

用法：
  python3 tools/check/validate_records.py
  python3 tools/check/validate_records.py --record content/facets/anxiety.record.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
CANON = os.path.join(ROOT, "data/ipip-neo-300.json")
NORMS = os.path.join(ROOT, "data/uk-norms.json")
BANDS = ["Very High", "High", "Average", "Low", "Very Low"]

errors: list[str] = []
warns: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warns.append(msg)


# ---------------------------------------------------------------- V2/V3：整卷结构
def check_canonical() -> dict:
    canon = json.load(open(CANON, encoding="utf-8"))
    items = canon["items"]

    if len(items) != 300:
        err(f"V2 题目数 {len(items)} != 300")

    facets: dict[str, list[dict]] = {}
    for it in items:
        facets.setdefault(it["facet"], []).append(it)

    if len(facets) != 30:
        err(f"V2 facet 数 {len(facets)} != 30")
    bad = {f: len(v) for f, v in facets.items() if len(v) != 10}
    if bad:
        err(f"V2 facet 题数异常：{bad}")

    # V1：id ↔ order ↔ key 三者一致
    for it in items:
        facet_items = sorted(facets[it["facet"]], key=lambda x: x["order"])
        idx = facet_items.index(it)
        # id 必须唯一
        if sum(1 for x in items if x["id"] == it["id"]) != 1:
            err(f"V1 id 重复：{it['id']}")
        if not isinstance(it["key"], int) or it["key"] not in (1, -1):
            err(f"V1 key 非法：{it['id']} key={it['key']}")

    if len({it["id"] for it in items}) != 300:
        err("V1 id 不唯一")

    # 施测顺序必须是从 1 到 300 的排列
    orders = sorted(it["order"] for it in items)
    if orders != list(range(1, 301)):
        err("V1 administration_order 不是 1..300 的排列")

    # 交错循环：前 30 题应覆盖 30 个不同 facet
    first30 = [it["facet"] for it in sorted(items, key=lambda x: x["order"])[:30]]
    if len(set(first30)) != 30:
        err("V1 施测顺序不是 30-facet 交错循环（前 30 题应覆盖全部 facet 各一次）")

    # V3：reverse_items 与 key == -1 一致
    n_rev = sum(1 for it in items if it["key"] < 0)
    if canon["structure"]["reverse_keyed_items"] != n_rev:
        err(f"V3 声明的反向题数 {canon['structure']['reverse_keyed_items']} != 实际 {n_rev}")

    # 每 facet 的正反向平衡
    for f, v in facets.items():
        pos = sum(1 for x in v if x["key"] > 0)
        neg = sum(1 for x in v if x["key"] < 0)
        if abs(pos - neg) > 2:
            warn(f"V3 facet {f} 计分键不平衡：{pos} 正 / {neg} 反")

    # 题面完整
    missing = [it["order"] for it in items if not it.get("text")]
    if missing:
        err(f"V4 缺题面：{missing[:10]}")

    alphas = [v for v in canon.get("facet_alphas", {}).values() if v]
    print(f"  整卷：{len(items)} 题 / {len(facets)} facet / {n_rev} 反向题"
          + (f" / facet α {min(alphas):.2f}–{max(alphas):.2f}" if alphas else ""))
    return canon


# ---------------------------------------------------------------- 档案记录
def check_record(path: str, canon: dict) -> None:
    rec = json.load(open(path, encoding="utf-8"))
    name = os.path.basename(path)
    by_id = {it["id"]: it for it in canon["items"]}
    rec_items = rec["items"]
    facet = rec["identity"]["id"].split(".")[-1]
    canon_facet = {it["id"]: it for it in canon["items"] if it["facet"] == facet}

    # V1：id ↔ order ↔ key ↔ text 四者一致
    for it in rec_items:
        c = by_id.get(it["id"])
        if c is None:
            err(f"V1 [{name}] id 不存在于规范数据集：{it['id']}")
            continue
        order = it.get("administration_order", it.get("order"))
        if order is None:
            err(f"V1 [{name}] {it['id']} 缺 administration_order")
        elif c["order"] != order:
            err(f"V1 [{name}] {it['id']} order 不符：档案 {order} vs 规范 {c['order']}")
        if c["key"] != it["key"]:
            err(f"V1 [{name}] {it['id']} key 不符：档案 {it['key']} vs 规范 {c['key']}")
        if c["facet"] != facet:
            err(f"V1 [{name}] {it['id']} facet 不符：{c['facet']} != {facet}")
        if c["text"] != it["text_en"]:
            err(f"V1 [{name}] {it['id']} 英文题干不符")

    # 覆盖：facet 内 10 题齐全
    if {it["id"] for it in rec_items} != set(canon_facet):
        missing = set(canon_facet) - {it["id"] for it in rec_items}
        err(f"V2 [{name}] facet {facet} 未覆盖全部题目，缺 {sorted(missing)}")

    # V3：scoring 声明与 items 一致
    sc = rec["scoring"]
    declared_rev = set(sc["reverse_items"])
    actual_rev = {it["id"] for it in rec_items if it["key"] < 0}
    if declared_rev != actual_rev:
        err(f"V3 [{name}] reverse_items 与 key=-1 不一致")
    if set(sc["reverse_items"]) | set(sc["forward_items"]) != {it["id"] for it in rec_items}:
        err(f"V3 [{name}] scoring 声明的题目集合与 items 不一致")

    # V4：中文溯源
    allowed = {"mandarin_baseline", "project_translation",
               "project_translation_override", "cognitive_interview_verified"}
    base = json.load(open(os.path.join(ROOT, "data/ipip-neo-120-mandarin.json"), encoding="utf-8"))
    base_zh = {i["zh"] for i in base["items"] if i["facet"] == facet}
    for it in rec_items:
        if not it.get("text_zh"):
            err(f"V4 [{name}] {it['id']} 缺中文题面")
        src = it.get("text_zh_source")
        if src not in allowed:
            err(f"V4 [{name}] {it['id']} text_zh_source 非法：{src}")
        if src == "mandarin_baseline" and it["text_zh"] not in base_zh:
            err(f"V4 [{name}] {it['id']} 标为官方译本但不在基线中：{it['text_zh']}")

    # V4b：译文覆盖（D27）——括号原文 + 溯源 + 说明，三者缺一不可
    for it in rec_items:
        if it.get("text_zh_source") == "project_translation_override":
            zh = it.get("text_zh") or ""
            if not ("（" in zh and "）" in zh):
                err(f"V4b [{name}] {it['id']} 覆盖译文未含中文全角括号与英文原文：{zh}")
            tn = it.get("translation_note") or {}
            if not tn.get("reason"):
                err(f"V4b [{name}] {it['id']} 覆盖译文缺 translation_note.reason")
            if not tn.get("defect"):
                err(f"V4b [{name}] {it['id']} 覆盖译文缺 translation_note.defect")

    # V5：脚手架
    req = ["asks", "key_term", "common_misreadings", "counts_as",
           "does_not_count_as", "provenance", "evidence_anchor"]
    sc_allowed = {"published_definition", "editorial_clarification",
                  "cognitive_interview_verified"}
    n_pending = 0
    for it in rec_items:
        s = it.get("scaffolding")
        if not s:
            err(f"V5 [{name}] {it['id']} 缺 scaffolding")
            continue
        # PENDING 是合法的显式状态（schema §6.1）——但必须写明 blocker
        if s.get("status") == "PENDING":
            n_pending += 1
            if not s.get("blocker"):
                err(f"V5 [{name}] {it['id']} scaffolding 为 PENDING 但未写 blocker")
            continue
        for f in req:
            if f not in s:
                err(f"V5 [{name}] {it['id']} scaffolding 缺字段 {f}")
        if s.get("provenance") not in sc_allowed:
            err(f"V5 [{name}] {it['id']} provenance 非法：{s.get('provenance')}")
        for m in s.get("common_misreadings", []):
            if "misreading" not in m or "correction" not in m:
                err(f"V5 [{name}] {it['id']} misreading 必须同时含 misreading 与 correction")
            elif not m["misreading"].strip() or not m["correction"].strip():
                err(f"V5 [{name}] {it['id']} misreading/correction 不得为空")
        # V5b：源数据层就要求 mis 是 (误读, 修正) 二元组——本轮踩过的坑
        for c in s.get("counts_as", []):
            if not isinstance(c, str) or not c.strip():
                err(f"V5 [{name}] {it['id']} counts_as 含非法项")
        for c in s.get("does_not_count_as", []):
            if not isinstance(c, str) or not c.strip():
                err(f"V5 [{name}] {it['id']} does_not_count_as 含非法项")
        if not s.get("counts_as"):
            err(f"V5 [{name}] {it['id']} counts_as 为空")
        if not s.get("does_not_count_as"):
            err(f"V5 [{name}] {it['id']} does_not_count_as 为空")
        if "localization_note" not in s:
            err(f"V5 [{name}] {it['id']} scaffolding 缺 localization_note（无则写 null）")
        if s.get("key_term") and "not_this" not in s["key_term"]:
            err(f"V5 [{name}] {it['id']} key_term 缺 not_this")

    # V6 + 常模对接：档案声明的分带必须与解析产物一致
    if os.path.exists(NORMS):
        norms = json.load(open(NORMS, encoding="utf-8"))
        declared = rec.get("norms", {}).get("bands_values")
        if declared:
            for age, bands in declared.items():
                parsed = norms["levels"]["facets"].get(age, {}).get(facet.capitalize())
                if parsed is None:
                    # 用与 builder 相同的显式映射，不做模糊匹配
                    import sys as _s
                    _s.path.insert(0, ROOT)
                    from content.facet_definitions import NORM_COLUMN
                    col = NORM_COLUMN.get(facet, facet)
                    tab = norms["levels"]["facets"].get(age, {})
                    parsed = tab.get(col)
                    if parsed is None:
                        cand = [k for k in tab if k.lower().replace("-", "").replace(" ", "")
                                == col.replace("_", "")]
                        parsed = tab[cand[0]] if cand else None
                if parsed is None:
                    warn(f"V6 [{name}] 常模表中找不到 {age}/{facet}，跳过比对")
                    continue
                for b in BANDS:
                    if b not in parsed:
                        continue
                    exp = parsed[b]
                    got = bands.get(b, [])
                    exp_s = f"{exp[0]}-{exp[-1]}" if len(exp) > 1 else str(exp[0])
                    if got != exp_s:
                        err(f"V6 [{name}] {age}/{b} 分带与常模产物不符："
                            f"档案 {got} vs 产物 {exp_s}")

    # V8：内容局限必须被"分诊"到用户可见层
    ev = rec.get("evidence", {}) or {}
    if "interpretation_caveats" not in ev:
        err(f"V8 [{name}] 缺 evidence.interpretation_caveats——"
            f"即使该 facet 无内容局限，也必须显式写出空数组")
    else:
        crit = ev.get("known_critiques", []) or []
        cav = ev.get("interpretation_caveats", []) or []
        if crit and not cav:
            warn(f"V8 [{name}] 有 {len(crit)} 条 known_critiques 但未分诊出任何"
                 f" interpretation_caveats——请确认没有该告知用户的内容局限")

    # PENDING 规则
    for key in ("norms", "reliability"):
        node = rec.get(key, {})
        for k, v in node.items():
            if isinstance(v, dict) and v.get("status") == "PENDING" and not v.get("blocker"):
                err(f"V6 [{name}] {key}.{k} 为 PENDING 但未写明 blocker")

    st = rec.get("item_status", {})
    print(f"  档案 {name[:44]:<46} {len(rec_items)} 题 "
          f"中文 {st.get('chinese_official','?')}+{st.get('chinese_project_translation','?')} "
          f"脚手架 {st.get('scaffolding_authored','?')}/{st.get('scaffolding_pending','?')}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", action="append", default=None)
    args = ap.parse_args()

    print("=== V2/V3 整卷结构 ===")
    canon = check_canonical()

    if args.record:
        records = args.record
    else:
        pilot = os.path.join(ROOT, "content/facets")
        records = sorted(os.path.join(pilot, f) for f in os.listdir(pilot)
                         if f.endswith(".record.json"))
    print("\n=== 档案记录 ===")
    for r in records:
        if os.path.exists(r):
            check_record(r, canon)
        else:
            warn(f"记录不存在，跳过：{r}")

    print()
    if errors:
        print(f"❌ {len(errors)} 个错误：")
        for e in errors:
            print("   -", e)
    else:
        print("✅ 全部校验规则通过（V1–V8）")
    if warns:
        print(f"\n⚠️ {len(warns)} 条提示：")
        for w in warns:
            print("   -", w)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
