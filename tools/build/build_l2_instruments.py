#!/usr/bin/env python3
"""为 DSM-5-TR Level 2 各册生成量表包（``data/instruments/dsm5tr-l2-*.json``）。

每册都是**单一维度**（域）的总分，计分口径为**求和**（手册表格标题即
「Total/Partial Raw Score」→ 总分；睡眠册另有 T 分数，属常模转换，本轮不做）。
躯体册（0–2）改编自公有领域的 PHQ-15，其计分同为求和。

授权：逐册取 ``source.json`` 里的原文（页脚或正文『Rights granted』段）。
**不通过 ``require_redistributable`` 门的不写文件。**
"""

from __future__ import annotations

import glob
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


def load(p: str) -> dict:
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def main() -> int:
    files = sorted(glob.glob(os.path.join(ROOT, "archive", "scales",
                                          "DSM5TR-L2-*", "items-extracted.json")))
    print(f"找到 {len(files)} 册已提取题项的 Level 2 量表\n")
    total_bad = 0
    for f in files:
        code = os.path.basename(os.path.dirname(f))
        doc = load(f)
        src = load(os.path.join(os.path.dirname(f), "source.json"))
        rf = doc["response_format"]
        dim_name = doc.get("dimension") or src["title"]
        # Substance 的题号是字母 a–j，维度名补上以免与其它册混
        if "dimension" not in doc:
            dim_name = {"DSM5TR-L2-Mania": "Mania",
                        "DSM5TR-L2-Repetitive": "Repetitive Thoughts and Behaviors",
                        "DSM5TR-L2-Substance": "Substance Use"}[code]
        dim_id = "l2_" + re.sub(r"[^a-z0-9]+", "_", dim_name.lower()).strip("_")

        items = []
        for x in doc["items"]:
            it = Item(order=x["order"],
                      id=f"{code.lower().replace('-', '')}_{x['order']:02d}",
                      text=x["text"], dimensions=[dim_id], key=1,
                      source_code=(f"{code} item {x.get('letter') or x['order']}"),
                      text_source=f"APA {code} manual")
            # 作答指示语：不是量表题项，界面应作为引导语呈现（不参与计分）
            if x.get("text_kind") == "instruction":
                it.kind = "instruction"
            items.append(it)
        ids = [x.id for x in items]
        dims = [Dimension(id=dim_id, name=dim_name, level=1, items=ids,
                          reverse_keyed=[])]
        # ── 计分口径**逐册不同**，不能一律按 sum（见 data/criteria/dsm5tr-l2.json）
        # ⚠️ Substance 册原文明确：Scores on the individual items should be
        #    interpreted independently because each item inquires about the use of a
        #    distinct substance. —— **它没有总分**。我最初按 sum 处理是错的，
        #    「10 项加起来 = 12 分」在临床上没有意义。改用 count_true（>0 的项数）。
        agg = "count_true" if code == "DSM5TR-L2-Substance" else "sum"
        note = ("手册『Scoring and Interpretation』：各题原始分求和"
                if agg == "sum" else
                "手册原文：各项**独立**解释（每项对应一种物质）；"
                ">0 的项数表示严重度与复杂度，**不求和**")
        rubrics = {dim_id: Rubric(
            id=dim_id, label=dim_name, aggregation=agg, scope="items", of=ids,
            notes=note)}

        lic = src["license"]
        # 统一标签为空时（Mania / Repetitive 每题的选项文本各不相同，
        # 挂在 provenance.item_options 上），用分值数字占位——
        # ResponseFormat 要求 labels 非空且与 points 等长。
        labels = rf.get("labels") or [str(rf["min"] + i)
                                      for i in range(rf["max"] - rf["min"] + 1)]
        inst = Instrument(
            instrument=code,
            display_name=src["title"],
            citation=f"American Psychiatric Association. {src['title']}.",
            license=License(
                kind="copyright_permitted",
                holder=lic.get("holder", "American Psychiatric Association"),
                text=lic["text"],
                url=src["source_url"],
                evidence=f"archive/scales/{code}/source.json"
                         f"（sha256 {src['sha256'][:16]}…）",
                redistribution=bool(lic.get("redistribution")),
                notes="APA 版权，允许研究人员/临床医生无需许可复制使用。",
            ),
            structure={
                "source": "APA DSM-5-TR Online Assessment Measures（官方公开）",
                "items": len(items), "dimensions": 1,
                "response_format": {"points": rf["points"], "min": rf["min"],
                                    "max": rf["max"], "labels": rf["labels"]},
                "window": doc.get("window", ""),
            },
            items=items, dimensions=dims, scoring=rubrics,
            version="1.0",
            response_format=ResponseFormat(points=rf["points"], min=rf["min"],
                                           max=rf["max"], labels=labels),
            item_order_source=f"archive/scales/{code}/manual.pdf 题项顺序",
            provenance={
                "items": f"archive/scales/{code}/items-extracted.json"
                         "（提取器 tools/build/build_l2_items.py 或 build_l2_items_rest.py）",
                "license": f"archive/scales/{code}/source.json",
                "reverse_keyed": doc.get("reverse_keyed", []),
                "manual_sha256": src["sha256"],
            },
        )
        # 每题选项文本（Mania 的选项是整句陈述；Repetitive 各题的锚点不同）。
        # ⚠️ 曾经只写 `provenance.item_options`——那是**错的位置**：按 schema 读
        #    `items[].options` 的消费者拿不到选项组，界面会渲染不出或渲染错
        #    （2026-10-04 定为缺陷④）。规范位置是 `items[].options`。
        #    `Item` 数据类没有 `options` 字段，`to_dict()` 会丢掉，所以在这里
        #    先记下来，等 `to_dict()` 之后按 order 补进题项字典（`kind` 同理）。
        per_item_options = {x["order"]: x["options"]
                            for x in doc["items"] if "options" in x}
        # 锚点的来源说明（如睡眠册第 8 题「Very Poor…Very good」逐字出自手册哪一行）。
        # 必须一并带出，否则「从缓存重建」会缺这个字段、与现场提取的结果不等价。
        per_item_evidence = {x["order"]: x["options_evidence"]
                             for x in doc["items"] if x.get("options_evidence")}

        errs = inst.validate(require_redistributable=True)
        decl = validate_against_declaration(inst)
        flag = "✓" if not errs and not decl else "✗"
        print(f"  {flag} {code:24} {len(items):3} 题 · 记分 {rf['min']}–{rf['max']} · "
              f"反向 {len(doc.get('reverse_keyed', []))} · 授权 "
              f"{inst.license.kind}/{inst.license.redistribution}")
        for e in (errs + decl)[:3]:
            print(f"        · {e}")
            total_bad += 1
        if errs or decl:
            continue
        out = os.path.join(ROOT, "data", "instruments",
                           code.lower() + ".json")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        payload = inst.to_dict()
        # ⚠️ 重新生成会**覆盖**掉后续步骤挂上去的字段（linkage 由
        #    tools/build/attach_linkage.py 挂）。这一坑我已经踩过一次
        #    （重跑 L2 生成 → L2 的链路条消失，表现为「回不到 Level 1」）。
        #    所以这里先把旧包里这些字段继承过来，再写新包。
        out_key = os.path.join(ROOT, "data", "instruments",
                               code.lower() + ".json")
        if os.path.exists(out_key):
            try:
                old = json.load(open(out_key, encoding="utf-8"))
                for k in ("linkage", "norms", "norms_status"):
                    if old.get(k) and not payload.get(k):
                        payload[k] = old[k]
            except Exception:                                # noqa: BLE001
                pass
        # 判读口径（分带/分界/逐项）：来自 data/criteria/dsm5tr-l2.json，
        # 全部源自各册手册的 Scoring and Interpretation 段。
        crit_path = os.path.join(ROOT, "data", "criteria", "dsm5tr-l2.json")
        if os.path.exists(crit_path):
            crit = json.load(open(crit_path, encoding="utf-8"))
            c = (crit.get("instruments") or {}).get(code)
            if c:
                payload["criteria"] = c
                payload["criteria_source"] = crit.get("source", "")
        # ⚠️ `Item` 数据类没有 `kind` 字段，塞进去会被丢弃。作答指示语要靠它
        #    与真实题项区分（文本库据此放行「中译=英文」的情况），所以在
        #    to_dict() **之后**按 order 补进题项字典。
        instr_orders = {x["order"] for x in doc["items"]
                        if x.get("text_kind") == "instruction"}
        if instr_orders:
            for row in payload.get("items", []):
                if row.get("order") in instr_orders:
                    row["kind"] = "instruction"
            payload.setdefault("provenance", {})["instructions"] = sorted(instr_orders)
        # 每题选项 → **规范位置 `items[].options`**（缺陷④，2026-10-04）
        # ⚠️ 2026-10-04 收口：`provenance.item_options` 的**兼容镜像已删除**。
        #    界面（`ui/index.html`）与本打包器（`tools/ui/build_ui_instruments.py`）
        #    都已切到 `items[].options`，镜像的存在理由消失；留着就是第二个真相源。
        #    `tools/check/check_dsm_item_text.py` 会断言镜像**不存在**。
        if per_item_options:
            for row in payload.get("items", []):
                if row.get("order") in per_item_options:
                    row["options"] = per_item_options[row["order"]]
                    if row["order"] in per_item_evidence:
                        row["options_evidence"] = per_item_evidence[row["order"]]
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=1)
            fh.write("\n")

    print(f"\n{'✗ 有 ' + str(total_bad) + ' 个问题' if total_bad else '✅ 全部生成'}")
    return 1 if total_bad else 0


if __name__ == "__main__":
    sys.exit(main())
