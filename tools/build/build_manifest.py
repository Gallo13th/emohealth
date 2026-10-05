#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重新生成两份清单：MANIFEST.sha256（逐字节校验）与 MANIFEST.txt（人类可读）。

为什么需要补这个脚本：原先生成清单的那一段没入库，于是每次加/删文件都只能手改，
结果清单**长期滞后于仓库**——实测它连 `ui/adaptive-data.js`、`data/adaptive-network.json`
这类早已存在的文件都没收录，等于「核心文件逐字节校验」这句话少验了 20 多个文件。

口径（与 README 一致）：
  · 核心文件 = 除 `archive/` 与 `vendor/` 之外的全部文件
  · 档案部分只给按目录汇总（逐个列 1917 个文件没有意义；原始件只读、永不改（PLAN.md R5），
    由 tools/check/verify_archive.py 逐字节校验；其中的派生缓存有缺陷时按 R3 更正）
  · 排除生成物与本地状态：**以 `.` 开头的目录一律跳过**（`.shots/`、`.git/`、`.tmp/`…），
    再点名 `archive`、`vendor`、`__pycache__`，以及 `*.pyc`

用法：
  python3 tools/build/build_manifest.py            # 写两份清单
  python3 tools/build/build_manifest.py --check    # 只报告差异，不写。**逐文件重算哈希**
                                                   # 与清单比对，并把三类差异分开报：
                                                   # ① 名字不在清单里（清单滞后）
                                                   # ② 清单里有、磁盘上没有
                                                   # ③ 名字在、内容/大小被改（证据链被动过）

为什么 `--check` 必须比哈希（2026-10-05 实测事故）
================================================
它原先**只比对文件名集合**，于是 `tools/README.md` 被清空成 0 字节（75055 → 0 B）
`--check` 一声不响——因为「名字还在清单里」。`MANIFEST.sha256` 是本项目的证据链底座
（`tools/_root.py` 靠它定位项目根、`verify_archive.py` 靠它守原始证据），
只比名字的校验等于**任何生成物被悄悄改坏都无人知晓**。所以这里逐文件重算并比对哈希。
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root, force_utf8_io  # noqa: E402
ROOT = find_root()

#: 点名的跳过目录（不含点的那些）。**以 `.` 开头的一律跳过**，见 ``skip_dir``。
SKIP_DIRS = {'archive', 'vendor', '__pycache__', '.shots', '.git', '.tmp'}
SKIP_FILES = {'MANIFEST.txt', 'MANIFEST.sha256'}
SKIP_EXT = {'.pyc'}


def skip_dir(name: str) -> bool:
    """这个目录是否跳过。

    规则：**以 `.` 开头的一律跳过**，再点名几个不含点的（`archive`、`vendor`、
    `__pycache__`）。

    为什么用前缀规则、而不是继续逐个点名：点名法必然漏下一个——实测 `.tmp/` 就这样
    进了证据清单（差异里出现 `+ .tmp/min-spawn.js`）：任何人在 `.tmp/` 下跑一次验证，
    清单就多一条临时文件；更糟的是**崩溃残留**的 `.build_descriptions.py.<pid>.*.tmpdir/`
    会让随后的遍历/哈希直接 `PermissionError`——一个已经崩掉的生成器把清单校验也带崩。
    `merge_scenes.py` / `build_item_structured.py` / `check_item_structured.py` 的
    docstring 都写明「验证机制用 `.tmp/`…别污染 data/」，所以它必须被排除在证据之外。
    """
    return name.startswith('.') or name in SKIP_DIRS


def core_files():
    out = []
    for dirpath, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if not skip_dir(d)]
        for name in sorted(files):
            if name in SKIP_FILES or os.path.splitext(name)[1] in SKIP_EXT:
                continue
            full = os.path.join(dirpath, name)
            out.append(os.path.relpath(full, ROOT).replace(os.sep, '/'))
    return sorted(out)


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def archive_summary():
    """档案按目录汇总（原始件只读、永不改；派生缓存按 R3 可更正。由 verify_archive.py 逐字节校验）。"""
    aroot = os.path.join(ROOT, 'archive')
    if not os.path.isdir(aroot):
        return [], 0, 0.0
    rows, total, size = [], 0, 0
    # 顶层目录 + 散落的文件各算一行
    entries = []
    for name in sorted(os.listdir(aroot)):
        full = os.path.join(aroot, name)
        entries.append((name, full, os.path.isdir(full)))
    for name, full, isdir in entries:
        if not isdir:
            n, sz = 1, os.path.getsize(full)
        else:
            n, sz = 0, 0
            for dp, dirs, fs in os.walk(full):
                dirs[:] = [d for d in dirs if not skip_dir(d)]
                for f in fs:
                    if f == '.DS_Store':
                        continue
                    n += 1
                    sz += os.path.getsize(os.path.join(dp, f))
        rows.append((name, n, sz))
        total += n
        size += sz
    return rows, total, size


def read_manifest_hashes(path: str) -> dict[str, str]:
    """读回 `MANIFEST.sha256` → ``{相对路径: sha256}``。"""
    out: dict[str, str] = {}
    if not os.path.exists(path):
        return out
    for line in open(path, encoding='utf-8'):
        if '  ./' in line:
            h, rel = line.split('  ./', 1)
            out[rel.strip()] = h.strip()
    return out


