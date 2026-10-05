#!/usr/bin/env python3
"""生成多量表目录（``data/instruments/catalog.json``）。

为什么需要目录
==============
界面不可能把 40 套量表、2178 道题一次加载（现在是 5 个静态 ``<script>`` 前置加载
1 MB）。多量表的做法是：

    ui/catalog.js            只有元信息（几 KB），先加载
    ui/instruments/<code>.js 每套量表一个数据包，选中时才注入

目录里**不放题项**，只放「有哪些量表、各多少题、授权是什么、数据包在哪」。
这样界面可以先渲染量表列表，用户选一套再拉那套的数据。

同时把「授权」摆在目录里（而不是埋在数据包里），是因为本项目要求
**界面上每个数字都能追到出处**——用户看到某个量表时，应能立刻看到它的授权与来源。

输出
====
· ``data/instruments/catalog.json``  目录（**数据层只到这里**，人读 + 程序读）

前端包 ``ui/catalog.js``（``window.EMOHEALTH_CATALOG``）由前端层的
``tools/ui/pack_ui_data.py`` 从这份 JSON 打包——数据层不再写 ``ui/``（契约 C3）。
"""

from __future__ import annotations

import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()

# 许可的类别标签（界面直接显示；顺序即展示顺序）
LICENSE_LABEL = {
    "public_domain": "公有领域",
    "cc_by": "CC 署名（可再分发）",
    "cc_by_nc": "CC 署名-非商用",
    "copyright_permitted": "权利人允许复制（需署名）",
    "unknown": "授权未明",
}

# 按「用户想了解自己什么」分组，而不是按来源分组。
#
# ⚠️ 分组顺序就是匹配优先级：一套量表只进**第一个**匹配到的组。
#    我第一版只有 4 组，结果「其它」塞了 285/341 套——那不是分类，是没收纳。
#    现在把态度信念、社会关系、健康、工作学业等拆出来，并留一个真正兜底的组。
GROUPS = {
    "personality": {
        "label": "人格特质",
        "match": r"IPIP-NEO|HEXACO|16PF|Big5|Big Five|BFAS|VIA|CATPD|Personality|"
                 r"Temperament|Character|Self-Conscious|Chapman|Buss",
    },
    "psychopathology": {
        "label": "适应不良与临床特质",
        "match": r"PID-5|Disorder|Psychopath|Borderline|Narciss|Machiavell|"
                 r"Dissociat|Autis|ADHD|Schizotyp|Impulsiv",
    },
    "state": {
        "label": "当前状态与症状",
        "match": r"DSM5TR|DASS|CESD|Depress|Anxi|Sleep|Somatic|Anger|Mania|"
                 r"Substance|Repetitive|Stress|Burnout|Panic|Phobia|Mood|Suicid|"
                 r"Trauma|PTSD|Eating|Loneli|Well-?being|Flourish|Resilien",
    },
    "attitudes": {
        "label": "态度、信念与价值观",
        "match": r"Attitude|Belief|Value|Ideolog|Conservat|Politic|Trust|Religion|"
                 r"Spiritual|Moral|Ethic|Justice|Environment|Worry|Conspiracy|"
                 r"Prejudice|Racis|Sexis|Ageis|Authoritarian|Dogmat|Worldview|"
                 r"Opinion|Norm|Climate|Science|Health Belief",
    },
    "social": {
        "label": "社会关系与沟通",
        "match": r"Social|Relation|Attach|Interpersonal|Empath|Compassion|"
                 r"Gratitude|Forgive|Conflict|Communication|Loneliness|Support|"
                 r"Trust in|Team|Leadership|Cooperation|Altruis|Aggress|"
                 r"Assert|Intimacy|Friendship|Family|Parent",
    },
    "health": {
        "label": "身心健康与行为",
        "match": r"Health|Sleep|Diet|Nutrition|Exercise|Physical|Pain|Fatigue|"
                 r"Smok|Alcohol|Drink|Screen|Video|Gaming|Internet|Phone|"
                 r"Addiction|Dependence|Coping|Cope|Recovery|Quality of Life|"
                 r"Sexual|Body|Weight|Medication|Antidepressant|Vaccin",
    },
    "work": {
        "label": "工作、学习与效能",
        "match": r"Work|Job|Career|Employ|Leader|Organiz|Motivation|Achieve|"
                 r"Cognit|Intellig|Creativ|Memory|Attention|Learning|Academic|"
                 r"Study|Procrastinat|Time|Control|Effort|Grit|Performance|"
                 r"Decision|Problem|Risk|Financial|Money|Consum",
    },
    "other": {"label": "其它", "match": r".*"},
}


