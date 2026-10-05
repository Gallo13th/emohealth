#!/usr/bin/env python3
"""把漏录的 5 个脚本补进 tools/README.md 的索引表，并修正计数。

⚠️ 归属说明（为什么在 `tools/legacy/` 而不在 `tools/build/`）
============================================================
它一度放在 `tools/build/`，于是被架构守卫判为 C3 违例——因为它的**插入文本**里
含 ``ui/**`` 这样的路径字面量（那是给人看的描述，不是真引用），而 C3 扫描
「数据层是否出现 ui/ 路径」。与其把描述文字改得别扭，不如按**性质**归类：这是
**文档维护的一次性工具**（跑完即完成使命），不是数据组织流水线的常规一环。

这与 `ARCHITECTURE.md` 记的那条原则一致：**分类依据是「它属于哪一层/什么性质」，
不是它叫什么名字**（`build_tier_layout.py` 归 `tools/ui/` 同理）。

为什么用脚本而不是手改
======================
① 表格是**按文件名排序**的，手工插入容易放错位置；脚本按字母序插稳。
② 计数散落在 §2/§3.x/§5 多处，手改会漏。脚本按磁盘实际数重算并核对。

插入的 5 个（`tools/check/check_index_completeness.py` 实测漏录）：
  §3.1 survey：survey_cross_layer.py、survey_stale_files.py
  §3.4 check ：check_index_completeness.py、verify_architecture_guard.py、
               verify_truncation_guard.py
"""

from __future__ import annotations

import os
import re
import sys

# 用 find_root 而不是数 `..` 层数：脚本换目录后层数会变（本项目已因此栽过几次）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = str(find_root())
MD = os.path.join(ROOT, "tools", "README.md")

NEW_ROWS = {
    "3.1": [
        ("survey_cross_layer.py",
         "测绘「跨层动作」：列出数据层写/读 `ui/**` 的全部位置与方向",
         "`tools/{build,analyze,ui,survey}/**`",
         "stdout（每处的层/脚本/行号/方向/目标）"),
        ("survey_stale_files.py",
         "测绘「过时失效文件」候选：临时缓存 / 空文件 / **迁移遗留**（用 "
         "`cleanup_manifest.json` 的 old→new 全树比对）/ 悬空路径字面量",
         "全树 + `tools/cleanup_manifest.json`",
         "stdout（四类候选，只测不删）"),
    ],
    "3.4": [
        ("check_index_completeness.py",
         "对账：`tools/README.md` 的索引表 vs 磁盘实际文件（未录入 / 悬空条目）",
         "`tools/README.md` + `tools/**`",
         "stdout；不一致则 exit 1"),
        ("verify_architecture_guard.py",
         "架构守卫的**正反验证**：临时沙盒植入应命中/不应命中/未判定的用例，"
         "确认守卫不是「变瞎后假绿」",
         "无（自建沙盒）",
         "stdout；17/17 用例符合预期才 exit 0"),
        ("verify_truncation_guard.py",
         "题文截断判据的正反验证：真实数据 0 条可疑 + 固定搭配不误报",
         "`data/instruments/*.json` + 被测判据",
         "stdout"),
    ],
}


def insert_rows(lines: list[str], sec: str, rows: list[tuple]) -> int:
    """在指定小节（如 "3.1"）的表格里按字母序插入行。"""
    # 找小节起止
    start = next((i for i, l in enumerate(lines)
                  if re.match(rf"^### {re.escape(sec)}\b", l)), None)
    if start is None:
        print(f"  ✗ 找不到小节 {sec}")
        return 0
    end = next((i for i in range(start + 1, len(lines))
                if re.match(r"^### ", lines[i])), len(lines))
    # 找表体的行号区间
    body = [i for i in range(start, end) if lines[i].startswith("|")]
    if not body:
        print(f"  ✗ 小节 {sec} 里没有表格")
        return 0
    added = 0
    for name, duty, inp, out in rows:
        new_line = f"| `{name}` | {duty} | {inp} | {out} |"
        # 找到第一个现有名字字母序大于它的行，插在它前面
        pos = None
        for i in body:
            m = re.match(r"\|\s*`(?:tools/)?([^`]+?)`", lines[i])
            if m and m.group(1) > name:
                pos = i
                break
        if pos is None:
            pos = body[-1] + 1
        lines.insert(pos, new_line)
        # 插入后重算行号区间（否则后续插入位置全偏）
        start = next(i for i, l in enumerate(lines)
                     if re.match(rf"^### {re.escape(sec)}\b", l))
        end = next((i for i in range(start + 1, len(lines))
                    if re.match(r"^### ", lines[i])), len(lines))
        body = [i for i in range(start, end) if lines[i].startswith("|")]
        print(f"  ✓ {sec} 插入 {name}")
        added += 1
    return added


def main() -> int:
    lines = open(MD, encoding="utf-8").read().split("\n")
    total = 0
    for sec, rows in NEW_ROWS.items():
        total += insert_rows(lines, sec, rows)

    md = "\n".join(lines)
    # 修正标题计数（按磁盘实际文件数）
    def count(sub):
        d = os.path.join(ROOT, "tools", sub)
        return len([f for f in os.listdir(d)
                    if os.path.isfile(os.path.join(d, f))])
    fixes = [
        (r"(### 3\.1 `tools/survey/`　[^（(]*[（(])\d+([）)])",
         rf"\g<1>{count('survey')}\g<2>", "3.1 survey"),
        (r"(### 3\.4 `tools/check/`　[^（(]*[（(])\d+([）)])",
         rf"\g<1>{count('check')}\g<2>", "3.4 check"),
        (r"(### 3\.2 `tools/build/`　[^（(]*[（(])\d+([）)])",
         rf"\g<1>{count('build')}\g<2>", "3.2 build"),
        (r"(### 3\.3 `tools/analyze/`　[^（(]*[（(])\d+([）)])",
         rf"\g<1>{count('analyze')}\g<2>", "3.3 analyze"),
        (r"(### 3\.5 `tools/ui/`　[^（(]*[（(])\d+([）)])",
         rf"\g<1>{count('ui')}\g<2>", "3.5 ui"),
        (r"(### 3\.6 `tools/legacy/`　[^（(]*[（(])\d+([）)])",
         rf"\g<1>{count('legacy')}\g<2>", "3.6 legacy"),
    ]
    for pat, rep, label in fixes:
        md, n = re.subn(pat, rep, md, count=1)
        print(f"  {'✓' if n else '·'} 标题计数 {label}")

    open(MD, "w", encoding="utf-8").write(md)
    print(f"\n共插入 {total} 行；标题计数按磁盘实际重算")
    return 0


if __name__ == "__main__":
    sys.exit(main())
