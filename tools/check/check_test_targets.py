#!/usr/bin/env python3
"""守卫：浏览器测试的默认目标**不能**指向某个部署副本。

为什么需要
==========
本仓库已因此**假绿三次**（测试对着旧构建通过，而工作区早已不同）：
  1. `test_scale_pages` / `test_tree_mode` 默认 `http://127.0.0.1:8891/emohealth/`，
     断言的是旧版的 `data-instview`；工作区早改成 `data-instmode` 却一直「通过」
  2. `check_deploy.js` 同样指向旧部署，本次改造后前端已不预载 `unlock-data.js`，
     它仍显示「解锁规则: 30」（旧 index.html 还预载着）
  3. `check_mobile_layout.js` / `test_multiscale_fetch` / `test_scale_export` 同样残留

这类问题**不会自我暴露**——脚本只是绿着，测的却是别的代码。所以固化成守卫。

判据
====
`tools/check/*.js` 里 `process.env.URL ||` 之后的目标：
  · ✅ 允许：`file://` 直开工作区（不依赖服务），或显式注释说明为何需要外部 URL
  · ❌ 禁止：`http://127.0.0.1:*`（除非该处有 `# allow-remote` 标记）
"""

from __future__ import annotations

import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from _root import find_root  # noqa: E402
ROOT = str(find_root())
CHECK = os.path.join(ROOT, "tools", "check")

URL_DEF = re.compile(r"const URL_ = process\.env\.URL \|\|(.{0,200}?);", re.S)
REMOTE = re.compile(r"https?://(?:127\.0\.0\.1|localhost)[:/]")


def main() -> int:
    bad, ok = [], 0
    for fn in sorted(os.listdir(CHECK)):
        if not fn.endswith(".js"):
            continue
        p = os.path.join(CHECK, fn)
        s = io.open(p, encoding="utf-8").read()
        m = URL_DEF.search(s)
        if not m:
            continue
        target = m.group(1)
        if REMOTE.search(target):
            # 允许显式标注的例外
            line_no = s[:m.start()].count("\n") + 1
            ctx = "\n".join(s.split("\n")[max(0, line_no - 4):line_no + 1])
            if "# allow-remote" in ctx:
                ok += 1
                continue
            bad.append((fn, line_no, target.strip()[:70]))
        else:
            ok += 1
    print(f"扫描 {CHECK}：✅ 合规 {ok} 个")
    if bad:
        print(f"\n❌ {len(bad)} 个测试的默认目标指向**部署副本**——会对着旧构建假绿：")
        for fn, ln, t in bad:
            print(f"    {fn}:{ln}  → {t}")
        print("\n修法：改为 file:// 直开工作区（参考 test_local_file.js），"
              "或加 `# allow-remote` 标注并说明理由。")
        return 1
    print("✅ 没有测试默认指向部署副本（都测工作区）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
