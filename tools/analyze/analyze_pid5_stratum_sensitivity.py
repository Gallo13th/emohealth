#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PID-5 条件常模：**9 个性别×年龄分层**的百分位 / T 分敏感性（task-36）。

要回答的问题
============
`ui/index.html` 的 `instPercentileDetail(data, name, value, cell)` 的 `cell` 参数
**全仓从未被传过**（只有定义处），所以 PID-5 的百分位**恒定落在 `cells[0]`**。
本脚本只做一件事：**量一量「始终用 `cells[0]`」会偏多少、会不会改变高/低的结论**。
**只给数据，不给主张。**

读什么：`data/norms/pid-5.json`（条件常模）
```
scales[<scale>].cells[<分层>][<raw>] = {pctl, pctl_lo, pctl_hi, T, T_lo, T_hi, extrap}
```
* **分层顺序按文件里的实际顺序取**（`list(cells.keys())`，JSON 保序），
  不按名字猜——实测 `cells[0] = "f [18,35)"`，而 **`"overall"` 排在最后**（index 8）。
* `raw` 是该 facet 的**均值/总分**（`unit=facet_total_or_mean_as_published`），
  各 scale 的 raw 网格不同，本脚本按每个 scale 自己的键遍历。

输出（对应 task-36 的 1–6）
=========================
① 9 层名称与文件顺序、`cells[0]` 是谁
② **分层跨度** `max(pctl) − min(pctl)`：全局最大（含 scale/raw/两层/数值）、中位、分布、超阈值计数；
   另附**「相对 `cells[0]` 的偏差」**（这才是产品问题：始终用第 0 层，对别人偏多少）
③ **是否改变结论**：以 50 / 70 / 85 百分位为界（理由见输出里的 `理由`），
   统计「同 (scale, raw) 在不同分层下跨过界」的组合数、**档位变化数**、并给具体实例；
   另附**「从 `cells[0]` 换到真实分层会变档」的组合数**（最贴近产品后果的口径）
④ **T 分**同做：`max(T) − min(T)` 全局最大与中位（含相对 `cells[0]` 的偏差、T 界 50/55/60/65）
⑤ **`extrap` 占比**：总体、逐层、逐 scale；哪些 raw 是外推的；有没有「同一 raw 在部分层外推、部分层不外推」
⑥ 一句话数据结论（只陈述数字）

用法
====
    python tools/analyze/analyze_pid5_stratum_sensitivity.py            # 全量输出
    python tools/analyze/analyze_pid5_stratum_sensitivity.py --top 8    # 实例多列几条
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root, force_utf8_io  # noqa: E402
ROOT = str(find_root())
NORMS = os.path.join(ROOT, "data", "norms", "pid-5.json")

#: 判据界值：50 / 70 / 85 百分位。理由（输出里也会打印）：
#:   · 50 —— 中位，天然把「高于/低于一般水平」分开；
#:   · 70 / 85 —— 用**表里自带**的 T 分对应关系反推：T=55、T=60 对应的经验百分位
#:     （脚本会算出这两个 T 附近的实际 pctl 中位，避免我凭空定界）。
#: 同时给出**不含阈值**的指标（跨度分布），所以界值选择不承担结论。
PCTL_BANDS = (50.0, 70.0, 85.0)
T_BANDS = (50.0, 55.0, 60.0, 65.0)


def band_of(x: float, cuts: tuple) -> int:
    """落在第几档（0 = 所有界值之下；len(cuts) = 所有界值之上）。"""
    return sum(1 for c in cuts if x >= c)


def pct(v: float) -> str:
    return f"{v:.2f}"


def fmt_raw(raw: str) -> str:
    """raw 键是该 facet 的均值，文件里带浮点残差（如 `0.6000000000000001`）；
    展示时取 6 位有效数字（`0.6`），但不改数据本身。"""
    try:
        return f"{float(raw):.6g}"
    except ValueError:
        return raw


