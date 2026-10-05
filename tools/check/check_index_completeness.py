#!/usr/bin/env python3
"""对账：`tools/README.md` 的索引表 vs 磁盘实际文件。

为什么需要
==========
索引的价值就是「与实际一致」。历史上已经出现过两次偏差（新增脚本没补录、
删除后没回改），而且**偏差是静默的**——没人会去数。所以把对账做成脚本。

判据：某文件被索引「录入」= 它的文件名在 README 中以 ``| `name` `` 表格单元格
或行内代码形态出现。只出现在说明文字里不算录入。
"""

from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from _root import find_root, force_utf8_io  # noqa: E402
ROOT = str(find_root())

SECTIONS = [("survey", "3.1"), ("build", "3.2"), ("analyze", "3.3"),
            ("check", "3.4"), ("ui", "3.5"), ("legacy", "3.6")]


def main() -> int:
    force_utf8_io()          # 入口第一件事：GBK 控制台下不许崩（见 tools/_root.py）
    md = open(os.path.join(ROOT, "tools", "README.md"), encoding="utf-8").read()
    # 索引条目的形态：表格行第一格是**反引号包的文件名（basename，不含 /）**。
    # ⚠️ 必须排除含 `/` 的形态：§5 之类的表格里写的是**完整路径**（如
    #    `tools/_root.py`），那是说明性引用、不是索引条目。第一版没排除，
    #    于是把 7 个基座文件全报成「索引里的悬空条目」（误报）。
    # 索引条目的形态：**表格行的第一格**被反引号包住的文件名。两种写法都算：
    #   形态 A（§3.x 各表）：`name.ext`
    #   形态 B（§5 基座表）：`tools/name.ext`
    # ⚠️ 只能认「第一格」：正文里提到的文件名（`adaptive-network.json` 等数据产物）
    #    是叙述，不是索引条目。我上一版把反引号里的文件名全收了，于是「悬空条目」
    #    虚增到 55 个（全是数据产物）。
    first_cell = re.findall(
        r"^\|\s*`(?:tools/)?([^`/\\]+\.(?:py|js|sh|json|md))`\s*\|", md, re.M)
    indexed = set(first_cell)
    print(f"README 索引条目：{len(indexed)} 个")
    # 索引自身不必录入自己
    SELF = {"README.md"}

    total_missing, total_extra = 0, 0
    for sub, sec in SECTIONS:
        d = os.path.join(ROOT, "tools", sub)
        if not os.path.isdir(d):
            continue
        actual = {f for f in os.listdir(d)
                  if os.path.isfile(os.path.join(d, f)) and f not in SELF}
        missing = sorted(actual - indexed)
        # 「多余」只在本节语境里判断：索引里有、但不在本目录也不在平铺层
        print(f"\n── tools/{sub}/　实际 {len(actual)} 个")
        if missing:
            total_missing += len(missing)
            for f in missing:
                print(f"    ❌ 未录入索引：{f}")
        else:
            print("    ✅ 全部已录入")
    # 平铺层
    flat = {f for f in os.listdir(os.path.join(ROOT, "tools"))
            if os.path.isfile(os.path.join(ROOT, "tools", f))} - SELF
    miss_flat = sorted(flat - indexed)
    print(f"\n── tools/（平铺）　实际 {len(flat)} 个")
    if miss_flat:
        total_missing += len(miss_flat)
        for f in miss_flat:
            print(f"    ❌ 未录入索引：{f}")
    else:
        print("    ✅ 全部已录入")

    # 索引里有、磁盘上没有 = 悬空条目
    on_disk = set()
    for sub, _ in SECTIONS:
        d = os.path.join(ROOT, "tools", sub)
        if os.path.isdir(d):
            on_disk |= set(os.listdir(d))
    on_disk |= flat
    # 索引里有、磁盘上没有 = 悬空条目。
    # ⚠️ 排除**根目录文档**（ARCHITECTURE.md、CLEANUP-PLAN.md、STALE-CLEANUP.md…）：
    #    它们不是 tools/ 的脚本，出现在表格里是交叉引用，不是索引条目。
    ROOT_DOCS = {"ARCHITECTURE.md", "CLEANUP-PLAN.md", "STALE-CLEANUP.md",
                 "README.md", "PLAN.md", "MANIFEST.txt", "MANIFEST.sha256"}
    stale = sorted(f for f in indexed if f not in on_disk and f not in ROOT_DOCS)
    if stale:
        total_extra = len(stale)
        print(f"\n── 索引里的悬空条目（磁盘上已无）{len(stale)} 个")
        for f in stale:
            print(f"    ❌ {f}")

    print()
    print(f"未录入 {total_missing} 个；悬空条目 {total_extra} 个")
    if total_missing or total_extra:
        print("❌ 索引与实际不一致")
        return 1
    print("✅ 索引与实际一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
