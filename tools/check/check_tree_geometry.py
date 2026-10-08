#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""几何守卫：树布局的「环」必须在画布上成立——**内环真的在中心**。

为什么需要（2026-10-09，task-44）
================================
task-42 把**环序**改成实证的（`item_dim_corr`），但画布几何 `xy` 还是结构性那套：
「能答的最内环」散布在半径 0.31~1.00 上，**图与环序毫无关系**，谈不上「从中心长出来」。
而旧版本脚本**只打印一张表、没有任何断言**——`内环半径 0.307..1.000` 也照样算"通过"，
等于给错误状态盖章。现在把它变成**会红的守卫**（`--selftest` 会证明它真的会红）。

判据（任一条不过 → exit 1）
==========================
  ① **最小半径随环号单调不减**：`min_r(r) >= min_r(r-1)`（内环更靠中心）
  ② **相邻环的半径带不穿插**：`min_r(r) > max_r(r-1)`（「环」读得出来）
  ③ 同一环内半径一致：`max_r(r) - min_r(r) <= 0.02`（成「环」，抖动很小）
  ④ 节点间距：不重合（> 0.008）且**不比旧结构性几何更差**（≥ 旧值 × 0.75；
     低于节点直径 0.055 给 ⚠️——PID-5 的扇区配方本来就近，属既有密度）
  ⑤ 环数三处一致：`len(ringNodes) == meta.rings == 顶层 rings`
  ⑥ 覆盖：每题的 `depth` 与它在 `ringNodes` 里的位置一致，题号不重不漏

用法
====
    python tools/check/check_tree_geometry.py               # 检查（红 = exit 1）
    python tools/check/check_tree_geometry.py --dir DIR     # 换一个 tree-layouts 目录
    python tools/check/check_tree_geometry.py --selftest    # 证明会红：把 xy 换回
                                                            # **结构性**几何造临时副本
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
sys.path.insert(0, TOOLS)

from _root import find_root, force_utf8_io  # noqa: E402

ROOT = str(find_root())
TLDIR = os.path.join(ROOT, "ui", "tree-layouts")
DATA_TL = os.path.join(ROOT, "data", "tree-layouts")

JS_RE = re.compile(r"\s*(?:/\*.*?\*/\s*)?window\.[A-Za-z0-9_]+\s*=\s*(.*);\s*$", re.S)


