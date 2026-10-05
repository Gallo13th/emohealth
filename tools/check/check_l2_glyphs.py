#!/usr/bin/env python3
"""确认 Level 2 各册的题面与选项文本里没有残留的「选择框」字形。"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()


def bad_chars(s: str) -> list[str]:
    out = []
    for ch in s:
        o = ord(ch)
        if 0xE000 <= o <= 0xF8FF or o in (0x2030, 0x25A1, 0x2610, 0x2611):
            out.append(f"U+{o:04X}")
    return out


total = 0
for p in sorted(glob.glob(os.path.join(ROOT, "archive", "scales",
                                       "DSM5TR-L2-*", "items-extracted.json"))):
    code = os.path.basename(os.path.dirname(p))
    d = json.load(open(p, encoding="utf-8"))
    hits = []
    for it in d["items"]:
        for where, txt in [("题干", it["text"])] + \
                [("选项", o["text"]) for o in it.get("options", [])]:
            b = bad_chars(txt)
            if b:
                hits.append((it["order"], where, b, txt[:60]))
    print(f"  {code:24} 残留 {len(hits)} 处")
    for o, w, b, t in hits[:3]:
        print(f"      第 {o} 题 {w}：{','.join(b)}  {t}")
    total += len(hits)
print(f"\n合计残留 {total} 处" + ("（应为 0）" if total else " ✅"))
