#!/usr/bin/env python3
"""读知乎开放平台文档 API，提取鉴权方式与可用接口。

知乎开发者站的文档是 umi SPA，内容在 `/console/api/v3/docs` 的 JSON 里
（`data[].children[].content` 是 markdown）。桌面/移动页都 403，这条路通。
"""

from __future__ import annotations

import io
import json
import os
import re
import sys
import urllib.request

OUT = r"C:\Codes\emohealth-20260930-full\emohealth\.zhihu_docs.json"
URL = "https://developer.zhihu.com/console/api/v3/docs"

if os.path.exists(OUT):
    raw = io.open(OUT, encoding="utf-8", errors="replace").read()
else:
    req = urllib.request.Request(URL, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0",
        "Accept": "application/json",
        "Referer": "https://developer.zhihu.com/docs",
    })
    with urllib.request.urlopen(req, timeout=40) as r:
        raw = r.read().decode("utf-8")
    io.open(OUT, "w", encoding="utf-8").write(raw)

d = json.loads(raw)
print(f"success={d.get('success')} 顶层分组 {len(d.get('data', []))} 个")

flat = []


def walk(nodes, path):
    for n in nodes:
        title = n.get("title") or ""
        key = n.get("key") or ""
        if n.get("content"):
            flat.append((path + " / " + title, key, n["content"]))
        if n.get("children"):
            walk(n["children"], path + " / " + title)


for g in d.get("data", []):
    walk([g], g.get("title", ""))

print(f"含正文的文档节点 {len(flat)} 个\n")
print("目录：")
for t, k, c in flat:
    print(f"  [{k}] {t}  ({len(c)} 字)")

# 输出鉴权文档
for t, k, c in flat:
    if k == "authorization":
        print("\n" + "=" * 70)
        print("鉴权文档全文：")
        print("=" * 70)
        print(c[:4000])
        break

# 找 API 端点线索
print("\n" + "=" * 70)
print("文档里出现的 URL / 端点：")
urls = set()
for t, k, c in flat:
    for m in re.finditer(r"https?://[\w\.\-/:?=&%#]+", c):
        urls.add(m.group(0))
    for m in re.finditer(r"`(/[\w\-/\.\{\}]+)`", c):
        urls.add(m.group(1))
for u in sorted(urls)[:40]:
    print("  " + u)
