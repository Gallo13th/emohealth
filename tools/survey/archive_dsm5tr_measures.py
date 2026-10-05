#!/usr/bin/env python3
"""把 APA「DSM-5-TR Online Assessment Measures」的成人版量表册收进归档。

与 ``tools/survey/archive_apa_manuals.py`` 的分工：那个脚本只收 PID-5 系列（已固定
URL 与授权原文）；这个脚本按**官方索引**（``_apa-measures-index.json``）
批量收 Level 1 / Level 2 量表册——它们的 PDF 页脚同样带授权声明，
所以入库时**逐册提取授权原文**，而不是照抄 PID-5 的文案。

原始件只读、永不改（`PLAN.md` R5）：已存在且哈希一致就跳过；哈希不一致则报错，必须人工确认。

用法：
    python tools/survey/archive_dsm5tr_measures.py            # 收缺失的
    python tools/survey/archive_dsm5tr_measures.py --verify    # 只校验
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
sys.path.insert(0, os.path.join(ROOT, "tools"))
from pdftext import PdfDoc, layout_lines  # noqa: E402

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36")
ARCHIVE = os.path.join(ROOT, "archive", "scales")
INDEX = os.path.join(ARCHIVE, "_apa-measures-index.json")

# 要收的册子：索引标题里的关键字 → 我方代码（目录名）
WANTED = {
    "DSM-5 Self-Rated Level 1 Cross-Cutting Symptom Measure—Adult": "DSM5TR-L1",
    "Level 2—Anger—Adult": "DSM5TR-L2-Anger",
    "Level 2—Anxiety—Adult": "DSM5TR-L2-Anxiety",
    "Level 2—Depression—Adult": "DSM5TR-L2-Depression",
    "Level 2—Mania—Adult": "DSM5TR-L2-Mania",
    "Level 2—Repetitive Thoughts and Behaviors—Adult": "DSM5TR-L2-Repetitive",
    "Level 2—Sleep Disturbance—Adult": "DSM5TR-L2-Sleep",
    "Level 2—Somatic Symptom—Adult": "DSM5TR-L2-Somatic",
    "Level 2—Substance Use—Adult": "DSM5TR-L2-Substance",
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


def extract_license(pdf: str) -> str:
    """从 PDF 里取授权声明原文（页脚那句）。"""
    try:
        doc = PdfDoc.load(pdf)
        maps = doc.to_unicode_maps()
        text = []
        for runs in doc.text_runs():
            for row in layout_lines(runs):
                text.append(row["text"])
        joined = re.sub(r"\s+", " ", " ".join(text))
    except Exception:                                       # noqa: BLE001
        return ""
    for pat in (r"(Copyright.{0,320}?patients\.)",
                r"(May be reproduced without permission.{0,200}?patients\.)",
                r"(This material can be reproduced.{0,200}?patients\.)"):
        m = re.search(pat, joined, re.I)
        if m:
            return re.sub(r"\s+", " ", m.group(1)).strip()
    return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()

    with open(INDEX, encoding="utf-8") as fh:
        idx = json.load(fh)
    by_title = {p["title"]: p["url"] for p in idx["pdfs"]}

    problems = 0
    for key, code in WANTED.items():
        match = next((t for t in by_title if t.startswith(key)), None)
        if not match:
            print(f"  ✗ {code}: 索引里找不到『{key}』")
            problems += 1
            continue
        url = by_title[match]
        folder = os.path.join(ARCHIVE, code)
        pdf = os.path.join(folder, "manual.pdf")
        rec_path = os.path.join(folder, "source.json")
        os.makedirs(folder, exist_ok=True)

        if os.path.exists(pdf):
            got = sha256(pdf)
            print(f"  ✓ {code:24} 已归档 {os.path.getsize(pdf):>7} 字节  "
                  f"sha256 {got[:12]}")
            if args.verify:
                if os.path.exists(rec_path):
                    with open(rec_path, encoding="utf-8") as fh:
                        rec = json.load(fh)
                    if rec.get("sha256") and rec["sha256"] != got:
                        print(f"      ✗ 与记录不符（原始件只读、永不改）")
                        problems += 1
            continue
        if args.verify:
            print(f"  ✗ {code:24} 未归档")
            problems += 1
            continue

        print(f"  ↓ {code:24} 下载…")
        try:
            body = fetch(url)
        except Exception as exc:                            # noqa: BLE001
            print(f"      ✗ 下载失败：{exc}")
            problems += 1
            continue
        if not body.startswith(b"%PDF"):
            print(f"      ✗ 不是 PDF（{len(body)} 字节）")
            problems += 1
            continue
        with open(pdf, "wb") as fh:
            fh.write(body)
        digest = sha256(pdf)
        lic = extract_license(pdf)
        with open(rec_path, "w", encoding="utf-8") as fh:
            json.dump({
                "code": code, "title": match, "source_url": url,
                "retrieved": "2026-10-03", "bytes": len(body), "sha256": digest,
                "license": {
                    "text": lic,
                    "holder": "American Psychiatric Association",
                    "redistribution": True if lic else None,
                    "evidence": f"PDF 页脚（archive/scales/{code}/manual.pdf）",
                },
                "collected_by": "tools/survey/archive_dsm5tr_measures.py",
                "notes": "APA 官方 DSM-5-TR Online Assessment Measures 页面公开提供；"
                         "授权原文逐册从 PDF 页脚提取。",
            }, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
        print(f"      ✓ {len(body)} 字节  sha256 {digest[:12]}  授权：{lic[:60] or '（未提取到）'}")

    print(f"\n{'✗ 有 ' + str(problems) + ' 个问题' if problems else '✅ 归档完整'}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
