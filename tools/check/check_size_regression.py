#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文件**大小回归**守卫：拿 `MANIFEST.txt` 记录的大小与磁盘现状比对，抓**意外截断**。

为什么要有它
============
2026-10-05 出过一次真事故：`tools/README.md` 被一句写坏的脚本
（`io.open(p,"w").write(io.open(p).read())`——**先构造写句柄就把文件截断了**，
再读回空串）从 **77,377 B 变成 0 B**。当时**没有任何守卫能发现**：
`check_index_completeness` 只查「文件有没有被索引」，空文件照样"通过"；
`build_manifest --check` 当时也只比**文件名集合**，0 字节的文件它同样无感。
本守卫补的正是这个盲区，而且做成**通用**的——任何文件被截断都能抓到，不只 README。

与 `build_manifest --check` 的**分工**（不要做成重复品）
=====================================================
* `tools/build/build_manifest.py --check`（正由 converge-pack 补**哈希比对**）：守
  **同一轮之内**的「内容被改」——逐字节比对，最硬；但它的基线是**最近一次重算 MANIFEST**，
  所以每次重算之后，之前发生的改动就**没有基线**了。
* **本脚本**：守**跨清单重算**——比对的是磁盘现状 vs **MANIFEST 里记下的历史大小**，
  即使 MANIFEST 刚被重算（哈希基线随之刷新），「当前大小 vs 上一轮记录的大小」仍能抓出
  **量级缩水**这类差错（截断/被清空/写坏）。两者的时间尺度不同，互补而非重复。

判据（阈值刻意保守，避免把正常重构报成红）
========================================
对 `MANIFEST.txt` 里**记录过、且现在仍存在**的每个文件：
* **文档**（`.md` / `.txt` / `.rst`）：缩水 **> 20%** ⇒ ❌
* **其它文件**：缩水 **> 50%** ⇒ ❌
输出列：文件、记录大小、当前大小、缩水比例。

另加 `tools/README.md` 的**结构性断言**（它是唯一没有别的守卫的文档）：
非 0 字节、索引表行 ≥ 200、`### 3.x` 小节 ≥ 6、字节数 ≥ MANIFEST 记录的 80%。

不判红但会提示
============
* MANIFEST 记录过、磁盘上已无的文件 → 只计数（合法删除很多，不做红）；
* MANIFEST 的生成时间（若明显早于最近改动，提示先跑 `tools/build/build_manifest.py`）；
* 字节级校验请用 `shasum -a 256 -c MANIFEST.sha256`（比大小更硬，但任何正常改动都会变红，
  所以不适合作「每轮必跑」的门；本守卫用**大小**做粗筛，专抓截断这类量级异常）。

用法
====
    python tools/check/check_size_regression.py        # 有 ❌ → 退出码 1
    python tools/check/check_size_regression.py -v     # 额外列出全部比对结果
