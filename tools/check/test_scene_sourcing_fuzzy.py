#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`check_scene_sourcing.py` 的**常驻回归测试**：守住「兜底/判红路径不许崩」这条不变量。

为什么要有它
============
2026-10-05 修掉一个真缺陷：哨兵的**近似（fuzzy）兜底分支**把 `found` 赋成了 entry
**字典**，而别处按 `(entry key, entry)` 元组取 `found[1]` → 走进该分支必 `KeyError: 1`。
最坏的地方不是崩溃本身，而是**崩溃的退出码（1）与「真的发现漏读」（也是 1）不可区分**：
哨兵自己坏了，却伪装成一条真实的红。

按项目规矩——**修一个真缺陷，就留一个能重新触发它的测试**（`build_l1_instrument.py`
的字段继承、`build_dim_ceiling.py` 的拼接、`pdftext.py` 的静默丢字，都是修完没留回归
才重蹈的）。所以本测试用**合成数据**（不依赖任何真实量表）钉住三件事：

① **不崩**：走到 fuzzy 分支时 `main()` 必须正常返回、退出码 = 1（真红），
   而不是抛 traceback；
② **诊断照常打印**：相似度 + 疑似同题的材料 key 必须出现在输出里；
③ **形态不变量**：源码里对 `found` 的每一次赋值都只能是 `None` 或 `(key, entry)`
   二元组——用 AST 静态断言（不靠数据，改坏就红）。

另外顺带守住两条通道（`text_en` → `text_en_verbatim` 回退）各自能被数出来。

用法
====
    python tools/check/test_scene_sourcing_fuzzy.py     # 绿=0 / 红=1
