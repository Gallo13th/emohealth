#!/usr/bin/env python3
"""守卫：量表包的**题面与选项**不得含下列四类污染（2026-10-04 起）。

为什么要有这条守卫
==================
`task-12` 登记、`task-14` 修复的 DSM-5-TR 缺陷都有一个共同特征：
**它们长得像正常数据**。题面末尾挂一条页脚授权声明、题面里混一个 `\\x00`、
题面被截断成半句——没有任何异常值、没有报错、也没有 `\\ufffd`，
只有人逐条读才会发现。所以必须机械地扫。

四类判据（都来自真实踩过的坑）：
  ① **控制字符**：睡眠册第 1/5 题残留 `\\x00`（框字形 `\\x00‰` 只清掉了一半）
  ② **混入授权句**：L1 第 23 题末尾被拼进了页脚
     `Copyright © 2013 American Psychiatric Association. All Rights Reserved.`
  ③ **方括号不配对**：题面被截断的征兆（L1 第 23 题断在 `or m`）
  ④ **以省略号结尾**：另一种截断征兆（用于人工复核，可用 allowlist 放行）

用法：`python tools/check/check_dsm_item_text.py`（有污染则 exit 1）
"""

from __future__ import annotations

import glob
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()

COPYRIGHT_MARKERS = ("Copyright ©", "All Rights Reserved",
                     "This material can be reproduced",
                     "Rights holder", "©2008-2012 PROMIS")

# ④ 合法地以省略号结尾的题面（逐条人工确认过；没有就留空）
ELLIPSIS_OK: set[tuple[str, int]] = set()


def ctrl(text: str) -> list[str]:
    """返回除 \\t\\n\\r 外的控制字符（十六进制）。"""
    return [f"U+{ord(c):04X}" for c in text
            if ord(c) < 0x20 and c not in "\t\n\r"]


def scan_pkg(path: str) -> list[str]:
    code = os.path.basename(path)
    doc = json.load(io.open(path, encoding="utf-8"))
    bad: list[str] = []
    for it in doc.get("items", []):
        order = it.get("order")
        for field in ("text",):
            t = it.get(field) or ""
            if ctrl(t):
                bad.append(f"{code} 题 {order}.{field} 含控制字符 {ctrl(t)}：{t!r}")
            for m in COPYRIGHT_MARKERS:
                if m in t:
                    bad.append(f"{code} 题 {order}.{field} 混入授权句（{m}）：{t[-70:]!r}")
            if t.count("[") != t.count("]"):
                bad.append(f"{code} 题 {order}.{field} 方括号不配对：{t[-70:]!r}")
            if t.rstrip().endswith(("...", "…")) and (code, order) not in ELLIPSIS_OK:
                bad.append(f"{code} 题 {order}.{field} 以省略号结尾（疑似截断）：{t[-70:]!r}")
        for o in it.get("options", []) or []:
            ot = (o or {}).get("text") or ""
            if ctrl(ot):
                bad.append(f"{code} 题 {order} 选项 {o.get('v')} 含控制字符：{ot!r}")
            if any(g in ot for g in ("❑", "‰")):
                bad.append(f"{code} 题 {order} 选项 {o.get('v')} 残留选择框字形：{ot!r}")
    # 选项位置：**规范位置是 `items[].options`**。`provenance.item_options`
    # 是过渡期的兼容镜像，**已于 2026-10-04 删除**——镜像一旦重新出现就是
    # 「第二个真相源」，所以这里断言它**不存在**。
    # ⚠️ 判据必须是「不得存在镜像」：删镜像后若仍写「两者一致」，
    #    `prov` 为 None 时旧写法会直接跳过，等于守卫变瞎。
    prov = (doc.get("provenance") or {}).get("item_options")
    if prov is not None:
        bad.append(f"{code}: 仍存在已废弃的镜像 provenance.item_options"
                   f"（规范位置是 items[].options；镜像已于 2026-10-04 删除，"
                   f"重新出现即为第二个真相源）")
    # L1 专用不变量：手册 23 题**每一题都是问句**，必以 `?` 结尾。
    # 这条比「方括号配对」更早命中：L1 第 23 题被截断成 `…or m` 时，
    # 文本里根本不含方括号，配对数相等（0==0），单靠规则③会漏。
    if code == "dsm5tr-l1.json":
        for it in doc.get("items", []):
            t = (it.get("text") or "").rstrip()
            if not t.endswith("?"):
                bad.append(f"{code} 题 {it.get('order')} 不以问号结尾"
                           f"（截断征兆）：{t[-70:]!r}")
    return bad


def main() -> int:
    files = sorted(glob.glob(os.path.join(ROOT, "data", "instruments", "*.json")))
    files = [f for f in files if os.path.basename(f) != "catalog.json"]
    total: list[str] = []
    for f in files:
        total += scan_pkg(f)
    print(f"扫描 {len(files)} 个量表包")
    for b in total:
        print("  ❌ " + b)
    if total:
        print(f"\n❌ {len(total)} 处污染")
        return 1
    print("✅ 题面与选项无控制字符、无授权句、方括号配对、无以省略号结尾")
    return 0


if __name__ == "__main__":
    sys.exit(main())
