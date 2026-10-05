#!/usr/bin/env python3
"""修 `tools/legacy/fix_test_targets.py` 引入的转义 bug，并复核 C2 未判定。

事故
====
我用 `fix_test_targets.py` 把测试的默认目标从部署副本改为 `file://` 时，
替换文本里的正则写成了 `.replace(/\\/g, '/')` 的**错误转义**——Python 三引号
里 `\\\\` 落盘成 `\\`，再经 JS 解析就成了 `/\\/g` 的字面形态 `/\\/g`…实际落盘
是 `replace(/\\/g, '/')` 变体，最终 `node --check` 直接语法错误：

    'file:///' + ... .replace(/\\/g, '/');     ← 少一个反斜杠，`/` 未闭合

正确写法是 `/\\\\/g`（Python 里）→ 落盘 `/\\\\/g`（JS 源码里）→ 匹配一个反斜杠。

教训：**批量正则替换脚本必须对产物跑 `node --check` / 语法校验**，
否则「替换成功」的假象会一直留到别人跑测试时才炸。
"""

from __future__ import annotations

import io
import os
import subprocess
import sys

ROOT = r"C:\Codes\emohealth-20260930-full\emohealth"
FILES = ["tools/check/check_deploy.js", "tools/check/check_mobile_layout.js"]

# 落盘的坏形态（Python 源码里这样写）
BAD = ".replace(/\\/g, '/')"
# 正确形态：JS 源码里应为 .replace(/\\/g, '/')
GOOD = ".replace(/\\\\/g, '/')"

for rel in FILES:
    p = os.path.join(ROOT, rel.replace("/", os.sep))
    s = io.open(p, encoding="utf-8").read()
    if BAD in s:
        s = s.replace(BAD, GOOD)
        io.open(p, "w", encoding="utf-8").write(s)
        print(f"  ✓ 已修 {rel}")
    else:
        print(f"  · {rel} 未找到坏形态（可能已是好的）")
    r = subprocess.run(["node", "--check", p], capture_output=True, text=True)
    print(f"    node --check → {'✅ 通过' if r.returncode == 0 else '❌ ' + r.stderr.splitlines()[0][:90]}")

# 复核 C2 未判定
print("\n=== C2 未判定复核（tools/survey/）===")
out = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "check_architecture.py")],
                     capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
for ln in (out.stdout or "").splitlines():
    if "未判定" in ln or "survey/" in ln:
        print("  " + ln.strip()[:110])
