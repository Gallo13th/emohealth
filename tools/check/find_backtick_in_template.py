#!/usr/bin/env python3
"""找出 `test_inference_ondemand.js` 里模板字符串**内部**的反引号。

背景：该测试用 ``ev(`(async () => { ... })()`)`` 的大模板串把代码送进浏览器。
模板串**内部**若出现未转义的反引号（尤其注释里的 markdown 行内代码），
会提前闭合模板串 → `SyntaxError: missing ) after argument list`。
我就这么踩过一次（注释里写了 `unlock-data.js`）。
"""

import io
import re
import sys

p = r"C:\Codes\emohealth-20260930-full\emohealth\tools\check\test_inference_ondemand.js"
lines = io.open(p, encoding="utf-8").read().split("\n")

# 找所有 ev(` 起点，逐字符扫到配对的反引号，报告内部出现的反引号
i = 0
found = 0
while i < len(lines):
    m = re.search(r"ev\(`", lines[i])
    if not m:
        i += 1
        continue
    start_line = i
    # 从该行 m.end() 之后开始扫
    col = {"line": i, "pos": m.end()}
    body_line = i
    j = m.end()
    closed = False
    while body_line < len(lines):
        text = lines[body_line]
        while j < len(text):
            ch = text[j]
            if ch == "\\":
                j += 2
                continue
            if ch == "`":
                closed = True
                break
            j += 1
        if closed:
            break
        body_line += 1
        j = 0
    print(f"  模板串起点 L{start_line + 1} → 闭合于 L{body_line + 1}")
    # 报告内部注释行里的反引号
    for k in range(start_line + 1, body_line + 1):
        t = lines[k]
        if "`" in t and t.strip().startswith("//"):
            print(f"    ❌ L{k + 1} 注释里有反引号：{t.strip()[:88]}")
            found += 1
    i = body_line + 1

print(f"\n内部注释里的反引号：{found} 处")
sys.exit(1 if found else 0)
