#!/usr/bin/env python3
"""找 PID-5 常模的**机器可读**来源（Zenodo 记录里的常模表与分析代码）。

为什么坚持要机器可读
====================
那篇 1.9 MB 的学位论文 PDF 里确实有常模数字，但**文本版式混乱**
（形如 ``descriptive statistics - representative samples for PID 5`` 的错位）。
从这种版面抠数字，正是我在 PID-5 计分键上踩过的坑——转录错一位，
界面上的百分位就是错的，而且看不出来。

所以先找是否存在 CSV/XLSX 形态的常模表；只有确实没有，才考虑逐册转写
（并且要双人交叉核对）。
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/120.0.0.0 Safari/537.36")


def get(url: str, accept: str = "*/*") -> bytes:
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": accept,
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://zenodo.org/",
        "Connection": "close",
    })
    with urllib.request.urlopen(req, timeout=90) as f:
        return f.read()


CANDS = [
    ("https://zenodo.org/records/22280403", "text/html"),
    ("https://zenodo.org/api/records/22280403", "application/json"),
    ("https://doi.org/10.5281/zenodo.22280403", "text/html"),
]


def main() -> int:
    for url, accept in CANDS:
        print(f"── {url}")
        try:
            b = get(url, accept)
        except Exception as exc:                              # noqa: BLE001
            print(f"   ✗ {exc}")
            continue
        print(f"   ✓ {len(b)} 字节")
        if accept.startswith("application/json"):
            try:
                j = json.loads(b)
            except Exception as exc:                          # noqa: BLE001
                print(f"   （不是 JSON：{exc}）")
                continue
            md = j.get("metadata") or {}
            print(f"   title: {str(md.get('title'))[:100]}")
            print(f"   license: {json.dumps(md.get('license'), ensure_ascii=False)[:120]}")
            files = j.get("files") or []
            print(f"   文件 {len(files)} 个：")
            for f in files:
                print(f"     · {f.get('key')}  {f.get('size')} 字节")
                print(f"       {(f.get('links') or {}).get('self')}")
        else:
            txt = b.decode("utf-8", "replace")
            links = set()
            for m in re.finditer(r'href="([^"]+)"', txt):
                h = m.group(1)
                if any(k in h for k in ("/files/", "download", "record/22280403/files")):
                    links.add(h)
            print(f"   命中文件链接 {len(links)} 个：")
            for h in list(links)[:20]:
                print("     ", h[:130])
    return 0


if __name__ == "__main__":
    sys.exit(main())
