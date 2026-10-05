#!/usr/bin/env python3
"""查大五人格 300 题里，哪一条没进文本库。

修订记录（T-CONVERGE-B 收尾）
=============================
修了三个问题，都是「看起来在查、其实查不准」的类型：

① **读前端包**：原先读 ``ui/emohealth-data.js``。检查层不该依赖前端生成物
   （三层契约的精神），而且该文件是**有损瘦身变换**的产物。改为读源头
   ``data/scene-taxonomy.json``（`items[*].text_en` / `text_zh`，
   `build_ui_bundle.py` 也是从这里取中译的）。

② **norm 缺连字符归一 → 误报**：原先自己的 `norm()` 不做连字符转空格，而
   规范实现 ``tools/build/build_text_db.py:norm()`` 明确要求归一，其 docstring
   记录了实测原因：同一道题在不同来源里写作 ``hang gliding`` 与 ``hang-gliding``，
   不归一会**漏配中译**。结果是本脚本误报 2 条「未进文本库」（order 179/300），
   而这两条实际都在库里。
   → 改为**直接复用** `build_text_db.norm`，避免两套 norm 各自漂移
   （漂移的代价就是这种静默误报）。

③ 输出的「库里近似项」查找也改用同一个 norm。
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()

# 复用规范实现，别再写一份（这是问题②的根因）
sys.path.insert(0, os.path.join(ROOT, "tools", "build"))
from build_text_db import norm  # noqa: E402


def main() -> int:
    tax = json.load(open(os.path.join(ROOT, "data", "scene-taxonomy.json"),
                         encoding="utf-8"))
    items = tax["items"]
    db = json.load(open(os.path.join(ROOT, "data", "text-db", "text-db.json"),
                        encoding="utf-8"))
    entries = db["entries"]

    rows = items.values() if isinstance(items, dict) else items
    missing = []
    for row in rows:
        en = (row.get("text_en") or "").strip()
        zh = row.get("text_zh") or ""
        order = row.get("order")
        if not en:
            missing.append((order, "(无英文)", zh))
            continue
        if norm(en) not in entries:
            missing.append((order, en, zh))

    print(f"大五人格里未进文本库的条目：{len(missing)}")
    for order, en, zh in missing:
        print(f"  order={order}")
        print(f"    en: {en}")
        print(f"    zh: {zh}")
        key = norm(en)[:14]
        if key:
            for k in entries:
                if key in k:
                    print(f"    库里近似: {k[:70]}")
                    break
    # 覆盖数一并报出，便于与 check_text_db 对账
    total = len(list(rows))
    print(f"（源头条目 {total} 条；文本库 {len(entries)} 条）")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