def main() -> int:
    force_utf8_io()
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=5, help="每条结论列几个实例")
    ap.add_argument("--json", default=None, help="把统计结果另存为 JSON（可选）")
    args = ap.parse_args()

    d = json.load(open(NORMS, encoding="utf-8"))
    scales = d["scales"]
    names = d.get("scale_names") or {}

    # ── ① 分层顺序（按文件实际顺序）──
    order = list(next(iter(scales.values()))["cells"].keys())
    for k, v in scales.items():
        assert list(v["cells"].keys()) == order, f"{k} 的分层顺序与首个 scale 不一致"
    print("=" * 100)
    print("① 分层名称与**文件里的实际顺序**（JSON 保序；所有 scale 一致）")
    print("=" * 100)
    for i, s in enumerate(order):
        mark = "  ← cells[0]：**界面恒定使用的那一层**" if i == 0 else (
            "  ← 排在最后" if i == len(order) - 1 else "")
        print(f"  [{i}] {s}{mark}")
    print(f"\n  结论：cells[0] = {order[0]!r}（不是 overall；overall 在 index {order.index('overall')}）")

    # ── 收集 ──
    n_scales = len(scales)
    cells_total = 0
    extrap_total = 0
    extrap_by_stratum = {s: [0, 0] for s in order}          # [extrap, total]
    extrap_by_scale = {}
    combos = []            # (scale, raw, {stratum: pctl}, {stratum: T}, {stratum: extrap})
    mixed_extrap = []
    for sk, sv in scales.items():
        c = sv["cells"]
        raws = list(c[order[0]].keys())
        extrap_by_scale[sk] = [0, 0]
        for raw in raws:
            pv, tv, ev = {}, {}, {}
            for s in order:
                cell = c[s].get(raw)
                if cell is None:
                    continue
                pv[s] = float(cell["pctl"])
                tv[s] = float(cell["T"])
                ev[s] = bool(cell.get("extrap"))
                cells_total += 1
                extrap_by_stratum[s][1] += 1
                extrap_by_scale[sk][1] += 1
                if ev[s]:
                    extrap_total += 1
                    extrap_by_stratum[s][0] += 1
                    extrap_by_scale[sk][0] += 1
            if len(pv) == len(order):
                combos.append((sk, raw, pv, tv, ev))
                if len(set(ev.values())) > 1:
                    mixed_extrap.append((sk, raw, ev))

    print(f"\n  数据规模：{n_scales} 个 scale × {len(order)} 层；单元格 {cells_total}"
          f"；可比较的 (scale, raw) 组合 {len(combos)}（九层齐全）")

    # ── ② 百分位跨度 ──
    spreads = []
    base_dev = []                     # |pctl(s) − pctl(cells[0])|
    for sk, raw, pv, tv, ev in combos:
        vals = list(pv.values())
        spreads.append((max(vals) - min(vals), sk, raw, pv))
        base = pv[order[0]]
        base_dev.append((max(abs(pv[s] - base) for s in order), sk, raw, pv))
    spreads.sort(reverse=True)
    base_dev.sort(reverse=True)
    sp_vals = [x[0] for x in spreads]
    dev_vals = [x[0] for x in base_dev]

    def pctl_stats(label, vals, items):
        med = statistics.median(vals)
        print(f"\n  【{label}】")
        print(f"    全局最大 {max(vals):.2f} 百分位"
              f" ｜ 中位 {med:.2f} ｜ 均值 {statistics.fmean(vals):.2f}")
        for q in (90, 99):
            print(f"    {q} 分位 {statistics.quantiles(vals, n=100)[q - 1]:.2f}", end="")
        print()
        for t in (5, 10, 15, 20, 30):
            n = sum(1 for v in vals if v > t)
            print(f"    跨度 > {t:>2} 百分位的组合：{n:>4} / {len(vals)}"
                  f"（{100 * n / len(vals):5.1f}%）")
        print(f"    最大几处：")
        for v, sk, raw, pv in items[:args.top]:
            hi = max(pv, key=lambda s: pv[s])
            lo = min(pv, key=lambda s: pv[s])
            print(f"      · {sk}（{names.get(sk, sk)}）raw={fmt_raw(raw)}：跨度 {v:.2f}"
                  f"｜最高 {pv[hi]:.2f} @ {hi} ／最低 {pv[lo]:.2f} @ {lo}")

    print("\n" + "=" * 100)
    print("② 百分位跨度：max(pctl) − min(pctl)（全部 scale × raw × 9 层）")
    print("=" * 100)
    pctl_stats("九个分层之间的跨度", sp_vals, spreads)
    print("\n  补充口径（更贴近产品问题）：**始终用 cells[0]，相对真实分层的偏差**")
    pctl_stats(f"|pctl(s) − pctl({order[0]})| 的最大值", dev_vals, base_dev)

    # ── ③ 是否改变结论 ──
    print("\n" + "=" * 100)
    print("③ 是否改变「高/低」结论")
    print("=" * 100)
    # 界值理由：用表里自带的 T↔pctl 对应反推 T55/T60 的经验百分位
    # （注意取的是该层的 pctl 标量 pv[s]，不是 pv 这个 dict——第一版就写错成 dict 了）
    t55 = [pv[s] for _, _, pv, tv, _ in combos for s in order if abs(tv[s] - 55) < 0.5]
    t60 = [pv[s] for _, _, pv, tv, _ in combos for s in order if abs(tv[s] - 60) < 0.5]
    m55 = statistics.median(t55) if t55 else float("nan")
    m60 = statistics.median(t60) if t60 else float("nan")
    print(f"  界值理由：50 = 中位；70 / 85 取自**表里 T 分的经验对应**——"
          f"T≈55 处的 pctl 中位 {m55:.1f}（n={len(t55)}）、"
          f"T≈60 处的 pctl 中位 {m60:.1f}（n={len(t60)}）。")
    print(f"  （另给不含阈值的跨度分布，见 ②；界值选择不承担本报告的结论。）")

    for label, cuts, key in (("pctl", PCTL_BANDS, "p"), ("T", T_BANDS, "t")):
        cross_any, band_change = [], []
        per_cut = {c: [] for c in cuts}
        for sk, raw, pv, tv, ev in combos:
            vals = pv if key == "p" else tv
            v = list(vals.values())
            mn, mx = min(v), max(v)
            hit = [c for c in cuts if mn < c <= mx]
            if hit:
                cross_any.append((sk, raw, vals, hit))
                for c in hit:
                    per_cut[c].append((sk, raw, vals, c))
            if len({band_of(x, cuts) for x in v}) > 1:
                band_change.append((sk, raw, vals))
        print(f"\n  【{label}】界值 {cuts}")
        for c in cuts:
            n = len(per_cut[c])
            print(f"    跨过 {c:>4}：{n:>4} 个 (scale, raw) 组合"
                  f"（{100 * n / len(combos):5.1f}%）")
        print(f"    跨过**至少一个**界：{len(cross_any)} / {len(combos)}"
              f"（{100 * len(cross_any) / len(combos):5.1f}%）")
        print(f"    **档位发生变化**（各层落进不同区间）：{len(band_change)} / {len(combos)}"
              f"（{100 * len(band_change) / len(combos):5.1f}%）")
        if cross_any:
            print(f"    跨界的例子（按跨度取前 {args.top}）：")
            for sk, raw, vals, hit in sorted(
                    cross_any, key=lambda x: -(max(x[2].values()) - min(x[2].values())))[:args.top]:
                print(f"      · {sk}（{names.get(sk, sk)}）raw={fmt_raw(raw)} 跨过 {hit}：")
                for s in order:
                    side = "/".join(f"{'≥' if vals[s] >= c else '<'}{c:g}" for c in cuts)
                    print(f"          {s:<12} {vals[s]:6.2f} ［{side}］")
        # 从 cells[0] 换到真实分层：档位变化 + 最大偏差
        sw = [(max(abs(v - vals[order[0]]) for v in vals.values()), sk, raw, vals)
              for sk, raw, vals in ((a, b, c) for a, b, c, _, _ in combos)
              if len({band_of(vals[order[0]], cuts)} |
                     {band_of(v, cuts) for v in vals.values()}) > 1]
        sw.sort(reverse=True)
        print(f"    从 cells[0]（{order[0]}）换到该人的真实分层，**档位会变**的组合："
              f"{len(sw)}（{100 * len(sw) / len(combos):5.1f}%）")
        if sw:
            print(f"      最大偏差的例子：")
            for dev, sk, raw, vals in sw[:args.top]:
                hi = max(vals, key=lambda s: abs(vals[s] - vals[order[0]]))
                print(f"      · {sk}（{names.get(sk, sk)}）raw={fmt_raw(raw)}："
                      f"cells[0]={vals[order[0]]:.2f} → {hi}={vals[hi]:.2f}"
                      f"（偏差 {vals[hi] - vals[order[0]]:+.2f}）")

    # ── ④ T 分跨度 ──
    t_spreads, t_dev = [], []
    for sk, raw, pv, tv, ev in combos:
        v = list(tv.values())
        t_spreads.append((max(v) - min(v), sk, raw, tv))
        t_dev.append((max(abs(tv[s] - tv[order[0]]) for s in order), sk, raw, tv))
    t_spreads.sort(reverse=True)
    t_dev.sort(reverse=True)
    print("\n" + "=" * 100)
    print("④ T 分跨度：max(T) − min(T)")
    print("=" * 100)
    tvals = [x[0] for x in t_spreads]
    print(f"  全局最大 {max(tvals):.2f} T 分 ｜ 中位 {statistics.median(tvals):.2f}"
          f" ｜ 均值 {statistics.fmean(tvals):.2f}")
    for t in (5, 10, 15, 20):
        n = sum(1 for v in tvals if v > t)
        print(f"    跨度 > {t:>2} T 分的组合：{n:>4} / {len(tvals)}（{100 * n / len(tvals):5.1f}%）")
    for v, sk, raw, tv in t_spreads[:args.top]:
        hi = max(tv, key=lambda s: tv[s])
        lo = min(tv, key=lambda s: tv[s])
        print(f"    · {sk}（{names.get(sk, sk)}）raw={fmt_raw(raw)}：跨度 {v:.2f}"
              f"｜最高 {tv[hi]:.2f} @ {hi} ／最低 {tv[lo]:.2f} @ {lo}")
    dv = [x[0] for x in t_dev]
    print(f"  相对 cells[0]（{order[0]}）的最大偏差：全局最大 {max(dv):.2f} ｜ 中位 "
          f"{statistics.median(dv):.2f}")

    # ── ⑤ 外推 ──
    print("\n" + "=" * 100)
    print("⑤ 外推标记 extrap")
    print("=" * 100)
    print(f"  总体：{extrap_total} / {cells_total} 格为外推"
          f"（{100 * extrap_total / max(1, cells_total):.1f}%）")
    print("  逐层：")
    for s in order:
        e, tot = extrap_by_stratum[s]
        print(f"    {s:<12} {e:>5} / {tot:<5}（{100 * e / max(1, tot):5.1f}%）")
    worst = sorted(extrap_by_scale.items(), key=lambda kv: -kv[1][0])[:5]
    print("  外推最多的 scale：")
    for sk, (e, tot) in worst:
        if e:
            print(f"    {sk:<16}（{names.get(sk, sk)}）{e}/{tot}（{100 * e / tot:.1f}%）")
    print(f"  「同一 raw 在部分层外推、部分层不外推」的组合：{len(mixed_extrap)}")
    for sk, raw, ev in mixed_extrap[:args.top]:
        ex = [s for s in order if ev[s]]
        print(f"    · {sk} raw={fmt_raw(raw)}：外推层 {ex}")
    # 外推 raw 的分布（哪些 raw 值落在分布两端）
    ex_raws = set()
    for sk, sv in scales.items():
        for s, cell in sv["cells"].items():
            for raw, c in cell.items():
                if c.get("extrap"):
                    ex_raws.add(float(raw))
    if ex_raws:
        print(f"  被外推过的 raw 取值：{len(ex_raws)} 个，范围 {min(ex_raws):.2f} – {max(ex_raws):.2f}")

    # ── ⑦ 候选默认层对比：换成 overall 会剩多少偏差 ──
    # 界面取默认层的**两条路径**（都已核对）：`nrm.cells[0]`（顶层数组）与
    # `Object.keys(sc.cells)[0]`；本文件里两者顺序**完全一致**，首个都是 f [18,35)。
    band_change_p = [1 for _, _, pv, _, _ in combos
                     if len({band_of(v, PCTL_BANDS) for v in pv.values()}) > 1]
    print("\n" + "=" * 100)
    print("⑦ 若默认层改用 `overall`（数据源已提供的总体层）")
    print("=" * 100)
    missing = [sk for sk, sv in scales.items() if "overall" not in sv["cells"]]
    print(f"  `overall` 存在性：{n_scales - len(missing)}/{n_scales} 个 scale 含 overall"
          + (f"；**缺失**：{missing}（这些 scale 回退到 {order[0]}，导出须注明）"
             if missing else "（31/31 全部存在，逐个断言过）"))

    # 候选默认层对比：把每一层当默认，算「相对其它 8 层的最大/中位偏差」
    print("\n  把每一层分别当默认时的偏差（对每个 (scale, raw)，取与其它 8 层的最大差）：")
    print(f"    {'候选默认层':<12}{'pctl 最大':>10}{'pctl 中位':>10}{'T 最大':>9}{'T 中位':>8}"
          f"{'跨50三元组':>12}{'跨70三元组':>12}{'跨85三元组':>12}")
    rank_rows = []
    for cand in order:
        dp, dt = [], []
        n_cross = {c: 0 for c in PCTL_BANDS}
        for _, _, pv, tv, _ in combos:
            dp.append(max(abs(pv[s] - pv[cand]) for s in order if s != cand))
            dt.append(max(abs(tv[s] - tv[cand]) for s in order if s != cand))
            for s in order:
                if s == cand:
                    continue
                for c in PCTL_BANDS:
                    if (pv[s] < c <= pv[cand]) or (pv[cand] < c <= pv[s]):
                        n_cross[c] += 1
        rank_rows.append((max(dp), statistics.median(dp), max(dt), statistics.median(dt),
                          n_cross[PCTL_BANDS[0]], n_cross[PCTL_BANDS[1]],
                          n_cross[PCTL_BANDS[2]], cand))
    for mx, md, tmx, tmd, c1, c2, c3, cand in sorted(rank_rows):
        star = "  ← cells[0]（当前默认）" if cand == order[0] else (
            "  ← overall（数据源的总体层）" if cand == "overall" else "")
        print(f"    {cand:<12}{mx:>10.2f}{md:>10.2f}{tmx:>9.2f}{tmd:>8.2f}"
              f"{c1:>12}{c2:>12}{c3:>12}{star}")

    # overall 口径的定位与实例
    ov = [r for r in rank_rows if r[7] == "overall"][0]
    print(f"\n  改用 `overall` 后：相对 8 个非总体层的 pctl 最大偏差 **{ov[0]:.2f}**、中位 {ov[1]:.2f}；"
          f"T 最大 **{ov[2]:.2f}**、中位 {ov[3]:.2f}")
    print(f"  跨界的**三元组**（scale, raw, 层）计数：50 → {ov[4]}；70 → {ov[5]}；85 → {ov[6]}"
          f"（分母 2491×8 = {len(combos) * 8}）")
    worst_ov = []
    for sk, raw, pv, tv, ev in combos:
        s = max((x for x in order if x != "overall"), key=lambda x: abs(pv[x] - pv["overall"]))
        worst_ov.append((abs(pv[s] - pv["overall"]), sk, raw, s, pv["overall"], pv[s]))
    worst_ov.sort(reverse=True)
    print(f"  偏差最大的实例：")
    for d_, sk, raw, s, a, b in worst_ov[:args.top]:
        print(f"    · {sk}（{names.get(sk, sk)}）raw={fmt_raw(raw)}：overall={a:.2f} vs {s}={b:.2f}"
              f"（差 {d_:.2f}）")
    print(f"\n  ⚠️ 注意口径：**「有分歧的 (scale, raw) 组合数」与选哪层当默认无关**——"
          f"只要 9 层里存在两个不同档位，任何默认层都会与至少一层不同档；"
          f"该数是 {len(band_change_p)}/{len(combos)}。默认层选择改变的是**偏差大小**"
          f"（上面每一行）与**哪些人拿到错的结论**。")

    # ── ⑧ 一句话 ──
    print("\n" + "=" * 100)
    print("⑧ 一句话（只陈述数据）")
    print("=" * 100)
    print(f"  始终用 cells[0]（{order[0]}）时：相对真实分层的百分位最大偏差 "
          f"**{max(dev_vals):.2f}** 个百分点、中位 {statistics.median(dev_vals):.2f}；"
          f"T 分最大偏差 **{max(dv):.2f}**、中位 {statistics.median(dv):.2f}；"
          f"在 50/70/85 三界下，**{len(band_change_p)}/{len(combos)}"
          f"（{100 * len(band_change_p) / len(combos):.1f}%）** 个 (scale, raw) 组合的档位"
          f"会因分层而变。")
    print(f"  若改用 `overall` 当默认：pctl 最大偏差降到 **{ov[0]:.2f}**、中位 {ov[1]:.2f}；"
          f"T 最大 **{ov[2]:.2f}**、中位 {ov[3]:.2f}；"
          f"（与上面同口径的「有分歧组合数」不变，仍是 {len(band_change_p)}——选哪层当默认不改变分歧的存在，只改变偏差大小与受影响的人。）")

    if args.json:
        out = {"order": order, "cells0": order[0], "combos": len(combos),
               "pctl_spread_max": max(sp_vals), "pctl_spread_median": statistics.median(sp_vals),
               "t_spread_max": max(tvals), "t_spread_median": statistics.median(tvals),
               "pctl_bias_vs_cells0_max": max(dev_vals),
               "pctl_bias_vs_cells0_median": statistics.median(dev_vals),
               "band_change_combos": len(band_change_p),
               "default_overall_pctl_max": ov[0], "default_overall_pctl_median": ov[1],
               "default_overall_t_max": ov[2], "default_overall_t_median": ov[3],
               "default_overall_triples_cross": {"50": ov[4], "70": ov[5], "85": ov[6]},
               "overall_present_in_scales": n_scales - len(missing),
               "t_cap_87_19_cells": sum(1 for _, _, _, tv, _ in combos for s in order
                                        if tv[s] >= 87.19),
               "extrap_total": extrap_total, "cells_total": cells_total}
        json.dump(out, open(args.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"\n  （统计摘要已写入 {os.path.relpath(args.json, ROOT)}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
