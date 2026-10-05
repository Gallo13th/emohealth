#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""守卫：``data/**`` 改了但 ``ui/**`` 没重新打包（**默认拦截**，不靠人记得跑）。

为什么需要
==========
``tools/ui/pack_ui_data.py`` 的 ``--check`` 能逐字节比对 23 个产物，但它**只有人主动跑
才有效**。本项目已连续两轮在人工验收里抓到「``data/`` 改了、``ui/items-structured/*.js``
没跟着重生」——界面**静默用旧数据**，不报错、不白屏，只是展示的内容与源头不符。
所以把这件事固化成一条会自己红的守卫。

判据：**逐 job** 比 mtime，不用全局最大 mtime
==========================================
对 ``pack_ui_data.py`` 声明的每一条 job 分别算：

    · 输入集合 = 该 job 的 ``inputs``（见 ``--list``；源 ``data/**``、``engine/**`` 等）
                 → 取**最大** mtime（最新输入）
    · 产物集合 = 该 job 的产物（``ui/**``）→ 取**最小** mtime（最旧产物）
    · 最新输入 mtime **严格大于** 最旧产物 mtime → ❌ 该 job 过期
    · 预期产物不存在（新增了源文件却没重打包）→ ❌

为什么不能拿「全仓最大 mtime」比：任何**无关**文件一被改（比如某个 check 脚本、
某份文档、别的作业的源）就会把整个仓库判红，守卫生效的第二天就会被无视。
逐 job 对应之后，只有**该作业自己的**输入变新才会红——这才拦得住又吵不到人。

只到「打包」这一层（边界说明）
==============================
本守卫只比对**打包器的直接输入**（``pack_ui_data.py`` 真正读的那些文件）。
若上游 build 脚本的输入（如 ``content/**``、``archive/**``）变了、而 build 脚本没重跑，
那么 ``data/**`` 与 ``ui/**`` 仍然**彼此一致**——那是**上游新鲜度**问题，
不在本守卫口径内（各自由对应的 ``check_*`` 负责）。本守卫守住的是最后一段：
``data/** → ui/**``。

已知局限（诚实写出来）
====================
* mtime 是启发式：``git checkout``、整目录复制、云盘同步都可能把 mtime 设得与内容新旧
  无关。此时报 ❌ 并不代表内容真的旧——**这是刻意的保守**：重打包一次即可消除，
  而漏报（静默用旧数据）的代价大得多。
* 反向也成立：若有人把产物 mtime 手动改新（或复制了一份新的 ``ui/``），守卫会误判为新鲜。
  内容层面的最终裁决仍是 ``python tools/ui/pack_ui_data.py --check``（逐字节）。

用法
====
    python tools/check/check_pack_freshness.py             # 检查；过期/缺失 = 退出码 1
    python tools/check/check_pack_freshness.py -v          # 附每个 job 的最新/最旧明细
    python tools/check/check_pack_freshness.py --selftest  # 真的改 mtime → 断言报红 → 还原

退出码：全部 job 新鲜 0；任一过期/产物缺失/源为空 1。
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.join(TOOLS, "ui"))       # `import pack_ui_data`

import pack_ui_data as pack  # noqa: E402
from _root import force_utf8_io  # noqa: E402

FRESH, STALE, UNKNOWN = "fresh", "stale", "unknown"

#: 报告里「怎么修」的提示
FIX_HINT = "python tools/ui/pack_ui_data.py"


def _full(rel: str) -> str:
    return os.path.join(pack.ROOT, *rel.split("/"))


def _mtime(rel: str) -> float:
    return os.path.getmtime(_full(rel))


def _fmt(t: float) -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t))


def _span(newer: float, older: float) -> str:
    d = max(0.0, newer - older)
    if d < 60:
        return f"{d:.0f} 秒"
    if d < 3600:
        return f"{d / 60:.1f} 分"
    if d < 86400:
        return f"{d / 3600:.1f} 小时"
    return f"{d / 86400:.1f} 天"


def inspect(job: dict) -> dict:
    """算一个 job 的新鲜度（只读 mtime / 存在性，不读内容、不执行打包）。"""
    patterns = pack.job_input_patterns(job)
    empty_patterns = [p for p in patterns if not pack.glob_rel(p)]
    ins = pack.job_input_paths(job)
    outs = pack.job_output_paths(job)
    res = {"job": job, "name": job["name"], "inputs": ins, "outputs": outs,
           "empty_patterns": empty_patterns}

    missing_out = [p for p in outs if not os.path.exists(_full(p))]
    if missing_out:
        res.update(status=STALE, reason=f"产物缺失 {len(missing_out)} 个",
                   missing_out=missing_out)
        return res
    if not ins or not outs:
        res.update(status=UNKNOWN,
                   reason="源为空/不存在，无法判定（打包器同样跑不了）")
        return res

    newest_in = max(ins, key=_mtime)
    oldest_out = min(outs, key=_mtime)
    res.update(newest_in=newest_in, oldest_out=oldest_out,
               newest_in_t=_mtime(newest_in), oldest_out_t=_mtime(oldest_out))
    if res["newest_in_t"] > res["oldest_out_t"]:
        res.update(status=STALE, reason="输入比产物新")
    else:
        res.update(status=FRESH, reason="")
    return res


def check_all() -> list[dict]:
    return [inspect(job) for job in pack.JOBS]


def report(results: list[dict], verbose: bool = False) -> int:
    print(f"打包新鲜度检查（项目根：{pack.ROOT}）")
    print("口径：逐 job 比「最新输入 mtime」与「最旧产物 mtime」"
          "（不用全局最大 mtime；作业表见 python tools/ui/pack_ui_data.py --list）")
    print()

    stale = [r for r in results if r["status"] == STALE]
    unknown = [r for r in results if r["status"] == UNKNOWN]

    for r in results:
        tag = {FRESH: "✅", STALE: "❌", UNKNOWN: "⚠️ "}[r["status"]]
        head = (f"{tag} {r['name']:16} 输入 {len(r['inputs']):3} / "
                f"产物 {len(r['outputs']):3}")
        if r["status"] == FRESH:
            print(f"{head}   最新输入 {_fmt(r['newest_in_t'])} {r['newest_in']}")
            print(f"{'':19}   ≤ 最旧产物 {_fmt(r['oldest_out_t'])} {r['oldest_out']}")
        else:
            print(f"{head}   {r['reason']}")

    if verbose:
        print()
        for r in results:
            print(f"── {r['name']}（输入 {len(r['inputs'])} / 产物 {len(r['outputs'])}）")
            for p in r["inputs"]:
                print(f"     输入  {_fmt(_mtime(p))}  {p}")
            for p in r["outputs"]:
                exists = os.path.exists(_full(p))
                mark = "      " if exists else "  ✗缺失"
                when = _fmt(_mtime(p)) if exists else "        --        "
                print(f"    {mark}产物  {when}  {p}")

    if stale or unknown:
        print()
        print(f"❌ {len(stale)} 个作业过期" + (f"，{len(unknown)} 个无法判定" if unknown else ""))
        for r in stale + unknown:
            print()
            print(f"── {r['name']}：{r['reason']}")
            if r.get("missing_out"):
                for p in r["missing_out"]:
                    print(f"   ✗ 预期产物不存在：{p}")
            if r.get("empty_patterns"):
                for p in r["empty_patterns"]:
                    print(f"   ⚠ 声明的输入一个都没匹配到：{p}")
            if r.get("newest_in"):
                print(f"   最新输入：{r['newest_in']}   {_fmt(r['newest_in_t'])}")
                print(f"   最旧产物：{r['oldest_out']}   {_fmt(r['oldest_out_t'])}"
                      f"   （输入新 {_span(r['newest_in_t'], r['oldest_out_t'])}）")
            print(f"   修法：{FIX_HINT}"
                  + (f" --only {r['name']}" if r["status"] == STALE else ""))
        print()
        print("   说明：本守卫只看 mtime（启发式）。内容层面的最终裁决是 "
              "`python tools/ui/pack_ui_data.py --check`（逐字节）。")
        return 1

    print()
    print(f"✅ {len(results)} 个作业全部新鲜：没有任何 job 的输入比它的产物新。")
    return 0


# --------------------------------------------------------------------- selftest

def _case_missing_output() -> tuple[bool, str]:
    """沙盒用例：**新增一个源 json 却没重打包** → 预期产物缺失 → 必须 ❌。

    这正是本项目两次踩到的形态（`ui/items-structured/*.js` 没跟着 `data/` 重生）。
    在临时沙盒里做，不碰仓库里的任何文件。
    """
    root = tempfile.mkdtemp(prefix="pack-fresh-")
    real_root = pack.ROOT
    try:
        os.makedirs(os.path.join(root, "data", "demo"))
        os.makedirs(os.path.join(root, "ui", "demo"))
        with open(os.path.join(root, "data", "demo", "a.json"), "w", encoding="utf-8") as fh:
            fh.write("{}")
        with open(os.path.join(root, "ui", "demo", "a.js"), "w", encoding="utf-8") as fh:
            fh.write("x")
        pack.ROOT = root
        job = {"name": "demo", "src_dir": "data/demo", "dst_dir": "ui/demo",
               "inputs": ("data/demo/*.json",)}
        before = inspect(job)
        with open(os.path.join(root, "data", "demo", "b.json"), "w", encoding="utf-8") as fh:
            fh.write("{}")
        after = inspect(job)
        ok = (before["status"] == FRESH and after["status"] == STALE
              and bool(after.get("missing_out")))
        detail = (f"新增 data/demo/b.json 前 {before['status']} / 后 {after['status']}"
                  f"（{after['reason']}：{after.get('missing_out')}）")
        return ok, detail
    finally:
        pack.ROOT = real_root
        shutil.rmtree(root, ignore_errors=True)


def selftest() -> int:
    """**真的**改一个输入的 mtime、断言报红、再逐纳秒还原、断言报绿。

    不 mock：注入与还原都走 ``os.utime``，还原失败会显式报错——否则「selftest 通过」
    本身就是假的。
    """
    print("=== --selftest：证明本守卫**真的会红**（真改 mtime + 真还原）===")
    print()

    base = check_all()
    dirty = [r["name"] for r in base if r["status"] != FRESH]
    if dirty:
        print("❌ 前置条件不满足：仓库当前就有不新鲜的 job → " + "、".join(dirty))
        print("   先跑 `python tools/ui/pack_ui_data.py` 再作 selftest。")
        return 1
    print(f"① 前置：{len(base)} 个作业当前全部新鲜 ✅")

    job = next(j for j in pack.JOBS if j["name"] == "tier")
    rel = pack.job_input_paths(job)[0]
    full = _full(rel)
    before = os.stat(full)
    print(f"② 选定注入点：job `{job['name']}` 的输入 {rel}")
    print(f"   注入前：mtime {_fmt(before.st_mtime)}（ns={before.st_mtime_ns}）")

    try:
        bumped = time.time() + 5
        os.utime(full, ns=(before.st_atime_ns, int(bumped * 1e9)))
        after = os.stat(full)
        changed = after.st_mtime_ns != before.st_mtime_ns
        print(f"   注入后：mtime {_fmt(after.st_mtime)}（ns={after.st_mtime_ns}）"
              f"  —— mtime 真的变了：{changed}")
        if not changed:
            print("❌ 注入没生效，selftest 无意义")
            return 1

        injected = inspect(job)
        if injected["status"] != STALE:
            print(f"❌ 注入后本应报 ❌，实际报 {injected['status']}——守卫是空转的！")
            return 1
        print(f"③ 注入后：`{job['name']}` → ❌ {injected['reason']}")
        print(f"   最新输入 {injected['newest_in']}   {_fmt(injected['newest_in_t'])}")
        print(f"   最旧产物 {injected['oldest_out']}   {_fmt(injected['oldest_out_t'])}"
              f"   （输入新 {_span(injected['newest_in_t'], injected['oldest_out_t'])}）")
        print(f"   → 整个仓库的判定："
              f"{'❌ 有过期作业（退出码 1）' if any(r['status'] != FRESH for r in check_all()) else '✅ 仍是绿的（守卫无效）'}")
        ok_inject = injected["status"] == STALE and any(
            r["status"] != FRESH for r in check_all())
    finally:
        os.utime(full, ns=(before.st_atime_ns, before.st_mtime_ns))

    restored = os.stat(full)
    same = (restored.st_mtime_ns == before.st_mtime_ns
            and restored.st_atime_ns == before.st_atime_ns)
    print(f"④ 还原：mtime {_fmt(restored.st_mtime)}（ns={restored.st_mtime_ns}）"
          f"  —— 与注入前逐纳秒一致：{same}")
    if not same:
        print("❌ mtime 没有被精确还原，仓库留在被改过的状态")
        return 1

    back = inspect(job)
    if back["status"] != FRESH:
        print(f"❌ 还原后本应报 ✅，实际报 {back['status']}")
        return 1
    print(f"⑤ 还原后：`{job['name']}` → ✅ 新鲜"
          f"（最新输入 {_fmt(back['newest_in_t'])} ≤ 最旧产物 {_fmt(back['oldest_out_t'])}）")

    if not ok_inject:
        return 1

    print()
    print("⑥ 第二个失败形态（本项目踩过的原形）：新增源文件却没重打包 → 产物缺失")
    ok_missing, detail = _case_missing_output()
    print(f"   沙盒实测：{detail}")
    if not ok_missing:
        print("❌ 「新增源文件却没重打包」没有被抓到——守卫漏了本项目踩过的那个坑")
        return 1

    print()
    print("✅ selftest 通过：① mtime 注入 → ❌，逐纳秒还原 → ✅；"
          "② 新增源文件未打包 → ❌（产物缺失）。守卫不是空转。")
    return 0


def main(argv: list[str] | None = None) -> int:
    force_utf8_io()          # 入口第一件事：GBK 控制台下不许崩（见函数 docstring）
    ap = argparse.ArgumentParser(
        description="守卫：data/** 改了但 ui/** 没重新打包（逐 job 比 mtime）")
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="附每个 job 的输入/产物 mtime 明细")
    ap.add_argument("--selftest", action="store_true",
                    help="真改一个输入的 mtime → 断言报 ❌ → 还原 → 断言报 ✅")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    return report(check_all(), verbose=args.verbose)


if __name__ == "__main__":
    sys.exit(main())
