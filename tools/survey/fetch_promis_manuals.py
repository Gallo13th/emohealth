#!/usr/bin/env python3
"""PROMIS 官方 scoring manual 获取：按当前有效的 URL 模式批量尝试。

关键情报（来自检索）
====================
旧的 ``PROMIS_Depression_Scoring_Manual_05Dec2023.pdf`` 已 404（站点改版），
但以下模式仍有效：

  .../manuals/Scoring_Manual_Only/PROMIS_Anxiety_Scoring_Manual_08Sept2023.pdf
  .../manuals/Scoring_Manual_Only/PROMIS_Adult_Profile_Scoring_Manual_16Sept2024.pdf
  .../manuals/Scoring_Manuals_/PROMIS_Adult_Profile_Scoring_Manual.pdf   ← 另一目录名

而且 **Adult Profile Scoring Manual 一份就含多个域的转换表**（检索片段里直接
出现了「Adult v1.0 - Depression 8a Short Form Conversion Table」），
所以它优先级最高——一份文档能覆盖多个域，也便于交叉核对。

本脚本按「候选 URL 列表逐个试」的方式获取，命中即登记（含哈希），不解析。
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
DEST = os.path.join(ROOT, "archive", "norms", "promis")
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/120.0.0.0 Safari/537.36")
H = "https://www.healthmeasures.net/images/PROMIS/manuals/"

CANDIDATES = [
    ("adult-profile", H + "Scoring_Manual_Only/PROMIS_Adult_Profile_Scoring_Manual_16Sept2024.pdf"),
    ("adult-profile", H + "Scoring_Manuals_/PROMIS_Adult_Profile_Scoring_Manual.pdf"),
    ("anxiety", H + "Scoring_Manual_Only/PROMIS_Anxiety_Scoring_Manual_08Sept2023.pdf"),
    ("anger", H + "Scoring_Manual_Only/PROMIS_Anger_Scoring_Manual.pdf"),
    ("depression", H + "Scoring_Manual_Only/PROMIS_Depression_Scoring_Manual.pdf"),
    ("sleep", H + "Scoring_Manual_Only/PROMIS_Sleep_Disturbance_Scoring_Manual.pdf"),
    ("sleep", H + "Scoring_Manual_Only/PROMIS_SleepDisturbance_Scoring_Manual.pdf"),
]

# 独立第三方来源（用于交叉核对；不单独作为权威依据）
THIRD_PARTY = [
    ("sunnaas-2021-appendix",
     "https://www.sunnaas.no/49c7bd/siteassets/seksjon/rkr/documents/"
     "11136_2021_2906_moesm1_esm.pdf"),
    ("chula-2020-thesis",
     "https://cuir.car.chula.ac.th/xmlui/bitstream/handle/123456789/86438/"
     "6370013437.pdf?sequence=1&isAllowed=y"),
    ("rimed-2021-appendix-a",
     "http://rimed.org/rimedicaljournal/2021/10/"
     "2021-10-contribution-vargas-appendix.pdf"),
]


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/pdf,text/html,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "close",
    })
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def main() -> int:
    os.makedirs(DEST, exist_ok=True)
    have: dict[str, str] = {}
    log = {"purpose": "PROMIS T 分转换表来源（DSM-5-TR L2 四册）",
           "retrieved": "2026-10-03",
           "note": "官方站点改版后旧 URL 404；本表记录实际命中的 URL 与哈希",
           "official": [], "third_party": []}

    for key, url in CANDIDATES:
        if key in have:
            continue
        try:
            b = fetch(url)
        except Exception as exc:                              # noqa: BLE001
            print(f"  ✗ {key:14} {os.path.basename(url)}  ({type(exc).__name__})")
            continue
        if not b.startswith(b"%PDF"):
            print(f"  ✗ {key:14} {os.path.basename(url)}  不是 PDF")
            continue
        path = os.path.join(DEST, f"promis-{key}.pdf")
        with open(path, "wb") as fh:
            fh.write(b)
        h = hashlib.sha256(b).hexdigest()
        have[key] = path
        log["official"].append({"key": key, "url": url, "bytes": len(b),
                                "sha256": h,
                                "saved_as": os.path.relpath(path, ROOT)})
        print(f"  ✓ {key:14} {os.path.basename(url)}  {len(b)} 字节  "
              f"sha256 {h[:12]}")

    for key, url in THIRD_PARTY:
        try:
            b = fetch(url)
        except Exception as exc:                              # noqa: BLE001
            print(f"  ✗ 第三方 {key}  ({type(exc).__name__})")
            continue
        if not b.startswith(b"%PDF"):
            continue
        path = os.path.join(DEST, f"crosscheck-{key}.pdf")
        with open(path, "wb") as fh:
            fh.write(b)
        h = hashlib.sha256(b).hexdigest()
        log["third_party"].append({"key": key, "url": url, "bytes": len(b),
                                   "sha256": h,
                                   "saved_as": os.path.relpath(path, ROOT)})
        print(f"  ✓ 第三方 {key}  {len(b)} 字节  sha256 {h[:12]}")

    out = os.path.join(DEST, "source-log.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(log, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(f"\n官方 {len(log['official'])} 份；第三方 {len(log['third_party'])} 份")
    print(f"登记 → {os.path.relpath(out, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
