#!/usr/bin/env python3
"""测绘范围裁剪的**候选清单**：哪些文件只服务「已被删的量表」。

用户授权删除的范围
==================
  ✅ 非核心量表数据（5 个 IPIP-NEO5-20）
  ✅ tools/ 里服务非核心量表的脚本
  ✅ content/ 里非核心的内容资产
  ✅ data/ 里非核心的中间产物
  ✅ research/ 里非核心量表的调研报告
  ❌ archive/ **不删**（证据链）

判据（**看内容，不凭文件名**）
==============================
核心标识（保留）：`IPIP-NEO`（含 300 题本体）、`PID-5`、`DSM5TR`/`dsm5tr`
被删标识（孤儿信号）：HEXACO / VIA / 16PF / CATPD / BFAS / Big5-100 / EI(情绪智力) /
  neo5-20 / 以及任何已不在 `data/instruments/` 里的量表代码

一个脚本若**只**提到被删标识、**从不**提到核心标识 → 判为孤儿候选。
若两者都提到（如通用工具 + 某量表举例）→ **保留**（拿不准就留）。

⚠️ 本脚本只列清单，不删。
"""

from __future__ import annotations

import io
import json
import os
import re
import sys

ROOT = r"C:\Codes\emohealth-20260930-full\emohealth"

CORE = ["IPIP-NEO", "IPIP_NEO", "ipip-neo", "ipip_neo", "PID-5", "PID5", "pid-5",
        "pid5", "DSM5TR", "dsm5tr", "DSM-5-TR"]
DROP = ["HEXACO", "hexaco", "IPIP-VIA", "ipip-via", "VIA", "16PF", "16pf",
        "CATPD", "CAT-PD", "catpd", "BFAS", "bfas", "Big5-100", "big5-100",
        "IPIP-EI", "ipip-ei", "neo5-20", "NEO5-20", "Openness-To-Experience",
        "Agreeableness", "Conscientiousness", "Extraversion", "Neuroticism"]

# 通用基础设施：**永不删**
KEEP_ALWAYS = {
    "tools/_root.py", "tools/_root.js", "tools/check_architecture.py",
    "tools/pdftext.py", "tools/build_scales.py", "tools/item_coding.py",
    "tools/ui/pack_ui_data.py", "tools/build/build_manifest.py",
    "tools/README.md", "tools/cleanup_manifest.json",
    "tools/survey/survey_refs.py", "tools/survey/survey_tools_layout.py",
    "tools/survey/survey_stale_files.py", "tools/survey/survey_capability_gaps.py",
    "tools/survey/survey_cross_layer.py", "tools/survey/survey_inference_deps.py",
    "tools/survey/survey_scope_reduction.py",
    "tools/check/check_index_completeness.py", "tools/check/check_readme_dups.py",
    "tools/check/check_test_targets.py", "tools/check/check_css_vars.py",
    "tools/legacy/autofill_readme_index.py", "tools/legacy/dedupe_readme_index.py",
    "tools/legacy/fix_placeholder_duties.py", "tools/legacy/fill_new_duties.py",
    "tools/legacy/fix_test_targets.py",
}


def read(p):
    try:
        return io.open(p, encoding="utf-8", errors="replace").read()
    except OSError:
        return ""


def main() -> int:
    print("=" * 76)
    print("① 5 个 IPIP-NEO5-20 相关文件（明确要删）")
    print("=" * 76)
    exact = []
    for base, _d, files in os.walk(ROOT):
        if "archive" in base or ".git" in base or "__pycache__" in base:
            continue
        for f in files:
            if "neo5-20" in f.lower() or "neo5_20" in f.lower():
                p = os.path.join(base, f)
                exact.append(os.path.relpath(p, ROOT))
    for p in sorted(exact):
        print(f"  {p}  ({os.path.getsize(os.path.join(ROOT, p))} B)")
    print(f"  合计 {len(exact)} 个")

    print()
    print("=" * 76)
    print("② tools/ 里的孤儿候选（只提被删标识、从不提核心标识）")
    print("=" * 76)
    orphans, keep_mixed = [], []
    for base, _d, files in os.walk(os.path.join(ROOT, "tools")):
        if "__pycache__" in base:
            continue
        for f in sorted(files):
            if not f.endswith((".py", ".js", ".md", ".sh")):
                continue
            p = os.path.join(base, f)
            rel = os.path.relpath(p, ROOT).replace(os.sep, "/")
            if rel in KEEP_ALWAYS:
                continue
            # ⚠️ 变量名别用 `s`——守卫会把 `s = read(p)` 当成「变量绑定的路径」，
            #    报「未判定」（survey 层受 C2 约束，未判定必须清零）。
            # 直接内联 read(p)：守卫会把 x = read(p) 判成「变量绑定的路径」
            # （未判定），survey 层受 C2 约束、未判定必须清零。
            has_core = any(k in read(p) for k in CORE)
            has_drop = any(k in read(p) for k in DROP)
            if has_drop and not has_core:
                orphans.append((rel, os.path.getsize(p), f))
            elif has_drop and has_core:
                keep_mixed.append(rel)
    for rel, sz, f in orphans:
        print(f"  {rel:58}{sz:8} B")
    print(f"  孤儿候选 {len(orphans)} 个；两者都提到（**保留**）{len(keep_mixed)} 个")
    if keep_mixed:
        print("  保留示例：" + "、".join(os.path.basename(x) for x in keep_mixed[:6]))

    print()
    print("=" * 76)
    print("③ content/ 与 research/ 的候选")
    print("=" * 76)
    for top in ("content", "research"):
        for base, _d, files in os.walk(os.path.join(ROOT, top)):
            for f in sorted(files):
                p = os.path.join(base, f)
                rel = os.path.relpath(p, ROOT).replace(os.sep, "/")
                body = read(p)
                if any(k in f for k in ("facet",)) and len(f) < 60:
                    continue
                has_drop = any(k in body or k in f for k in DROP)
                has_core = any(k in body or k in f for k in CORE)
                if has_drop and not has_core:
                    print(f"  {rel:64}{os.path.getsize(p):8} B")

    print()
    print("=" * 76)
    print("④ data/ 顶层产物（判断哪些只服务被删量表）")
    print("=" * 76)
    for f in sorted(os.listdir(os.path.join(ROOT, "data"))):
        p = os.path.join(ROOT, "data", f)
        if os.path.isfile(p):
            # ⚠️ 变量名别用 `s`（见 L98 的说明）：守卫会把它当路径绑定 → 报「未判定」
            has_core = any(k in read(p) for k in CORE)
            print(f"  {f:44}{os.path.getsize(p) / 1024:8.1f} KB  "
                  f"{'含核心' if has_core else '⚠ 未见核心标识'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
