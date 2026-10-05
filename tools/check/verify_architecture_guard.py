#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""架构守卫的**正反验证**：在临时沙盒里植入已知形态，确认「该命中的命中、不该命中的不命中」。

为什么必须有它
==============
守卫变绿只有两种可能：仓库真的干净，或者**守卫变瞎了**。
上一轮就是后者——`p = os.path.join(ROOT, "ui", "emohealth-data.js")` 之后 `open(p)`
这条真实 C3 违例，被「静态路径字面量」口径漏掉，而报告里写着「C3 全绿」。
所以本脚本的作用是**先证明守卫能命中**（含上一轮漏掉的单字母变量形态），
再去相信 `tools/check_architecture.py` 的绿。

做法
====
每个用例开一个临时沙盒目录，只放该用例涉及的文件，直接调用守卫的
``check_contract(root, contract)``，断言「违例数 / 未判定数 / 命中行内容」。
沙盒用完即删，不碰仓库里的任何文件。

用法
====
    python tools/check/verify_architecture_guard.py
退出码：全部用例符合预期 0；任一不符 1。
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
sys.path.insert(0, TOOLS)

import check_architecture as guard  # noqa: E402


def legacy_rule_tracks(name: str) -> bool:
    """上一版 ``_bound_names`` 的口径（逐字复制，作为对照）：

        return [name] if (len(name) >= 3 or name.isupper()) else []

    单字母小写变量不在跟踪范围——这就是上一轮 ``p`` 漏检的原因。
    """
    return len(name) >= 3 or name.isupper()


