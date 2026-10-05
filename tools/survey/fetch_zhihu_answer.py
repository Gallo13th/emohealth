#!/usr/bin/env python3
"""用知乎开放平台 API 取问题 518751517 的回答列表，找出目标回答。

用法：ZHIHU_KEY=<secret> python tools/survey/fetch_zhihu_answer.py
密钥只从**环境变量**读，不落盘（避免把凭据写进仓库）。
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

TARGET = "1933829036003530674"
QURL = "https://www.zhihu.com/question/518751517"
BASE = "https://developer.zhihu.com/api/v1/content/"


def call(path: str, params: dict) -> dict:
    url = BASE + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {KEY}",
        "X-Request-Timestamp": str(int(time.time())),
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0",
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


d = call("question_answers", {"QuestionUrl": QURL, "Limit": 50})
io.open(".zhihu_qa.json", "w", encoding="utf-8").write(
    json.dumps(d, ensure_ascii=False, indent=1))
print(f"Code={d.get('Code')} Message={d.get('Message')}")
data = d.get("Data") or {}
items = data.get("Items") or []
pg = data.get("Paging") or {}
print(f"回答 {len(items)} 条｜Paging={json.dumps(pg, ensure_ascii=False)[:160]}\n")

hit = None
for it in items:
    tok = str(it.get("ContentToken"))
    s = it.get("Summary") or ""
    star = "  ★← 目标" if tok == TARGET else ""
    print(f"  token={tok:24} {len(s):5} 字{star}")
    if tok == TARGET:
        hit = it
        print("\n--- 目标回答 Summary ---")
        print(s)
        io.open(".zhihu_target.txt", "w", encoding="utf-8").write(s)
if not hit:
    print(f"\n⚠️ 本次 {len(items)} 条里没有目标 token（答案可能在更后面，需分页）")
