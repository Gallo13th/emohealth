#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`build_manifest.py --check` 的**正反验证**：证明它的哈希比对真的会红。

为什么必须有它
=============
2026-10-05 实测事故：`tools/README.md` 被清空成 0 字节（75055 → 0 B），而当时的
``--check`` **只比对文件名集合**，所以一声不响——因为「名字还在清单里」。
``MANIFEST.sha256`` 是本项目的证据链底座（``tools/_root.py`` 靠它定位项目根、
``tools/check/verify_archive.py`` 靠它守原始证据）：只比名字的校验等于
**任何生成物被悄悄改坏都无人知晓**。

修好之后必须留一个**能重新触发它**的测试，于是有本脚本：用真脚本的副本在沙盒里跑，
断言三类差异（新增 / 缺失 / **内容被改**）都被报出，而且**类别正确**——
不是「报了就行」。谁哪天把哈希比对删了/写坏了，本脚本会红；
``--selftest`` 就是当场演示这一点。

绝不碰真仓库（这条比测试本身更重要）
==================================
「验证工具改坏了被验证的东西」是这类测试最危险的失败模式，所以有三重保险：

1. 沙盒自带一个**空的** ``MANIFEST.sha256`` 当根标记 —— ``find_root()`` 会停在沙盒；
2. 每次运行都断言报告的是**沙盒规模**（``清单里 ≤ 10 个``），而不是仓库规模（500+）；
3. 跑完再核对真仓库 ``MANIFEST.sha256`` / ``MANIFEST.txt`` 的 sha256 **逐字节未变**。

用例（每例都在**全新沙盒**里跑，互不污染）
========================================
    baseline   无差异                       → exit 0，三类计数 (0,0,0)
    内容被改   只改 data/a.txt 的内容         → exit 1，(0,0,1) 且打印 大小/清单/实际 两个哈希
    新增文件   data/c.txt（清单里没有）       → exit 1，(1,0,0)
    删除文件   删掉 data/b.txt（清单里有）     → exit 1，(0,1,0)
    三类同时   改 a + 增 c + 删 b             → exit 1，(1,1,1)

用法
====
    python tools/check/verify_manifest_check.py             # 跑全部用例；全符合预期 0
    python tools/check/verify_manifest_check.py -v          # 附每个用例的原始输出
    python tools/check/verify_manifest_check.py --selftest  # 证明本测试**会红**：
                                                            # 把副本的哈希比对退回旧版
                                                            # （只比名字），断言本测试抓得到
退出码：全部符合预期 0；任一不符 1。
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
sys.path.insert(0, TOOLS)

from _root import find_root, force_utf8_io  # noqa: E402

ROOT = str(find_root())
BM = os.path.join(ROOT, "tools", "build", "build_manifest.py")
ROOT_PY = os.path.join(ROOT, "tools", "_root.py")
MAN_SHA = os.path.join(ROOT, "MANIFEST.sha256")
MAN_TXT = os.path.join(ROOT, "MANIFEST.txt")

#: 三类计数行的解析（这也是「类别正确」的判据——只断言「报了」是不够的）
COUNTS_RE = re.compile(r"名字不在清单 (\d+)、清单里有磁盘无 (\d+)、内容被改 (\d+)、读不到 (\d+)")
#: 「清单里 N 个」——用来断言跑的是沙盒而不是真仓库
SCALE_RE = re.compile(r"清单里 (\d+) 个")

A_BODY = "A original\n"
B_BODY = "B original\n"

CASES: tuple[dict, ...] = (
    {"name": "baseline 无差异", "mutate": None,
     "rc": 0, "counts": None, "must_contain": ["✅"]},
    {"name": "内容被改（名字不变）", "mutate": "modify_a",
     "rc": 1, "counts": (0, 0, 1),
     "must_contain": ["✗ data/a.txt", "大小", "清单", "实际", "→"]},
    {"name": "新增文件（清单滞后）", "mutate": "add_c",
     "rc": 1, "counts": (1, 0, 0), "must_contain": ["+ data/c.txt"]},
    {"name": "删除文件（清单里有）", "mutate": "del_b",
     "rc": 1, "counts": (0, 1, 0), "must_contain": ["- data/b.txt"]},
    {"name": "三类同时", "mutate": "all_three",
     "rc": 1, "counts": (1, 1, 1),
     "must_contain": ["+ data/c.txt", "- data/b.txt", "✗ data/a.txt"]},
)


