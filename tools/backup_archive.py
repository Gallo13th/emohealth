#!/usr/bin/env python3
"""把 git 保护不到的东西备份到另一块盘 —— 目前是 `archive/` 与整个工程树。

为什么需要这个脚本
==================
`archive/` **有意不入版本控制**（见 `.gitignore` 第 36 行附近的完整理由：2041 文件 /
755,865,089 B，入库会让 .git 多出约 490 MB 并撞上远端推送上限，且它只增不改）。

代价是：**git 只能检出 `archive/` 被改，不能还原**——历史上从未存过它的内容。
`tools/check/verify_archive.py` 是逐字节校验，它的作用是"发现损坏"，不是"恢复数据"。
所以 archive 必须有一份**独立的物理副本**，这个脚本就是那份副本的生产者与验证者。

它备份什么
==========
两个 payload（可用 `--only` 二选一）：

* ``archive`` —— `<root>/archive/**`，即 git 之外的那 755 MB 证据底本；
* ``repo``    —— 工程树除 archive 与忽略目录外的全部内容，**包含 `.git`**，
  因此目标目录单独就能恢复出一个可用的仓库（含提交历史）。

忽略目录（都是可再生的）：``.shots/``、``.tmp/``、``__pycache__/``、``vendor/``。

它怎么保证副本是对的
====================
**先拷、再逐文件重算 sha256 双向比对**，不留"拷完就当成功"的口子：

* 源有、目标缺 → 报错；
* 目标有、源没有 → 报错（说明副本里混进了不该有的东西）；
* 两边都在但哈希不同 → 报错并列出行。

只有 0 差异才返回 0。任何非 0 都意味着**这份备份不能信**，必须查明原因再重跑。
（这条是本项目的既有教训：`build_manifest.py --check` 曾经只比文件名不比哈希，
于是 `tools/README.md` 被清空成 0 字节它完全无感——"看起来一样"不等于一样。）

用法
====
    python tools/backup_archive.py                     # 拷到默认盘并全量校验
    python tools/backup_archive.py --dest D:\\backup
    python tools/backup_archive.py --verify-only        # 只校验，不拷贝
    python tools/backup_archive.py --only archive       # 只备份 archive

退出码：全部一致 0；有任何缺失/多余/哈希不符 1；用法或环境错误 2。

产物
====
    <dest>/archive/**            （当 --only repo 时不生成）
    <dest>/repo/**               （当 --only archive 时不生成）
    <dest>/BACKUP-INFO.json      时间戳、源根、git HEAD、计数、字节、校验结论
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _root import find_root, force_utf8_io  # noqa: E402

#: 可再生的目录，一律不进副本。`.git` **不在**此列——它是 repo payload 的核心。
SKIP_DIRS = {".shots", ".tmp", "__pycache__", "vendor"}

#: 默认备份目标。放 D 盘：C 盘是同盘，同盘备份挡不住盘挂。
DEFAULT_DEST = r"D:\emohealth-backup"

CHUNK = 1 << 20


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(CHUNK)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def iter_files(base: str):
    """archive payload：**原样全拷**，含隐藏目录。

    特意**不**排除 `.` 开头的目录：`archive/ipip/data/OpenScales/.git` 是那 1599 个
    文件所属克隆的元数据，排除它会让这份副本失去"可继续 pull/回溯"的能力。备份的
    职责是原样复制，不是替谁做整理——只排除纯再生的 `__pycache__`/`vendor`。
    """
    for cur, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            full = os.path.join(cur, name)
            yield os.path.relpath(full, base).replace(os.sep, "/"), full


def collect_repo_files(base: str):
    """repo payload：跳过忽略目录，但**保留** `.git`。"""
    for cur, dirs, files in os.walk(base):
        at_top = os.path.abspath(cur) == os.path.abspath(base)
        keep = []
        for d in dirs:
            if d in SKIP_DIRS:
                continue
            if at_top and d == "archive":      # 由 archive payload 负责
                continue
            keep.append(d)
        dirs[:] = keep
        for name in files:
            full = os.path.join(cur, name)
            yield os.path.relpath(full, base).replace(os.sep, "/"), full


def copy_payload(label: str, pairs, src_base: str, dst_base: str, do_copy: bool):
    """拷贝一组 (rel, src)。返回 (copied, skipped) 计数。"""
    copied = skipped = 0
    for rel, src in pairs:
        dst = os.path.join(dst_base, rel.replace("/", os.sep))
        if do_copy:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            need = True
            if os.path.isfile(dst):
                try:
                    s, d = os.stat(src), os.stat(dst)
                    need = (s.st_size != d.st_size) or (int(s.st_mtime) != int(d.st_mtime))
                except OSError:
                    need = True
            if need:
                shutil.copy2(src, dst)
                copied += 1
            else:
                skipped += 1
        else:
            skipped += 1
    print(f"  {label:<8} 源 {len(pairs):>5} 个文件   拷贝 {copied:>5}   跳过（已一致）{skipped:>5}")
    return copied, skipped


def verify_payload(label: str, pairs, dst_base: str):
    """逐文件重算 sha256 双向比对。返回 (checked, bytes, problems[])。"""
    problems: list[str] = []
    checked = 0
    total = 0
    src_rels = set()
    for rel, src in pairs:
        src_rels.add(rel)
        dst = os.path.join(dst_base, rel.replace("/", os.sep))
        if not os.path.isfile(dst):
            problems.append(f"缺失：{rel}")
            continue
        a = sha256_file(src)
        b = sha256_file(dst)
        checked += 1
        total += os.path.getsize(src)
        if a != b:
            problems.append(f"哈希不符：{rel}\n      源 {a}\n      副本 {b}")
    if os.path.isdir(dst_base):
        for cur, dirs, files in os.walk(dst_base):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for name in files:
                rel = os.path.relpath(os.path.join(cur, name), dst_base).replace(os.sep, "/")
                if rel not in src_rels:
                    problems.append(f"多余（副本里有、源里没有）：{rel}")
    print(f"  {label:<8} 校验 {checked:>5} 个文件   {total:>15,} B   问题 {len(problems)}")
    return checked, total, problems


def git_head(root: str) -> str:
    try:
        out = subprocess.run(["git", "-C", root, "rev-parse", "HEAD"],
                             capture_output=True, text=True, timeout=20)
        return out.stdout.strip() or "(no commit)"
    except Exception:
        return "(unavailable)"


def main() -> int:
    force_utf8_io()
    ap = argparse.ArgumentParser(description="把 archive/ 与工程树备份到另一块盘并逐文件校验")
    ap.add_argument("--dest", default=DEFAULT_DEST, help=f"备份目标目录（默认 {DEFAULT_DEST}）")
    ap.add_argument("--only", choices=["archive", "repo"], help="只备份其中一个 payload")
    ap.add_argument("--verify-only", action="store_true", help="只校验，不拷贝")
    args = ap.parse_args()

    root = str(find_root())
    dest = os.path.abspath(args.dest)
    do_copy = not args.verify_only
    wanted = {args.only} if args.only else {"archive", "repo"}

    print(f"源   {root}")
    print(f"目标 {dest}")
    print(f"模式 {'只校验' if not do_copy else '拷贝 + 校验'}｜payload {', '.join(sorted(wanted))}")
    print()

    if do_copy:
        head = dest.split(os.sep)[0] + os.sep
        if not os.path.isdir(head):
            print(f"❌ 目标盘不存在：{head}")
            return 2
        os.makedirs(dest, exist_ok=True)

    payloads = {}
    if "archive" in wanted:
        payloads["archive"] = (list(iter_files(os.path.join(root, "archive"))),
                               os.path.join(dest, "archive"))
    if "repo" in wanted:
        payloads["repo"] = (list(collect_repo_files(root)), os.path.join(dest, "repo"))

    if do_copy:
        print("── 拷贝 ──")
        for label, (pairs, dst) in payloads.items():
            copy_payload(label, pairs, root, dst, True)
        print()

    print("── 校验（逐文件 sha256，双向）──")
    report = {}
    all_problems: list[str] = []
    for label, (pairs, dst) in payloads.items():
        checked, total, problems = verify_payload(label, pairs, dst)
        report[label] = {"files": checked, "bytes": total, "problems": len(problems)}
        all_problems += [f"[{label}] {p}" for p in problems]
    print()

    info = {
        "backed_up_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "source_root": root,
        "dest": dest,
        "git_head": git_head(root),
        "mode": "verify-only" if not do_copy else "copy+verify",
        "payloads": report,
        "problems": len(all_problems),
    }
    if do_copy:
        with open(os.path.join(dest, "BACKUP-INFO.json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(info, fh, ensure_ascii=False, indent=1, sort_keys=True)
            fh.write("\n")
        print(f"已写 {os.path.join(dest, 'BACKUP-INFO.json')}")
        print()

    if all_problems:
        print(f"❌ 备份不可信：{len(all_problems)} 个问题")
        for p in all_problems[:50]:
            print(f"   · {p}")
        if len(all_problems) > 50:
            print(f"   …另有 {len(all_problems) - 50} 个，未全部列出")
        return 1

    total_files = sum(v["files"] for v in report.values())
    total_bytes = sum(v["bytes"] for v in report.values())
    print(f"✅ 备份已校验：{total_files:,} 个文件 / {total_bytes:,} B，逐文件 sha256 与源一致，无缺失、无多余。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
