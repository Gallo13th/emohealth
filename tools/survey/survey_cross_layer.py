#!/usr/bin/env python3
"""精确测绘「跨层动作」：数据层脚本写/读 `ui/**` 的全部位置。

背景：三层契约（C1/C2/C3）已在 ARCHITECTURE.md 定义，守卫也建好了，但
`tools/build/**`（数据层）里仍有脚本直接写 `ui/*.js` 生成包、以及一处直接
**读** `ui/emohealth-data.js`。本轮要把它们收敛：数据层只出 `data/`，
`ui/` 的 `.js` 包改由前端层（`tools/ui/`）从 `data/` 生成。

本脚本只测绘，不改动。输出每处的：脚本、方向（读/写）、目标、行号、代码。
"""

from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

LAYERS = {
    "build": ["tools/build"],
    "analyze": ["tools/analyze"],
    "ui": ["tools/ui"],
    "survey": ["tools/survey"],
}

# 匹配 ui/ 路径字面量（含 w/ 写、open(...,"w")、write_text 等）
UI_PATH = re.compile(r"""["'](?:\.\./)*ui/([A-Za-z0-9_\-./]+)["']""")
WRITE_HINT = re.compile(r"""open\s*\([^)]*['"]w|write_text|writeFileSync|mkdirSync|
                             \.write\s*\(|json\.dump""", re.X)


def main() -> int:
    rows = []
    for layer, dirs in LAYERS.items():
        for d in dirs:
            base = os.path.join(ROOT, d)
            if not os.path.isdir(base):
                continue
            for fn in sorted(os.listdir(base)):
                if not fn.endswith((".py", ".js", ".sh")):
                    continue
                p = os.path.join(base, fn)
                lines = open(p, encoding="utf-8", errors="replace").read().split("\n")
                for i, line in enumerate(lines, 1):
                    for m in UI_PATH.finditer(line):
                        target = "ui/" + m.group(1)
                        # 判断方向：同段落里出现写意图 → 写，否则读
                        ctx = "\n".join(lines[max(0, i - 4):i + 3])
                        is_write = bool(WRITE_HINT.search(ctx))
                        # 生成产物豁免
                        if re.search(r"ui/(instruments|tree-layouts)/", target):
                            kind = "产物"
                        else:
                            kind = "写" if is_write else "读"
                        rows.append({"layer": layer, "file": f"{d}/{fn}",
                                     "line": i, "target": target, "kind": kind,
                                     "code": line.strip()[:96]})
    print(f"{'层':8}{'脚本':42}{'行':>5} {'向':4} {'目标'}")
    for r in rows:
        print(f"{r['layer']:8}{r['file']:42}{r['line']:>5} {r['kind']:4} "
              f"{r['target']}")
    print()
    for layer in ("build", "analyze"):
        w = [r for r in rows if r["layer"] == layer and r["kind"] == "写"]
        rd = [r for r in rows if r["layer"] == layer and r["kind"] == "读"]
        print(f"{layer}: 写 ui/ {len(w)} 处，读 ui/ {len(rd)} 处（不含生成产物）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
