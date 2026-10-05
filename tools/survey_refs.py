#!/usr/bin/env python3
"""测出 tools/ 下哪些脚本**被其它文件引用**，作为「能否安全移动」的依据。

为什么先测这个
==============
移动文件的风险不在文件本身，而在**引用**。本项目里有三类引用：

  ① Python ``import``（如 ``from pdftext import PdfDoc``）
  ② 脚本互相调用（``subprocess`` 调 ``tools/xxx.py``，或字符串里出现文件名）
  ③ 文档/测试里的路径（``node tools/xxx.js``、`python tools/xxx.py`）

**没有被任何文件引用的脚本可以安全搬到子目录**；被引用的必须先统一改引用点，
否则「清理」会变成「破坏」。本脚本只测量，不改动。

输出：``--json`` 时打印机器可读的统计。
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 扫描范围：脚本、文档、配置（这些地方可能引用 tools/ 下的文件）
SCAN_DIRS = ["tools", "engine", "content", "ui"]
SCAN_FILES = ["README.md", "PLAN.md", "ARCHITECTURE.md", "instrument-record.schema.md"]
SCAN_EXT = (".py", ".js", ".md", ".json", ".txt", ".html")


def list_tools() -> list[str]:
    """列出 ``tools/`` 下的脚本，路径相对 ``tools/``（如 ``build/build_scales.py``）。

    迁移后脚本按职责分居 ``tools/{survey,build,analyze,check,ui,legacy}/``，
    所以这里**递归**列举；平铺的共享库与守卫仍以 ``xxx.py`` 形式出现。
    """
    base = os.path.join(ROOT, "tools")
    out = []
    for dp, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in ("__pycache__",)]
        for f in files:
            out.append(os.path.relpath(os.path.join(dp, f), base).replace(os.sep, "/"))
    return sorted(out)


def main() -> int:
    tools = list_tools()
    # 注意：按「完整文件名」建表，不能按 stem 建 dict——`_root.py` 与 `_root.js`
    # 的 stem 相同，用 dict 会互相覆盖，导致其中一份永远测不出引用者。
    entries = [(os.path.splitext(os.path.basename(f))[0], f) for f in tools]

    refs: dict[str, set[str]] = defaultdict(set)      # 被引用者 -> 引用者集合
    scanned = 0
    targets = []
    for d in SCAN_DIRS:
        for base, _dirs, files in os.walk(os.path.join(ROOT, d)):
            for fn in files:
                if fn.endswith(SCAN_EXT):
                    targets.append(os.path.join(base, fn))
    for fn in SCAN_FILES:
        p = os.path.join(ROOT, fn)
        if os.path.exists(p):
            targets.append(p)

    for p in targets:
        try:
            txt = open(p, encoding="utf-8", errors="replace").read()
        except Exception:                                     # noqa: BLE001
            continue
        scanned += 1
        me = os.path.relpath(p, ROOT)
        for stem, fname in entries:
            # 只认「像引用」的出现：import stem / tools/<path> / <basename>
            if re.search(rf"(?:^|\s|/|\"|')(?:from|import)\s+{re.escape(stem)}\b", txt) \
               or f"tools/{fname}" in txt or f"/{fname}" in txt \
               or re.search(rf"\b{re.escape(os.path.basename(fname))}\b", txt):
                if f"tools/{fname}" != me.replace(os.sep, "/"):
                    refs[fname].add(me)

    free = [f for f in tools if f not in refs]
    used = {f: sorted(v) for f, v in refs.items() if f in tools}
    print(f"扫描 {scanned} 个文件")
    print(f"tools/ 共 {len(tools)} 个脚本："
          f"**无引用（可安全移动）{len(free)} 个**，被引用 {len(used)} 个\n")
    print("── 无引用（可移动）")
    for f in free:
        print("   ", f)
    print("\n── 被引用（移动需同步改引用点；列前 3 个引用者）")
    for f in sorted(used):
        print(f"    {f:48} ← {', '.join(used[f][:3])}")
    if "--json" in sys.argv:
        print("\n" + json.dumps({"free": free, "used": used},
                                ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
