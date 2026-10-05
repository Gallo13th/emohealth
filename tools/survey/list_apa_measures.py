#!/usr/bin/env python3
"""列出 APA「DSM-5-TR Online Assessment Measures」页面上的全部量表 PDF 链接。"""
import html
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36")
URL = ("https://www.psychiatry.org/psychiatrists/practice/dsm/educational-resources/"
       "assessment-measures")


def main() -> int:
    req = urllib.request.Request(URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        body = r.read().decode("utf-8", "replace")
    print(f"页面 {len(body)} 字节")

    seen = {}
    for m in re.finditer(r'<a[^>]+href="([^"]*getmedia[^"]*)"[^>]*>(.*?)</a>',
                         body, re.S | re.I):
        href = html.unescape(m.group(1))
        if not href.startswith("http"):
            href = "https://www.psychiatry.org" + href
        title = html.unescape(re.sub(r"<[^>]+>", "", m.group(2)))
        title = re.sub(r"\s+", " ", title).strip()
        if href.lower().endswith(".pdf") and href not in seen:
            seen[href] = title

    print(f"PDF 链接 {len(seen)} 个\n")
    adult = {u: t for u, t in seen.items()
             if not re.search(r"child|parent|guardian|age 6|age 11", t, re.I)}
    print(f"成人版（排除儿童/家长版）：{len(adult)} 个")
    for i, (u, t) in enumerate(sorted(adult.items(), key=lambda kv: kv[1]), 1):
        print(f"  {i:2}. {t[:78]}")
        print(f"      {u.split('/')[-1]}")

    out = os.path.join(ROOT, "archive", "scales", "_apa-measures-index.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"source_page": URL, "count": len(seen),
                   "pdfs": [{"title": t, "url": u} for u, t in sorted(seen.items())]},
                  fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(f"\n已写出 {os.path.relpath(out, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
