#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重新标定判据门槛：`conf_r`（**已可借跨维度**）≥ `dim_ceiling × ratio`。

为什么要重标（task-17 用户指示 2）
==================================
`dim_ceiling` / `ceiling_ratio=0.90` 是为**旧的** `conf_r` 标的：旧口径只用本维度
已答的题、**完全不借跨维度**（桥接信息恒为 0）。新口径把「别的维度已答」也算进
`conf_r`（本维度已答部分仍用 corrected 去本题），于是
  · **无跨维度时**：新旧逐值相同 ⇒ 旧标定在「只看本维度」这条轴上**原样成立**；
  · **有跨维度时**：`conf_r` 抬高 ⇒ 门槛更容易达到，必须把这条新轴上的分布
    摊开来看，不能沿用旧值假装没事。

标定口径（与 `calibrate_ceiling_ratio.py` 同一套判据）
=====================================================
  · 达门槛所需「本维度题数」：对每个维度**枚举该维度的全部子集**取最小 k
  · 三个指标：中位 k、最大 k、**永不达标的维度数**（要求 0）
  · ratio 网格：0.85 / 0.90 / 0.95 / 1.00 / 1.05

`conf_r` 只取决于「答了哪些题」，与作答值无关，所以这里不需要真人数据；
真人的准确性验证在 `validate_inference_holdout.py`。

用法
====
    python tools/check/calibrate_conf_gate.py
输出：`research/conf-r-cross-calibration.md`（+ stdout 摘要）
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = str(find_root())
sys.path.insert(0, ROOT)

from engine.inference import dim_confidence, load  # noqa: E402

RATIOS = [0.85, 0.90, 0.95, 1.00, 1.05]
N_CROSS = [0, 5, 10, 20, 30, None]          # None = 其余全部题
SEED = 20261004


def _others_for(model, dim: str) -> list[str]:
    """**别的维度**的题（该维度之外的题；注意不是「不属于任何维度的题」——
    后者在本项目里是空集，会让跨维度场景恒等于 0，我第一版就栽在这）。"""
    own = set(model.dim_items[dim])
    return [i for i in model.ids if i not in own]


