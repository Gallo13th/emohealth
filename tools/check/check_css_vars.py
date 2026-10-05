#!/usr/bin/env python3
"""检查 `ui/index.html` 里被引用但**未定义**的 CSS 自定义属性。

为什么值得单独一个检查
======================
CSS 变量名写错**不会报任何错**：`stroke:var(--brand)` 在 `--brand` 不存在时
整条声明失效，元素退回默认样式。实测我写的多量表/天赋树样式里
10 处用了不存在的 `--brand`（项目里的真名是 `--accent`），于是：
  · 天赋树「可答」节点的描边没了 → 只剩一个**白色空心圈**
  · 与「锁定」节点的浅灰几乎分不出

用户看到的现象是「**根本没有任何高亮节点**」。这类 bug 靠肉眼看代码很难发现，
靠出图才能撞上——所以固化成检查。
"""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
HTML = os.path.join(ROOT, "ui", "index.html")

# 内联在 HTML 属性里的自定义属性也算定义（如 style="--x:1"）
DEF_RE = re.compile(r"(--[a-zA-Z0-9-]+)\s*:")
USE_RE = re.compile(r"var\(\s*(--[a-zA-Z0-9-]+)")


def main() -> int:
    src = open(HTML, encoding="utf-8").read()
    # 只看 CSS 与 HTML 属性里的定义；JS 字符串里出现的 `--x:` 不算（避免误判）
    defined = {m.group(1) for m in DEF_RE.finditer(src)}
    used = {m.group(1) for m in USE_RE.finditer(src)}
    missing = sorted(used - defined)

    print(f"自定义属性：定义 {len(defined)} 个，引用 {len(used)} 个")
    if missing:
        print(f"\n❌ {len(missing)} 个被引用但未定义（这些声明会**静默失效**）：")
        for v in missing:
            # 打印用到它的行，便于定位
            hits = [i + 1 for i, ln in enumerate(src.splitlines())
                    if f"var({v})" in ln]
            print(f"  {v}  出现在行 {hits[:6]}{' …' if len(hits) > 6 else ''}")
        print("\n（真要新增变量，请先在 :root 里定义；否则请改用已有变量）")
        return 1
    print("✅ 没有悬空的 CSS 变量引用")
    return 0


if __name__ == "__main__":
    sys.exit(main())