def read_manifest_sizes(path: str) -> dict[str, int]:
    """读回 `MANIFEST.txt` 的「大小 → 路径」表 → ``{相对路径: 字节数}``。

    清单只记哈希、**不记大小**；但 `MANIFEST.txt` 与 `MANIFEST.sha256` 是同一时刻
    生成的，拿它当「旧大小」足够，好把差异打印成 `75055 → 0 B` 这种一眼可见的形式
    （两个十六进制哈希要盯着看半天）。读不到就返回空表，只影响显示。
    """
    out: dict[str, int] = {}
    if not os.path.exists(path):
        return out
    for line in open(path, encoding='utf-8'):
        m = re.match(r'^\s*(\d+)\s+(\S.*?)\s*$', line)
        if m:
            out[m.group(2)] = int(m.group(1))
    return out


def main() -> int:
    force_utf8_io()          # 入口第一件事：GBK 控制台下不许崩（见 tools/_root.py）
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true',
                    help='只报告差异（名字集合 + 逐文件哈希），不写')
    args = ap.parse_args()

    files = core_files()
    lines_sha, lines_txt, missing = [], [], []
    actual: dict[str, str] = {}
    for rel in files:
        full = os.path.join(ROOT, rel)
        if not os.path.isfile(full):
            missing.append(rel)
            continue
        try:
            digest = sha256(full)
        except OSError as exc:                     # 读不到也不许把校验本身带崩
            missing.append(rel)
            print(f'  ⚠ 读不到 {rel}：{type(exc).__name__}: {exc}')
            continue
        actual[rel] = digest
        lines_sha.append(f'{digest}  ./{rel}')
        lines_txt.append((os.path.getsize(full), rel))

    arows, an, asize = archive_summary()
    now = time.strftime('%Y-%m-%dT%H:%M:%S')
    txt = [
        '# EmoHealth 打包清单',
        f'# 生成时间 {now}',
        f'# 文件总数 {len(files) + an}（核心 {len(files)}，档案 {an}）',
        f'# 总大小 {(sum(s for s, _ in lines_txt) + asize) / 1048576:.1f} MB',
        '#',
        '# 核心文件校验：  shasum -a 256 -c MANIFEST.sha256',
        '# 档案校验：      python3 tools/check/verify_archive.py --root archive',
        '',
        f'## 核心文件（{len(files)} 个，逐字节校验）',
    ]
    for sz, rel in sorted(lines_txt, key=lambda x: x[1]):
        txt.append(f'{sz:>10}  {rel}')
    txt += ['', f'## 档案（{an} 个，按目录汇总）']
    for name, n, sz in arows:
        txt.append(f'{n:>6} 个  {sz / 1048576:>8.1f} MB  archive/{name}')

    dst_sha = os.path.join(ROOT, 'MANIFEST.sha256')
    dst_txt = os.path.join(ROOT, 'MANIFEST.txt')

    if args.check:
        old = read_manifest_hashes(dst_sha)
        old_sizes = read_manifest_sizes(dst_txt)
        new = set(files)
        # 三类差异**分开报**——处置完全不同：
        added = sorted(new - set(old))                       # ① 名字不在清单里：清单滞后
        gone = sorted(set(old) - new)                        # ② 清单里有、磁盘上没有
        changed = sorted(r for r in (new & set(old))         # ③ 名字在、内容/大小变了
                         if actual.get(r) != old[r])
        unreadable = sorted(r for r in files if r not in actual)

        print(f'清单里 {len(old)} 个，实际 {len(new)} 个'
              f'（可读 {len(actual)}，读不到 {len(unreadable)}）')
        print()

        if added:
            print(f'❌ ① 「名字不在清单里」{len(added)} 个 —— **清单滞后**；'
                  f'确认这些是有意新增后再重算清单（不要手改清单）：')
            for r in added:
                print(f'   + {r}（{os.path.getsize(os.path.join(ROOT, r))} B）')
            print()
        if gone:
            print(f'❌ ② 「清单里有、磁盘上已无」{len(gone)} 个 —— 文件被删或改名：')
            for r in gone:
                print(f'   - {r}（清单大小 {old_sizes.get(r, "?")} B）')
            print()
        if changed:
            print(f'❌ ③ 「名字在清单里、内容已被改」{len(changed)} 个 —— '
                  f'**证据链被动过**；这一类才是 `--check` 存在的理由'
                  f'（旧版只比名字集合，对它们完全无感）：')
            for r in changed:
                now = os.path.getsize(os.path.join(ROOT, r))
                was = old_sizes.get(r)
                print(f'   ✗ {r}')
                print(f'       大小   {was if was is not None else "?"} → {now} B')
                print(f'       清单   {old[r]}')
                print(f'       实际   {actual[r]}')
            print()
        if unreadable:
            print(f'⚠ 读不到 {len(unreadable)} 个（见上面的 ⚠ 行）：'
                  + '、'.join(unreadable[:5]) + (' …' if len(unreadable) > 5 else ''))
            print()

        if not (added or gone or changed or unreadable):
            print('✅ 名字集合与逐文件哈希都与清单一致。')
            return 0
        print(f'❌ MANIFEST 校验未通过：名字不在清单 {len(added)}、清单里有磁盘无 {len(gone)}、'
              f'内容被改 {len(changed)}、读不到 {len(unreadable)}。')
        return 1

    with open(dst_sha, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(lines_sha) + '\n')
    with open(dst_txt, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(txt) + '\n')
    print(f'核心 {len(files)} 个文件 → MANIFEST.sha256 / MANIFEST.txt'
          + (f'（{len(missing)} 个读不到）' if missing else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