def load_layout(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        m = JS_RE.match(fh.read())
    if not m:
        raise ValueError(f"{path}：不是 window.<VAR> = {{…}}; 形态")
    return json.loads(m.group(1))


def radii_by_ring(d: dict) -> list[dict]:
    """逐环：题数、半径 min/max。"""
    out = []
    for r, ring in enumerate(d["ringNodes"]):
        rs = [math.hypot(*(d["xy"][str(o)])) for o in ring]
        out.append({"ring": r, "n": len(ring),
                    "min": min(rs) if rs else 0.0,
                    "max": max(rs) if rs else 0.0})
    return out


def min_node_distance(d: dict) -> float:
    """节点间最小距离（**精确**；n ≤ 300，O(n²) 足够快）。

    ⚠️ 曾经写成等距抽样——抽样会**漏掉最近的那一对**，把 IPIP-NEO 的 0.0127 报成
    0.0660（假通过）。这个指标的意义全在最小值上，必须精确。
    """
    pts = list(d["xy"].values())
    best = 9e9
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            dd = math.hypot(pts[i][0] - pts[j][0], pts[i][1] - pts[j][1])
            if dd < best:
                best = dd
    return best


def check_dir(tldir: str) -> tuple[int, list[str]]:
    """→ (失败条数, 输出行)。"""
    lines: list[str] = []
    files = sorted(glob.glob(os.path.join(tldir, "*.js")))
    if not files:
        return 1, [f"❌ {tldir} 下没有 *.js"]
    fails = 0
    for p in files:
        d = load_layout(p)
        code = d["meta"]["instrument"]
        rings = d["ringNodes"]
        table = radii_by_ring(d)
        lines.append(f"── {code}（{d['meta']['items']} 题 / {len(d['clusters'])} 簇 / "
                     f"{len(rings)} 环）")
        lines.append(f"   {'环':>3} {'题数':>5} {'半径 min':>9} {'半径 max':>9}")
        for row in table:
            lines.append(f"   {row['ring']:>3} {row['n']:>5} {row['min']:>9.3f} "
                         f"{row['max']:>9.3f}")
        mins = [row["min"] for row in table]
        maxs = [row["max"] for row in table]
        lines.append(f"   逐环最小半径：{[round(x, 3) for x in mins]}")

        def bad(msg: str) -> None:
            nonlocal fails
            fails += 1
            lines.append(f"   ❌ {msg}")

        # ① 最小半径随环号单调不减
        if any(mins[r] + 1e-9 < mins[r - 1] for r in range(1, len(mins))):
            first = next(r for r in range(1, len(mins)) if mins[r] + 1e-9 < mins[r - 1])
            bad(f"① 最小半径未随环号单调不减：环 {first - 1} = {mins[first - 1]:.3f} → "
                f"环 {first} = {mins[first]:.3f}")
        else:
            lines.append("   ✅ ① 最小半径随环号单调不减（内环真的更靠中心）")
        # ② 相邻环半径带不穿插
        bad_band = [(r, maxs[r - 1], mins[r]) for r in range(1, len(mins))
                    if mins[r] <= maxs[r - 1] + 1e-9]
        if bad_band:
            r, pmax, cmin = bad_band[0]
            bad(f"② 相邻环半径带穿插：环 {r - 1} 最大半径 {pmax:.3f} ≥ 环 {r} 最小半径 "
                f"{cmin:.3f}（共 {len(bad_band)} 处）")
        else:
            lines.append("   ✅ ② 相邻环半径带不穿插")
        # ③ 同环内半径一致
        wide = [row for row in table if row["max"] - row["min"] > 0.02]
        if wide:
            bad("③ 同环内半径不一致（极差 > 0.02）："
                + str([(row["ring"], round(row["max"] - row["min"], 3)) for row in wide][:4]))
        else:
            lines.append("   ✅ ③ 同环内半径一致（成「环」）")
        # ④ 节点间距：不重合，且**不得比旧结构性几何更差**
        #   （PID-5 的簇多而小、扇区窄，中心区本来就近；旧几何实测 0.0131、IPIP-NEO 0.0730。
        #    这一条拦的是「本次改动把中心挤得更死」，不是「节点一定不重叠」——真要完全不重叠
        #    得改数据层的**扇区宽度配方**，不在本守卫范围。低于节点直径 0.055 时给 ⚠️。）
        mind = min_node_distance(d)
        struct = os.path.join(DATA_TL, code.lower() + ".json")
        old_mind = None
        if os.path.exists(struct):
            try:
                with open(struct, encoding="utf-8") as fh:
                    sd = json.load(fh)
                old_mind = min_node_distance(sd)
            except Exception:
                old_mind = None
        if mind <= 0.008:
            bad(f"④ 节点最小间距 {mind:.4f} ≤ 0.008（点重合/几何崩坏）")
        elif old_mind is not None and mind < 0.75 * old_mind:
            bad(f"④ 节点最小间距 {mind:.4f} 比旧结构性几何 {old_mind:.4f} 更差"
                f"（低于旧值的 75%）")
        else:
            # 低于「节点直径常数 0.055」时给出**说清原因**的警告：绝大多数是同一分支上
            # 相邻环的两点（径向间距 = 环步长），旧几何这一步是 0.055~0.073。
            step = min((table[r]["min"] - table[r - 1]["min"] for r in range(1, len(table))),
                       default=0.0)
            pts = list(d["xy"].values())
            n_close = sum(1 for i in range(len(pts)) for j in range(i + 1, len(pts))
                          if math.hypot(pts[i][0] - pts[j][0],
                                        pts[i][1] - pts[j][1]) < 0.055)
            warn = ""
            if mind < 0.055:
                warn = (f"　⚠️ {n_close} 对点距离 < 节点直径常数 0.055"
                        f"（同心环步长 {step:.3f}：同簇相邻环节点刚好相切；"
                        f"旧几何与此同量级）")
            lines.append(f"   ✅ ④ 节点最小间距 {mind:.4f}（精确）"
                         + (f"，旧结构性几何 {old_mind:.4f}" if old_mind is not None else "")
                         + warn)
        # ⑤ 环数三处一致
        n_rings = [len(rings), d["meta"].get("rings"), d.get("rings")]
        if len(set(n_rings)) != 1:
            bad(f"⑤ 环数不一致：len(ringNodes)={n_rings[0]} / meta.rings={n_rings[1]} / "
                f"顶层 rings={n_rings[2]}")
        else:
            lines.append(f"   ✅ ⑤ 环数三处一致（{n_rings[0]}）")
        # ⑥ 覆盖 + depth 一致
        flat = [o for ring in rings for o in ring]
        depth_ok = all(d["depth"].get(str(o)) == r for r, ring in enumerate(rings) for o in ring)
        cov_ok = (len(flat) == len(set(flat)) == d["meta"]["items"]
                  and sorted(flat) == sorted(int(k) for k in d["depth"]))
        if not (depth_ok and cov_ok):
            bad(f"⑥ 覆盖/depth 不一致：depth 对齐 {depth_ok}、覆盖 {cov_ok}"
                f"（{len(flat)} 题 vs {d['meta']['items']}）")
        else:
            lines.append(f"   ✅ ⑥ 覆盖完整、depth 与环一致（{len(flat)} 题）")
        lines.append("")
    return fails, lines


# ------------------------------------------------------------------ selftest

def _hash(p: str) -> str:
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def selftest() -> int:
    """证明本守卫**会红**：把 `xy` 换回**结构性**几何 → ①/② 必须报错。

    做法：把 `ui/tree-layouts/*.js` 的 payload 复制到临时目录，只把 `xy` 换成
    `data/tree-layouts/<code>.json` 的（结构性）`xy` —— 这正是 task-44 之前的状态。
    真产物**一个字节都不碰**（跑完核对哈希）。
    """
    print("=== --selftest：把几何换回结构性 xy → 必须报错 ===")
    print()
    real = sorted(glob.glob(os.path.join(TLDIR, "*.js")))
    before = {p: _hash(p) for p in real}
    ok = True
    rc_real, _ = check_dir(TLDIR)
    print(f"① 真产物（{len(real)} 个文件）："
          f"{'✅ 全部通过' if rc_real == 0 else f'❌ {rc_real} 条不过'}")
    ok &= (rc_real == 0)

    tmp = tempfile.mkdtemp(prefix="tree-geom-selftest-")
    try:
        n = 0
        for p in real:
            d = load_layout(p)
            code = d["meta"]["instrument"]
            struct = os.path.join(DATA_TL, code.lower() + ".json")
            if not os.path.exists(struct):
                continue
            d2 = json.loads(json.dumps(d))
            d2["xy"] = json.load(open(struct, encoding="utf-8"))["xy"]   # ← 换回结构性几何
            with open(os.path.join(tmp, os.path.basename(p)), "w", encoding="utf-8") as fh:
                fh.write(f"window.EMOHEALTH_TREE_TEST = {json.dumps(d2, ensure_ascii=False)};\n")
            n += 1
        print(f"② 已造 {n} 份「结构性 xy + 实证环序」副本 → {tmp}")
        rc_bad, lines_bad = check_dir(tmp)
        print(f"   本守卫判定：{'❌ 通过（说明它是空转的！）' if rc_bad == 0 else f'✅ 报错 {rc_bad} 条'}")
        for ln in lines_bad:
            s = ln.strip()
            if s.startswith("❌") or s.startswith("✅ ①") or s.startswith("✅ ②"):
                print("      " + s)
        ok &= (rc_bad > 0)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    after = {p: _hash(p) for p in real}
    same = before == after
    print()
    print(f"③ 真产物哈希未被本 selftest 改动：{same}")
    for p in real[:2]:
        print(f"   {os.path.basename(p)} {before[p][:16]}… → {after[p][:16]}…")
    ok &= same

    print()
    print("✅ selftest 通过：真产物 ✅、结构性几何 ❌、真产物未被改动。" if ok
          else "❌ selftest 未通过（见上）")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    force_utf8_io()          # 入口第一件事：GBK 控制台下不许崩
    ap = argparse.ArgumentParser(description="几何守卫：树布局的「环」必须在画布上成立")
    ap.add_argument("--dir", default=None, help="tree-layouts 目录（默认 ui/tree-layouts）")
    ap.add_argument("--selftest", action="store_true",
                    help="把 xy 换回结构性几何造临时副本，断言本守卫会红")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()

    tldir = args.dir or TLDIR
    fails, lines = check_dir(tldir)
    print(f"树布局几何守卫（{tldir}）")
    print("判据：① 最小半径随环号单调不减 ② 相邻环半径带不穿插 ③ 同环半径一致 "
          "④ 节点不重叠 ⑤ 环数三处一致 ⑥ 覆盖完整")
    print()
    for ln in lines:
        print(ln)
    if fails:
        print(f"❌ {fails} 条几何判据不过。")
        return 1
    print("✅ 全部几何判据通过：内环在中心、环带不穿插、节点未重合"
          "（中心区密度若低于节点直径会给 ⚠️，属数据层扇区配方的既有密度）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