def run_case(files: dict[str, str], contract_id: str):
    """在临时沙盒里跑一遍守卫，返回 (违例, 未判定, 扫描文件数, 摘要)。"""
    root = tempfile.mkdtemp(prefix="guard-verify-")
    try:
        for rel, content in files.items():
            full = os.path.join(root, *rel.split("/"))
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as fh:
                fh.write(content)
        contract = next(c for c in guard.CONTRACTS if c["id"] == contract_id)
        _ok, summary, violations, scanned, undetermined = guard.check_contract(root, contract)
        return violations, undetermined, len(scanned), summary
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ------------------------------------------------------------------ 用例定义
# 每个用例：name / contract / files / expect_hits / expect_undet /
#           expect_hit_contains（可选，任一命中行须含该子串）
CASES: list[dict] = [
    # ── C3：应命中（数据层读 ui/） ────────────────────────────────────────
    {
        "name": "C3 直接字面量",
        "contract": "C3",
        "files": {"tools/build/p.py":
                  'import os\n'
                  'ROOT = "."\n'
                  'raw = open(os.path.join(ROOT, "ui", "emohealth-data.js"), encoding="utf-8").read()\n'},
        "expect_hits": 1, "expect_undet": 0,
    },
    {
        "name": "C3 单字母变量绑定（上一轮漏检的真实形态）",
        "contract": "C3",
        "files": {"tools/build/p.py":
                  'import json, os\n'
                  'ROOT = "."\n'
                  '\n'
                  'def load_neo_zh():\n'
                  '    p = os.path.join(ROOT, "ui", "emohealth-data.js")\n'
                  '    raw = open(p, encoding="utf-8").read()\n'
                  '    return json.loads(raw)\n'},
        "expect_hits": 1, "expect_undet": 0,
        "expect_hit_contains": "open(p",
    },
    {
        "name": "C3 长变量名绑定（旧口径也覆盖，防退化）",
        "contract": "C3",
        "files": {"tools/build/p.py":
                  'import json, os\n'
                  'ROOT = "."\n'
                  'UI_PAYLOAD = os.path.join(ROOT, "ui", "emohealth-data.js")\n'
                  'data = json.load(open(UI_PAYLOAD, encoding="utf-8"))\n'},
        "expect_hits": 1, "expect_undet": 0,
    },
    {
        "name": "C3 跨行拼接（字面量在拼接首行）",
        "contract": "C3",
        "files": {"tools/build/p.py":
                  'import os\n'
                  'ROOT = "."\n'
                  'p = os.path.join(ROOT, "ui",\n'
                  '                 "emohealth-data.js")\n'
                  'raw = open(p, encoding="utf-8").read()\n'},
        "expect_hits": 1, "expect_undet": 0,
    },
    {
        "name": "C3 `..` 相对路径",
        "contract": "C3",
        "files": {"tools/build/p.py":
                  'import os\n'
                  'p = "../ui/emohealth-data.js"\n'
                  'raw = open(p, encoding="utf-8").read()\n'},
        "expect_hits": 1, "expect_undet": 0,
    },
    {
        "name": "C3 模块级常量 + 函数内使用（LEGB 外层可见）",
        "contract": "C3",
        "files": {"tools/build/p.py":
                  'import os\n'
                  'ROOT = "."\n'
                  'UI_PAYLOAD = os.path.join(ROOT, "ui", "data.js")\n'
                  '\n'
                  'def load():\n'
                  '    return open(UI_PAYLOAD, encoding="utf-8").read()\n'},
        "expect_hits": 1, "expect_undet": 0,
    },
    {
        # 旧口径是「文件级绑定」，这个用例里 main() 的 p 会被误算成同一条依赖；
        # 新口径按作用域解析，只应命中 load_neo_zh() 里那一行（第 6 行），
        # main() 里读 data/instruments 的 open(p)（第 10 行）不算。
        "name": "C3 同名变量跨函数不误报（作用域感知）",
        "contract": "C3",
        "files": {"tools/build/p.py":
                  'import glob, json, os\n'
                  'ROOT = "."\n'
                  '\n'
                  'def load_neo_zh():\n'
                  '    p = os.path.join(ROOT, "ui", "emohealth-data.js")\n'
                  '    return open(p, encoding="utf-8").read()\n'
                  '\n'
                  'def main():\n'
                  '    for p in glob.glob(os.path.join(ROOT, "data", "instruments", "*.json")):\n'
                  '        json.load(open(p, encoding="utf-8"))\n'},
        "expect_hits": 1, "expect_undet": 0,
        "expect_hit_lines": [6],
    },
    # ── C3：一律不命中（注释 / docstring / 日志 / 标签 / 只写） ─────────────
    {
        "name": "C3 注释、docstring、日志、标签、只写 ui/（都不算读）",
        "contract": "C3",
        "files": {"tools/build/p.py":
                  '"""本脚本**以前**读 ui/emohealth-data.js，现在改读 data/scene-taxonomy.json。"""\n'
                  'import json, os\n'
                  'ROOT = "."\n'
                  '# 读 ui/emohealth-data.js 是 C3 违例（这行是注释）\n'
                  'TAX = os.path.join(ROOT, "data", "scene-taxonomy.json")\n'
                  'entries = json.load(open(TAX, encoding="utf-8"))\n'
                  'entries["zh_source"] = "ui/emohealth-data.js（已人工核对）"\n'
                  'print("数据包 → ui/emohealth-data.js")\n'
                  'print("写出", os.path.join(ROOT, "ui", "out.js"))\n'
                  'with open(os.path.join(ROOT, "ui", "out.js"), "w", encoding="utf-8") as fh:\n'
                  '    fh.write("x")\n'},
        "expect_hits": 0, "expect_undet": 0,
        "expect_summary_contains": "1 处写入 ui/",
    },
    # ── C3：未判定（判不出来，但不能当通过） ────────────────────────────────
    {
        "name": "C3 未判定：绑定变量只用于读也判不出的上下文",
        "contract": "C3",
        "files": {"tools/build/p.py":
                  'import os\n'
                  'ROOT = "."\n'
                  'p = os.path.join(ROOT, "ui", "net-layout.js")\n'
                  'register(p)\n'},
        "expect_hits": 0, "expect_undet": 1,
    },
    {
        "name": "C3 未判定：跨行拼接把路径段拆成单独一行",
        "contract": "C3",
        "files": {"tools/build/p.py":
                  'import os\n'
                  'ROOT = "."\n'
                  'p = (ROOT + "/"\n'
                  '     + "ui"\n'
                  '     + "/emohealth-data.js")\n'
                  'raw = open(p, encoding="utf-8").read()\n'},
        "expect_hits": 0, "expect_undet": 1,
    },
    {
        "name": "C3 未判定：路径藏在容器里（弱绑定）",
        "contract": "C3",
        "files": {"tools/build/p.py":
                  'PATHS = {"ui/a.js", "ui/b.js"}\n'
                  'load(PATHS)\n'},
        "expect_hits": 0, "expect_undet": 1,
    },
    {
        # Python 语法错误 → 收不到 AST → 变量判定退化为同行启发式；
        # 退化本身必须报「未判定」，不能悄悄按「没问题」处理。
        "name": "C3 Python 无法解析：退化但仍命中 + 报未判定",
        "contract": "C3",
        "files": {"tools/build/p.py":
                  'import os\n'
                  'ROOT = "."\n'
                  'def broken(:\n'
                  '    p = os.path.join(ROOT, "ui", "x.js")\n'
                  '    return open(p, encoding="utf-8").read()\n'},
        "expect_hits": 1, "expect_undet": 1,
    },
    # ── C1：生成产物豁免要真豁免，非生成文件要真命中 ────────────────────────
    {
        "name": "C1 生成产物目录（ui/instruments/）豁免",
        "contract": "C1",
        "files": {"ui/instruments/chart.js":
                  'const fs = require("fs");\n'
                  'const raw = fs.readFileSync("archive/scales/x.json");\n'},
        "expect_hits": 0, "expect_undet": 0, "expect_scanned": 0,
    },
    {
        "name": "C1 非生成 ui/ 文件读 archive/（豁免不能过宽）",
        "contract": "C1",
        "files": {"ui/app.js":
                  'const raw = require("./archive/scales/x.json");\n'},
        "expect_hits": 1, "expect_undet": 0,
    },
    {
        # C1 是「任一引用即违例」（mode=any）：常量定义行本身与使用行都算，
        # 所以这里是 2 行违例、1 条依赖——与 C3「写不算读」的口径不同，是有意为之。
        "name": "C1 前端脚本变量绑定 archive/",
        "contract": "C1",
        "files": {"tools/ui/shoot.py":
                  'import json, os\n'
                  'ROOT = "."\n'
                  'a = os.path.join(ROOT, "archive", "ipip", "data.json")\n'
                  'd = json.load(open(a, encoding="utf-8"))\n'},
        "expect_hits": 2, "expect_undet": 0,
    },
    # ── C2：只禁「写 data/」 ────────────────────────────────────────────────
    {
        "name": "C2 变量绑定后写 data/（命中）",
        "contract": "C2",
        "files": {"tools/survey/probe.py":
                  'import json, os\n'
                  'ROOT = "."\n'
                  'p = os.path.join(ROOT, "data", "candidates.json")\n'
                  'json.dump({"a": 1}, open(p, "w", encoding="utf-8"))\n'},
        "expect_hits": 1, "expect_undet": 0,
    },
    {
        "name": "C2 读 data/ 不算违例（C2 只管写）",
        "contract": "C2",
        "files": {"tools/survey/probe.py":
                  'import json, os\n'
                  'ROOT = "."\n'
                  'p = os.path.join(ROOT, "data", "text-db", "text-db.json")\n'
                  'db = json.load(open(p, encoding="utf-8"))\n'},
        "expect_hits": 0, "expect_undet": 0,
    },
]


