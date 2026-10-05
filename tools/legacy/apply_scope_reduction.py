#!/usr/bin/env python3
"""执行范围裁剪：删除 5 个 IPIP-NEO5-20 与 2 个孤儿脚本，并把清单写进 SCOPE-REDUCTION.md。

为什么这么少
============
用户的授权范围很大，但**上一轮已删得很彻底**（实测 `content/`/`research/` 的孤儿为 0，
`tools/` 里只提被删量表、不提核心的脚本仅 4 个）。本脚本只处理确实成立的：

  ① 5 个 `IPIP-NEO5-20-*` 量表包 + 5 个 `ui/instruments/` 包 —— 不在核心清单里
  ② `tools/survey/fetch_hexaco_keys.py` —— HEXACO 专属（该量表数据已删）
  ③ `tools/ui/shoot_ei_tree.js` —— IPIP-EI 专属截图脚本（EI 已删）

**保留**（容易被误判为孤儿，实为核心/通用）：
  · `tools/check/check_tree_geometry.py` —— 检查**天赋树几何**（用户要保留的核心思想），
    只是 docstring 举了 IPIP-EI 的例子 → 改例子，不删文件
  · `tools/survey/probe_en_pool.py` —— 英文池探测，服务**翻译质量**（核心量表也用）

⚠️ `archive/` 不在范围内（用户未勾选，它是证据链）。
"""

from __future__ import annotations

import io
import os
import sys

ROOT = r"C:\Codes\emohealth-20260930-full\emohealth"

DELETE = [
    *(f"data/instruments/ipip-neo5-20-{k}.json" for k in
      ("agreeableness", "conscientiousness", "extraversion", "neuroticism",
       "openness-to-experience")),
    *(f"ui/instruments/ipip-neo5-20-{k}.js" for k in
      ("agreeableness", "conscientiousness", "extraversion", "neuroticism",
       "openness-to-experience")),
    "tools/survey/fetch_hexaco_keys.py",
    "tools/ui/shoot_ei_tree.js",
]

REASON = {
    "neo5-20": "IPIP-NEO5-20 子量表不在核心清单（核心是 IPIP-NEO-300 本体）",
    "fetch_hexaco_keys": "HEXACO 专属；该量表数据已删，脚本成孤儿",
    "shoot_ei_tree": "IPIP-EI 专属截图脚本；EI 已删",
}


def main() -> int:
    removed, rows = [], []
    for rel in DELETE:
        p = os.path.join(ROOT, rel.replace("/", os.sep))
        if not os.path.exists(p):
            rows.append((rel, 0, "（已不存在）"))
            continue
        sz = os.path.getsize(p)
        why = next((v for k, v in REASON.items() if k in rel), "")
        os.remove(p)
        removed.append(rel)
        rows.append((rel, sz, why))
        print(f"  ✗ {rel}  ({sz} B)  {why}")

    log = os.path.join(ROOT, "SCOPE-REDUCTION.md")
    with io.open(log, "a", encoding="utf-8") as fh:
        fh.write("\n## 本轮删除清单（Lead 执行）\n\n")
        fh.write("| 路径 | 大小 | 依据 |\n|---|---|---|\n")
        for rel, sz, why in rows:
            fh.write(f"| `{rel}` | {sz} B | {why} |\n")
        fh.write(f"\n共删 {len(removed)} 个文件。\n")
        fh.write("\n### 明确保留（易误判为孤儿）\n\n")
        fh.write("| 路径 | 为什么留 |\n|---|---|\n")
        fh.write("| `tools/check/check_tree_geometry.py` | 检查**天赋树几何**"
                 "（用户要保留的核心思想）；只是 docstring 举了 IPIP-EI 的例子 → 改例子不删文件 |\n")
        fh.write("| `tools/survey/probe_en_pool.py` | 英文池探测，服务**翻译质量**"
                 "（核心量表的翻译同样需要） |\n")
        fh.write("| `tools/check/check_deploy.js`、`check_mobile_layout.js` | "
                 "UI 与部署检查，与具体量表无关 |\n")
    print(f"\n删除 {len(removed)} 个文件；清单已追加到 SCOPE-REDUCTION.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
