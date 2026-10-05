#!/usr/bin/env python3
"""把所有浏览器测试的默认目标从「某个部署副本」改为 **file:// 直开工作区**。

问题（同一坑第三次出现）
========================
测试若默认指向 `http://127.0.0.1:8891/emohealth/`（WSL 里的旧部署），就会
**对着旧构建假绿**——测的不是工作区代码。已实锤两次：
  · `test_scale_pages` / `test_tree_mode`：断言 `data-instview`（旧），
    而工作区早已改成 `data-instmode` → 换到工作区后立刻变红
  · `check_deploy.js`：本次改造后前端不再预载 `unlock-data.js`，
    但它指向旧部署，仍显示「解锁规则: 30」（旧 index.html 还预载着）
两者都只在换到工作区后才暴露。

本脚本把残留的 4 个改为 file:// 直开，并配套一个守卫
（`tools/check/check_test_targets.py`）防止再犯。
"""

from __future__ import annotations

import io
import os
import re
import sys

ROOT = r"C:\Codes\emohealth-20260930-full\emohealth"
CHECK = os.path.join(ROOT, "tools", "check")

# 目标写法：与 test_local_file.js 一致（file:// 直开工作区，不依赖任何服务）
NEW = """const ROOT_ = require('path').resolve(__dirname, '..', '..');
// ⚠️ 默认必须指向**工作区**，不能是某个部署副本——否则会对着旧构建**假绿**
//    （本仓库已因此踩过三次）。file:// 直开不依赖任何服务，测的就是工作区。
const URL_ = process.env.URL ||
  'file:///' + require('path').join(ROOT_, 'ui', 'index.html').replace(/\\\\/g, '/');"""

OLD_RE = re.compile(
    r"const URL_ = process\.env\.URL \|\| 'http://127\.0\.0\.1:8891/emohealth/';")

changed = []
for fn in sorted(os.listdir(CHECK)):
    if not fn.endswith(".js"):
        continue
    p = os.path.join(CHECK, fn)
    s = io.open(p, encoding="utf-8").read()
    if not OLD_RE.search(s):
        continue
    s2 = OLD_RE.sub(NEW, s, count=1)
    io.open(p, "w", encoding="utf-8").write(s2)
    changed.append(fn)
    print(f"  ✓ {fn}")

print(f"\n改 {len(changed)} 个：{changed}")