"""
from __future__ import annotations

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root, force_utf8_io  # noqa: E402
ROOT = str(find_root())

MANIFEST = os.path.join(ROOT, "MANIFEST.txt")
README = os.path.join(ROOT, "tools", "README.md")
DOC_SUFFIXES = (".md", ".txt", ".rst")
DOC_SHRINK = 0.20
OTHER_SHRINK = 0.50
README_MIN_ROWS = 200
README_MIN_SECTIONS = 6
README_MIN_FRACTION = 0.80


def main() -> int:
    # ⚠️ 必须放**第一行**（早于 parse_args）：Windows 默认控制台是 GBK，
    #    `print("✅ …")` 会抛 UnicodeEncodeError → 退出码 1，与「真的发现截断」
    #    **不可区分**——一个完好的守卫会在默认控制台上永远假装变红。
    #    唯一实现在 tools/_root.py（不要在本地重写一份）。
    force_utf8_io()
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--verbose", action="store_true", help="列出全部比对结果")
    args = ap.parse_args()

    if not os.path.exists(MANIFEST):
        print(f"❌ 缺 {os.path.relpath(MANIFEST, ROOT)}——先跑 tools/build/build_manifest.py")
        return 1
    text = open(MANIFEST, encoding="utf-8", errors="replace").read()
    lines = text.split("\n")

    recorded = {}
    fake = 0
    for l in lines:
        if l.startswith("#") or not l.strip():
            continue
        m = re.match(r"^\s*(\d+)\s+(\S.*?)\s*$", l)
        if not m:
            continue
        size, path = int(m.group(1)), m.group(2)
        # 档案段是「按目录汇总」行（`1 个  0.0 MB  archive/README.md`），不是单个文件
        if re.search(r"\s", path):
            fake += 1
            continue
        recorded[path] = size

    shrunk, gone, ok = [], [], 0
    for path, size in sorted(recorded.items()):
        fp = os.path.join(ROOT, path.replace("/", os.sep))
        if not os.path.exists(fp) or not os.path.isfile(fp):
            gone.append(path)
            continue
        cur = os.path.getsize(fp)
        ratio = (1 - cur / size) if size else 0.0
        is_doc = path.lower().endswith(DOC_SUFFIXES)
        limit = DOC_SHRINK if is_doc else OTHER_SHRINK
        if ratio > limit:
            shrunk.append((path, size, cur, ratio, limit))
        else:
            ok += 1
        if args.verbose and ratio > 0.05:
            print(f"    -{ratio * 100:5.1f}%  {cur:>10} (记录 {size:>10})  {path}")

    gen = next((l.strip("# ").strip() for l in lines if "生成时间" in l), "?")

    print("=" * 96)
    print("文件大小回归守卫（对照 MANIFEST.txt 的记录，抓意外截断）")
    print("=" * 96)
    print(f"MANIFEST：{os.path.relpath(MANIFEST, ROOT)}（{gen}）")
    print(f"记录文件 {len(recorded)} 个（另跳过 {fake} 行目录汇总）"
          f"｜仍存在且未异常缩水 {ok}｜异常缩水 {len(shrunk)}｜已不存在 {len(gone)}")

    # ── README 结构断言（唯一没有别的守卫的文档）──
    print("\n── tools/README.md 结构 ──")
    readme_bad = []
    if not os.path.exists(README):
        readme_bad.append("文件不存在")
        size = rows = secs = 0
    else:
        size = os.path.getsize(README)
        rt = open(README, encoding="utf-8", errors="replace").read()
        rows = len(re.findall(r"(?m)^\|\s*`", rt))
        secs = len(re.findall(r"(?m)^### 3\.\d", rt))
        rec = recorded.get("tools/README.md")
        if size == 0:
            readme_bad.append("被清空（0 字节）")
        if rows < README_MIN_ROWS:
            readme_bad.append(f"索引表行 {rows} < {README_MIN_ROWS}")
        if secs < README_MIN_SECTIONS:
            readme_bad.append(f"### 3.x 小节 {secs} < {README_MIN_SECTIONS}")
        if rec and size < rec * README_MIN_FRACTION:
            readme_bad.append(f"字节 {size} < 记录 {rec} 的 {README_MIN_FRACTION:.0%}")
        print(f"  字节 {size}｜索引表行 {rows}｜### 3.x 小节 {secs}"
              f"｜MANIFEST 记录 {rec if rec else '（未记录）'}")
    if readme_bad:
        print("  ❌ " + "；".join(readme_bad))
    else:
        print("  ✅ 非空、表行/小节/字节数均达标")

    bad = bool(shrunk) or bool(readme_bad)
    if shrunk:
        print(f"\n❌ {len(shrunk)} 个文件缩水超过阈值（文档 >{DOC_SHRINK:.0%}、其它 >{OTHER_SHRINK:.0%}）：")
        for path, size, cur, ratio, limit in shrunk:
            print(f"   · {path}")
            print(f"       MANIFEST 记录 {size} B → 当前 {cur} B（缩水 {ratio * 100:.1f}%，阈值 {limit:.0%}）")
        print("   ⟶ 先确认是不是正常重构；若不是，多半是**意外截断**（参见 tools/README.md 的《事故记录》）。")
    if gone:
        print(f"\n⚠️ {len(gone)} 个 MANIFEST 记录过的文件已不在磁盘（不判红；合法删除很多）：")
        for p in gone[:15]:
            print("   · " + p)
        if len(gone) > 15:
            print(f"   …其余 {len(gone) - 15} 个略")

    if bad:
        return 1
    print("\n✅ 无异常缩水；README 结构完好。")
    print("   （字节级校验另见 `shasum -a 256 -c MANIFEST.sha256`——它比大小更硬，"
          "但正常改动也会变红，故不作为每轮门。）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
