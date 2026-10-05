#!/usr/bin/env python3
"""把**未录入索引**的脚本自动补进 `tools/README.md` 对应小节，并重算标题计数。

为什么重写
==========
原 `patch_readme_index.py` 的待补条目是**硬编码清单**，所以只能补它认识的那几个；
新脚本一多就漏（实测：又漏了 4 个）。本脚本改为**自动发现**——凡是磁盘上有、
索引里没有的，一律补进它所在子目录对应的小节，按字母序插入。

⚠️ 本脚本**幂等**（原 patch 脚本没有幂等检查，连跑两次会插两遍，我踩过）：
   已有的条目不重复插入。

配套：`tools/check/check_index_completeness.py` 负责对账，
      `tools/legacy/dedupe_readme_index.py` 负责兜底去重。
"""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = str(find_root())
MD = os.path.join(ROOT, "tools", "README.md")

# 子目录 → 小节号（与 README 的 §3.x 一致）
SEC_OF = {"survey": "3.1", "build": "3.2", "analyze": "3.3",
          "check": "3.4", "ui": "3.5", "legacy": "3.6"}
H3 = re.compile(r"^### ([0-9.]+)\s")
ITEM = re.compile(r"^\|\s*`(?:tools/)?([^`/\\]+)`\s*\|")


def section_span(lines, sec):
    for i, l in enumerate(lines):
        m = H3.match(l)
        if m and m.group(1) == sec:
            end = next((j for j in range(i + 1, len(lines)) if H3.match(lines[j])),
                       len(lines))
            return i, end
    return None, None


def main() -> int:
    lines = open(MD, encoding="utf-8").read().split("\n")

    # 已录入的条目名（表格行第一格）
    indexed = set()
    for l in lines:
        m = ITEM.match(l)
        if m:
            indexed.add(m.group(1))

    # 磁盘上的脚本，按子目录分组
    added = 0
    for sub, sec in SEC_OF.items():
        d = os.path.join(ROOT, "tools", sub)
        if not os.path.isdir(d):
            continue
        missing = sorted(f for f in os.listdir(d)
                         if os.path.isfile(os.path.join(d, f)) and f not in indexed)
        if not missing:
            continue
        for name in missing:
            start, end = section_span(lines, sec)
            if start is None:
                print(f"  ✗ 找不到小节 {sec}")
                break
            # 幂等：再确认一次（插入过程中 indexed 会更新，但保险）
            if any(ITEM.match(l) and ITEM.match(l).group(1) == name
                   for l in lines[start:end]):
                continue
            # 职责写在索引里要有意义；这里给占位说明并提示补写
            row = (f"| `{name}` | （**待补写职责**——自动录入，请打开脚本读 docstring "
                   f"后改这里） | 见脚本 | 见脚本 |")
            body = [i for i in range(start, end) if ITEM.match(lines[i])]
            pos = None
            for i in body:
                m = ITEM.match(lines[i])
                if m and m.group(1) > name:
                    pos = i
                    break
            if pos is None:
                pos = (body[-1] + 1) if body else end
            lines.insert(pos, row)
            indexed.add(name)
            added += 1
            print(f"  + §{sec} {name}")

    # 平铺层（归 §3.7）
    flat = sorted(f for f in os.listdir(os.path.join(ROOT, "tools"))
                  if os.path.isfile(os.path.join(ROOT, "tools", f))
                  and f not in indexed and f != "README.md")
    if flat:
        start, end = section_span(lines, "3.7")
        if start is not None:
            for name in flat:
                row = (f"| `{name}` | （**待补写职责**——自动录入，请打开脚本读 "
                       f"docstring 后改这里） | 见脚本 | 见脚本 |")
                body = [i for i in range(start, end) if ITEM.match(lines[i])]
                lines.insert((body[-1] + 1) if body else end, row)
                indexed.add(name)
                added += 1
                print(f"  + §3.7 {name}")

    md = "\n".join(lines)
    # 标题计数按磁盘实际重算
    for sub, sec in SEC_OF.items():
        d = os.path.join(ROOT, "tools", sub)
        n = len([f for f in os.listdir(d) if os.path.isfile(os.path.join(d, f))])
        md, cnt = re.subn(rf"(^### {re.escape(sec)} .*?[（(])\d+([）)])",
                          rf"\g<1>{n}\g<2>", md, count=1, flags=re.M)
        if cnt:
            print(f"  ✓ §{sec} 标题计数 → {n}")

    open(MD, "w", encoding="utf-8").write(md)
    print(f"\n补录 {added} 条（幂等；已有条目不会重复插入）")
    print("⚠️ 自动录入的条目职责是占位文字，请读 docstring 后补写。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
