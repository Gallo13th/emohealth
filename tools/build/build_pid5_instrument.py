#!/usr/bin/env python3
"""组装 PID-5 量表包（``data/instruments/pid-5.json``）。

把三份已确证的产物合起来：
  · ``archive/scales/PID-5/items-extracted.json``   220 道题干（提取 + 交叉核对）
  · ``data/pid5-scoring-keys.json``                 25 facet / 5 域 / 反向题
  · ``archive/scales/PID-5/source.json``            授权与来源（SHA256、页脚原文）

输出遵守 ``engine/instrument_schema.py`` 的约定，并强制通过两道项目硬规则：
  · ``validate(require_redistributable=True)``：授权不允许再分发的量表直接判错（D20）
  · ``validate_against_declaration()``：计分规则与维度声明必须自洽（防两处口径漂移）

域的处理：手册域表只列了每域 **3 个主要 facet**（共 15 个）。PID-5 的域分是
「该域三个 facet 得分的均分」，所以域维度声明为 ``scope=dimensions`` 的 mean 规则，
子项就是这三个 facet。
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


def main() -> int:
    items_doc = load("archive/scales/PID-5/items-extracted.json")
    keys = load("data/pid5-scoring-keys.json")
    src = load("archive/scales/PID-5/source.json")

    texts = {x["order"]: x["text"] for x in items_doc["items"]}
    rev_keyed = set(keys["reverse_keyed"])
    facets = keys["facets"]
    domains = keys["domains"]

    # ── 题项：key = -1 表示需反向计分（手册 Step 1 清单） ──────────────
    fid_of: dict[int, str] = {}
    for fname, rec in facets.items():
        for o in rec["items"]:
            fid_of[o] = fname

    items: list[Item] = []
    for order in sorted(texts):
        fname = fid_of[order]
        items.append(Item(
            order=order, id=f"pid5_{order:03d}", text=texts[order],
            dimensions=[_dim_id(fname)],
            key=(-1 if order in rev_keyed else 1),
            source_code=f"PID-5 item {order}",
            text_source="APA PID-5 manual (archive/scales/PID-5/manual.pdf)",
        ))

    # ── 维度：25 个 facet（level 1）+ 5 个域（level 2） ───────────────
    #
    # ⚠️ 两种「反向」必须分清，否则计分会静默出错——schema 校验器第一次就把
    #    这里抓出来了（声明 1 个反向题、题项却有 5 个）：
    #      · ``item.key = -1``   ⇔ 该题**原始作答需要翻转**（手册 Step 1 的 14 题）
    #      · 表格里题号后的 ``R`` ⇔ 「该题在其所属 facet 上是反向键」，比 Step 1
    #        更宽（多出 7、30），只是**证据/备注**，不是执行指令
    #    因此 ``dimension.reverse_keyed`` 必须与 ``key`` 完全一致：只列本维度内
    #    key=-1 的题；表格 R 标记写进 rubric 的 notes 备查。
    dims: list[Dimension] = []
    rubrics: dict[str, Rubric] = {}
    for fname, rec in facets.items():
        did = _dim_id(fname)
        objs = sorted(rec["items"])
        table_rk = sorted(set(rec.get("reverse_keyed") or []))
        flip = [o for o in objs if o in rev_keyed]
        dims.append(Dimension(
            id=did, name=fname, level=1,
            items=[f"pid5_{o:03d}" for o in objs],
            reverse_keyed=[f"pid5_{o:03d}" for o in flip],
        ))
        notes = f"手册 Facet Table；题数 {len(objs)}"
        if table_rk:
            notes += ("；表格 R 标记（该题在本 facet 上是反向键，仅备查）："
                      + ",".join(str(x) for x in table_rk))
        rubrics[did] = Rubric(
            id=did, label=fname, aggregation="mean", scope="items",
            of=[f"pid5_{o:03d}" for o in objs],
            notes=f"手册 Facet Table；题数 {len(objs)}")

    for dname, fnames in domains.items():
        did = _dim_id(dname)
        children = [_dim_id(f) for f in fnames]
        dims.append(Dimension(id=did, name=dname, level=2, children=children))
        rubrics[did] = Rubric(
            id=did, label=dname, aggregation="mean", scope="dimensions",
            of=children,
            notes="手册 Domain Table：域分 = 该域三个 facet 得分的均分")

    rf = keys["response_format"]
    inst = Instrument(
        instrument="PID-5",
        display_name="The Personality Inventory for DSM-5 (PID-5)—Adult",
        citation=src.get("citation") or
                 "Krueger RF, Derringer J, Markon KE, Watson D, Skodol AE. "
                 "The Personality Inventory for DSM-5 (PID-5)—Adult.",
        license=License(
            kind="copyright_permitted",
            holder="American Psychiatric Association",
            text=src["license"]["text"],
            url=src["source_url"],
            evidence="archive/scales/PID-5/source.json + PDF 页脚原文 "
                     f"(sha256 {src['sha256'][:16]}…)",
            redistribution=bool(src["license"]["redistribution"]),
            notes="APA 版权，但明文允许研究人员与临床医生无需许可复制；"
                  "收录时完整保留版权声明与推荐引用。",
        ),
        structure={
            "source": "APA DSM-5-TR Online Assessment Measures（官方公开）",
            "items": len(items),
            "facets": len(facets),
            "domains": len(domains),
            "response_format": {"points": rf["points"], "min": rf["min"],
                                "max": rf["max"], "labels": rf["labels"]},
        },
        items=items, dimensions=dims, scoring=rubrics,
        version="1.0",
        response_format=ResponseFormat(points=rf["points"], min=rf["min"],
                                       max=rf["max"], labels=rf["labels"]),
        item_order_source="archive/scales/PID-5/manual.pdf 的题项区顺序（题号 1..220）",
        provenance={
            "items": "archive/scales/PID-5/items-extracted.json（提取器 "
                     "tools/build/build_pid5_items.py；与 PID-5-BF 25/25 交叉核对）",
            "scoring_keys": "data/pid5-scoring-keys.json（生成器 "
                            "tools/build/build_pid5_scoring_keys.py；220 题恰好各归一个 facet）",
            "license": "archive/scales/PID-5/source.json",
            "manual_sha256": src["sha256"],
            "manual_bytes": src["bytes"],
        },
    )

    errs = inst.validate(require_redistributable=True)
    decl = validate_against_declaration(inst)
    print(f"题项 {len(items)}｜facet {len(facets)}｜域 {len(dimensions_facet(dims))}"
          f"｜维度合计 {len(dims)}｜计分规则 {len(rubrics)}")
    if errs:
        print("✗ schema 校验未通过：")
        for e in errs[:10]:
            print(f"  · {e}")
        return 1
    if decl:
        print("✗ 计分规则与维度声明不一致：")
        for e in decl[:10]:
            print(f"  · {e}")
        return 1
    print("✓ schema 校验通过（含 require_redistributable=True 的 D20 门）")
    print("✓ 计分规则与维度声明自洽")

    out_dir = os.path.join(ROOT, "data", "instruments")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "pid-5.json")
    payload = inst.to_dict()
    # ⚠️ 重新生成会**覆盖**掉后续步骤挂上去的字段。本项目已因此栽过三次
    #    （text-db 的翻译、L2 的 linkage、PID-5 的 norms+linkage：
    #     最后这次表现为 `test_pid5_norms_ui` 报 n=undefined、`test_chain_nav`
    #     报「PID-5 无链路条」——都是因为我重跑了这个脚本）。
    #    先把旧包里这些字段继承过来，再写新包。
    if os.path.exists(path):
        try:
            old = json.load(open(path, encoding="utf-8"))
            for k in ("norms", "norms_status", "linkage", "criteria",
                      "criteria_source", "interpretation"):
                if old.get(k) and not payload.get(k):
                    payload[k] = old[k]
                    print(f"  继承旧包的 {k}")
        except Exception:                                      # noqa: BLE001
            pass
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(f"✓ 已写出 {os.path.relpath(path, ROOT)}")
    return 0


def _dim_id(name: str) -> str:
    return "pid5_" + re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def dimensions_facet(dims: list[Dimension]) -> list[Dimension]:
    return [d for d in dims if d.level == 1]


if __name__ == "__main__":
    sys.exit(main())