"""
from __future__ import annotations

import ast
import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SENTINEL = os.path.join(ROOT, "tools", "check", "check_scene_sourcing.py")
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "tools", "check"))

fail = 0


def ck(name: str, cond: bool, detail: str = "") -> None:
    global fail
    print(f"  {'✅' if cond else '❌'} {name}" + (f"  —— {detail}" if detail else ""))
    if not cond:
        fail += 1


def load_sentinel():
    spec = importlib.util.spec_from_file_location("sentinel_under_test", SENTINEL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_main(mod, tmp: str, argv_extra=()):
    """把哨兵的三个路径常量指到合成数据上，跑一次 main()，返回 (退出码, 输出)。"""
    mod.STRUCT_DIR = os.path.join(tmp, "items")
    mod.TEXT_DB = os.path.join(tmp, "text-db.json")
    mod.INDEX_NORM = os.path.join(tmp, "index-norm.json")
    sys.argv = ["check_scene_sourcing.py", "--index", mod.INDEX_NORM, *argv_extra]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = mod.main()
    return rc, buf.getvalue()


def make_case(tmp: str, entries: dict, items: list, index: dict) -> None:
    os.makedirs(os.path.join(tmp, "items"), exist_ok=True)
    with open(os.path.join(tmp, "text-db.json"), "w", encoding="utf-8") as fh:
        json.dump({"entries": entries}, fh, ensure_ascii=False)
    with open(os.path.join(tmp, "items", "test-scale.json"), "w", encoding="utf-8") as fh:
        json.dump({"code": "test-scale", "items": items}, fh, ensure_ascii=False)
    with open(os.path.join(tmp, "index-norm.json"), "w", encoding="utf-8") as fh:
        json.dump(index, fh, ensure_ascii=False)


def main() -> int:
    mod = load_sentinel()

    print("=== ③ 形态不变量（AST 静态断言；不依赖任何数据）===")
    src = open(SENTINEL, encoding="utf-8").read()
    tree = ast.parse(src)
    assigns = []          # 对 found 的赋值表达式（RHS 侧）
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "found":
                    assigns.append(node.value)
                elif isinstance(t, ast.Tuple):
                    # ⚠️ 元组解包也必须查：旧 bug 的**原形态**正是
                    #    `found, channel = best[1], f"近似(…)"` —— 目标在 Tuple 里，
                    #    只查 `t.id == "found"` 会漏掉它（本测试第一版就漏了，
                    #    是「变异体能否抓住旧 bug」那次自检把它抓出来的）。
                    for i, el in enumerate(t.elts):
                        if isinstance(el, ast.Name) and el.id == "found":
                            if isinstance(node.value, ast.Tuple) \
                                    and len(node.value.elts) == len(t.elts):
                                assigns.append(node.value.elts[i])
                            else:
                                assigns.append(node.value)      # 形态不明 → 视为违规
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) \
                and node.target.id == "found":
            assigns.append(node.value)
    bad = []
    for v in assigns:
        if isinstance(v, ast.Constant) and v.value is None:
            continue                                  # found = None
        if isinstance(v, ast.Tuple) and len(v.elts) == 2:
            continue                                  # found = (key, entry)
        bad.append(ast.dump(v)[:90])
    ck("对 `found` 的赋值只有 `None` 或二元组 `(key, entry)`（含元组解包形态）",
       len(assigns) >= 2 and not bad,
       f"{len(assigns)} 处赋值；违规 {len(bad)} 处" + (f"：{bad}" if bad else ""))
    ck("源码里没有「把 entry/下标直接塞进 found」的旧形态（如 `found = best[1]`）",
       not any(isinstance(v, ast.Subscript) for v in assigns),
       "旧 bug 的形态是 Subscript 赋值（含元组解包）")
    ck("注释里留了这条教训（兜底分支不允许留在崩溃路径上）",
       "兜底分支不允许留在崩溃路径上" in src)

    tmp = tempfile.mkdtemp(prefix="scenesourcing-")
    try:
        # ── ① + ② fuzzy 分支：不崩、真红、诊断照常打印 ──
        print("\n=== ① ② fuzzy 兜底分支：不崩 + 真红 + 诊断打印 ===")
        make_case(
            tmp,
            entries={"worry about things a lot": {
                "codes": ["T1"], "en": "Worry about things a lot.",
                "instruments": ["TEST-SCALE"], "scaffold": None,
                "note": "仅自由文本", "zh": "为很多事担心"}},
            items=[{"id": "t_001", "text_en": "Worry about things."}],
            index={},                                  # 索引里没有 → 必走 fuzzy 分支
        )
        try:
            rc, out = run_main(mod, tmp)
            crashed = False
        except Exception as e:                          # pragma: no cover
            rc, out, crashed = None, "", f"{type(e).__name__}: {e}"

        ck("走到 fuzzy 分支时**不崩**", not crashed, crashed or "正常返回")
        ck("退出码 = 1（真红，不是 traceback）", rc == 1, f"rc={rc}")
        ck("输出里没有 traceback", "Traceback" not in out)
        ck("打印了「材料在库里，但三条通道都查不到」",
           "材料在库里，但三条通道都查不到" in out)
        ck("打印了相似度", "疑似同题（相似度 0.857）" in out,
           [l.strip() for l in out.splitlines() if "疑似同题" in l][:1])
        ck("打印了疑似同题的材料 key", "worry about things a lot" in out)
        ck("通道表把这一题记成红（0/0/1）", "0             0     1" in out)

        # ── 正常路径：text_en 命中 → 绿 ──
        print("\n=== 正常路径：`text_en` 命中（绿、退出码 0）===")
        make_case(
            tmp,
            entries={"worry about things": {
                "codes": ["T1"], "en": "Worry about things.",
                "instruments": ["TEST-SCALE"], "scaffold": None,
                "note": "仅自由文本", "zh": "为很多事担心"}},
            items=[{"id": "t_001", "text_en": "Worry about things."}],
            index={"worry about things": "worry about things"},
        )
        rc2, out2 = run_main(mod, tmp)
        ck("退出码 = 0（绿）", rc2 == 0, f"rc={rc2}")
        ck("报告 text_en 命中 1 条", "1             0     0" in out2, out2.strip().splitlines()[-1])

        # ── 回退路径：text_en 不中、text_en_verbatim 命中 → 绿 + 通道被看见 ──
        print("\n=== 回退路径：`text_en_verbatim` 命中（绿、通道必须被打印）===")
        make_case(
            tmp,
            entries={"ikeep my distance": {
                "codes": ["T2"], "en": "Ikeep my distance.",
                "instruments": ["TEST-SCALE"], "scaffold": None,
                "note": "仅自由文本", "zh": "我保持距离"}},
            items=[{"id": "t_002", "text_en": "I keep my distance.",
                    "text_en_verbatim": "Ikeep my distance."}],
            index={"ikeep my distance": "ikeep my distance"},
        )
        rc3, out3 = run_main(mod, tmp, ("--items",))
        ck("退出码 = 0（绿）", rc3 == 0, f"rc={rc3}")
        ck("报告 verbatim 回退 1 条（0/1/0）", "0             1     0" in out3)
        ck("逐题行把通道标成 text_en_verbatim", "text_en_verbatim" in out3)

        # ── 形态不变量的**运行期**旁证：fuzzy 分支若再返回字典，上面 ① 必崩 ──
        print("\n=== 运行期旁证 ===")
        ck("fuzzy 分支 + 正常分支 + 回退分支都真跑过（不是只做静态检查）",
           not crashed and rc == 1 and rc2 == 0 and rc3 == 0)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\n{'❌ ' + str(fail) + ' 项未通过' if fail else '✅ 哨兵回归全部通过（兜底/判红路径不许崩）'}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
