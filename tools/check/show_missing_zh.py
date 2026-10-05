#!/usr/bin/env python3
"""列出最后没中译的条目，看是哪些、为什么被跳过。"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
db = json.load(open(os.path.join(ROOT, "data", "text-db", "text-db.json"),
                    encoding="utf-8"))
E = db["entries"]
missing = {k: e for k, e in E.items() if not e.get("zh")}
print(f"还缺 {len(missing)} 条：\n")
for k, e in missing.items():
    print(f"  key: {k[:96]!r}")
    print(f"       en: {e['en'][:96]!r}")
    print(f"       instruments: {e.get('instruments')}")
    # 找译文文件里有没有它、值是什么
    for p in glob.glob(os.path.join(ROOT, "data/text-db/pending/*-zh.json")):
        try:
            rows = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        for r in rows:
            if isinstance(r, dict) and str(r.get("key", "")) == k:
                print(f"       译文文件 {os.path.basename(p)}: zh={r.get('zh')!r}")
                break
    print()
