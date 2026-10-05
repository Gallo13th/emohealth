#!/usr/bin/env python3
"""组装 DSM-5-TR Level 1 成人册的量表包（``data/instruments/dsm5tr-l1.json``）。

要点
====
· 计分口径：**每个域的分数 = 该域内题目的最高分**（手册 Instructions to
  Clinicians 原文）。所以 rubric 用 ``aggregation="max"``。
· 授权：APA 版权，允许研究人员/临床医生无需许可复制，**但明文「不得修改」**
  （may not be modified absent written permission from APA）。这一条要写进
  量表包的 license.notes 与 provenance，因为**它直接影响我们能否提供中译**——
  中译属于「修改」，未获书面许可就不能做。
· 来源与哈希取自 ``archive/scales/DSM5TR-L1/source.json``。
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

from engine.instrument_schema import (  # noqa: E402
    Dimension, Instrument, Item, License, ResponseFormat, Rubric,
)
from engine.scoring import validate_against_declaration  # noqa: E402


def load(rel: str) -> dict:
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def dim_id(name: str) -> str:
    return "l1_" + re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def main() -> int:
    doc = load("archive/scales/DSM5TR-L1/items-extracted.json")
    src = load("archive/scales/DSM5TR-L1/source.json")
    rf = doc["response_format"]

    items = [Item(order=x["order"], id=f"l1_{x['order']:02d}", text=x["text"],
                  dimensions=[dim_id(next(d["name"] for d in doc["domains"]
                                          if x["order"] in d["items"]))],
                  key=1,
                  source_code=f"Level 1 item {x['order']}",
                  text_source="APA DSM-5-TR Level 1 manual "
                              "(archive/scales/DSM5TR-L1/manual.pdf)")
             for x in doc["items"]]

    dims: list[Dimension] = []
    rubrics: dict[str, Rubric] = {}
    for d in doc["domains"]:
        if not d["items"]:
            continue
        did = dim_id(d["name"])
        ids = [f"l1_{o:02d}" for o in d["items"]]
        dims.append(Dimension(id=did, name=d["name"], level=1, items=ids))
        rubrics[did] = Rubric(
            id=did, label=d["name"], aggregation="max", scope="items", of=ids,
            notes="手册 Instructions to Clinicians：该域分数 = 域内题目最高分")

    lic = src["license"]
    inst = Instrument(
        instrument="DSM5TR-L1",
        display_name=src["title"],
        citation=("American Psychiatric Association. DSM-5-TR Self-Rated Level 1 "
                  "Cross-Cutting Symptom Measure—Adult."),
        license=License(
            kind="copyright_permitted",
            holder=lic.get("holder", "American Psychiatric Association"),
            text=lic["text"],
            url=src["source_url"],
            evidence=f"archive/scales/DSM5TR-L1/source.json + PDF 正文『Rights granted』"
                     f"（sha256 {src['sha256'][:16]}…）",
            redistribution=bool(lic.get("redistribution")),
            notes="APA 版权，允许研究人员/临床医生无需许可复制使用；"
                  "**但明文规定不得修改**（may not be modified absent written "
                  "permission from APA）。按 R2（用户 2026-10-04）：本项目**逐字不改原文**，"
                  "而是把英文原文、中文翻译、本地化内容讲解三者**并列**作为"
                  "**补充性独立内容**呈现——中译与讲解不是对原文的修改。",
        ),
        structure={
            "source": "APA DSM-5-TR Online Assessment Measures（官方公开）",
            "items": len(items),
            "domains": len(dims),
            "response_format": {"points": rf["points"], "min": rf["min"],
                                "max": rf["max"], "labels": rf["labels"]},
            "window": rf.get("window", ""),
        },
        items=items, dimensions=dims, scoring=rubrics,
        version="1.0",
        response_format=ResponseFormat(points=rf["points"], min=rf["min"],
                                       max=rf["max"], labels=rf["labels"]),
        item_order_source="archive/scales/DSM5TR-L1/manual.pdf 题项区顺序（题号 1..23）",
        provenance={
            "items": "archive/scales/DSM5TR-L1/items-extracted.json"
                     "（提取器 tools/build/build_l1_items.py）",
            "license": "archive/scales/DSM5TR-L1/source.json"
                       "（授权原文补录：tools/build/fix_dsm5tr_licenses.py）",
            "scoring_rule": doc["scoring_rule"],
            "manual_sha256": src["sha256"],
            "manual_bytes": src["bytes"],
            "translation_policy": {
                "stance": "supplementary_bilingual",
                "text": "R2（用户 2026-10-04）：授权禁止**修改**原文，故本项目逐字不改；"
                        "英文原文、中文翻译、本地化内容讲解三者并列，属"
                        "**补充性独立内容**，不是修改。中译复核状态见 data/text-db 的 "
                        "zh_source（均未人工复核）。",
            },
        },
    )

    errs = inst.validate(require_redistributable=True)
    decl = validate_against_declaration(inst)
    # ── 判读口径：Level 1 **不是常模量表**，它给的是「进一步询问的门槛」。
    #    这个字段让界面能如实呈现门槛判定，而不是去显示百分位（那会是编造的）。
    #    数据来自 data/linkage/dsm5tr-chain.json（源自手册 Table 1，可溯源）。
    chain_path = os.path.join(ROOT, "data", "linkage", "dsm5tr-chain.json")
    if os.path.exists(chain_path):
        chain = load("data/linkage/dsm5tr-chain.json")
        l1 = chain["level1"]
        by_name = {d["name"]: d for d in l1["domains"]}
        inst.interpretation = {
            "kind": "threshold",
            "note": l1["purpose"],
            "scoring": l1["scoring"],
            "window": l1.get("window", ""),
            "domains": [{
                "domain": name,
                "items": dim.items,
                "threshold": by_name[name]["threshold"],
                "threshold_label": by_name[name]["threshold_label"],
                "level2": by_name[name]["level2"],
                "note": by_name[name]["note"],
            } for name, dim in ((d["name"], next(x for x in dims if x.name == d["name"]))
                                for d in l1["domains"])],
            "evidence": l1["evidence"],
            "pid5_interface": chain["pid5_interface"],
            "disclaimer": chain["disclaimer"],
        }
        print(f"判读口径已写入：13 域门槛 + 与 PID-5 的接口（标为推论）")
    print(f"题项 {len(items)}｜域 {len(dims)}｜计分规则 {len(rubrics)}")
    print(f"域题数分布：{sorted(len(d.items) for d in dims)}")
    if errs:
        print("✗ schema 校验未通过：")
        for e in errs[:8]:
            print(f"  · {e}")
        return 1
    if decl:
        print("✗ 计分声明不自洽：")
        for e in decl[:8]:
            print(f"  · {e}")
        return 1
    print("✓ schema 校验通过（含再分发门）")
    print("✓ 计分规则与维度声明自洽")

    out_dir = os.path.join(ROOT, "data", "instruments")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "dsm5tr-l1.json")
    payload = inst.to_dict()
    # ⚠️ 重新生成会**覆盖**掉后续步骤挂上去的字段。
    #    `linkage` 由 `tools/build/attach_linkage.py` 挂、`norms_status` 由
    #    `tools/build/attach_norms.py` 挂，它们**都不在** `Instrument` 数据类里，
    #    所以 `to_dict()` 之后就不见了。
    #    我（2026-10-04）因改 R2 措辞重跑本脚本，正是这一下**静默删掉了 L1 的
    #    链路条与 PID-5 入口**——`test_chain_nav` 两项失败，但页面不报任何错
    #    （典型「静默半渲染」）。L2 的生成器早有同样的继承逻辑（见 build_l2_
    #    instruments.py），L1 这里漏了。先把旧值继承过来，再写。
    if os.path.exists(path):
        try:
            old = json.load(open(path, encoding="utf-8"))
            for k in ("linkage", "norms", "norms_status", "criteria",
                      "criteria_source"):
                if old.get(k) and not payload.get(k):
                    payload[k] = old[k]
        except Exception:                                    # noqa: BLE001
            pass
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(f"✓ 已写出 {os.path.relpath(path, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
