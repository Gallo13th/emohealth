#!/usr/bin/env python3
"""查清：文本库的 `zh` 从哪来、第 23 题现状如何、那 4 条确认问题在哪一层。

为什么必须先查
==============
若 `build_text_db.py` 从某个**源资产**取中译，那么直接改 `data/text-db/text-db.json`
会在下次重跑时被覆盖——必须改**源头**。反之若它是权威源，则直接改它。
"""

from __future__ import annotations

import io
import json
import os
import re
import sys

sys.path.insert(0, r"C:\Codes\emohealth-20260930-full\emohealth\tools")
from _root import find_root  # noqa: E402
ROOT = str(find_root())

print("=== build_text_db.py 里与 zh 相关的行 ===")
src = io.open(os.path.join(ROOT, "tools", "build", "build_text_db.py"),
              encoding="utf-8").read()
for i, ln in enumerate(src.split("\n"), 1):
    if re.search(r"zh_source|zh\"|'zh'|SCAFFOLD|load_json|json.load|open\(", ln):
        print(f"  L{i}: {ln.strip()[:96]}")

print("\n=== 第 23 题在文本库里的现状 ===")
db = json.load(io.open(os.path.join(ROOT, "data", "text-db", "text-db.json"),
                       encoding="utf-8"))
hits = [(k, v) for k, v in db["entries"].items()
        if "painkillers" in ((v.get("en") or "").lower())]
print(f"  含 painkillers 的条目：{len(hits)}")
for k, v in hits:
    en = v.get("en") or ""
    zh = v.get("zh") or ""
    print(f"  EN[{len(en)}]: {en[:120]}")
    print(f"  ZH[{len(zh)}]: {zh[:120]}")
    print(f"  源: {v.get('zh_source')}")

print("\n=== 那 4 条确认问题在文本库里的定位 ===")
TARGETS = [
    "Make demands on others.",
    "Methamphetamine (like speed)",
    "You need to step on some toes",
    "Methamphetamine",
]
for t in TARGETS:
    found = [(k, v) for k, v in db["entries"].items()
             if t.lower() in ((v.get("en") or "").lower())]
    print(f"  「{t}」→ {len(found)} 条")
    for k, v in found:
        print(f"      EN: {str(v.get('en'))[:70]}")
        print(f"      ZH: {str(v.get('zh'))[:70]}")

print("\n=== 文本库是不是生成物（看它的 stats/生成者字段）===")
for k in list(db)[:8]:
    if k != "entries":
        print(f"  {k}: {str(db[k])[:220]}")
