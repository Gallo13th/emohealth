#!/usr/bin/env python3
"""通用知乎开放平台 API 调用器（结果落盘，便于反复查看）。

用法：
  ZHIHU_KEY=<secret> python tools/survey/call_zhihu_api.py <接口名> [k=v ...]
例：
  ... call_zhihu_api.py zhihu_search Query="MBTI 大五 心理测量学" Count=10

密钥只从环境变量读，不落盘。
"""

from __future__ import annotations

import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request

KEY = os.environ.get("ZHIHU_KEY", "")
if not KEY:
    print("❌ 缺环境变量 ZHIHU_KEY")
    sys.exit(1)
if len(sys.argv) < 2:
    print(__doc__)
    sys.exit(2)

path = sys.argv[1]
params = {}
for a in sys.argv[2:]:
    if "=" in a:
        k, v = a.split("=", 1)
        params[k] = v

url = "https://developer.zhihu.com/api/v1/content/" + path + "?" + urllib.parse.urlencode(params)
req = urllib.request.Request(url, headers={
    "Authorization": f"Bearer {KEY}",
    "X-Request-Timestamp": str(int(time.time())),
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0",
})
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read().decode("utf-8")
except urllib.error.HTTPError as e:
    print(f"❌ HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:400]}")
    sys.exit(1)

fn = ".zhihu_" + path + ".json"
io.open(fn, "w", encoding="utf-8").write(raw)
d = json.loads(raw)
print(f"Code={d.get('Code')} Message={d.get('Message')}  → {fn}")

# 打印内容概览
def show(node, depth=0, maxdepth=4):
    pad = "  " * depth
    if depth > maxdepth:
        return
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, (dict, list)):
                n = len(v)
                print(f"{pad}{k}: {type(v).__name__}({n})")
                show(v, depth + 1, maxdepth)
            else:
                s = str(v).replace("\n", " ")
                if len(s) > 120:
                    s = s[:120] + "…"
                print(f"{pad}{k}: {s}")
    elif isinstance(node, list):
        for i, v in enumerate(node[:3]):
            print(f"{pad}[{i}]")
            show(v, depth + 1, maxdepth)
        if len(node) > 3:
            print(f"{pad}… 另 {len(node) - 3} 项")


show(d)
