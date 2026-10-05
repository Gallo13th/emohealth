#!/usr/bin/env python3
"""排除「归档里只有非英文题文」的量表，并记录排除原因。

判定依据
========
用 ``tools/check/check_item_language.py`` 的同款语言检测：题文里出现 ≥2 个某语言的
常见功能词即判为非英文。**逐题判定，逐套决定**：

  · 全部题都是非英文 → 该量表整体排除（没有英文原题可用）
  · 只有个别题非英文 → 不在这里排除，而是回到 ``build_scales.py`` 的
    语言校验去修（英文池通常有对应的英文原题，如 IPIP 家族的瑞典语串）

为什么不自己翻译
================
翻译引入的文本没有任何归档来源，违背「界面每个数字可追到出处」。
宁可少收录一套，也不引入无法溯源的题文。

产出
====
· 被排除的量表包 → 移到 ``data/instruments/_excluded/``（保留证据，不删）
· ``data/instruments/_excluded/EXCLUSIONS.json`` → 逐套记录原因与可疑题数
"""

from __future__ import annotations

import glob
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
INST_DIR = os.path.join(ROOT, "data", "instruments")
EXCL_DIR = os.path.join(INST_DIR, "_excluded")

LANG_PATTERNS = {
    "sv": r"\b(att|och|inte|är|för|med|som|jag|vill|rätt|allt|har|kan|det)\b",
    "de": r"\b(und|nicht|ich|das|ist|mit|für|auf|eine|dass|werden)\b",
    "fr": r"\b(les|des|une|est|que|qui|pour|dans|avec|pas)\b",
    "es": r"\b(los|las|una|que|para|con|por|como|más|pero)\b",
    "nl": r"\b(het|een|niet|van|dat|met|voor|zijn|worden)\b",
    "pt": r"\b(que|para|com|por|como|mais|mas|uma|dos|das)\b",
    "fi": r"\b(ja|on|ei|se|että|kun|niin|kuin|myös)\b",
    "da": r"\b(og|ikke|jeg|det|som|med|til|på|er)\b",
    "no": r"\b(og|ikke|jeg|det|som|med|til|på|er|har)\b",
}


def lang_of(t: str) -> str | None:
    for lang, pat in LANG_PATTERNS.items():
        if len(re.findall(pat, t, re.I)) >= 2:
            return lang
    return None


def main() -> int:
    os.makedirs(EXCL_DIR, exist_ok=True)
    moved = []
    for p in sorted(glob.glob(os.path.join(INST_DIR, "*.json"))):
        name = os.path.basename(p)
        if name == "catalog.json":
            continue
        d = json.load(open(p, encoding="utf-8"))
        langs = {}
        foreign = []
        for it in d["items"]:
            lg = lang_of(it["text"])
            if lg:
                langs[lg] = langs.get(lg, 0) + 1
                foreign.append((it["order"], lg, it["text"]))
        if not foreign:
            continue
        ratio = len(foreign) / max(1, len(d["items"]))
        rec = {
            "code": d["instrument"], "file": name,
            "items": len(d["items"]), "foreign_items": len(foreign),
            "ratio": round(ratio, 3), "languages": langs,
            "samples": [{"order": o, "lang": lg, "text": t[:90]}
                        for o, lg, t in foreign[:4]],
            "reason": "归档中该量表的题文只有非英文版本，没有可溯源的英文原题；"
                      "自行翻译会引入无法追溯的内容，故不收录",
        }
        if ratio >= 0.5:
            # 过半非英文 → 排除
            shutil.move(p, os.path.join(EXCL_DIR, name))
            rec["action"] = "excluded"
            moved.append(rec)
            print(f"  排除 {d['instrument']:22} {len(foreign)}/{len(d['items'])} 题非英文 "
                  f"({','.join(f'{k}×{v}' for k, v in langs.items())})")
        else:
            rec["action"] = "kept_with_warning"
            print(f"  保留 {d['instrument']:22} {len(foreign)}/{len(d['items'])} 题非英文"
                  f"（未过半，需人工复核）")

    out = os.path.join(EXCL_DIR, "EXCLUSIONS.json")
    old = []
    if os.path.exists(out):
        old = json.load(open(out, encoding="utf-8")).get("excluded", [])
    codes = {r["code"] for r in moved}
    merged = [r for r in old if r["code"] not in codes] + moved
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({
            "policy": "归档里只有非英文题文的量表不收录（不自行翻译）",
            "checker": "tools/check/check_item_language.py / tools/build/exclude_non_english.py",
            "excluded": merged,
        }, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(f"\n本次排除 {len(moved)} 套；累计排除 {len(merged)} 套")
    print(f"记录 → {os.path.relpath(out, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