def main() -> int:
    print("架构守卫正反验证（沙盒植入 → 断言命中/不命中）")
    print(f"守卫：{os.path.relpath(guard.__file__, TOOLS)}")
    print()
    failures: list[str] = []
    for case in CASES:
        hits, undet, scanned, summary = run_case(case["files"], case["contract"])
        problems: list[str] = []
        if len(hits) != case["expect_hits"]:
            problems.append(f"违例 {len(hits)} ≠ 预期 {case['expect_hits']}")
        if len(undet) != case["expect_undet"]:
            problems.append(f"未判定 {len(undet)} ≠ 预期 {case['expect_undet']}")
        if "expect_scanned" in case and scanned != case["expect_scanned"]:
            problems.append(f"扫描文件 {scanned} ≠ 预期 {case['expect_scanned']}")
        if case.get("expect_hit_contains") and hits:
            if not any(case["expect_hit_contains"] in h for h in hits):
                problems.append(f"命中行不含 {case['expect_hit_contains']!r}")
        if case.get("expect_hit_lines"):
            got_lines = sorted(int(h.split(":")[1].split()[0]) for h in hits)
            if got_lines != sorted(case["expect_hit_lines"]):
                problems.append(f"命中行号 {got_lines} ≠ 预期 {case['expect_hit_lines']}")
        if case.get("expect_summary_contains"):
            if not any(case["expect_summary_contains"] in s for s in summary):
                problems.append(f"摘要不含 {case['expect_summary_contains']!r}")
        mark = "✅" if not problems else "❌"
        print(f"{mark} [{case['contract']}] {case['name']}")
        print(f"     违例 {len(hits)}（预期 {case['expect_hits']}）"
              f"｜未判定 {len(undet)}（预期 {case['expect_undet']}）"
              f"｜扫描 {scanned} 文件")
        for s in summary:
            print(f"     · {s}")
        for h in hits:
            print(f"     命中 → {h}")
        for u in undet:
            print(f"     未判定 → {u}")
        for p in problems:
            print(f"     ⚠ {p}")
        if problems:
            failures.append(f"{case['name']}：{'；'.join(problems)}")
        print()

    # 对照：上一轮为什么漏检（旧口径对单字母小写的 p 不跟踪）
    print("对照（旧口径 vs 新口径，同一形态）")
    print(f"  旧 `_bound_names` 对 'p' 的判定："
          f"{'跟踪' if legacy_rule_tracks('p') else '不跟踪 ← 这正是上一轮的漏检原因'}")
    old_case = next(c for c in CASES if "单字母变量绑定" in c["name"])
    hits, _undet, _sc, _s = run_case(old_case["files"], old_case["contract"])
    print(f"  新守卫对同一形态命中：{len(hits)} 条（预期 ≥1）")
    if len(hits) < 1:
        failures.append("新守卫漏掉了单字母变量绑定的历史形态")
    print()

    if failures:
        print(f"❌ {len(failures)} 个用例不符合预期：")
        for f in failures:
            print("  ·", f)
        return 1
    print(f"✅ {len(CASES)} 个用例全部符合预期"
          "（应命中的都命中、不该命中的都不命中、判不出的都进了未判定）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
