#!/usr/bin/env python3
"""验证：英文池对那几道瑞典语/非英文题的同一个 key，是否给出英文原题。

这是「修」与「排除」的分界：只有英文池里确实有对应英文，才能修；
否则只能排除该量表（翻译引入的内容无法溯源）。
"""

from __future__ import annotations

import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
OSD_DIR = os.path.join(ROOT, "archive", "ipip", "data", "OpenScales")
TRANS = os.path.join(OSD_DIR, "scales", "ipip", "translations")


def main() -> int:
    en = {}
    for p in glob.glob(os.path.join(TRANS, "*_en.json")):
        d = json.load(open(p, encoding="utf-8"))
        if isinstance(d, dict):
            en.update({k: v for k, v in d.items() if isinstance(v, str)})

    for code, order, expect in [("IPIP-BFAS", 54, "just right"),
                                ("IPIP-HEXACO", 187, "just right"),
                                ("IPIP-BFAS", 77, "personality")]:
        osd = glob.glob(os.path.join(OSD_DIR, "**", code + ".osd"), recursive=True)[0]
        raw = json.load(open(osd, encoding="utf-8"))
        items = (raw["definition"].get("items") or {})
        if isinstance(items, dict):
            seq = [v for v in items.values() if isinstance(v, dict)]
        else:
            seq = [v for v in items if isinstance(v, dict)]
        it = seq[order - 1]
        key = (it.get("text_key") or "").strip()
        bare = key[len("ipip_"):] if key.startswith("ipip_") else key
        print("=" * 72)
        print(f"{code} 第 {order} 题")
        print(f"  text_key     : {key}")
        print(f"  嵌入 text    : {(it.get('text') or '(空)')[:70]}")

        # 本 OSD 的 translations 池里各语言给出什么
        for lang, pool in (raw.get("translations") or {}).items():
            if isinstance(pool, dict) and (key in pool or bare in pool):
                v = pool.get(key) or pool.get(bare)
                if isinstance(v, str) and any(x in v.lower() for x in ("vill", "har inte", "just right", "personality")):
                    print(f"  translations[{lang}]: {v[:70]}")
        print(f"  英文池 ipip_master_en: {en.get(key) or en.get(bare) or '(无)'}")
        hit = en.get(key) or en.get(bare) or ""
        print(f"  → 判定：{'✅ 有英文可修' if expect in hit.lower() else '❌ 英文池未覆盖，只能排除'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
