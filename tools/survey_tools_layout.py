#!/usr/bin/env python3
"""为清理方案做现状测绘：按**职责**给 tools/ 下所有脚本分类。

分类口径（对应要解耦的三件事 + 支撑）
  survey   文献调研与获取（fetch_/extract_/probe_/archive_/list_）
  build    数据组织（build_/convert_ 从归档产出 data/）
  analyze  统计与表格再组织（analyze_/optimize_/validate_ 设计类）
  check    守卫与校验（check_/test_/verify_）
  ui       前端生成与预览（*_ui*/serve_/shoot_/sync_/dev_）
  other    未归类（需人工判断）

**迁移后**（T2–T5 已执行）脚本已按职责住在 `tools/<cat>/`，本脚本改为**递归**遍历，
并同时打印「前缀初筛」与「实际所在目录」，把两者不一致的条目单独列出——
按 `tools/README.md` 的定案原则：**初筛用前缀，定案用契约**，不一致必须看得见。

只输出分类结果，不改任何文件。
"""

from __future__ import annotations

import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RULES = [
    ("survey", r"^(fetch|extract|probe|archive|list|survey|import)_"),
    ("analyze", r"^(analyze|optimize|compute|calibrate|design)_"),
    ("check", r"^(check|test|verify|validate)_"),
    ("ui", r"^(build_ui|build_tier_ui|serve_|shoot_|sync_|dev_|render_)"),
    ("build", r"^(build_|convert_)"),
]


def classify(name: str) -> str:
    for cat, pat in RULES:
        if re.search(pat, name):
            return cat
    return "other"


def main() -> int:
    base = os.path.join(ROOT, "tools")
    files = []
    for dp, dirs, fns in os.walk(base):
        dirs[:] = [d for d in dirs if d not in ("__pycache__",)]
        for f in sorted(fns):
            rel = os.path.relpath(os.path.join(dp, f), base).replace(os.sep, "/")
            if rel == "README.md":
                continue
            files.append(rel)

    groups: dict[str, list[str]] = defaultdict(list)
    for f in files:
        groups[classify(os.path.basename(f))].append(f)

    order = ["survey", "build", "analyze", "check", "ui", "other"]
    print(f"tools/ 共 {len(files)} 个文件（递归）\n")
    for cat in order:
        fs = groups.get(cat, [])
        print(f"── 前缀初筛 {cat}（{len(fs)}）")
        for f in fs:
            home = os.path.dirname(f) or "(平铺)"
            print(f"    {f:52} 实际目录 {home}")
        print()

    flat = [f for f in files if "/" not in f]
    print(f"平铺在 tools/ 的 {len(flat)} 个：")
    for f in flat:
        print("   ", f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
