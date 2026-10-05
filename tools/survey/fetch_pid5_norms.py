#!/usr/bin/env python3
"""为 PID-5 抓取可溯源的常模资料（先入档，再谈使用）。

为什么要走这一步
================
用户要求「对大五人格做过的常模/注释/相关性分级全流程，对新量表各做一遍」。
大五人格的常模有 Johnson (2005) 的原始作答（145,388 份），可以自己算；
PID-5 没有原始作答，只能引用**已发表的常模**——那就必须把常模来源原文抓下来
存档（原始件只读、永不改；`PLAN.md` R5），否则「界面上的百分位可追到出处」这条硬规则无法满足。

本脚本只负责**下载与登记**，不解析、不采用。解析前先人工看清是什么再决定。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
DEST = os.path.join(ROOT, "archive", "norms", "pid-5")
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36")

TARGETS = [
    {
        "name": "zenodo-norms",
        "url": "https://zenodo.org/api/records/22280403",
        "kind": "json",   # 先取元数据，看有哪些文件
        "note": "Population-Representative Norms for PID-5（含常模表与分析代码）",
    },
    {
        "name": "pubmed-35084874",
        "url": "https://pubmed.ncbi.nlm.nih.gov/35084874/",
        "kind": "html",
        "note": "Normative data for PID-5 domains/facets（2022, Personality Disorders）",
    },
]


def fetch(url: str) -> bytes:
    # Zenodo 对缺 Accept 的请求返回 403，所以带上完整的浏览器头
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/json, text/html, application/pdf, */*",
        "Accept-Language": "en-US,en;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


TARGETS2 = [
    {
        "name": "kassel-representative-norms",
        "url": ("https://kobra.uni-kassel.de/server/api/core/bitstreams/"
                "f112092d-ab99-449c-984a-49084a57db35/content"),
        "kind": "pdf",
        "note": "Norm values and correlates in a representative sample（开放获取全文）",
    },
]


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> int:
    os.makedirs(DEST, exist_ok=True)
    log = []
    for t in TARGETS + TARGETS2:
        ext = {"json": ".json", "html": ".html", "pdf": ".pdf"}[t["kind"]]
        path = os.path.join(DEST, t["name"] + ext)
        print(f"↓ {t['name']}  {t['url']}")
        try:
            body = fetch(t["url"])
        except Exception as exc:                              # noqa: BLE001
            print(f"  ✗ 下载失败：{exc}")
            log.append({**t, "ok": False, "error": str(exc)})
            continue
        with open(path, "wb") as fh:
            fh.write(body)
        row = {"name": t["name"], "url": t["url"], "note": t["note"],
               "file": os.path.relpath(path, ROOT), "bytes": len(body),
               "sha256": sha256(body), "ok": True}
        print(f"  ✓ {len(body)} 字节  sha256 {row['sha256'][:12]}")
        if t["kind"] == "json":
            try:
                j = json.loads(body)
                files = j.get("files") or []
                row["files"] = [{"key": f.get("key"),
                                 "size": f.get("size"),
                                 "url": (f.get("links") or {}).get("self")}
                                for f in files]
                print(f"    该记录含 {len(files)} 个文件：")
                for f in row["files"][:12]:
                    print(f"      · {f['key']}  {f['size']} 字节")
            except Exception as exc:                          # noqa: BLE001
                print(f"    （元数据解析失败：{exc}）")
        log.append(row)

    out = os.path.join(DEST, "source-log.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"purpose": "PID-5 常模来源（原始资料入档，供解析与引用）",
                   "retrieved": "2026-10-03", "items": log},
                  fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(f"\n登记 → {os.path.relpath(out, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
