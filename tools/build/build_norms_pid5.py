#!/usr/bin/env python3
"""把 Zenodo 的 PID-5 常模表转成项目统一的常模格式。

来源（已入档，CC BY 4.0）
========================
``archive/norms/pid-5/norm_tables_long.csv``（6.9 MB，32,967 行）
出自 Zimmermann, Kerber, Kemper & Weweck (2026) 的
*Population-Representative Norms for the PID-5 and Its Abbreviated Versions*，
DOI 10.5281/zenodo.22280403。参考样本为 GESIS Panel（德国总体，N=4,727）。

表结构（实测表头）
==================
``gender, age_group, raw, pctl_med, pctl_lo, pctl_hi, T, T_lo, T_hi, cell, version,
scale, level, extrapolation, T_cond_lo, T_cond_hi, T_int_lo, T_int_hi``

关键取舍
========
① **只取 ``version="full"``**（220 题完整版），因为界面收录的是完整版；
② **保留性别与年龄分层**——该来源的常模就是条件常模，抹平成一套会丢掉信息、
   也偏离原文口径。界面上给用户选（默认用总体/不指定）；
③ **保留不确定性与外推标记**：``pctl_lo/hi`` 与 ``extrapolation`` 一并带入，
   界面显示百分位时可以如实说明「这个位置在经验范围之外，属外推」；
④ 输出 **raw → 百分位** 的查表（含 T 分），与 IPIP-NEO 常模同构，
   这样界面的百分位换算函数不用改。
"""

from __future__ import annotations

import csv
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
SRC = os.path.join(ROOT, "archive", "norms", "pid-5", "norm_tables_long.csv")
OUT = os.path.join(ROOT, "data", "norms", "pid-5.json")


