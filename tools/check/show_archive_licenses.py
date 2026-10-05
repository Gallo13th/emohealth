#!/usr/bin/env python3
"""列出 DSM-5-TR 各册归档记录里的授权原文，逐册核对。"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
paths = sorted(glob.glob(os.path.join(ROOT, "archive", "scales", "DSM5TR-*", "source.json")))
print(f"归档 {len(paths)} 册\n")
for p in paths:
    with open(p, encoding="utf-8") as fh:
        d = json.load(fh)
    lic = d.get("license", {})
    txt = (lic.get("text") or "").strip()
    print(f"{d['code']:22} {d['bytes']:>7} 字节")
    print(f"    title      {d['title'][:88]}")
    print(f"    授权原文   {txt[:150] or '（未提取到）'}")
    print(f"    可再分发   {lic.get('redistribution')}")
    print()
