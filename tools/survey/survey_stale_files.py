#!/usr/bin/env python3
"""测绘「过时失效文件」候选，分四类，**只测不删**。

清理的前提是证据，所以每类都要给出「为什么判定它过时/失效」：

  A 失效的可执行物  —— 跑起来就报错的测试/脚本（需人工确认，本脚本只列候选）
  B 悬空引用        —— 指向不存在路径的引用，含**迁移遗留**（主要来源）
  C 临时与缓存      —— .tmp* / __pycache__ / *.pyc / 编辑器残留
  D 空文件          —— 0 字节

⚠️ 判定为「候选」不等于该删。删之前必须确认：不是入口、不被引用、
   不是文档承诺的资产、不是 archive/ 里的证据。

修订记录（2026-10-03，第 2 版）
==============================
B 类第一版只用「**被引号包住的路径**」正则，实测**漏报 400+ 处**：
注释、JSON 的 `_note`、生成物文件头的 provenance 里大量引用是**不带引号**的
（如 `# 生成器 tools/build_ui_instruments.py`、`"_source": "tools/parse_uk_norms.py"`），
引号口径一个都抓不到——而「漏报」在清理场景里比误报危险得多（会留下断链）。

第 2 版改用**两条互补的判据**：
  ① **迁移账本比对**（主）：读 `tools/cleanup_manifest.json` 的 153 条 `old → new`，
     全树扫描**任何**位置的旧路径出现（不限引号、不限上下文），报出仍指旧路径的行。
     这是「迁移遗留」的权威判据——账本本身就是事实来源。
  ② **路径字面量存在性**（辅）：覆盖非迁移原因造成的悬空（手写路径写错、文件被删）。
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# ⚠️ 本脚本在 tools/survey/ 下，上退两层只到 tools/。第一版就这么写错，
#    结果把**存在**的 data/ipip-neo-300.json 全报成「悬空引用」。
#    统一用 find_root()（向上找 MANIFEST.sha256）才是对的。
sys.path.insert(0, os.path.join(ROOT, "tools"))
from _root import find_root  # noqa: E402
ROOT = str(find_root())

SKIP_DIRS = {"archive", ".git", "node_modules", ".shots", "__pycache__"}
SCAN_EXT = (".py", ".js", ".mjs", ".cjs", ".ts", ".md", ".json", ".sh",
            ".html", ".css", ".txt", ".yaml", ".yml", ".toml")

# 账本自身与测量工具会把旧路径当「数据」记录，不算遗留
EXEMPT_FILES = {
    "tools/cleanup_manifest.json",        # 回滚账本，old 字段本就是旧路径
    "tools/survey/survey_stale_files.py",  # 本脚本的说明文字
    "tools/survey/survey_refs.py",
    "STALE-CLEANUP.md",                   # 清理留痕，必须保留旧路径以便追溯
    "CLEANUP-PLAN.md",
    "ARCHITECTURE.md",                    # 守卫口径里的示例
}

# 文档示例与测试用例里的路径（正常，不是真引用）。
# ⚠️ 这里**只写 basename**：若写成完整路径（`data/x.json`），守卫会把本容器
#    当成「含路径的容器变量」，在 `if m in EXAMPLE_PATHS:` 处报「未判定」——
#    survey 层受 C2 约束，未判定必须清零。比对时按 basename 匹配即可。
EXAMPLE_BASENAMES = {"x.json", "a.js", "b.js", "app.js", "out.js", "chart.js",
                     "p.py", "probe.py", "shoot.py"}


def iter_files():
    for base, dirs, files in os.walk(ROOT):
        rel = os.path.relpath(base, ROOT)
        top = rel.split(os.sep)[0]
        if top in SKIP_DIRS:
            dirs[:] = []
            continue
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f.endswith(SCAN_EXT):
                yield os.path.join(base, f)


def main() -> int:
    # ── C 临时与缓存 ────────────────────────────────────────
    print("═" * 74)
    print("C 临时与缓存")
    print("═" * 74)
    tmp, pyc, pycache = [], 0, 0
    for base, dirs, files in os.walk(ROOT):
        if "__pycache__" in dirs:
            pycache += 1
        for f in files:
            if f.startswith(".tmp") or f.endswith((".tmp", ".bak", ".orig", ".swp")):
                tmp.append(os.path.relpath(os.path.join(base, f), ROOT))
            if f.endswith((".pyc", ".pyo")):
                pyc += 1
    print(f"  .tmp/.bak/.orig/.swp：{len(tmp)}")
    for p in tmp[:20]:
        print("    ", p)
    print(f"  __pycache__ 目录：{pycache}    *.pyc：{pyc}")

    # ── D 空文件 ────────────────────────────────────────────
    print()
    print("═" * 74)
    print("D 0 字节文件")
    print("═" * 74)
    empty = []
    for p in iter_files():
        try:
            if os.path.getsize(p) == 0:
                empty.append(os.path.relpath(p, ROOT))
        except OSError:
            pass
    print(f"  {len(empty)}")
    for p in empty[:20]:
        print("    ", p)

    # ── B-① 迁移遗留（主判据：账本比对）────────────────────
    print()
    print("═" * 74)
    print("B-① 迁移遗留：仍指向迁移前旧路径的引用（账本 old→new 比对）")
    print("═" * 74)
    led_path = os.path.join(ROOT, "tools", "cleanup_manifest.json")
    if not os.path.exists(led_path):
        print("  ⚠ 找不到迁移账本 tools/cleanup_manifest.json，跳过")
        moves = []
    else:
        moves = json.load(open(led_path, encoding="utf-8"))["moves"]
    # 按 basename 建索引，同时保留带目录的完整旧路径（优先匹配长形态）
    by_base: dict[str, list[dict]] = defaultdict(list)
    for mv in moves:
        by_base[os.path.basename(mv["old"])].append(mv)

    leftovers = defaultdict(list)
    for p in iter_files():
        rel = os.path.relpath(p, ROOT).replace(os.sep, "/")
        if rel in EXEMPT_FILES:
            continue
        try:
            lines = open(p, encoding="utf-8", errors="replace").read().split("\n")
        except OSError:
            continue
        for i, line in enumerate(lines, 1):
            for base, mvs in by_base.items():
                if base not in line:
                    continue
                for mv in mvs:
                    old_rel = mv["old"].replace(os.sep, "/")
                    # 已经写成新路径 → 正常
                    if mv["new"].replace(os.sep, "/") in line:
                        continue
                    # 出现「带 tools/ 前缀的旧路径」或「仅 basename」
                    if old_rel in line or re.search(
                            r"tools[/\\]" + re.escape(base), line):
                        leftovers[rel].append((i, base, mv["new"]))
    if not leftovers:
        print("  ✅ 无迁移遗留")
    else:
        for rel, hits in sorted(leftovers.items()):
            print(f"  {rel}")
            for ln, base, new in hits[:4]:
                print(f"      :{ln}  仍指 {base}  → 应为 {new}")
            if len(hits) > 4:
                print(f"      … 另 {len(hits) - 4} 处")
    print(f"\n  涉及 {len(leftovers)} 个文件、"
          f"{sum(len(v) for v in leftovers.values())} 处")

    # ── B-② 路径字面量存在性（辅判据）─────────────────────
    print()
    print("═" * 74)
    print("B-② 悬空引用：路径字面量指向不存在的文件（非迁移原因）")
    print("═" * 74)
    pat = re.compile(
        r"""["']((?:tools|data|ui|content|engine|research|archive)/
             [A-Za-z0-9_\-./]+\.(?:py|js|json|md|html|css|sh))["']""", re.X)
    dangling = defaultdict(list)
    for p in iter_files():
        rel = os.path.relpath(p, ROOT).replace(os.sep, "/")
        if rel in EXEMPT_FILES:
            continue
        try:
            t = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for m in set(pat.findall(t)):
            if os.path.basename(m) in EXAMPLE_BASENAMES:
                continue
            if not os.path.exists(os.path.join(ROOT, m)):
                dangling[rel].append(m)
    if not dangling:
        print("  ✅ 无悬空引用")
    else:
        for rel, targets in sorted(dangling.items()):
            print(f"  {rel}")
            for t in sorted(targets)[:6]:
                print(f"      → {t}  （不存在）")
    print(f"\n  涉及 {len(dangling)} 个文件")
    print()
    print("提示：B-① 是迁移遗留的权威判据；B-② 覆盖手写错误/文件被删。")
    print("      两处报出的都需逐条确认「是引用还是示例/留痕」再动手。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