def main() -> int:
    if not os.path.exists(SRC):
        print(f"✗ 找不到 {SRC}")
        return 1
    rows = 0
    keep = 0
    # scale -> cell("m [18,35)") -> raw -> {pctl, T, ...}
    data: dict[str, dict[str, dict[str, dict]]] = defaultdict(
        lambda: defaultdict(dict))
    scales, cells, versions = set(), set(), set()

    with open(SRC, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            rows += 1
            versions.add(r["version"])
            if r["version"] != "full":
                continue
            keep += 1
            sc, cell = r["scale"], r["cell"]
            scales.add(sc)
            cells.add(cell)
            try:
                raw = float(r["raw"])
            except ValueError:
                continue
            data[sc][cell][repr(raw) if raw != int(raw) else str(int(raw))] = {
                "pctl": round(float(r["pctl_med"]) * 100, 2),
                "pctl_lo": round(float(r["pctl_lo"]) * 100, 2),
                "pctl_hi": round(float(r["pctl_hi"]) * 100, 2),
                "T": round(float(r["T"]), 2),
                "T_lo": round(float(r["T_lo"]), 2),
                "T_hi": round(float(r["T_hi"]), 2),
                "extrap": r["extrapolation"].strip().lower() in ("true", "1", "yes"),
            }

    print(f"CSV 共 {rows} 行；version=full 保留 {keep} 行")
    print(f"version 取值：{sorted(versions)}")
    print(f"量表 {len(scales)} 个；分层 cell {len(cells)} 个")
    print(f"  例：{sorted(cells)[:6]}")

    out = {
        "instrument": "PID-5",
        # ⚠️ 来源用的是**官方缩写**（attention_seek / emo_lability / unusual_beliefs…），
        #    而量表包与界面用全名（Attention Seeking / Emotional Lability…）。
        #    直接按名字查会**静默落空**（百分位全空且不报错），所以显式列出映射。
        #    映射值以 APA 手册的 facet 全名为准。
        "scale_names": {
            "anhedonia": "Anhedonia",
            "anxiousness": "Anxiousness",
            "attention_seek": "Attention Seeking",
            "callousness": "Callousness",
            "deceitfulness": "Deceitfulness",
            "depressivity": "Depressivity",
            "distractibility": "Distractibility",
            "eccentricity": "Eccentricity",
            "emo_lability": "Emotional Lability",
            "grandiosity": "Grandiosity",
            "hostility": "Hostility",
            "impulsivity": "Impulsivity",
            "intimacy_avoid": "Intimacy Avoidance",
            "irresponsibility": "Irresponsibility",
            "manipulativeness": "Manipulativeness",
            "percept_dysreg": "Perceptual Dysregulation",
            "perseveration": "Perseveration",
            "restricted_aff": "Restricted Affectivity",
            "rigid_perfect": "Rigid Perfectionism",
            "risk_taking": "Risk Taking",
            "separation_insec": "Separation Insecurity",
            "submissiveness": "Submissiveness",
            "suspiciousness": "Suspiciousness",
            "unusual_beliefs": "Unusual Beliefs & Experiences",
            "withdrawal": "Withdrawal",
            "negative_affectivity": "Negative Affect",
            "detachment": "Detachment",
            "antagonism": "Antagonism",
            "disinhibition": "Disinhibition",
            "psychoticism": "Psychoticism",
            "total": "Total",
        },
        "source": ("Zimmermann, Kerber, Kemper & Weweck (2026). "
                   "Population-Representative Norms for the PID-5 and Its "
                   "Abbreviated Versions."),
        "source_files": {
            "norm_table": "archive/norms/pid-5/norm_tables_long.csv",
            "doi": "10.5281/zenodo.22280403",
            "readme": "archive/norms/pid-5/README.md",
        },
        "license": "CC BY 4.0（常模表；分析代码 MIT）",
        "n": 4727,
        "n_note": ("参考样本为 GESIS Panel（德国总体，N=4,727），只施测了 34 题 "
                   "PID5BF+ 短表；完整 220 题的分布由三个施测了全量表的供体样本"
                   "（N=2,471）经贝叶斯桥接投影而来。因此这不是「4,727 人做过 "
                   "220 题」，而是**投影后的总体代表性常模**。"),
        "method": "percentile_rank_conditional_on_gender_and_age",
        "unit": "facet_total_or_mean_as_published",
        "percentile_method": "来源直接给出百分位秩（pctl_med/lo/hi），本仓库不重新计算",
        "scale_range": [0, 3],
        "conditional": True,
        "cells": sorted(cells),
        "scales": {sc: {"cells": {c: v for c, v in sorted(cells_d.items())}}
                   for sc, cells_d in sorted(data.items())},
        "columns_note": "raw → {百分比中位与 95% 区间、T 分、是否外推}",

        # ── 描述层信封（tools/build/build_descriptions.py 消费）──────────────
        # 为什么把信封写进同一个文件：本文件**就是** PID-5 的常模记录
        # （data/norms/<code>.json 的约定），再建第二个文件就等于两个真相源。
        # 以下字段是**纯增量**，不改变上面细表的任何数值；
        # tools/check/check_descriptions.py 的 V8 会重新生成并逐字节比对。
        "schema_version": "1.0",
        "record_kind": "detailed_norms",
        "code": "pid-5",
        "status": "available",
        "interpretation_basis": "percentile_conditional_on_gender_and_age",
        "reference_sample": {
            "n": 4727,
            "population": "德国 GESIS Panel（总体代表性概率样本）",
            "recruitment": "概率抽样面板；完整 220 题的分布由三个全量表供体样本"
                           "（N=2,471）经贝叶斯桥接投影得到",
            "year": 2026,
            "conditional_cells": "9 个性别×年龄组（如「f [18,35)」）",
        },
        "detail_source": None,
        "applicability_warning": "常模是**德国总体样本**，不是中国人群；且完整 220 题的百分位是"
                                 "**桥接投影**的结果（4,727 人没有直接做过 220 题）。",
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write("\n")
    print(f"\n✓ 已写出 {os.path.relpath(OUT, ROOT)}"
          f"（{os.path.getsize(OUT) / 1024:.0f} KB）")
    # 抽查一个 facet，确认数字合理（百分位应随 raw 单调升）
    ex = "anhedonia" if "anhedonia" in data else sorted(data)[0]
    cell0 = sorted(data[ex])[0]
    pts = sorted(((float(k), v["pctl"]) for k, v in data[ex][cell0].items()))
    mono = all(pts[i][1] <= pts[i + 1][1] for i in range(len(pts) - 1))
    print(f"抽查 {ex} / {cell0}：{len(pts)} 个 raw 点，"
          f"百分位单调递增：{'是' if mono else '否 ✗'}")
    print(f"  例：raw={pts[0][0]:g}→{pts[0][1]}%ile，"
          f"raw={pts[len(pts)//2][0]:g}→{pts[len(pts)//2][1]}%ile，"
          f"raw={pts[-1][0]:g}→{pts[-1][1]}%ile")
    return 0


if __name__ == "__main__":
    sys.exit(main())
