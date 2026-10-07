#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`conf_r` 到底在测什么：**跑数字**复核（不靠字段名猜含义）。

背景：用户答满 PID-5 全 220 题后，导出报告的「置信度 r」不是 1（如 Anhedonia 0.9307），
看起来像 bug。本脚本只做一件事：把「答满时的 r 是什么」按实现跑出来，并给出可复核的等式。

结论口径见 `research/conf_r_definition.md`；本脚本产出它的全部证据：

A. **答满全卷**时逐维 `conf_r` == 数据里的 `dim_ceiling_cross`（跨维度上限）——逐值比对
B. **只答本维度全部题**时 `conf_r` == `dim_ceiling`（本维度上限）
C. `conf_r` 只取决于**答了哪些题**，与**作答值**无关（同一答题集合、全 0 vs 全 3）
D. `dim_ceiling ≤ dim_ceiling_cross < 1`（跨维度上限更高，但**永远不是 1**）
E. 对照 `r2_total`：答满本维度时它 **= 1**，且预测分 == 官方分（"得分答满即精确"）
F. **合成单因子演示**：`√(bᵀΣ⁻¹b)` 在"题目无独特方差（ψ→0）"时才 → 1；
   这解释 r<1 的来源是**每道题的独特方差（测量误差）被 corrected 口径排除**
G. 逐维表格（25 维）：own 上限 / cross 上限 / 比值 / 答满重算值

用法：python tools/analyze/analyze_conf_r_semantics.py
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root, add_root_to_path, force_utf8_io  # noqa: E402

ROOT = str(find_root())
add_root_to_path()

import numpy as np  # noqa: E402

from engine.inference import dim_confidence, load, predict  # noqa: E402

INF = os.path.join(ROOT, "data", "inference", "pid-5.json")
CODE = "PID-5"


def synth_corrected_r(psi: float, k: int = 5) -> float:
    """合成单因子模型：k 道题，λ=√(1−ψ)，Σ = λλᵀ + diag(ψ)（各自方差为 1）。

    按实现同一定义算 `√(bᵀΣ⁻¹b)`：
      bᵢ = corr(zᵢ, T − zᵢ)（corrected，去本题），T = Σⱼ zⱼ。
    ψ=0 ⇒ 题目之间完全相关（无独特方差）⇒ 期望 → 1。
    """
    lam = math.sqrt(max(0.0, 1.0 - psi))
    sigma = np.full((k, k), lam * lam)
    np.fill_diagonal(sigma, 1.0)
    b = np.empty(k)
    for i in range(k):
        others = [j for j in range(k) if j != i]
        cov = sum(sigma[i, j] for j in others)
        var = sum(sigma[j, l] for j in others for l in others)
        b[i] = cov / math.sqrt(var)
    x = np.linalg.pinv(sigma) @ b          # 用伪逆以便 ψ=0 的极限
    return math.sqrt(max(0.0, float(b @ x)))


