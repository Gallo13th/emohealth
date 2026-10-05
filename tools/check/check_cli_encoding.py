#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""守卫：PLAN.md「每轮必跑」的每条命令，在 **GBK 控制台**下不许崩。

为什么需要
==========
2026-10-05 实测：`tools/ui/pack_ui_data.py` 与 `tools/check/check_pack_freshness.py`
在 Windows 默认控制台（GBK 代码页）下打印 `✓` / `✅` 时抛 `UnicodeEncodeError`，
**退出码 1——与「真的发现产物不一致 / job 过期」完全无法区分**。后果是双重的：

* 守卫在最常见的一类环境里**永远红**，人只会学会无视它；
* `pack_ui_data.py` 更糟：它的打印在**写盘之后**，于是表现为「打包成功却报错」，
  很容易被当成失败去回滚或重跑。

这正是本项目最防的一类问题：**哨兵自己坏了，却伪装成一条真实的红**。修法是入口兜底
（`force_utf8_io()`），而这条守卫负责**证明整个「每轮必跑」清单都不会再犯**。

判据
====
* 命令清单**从 PLAN.md 的「每轮必跑（复现命令）」代码块解析**——绝不另抄一份
  （抄一份就会长成第二份会过期的清单，这正是本项目反复踩的坑）。解析不到就报错退出。
* 每条命令都用 `PYTHONIOENCODING=gbk` **子进程**跑：强制复现最恶劣的控制台编码，
  与当前机器/控制台/CI 无关。解释器统一换成当前 `sys.executable`（避免 PATH 歧义）。
* **崩溃 = ❌**：stderr 出现 `UnicodeEncodeError` 或 `Traceback (most recent call last)`。
* **业务性红不算失败**：如 `check_pack_freshness` 发现过期 → exit 1，那是守卫该做的事；
  本守卫只抓「它坏了」，不重复判业务。
* 附加一类（超出「崩溃」但明显不是业务红）：**命令无法启动**（脚本不存在、
  `can't open file`）→ ❌。否则清单里一条写错的命令会被当成「业务性红」静默放过。

用法
====
    python tools/check/check_cli_encoding.py             # 静态全扫 + 跑 PLAN.md 的全部分条命令
    python tools/check/check_cli_encoding.py --static-only  # 只做静态全扫（秒级，便于快速复核）
    python tools/check/check_cli_encoding.py -v          # 附每条命令的耗时
    python tools/check/check_cli_encoding.py --list      # 只打印解析出来的清单
    python tools/check/check_cli_encoding.py --plan P    # 换一份清单（selftest 用）
    python tools/check/check_cli_encoding.py --selftest  # 在临时副本上证明它会红

静态全扫（`tools/**/*.py`）
==========================
运行时检查只能发现**清单里那几条**；而这一类缺陷（打印非 ASCII 又没兜底）在本项目
已经**三次**都是「事后被撞见」的。所以再加一遍静态扫描，把「逐个被发现」变成
「一次全扫出来」。命中条件（两条同时满足）：

    ① 有 `print(...)` / `sys.stdout.write(...)` / `sys.stderr.write(...)`，
       且该调用的源码里含**非 ASCII**（中文或 `✅❌⚠→✓`）；
    ② 文件里**根本没有** `force_utf8_io`（既没 import 也没调用）。

**严重性分级**（避免一堆噪音把人训练成无视）：
    ❌ 失败：该文件在 `PLAN.md` 的「每轮必跑」清单里——它必须被守住；
    ⚠️ 警告：其余脚本（多为一次性诊断/标定工具），**列出文件名但不计失败、不影响退出码**。

已知口径与局限（诚实写出来）：
* `tools/_root.py` **显式排除**——它就是 `force_utf8_io` 的实现本身；
* 判「有兜底」只看**名字是否出现**，不判断它是否真的被调用：静态扫描抓的是
  「完全没设防」；「有没有真的调、调的位置对不对」由运行时那 12 条负责；
* `ast` 解析失败的文件单列（不计失败）——它连跑都跑不起来，运行时会报出来。