def main() -> int:
    paths = sorted(glob.glob(os.path.join(ROOT, "data", "instruments", "*.json")))
    entries = []
    for p in paths:
        if os.path.basename(p) == "catalog.json":
            continue
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
        code = d["instrument"]
        lic = d["license"]
        facets = [x for x in d["dimensions"] if x.get("level", 1) == 1]
        # 只列出「真正要作答的维度」：叶子维度里题项最多的那些
        top_dims = sorted(facets, key=lambda x: -len(x.get("items", [])))[:3]
        entries.append({
            "code": code,
            "file": os.path.basename(p),
            "display_name": d["display_name"],
            "items": len(d["items"]),
            "dimensions": len(facets),
            "response": {
                "min": d["structure"]["response_format"]["min"],
                "max": d["structure"]["response_format"]["max"],
            },
            "license": {
                # ⚠️ 目录里**只放标签与可再分发标志**，不放授权原文与证据路径。
                #    原文在数据包里也有一份（`loadInstrument` 之后即可取到），
                #    目录重复存会让首屏膨胀：实测 341 套时 license + citation
                #    占了目录体积的 58%（155 KB / 267 KB）。
                "kind": lic["kind"],
                "label": LICENSE_LABEL.get(lic["kind"], lic["kind"]),
                "redistribution": lic.get("redistribution"),
            },
            "pack": f"instruments/{os.path.basename(p)}",
        })

    # 分组：按 GROUPS 的顺序，每套量表只进第一个匹配的分组
    import re
    for g in GROUPS.values():
        g["codes"] = []
    assigned = set()
    for gname, g in GROUPS.items():
        for e in entries:
            if e["code"] in assigned:
                continue
            hay = f"{e['code']} {e['display_name']}"
            if re.search(g["match"], hay, re.I):
                g["codes"].append(e["code"])
                assigned.add(e["code"])
    # 兜底：没进任何分组的进 other
    for e in entries:
        if e["code"] not in assigned:
            GROUPS["other"]["codes"].append(e["code"])

    catalog = {
        "schema_version": "2.0",
        "note": "多量表目录：只有元信息，题项在各 data/instruments/<code>.json 里，"
                "界面按需加载",
        "count": len(entries),
        "total_items": sum(e["items"] for e in entries),
        "groups": [{"id": k, "label": v["label"], "codes": v["codes"]}
                   for k, v in GROUPS.items() if v["codes"]],
        "instruments": entries,
    }

    out_json = os.path.join(ROOT, "data", "instruments", "catalog.json")
    with open(out_json, "w", encoding="utf-8") as fh:
        json.dump(catalog, fh, ensure_ascii=False, indent=1)
        fh.write("\n")

    print(f"量表 {catalog['count']} 套，题项合计 {catalog['total_items']}")
    print(f"分组：")
    for g in catalog["groups"]:
        print(f"  {g['label']:34} {len(g['codes']):2} 套")
    print(f"\n授权分布：")
    from collections import Counter
    c = Counter(e["license"]["kind"] for e in entries)
    for k, n in c.most_common():
        print(f"  {LICENSE_LABEL.get(k, k):34} {n:2} 套")
    print(f"\n已写出 {os.path.relpath(out_json, ROOT)}"
          f"（{os.path.getsize(out_json) / 1024:.1f} KB）"
          f"（前端包 ui/catalog.js 由 tools/ui/pack_ui_data.py 打包）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