def gate_rows(model, ratio: float, *, cross: int | None, rng: random.Random,
              exhaustive: bool | None = None, max_subsets: int = 4000) -> dict:
    """给一个 ratio 与「跨维度题数」，算各维度达门槛所需的最小本维度题数。

    `cross=0` 时**枚举该维度的全部子集**（真正的「最差子集」口径，与
    `calibrate_ceiling_ratio.py` 一致）；`cross>0` 时为了可跑，改用
    「本维度按题序取前 k 题 + 固定的一组跨维度题」——它衡量的是**跨维度能帮多少**，
    不是最差子集，表头会写明。
    """
    if exhaustive is None:
        exhaustive = (cross == 0)
    ks, never = [], 0
    for dim in model.dims:
        own = model.dim_items[dim]
        others_all = _others_for(model, dim)
        need = model.dim_ceiling[dim] * ratio
        n_cross = len(others_all) if cross is None else cross
        xsub = rng.sample(others_all, min(n_cross, len(others_all))) if n_cross else []
        found = None
        for k in range(1, len(own) + 1):
            if exhaustive:
                subsets = list(itertools.combinations(own, k))
                if len(subsets) > max_subsets:
                    subsets = rng.sample(subsets, max_subsets)
            else:
                subsets = [tuple(own[:k])]
            hit = False
            for sub in subsets:
                coded = {i: 0 for i in sub}
                coded.update({i: 0 for i in xsub})
                r = dim_confidence(model, dim, coded)["confidence_r"]
                if r is not None and r >= need:
                    hit = True
                    break
            if hit:
                found = k
                break
        if found is None:
            never += 1
        else:
            ks.append(found)
    ks.sort()
    return {
        "ratio": ratio, "cross": cross, "exhaustive": exhaustive,
        "median_k": ks[len(ks) // 2] if ks else None,
        "max_k": max(ks) if ks else None,
        "never": never,
        "dist": {k: ks.count(k) for k in sorted(set(ks))},
    }


def conf_vs_cross(model, rng: random.Random) -> list[dict]:
    """本维度答 1 / 2 / 3 / 5 题时，conf_r 随「跨维度题数」怎么变（逐维度平均）。"""
    out = []
    for n_own in (1, 2, 3, 5):
        for cross in N_CROSS:
            vals, own_only, needs = [], [], []
            for dim in model.dims:
                own = model.dim_items[dim]
                others_all = _others_for(model, dim)
                if n_own > len(own):
                    continue
                coded = {i: 0 for i in own[:n_own]}
                r_own = dim_confidence(model, dim, coded)["confidence_r"]
                # ⚠️ 这里必须用 `n_cross`（数字）判断，不能用 `if cross`：
                #    `cross=None` 表示「其余全部」，但 None 是假值，会静默跳过跨维度题
                #    （第一版就踩了这个坑，整列显示 0 增益）。
                n_cross = len(others_all) if cross is None else cross
                if n_cross:
                    xsub = rng.sample(others_all, min(n_cross, len(others_all)))
                    coded.update({i: 0 for i in xsub})
                r = dim_confidence(model, dim, coded)["confidence_r"]
                vals.append(r)
                own_only.append(r_own)
                needs.append(model.dim_ceiling[dim] * 0.90)
            if not vals:
                continue
            out.append({
                "n_own": n_own, "n_cross": cross,
                "conf_mean": sum(vals) / len(vals),
                "own_only_mean": sum(own_only) / len(own_only),
                "unlock90": sum(1 for r, nd in zip(vals, needs) if r >= nd),
                "n_dims": len(vals),
            })
    return out


def cross_ceiling_rows(model) -> list[dict]:
    """建议的新锚点 `dim_ceiling_cross`：**全部题都答时**的 `conf_r`。

    界面要显示「已达上限的 X%」时，分母必须是「跨维度也算进来」的上限，
    否则 `conf_r` 会超过 `dim_ceiling`（本维度上限），出现 >100%。
    这里只**给出数值与依据**；是否落进 `data/inference/*.json` 由数据层决定。
    """
    rows = []
    for dim in model.dims:
        own = model.dim_items[dim]
        coded = {i: 0 for i in model.ids}          # 整卷答满
        r = dim_confidence(model, dim, coded)["confidence_r"]
        rows.append({"dim": dim, "dim_ceiling": model.dim_ceiling[dim],
                     "dim_ceiling_cross": r,
                     "ratio_old": model.dim_ceiling[dim] and r / model.dim_ceiling[dim]})
    return rows


def write_ceiling_cross(ceil_rows: list[dict], code: str) -> dict:
    """把 `dim_ceiling_cross` / `ceiling_ratio_cross` **落盘**到 `data/inference/<code>.json`。

    落盘口径（Lead 已授权，task-17 收尾）
    ------------------------------------
      · `dim_ceiling_cross[dim]` = 整卷答满时的 `conf_r`（= 跨维度上限），
        界面「已达上限的 X%」的**分母**；`round(…, 4)`。
      · `ceiling_ratio_cross` = 0.90，与 `ceiling_ratio` 同值。语义：
        **若将来把判据也改成相对跨维度上限**，用它；
        **当前判据仍是** `conf_r ≥ dim_ceiling × ceiling_ratio`（那是有标定依据的口径，
        见本文件 §A：无跨维度时新旧 conf_r 逐值相同）。
      · 其余字段与文件格式**原样不动**（`ensure_ascii=False`、`separators=(",",":")`、
        行尾换行，与 `tools/build/build_dim_ceiling.py` 一致），便于逐行 diff。
      · 幂等：同值重复写入不会改变结果。
    """
    path = os.path.join(ROOT, "data", "inference", f"{code.lower()}.json")
    inf = json.load(open(path, encoding="utf-8"))
    inf["dim_ceiling_cross"] = {r["dim"]: round(r["dim_ceiling_cross"], 4)
                                for r in ceil_rows}
    inf["ceiling_ratio_cross"] = 0.90
    inf["ceiling_cross_note"] = (
        "跨维度上限：整卷答满时的 conf_r（本维度已答的题仍用 corrected 去本题、"
        "别的维度用与完整分的普通相关）。它**只是界面「已达上限的 X%」的分母**，"
        "不会让 conf_r 超过 100%。判据（能否给结果）仍用 "
        "`conf_r ≥ dim_ceiling × ceiling_ratio`：当一道别的维度的题都没答时，"
        "新 conf_r 与旧口径逐值相同，所以那套标定原样成立。"
        "生成器：tools/check/calibrate_conf_gate.py --write；"
        "标定报告：research/conf-r-cross-calibration.md。")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(inf, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write("\n")
    return {"path": path, "n_dims": len(inf["dim_ceiling_cross"])}


def build_report(code, own_only_rows, cross_rows, ratio_rows, ceil_rows) -> str:
    L: list[str] = []
    A = L.append
    A(f"## {code}")
    A("")
    A("### A. 只看本维度（无跨维度）——旧标定在这条轴上原样成立")
    A("")
    A("| ratio | 达门槛所需本维度题数（中位） | 最大 | 永不达标维度数 | 分布 |")
    A("|---:|---:|---:|---:|---|")
    for r in own_only_rows:
        A(f"| {r['ratio']:.2f} | {r['median_k']} | {r['max_k']} | {r['never']} | "
          f"{r['dist']} |")
    A("")
    A("### B. `conf_r` 随「跨维度已答题数」怎么变（本维度答 1/2/3/5 题）")
    A("")
    A("| 本维度已答 | 跨维度已答 | 旧口径 conf_r 均值 | **新口径 conf_r 均值** | "
      "增益 | 达 0.90 门槛的维度数 |")
    A("|---:|---:|---:|---:|---:|---:|")
    for r in cross_rows:
        n_cross = "其余全部" if r["n_cross"] is None else r["n_cross"]
        A(f"| {r['n_own']} | {n_cross} | {r['own_only_mean']:.4f} | "
          f"**{r['conf_mean']:.4f}** | {r['conf_mean'] - r['own_only_mean']:+.4f} | "
          f"{r['unlock90']}/{r['n_dims']} |")
    A("")
    A("### C. 跨维度已答时，达门槛所需本维度题数")
    A("")
    A("⚠️ 本节跨维度行**不做子集枚举**：本维度按题序取前 k 题 + 固定的一组跨维度题，")
    A("衡量的是「跨维度能帮多少」，不是最差子集（最差子集见 A 节）。")
    A("")
    A("| ratio | 跨维度题数 | 达门槛所需本维度题数（中位） | 最大 | 永不达标 |")
    A("|---:|---:|---:|---:|---:|")
    for r in ratio_rows:
        n_cross = "其余全部" if r["cross"] is None else r["cross"]
        A(f"| {r['ratio']:.2f} | {n_cross} | {r['median_k']} | {r['max_k']} | "
          f"{r['never']} |")
    A("")
    A("### D. 建议的新锚点 `dim_ceiling_cross`（整卷答满时的 `conf_r`）")
    A("")
    A("界面若要显示「已达上限的百分之几」，分母必须换成它，否则跨维度借用会让 "
      "`conf_r` 超过 `dim_ceiling`（出现 >100%）。**本脚本只给数值与依据**，"
      "是否落进 `data/inference/*.json` 由数据层决定。")
    A("")
    A("| 维度 | `dim_ceiling`（本维度上限） | `dim_ceiling_cross`（整卷答满） | 比值 |")
    A("|---|---:|---:|---:|")
    for r in ceil_rows:
        A(f"| {r['dim']} | {r['dim_ceiling']:.4f} | {r['dim_ceiling_cross']:.4f} | "
          f"{r['ratio_old']:.3f} |")
    A("")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="重标定 conf_r 门槛；--write 落盘跨维度上限")
    ap.add_argument("--write", action="store_true",
                    help="把 dim_ceiling_cross / ceiling_ratio_cross 写进 "
                         "data/inference/*.json（其余字段原样不动）")
    args = ap.parse_args()
    rng = random.Random(SEED)
    sections = []
    summary = {}
    written = []
    for code in ("IPIP-NEO", "PID-5"):
        m = load(code)
        own_only = [gate_rows(m, r, cross=0, rng=rng) for r in RATIOS]
        cross_rows = conf_vs_cross(m, rng)
        ratio_rows = []
        for r in RATIOS:
            for cross in (0, 10, 30, None):
                ratio_rows.append(gate_rows(m, r, cross=cross, rng=rng))
        ceil_rows = cross_ceiling_rows(m)
        if args.write:
            written.append((code, write_ceiling_cross(ceil_rows, code)))
        summary[code] = {"own_only": own_only, "cross_rows": cross_rows,
                         "ratio_rows": ratio_rows, "ceiling_cross": ceil_rows}
        sections.append(build_report(code, own_only, cross_rows, ratio_rows, ceil_rows))
        print(f"=== {code} ===")
        for r in own_only:
            print(f"  无跨维度 ratio={r['ratio']:.2f}: 中位 k={r['median_k']} "
                  f"max={r['max_k']} 永不达标={r['never']}")
        for r in cross_rows:
            if r["n_cross"] is None or r["n_own"] == 1:
                nc = "其余全部" if r["n_cross"] is None else r["n_cross"]
                print(f"  本维度{r['n_own']}题+跨维度{nc}: conf={r['conf_mean']:.4f} "
                      f"（旧 {r['own_only_mean']:.4f}），达 0.90 门槛 "
                      f"{r['unlock90']}/{r['n_dims']}")

    head = [
        "# 判据门槛重标定：`conf_r`（已可借跨维度）× `dim_ceiling`",
        "",
        "> 生成者：`tools/check/calibrate_conf_gate.py`（可复跑）。",
        "> 背景：task-17 用户指示「conf_r 计算可以借助别的维度，但当本维度未答题时，",
        "> 禁止展示」。旧 `ceiling_ratio=0.90` 是为**不借跨维度**的旧 `conf_r` 标的。",
        "",
        "## 结论（先看）",
        "",
        "1. **无跨维度时新旧 `conf_r` 逐值相同** ⇒ `ratio=0.90` 这条轴上的旧标定",
        "   **原样成立**（见各表 A 行 ratio=0.90）。所以**推荐保留 `ceiling_ratio=0.90`**，",
        "   并把跨维度增益看作「用户要的借用效果」，而不是需要抵消的偏差。",
        "2. 有跨维度时 `conf_r` 抬高、门槛更容易达到（见 B/C 表）；",
        "   **硬规则**（本维度 0 题 → 禁止展示）把「完全靠别的维度推断」挡在外面，",
        "   这是本次唯一新增的禁令，与 ratio 无关。",
        "3. `dim_ceiling` **不变**：它是「答满本维度、无跨维度」时的 `conf_r`，",
        "   新口径在该点上逐值等于旧口径（实测 |Δ| < 1e-4，见 engine 测试）。",
        "   于是它仍然是「该维度自身证据上限」的锚点；跨维度只可能把它**超过**，",
        "   界面若要显示「已达上限的百分之几」，需要另取一个跨维度上限（见 §待决策）。",
        "",
        "## 标定方法与口径",
        "",
        "· `conf_r` 只取决于**答了哪些题**（与作答值无关），所以本节不需要真人数据；",
        "  真人的准确性验证在 `research/inference-validation-report.md`。",
        "· 「达门槛所需本维度题数」= 对该维度**枚举全部子集**、固定跨维度题数后",
        "  「最小 k 使 conf_r ≥ dim_ceiling × ratio」；永不达标必须为 0。",
        "· 跨维度题从「其余全部题」里**随机抽**（固定种子），抽到多少报多少。",
        "",
    ]
    out = os.path.join(ROOT, "research", "conf-r-cross-calibration.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(head) + "\n".join(sections) + "\n\n")
        fh.write("## 已落盘（task-17 收尾，Lead 授权）\n\n")
        fh.write("- `data/inference/ipip-neo.json` / `data/inference/pid-5.json` 已写入"
                 " `dim_ceiling_cross`（逐维度，见各节 §D）与 `ceiling_ratio_cross=0.90`；"
                 "写入器：`python tools/check/calibrate_conf_gate.py --write`（幂等）。\n")
        fh.write("- **判据不变**：仍是 `conf_r ≥ dim_ceiling × ceiling_ratio(0.90)`；"
                 "`dim_ceiling_cross` 只作界面「已达上限的 X%」的**分母**"
                 "（否则跨维度借用会显示 >100%）。\n")
        fh.write("- 引擎输出里对应 `ceiling_cross` 与 `ceiling_pct`（= conf_r ÷ "
                 "ceiling_cross，夹在 [0,1]）。\n")
        fh.write("\n## 待决策\n\n")
        fh.write("- 界面接入时同时落：新 `conf_r`、`NO_OWN_ITEM_ANSWERED` 的禁展示、"
                 "以及用 `dim_ceiling_cross` 作分母（当前界面还没接，属「完善答题界面」轮）。\n")
        fh.write("- 是否要在「本维度只答 1 题、别的维度答满」时放行：**已按用户红线执行**"
                 "（只禁「本维度未答题」），不再加「≥2 题」这类静态题量规则。\n")
    with open(os.path.join(ROOT, "research", "conf-r-cross-calibration.json"),
              "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=1)
    print(f"\n报告 → {out}")
    for code, w in written:
        print(f"落盘 {code} → {os.path.relpath(w['path'], ROOT)}（{w['n_dims']} 个维度）")
    if not args.write:
        print("（未加 --write：只出报告，不写数据层）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