退出码：全部命令无崩溃且静态 ❌ 为 0 → 0；否则 1。⚠️ 警告不影响退出码。
"""
from __future__ import annotations

import argparse
import ast
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
sys.path.insert(0, TOOLS)

from _root import find_root, force_utf8_io  # noqa: E402

ROOT = str(find_root())

#: 清单所在小节的关键词——**唯一事实来源是 PLAN.md**。
SECTION = "每轮必跑"

#: 崩塴判定：stderr 里出现任一即算「脚本自己坏了」。按**字节**匹配，避免编码来回转换。
CRASH_MARKERS = (b"UnicodeEncodeError", b"Traceback (most recent call last)")

#: 「命令根本起不来」（脚本不存在 / 解释器找不到）——不是业务红，单列一类。
NO_START_MARKERS = (b"can't open file", b"No such file or directory",
                    b"is not recognized as an internal or external command")

PY_NAMES = {"python", "python3", "py", "python.exe", "python3.exe", "py.exe"}

#: 自己的文件名。清单里一旦收录本守卫（应该收——它也是「每轮必跑」的一环），
#: 必须**跳过自己**，否则它会在一层套一层地跑整个清单，直到超时。
SELF_NAME = os.path.basename(os.path.abspath(__file__))

#: 强制复现最恶劣的控制台编码（GBK 代码页）。不设这个的话本守卫毫无意义。
GBK = "gbk"


# --------------------------------------------------------------------- 解析清单

def parse_plan_commands(text: str) -> tuple[list[str], str | None]:
    """从 PLAN.md 解析「每轮必跑」代码块里的命令 → (命令列表, 失败原因)。

    只认**第一个**围栏代码块；行内注释（``  # …``）会剥掉；整行注释与空行跳过。
    """
    idx = text.find(SECTION)
    if idx < 0:
        return [], f"找不到「{SECTION}」小节"
    m = re.search(r"```[A-Za-z]*\r?\n(.*?)```", text[idx:], re.S)
    if not m:
        return [], f"「{SECTION}」小节下面没有围栏代码块"
    cmds: list[str] = []
    for raw in m.group(1).splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        line = re.split(r"\s+#", line, maxsplit=1)[0].strip()
        if line:
            cmds.append(line)
    if not cmds:
        return [], "代码块里没有可执行的命令"
    return cmds, None


def must_run_scripts(cmds: list[str]) -> set[str]:
    """从「每轮必跑」命令里抽出脚本的相对路径（`tools/a/b.py`）。"""
    out: set[str] = set()
    for cmd in cmds:
        for tok in shlex.split(cmd):
            if tok.endswith(".py"):
                out.add(tok.replace("\\", "/").lstrip("./"))
    return out


# --------------------------------------------------------------------- 静态全扫

#: 显式排除：`tools/_root.py` 就是 ``force_utf8_io`` 的实现本身，不该被自己的规则判。
STATIC_EXCLUDE = {"tools/_root.py"}

#: selftest 用：**已知会以「非 ASCII 输出 + 无兜底」崩过的三个实例**
#: （`check_size_regression.py` 交付几分钟就被撞、`verify_archive.py` 只是"潜在雷"、
#:  `check_readme_dups.py` 刚被 stale-cleanup 撞）。它们现在都已由各自负责人修好，
#: 所以真实文件**不该**被标记——selftest 就把它们的兜底从副本里去掉，证明规则仍能命中。
STATIC_KNOWN = ("tools/check/check_size_regression.py",
                "tools/check/verify_archive.py",
                "tools/check/check_readme_dups.py")

#: selftest 用：**已修好的对照组**，不许误报。
STATIC_CLEAN = ("tools/check_architecture.py",
                "tools/check/check_pack_freshness.py",
                "tools/check/check_cli_encoding.py",
                "tools/ui/pack_ui_data.py")


def emits_non_ascii(src: str) -> tuple[bool | None, int | None]:
    """该源码里有没有 ``print(...)`` / ``sys.stdout|stderr.write(...)`` 且实参含非 ASCII。

    用 ``ast`` 取**整个调用的源码段**，所以跨行的 f-string 也能认出来
    （按行匹配会把非 ASCII 漏在续行上）。
    → (是否命中, 首个命中的行号)；``None`` 表示源码解析失败。
    """
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None, None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if isinstance(fn, ast.Name) and fn.id == "print":
            pass
        elif (isinstance(fn, ast.Attribute) and fn.attr == "write"
              and isinstance(fn.value, ast.Attribute)
              and fn.value.attr in ("stdout", "stderr")):
            pass
        else:
            continue
        seg = ast.get_source_segment(src, node) or ""
        if any(ord(ch) > 127 for ch in seg):
            return True, node.lineno
    return False, None


def static_scan(cmds: list[str]) -> dict:
    """遍历 ``tools/**/*.py``：打印非 ASCII 又没有 ``force_utf8_io`` 的文件。"""
    must = must_run_scripts(cmds)
    scanned = guarded = 0
    fails: list[tuple[str, int]] = []          # 在「每轮必跑」里 → ❌
    warns: list[tuple[str, int]] = []          # 其余 → ⚠️（不计失败）
    unparsed: list[str] = []
    for dirpath, dirs, fnames in os.walk(os.path.join(ROOT, "tools")):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        for fn in sorted(fnames):
            if not fn.endswith(".py"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, fn), ROOT).replace(os.sep, "/")
            if rel in STATIC_EXCLUDE:
                continue
            scanned += 1
            src = open(os.path.join(dirpath, fn), encoding="utf-8", errors="replace").read()
            if "force_utf8_io" in src:         # 有 import 或调用即算设防（见 docstring 局限）
                guarded += 1
                continue
            hit, line = emits_non_ascii(src)
            if hit is None:
                unparsed.append(rel)
            elif hit:
                (fails if rel in must else warns).append((rel, line or 0))
    return {"must": must, "scanned": scanned, "guarded": guarded,
            "fails": fails, "warns": warns, "unparsed": unparsed}


def report_static(res: dict) -> int:
    """打印静态全扫结果 → 失败数（❌ 的个数；⚠️ 不计）。"""
    print(f"── 静态全扫：tools/**/*.py（排除 __pycache__、{', '.join(sorted(STATIC_EXCLUDE))}"
          "——它就是本机制的实现本身）")
    print(f"   扫描 {res['scanned']} 个文件；有 force_utf8_io 兜底 {res['guarded']} 个；"
          f"**输出非 ASCII 又无兜底** {len(res['fails']) + len(res['warns'])} 个")
    print()

    if res["fails"]:
        print(f"   ❌ 失败 {len(res['fails'])} 个 —— 它们在 PLAN.md「每轮必跑」清单里，必须修：")
        for rel, line in res["fails"]:
            print(f"        {rel}:{line}")
    else:
        print(f"   ✅ 「每轮必跑」的 {len(res['must'])} 个脚本全部有兜底")
    print()

    if res["warns"]:
        by_dir: dict[str, list[str]] = {}
        for rel, _line in res["warns"]:
            d = os.path.dirname(rel)
            by_dir.setdefault(d, []).append(os.path.basename(rel))
        print(f"   ⚠️ 警告 {len(res['warns'])} 个 —— 其余脚本（多为一次性诊断/标定工具），"
              "**不强制、不影响退出码**；将来谁要用谁先修：")
        for d in sorted(by_dir):
            print(f"        {d}/（{len(by_dir[d])}）：" + "、".join(sorted(by_dir[d])))
        print()
    if res["unparsed"]:
        print(f"   ⚠️ {len(res['unparsed'])} 个文件 ast 解析失败（连跑都跑不起来，"
              "运行时那 12 条会报）：" + "、".join(res["unparsed"]))
        print()
    print("   修法：`from _root import force_utf8_io` + `main()` 第一行 `force_utf8_io()`"
          "（见 tools/_root.py 的说明）")
    print()
    return len(res["fails"])


# --------------------------------------------------------------------- 跑一条命令

def run_one(cmd: str, timeout: float) -> dict:
    """用 PYTHONIOENCODING=gbk 跑一条命令，返回退出码/输出/崩溃判定。"""
    argv = shlex.split(cmd)
    if argv and os.path.basename(argv[0]).lower() in PY_NAMES:
        argv[0] = sys.executable               # 同一个解释器，避免 PATH 歧义
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = GBK              # 强制最恶劣的控制台编码
    env.pop("PYTHONUTF8", None)

    t0 = time.time()
    rc, out, err, note = None, b"", b"", None
    try:
        p = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True,
                           timeout=timeout)
        rc, out, err = p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired as exc:
        out, err = exc.stdout or b"", exc.stderr or b""
        note = f"超时（>{timeout:.0f}s）"
    except OSError as exc:
        # 受限环境可能禁止管道：退化成临时文件重定向（文件不是管道）再试一次。
        try:
            with tempfile.TemporaryDirectory(prefix="cli-enc-") as td:
                fo = os.path.join(td, "out.bin")
                fe = os.path.join(td, "err.bin")
                with open(fo, "wb") as fh_o, open(fe, "wb") as fh_e:
                    p2 = subprocess.run(argv, cwd=ROOT, env=env,
                                        stdout=fh_o, stderr=fh_e, timeout=timeout)
                    rc = p2.returncode
                out = open(fo, "rb").read()
                err = open(fe, "rb").read()
        except Exception as exc2:                              # noqa: BLE001
            note = f"无法启动：{type(exc).__name__}/{type(exc2).__name__}: {exc2}"

    took = time.time() - t0
    crash = [m.decode() for m in CRASH_MARKERS if m in err]
    no_start = [m.decode() for m in NO_START_MARKERS if m in err]
    return {"cmd": cmd, "rc": rc, "out": out, "err": err, "note": note,
            "took": took, "crash": crash, "no_start": no_start}


def is_self(cmd: str) -> bool:
    """该命令是不是在跑本守卫自己？（清单收录本守卫时必须跳过，否则无限递归）"""
    try:
        argv = shlex.split(cmd)
    except ValueError:
        return False
    return any(os.path.basename(a) == SELF_NAME for a in argv)


def _tail(data: bytes, lines: int = 12, width: int = 200) -> list[str]:
    text = data.decode("utf-8", errors="replace")
    return [ln[:width] for ln in text.splitlines()[-lines:]]


def _verdict(r: dict) -> tuple[bool, str]:
    """→ (是否失败, 说明)。业务性红**不算失败**。"""
    if r["note"]:
        return True, r["note"]
    if r["crash"]:
        return True, "崩溃：" + " + ".join(r["crash"])
    if r["no_start"]:
        return True, "命令无法启动：" + " + ".join(r["no_start"])
    if r["rc"] != 0:
        return False, f"业务性红（exit={r['rc']}，无崩溃——不算本守卫的失败）"
    return False, ""


# --------------------------------------------------------------------- 主流程

def run_plan(plan_path: str, timeout: float, verbose: bool) -> int:
    """解析清单 → 跑运行时检查（selftest 用它跑临时清单）。"""
    try:
        text = open(plan_path, encoding="utf-8").read()
    except OSError as exc:
        print(f"❌ 读不到清单 {plan_path}：{exc}")
        return 1
    cmds, err = parse_plan_commands(text)
    if err:
        print(f"❌ 解析清单失败：{err}")
        print(f"   清单必须来自 PLAN.md 的「{SECTION}（复现命令）」围栏代码块；"
              "本脚本不另抄一份清单（抄一份就会长成第二份会过期的清单）。")
        return 1
    print(f"GBK 控制台健壮性守卫（清单：{plan_path}，{len(cmds)} 条命令）")
    print()
    return run_runtime(cmds, timeout, verbose)


def run_runtime(cmds: list[str], timeout: float, verbose: bool) -> int:
    """把清单里每条命令用 `PYTHONIOENCODING=gbk` 跑一遍。"""
    print(f"── 运行时检查：把 {len(cmds)} 条命令各用 PYTHONIOENCODING={GBK} 跑一遍")
    print("   口径：业务性红（exit≠0）不算失败；崩溃（stderr 含 UnicodeEncodeError / "
          "Traceback）与「无法启动」才算。")
    print()

    failed = []
    skipped = 0
    prev_crashed: str | None = None
    for cmd in cmds:
        if is_self(cmd):
            skipped += 1
            print(f"⏭ exit=   -  {cmd}   （跳过自身：本守卫已在运行，避免无限递归）")
            continue
        if prev_crashed:
            # 崩溃的脚本可能留下临时目录/半写文件，让**下一条**看起来也坏了。
            # 这是级联，不是它自身的缺陷——不区分开，人就会去修错的那个脚本。
            print(f"⚠️  上一条命令崩溃（{prev_crashed}），可能留下临时状态"
                  "（临时目录 / 半写文件）——下面这条若失败，可能是**级联**，"
                  "不等于它自己坏了。")
        r = run_one(cmd, timeout)
        bad, why = _verdict(r)
        mark = "❌" if bad else "✅"
        extra = f"   {why}" if why else ""
        took = f"{r['took']:6.1f}s" if verbose else ""
        tail = _tail(r["err"], 3, 110) if bad else []
        print(f"{mark} exit={str(r['rc']):>4}  {took}  {cmd}{extra}")
        for ln in tail:
            print(f"        │ {ln}")
        if bad:
            failed.append((r, why))
        prev_crashed = cmd if r["crash"] else None

    print()
    if failed:
        print(f"❌ {len(failed)}/{len(cmds)} 条命令在 GBK 下**自己坏了**：")
        for r, why in failed:
            print()
            print(f"── {r['cmd']}")
            print(f"   判定：{why}")
            if r["note"]:
                print(f"   说明：{r['note']}")
            for ln in _tail(r["err"]):
                print(f"   │ {ln}")
        print()
        print("   修法：在该脚本入口加 UTF-8 兜底（把 stdout/stderr reconfigure 成"
              " utf-8，不靠调用者设 PYTHONIOENCODING）。")
        return 1
    print(f"✅ {len(cmds)} 条命令在 GBK 控制台下都没有崩溃（业务性红不算失败）。"
          + (f"（跳过自身 {skipped} 条）" if skipped else ""))
    return 0


# --------------------------------------------------------------------- selftest

BROKEN_NAME = ".selftest_no_utf8_pack_ui_data.py"
CALL_RE = re.compile(r"^(\s*)force_utf8_io\(\).*$", re.M)


def _selftest_plan(tmpdir: str, broken_abs: str) -> str:
    plan = os.path.join(tmpdir, "PLAN-broken.md")
    with open(plan, "w", encoding="utf-8") as fh:
        fh.write(f"**{SECTION}（复现命令）**\n\n```powershell\n"
                 f'python "{broken_abs}" --check\n```\n')
    return plan


def selftest(timeout: float) -> int:
    """证明本守卫**真的会红**：临时副本上真的去掉兜底 → 必须被判崩溃。

    不 mock：真的复制文件、真的删掉那一行调用、真的跑子进程、真的让守卫整体跑一遍。
    """
    print("=== --selftest：证明本守卫能命中（临时副本上真的去掉 UTF-8 兜底）===")
    print()

    real = os.path.join(ROOT, "tools", "ui", "pack_ui_data.py")
    broken = os.path.join(HERE, BROKEN_NAME)          # 放 tools/check/ 下：向上能找到项目根
    src = open(real, encoding="utf-8").read()
    patched, n = CALL_RE.subn(r"\1pass  # selftest：故意去掉兜底", src)
    if n == 0:
        print(f"❌ 在 {real} 里找不到 `force_utf8_io()` 调用点，selftest 无法进行")
        return 1

    ok = True
    try:
        with open(broken, "w", encoding="utf-8") as fh:
            fh.write(patched)
        print(f"① 已生成临时副本（去掉了兜底）：{os.path.relpath(broken, ROOT)}")

        # ② 真实脚本（已修）在 gbk 下不许崩
        good = run_one(f'python "{real}" --check', timeout)
        bad_good, why_good = _verdict(good)
        print(f"② 真实脚本 {os.path.relpath(real, ROOT)} 在 GBK 下："
              f"{'❌ 竟然崩了：' + why_good if bad_good else '✅ 无崩溃'}"
              f"（exit={good['rc']}）")
        ok &= not bad_good

        # ③ 临时副本在 gbk 下必须崩（直接跑，看 stderr）
        r = run_one(f'python "{broken}" --check', timeout)
        bad, why = _verdict(r)
        print(f"③ 去掉兜底的副本在 GBK 下：{'✅ 如预期崩溃' if bad else '❌ 竟然没崩'}"
              f"（exit={r['rc']}，判定：{why}）")
        for ln in _tail(r["err"], 4, 120):
            print(f"      │ {ln}")
        ok &= bad

        # ④ 用同一条命令造临时清单，让守卫整体跑一遍 → 必须退出 1
        with tempfile.TemporaryDirectory(prefix="cli-enc-plan-") as td:
            plan = _selftest_plan(td, broken.replace(os.sep, "/"))
            print(f"④ 用临时清单让本守卫整体跑一遍：{plan}")
            print("   " + "-" * 66)
            rc = run_plan(plan, timeout, verbose=False)
            print("   " + "-" * 66)
            print(f"   → 守卫退出码 {rc}（预期 1）")
            ok &= (rc == 1)
    finally:
        if os.path.exists(broken):
            os.remove(broken)
        gone = not os.path.exists(broken)
        print(f"⑤ 临时副本已清理：{gone}（{os.path.relpath(broken, ROOT)}）")
        ok &= gone

    # ⑥⑦ 静态扫描非空洞：已知实例的兜底一旦被去掉，必须命中；已修好的不许误报
    print()
    print("⑥ 静态扫描非空洞：把**已知实例**的兜底从副本里去掉 → 必须命中")
    for rel in STATIC_KNOWN:
        full = os.path.join(ROOT, *rel.split("/"))
        if not os.path.exists(full):
            print(f"   ⚠ {rel} 不存在，跳过")
            continue
        src = open(full, encoding="utf-8").read()
        real_guarded = "force_utf8_io" in src
        stripped = src.replace("force_utf8_io", "_DISABLED_utf8")
        hit_real, _ = (False, None) if real_guarded else emits_non_ascii(src)
        hit_stripped, line = emits_non_ascii(stripped)
        ok_case = (not hit_real) and bool(hit_stripped)
        print(f"   {'✅' if ok_case else '❌'} {rel}")
        print(f"        真实文件有兜底 → 不命中：{not hit_real}"
              f"（force_utf8_io 出现：{real_guarded}）")
        print(f"        去掉兜底后 → 命中：{bool(hit_stripped)}"
              + (f"（首个非 ASCII 输出在第 {line} 行）" if hit_stripped else ""))
        ok &= ok_case

    print()
    print("⑦ 不误报已修好的：逐个核对对照组")
    for rel in STATIC_CLEAN:
        full = os.path.join(ROOT, *rel.split("/"))
        if not os.path.exists(full):
            print(f"   ⚠ {rel} 不存在，跳过")
            continue
        src = open(full, encoding="utf-8").read()
        guarded = "force_utf8_io" in src
        flagged = not guarded and bool(emits_non_ascii(src)[0])
        print(f"   {'✅' if not flagged else '❌'} {rel}：有兜底 {guarded} → 未被标记 {not flagged}")
        ok &= (not flagged)
    print(f"   ✅ 规则例外已排除：{', '.join(sorted(STATIC_EXCLUDE))}（它就是实现本身，不参与判定）")

    print()
    print("✅ selftest 通过：运行时兜底与静态扫描两侧都能命中，且不误报已修好的。"
          if ok else "❌ selftest 未通过（见上）")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    force_utf8_io()          # 入口第一件事：GBK 控制台下不许崩
    ap = argparse.ArgumentParser(
        description=f"守卫：PLAN.md「{SECTION}」的每条命令在 GBK 控制台下不许崩")
    ap.add_argument("-v", "--verbose", action="store_true", help="附每条命令耗时")
    ap.add_argument("--plan", default=None, help="清单文件（默认 PLAN.md）")
    ap.add_argument("--list", action="store_true", help="只打印解析出的命令清单")
    ap.add_argument("--timeout", type=float, default=900.0,
                    help="单条命令超时秒数（默认 900）")
    ap.add_argument("--selftest", action="store_true",
                    help="在去掉兜底的临时副本上验证本守卫会红")
    ap.add_argument("--static-only", action="store_true",
                    help="只做静态全扫（tools/**/*.py），不跑清单里的子进程")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest(args.timeout)

    plan = args.plan or os.path.join(ROOT, "PLAN.md")
    cmds, err = parse_plan_commands(open(plan, encoding="utf-8").read())
    if err:                       # 静态分级的依据也来自这份清单，解析不了就不给 ❌ 分级
        print(f"❌ 解析清单失败：{err}")
        print(f"   清单必须来自 PLAN.md 的「{SECTION}（复现命令）」围栏代码块；"
              "本脚本不另抄一份清单（抄一份就会长成第二份会过期的清单）。")
        return 1

    if args.list:
        print(f"从 {plan} 解析出 {len(cmds)} 条命令：")
        for c in cmds:
            print(f"  {c}")
        return 0

    print(f"GBK 控制台健壮性守卫（清单：{plan}，{len(cmds)} 条命令）")
    print("静态全扫把「逐个被撞见」变成「一次全扫出来」；静态的 ⚠️ 警告不计失败。")
    print()

    static_failed = report_static(static_scan(cmds))
    if args.static_only:
        if static_failed:
            print(f"❌ 静态全扫发现 {static_failed} 个「必跑脚本没有兜底」——"
                  "它们在 GBK 控制台下会把崩溃伪装成真红，必须修。")
            return 1
        print("✅ 静态全扫：必跑脚本全部有兜底（⚠️ 警告不计失败）。")
        return 0

    rc = run_runtime(cmds, args.timeout, args.verbose)
    if rc == 0 and static_failed:
        print()
        print(f"❌ 运行时没崩，但静态全扫另有 {static_failed} 个「必跑脚本没有兜底」。")
        return 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
