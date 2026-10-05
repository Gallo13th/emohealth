#!/usr/bin/env python3
"""修范围裁剪后的索引：删 2 行悬空条目、补写 7 条新脚本职责。

悬空的是 `build_catpd_reverse_keys.py` / `build_hexaco_direction_evidence.py`
（脚本已在更早的裁剪里删掉，索引行还在）——**索引指向不存在的文件**会让
`check_index_completeness.py` 报错，也会误导后续的人去找这些脚本。
"""

from __future__ import annotations

import io
import os
import sys

ROOT = r"C:\Codes\emohealth-20260930-full\emohealth"
MD = os.path.join(ROOT, "tools", "README.md")

DANGLING = ("build_catpd_reverse_keys.py", "build_hexaco_direction_evidence.py")
PLACEHOLDER = "（**待补写职责**——自动录入，请打开脚本读 docstring 后改这里）"

DUTIES = {
    "survey_orphans.py": "测绘范围裁剪的孤儿候选：只提被删量表标识、从不提核心标识的脚本或资产",
    "survey_scope_reduction.py": "测绘「保留 4 个核心、其余全删」的影响面：保留/删除清单与各目录规模",
    "check_test_targets.py": "守卫：浏览器测试的默认目标不得指向部署副本（否则对着旧构建假绿）",
    "find_backtick_in_template.py": "查模板字符串内部有没有未转义的反引号（会提前闭合模板串，报 missing ) 错）",
    "apply_scope_reduction.py": "执行范围裁剪：删 5 个 IPIP-NEO5-20 与 2 个孤儿脚本，清单写进 SCOPE-REDUCTION.md",
    "fix_test_counts.py": "把测试里写死的量表套数改为从 catalog 动态读（避免每次裁剪都要手改）",
    "fix_test_targets.py": "批量把测试的默认目标从部署副本改为 file:// 直开工作区",
    "fill_new_duties.py": "补写索引里新录入条目的占位职责（本脚本自己那条也由它补）",
    "fix_index_after_reduction.py": "范围裁剪后修索引：删指向已删脚本的悬空条目、补写新脚本职责",
}


def main() -> int:
    lines = io.open(MD, encoding="utf-8").read().split("\n")
    out, dropped, filled = [], 0, 0
    for ln in lines:
        if any(d in ln for d in DANGLING) and ln.strip().startswith("|"):
            dropped += 1
            continue
        if PLACEHOLDER in ln and ln.strip().startswith("|"):
            name = None
            for k in DUTIES:
                if f"`{k}`" in ln:
                    name = k
                    break
            if name:
                parts = ln.split("|")
                # 结构：['', ' `name` ', ' 职责 ', ' 输入 ', ' 输出 ', '']
                if len(parts) >= 5:
                    parts[2] = f" {DUTIES[name]} "
                    parts[3] = " 见脚本 docstring "
                    parts[4] = " 见脚本 docstring "
                    out.append("|".join(parts))
                    filled += 1
                    continue
        out.append(ln)
    io.open(MD, "w", encoding="utf-8").write("\n".join(out))
    print(f"  删除悬空条目 {dropped} 行；补写职责 {filled} 条")
    left = sum(1 for ln in out if PLACEHOLDER in ln)
    print(f"  剩余占位 {left} 处")
    return 0


if __name__ == "__main__":
    sys.exit(main())