def sha_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------ 沙盒

def make_sandbox(bm_source: str) -> str:
    """造一个独立沙盒：`_root.py` 副本 + `build_manifest.py` 副本 + 空根标记。"""
    sb = tempfile.mkdtemp(prefix="manifest-check-verify-")
    os.makedirs(os.path.join(sb, "tools", "build"))
    os.makedirs(os.path.join(sb, "data"))
    shutil.copy(ROOT_PY, os.path.join(sb, "tools", "_root.py"))
    with open(os.path.join(sb, "tools", "build", "build_manifest.py"),
              "w", encoding="utf-8") as fh:
        fh.write(bm_source)
    # ⚠️ 必须在任何运行之前就写这个空标记，find_root() 才会停在沙盒、
    #    而不是一路向上找到真仓库的 MANIFEST.sha256。
    open(os.path.join(sb, "MANIFEST.sha256"), "w").close()
    return sb


def run(sb: str, *args: str) -> tuple[int, str]:
    p = subprocess.run(
        [sys.executable, os.path.join(sb, "tools", "build", "build_manifest.py"), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=sb)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def write_state(sb: str) -> None:
    """把沙盒还原成「清单刚生成好」的初始状态。"""
    with open(os.path.join(sb, "data", "a.txt"), "w", encoding="utf-8") as fh:
        fh.write(A_BODY)
    with open(os.path.join(sb, "data", "b.txt"), "w", encoding="utf-8") as fh:
        fh.write(B_BODY)
    c = os.path.join(sb, "data", "c.txt")
    if os.path.exists(c):
        os.remove(c)


def apply_mutation(sb: str, mutate: str | None) -> None:
    if mutate in (None,):
        return
    if mutate in ("modify_a", "all_three"):
        with open(os.path.join(sb, "data", "a.txt"), "w", encoding="utf-8") as fh:
            fh.write("A MODIFIED\n" * 30)              # 名字不变、内容与大小都变
    if mutate in ("add_c", "all_three"):
        with open(os.path.join(sb, "data", "c.txt"), "w", encoding="utf-8") as fh:
            fh.write("C new\n")
    if mutate in ("del_b", "all_three"):
        os.remove(os.path.join(sb, "data", "b.txt"))


def run_case(bm_source: str, case: dict) -> tuple[bool, str, str]:
    """→ (是否符合预期, 原始输出, 不符合的原因)。沙盒用完即删。"""
    sb = make_sandbox(bm_source)
    try:
        write_state(sb)
        rc0, out0 = run(sb)                            # 先跑写入模式生成清单
        if rc0 != 0:
            return False, out0, f"沙盒里生成清单就失败了（exit={rc0}）"
        apply_mutation(sb, case["mutate"])
        rc, out = run(sb, "--check")

        why: list[str] = []
        if rc != case["rc"]:
            why.append(f"退出码 {rc} ≠ 期望 {case['rc']}")
        if case["counts"] is None:
            # 无差异时只打 ✅、**不打**三类计数行（那是失败摘要的一部分）
            if rc == 0 and "❌" in out:
                why.append("退出码 0，但输出里出现了 ❌")
        else:
            m = COUNTS_RE.search(out)
            if not m:
                why.append("输出里没有三类计数行（解析不到「名字不在清单 N、…」）")
            else:
                got = tuple(int(x) for x in m.groups()[:3])
                if got != case["counts"]:
                    why.append(f"类别计数 {got} ≠ 期望 {case['counts']}")
        for needle in case["must_contain"]:
            if needle not in out:
                why.append(f"输出里缺 {needle!r}")
        scale = SCALE_RE.search(out)
        if not scale or int(scale.group(1)) > 10:
            why.append("报告的不是沙盒规模"
                       f"（清单里 {scale.group(1) if scale else '?'} 个）"
                       "——疑似跑到了真仓库，必须立刻停！")
        return (not why), out, "；".join(why)
    finally:
        shutil.rmtree(sb, ignore_errors=True)


# ------------------------------------------------------------------ selftest

#: 把 ③「名字在、内容被改」的判定退回旧版（只比名字）。selftest 用它证明本测试会红。
NEUTER_FROM = """        changed = sorted(r for r in (new & set(old))         # ③ 名字在、内容/大小变了
                         if actual.get(r) != old[r])"""
NEUTER_TO = """        changed = []   # selftest：故意退回旧版行为（只比名字，不比哈希）"""


def selftest(verbose: bool) -> int:
    print("=== --selftest：证明本测试**会红**（把副本的哈希比对退回旧版）===")
    print()
    src = open(BM, encoding="utf-8").read()
    if NEUTER_FROM not in src:
        print("❌ 在 build_manifest.py 里找不到 ③ 的判定代码，selftest 无法进行。")
        print("   （实现改了的话，请同步更新本脚本里的 NEUTER_FROM/NEUTER_TO）")
        return 1
    neutered = src.replace(NEUTER_FROM, NEUTER_TO)

    repo_before = (sha_file(MAN_SHA), sha_file(MAN_TXT))
    case = next(c for c in CASES if c["mutate"] == "modify_a")

    print(f"用例：{case['name']}（期望 {case['counts']}，exit {case['rc']}）")
    print()
    ok_real, out_real, why_real = run_case(src, case)
    print(f"① 用**真脚本**跑该用例 → 本测试判定：{'✅ 通过（符合预期）' if ok_real else '❌ 不通过'}")
    if not ok_real:
        print(f"   原因：{why_real}")
    ok_broken, out_broken, why_broken = run_case(neutered, case)
    print(f"② 用**退回旧版**的副本跑同一用例 → 本测试判定："
          f"{'❌ 不通过 ← 这正是我们要的：本测试抓到了' if not ok_broken else '✅ 通过（说明本测试的断言是空的！）'}")
    if not ok_broken:
        print(f"   抓到原因：{why_broken}")
    if verbose:
        print("\n── 退回旧版时的原始输出 ──")
        print(out_broken.rstrip())
        print("── 真脚本时的原始输出 ──")
        print(out_real.rstrip())

    repo_after = (sha_file(MAN_SHA), sha_file(MAN_TXT))
    same = repo_before == repo_after
    print()
    print(f"③ 安全检查：真仓库 MANIFEST.sha256 / MANIFEST.txt 未被改动：{same}")
    print(f"   {repo_before[0][:16]}… → {repo_after[0][:16]}…")
    print(f"   {repo_before[1][:16]}… → {repo_after[1][:16]}…")

    good = ok_real and (not ok_broken) and same
    print()
    print("✅ selftest 通过：真脚本下本测试通过；**退回旧版（只比名字）后本测试抓得到**——"
          "本测试不是空转。" if good else "❌ selftest 未通过（见上）")
    return 0 if good else 1


# ------------------------------------------------------------------ main

def main(argv: list[str] | None = None) -> int:
    force_utf8_io()          # 入口第一件事：GBK 控制台下不许崩（见 tools/_root.py）
    ap = argparse.ArgumentParser(
        description="build_manifest.py --check 的正反验证（三类差异 + 类别正确 + 不碰真仓库）")
    ap.add_argument("-v", "--verbose", action="store_true", help="附每个用例的原始输出")
    ap.add_argument("--selftest", action="store_true",
                    help="把副本的哈希比对退回旧版，断言本测试会红")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest(args.verbose)

    print("build_manifest.py --check 的正反验证")
    print(f"项目根：{ROOT}")
    print("三重保险：沙盒自带空 MANIFEST.sha256 当根标记 / 断言报告的是沙盒规模 / 核对真清单未变")
    print()

    repo_before = (sha_file(MAN_SHA), sha_file(MAN_TXT))
    src = open(BM, encoding="utf-8").read()

    failed = 0
    for case in CASES:
        ok, out, why = run_case(src, case)
        mark = "✅" if ok else "❌"
        print(f"{mark} {case['name']:22} 期望 exit={case['rc']} 计数={case['counts']}"
              + (f"   ← {why}" if why else ""))
        if not ok:
            failed += 1
            for line in out.splitlines():
                print(f"      │ {line}")
        elif args.verbose:
            for line in out.splitlines():
                print(f"      │ {line}")

    repo_after = (sha_file(MAN_SHA), sha_file(MAN_TXT))
    same = repo_before == repo_after
    print()
    print(f"安全检查：真仓库 MANIFEST.sha256 / MANIFEST.txt 未被改动：{same}")
    if not same:
        failed += 1

    print()
    if failed:
        print(f"❌ {failed} 项不符合预期（含安全检查）——"
              "要么 `--check` 的哈希比对坏了，要么它跑到了真仓库。")
        return 1
    print(f"✅ {len(CASES)}/{len(CASES)} 个用例符合预期，且真仓库清单未被触碰。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
