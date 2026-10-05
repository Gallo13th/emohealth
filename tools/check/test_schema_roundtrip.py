#!/usr/bin/env python3
"""用**已有的人工核对产物**检验新 schema 转换器的正确性。

思路：``data/ipip-neo-300.json`` 是本项目早先逐题核对过的权威产物
（含 facet 归属、+1/−1 计分键、题项正文、反向题清单）。把同一份 OpenScales
源用新转换器转一遍，逐字段比对：

  · facet 归属：同一道题是否落在同一 facet
  · 计分方向：+1/−1 是否一致（含 148 个反向题）
  · 题项正文：是否逐字一致

比中越多，越能说明转换器可以安全地用于其他量表。比不中之处要**逐条列出**，
不能只报一个百分比——差异本身是信息。
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

from build_scales import (  # noqa: E402
    CODES_FILE, EN_TRANSLATIONS, build_instrument, load_json,
)


def main() -> int:
    with open(os.path.join(ROOT, "data", "ipip-neo-300.json"), encoding="utf-8") as fh:
        ref = json.load(fh)

    code_pool = load_json(CODES_FILE).get("code_to_text") or {}
    en_pool = load_json(EN_TRANSLATIONS)

    # 已知缺陷：ipip_E11 是悬空引用，其正文由官方问卷 #70 提供
    # （见 data/ipip-neo-300.json 的 known_defects_repaired[0]：
    #   text_source = "questionnaire_docx(补全机读缺陷)"）。
    # 这里显式传入该权威正文，而不是让转换器静默填占位符。
    # ⚠️ 我曾在这里凭记忆填过一句别的正文，导致 1/300 误报——测试里的
    #    「已知值」也必须来自产物，不能来自记忆。
    overrides = {}
    for it in ref["items"]:
        if it.get("code"):
            overrides[it["code"]] = it["text"]

    inst, warn = build_instrument("IPIP-NEO", code_pool=code_pool, en_pool=en_pool,
                                  text_overrides=overrides)
    print(f"转换结果：{len(inst.items)} 题 · {len(inst.dimensions)} 维 · "
          f"{len(inst.scoring)} 规则")
    if warn:
        print(f"警告 {len(warn)} 条：")
        for w in warn[:8]:
            print("  ·", w)

    ref_by_code = {it["code"]: it for it in ref["items"] if it.get("code")}
    new_by_code = {it.source_code: it for it in inst.items if it.source_code}

    print(f"\n基准（data/ipip-neo-300.json）：{len(ref_by_code)} 题有 code")
    print(f"新转换：{len(new_by_code)} 题有 source_code")
    common = sorted(set(ref_by_code) & set(new_by_code))
    print(f"可逐题比对：{len(common)} 题")

    # ① 计分方向
    dir_bad = [(c, ref_by_code[c]["key"], new_by_code[c].key)
               for c in common if ref_by_code[c]["key"] != new_by_code[c].key]
    print(f"\n① 计分方向一致：{len(common) - len(dir_bad)}/{len(common)}")
    for c, a, b in dir_bad[:10]:
        print(f"   ✗ {c}: 基准 {a} vs 新 {b}  ({ref_by_code[c]['text'][:50]})")

    # ② 题项正文
    txt_bad = [(c, ref_by_code[c]["text"], new_by_code[c].text)
               for c in common
               if ref_by_code[c]["text"].strip().lower() != new_by_code[c].text.strip().lower()]
    print(f"\n② 题项正文一致：{len(common) - len(txt_bad)}/{len(common)}")
    for c, a, b in txt_bad[:10]:
        print(f"   ✗ {c}:\n       基准: {a[:80]}\n       新的: {b[:80]}")

    # ③ facet 归属（基准的 facet 名 → 新 schema 的维度 id）
    facet_bad = []
    for c in common:
        ref_f = ref_by_code[c]["facet"]
        new_dims = set()
        for d in inst.dimensions:
            if any(it.id == new_by_code[c].id for it in []):
                pass
        # 新 schema 里题项自己带 dimensions
        new_dims = set(new_by_code[c].dimensions)
        if not new_dims:
            new_dims = {d.id for d in inst.dimensions
                        if new_by_code[c].id in d.items}
        if ref_f not in new_dims:
            facet_bad.append((c, ref_f, sorted(new_dims)))
    print(f"\n③ facet 归属一致：{len(common) - len(facet_bad)}/{len(common)}")
    for c, a, b in facet_bad[:10]:
        print(f"   ✗ {c}: 基准 {a} vs 新 {b}")

    # ④ 反向题总数
    ref_rev = sum(1 for it in ref["items"] if it.get("key") == -1)
    new_rev = sum(1 for it in inst.items if it.key == -1)
    print(f"\n④ 反向题数：基准 {ref_rev} vs 新 {new_rev}"
          f"  {'✅' if ref_rev == new_rev else '❌'}")

    # ⑤ 维度数
    ref_facets = {it["facet"] for it in ref["items"] if it.get("facet")}
    print(f"⑤ 维度数：基准 {len(ref_facets)} 个 facet vs 新 {len(inst.dimensions)} 维"
          f"  {'✅' if len(ref_facets) == len(inst.dimensions) else '❌'}")
    missing = ref_facets - {d.id for d in inst.dimensions}
    extra = {d.id for d in inst.dimensions} - ref_facets
    if missing:
        print(f"   新 schema 缺少的 facet：{sorted(missing)}")
    if extra:
        print(f"   新 schema 多出的维度：{sorted(extra)}")

    problems = len(dir_bad) + len(txt_bad) + len(facet_bad)
    print(f"\n{'='*60}")
    if problems == 0 and ref_rev == new_rev:
        print("✅ 转换器与人工核对产物完全一致——可用于其他量表")
        return 0
    print(f"❌ 共 {problems} 处差异，需要逐条查清（差异本身是信息）")
    return 1


if __name__ == "__main__":
    sys.exit(main())
