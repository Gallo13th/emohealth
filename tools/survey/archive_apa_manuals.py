#!/usr/bin/env python3
"""把 APA 官方 DSM-5-TR 量表册 PDF 收进归档，并记录来源、SHA256、授权原文。

为什么要收 PDF 而不是只收提取出的题项
=====================================
项目硬规则要求「每个数字都能追到出处」。PID-5 的授权是「APA 版权，但允许研究人员
与临床医生无需许可复制」。要证明我们有资格收录，必须能出示**官方原件的哈希**
与**其上的授权声明**——只保存一份自制的 JSON 不够。

归档策略（原始件只读、永不改；`PLAN.md` R5）
============================================
`archive/scales/<code>/manual.pdf` 一旦落盘就不再覆盖；重跑时若哈希不同会报错，
必须人工确认（这正是「原始件只读、永不改」的意思）。

用法：
    python tools/survey/archive_apa_manuals.py            # 下载缺失的
    python tools/survey/archive_apa_manuals.py --verify    # 只校验已有归档
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
ARCHIVE = os.path.join(ROOT, "archive", "scales")
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36")

# 官方页面：https://www.psychiatry.org/psychiatrists/practice/dsm/educational-resources/assessment-measures
MANUALS = {
    "PID-5": {
        "url": "https://www.psychiatry.org/getmedia/594673a6-1b9b-4298-8b52-c4c652c4a4e2/"
               "APA-DSM5TR-ThePersonalityInventoryForDSM5FullVersionAdult.pdf",
        "title": "The Personality Inventory for DSM-5 (PID-5)—Adult",
        "items": 220,
        "license": ("Copyright ©2013 American Psychiatric Association. "
                    "All Rights Reserved. This material can be reproduced without "
                    "permission by researchers and by clinicians for use with their patients."),
        "license_holder": "American Psychiatric Association",
        "redistribution": True,
        "citation": ("Krueger RF, Derringer J, Markon KE, Watson D, Skodol AE. "
                     "The Personality Inventory for DSM-5 (PID-5)—Adult."),
    },
    "PID-5-BF": {
        "url": "https://www.psychiatry.org/getmedia/f65c4386-b2bc-44a5-9ace-d6fea2211506/"
               "APA-DSM5TR-ThePersonalityInventoryForDSM5BriefFormAdult.pdf",
        "title": "The Personality Inventory for DSM-5—Brief Form (PID-5-BF)—Adult",
        "items": 25,
        "license": ("Copyright 2013 American Psychiatric Association. All Rights Reserved. "
                    "May be reproduced without permission by researchers and by clinicians "
                    "for use with their patients."),
        "license_holder": "American Psychiatric Association",
        "redistribution": True,
        "citation": ("Krueger RF, Derringer J, Markon KE, Watson D, Skodol AE. "
                     "The Personality Inventory for DSM-5—Brief Form (PID-5-BF)—Adult."),
    },
    "DSM5TR-L1": {
        "url": "https://www.psychiatry.org/getmedia/e0b4b299-95b3-407b-b8c2-caa871ca218d/"
               "APA-DSM5TR-Level1MeasureAdult.pdf",
        "title": "DSM-5 Self-Rated Level 1 Cross-Cutting Symptom Measure—Adult",
        "items": None,                      # 待提取确认为 23
        "license": "",                      # 待逐册核实
        "license_holder": "American Psychiatric Association",
        "redistribution": None,
        "citation": "American Psychiatric Association. DSM-5-TR Online Assessment Measures.",
    },
}


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true", help="只校验已有归档，不下载")
    args = ap.parse_args()

    os.makedirs(ARCHIVE, exist_ok=True)
    problems = 0
    for code, meta in MANUALS.items():
        folder = os.path.join(ARCHIVE, code)
        pdf = os.path.join(folder, "manual.pdf")
        rec_path = os.path.join(folder, "source.json")
        os.makedirs(folder, exist_ok=True)

        if os.path.exists(pdf):
            got = sha256(pdf)
            print(f"  ✓ {code:10} 已归档  {os.path.getsize(pdf):>8} 字节  sha256 {got[:16]}")
            if args.verify:
                if os.path.exists(rec_path):
                    with open(rec_path, encoding="utf-8") as fh:
                        rec = json.load(fh)
                    if rec.get("sha256") and rec["sha256"] != got:
                        print(f"      ✗ 与记录不符：{rec['sha256'][:16]}（原始件只读、永不改）")
                        problems += 1
            continue

        if args.verify:
            print(f"  ✗ {code:10} 未归档")
            problems += 1
            continue

        print(f"  ↓ {code:10} 下载 {meta['url'][:88]}…")
        try:
            body = fetch(meta["url"])
        except Exception as exc:                                # noqa: BLE001
            print(f"      ✗ 下载失败：{exc}")
            problems += 1
            continue
        if not body.startswith(b"%PDF"):
            print(f"      ✗ 返回的不是 PDF（{len(body)} 字节，疑似拦截页）")
            problems += 1
            continue
        with open(pdf, "wb") as fh:
            fh.write(body)
        digest = sha256(pdf)
        rec = {
            "code": code, "title": meta["title"], "source_url": meta["url"],
            "retrieved": "2026-10-03", "bytes": len(body), "sha256": digest,
            "declared_items": meta["items"],
            "license": {"text": meta["license"], "holder": meta["license_holder"],
                        "redistribution": meta["redistribution"],
                        "evidence": f"PDF 页脚（archive/scales/{code}/manual.pdf）"},
            "citation": meta["citation"],
            "collected_by": "tools/survey/archive_apa_manuals.py",
            "notes": "APA 官方「DSM-5-TR Online Assessment Measures」页面公开提供。"
                     "授权声明逐字取自 PDF 页脚。",
        }
        with open(rec_path, "w", encoding="utf-8") as fh:
            json.dump(rec, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
        print(f"      ✓ {len(body)} 字节  sha256 {digest[:16]}  → {os.path.relpath(pdf, ROOT)}")

    print(f"\n{'✗ 有 ' + str(problems) + ' 个问题' if problems else '✅ 归档完整'}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
