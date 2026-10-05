#!/usr/bin/env python3
"""查混合语言量表：本 OSD 自带的 ``en`` 语言池里，能否取到英文原题。

关键认识（我前后判反了两次）
============================
这些 OSD（PCI/EWS/PCOPE/PAS/TSES…）的 ``translations`` 里**同时有 en 池**，
也就是说**英文原题在归档里就有**。之前我查的是
``translations[lang][text_key]``，而这些量表的题**没有 text_key**
（题文是嵌入的 ``definition.items[*].text``）——所以查不到，误判成「不可修」。

这里改成按**条目 id / 顺序**去 en 池取值。取到就说明可修，取不到才排除。
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

LANGS = {
    "sv": r"\b(att|och|inte|är|för|med|som|jag|vill|rätt|allt|har|kan|det)\b",
    "de": r"\b(und|nicht|ich|das|ist|mit|für|auf|eine|dass|werden)\b",
    "fr": r"\b(les|des|une|est|que|qui|pour|dans|avec|pas)\b",
    "es": r"\b(los|las|una|que|para|con|por|como|más|pero)\b",
    "pt": r"\b(que|para|com|por|como|mais|mas|uma|dos|das)\b",
    "nl": r"\b(het|een|niet|van|dat|met|voor|zijn|worden)\b",
}


def lang_of(t):
    for lg, pat in LANGS.items():
        if len(re.findall(pat, t, re.I)) >= 2:
            return lg
    return None


def main() -> int:
    for code in ["PCI", "PCOPE", "EWS", "PAS", "AIDEP", "TSES", "RNSS", "PROCR", "SRS"]:
        hits = glob.glob(os.path.join(OSD_DIR, "**", code + ".osd"), recursive=True)
        if not hits:
            continue
        raw = json.load(open(hits[0], encoding="utf-8"))
        defn = raw.get("definition") or {}
        items = defn.get("items") or {}
        seq, ids = [], []
        if isinstance(items, dict):
            for k, v in items.items():
                if isinstance(v, dict):
                    seq.append(v)
                    ids.append(k)
        else:
            for v in items:
                if isinstance(v, dict):
                    seq.append(v)
                    ids.append(v.get("id"))
        trans = raw.get("translations") or {}
        en_pools = {k: v for k, v in trans.items()
                    if isinstance(v, dict) and k.lower().startswith("en")}
        print("=" * 74)
        print(f"{code}: {len(seq)} 题；语言池 {sorted(trans)}；"
              f"en 池条目 {sum(len(v) for v in en_pools.values())}")

        # 逐题：非英文的能否在 en 池里找到
        fix = miss = 0
        for i, it in enumerate(seq):
            t = (it.get("text") or "").strip()
            if not t or not lang_of(t):
                continue
            iid = it.get("id") or ids[i] or ""
            key = (it.get("text_key") or "").strip()
            got = ""
            for pool in en_pools.values():
                for cand in (iid, key, key.replace("ipip_", ""),
                             str(i + 1), f"item{i + 1}"):
                    if cand and cand in pool and isinstance(pool[cand], str):
                        got = pool[cand]
                        break
                if got:
                    break
            if got:
                fix += 1
            else:
                miss += 1
            if i < 6 or (fix + miss) <= 3:
                print(f"   第 {i + 1:3} 题 [{lang_of(t)}] id={iid[:22]:22} "
                      f"{'→ ' + got[:52] if got else '→ (en 池无对应)'}")
        print(f"   小结：可修 {fix} 题，无英文 {miss} 题")
    return 0


if __name__ == "__main__":
    sys.exit(main())
