#!/usr/bin/env python3
"""打印知乎开放平台指定文档的全文（含端点、参数、示例）。

用法：python tools/survey/read_zhihu_docs.py authorization question_answers ...
"""

from __future__ import annotations

import io
import json
import os
import sys

P = r"C:\Codes\emohealth-20260930-full\emohealth\.zhihu_docs.json"
d = json.loads(io.open(P, encoding="utf-8", errors="replace").read())
flat = {}


def walk(nodes):
    for n in nodes:
        if n.get("content"):
            flat[n.get("key")] = (n.get("title"), n["content"])
        if n.get("children"):
            walk(n["children"])


for g in d.get("data", []):
    walk([g])

want = sys.argv[1:] or ["authorization", "question_answers"]
for k in want:
    if k not in flat:
        print(f"❌ 没有文档 {k}")
        continue
    t, c = flat[k]
    print("=" * 72)
    print(f"【{k}】{t}")
    print("=" * 72)
    print(c)
    print()
