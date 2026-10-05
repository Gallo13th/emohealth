#!/usr/bin/env python3
"""查每套「有非英文题项」的量表：归档里是否存在**英文**题文可用。

判断分两路
==========
· IPIP 家族：题文由 ``translations`` 池按 key 提供，池里可能同时有几十种语言。
  若同一 key 在英文池里有值，就能**修**（换成英文原题）。
· 其它量表（EWS/PCI/PCOPE 等）：``definition.items[*].text`` 是**嵌入**的题文，
  通常只有一种语言。若嵌入的就是德语/西语，归档里没有英文 —— 只能**排除**该量表，
  不能翻译（翻译引入的内容无法溯源，违反硬规则）。

本脚本只做判定与报告，不动数据。
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
OSD_DIR = os.path.join(ROOT, "archive", "ipip", "data", "OpenScales")
TRANS_DIR = os.path.join(OSD_DIR, "scales", "ipip", "translations")

LANG_PATTERNS = {
    "sv": r"\b(att|och|inte|är|för|med|som|jag|vill|rätt|allt|har|kan|det)\b",
    "de": r"\b(und|nicht|ich|das|ist|mit|für|auf|eine|dass|werden)\b",
    "fr": r"\b(les|des|une|est|que|qui|pour|dans|avec|pas)\b",
    "es": r"\b(los|las|una|que|para|con|por|como|más|pero)\b",
    "nl": r"\b(het|een|niet|van|dat|met|voor|zijn|worden)\b",
    "pt": r"\b(que|para|com|por|como|mais|mas|uma|dos|das)\b",
    "fi": r"\b(ja|on|ei|se|että|kun|niin|kuin|myös)\b",
}


def is_foreign(t: str) -> bool:
    for lang, pat in LANG_PATTERNS.items():
        if len(re.findall(pat, t, re.I)) >= 2:
            return True
    return False


def find_osd(code: str) -> str | None:
    hits = glob.glob(os.path.join(OSD_DIR, "**", code + ".osd"), recursive=True)
    return hits[0] if hits else None


def main() -> int:
    # 英文池：合并所有 *_en.json
    en_pool = {}
    for p in glob.glob(os.path.join(TRANS_DIR, "*_en.json")):
        d = json.load(open(p, encoding="utf-8"))
        if isinstance(d, dict):
            en_pool.update({k: v for k, v in d.items() if isinstance(v, str)})
    print(f"英文池条目：{len(en_pool)}（来自 {len(glob.glob(os.path.join(TRANS_DIR, '*_en.json')))} 个文件）\n")

    rows = []
    for p in sorted(glob.glob(os.path.join(ROOT, "data", "instruments", "*.json"))):
        if os.path.basename(p) == "catalog.json":
            continue
        d = json.load(open(p, encoding="utf-8"))
        bad = [it for it in d["items"] if is_foreign(it["text"])]
        if not bad:
            continue
        osd = find_osd(d["instrument"])
        raw = json.load(open(osd, encoding="utf-8")) if osd else {}
        defn = (raw.get("definition") or {}) if raw else {}
        items = defn.get("items") or {}
        # ⚠️ definition.items 有**两种形态**：dict（key → 题）与 list（顺序题表）。
        #    统一成「按顺序的题对象列表」再统计，否则 list 形态直接 AttributeError。
        if isinstance(items, dict):
            item_list = [v for v in items.values() if isinstance(v, dict)]
        elif isinstance(items, list):
            item_list = [v for v in items if isinstance(v, dict)]
        else:
            item_list = []
        embedded = sum(1 for v in item_list if (v.get("text") or "").strip())
        tpool = {}
        for v in (raw.get("translations") or {}).values():
            if isinstance(v, dict):
                tpool.update(v)
        # 这些坏题能否在英文池里找到替代：看原始题条目的 text_key
        fixable = 0
        for it in bad:
            idx = it["order"] - 1
            if 0 <= idx < len(item_list):
                key = (item_list[idx].get("text_key") or "").strip()
                if key and (key in en_pool
                            or key[len("ipip_"):] in en_pool
                            or key in tpool or key[len("ipip_"):] in tpool):
                    fixable += 1
        rows.append({
            "code": d["instrument"], "bad": len(bad), "items": len(d["items"]),
            "embedded_text": embedded, "pool_entries": len(tpool),
            "en_fixable_guess": fixable,
        })

    print(f"{'量表':26} {'坏题':>4} {'总题':>4} {'嵌入题文':>8} {'翻译池':>6} {'英文可修?':>9}")
    for r in sorted(rows, key=lambda x: -x["bad"]):
        print(f"{r['code']:26} {r['bad']:4} {r['items']:4} "
              f"{r['embedded_text']:8} {r['pool_entries']:6} "
              f"{('是(' + str(r['en_fixable_guess']) + ')') if r['en_fixable_guess'] else '否':>9}")
    print(f"\n受影响 {len(rows)} 套")
    return 0


if __name__ == "__main__":
    sys.exit(main())
