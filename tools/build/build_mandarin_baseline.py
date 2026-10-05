#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建官方便携中文译本基线（IPIP-NEO-120 Mandarin）。

为什么重要：IPIP-NEO-300 **没有**任何中文译本（见 `research/phase0_ipip_audit.md` §3），
我们必须自译。但官方的 **120 题**普通话译本是唯一经过规范流程
（前译 → 共识会议 → 回译 → 专家/英语教师/潜在用户审阅，华东师大团队）的中文资产，
且**覆盖全部 30 个 facet，每 facet 4 题**。

因此它应当作为自译的**校准基准**：复用其已确立的术语与语体，而不是从零开始。

来源：<https://www.ipip.ori.org/Mandarin%20translation%20of%20IPIP-NEO-120.htm>

⚠️ 溯源警告：IPIP 官方明确声明 **"The accuracy of these translations has not been verified by
anyone associated with the IPIP project."** —— 本译本未经 IPIP 背书，仅作为参考基准，
不得当作已验证的测量工具直接使用。

输出：`data/ipip-neo-120-mandarin.json`
"""
from __future__ import annotations

import collections
import html
import json
import os
import sys
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
PAGE = os.path.join(ROOT, "archive/ipip/site/Mandarin_translation_of_IPIP-NEO-120.htm")
OSD_DIR = os.path.join(ROOT, "archive/ipip/data/OpenScales/scales/ipip")
OUT = os.path.join(ROOT, "data/ipip-neo-120-mandarin.json")

CYCLE_LEN = 30


def norm(s: str) -> str:
    return re.sub(r"[^a-z]", "", (s or "").lower())


def parse_pairs(path: str) -> list[tuple[str, str]]:
    """该页面是 Word 导出的 windows-1252 HTML，中文以数字实体存储。"""
    text = html.unescape(open(path, "rb").read().decode("cp1252"))

    def cells(row: str) -> list[str]:
        return [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", c)).strip()
                for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S | re.I)]

    pairs = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", text, re.S | re.I):
        c = [x for x in cells(row) if x]
        if len(c) >= 2:
            en = re.sub(r"^\d+\.\s*", "", c[0])
            zh = re.sub(r"^\d+\.\s*", "", c[1])
            if re.search(r"[\u4e00-\u9fff]", zh) and re.search(r"[A-Za-z]{3}", en):
                pairs.append((en, zh))
    return pairs


def main() -> int:
    pairs = parse_pairs(PAGE)
    codes = json.load(open(os.path.join(OSD_DIR, "ipip_item_codes.json"), encoding="utf-8"))["code_to_text"]
    txt2code = {norm(v): k for k, v in codes.items() if v}

    od = json.load(open(os.path.join(OSD_DIR, "IPIP-NEO", "IPIP-NEO.osd"), encoding="utf-8"))["definition"]
    code2facet: dict[str, str] = {}
    for fk, spec in od["scoring"].items():
        if not fk.endswith("_sum"):
            continue
        for iid in spec["items"]:
            it = next(x for x in od["items"] if x["id"] == iid)
            raw = it["text_key"]
            c = (raw[len("ipip_"):] if raw.startswith("ipip_") else raw).strip()
            code2facet[c] = fk[: -len("_sum")]

    log: list[str] = []
    rows = []
    for n, (en, zh) in enumerate(pairs, 1):
        code = txt2code.get(norm(en))
        facet = code2facet.get(code) if code else None
        method = "text_match"
        if facet is None:
            # 结构回退：该译本与 300 题问卷共用同一个 30-facet 交错循环。
            # 循环由已匹配项推定；未匹配项按位置取自同一循环。
            method = "pending"
        rows.append({"order": n, "en": en, "zh": zh, "ipip_code": code,
                     "facet": facet, "match_method": method})

    # 用已匹配项推定循环
    pos_facet: dict[int, str] = {}
    for r in rows:
        if r["facet"]:
            pos_facet[(r["order"] - 1) % CYCLE_LEN] = r["facet"]
    complete = len(pos_facet) == CYCLE_LEN
    log.append(f"由文本匹配确定的循环位置：{len(pos_facet)} / {CYCLE_LEN}")

    for r in rows:
        if r["facet"] is None:
            if complete:
                r["facet"] = pos_facet[(r["order"] - 1) % CYCLE_LEN]
                r["match_method"] = "structural_cycle_fallback"
                log.append(f"结构回退：#{r['order']} 「{r['en'][:48]}」→ {r['facet']}")
            else:
                log.append(f"❌ 无法归属：#{r['order']} 「{r['en'][:48]}」")

    counts = collections.Counter(r["facet"] for r in rows)
    problems = []
    if len(rows) != 120:
        problems.append(f"题目数 {len(rows)} != 120")
    if len(counts) != 30:
        problems.append(f"facet 数 {len(counts)} != 30")
    bad = {f: c for f, c in counts.items() if c != 4}
    if bad:
        problems.append(f"facet 题数异常：{bad}")

    payload = {
        "instrument": "IPIP-NEO-120 (Mandarin Chinese)",
        "translation_of": "Johnson, J. A. (2014). IPIP-NEO-120. JRP, 51, 78-89.",
        "translators": "Zhongyang Xu, Jing Qian, Kunning Chen, Lianxin Zhu, Jianlong Ao "
                       "(East China Normal University), supervised by Ya Zhang, Ph.D.",
        "translation_procedure": "forward translation → consensus meetings → back translation → "
                                 "review by experts, English teacher and potential users",
        "source_url": "https://www.ipip.ori.org/Mandarin%20translation%20of%20IPIP-NEO-120.htm",
        "retrieved_at": "2026-09-29",
        "provenance_warning": "IPIP 官方声明：'The accuracy of these translations has not been "
                              "verified by anyone associated with the IPIP project.' "
                              "本译本未经 IPIP 背书，仅作自译校准基准，不得当作已验证工具使用。",
        "role_in_project": "IPIP-NEO-300 自译的术语与语体校准基准（300 题无任何中文译本）",
        "coverage": {
            "items": len(rows),
            "facets": len(counts),
            "items_per_facet": 4,
            "covers_all_30_facets": len(counts) == 30,
        },
        "validation": {"problems": problems},
        "build_log": log,
        "items": rows,
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)

    print(json.dumps(payload["coverage"], ensure_ascii=False))
    print(json.dumps({"problems": problems}, ensure_ascii=False))
    print("\n".join(log))
    print("facet 题数分布:", dict(collections.Counter(counts.values())))
    print(f"wrote {OUT}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
