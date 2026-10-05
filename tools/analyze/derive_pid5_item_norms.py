#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""补 PID-5 的**题级均值/SD** → `data/item-norms-pid5.json`。

为什么需要（task-17 用户指示「补数据」）
========================================
`data/**` 里只有 facet 的 T 分表，没有题级分布，于是 `engine/inference.py` 只能拿
「T 分表插值 + 面内等 SD」顶上，导致**原始分误差条跨尺度被放大**
（MAE/理论SE 在 0–3 尺度 ≈1.20–1.26、在 1–4 尺度 ≈1.28–1.75；相关系数不受影响）。
这里从两份公开原始作答直接算题级统计。

两份样本**尺度不同，不能直接拼**（既有教训：`build_pid5_psychometrics.py` 的
Fisher-z 分样本）
==============
  · `donor_kerber2022.csv`  1,243 人，**0–3**
  · `SKIDComMet_data.csv`   1,228 人，**1–4**
先各自用**自己的 min/max** 翻转反向题（与 `build_pid5_psychometrics.py` 同法），
再把 SKID 平移到 0–3 约定（`x -= 1`）。⚠️ 平移与反向可交换：先平移再翻转
`(0+3)−(x−1) = 4−x`，与先翻转再平移完全相同，所以这一步不会改变计分方向。

合并口径（**不直接拼原始数据**）
================================
  · 均值：`Σ nₛ·meanₛ / Σ nₛ`（按人数加权）
  · SD  ：**组内合并** `sqrt(Σ (nₛ−1)·SDₛ² / Σ (nₛ−1))`
    —— 刻意**不用**「把两样本拼起来算总体 SD」：那样会把两样本的**均值差**
    也计入方差（组间方差），算出偏大的 SD。这与「分样本算再合并」的既有教训同源。
  · 逐样本的值一并落盘，便于审计与替换。

输出：`data/item-norms-pid5.json`
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = str(find_root())

DATA = os.path.join(ROOT, "archive", "norms", "pid-5-psychometrics",
                    "zenodo-extracted", "data")
OUT = os.path.join(ROOT, "data", "item-norms-pid5.json")
SAMPLES = [("donor_kerber2022.csv", 0, 3), ("SKIDComMet_data.csv", 1, 4)]
MISSING = {"", " ", "NA", "na", "NaN", ".", "-"}


