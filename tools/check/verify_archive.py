#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""归档完整性校验器 —— 检查文件真实类型是否与扩展名一致，并核对 manifest 的 SHA-256。

动机：下载失败时服务器常返回 HTML 错误页，但被保存成 .pdf。归档若混入这类文件，
溯源就失效了。本工具把这类"伪装件"找出来。

用法：
  python3 tools/check/verify_archive.py --root archive                 # 只报告
  python3 tools/check/verify_archive.py --root archive --quarantine    # 移入 _quarantine/
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys

#: UTF-8 兜底：唯一实现在 tools/_root.py（GBK 控制台下 print 中文/✅ 会崩，
#: 而崩溃退出码 1 与「原始证据被篡改」不可区分——证据链上最不能出假红的地方）。
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import force_utf8_io  # noqa: E402

MAGIC = [
    (b"%PDF", ".pdf", "PDF"),
    (b"PK\x03\x04", ".zip", "ZIP/OOXML"),
    (b"\xd0\xcf\x11\xe0", ".doc", "OLE2 (doc/xls)"),
    (b"\x89PNG", ".png", "PNG"),
    (b"\xff\xd8\xff", ".jpg", "JPEG"),
    (b"GIF8", ".gif", "GIF"),
    (b"SQLite format 3", ".sqlite", "SQLite"),
    (b"\x1f\x8b", ".gz", "GZIP"),
]

TEXT_SNIFF = (b"<!DOCTYPE", b"<html", b"<?xml", b"<HTML")


def kind_of(path: str) -> str:
    """返回文件的真实类型标签。"""
    try:
        with open(path, "rb") as fh:
            head = fh.read(4096)
    except OSError as e:
        return f"UNREADABLE ({e})"
    for magic, _ext, label in MAGIC:
        if head.startswith(magic):
            return label
    stripped = head.lstrip()[:64].upper()
    for sniff in TEXT_SNIFF:
        if stripped.startswith(sniff):
            return "HTML"
    if not head.strip():
        return "EMPTY"
    return "UNKNOWN"


def main() -> int:
    force_utf8_io()          # 入口第一件事：GBK 控制台下不许崩（见 tools/_root.py）
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="archive")
    ap.add_argument("--quarantine", action="store_true")
    args = ap.parse_args()

    suspicious: list[tuple[str, str]] = []
    total = 0
    for dirpath, _dirs, files in os.walk(args.root):
        if "_quarantine" in dirpath:
            continue
        for name in files:
            path = os.path.join(dirpath, name)
            total += 1
            ext = os.path.splitext(name)[1].lower()
            real = kind_of(path)

            bad = False
            if ext == ".pdf" and real != "PDF":
                bad = True
            elif ext in (".docx", ".xlsx", ".pptx") and real != "ZIP/OOXML":
                bad = True
            elif ext in (".doc", ".xls") and real not in ("OLE2 (doc/xls)", "ZIP/OOXML"):
                bad = True
            elif real == "EMPTY":
                bad = True

            if bad:
                suspicious.append((path, real))

    # 核对 manifest 中的 sha256
    hash_bad: list[str] = []
    checked = 0
    for dirpath, _dirs, files in os.walk(args.root):
        for name in files:
            if not name.endswith("manifest.jsonl"):
                continue
            mpath = os.path.join(dirpath, name)
            for line in open(mpath, encoding="utf-8"):
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if "sha256" not in rec or "path" not in rec:
                    continue
                target = os.path.join(os.path.dirname(mpath), rec["path"])
                if not os.path.exists(target):
                    target = os.path.join(os.path.dirname(mpath), rec.get("dir", ""), rec.get("name", ""))
                if not os.path.exists(target):
                    hash_bad.append(f"MISSING {rec.get('name', rec['path'])}")
                    continue
                checked += 1
                actual = hashlib.sha256(open(target, "rb").read()).hexdigest()
                if actual != rec["sha256"]:
                    hash_bad.append(f"HASH MISMATCH {target}")

    print(json.dumps({
        "files_scanned": total,
        "suspicious": len(suspicious),
        "manifest_checked": checked,
        "manifest_problems": len(hash_bad),
    }, ensure_ascii=False))

    if suspicious:
        print("\n--- 伪装/损坏文件 ---")
        for path, real in suspicious:
            print(f"  [{real:18}] {path}")

    if hash_bad:
        print("\n--- manifest 问题 ---")
        for item in hash_bad:
            print(f"  {item}")

    if args.quarantine and suspicious:
        qroot = os.path.join(args.root, "_quarantine")
        for path, _real in suspicious:
            rel = os.path.relpath(path, args.root)
            dest = os.path.join(qroot, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.move(path, dest)
        print(f"\n已移入隔离区：{qroot}")

    return 1 if (suspicious or hash_bad) else 0


if __name__ == "__main__":
    raise SystemExit(main())