def main() -> int:
    force_utf8_io()
    ap = argparse.ArgumentParser()
    ap.add_argument("--all-dims", action="store_true", help="列出全部维度（默认列出用户报告涉及的 9 个）")
    args = ap.parse_args()

    model = load(CODE)
    d = json.load(open(INF, encoding="utf-8"))
    own_cap = {k: float(v) for k, v in d["dim_ceiling"].items()}
    cross_cap = {k: float(v) for k, v in d["dim_ceiling_cross"].items()}
    ratio = float(d.get("ceiling_ratio", 0.90))
    dims = [x for x in model.dims if x in own_cap]

    print("=" * 100)
    print("A. 整卷答满（220/220）时逐维 conf_r  vs  数据里的 dim_ceiling_cross")
    print("=" * 100)
    full_coded = {i: 0 for i in model.ids}                  # 只用到"答了哪些题"
    worst_a = 0.0
    rows = []
    for dim in dims:
        r = dim_confidence(model, dim, full_coded)["confidence_r"]
        delta = abs(r - cross_cap[dim])
        worst_a = max(worst_a, delta)
        rows.append((dim, own_cap[dim], cross_cap[dim], r))
    print(f"  维度数 {len(dims)}｜**最大 |重算 conf_r − 文件 dim_ceiling_cross| = {worst_a:.2e}**"
          f"（文件里是 round(…,4)，所以差异应在 1e-4 量级内）")
    for dim, own, cross, r in rows[:4]:
        print(f"    {dim:<22} 重算 {r:.6f}｜文件 cross {cross:.4f}｜own 上限 {own:.4f}")

    print("\n" + "=" * 100)
    print("B. 只答本维度全部题（无跨维度）时 conf_r  vs  dim_ceiling")
    print("=" * 100)
    worst_b = 0.0
    for dim in dims:
        coded = {i: 0 for i in model.dim_items[dim] if i in model.ids}
        r = dim_confidence(model, dim, coded)["confidence_r"]
        worst_b = max(worst_b, abs(r - own_cap[dim]))
    print(f"  **最大 |重算 conf_r − 文件 dim_ceiling| = {worst_b:.2e}**")

    print("\n" + "=" * 100)
    print("C. conf_r 只取决于**答了哪些题**，与作答值无关")
    print("=" * 100)
    resp0 = {i: 0 for i in model.ids}
    resp3 = {i: 3 for i in model.ids}
    p0, p3 = predict(model, resp0), predict(model, resp3)
    diffs = [abs(p0["inferred"][x]["confidence_r"] - p3["inferred"][x]["confidence_r"])
             for x in dims]
    print(f"  全 0 作答 vs 全 3 作答：**逐维 conf_r 最大差 = {max(diffs):.2e}**"
          f"（{len(dims)} 维）→ 它衡量的是「题目集合的信息量」，不是「你答出来的分数」")
    est0 = p0["inferred"][dims[0]]["predicted_score"]
    est3 = p3["inferred"][dims[0]]["predicted_score"]
    print(f"  对照同一维的预测分：全 0 → {est0}；全 3 → {est3}（**预测分随作答值变，conf_r 不变**）")

    print("\n" + "=" * 100)
    print("D. 两个上限的关系：dim_ceiling ≤ dim_ceiling_cross < 1")
    print("=" * 100)
    viol = [x for x in dims if cross_cap[x] < own_cap[x] - 1e-9]
    print(f"  own：min {min(own_cap.values()):.4f}／中位 {statistics.median(own_cap.values()):.4f}"
          f"／max {max(own_cap.values()):.4f}")
    print(f"  cross：min {min(cross_cap.values()):.4f}／中位 {statistics.median(cross_cap.values()):.4f}"
          f"／max {max(cross_cap.values()):.4f}")
    print(f"  cross/own 比值：min {min(cross_cap[x] / own_cap[x] for x in dims):.4f}"
          f"／max {max(cross_cap[x] / own_cap[x] for x in dims):.4f}")
    print(f"  **cross < 1 的维度：{sum(1 for x in dims if cross_cap[x] < 1)}/{len(dims)}**"
          f"（最大 {max(cross_cap.values()):.4f} < 1）"
          f"｜cross < own 的维度：{len(viol)}（应为 0）")
    print(f"  答满时的「已达上限 X%」= conf_r / cross → 逐维 = "
          f"{statistics.median([dim_confidence(model, x, full_coded)['confidence_r'] / cross_cap[x] for x in dims]):.6f}"
          f"（中位；即 100.0%）")

    print("\n" + "=" * 100)
    print("E. 对照口径：答满本维度时 r_total = 1，预测分 == 官方分（得分精确）")
    print("=" * 100)
    one = dims[0]
    own_items = [i for i in model.dim_items[one] if i in model.ids]
    resp_own = {i: 2 for i in own_items}
    po = predict(model, resp_own)
    ib = po["inferred"][one]
    ob = po["official"].get(one)
    print(f"  {one}：只答本维度 {len(own_items)} 题")
    print(f"    confidence_r（判据口径）      = {ib['confidence_r']:.6f}"
          f"   ← 不等于 1，也不是「得分置信度」")
    print(f"    r2_total（预测准确度口径）     = {ib['r2_total']}")
    print(f"    inferred.predicted_score      = {ib['predicted_score']}")
    print(f"    official.value（官方分，答满即精确） = {ob['value'] if ob else None}")
    print(f"    → **两者相等**说明：该维度答满时得分已经精确，"
          f"conf_r 说的不是「分数准不准」")

    print("\n" + "=" * 100)
    print("F. 合成单因子演示：r < 1 的来源 = 每道题的独特方差（corrected 口径把它排除）")
    print("=" * 100)
    print(f"    题数 k=5，λ=√(1−ψ)，Σ = λλᵀ+diag(ψ)（每题方差 1）")
    print(f"    {'ψ（独特方差占比）':<20}{'√(bᵀΣ⁻¹b)':>14}")
    for psi in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6):
        print(f"    {psi:<20.2f}{synth_corrected_r(psi):>14.4f}")
    print("    ⇒ 只有「题目完全没有独特方差」（ψ→0，即题目之间完全相关）时才趋近 1；"
          "真实量表每题都有独特方差，所以上限 < 1。")

    print("\n" + "=" * 100)
    print("G. 逐维表格（own 上限 / cross 上限 / 比值 / 答满重算）")
    print("=" * 100)
    focus = ["Anhedonia", "Anxiousness", "Depressivity", "Submissiveness",
             "Irresponsibility", "Grandiosity", "Impulsivity", "Risk Taking"]
    # 维度名 → id（dim_name 里存的是可读名）
    name2id = {model.dim_name[x]: x for x in dims}
    print(f"  {'维度':<24}{'own 上限':>10}{'cross 上限':>12}{'比值':>8}{'答满重算':>12}")
    show = dims if args.all_dims else [name2id[n] for n in focus if n in name2id]
    for x in show:
        r = dim_confidence(model, x, full_coded)["confidence_r"]
        print(f"  {model.dim_name[x]:<24}{own_cap[x]:>10.4f}{cross_cap[x]:>12.4f}"
              f"{cross_cap[x] / own_cap[x]:>8.4f}{r:>12.6f}")
    if not args.all_dims:
        print(f"  （只列用户报告涉及的 {len(show)} 维；--all-dims 列全部 {len(dims)} 维）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