def load_sample(fname: str, lo: int, hi: int, shift: int):
    """返回 {item_id: [计分值, ...]}（反向题按该样本自己的 min/max 翻转，再平移）。"""
    rev = set(json.load(open(os.path.join(ROOT, "data", "pid5-reverse-keys.json"),
                             encoding="utf-8"))["reverse_keyed"])
    with open(os.path.join(DATA, fname), encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    cols = sorted([c for c in rows[0] if c.strip().lower().startswith("pid_")],
                  key=lambda c: int("".join(ch for ch in c if ch.isdigit()) or 0))
    series: dict[str, list[float]] = {}
    for o in range(1, 221):
        iid = "pid5_%03d" % o
        vals: list[float] = []
        for r in rows:
            v = (r[cols[o - 1]] or "").strip()
            if v in MISSING:
                continue
            x = float(v)
            if iid in rev:
                x = (lo + hi) - x
            vals.append(x + shift)
        series[iid] = vals
    return series


def stat(vals: list[float]) -> tuple[int, float, float]:
    n = len(vals)
    if n < 2:
        return n, (vals[0] if vals else 0.0), 0.0
    m = sum(vals) / n
    var = sum((x - m) ** 2 for x in vals) / (n - 1)
    return n, m, math.sqrt(var)


def main() -> int:
    per_sample = {}
    for fname, lo, hi in SAMPLES:
        shift = -lo                       # 平移到 0 起（kerber 0–3 不动；SKID 1–4 → 0–3）
        series = load_sample(fname, lo, hi, shift)
        per_sample[fname] = {iid: stat(v) for iid, v in series.items()}
        print(f"  ✓ {fname}：{len(series)} 题（原始尺度 {lo}–{hi} → 0–3，shift={shift:+d}）")

    items = {}
    for o in range(1, 221):
        iid = "pid5_%03d" % o
        ns = mm = 0.0
        ss = sd = 0.0
        parts = {}
        for fname, _lo, _hi in SAMPLES:
            n, m, s = per_sample[fname][iid]
            parts[fname] = {"n": n, "mean": round(m, 4), "sd": round(s, 4)}
            ns += n
            mm += n * m
            ss += (n - 1) * s * s
            sd += (n - 1)
        mean = mm / ns if ns else 0.0
        pooled_sd = math.sqrt(ss / sd) if sd else 0.0
        items[iid] = {"id": iid, "n": int(ns), "mean": round(mean, 4),
                      "sd": round(pooled_sd, 4), "per_sample": parts}

    payload = {
        "instrument": "PID-5",
        "source": ("两份公开原始作答（Zenodo 22280403 / zenodo-extracted）："
                   "donor_kerber2022.csv（1,243 人，0–3）、"
                   "SKIDComMet_data.csv（1,228 人，1–4）"),
        "license": "见 data/norms/pid-5.json 与 archive/norms/pid-5-psychometrics/README.md",
        "unit": "item_score_0_to_3（计分方向；反向题已按各样本自己的 min/max 翻转并平移对齐）",
        "method": ("分样本算题级均值/SD → SKID 平移到 0–3 → 均值按人数加权、"
                   "SD 用组内合并 sqrt(Σ(nₛ−1)SDₛ²/Σ(nₛ−1))；"
                   "**不拼接原始数据**（两样本尺度与人群都不同）"),
        "combine_note": (
            "**合并口径（为什么不能直接拼两份样本）**："
            "① 两份样本的作答尺度不同——`donor_kerber2022.csv` 是 0–3、"
            "`SKIDComMet_data.csv` 是 1–4——且人群不同（临床+非临床 vs 配额样本）；"
            "把原始数据直接拼起来会把「尺度差」与「组间均值差」算进方差与相关，"
            "得到偏大的 SD 与偏低的题间相关（既有教训见 "
            "`tools/build/build_pid5_psychometrics.py` 的 Fisher-z 分样本合并）。"
            "② 本文件的做法：**各自**用自己的 min/max 翻转反向题"
            "（0–3 即 `(0+3)−v`、1–4 即 `(1+4)−v`）→ 再把 SKID 平移到 0–3 约定"
            "（`x−1`；平移与反向可交换：先平移再翻转 `(0+3)−(x−1) = 4−x`，"
            "与先翻转再平移完全相同，所以**不改变计分方向**）。"
            "③ 合并：均值按人数加权 `Σnₛ·meanₛ / Σnₛ`；"
            "SD 用**组内合并** `sqrt(Σ(nₛ−1)·SDₛ² / Σ(nₛ−1))`，"
            "刻意**不**用「拼起来算总体 SD」——那会把两样本的均值差也计入方差"
            "（组间方差）。④ 逐样本的 n / mean / sd 保留在 `items[*].per_sample`，"
            "可单独审计或替换。"),
        "n_note": ("逐题 n 为该题在两样本中的非缺失作答总数；"
                   "两份样本合计 2,471 人，220 题全答者 1,534 人"
                   "（与 build_pid5_psychometrics.py 的口径一致）"),
        "usage_boundary": ("题级分布用于把预测换算回**原始分尺度**；"
                           "不得把单题均值当成 facet 测量结果（见 "
                           "research/inference-validation-report.md）。"),
        "items": items,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write("\n")
    print(f"  ✓ 写出 {os.path.relpath(OUT, ROOT)}（{os.path.getsize(OUT) / 1024:.0f} KB，"
          f"{len(items)} 题）")

    # ---- 交叉核对：facet 均值是否与常模表（T 分表插值）大致一致 ----
    inst = json.load(open(os.path.join(ROOT, "data", "instruments", "pid-5.json"),
                          encoding="utf-8"))
    dims = [d["id"] for d in inst["dimensions"] if d.get("items")]
    print("\n  facet 均值交叉核对（题级均值 → facet 均分 vs 常模 T 分表 T=50 处的原始分）")
    norms = json.load(open(os.path.join(ROOT, "data", "norms", "pid-5.json"),
                           encoding="utf-8"))
    names = {k: "".join(c for c in (v or "").lower() if c.isalnum())
             for k, v in (norms.get("scale_names") or {}).items()}
    worst = 0.0
    for dim in dims:
        own = [items[i]["mean"] for i in next(d for d in inst["dimensions"]
                                              if d["id"] == dim)["items"]]
        m_item = sum(own) / len(own)
        nd = "".join(c for c in (next(d for d in inst["dimensions"]
                                      if d["id"] == dim)["name"]).lower() if c.isalnum())
        key = None
        for k, nv in names.items():
            if nv and (nd.startswith(nv) or nv.startswith(nd)):
                key = k
        cell = (norms["scales"].get(key, {}).get("cells", {})
                .get("f [18,35)", {})) if key else {}
        pts = sorted((v["T"], float(k)) for k, v in cell.items()
                     if isinstance(v, dict) and "T" in v and not v.get("extrap"))
        if not pts:
            continue
        ts = [a for a, _ in pts]
        vs = [b for _, b in pts]

        def interp(x):
            if x <= ts[0]:
                return vs[0]
            if x >= ts[-1]:
                return vs[-1]
            for i in range(1, len(ts)):
                if x <= ts[i]:
                    t = (x - ts[i - 1]) / (ts[i] - ts[i - 1])
                    return vs[i - 1] + t * (vs[i] - vs[i - 1])
            return vs[-1]
        norm_mean = interp(50.0)
        worst = max(worst, abs(m_item - norm_mean))
    print(f"    最大差 = {worst:.3f} 分（题级均值→facet 均分 vs 常模表；"
          f"两套样本人群不同，量级一致即合理）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
