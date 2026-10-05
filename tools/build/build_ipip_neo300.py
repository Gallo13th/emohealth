#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建规范的 IPIP-NEO-300 数据集。

Phase 1 交叉校验的结论：没有任何单一来源是完整的，必须合并两处：

  A. 官方问卷 docx（`IPIP-NEO-300_Questionnaire_printable.docx`）
     - 提供 **施测顺序**（30 facet 交错循环，每 30 题覆盖全部 facet 一次）
     - 提供 **缺失题文本**（其第 70 题正是机读源坏引用 ipip_E11 的正文）

  B. OpenScales 机读包（`IPIP-NEO.osd` + `ipip_item_codes.json`）
     - 提供 **facet 归属**、**计分键（含 148 个反向题）**、**每 facet 的 Cronbach's α**

已知缺陷（本脚本显式修正）：
  1. `ipip_E11` 是悬空引用——`code_to_text` 中不存在该键（只有 E110/E111/...）。
     对应题目即官方问卷 #70。
  2. `text_key` 形如 `ipip_H1157`，需剥掉 `ipip_` 前缀才能查表；部分键含尾随空格。
  3. OpenScales 的 `README.md` 报 `Items: 0`，属元数据错误，实际 300 题齐全。

输出：`data/ipip-neo-300.json`（含逐题溯源与合并日志）
"""
from __future__ import annotations

import json
import os
import sys
import re
import unicodedata
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
SCORING_DIR = os.path.join(ROOT, "archive/datasets/osf-johnson/scoring")
OSD_DIR = os.path.join(ROOT, "archive/ipip/data/OpenScales/scales/ipip")
OUT = os.path.join(ROOT, "data/ipip-neo-300.json")

DOCX = os.path.join(SCORING_DIR, "IPIP-NEO-300_Questionnaire_printable.docx")
OSD = os.path.join(OSD_DIR, "IPIP-NEO", "IPIP-NEO.osd")
CODES = os.path.join(OSD_DIR, "ipip_item_codes.json")

# IPIP-NEO-300 的施测循环：官方问卷每 30 题覆盖全部 facet 一次。
# 该顺序由问卷本身推导（见 build 日志），不是外部假设。
CYCLE_LEN = 30
ITEMS_PER_FACET = 10
EXPECTED_ITEMS = 300


def norm(s: str) -> str:
    """归一化用于比对：去标点、去空白、小写、统一引号。"""
    s = unicodedata.normalize("NFKD", s or "")
    s = s.replace("\u201c", '"').replace("\u201d", '"').replace("\u2019", "'")
    return re.sub(r"[^a-z]", "", s.lower())


def read_docx_items(path: str) -> list[tuple[int, str]]:
    """从官方问卷 docx 抽取 (题号, 题干)。

    版面模式：题号 → 题干 → 五个选项圈（'O'）。
    """
    z = zipfile.ZipFile(path)
    xml = z.read("word/document.xml").decode("utf-8")
    lines = [l.strip() for l in re.sub(r"<[^>]+>", "\n", xml).split("\n") if l.strip()]
    items: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        if re.fullmatch(r"\d{1,3}", line) and i + 1 < len(lines):
            nxt = lines[i + 1]
            if nxt != "O" and not re.fullmatch(r"\d{1,3}", nxt):
                items.append((int(line), nxt))
    return items


def read_osd(path: str, codes: dict[str, str]):
    """从 .osd 读取题目、facet 归属与计分键。"""
    d = json.load(open(path, encoding="utf-8"))["definition"]
    scoring = {k: v for k, v in d["scoring"].items() if k.endswith("_sum")}

    id2facet: dict[str, str] = {}
    id2key: dict[str, int] = {}
    for facet_key, spec in scoring.items():
        facet = facet_key[: -len("_sum")]
        for item_id, key in spec["items"].items():
            id2facet[item_id] = facet
            id2key[item_id] = key

    alphas: dict[str, float | None] = {}
    for facet_key, spec in scoring.items():
        m = re.search(r"alpha = ([0-9.]+)", spec.get("description", ""))
        alphas[facet_key[: -len("_sum")]] = float(m.group(1)) if m else None

    rows = []
    for it in d["items"]:
        tk = it["text_key"]
        code = (tk[len("ipip_"):] if tk.startswith("ipip_") else tk).strip()
        rows.append({
            "id": it["id"],
            "code": code,
            "text_master": codes.get(code),   # 可能为 None（悬空引用）
            "facet": id2facet.get(it["id"]),
            "key": id2key.get(it["id"]),
        })
    return rows, alphas, scoring


def main() -> int:
    codes = json.load(open(CODES, encoding="utf-8"))["code_to_text"]
    doc_items = read_docx_items(DOCX)
    osd_rows, alphas, scoring = read_osd(OSD, codes)

    log: list[str] = []
    log.append(f"docx 解析题目数：{len(doc_items)}")
    log.append(f"osd  解析题目数：{len(osd_rows)}")

    # --- 1. 文本精确匹配，建立 docx → osd 的映射 ---
    by_norm: dict[str, list[int]] = {}
    for idx, r in enumerate(osd_rows):
        if r["text_master"]:
            by_norm.setdefault(norm(r["text_master"]), []).append(idx)

    mapping: dict[int, int] = {}          # docx 题号 -> osd 下标
    for n, text in doc_items:
        cand = by_norm.get(norm(text), [])
        if len(cand) == 1:
            mapping[n] = cand[0]

    exact = len(mapping)
    log.append(f"文本精确匹配：{exact} / {len(doc_items)}")

    # --- 2. 结构性补全：用 facet 循环位置推定剩余项 ---
    # docx 第 n 题的循环位置 = (n-1) % 30；该位置的 facet 由已匹配项确定。
    pos_facet: dict[int, str] = {}
    for n, idx in mapping.items():
        pos_facet[(n - 1) % CYCLE_LEN] = osd_rows[idx]["facet"]

    missing_positions = [p for p in range(CYCLE_LEN) if p not in pos_facet]
    if missing_positions:
        log.append(f"⚠️ 循环中未确定的 facet 位置：{missing_positions}")

    # 每个 facet 内的 osd 题目，按 .osd 出现顺序排列
    facet_items: dict[str, list[int]] = {}
    for idx, r in enumerate(osd_rows):
        facet_items.setdefault(r["facet"], []).append(idx)

    # 统计每个 facet 已被精确匹配占用的槽位
    facet_used: dict[str, set[int]] = {}
    for n, idx in mapping.items():
        f = osd_rows[idx]["facet"]
        slot = facet_items[f].index(idx)
        facet_used.setdefault(f, set()).add(slot)

    repaired = 0
    order_slots: dict[str, int] = {}
    for n, text in doc_items:
        if n in mapping:
            continue
        pos = (n - 1) % CYCLE_LEN
        facet = pos_facet.get(pos)
        if facet is None:
            continue
        # 该 facet 内第几个空闲槽位
        used = facet_used.setdefault(facet, set())
        nxt = next(s for s in range(ITEMS_PER_FACET) if s not in used)
        used.add(nxt)
        idx = facet_items[facet][nxt]
        mapping[n] = idx
        repaired += 1
        master = osd_rows[idx]["text_master"]
        if master:
            log.append(f"措辞变体：docx #{n}「{text}」 vs 主表「{master}」"
                       f"（facet={facet}，osd={osd_rows[idx]['id']}）")
        else:
            log.append(f"修复机读缺陷：docx #{n} 补齐 osd {osd_rows[idx]['id']}"
                       f" 的悬空引用 key={osd_rows[idx]['code']}（facet={facet}）")

    log.append(f"结构补全项：{repaired}")

    # --- 3. 组装 ---
    items = []
    for n, doc_text in sorted(doc_items):
        idx = mapping.get(n)
        if idx is None:
            log.append(f"❌ 无法映射 docx #{n}: {doc_text}")
            continue
        r = osd_rows[idx]
        items.append({
            "order": n,
            "id": r["id"],
            "code": r["code"],
            "facet": r["facet"],
            "key": r["key"],
            "text": doc_text,                                  # 施测用语（官方问卷）
            "text_master": r["text_master"],                    # IPIP 主表用语（可能为 None）
            "text_source": "questionnaire_docx" if r["text_master"] and norm(r["text_master"]) == norm(doc_text)
                           else "questionnaire_docx(差异化)" if r["text_master"] else "questionnaire_docx(补全机读缺陷)",
        })

    # --- 4. 校验 ---
    problems = []
    if len(items) != EXPECTED_ITEMS:
        problems.append(f"题目数 {len(items)} != {EXPECTED_ITEMS}")
    facet_counts: dict[str, int] = {}
    for it in items:
        facet_counts[it["facet"]] = facet_counts.get(it["facet"], 0) + 1
    if len(facet_counts) != 30:
        problems.append(f"facet 数 {len(facet_counts)} != 30")
    bad = {f: c for f, c in facet_counts.items() if c != ITEMS_PER_FACET}
    if bad:
        problems.append(f"facet 题数异常：{bad}")
    n_rev = sum(1 for it in items if it["key"] is not None and it["key"] < 0)
    missing_text = [it["order"] for it in items if not it["text"]]

    payload = {
        "instrument": "IPIP-NEO-300",
        "version": "1.0",
        "citation": "Goldberg, L. R. (1999). A broad-bandwidth, public domain, personality inventory "
                    "measuring the lower-level facets of several five-factor models. In Personality "
                    "Psychology in Europe (Vol. 7, pp. 7-28). Tilburg University Press.",
        "license": "Public Domain",
        "license_evidence": "https://www.ipip.ori.org/newPermission.htm — "
                            "'permission has already been automatically granted for any person to use "
                            "IPIP items, scales, and inventories for any purpose, commercial or non-commercial'",
        "structure": {
            "domains": 5,
            "facets": len(facet_counts),
            "items": len(items),
            "items_per_facet": ITEMS_PER_FACET,
            "reverse_keyed_items": n_rev,
            "administration_order": "interleaved_30_facet_cycle",
            "estimated_duration_min": 35,
        },
        "facet_alphas": alphas,
        "sources": {
            "administration_form": "archive/datasets/osf-johnson/scoring/IPIP-NEO-300_Questionnaire_printable.docx",
            "machine_readable_structure": "archive/ipip/data/OpenScales/scales/ipip/IPIP-NEO/IPIP-NEO.osd",
            "item_text_master": "archive/ipip/data/OpenScales/scales/ipip/ipip_item_codes.json",
            "scoring_keys": "archive/datasets/osf-johnson/scoring/IPIP-NEO-300_ScoringTool.xlsx",
            "norms": "archive/datasets/osf-johnson/scoring/uk-norms/",
        },
        "known_defects_repaired": [
            "osd text_key 'ipip_E11' 为悬空引用；其正文由官方问卷 #70 提供",
            "text_key 需剥离 'ipip_' 前缀且部分含尾随空格",
            "OpenScales README 报 'Items: 0' 为元数据错误",
        ],
        "validation": {
            "items": len(items),
            "facets": len(facet_counts),
            "reverse_keyed": n_rev,
            "items_missing_text": missing_text,
            "problems": problems,
        },
        "build_log": log,
        "items": items,
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)

    print(json.dumps(payload["validation"], ensure_ascii=False, indent=1))
    print("\n".join(log))
    print(f"\nwrote {OUT}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
