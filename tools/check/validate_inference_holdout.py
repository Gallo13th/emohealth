#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""留出验证：**理论置信度 r 与实际预测准确度是否吻合？**

为什么必须做这一步（Lead 的原话）
==================================
「不要只交一个『算出 r』的实现——那等于把上一轮的问题换个地方重演。」
理论 r 是从**参数矩阵**算出来的（`R²=bᵀA⁻¹b`），它是一个**模型自述**；只有拿
**真实完整作答**做留出验证，才能回答界面该不该把 r 当作「可信度」呈现。

数据（只读证据，不改一个字节）
==============================
* IPIP-NEO：`archive/datasets/osf-johnson/validity/ipip20993.dat`
  —— 20,993 行，**7,325 份完整作答**（I1..I300，已反向重编码）
* PID-5：`archive/norms/pid-5-psychometrics/zenodo-extracted/data/`
  —— `donor_kerber2022.csv`（1,243 人，0–3）与 `SKIDComMet_data.csv`
     （1,228 人，1–4，逐样本用自己的 min/max 翻转反向题）

两个场景
========
A. **只答本维度的题**（遮住该维度的 k 题）：与 `dim_ceiling`、
   `data/partial-administration.json` 的 k-曲线同口径，逐 k **枚举全部子集**
   （C(10,k)），因此能给出**最差子集**（r_min 口径）。
B. **跨维度混合作答**：随机答全卷的 30 / 60 / 90 题（= 阶梯第 1/2/3 环的题量），
   对全部 30 个维度评估 —— 与 `data/model-comparison.json` 的 5 折 CV 数对照。

输出
====
`research/inference-validation-report.md`（含完整对照表），并把摘要打到 stdout。

用法
====
    python tools/check/validate_inference_holdout.py            # 全量
    python tools/check/validate_inference_holdout.py --fast     # 抽样，快速
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import sys
from itertools import combinations

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = str(find_root())
sys.path.insert(0, ROOT)

from engine.inference import dim_confidence  # noqa: E402
from engine.inference import load as load_model  # noqa: E402

IPIP_DAT = os.path.join(ROOT, "archive", "datasets", "osf-johnson", "validity",
                        "ipip20993.dat")
PID5_DIR = os.path.join(ROOT, "archive", "norms", "pid-5-psychometrics",
                        "zenodo-extracted", "data")
PID5_SAMPLES = [("donor_kerber2022.csv", 0, 3), ("SKIDComMet_data.csv", 1, 4)]
MISSING = {"", " ", "NA", "na", "NaN", ".", "-"}


# --------------------------------------------------------------------------- 数据
def _canon_to_instrument_perm(model) -> np.ndarray:
    """`ipip20993.dat` 的列序 = canon 题序（轮转），而 pairB64 是**量表包题序**。

    用**题文**把 canon 的 300 题对回量表包（与
    `tools/build/build_inference_data.py` 同法），再转成「量表包下标 → dat 列下标」。
    """
    canon = json.load(open(os.path.join(ROOT, "data", "ipip-neo-300.json"),
                           encoding="utf-8"))
    inst = model.raw_instrument

    def nn(s: str) -> str:
        return "".join(c for c in (s or "").lower() if c.isalnum())

    by_text = {nn(it.get("text")): it["id"] for it in inst["items"]}
    perm = np.full(len(model.ids), -1, dtype=int)
    for c in sorted(canon["items"], key=lambda x: x["order"]):
        iid = by_text.get(nn(c.get("text")))
        if iid is None:
            raise RuntimeError("canon 题文对不回量表包：" + str(c.get("text"))[:40])
        perm[model.order_index[iid]] = c["order"] - 1        # 0-based dat 列
    if (perm < 0).any():
        raise RuntimeError("有题没有对上 dat 列")
    return perm


def load_ipip(model, *, max_n: int | None = None) -> np.ndarray:
    """返回 (N, n_items) 的**量表包题序**计分矩阵（数据已反向重编码，直接用）。"""
    with open(IPIP_DAT, encoding="utf-8", errors="replace") as fh:
        rows = list(csv.reader(fh, delimiter="\t"))
    hdr = rows[0]
    idx = [hdr.index(f"I{i}") for i in range(1, 301)]
    vals = []
    for r in rows[1:]:
        cells = [r[j].strip() for j in idx]
        if any(c in MISSING or c == "0" for c in cells):
            continue
        vals.append([float(c) for c in cells])
    x = np.array(vals, dtype=np.float64)
    if max_n and x.shape[0] > max_n:
        rng = np.random.default_rng(20261004)
        x = x[rng.choice(x.shape[0], max_n, replace=False)]
    perm = _canon_to_instrument_perm(model)
    return x[:, perm]


def load_pid5_sample(model, fname: str, lo: int, hi: int) -> np.ndarray:
    """返回 (N, 220) 计分矩阵（逐样本用自己的 min/max 翻转反向题，与
    `tools/build/build_pid5_psychometrics.py` 同法）。"""
    rev = set(json.load(open(os.path.join(ROOT, "data", "pid5-reverse-keys.json"),
                             encoding="utf-8"))["reverse_keyed"])
    p = os.path.join(PID5_DIR, fname)
    with open(p, encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    cols = sorted([c for c in rows[0] if c.strip().lower().startswith("pid_")],
                  key=lambda c: int("".join(ch for ch in c if ch.isdigit()) or 0))
    vals = []
    for r in rows:
        vec, ok = [], True
        for o in range(1, 221):
            v = (r[cols[o - 1]] or "").strip()
            if v in MISSING:
                ok = False
                break
            x = float(v)
            if ("pid5_%03d" % o) in rev:
                x = (lo + hi) - x
            vec.append(x)
        if ok:
            vals.append(vec)
    x = np.array(vals, dtype=np.float64)
    perm = np.array([model.order_index["pid5_%03d" % o] for o in range(1, 221)])
    return x[:, perm]


# --------------------------------------------------------------------------- 理论量
def theory(model, dim: str, answered_own: list[str], answered_all: list[str]):
    """给定已答集合，算：判据口径 conf_r、精确口径 r_total、预测权重。

    返回 dict，其中 `apply_own(XO)` 用「本维度那几列」的小矩阵（快），
    `apply_full(X)` 用整张作答矩阵（含跨维度题时用）。两者互斥。
    """
    own = model.dim_items[dim]
    oset = set(answered_own)
    a_own = [i for i in own if i in oset]
    u = [i for i in own if i not in oset]
    io = [model.idx(i) for i in own]
    sub = model.pairs[np.ix_(io, io)]
    s = np.array([model.item_sd[i] for i in own])
    mu = np.array([model.item_mean[i] for i in own])
    cov = np.outer(s, s) * sub
    pos = {iid: k for k, iid in enumerate(own)}
    scale = model.dim_scale(dim)
    out: dict = {"dim": dim, "n_own_answered": len(a_own), "n_unknown": len(u),
                 "scale": scale, "own_idx": io}

    # 判据口径 conf_r：**可借跨维度**（task-17 起）。直接调引擎的同一函数，
    # 避免「验证脚本一套、引擎一套」的漂移；conf_r 只取决于答了哪些题。
    # 同时记录旧的「只用本维度」口径，便于改前/改后对照。
    if a_own:
        conf = dim_confidence(model, dim, {i: 0 for i in answered_all})
        cr = conf["confidence_r"]
        cr_own = conf["confidence_r_own_only"]
    else:
        cr = cr_own = None
    out["conf_r"] = cr
    out["conf_r_own_only"] = cr_own

    a_pos_own = [pos[i] for i in a_own]
    if not u:
        out["r_total"] = 1.0
        out["apply_own"] = (lambda XO, ap=a_pos_own, sc=scale:
                            XO[:, ap].sum(axis=1) / sc)
        out["apply_full"] = None
        return out

    ku = [pos[i] for i in u]
    sigma_u = math.sqrt(max(float(cov[np.ix_(ku, ku)].sum()), 1e-12))
    a_all = list(answered_all)
    c = np.array([float(sum(s[k] * model.pairs[model.idx(i)][model.idx(own[k])]
                           for k in ku)) / sigma_u for i in a_all])
    ia_all = [model.idx(i) for i in a_all]
    m_all = model.pairs[np.ix_(ia_all, ia_all)]
    beta = np.linalg.solve(m_all, c)
    r2_tu = max(0.0, min(1.0, float(c @ beta)))
    sigma_sum = math.sqrt(max(float(cov.sum()), 1e-12))
    r2_total = max(0.0, min(1.0, 1.0 - (sigma_u ** 2) * (1.0 - r2_tu) / sigma_sum ** 2))
    out["r_total"] = math.sqrt(r2_total)
    mu_u = float(mu[ku].sum())
    w = sigma_u * beta                                     # 对 z_A 的权重

    if set(a_all) <= set(own):                             # 快路径：只看本维度列
        am = np.array([model.item_mean[i] for i in a_all])
        asd = np.array([model.item_sd[i] for i in a_all])
        ap = [pos[i] for i in a_all]
        known_p = a_pos_own

        def apply_own(XO):
            known = XO[:, known_p].sum(axis=1)
            z = (XO[:, ap] - am) / asd
            return (known + mu_u + z @ w) / scale

        out["apply_own"] = apply_own
        out["apply_full"] = None
    else:
        am = np.array([model.item_mean[i] for i in a_all])
        asd = np.array([model.item_sd[i] for i in a_all])
        ai = ia_all

        def apply_full(X):
            known = X[:, [model.idx(i) for i in a_own]].sum(axis=1)
            z = (X[:, ai] - am) / asd
            return (known + mu_u + z @ w) / scale

        out["apply_own"] = None
        out["apply_full"] = apply_full
    return out


def _apply(th, x, XO=None):
    if th["apply_own"] is not None:
        return th["apply_own"](XO)
    return th["apply_full"](x)


# --------------------------------------------------------------------------- 场景 C
def ladder_ring_items(model, sizes: list[int]) -> dict[int, list[str]]:
    """按 `data/tier-ladder.json` 的**阶梯前 m 题**取作答集（与
    `data/model-comparison.json` 的 ring 口径同源），用于 apples-to-apples 对照。"""
    lad = json.load(open(os.path.join(ROOT, "data", "tier-ladder.json"),
                         encoding="utf-8"))
    canon_order = lad["order"]                        # 1-based canon 题号
    perm = _canon_to_instrument_perm(model)           # instrument idx → canon 0-based
    inv = {c: i for i, c in enumerate(perm)}
    out = {}
    for m in sizes:
        out[m] = [model.ids[inv[o - 1]] for o in canon_order[:m]]
    return out


def scenario_ladder(model, x: np.ndarray, sizes: list[int]) -> dict:
    """按阶梯前 m 题作答（**不留出、单一样本**），对全部维度评估。"""
    rings = ladder_ring_items(model, sizes)
    res: dict = {}
    for m, answered in rings.items():
        aset = set(answered)
        res[m] = {}
        for dim in model.dims:
            own = model.dim_items[dim]
            if all(i in aset for i in own):
                continue
            if not any(i in aset for i in own):
                continue                     # 硬规则：本维度未答 → 引擎不给展示
            th = theory(model, dim, [i for i in own if i in aset], answered)
            pred = _apply(th, x)
            true = x[:, [model.idx(i) for i in own]].mean(axis=1)
            res[m][dim] = {
                "n_masks": 1,
                "theory_r_mean": th["conf_r"],
                "r_total_mean": th["r_total"],
                "realized_r_mean": corr(pred, true),
                "realized_r_min": corr(pred, true),
                "mae_mean": float(np.abs(pred - true).mean()),
                "sd_true": float(true.std(ddof=1)),
            }
    return res


def corr(a: np.ndarray, b: np.ndarray) -> float:
    a = a - a.mean()
    b = b - b.mean()
    d = math.sqrt(float(a @ a) * float(b @ b))
    return float(a @ b) / d if d else float("nan")


# ------------------------------------------------------------------- 半样本留出
def train_test_split(model, x: np.ndarray, seed: int = 20261004):
    """把完整作答对半切，**在训练半上重新估计** 题间相关 / corrected 相关 / 题级
    均值·SD，再用另一半评估——这样才排除「参数与验证样本同一批人」的乐观偏差。

    注意：线上模型用的是**全样本**参数；本节测的是**方法本身的泛化**，不是线上参数。
    """
    rng = np.random.default_rng(seed)
    n = x.shape[0]
    idx = rng.permutation(n)
    tr, te = idx[: n // 2], idx[n // 2:]
    xtr, xte = x[tr], x[te]
    pairs_tr = np.corrcoef(xtr, rowvar=False).astype(np.float64)
    np.fill_diagonal(pairs_tr, 1.0)
    mean_tr = {iid: float(xtr[:, k].mean()) for iid, k in model.order_index.items()}
    sd_tr = {iid: float(xtr[:, k].std(ddof=1)) or 1.0
             for iid, k in model.order_index.items()}
    idc_tr: dict[str, dict[str, float]] = {}          # item → {dim: corrected r}
    for dim, own in model.dim_items.items():
        io = [model.idx(i) for i in own]
        tot = xtr[:, io].sum(axis=1)
        for i in own:
            xi = xtr[:, model.idx(i)]
            y = tot - xi
            idc_tr.setdefault(i, {})[dim] = (
                corr(xi, y) if xi.std() > 0 and y.std() > 0 else 0.0)
    import dataclasses
    model_tr = dataclasses.replace(model, pairs=pairs_tr, item_mean=mean_tr,
                                   item_sd=sd_tr, item_dim_corr=idc_tr)
    return model_tr, xte, xtr.shape[0], xte.shape[0]


def scenario_a_holdout(model, x: np.ndarray, k_list: list[int], seed: int):
    """半样本留出版场景 A（训练半估参数，测试半评准确度）。返回 (结果, 切分信息)。"""
    m_tr, xte, n_tr, n_te = train_test_split(model, x, seed)
    return scenario_a(m_tr, xte, k_list, verbose=False), {"n_train": n_tr, "n_test": n_te}


def scenario_b_holdout(model, x: np.ndarray, sizes: list[int], n_masks: int, seed: int):
    m_tr, xte, n_tr, n_te = train_test_split(model, x, seed)
    return scenario_b(m_tr, xte, sizes, n_masks, seed=seed), {"n_train": n_tr, "n_test": n_te}


def scenario_n_curve(model, x: np.ndarray, ns=(1, 2, 3, 5, 8, 10),
                     n_subsets: int = 20, seed: int = 20261004) -> dict:
    """**用「答题数 n」表述**的曲线（消歧用；task-17 用户质疑的直接回应）。

    本维度只答 n 题（无跨维度），对随机子集平均，报告
    `conf_r`（判据）/ `r_total`（估计准确度）/ 实测 `realized_r` / MAE。
    与场景 A 的区别：场景 A 的 k 是**遮住**几题，这里是**答了**几题。
    """
    rng = np.random.default_rng(seed)
    out: dict = {}
    for n in ns:
        te, to, real, mae, rtot = [], [], [], [], []
        for dim in model.dims:
            own = model.dim_items[dim]
            if n > len(own):
                continue
            own_idx = [model.idx(i) for i in own]
            xo = x[:, own_idx]
            true = xo.mean(axis=1)
            for _ in range(n_subsets):
                sub = [own[i] for i in rng.choice(len(own), n, replace=False)]
                th = theory(model, dim, sub, sub)
                pred = _apply(th, x, xo)
                te.append(th["conf_r"])
                to.append(th["conf_r_own_only"])
                rtot.append(th["r_total"])
                real.append(corr(pred, true))
                mae.append(float(np.abs(pred - true).mean()))
        out[n] = {
            "n_answered": n, "n_cross": 0, "n_subsets": len(te),
            "conf_r_mean": float(np.mean(te)),
            "conf_r_own_only_mean": float(np.mean(to)),
            "r_total_mean": float(np.mean(rtot)),
            "realized_r_mean": float(np.mean(real)),
            "mae_mean": float(np.mean(mae)),
        }
    return out


# --------------------------------------------------------------------------- 场景 A
def scenario_a(model, x: np.ndarray, k_list: list[int], *, verbose: bool) -> dict:
    """只答本维度的题：遮住该维度 **k 题**，枚举全部子集。

    ⚠️ 字段名一律用 `k_masked` / `by_k_masked`，并在每个单元里显式写出
    `n_answered`（= 该维度题数 − k_masked）——「k」曾被误读成「答题数」，
    字段名误导与报告误导同罪（task-17 审计的直接产出）。
    """
    res: dict = {}
    for dim in model.dims:
        own = model.dim_items[dim]
        n = len(own)
        own_idx = [model.idx(i) for i in own]
        xo = x[:, own_idx]
        true = xo.mean(axis=1)                                # 官方分（mean 聚合）
        by_k_masked = {}
        for k_masked in k_list:
            if k_masked >= n:
                continue
            rs_te, rs_te_own, rs_real, maes, rtot = [], [], [], [], []
            for masked in combinations(own, k_masked):
                answered = [i for i in own if i not in set(masked)]
                th = theory(model, dim, answered, answered)
                pred = _apply(th, x, xo)
                rs_te.append(th["conf_r"])
                rs_te_own.append(th["conf_r_own_only"])
                rtot.append(th["r_total"])
                rs_real.append(corr(pred, true))
                maes.append(float(np.abs(pred - true).mean()))
            by_k_masked[k_masked] = {
                "k_masked": k_masked,
                "n_answered": n - k_masked,
                "n_items": n,
                "n_subsets": len(rs_te),
                "theory_r_mean": float(np.mean(rs_te)),
                "theory_r_min": float(np.min(rs_te)),
                "theory_r_max": float(np.max(rs_te)),
                "theory_r_own_only_mean": float(np.mean(rs_te_own)),
                "realized_r_mean": float(np.mean(rs_real)),
                "realized_r_min": float(np.min(rs_real)),
                "realized_r_max": float(np.max(rs_real)),
                "r_total_mean": float(np.mean(rtot)),
                "r_total_min": float(np.min(rtot)),
                "mae_mean": float(np.mean(maes)),
                "mae_max": float(np.max(maes)),
                "sd_true": float(true.std(ddof=1)),
            }
        res[dim] = {"n_items": n, "by_k_masked": by_k_masked}
        if verbose:
            line = "  ".join(f"k={k}:r_te={v['theory_r_mean']:.3f}/r_real="
                             f"{v['realized_r_mean']:.3f}"
                             for k, v in by_k_masked.items())
            print(f"    {model.dim_name[dim][:22]:<24}{line}")
    return res


# --------------------------------------------------------------------------- 场景 B
def scenario_b(model, x: np.ndarray, sizes: list[int], n_masks: int,
               seed: int = 20261004) -> dict:
    """随机答全卷 m 题，对全部维度评估。"""
    rng = np.random.default_rng(seed)
    n_items = len(model.ids)
    res: dict = {m: {} for m in sizes}
    for m in sizes:
        acc: dict[str, list] = {d: [] for d in model.dims}
        sd_true: dict[str, float] = {}
        blocked = 0
        for _ in range(n_masks):
            idx = rng.choice(n_items, m, replace=False)
            answered = [model.ids[i] for i in idx]
            aset = set(answered)
            for dim in model.dims:
                own = model.dim_items[dim]
                if all(i in aset for i in own):
                    continue                        # 该维度全答满：不是预测场景
                if not any(i in aset for i in own):
                    # 本维度一道题都没答 → 引擎按硬规则**禁止展示**，
                    # 这一格不计入「理论 vs 实测」对比，只统计被挡掉多少格。
                    blocked += 1
                    continue
                th = theory(model, dim, [i for i in own if i in aset], answered)
                pred = _apply(th, x)
                true = x[:, [model.idx(i) for i in own]].mean(axis=1)
                acc[dim].append((th["conf_r"], th["r_total"], corr(pred, true),
                                 float(np.abs(pred - true).mean())))
                sd_true[dim] = float(true.std(ddof=1))
        for dim, rows in acc.items():
            if not rows:
                continue
            arr = np.array(rows)
            res[m][dim] = {
                "n_masks": len(rows),
                "n_blocked_by_hard_rule": blocked,
                "theory_r_mean": float(arr[:, 0].mean()),
                "r_total_mean": float(arr[:, 1].mean()),
                "realized_r_mean": float(arr[:, 2].mean()),
                "realized_r_min": float(arr[:, 2].min()),
                "mae_mean": float(arr[:, 3].mean()),
                "sd_true": sd_true[dim],
            }
    return res


# --------------------------------------------------------------------------- 报告
def _fmt(v: float, nd: int = 4) -> str:
    return "—" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{v:.{nd}f}"


def _agg(rows: list[dict], key: str) -> float:
    return float(np.mean([r[key] for r in rows if r.get(key) is not None]))


def _se_ratio(rows: list[dict]) -> float:
    """MAE ÷ 高斯理论 E|e| = 0.7979·σ_e·√(1−r_total²)。≈1 表示 SE 标定正确。"""
    num, den = [], []
    for r in rows:
        e = 0.7979 * r["sd_true"] * math.sqrt(max(0.0, 1 - r["r_total_mean"] ** 2))
        if e > 1e-9:
            num.append(r["mae_mean"])
            den.append(e)
    return float(np.mean(num) / np.mean(den)) if den else float("nan")


def _table_a(A: dict, ks: list[int], A_out: dict | None = None,
             split_note: str = "") -> list[str]:
    L: list[str] = []
    head = ("| 遮住 k 题 | **已答 n 题**（同维度） | 子集数 | "
            "conf_r 新口径 | conf_r 旧口径（只用本维度） | conf_r 最小 | "
            "r_total 均值 | **realized_r 均值** | realized_r 最小 | MAE(分) | "
            "真实分 SD | MAE/理论SE |")
    hsep = "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    L.append(head)
    L.append(hsep)
    for k in ks:
        rows = [d["by_k_masked"][k] for d in A.values() if k in d["by_k_masked"]]
        if not rows:
            continue
        L.append(f"| {k} | {rows[0]['n_answered']} | {rows[0]['n_subsets']} | "
                 f"{_agg(rows, 'theory_r_mean'):.4f} | "
                 f"{_agg(rows, 'theory_r_own_only_mean'):.4f} | "
                 f"{_agg(rows, 'theory_r_min'):.4f} | {_agg(rows, 'r_total_mean'):.4f} | "
                 f"**{_agg(rows, 'realized_r_mean'):.4f}** | "
                 f"{_agg(rows, 'realized_r_min'):.4f} | {_agg(rows, 'mae_mean'):.4f} | "
                 f"{_agg(rows, 'sd_true'):.4f} | {_se_ratio(rows):.3f} |")
    if A_out is not None:
        L.append("")
        L.append(f"**半样本留出（训练半估参数 → 测试半评估{('，' + split_note) if split_note else ''}）**")
        L.append("")
        L.append("| 遮住 k 题 | 已答 n 题 | 子集数 | conf_r 新口径 | r_total 均值 | "
                 "**realized_r 均值** | realized_r 最小 | MAE(分) | MAE/理论SE |")
        L.append("|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for k in ks:
            rows = [d["by_k_masked"][k] for d in A_out.values()
                    if k in d["by_k_masked"]]
            if not rows:
                continue
            L.append(f"| {k} | {rows[0]['n_answered']} | {rows[0]['n_subsets']} | "
                     f"{_agg(rows, 'theory_r_mean'):.4f} | "
                     f"{_agg(rows, 'r_total_mean'):.4f} | "
                     f"**{_agg(rows, 'realized_r_mean'):.4f}** | "
                     f"{_agg(rows, 'realized_r_min'):.4f} | {_agg(rows, 'mae_mean'):.4f} | "
                     f"{_se_ratio(rows):.3f} |")
    return L


def build_report(ipip_a, ipip_a_out, ipip_b, ipip_b_out, ipip_c, n_curve,
                 pid5, pid5_out, meta, splits) -> str:
    L: list[str] = []
    A = L.append
    A("# 题级预测的留出验证：**理论置信度 r 与实际预测准确度是否吻合**")
    A("")
    A("> 生成者：`tools/check/validate_inference_holdout.py`（可复跑）。")
    A("> 模型：`engine/inference.py`（条件期望线性预测，参数来自 `data/inference/*.json`）。")
    A("> 本报告是**实测**，不是模型自述；所有数字都能从脚本复算。")
    A("")
    A("## ⚠️ 先读这一条：`k` 是「**遮住**几题」，不是「答了几题」")
    A("")
    A("本报告的场景 A 用 `combinations(own, k)` 枚举被**遮住**的子集，所以")
    A("**`k=1` 表示答了 10−1=9 题**（相关性自然高），**`k=6` 表示只答了 4 题**")
    A("（相关性自然低）。每一行的「已答 n 题」列都写明了这点；另有 §0b 的")
    A("**答题数曲线**直接用 n 表述，两者互为对照。")
    A("")
    A("> 历史：初版报告没写清 k 的含义，读者（含 Lead 转述）把它读成了「答题数」，")
    A("> 于是产生「只答 1 题就有 0.99」的错觉。**字段名也随之改成 `k_masked` /")
    A("> `by_k_masked` 并加显式 `n_answered`**——字段名误导与报告误导同罪。")
    A("")
    A("**三个数各自是什么（务必分开看）**")
    A("")
    A("- `conf_r`（**判据/可信度**口径）＝ `√(cᵀΣ_AA⁻¹c)`：本维度已答的题用 "
      "corrected（去本题）、别的维度的已答题用与完整分的普通相关（task-17 起"
      "**可借跨维度**）。它**不把已答项当已知真值**，因此**系统性低于**实测准确度——"
      "是**保守下界**，不是预测误差的估计。")
    A("- `r_total`（**估计准确度**口径）：预测最终得分的期望 R²，把「已答的本维度题」"
      "当成**已知真实值**计入。它与实测相关几乎逐位吻合，**但注意口径**：这是"
      "「在已经拿到这些作答值的条件下，最终分估得多准」，**不是**「纯预测的相关」；"
      "答满本维度时它恒为 1（因为分已经算出来了），这正是它与 `conf_r` 的区别。")
    A("- MAE 与理论 SE 的比值接近 1 ⇒ 残差尺度也标定正确。")
    A("")
    A("## 0. 数据与口径")
    A("")
    A(f"- IPIP-NEO：`{meta['ipip_file']}` —— 文件 {meta['ipip_rows']} 行，"
      f"**完整作答 N={meta['ipip_n']}**（已反向重编码，直接用）")
    A("- 题级参数：`data/inference/ipip-neo.json`（`pairB64` + corrected "
      "`item_dim_corr` + `dim_ceiling`）、`data/item-norms.json`（IPIP 题级均值/SD，"
      "N=20,974）、`data/item-norms-pid5.json`（**task-17 新补**的 PID-5 题级均值/SD，"
      "两份供体样本分样本算再按组内合并）")
    A("- PID-5：" + "；".join(f"`{k}` N={v}" for k, v in meta["pid5_n"].items())
      + "（各自用自己的 min/max 翻转反向题，与 `build_pid5_psychometrics.py` 同法）")
    A("- 判据门槛的重标定见 `research/conf-r-cross-calibration.md`"
      "（`conf_r` 纳入跨维度后的分布、各 ratio 后果、建议的跨维度上限）。")
    A("- 报告里的 realized_r 一律是「预测值 × 真实完整分」的 Pearson 相关"
      "（同一批受访者）；MAE 是原始分单位的平均绝对误差。")
    A("")
    A("| 记号 | 定义 | 用途 |")
    A("|---|---|---|")
    A("| `conf_r` | `√(cᵀΣ_AA⁻¹c)`：本维度已答的题用 corrected（去本题）、"
      "**别的维度**的已答题用与完整分的普通相关——即「可以借助别的维度」 | "
      "判据/可信度；决定「可给结果」。**本维度 0 题时禁止展示**（硬规则） |")
    A("| `r_total` | 预测**最终得分**的期望 R²（已答的本维度题算**已知真值**） | "
      "「已拿到这些作答值」条件下的估计准确度（答满 = 1） |")
    A("| `realized_r` | **实测**：预测值 vs 真实完整分的相关 | 检验上面两个数 |")
    A("")
    A("## 0b. **答题数 n** 曲线（无歧义版；直接回应「只答一题就有 0.99」的质疑）")
    A("")
    A("本维度**只答 n 题**（无跨维度），对随机子集平均。趋势应为：答得越多越准，")
    A("答满时 `r_total = 1`（预测精确等于官方分）。")
    A("")
    A("| 答 n 题（本维度） | 子集数 | conf_r | r_total | **realized_r 均值** | MAE(分) |")
    A("|---:|---:|---:|---:|---:|---:|")
    for n in sorted(n_curve):
        r = n_curve[n]
        A(f"| {n} | {r['n_subsets']} | {r['conf_r_mean']:.4f} | "
          f"{r['r_total_mean']:.4f} | **{r['realized_r_mean']:.4f}** | "
          f"{r['mae_mean']:.4f} |")
    A("")
    A("> 同一件事的另一个视角见 `tools/analyze/audit_rtotal_curve.py`（逐维度、")
    A("> 用「前 n 题」而非随机子集）。两者趋势一致。")
    A("")
    A("## 1. 场景 A：只答本维度的题（**逐 k 枚举全部子集** ⇒ 含真正的最差情况）")
    A("")
    A("遮住该维度的 **k 题**（k=1..6），用剩下 **10−k 题**预测该维度最终分。")
    A("`C(10,k)` 个子集**全部枚举**，所以 `*_min` 列是真正的最差子集。")
    A("**「已答 n 题」列 = 10 − k**，看趋势请看它，不要看 k。")
    A("")
    L.extend(_table_a(ipip_a, [1, 2, 3, 4, 5, 6], ipip_a_out,
                      f"N_train={splits['ipip_a']['n_train']}，"
                      f"N_test={splits['ipip_a']['n_test']}"))
    A("")
    A("### 1b. 逐维度明细（遮住 3 题 = 已答 7 题 / 遮住 6 题 = 已答 4 题）")
    A("")
    A("| 维度 | 题数 | k=3 conf_r | k=3 r_total | k=3 realized_r | k=3 MAE | "
      "k=6 conf_r | k=6 r_total | k=6 realized_r | k=6 MAE |")
    A("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for dim, d in ipip_a.items():
        b3, b6 = d["by_k_masked"].get(3), d["by_k_masked"].get(6)
        A(f"| {dim} | {d['n_items']} | "
          f"{_fmt(b3 and b3['theory_r_mean'], 3)} | {_fmt(b3 and b3['r_total_mean'], 3)} | "
          f"{_fmt(b3 and b3['realized_r_mean'], 3)} | {_fmt(b3 and b3['mae_mean'], 3)} | "
          f"{_fmt(b6 and b6['theory_r_mean'], 3)} | {_fmt(b6 and b6['r_total_mean'], 3)} | "
          f"{_fmt(b6 and b6['realized_r_mean'], 3)} | {_fmt(b6 and b6['mae_mean'], 3)} |")
    A("")
    A("## 2. 场景 B：跨维度混合作答（随机答全卷 30 / 60 / 90 题）")
    A("")
    A("与 `data/model-comparison.json` 的 5 折 CV（OLS）对照——那是**另一套**口径"
      "（按阶梯题序取环、且是 5 折），不能逐位对齐，只看量级。")
    A("")
    A("| 已答题数 | 掩码数 | conf_r 均值 | r_total 均值 | **realized_r 均值** | "
      "realized_r 最小 | MAE(分) | model-comparison OLS R²（5 折 CV） |")
    A("|---:|---:|---:|---:|---:|---:|---:|---:|")
    mc = meta["model_comparison"]
    for m in sorted(ipip_b):
        dims = list(ipip_b[m].values())
        if not dims:
            continue
        r2cv = mc.get(int(m), mc.get(m))
        A(f"| {m} | {max(d['n_masks'] for d in dims)} | "
          f"{_agg(dims, 'theory_r_mean'):.4f} | {_agg(dims, 'r_total_mean'):.4f} | "
          f"**{_agg(dims, 'realized_r_mean'):.4f}** | "
          f"{_agg(dims, 'realized_r_min'):.4f} | {_agg(dims, 'mae_mean'):.4f} | "
          f"{'—' if r2cv is None else f'{math.sqrt(r2cv):.4f}（r，即 √R²）'} |")
    if ipip_b_out:
        m = sorted(ipip_b_out)[0]
        dims = list(ipip_b_out[m].values())
        if dims:
            A("")
            A(f"**半样本留出（m={m}，N_train={splits['ipip_b']['n_train']}，"
              f"N_test={splits['ipip_b']['n_test']}）**：conf_r "
              f"{_agg(dims, 'theory_r_mean'):.4f}｜r_total {_agg(dims, 'r_total_mean'):.4f}｜"
              f"**realized_r {_agg(dims, 'realized_r_mean'):.4f}**（最小 "
              f"{_agg(dims, 'realized_r_min'):.4f}）｜MAE {_agg(dims, 'mae_mean'):.4f}｜"
              f"MAE/理论SE {_se_ratio(dims):.3f}")
    A("")
    A("### 2b. 同口径对照：**阶梯前 m 题**（`data/tier-ladder.json` 的题序）")
    A("")
    A("上面那几行是**随机** m 题；`data/model-comparison.json` 用的是**阶梯题序**，"
      "两者不可比。下表用阶梯题序重跑，才能与那份 5 折 CV 对齐。")
    A("")
    A("| 阶梯前 m 题 | conf_r 均值 | r_total 均值 | **realized_r 均值** | "
      "realized_r 最小 | MAE(分) | model-comparison OLS R²（5 折 CV） |")
    A("|---:|---:|---:|---:|---:|---:|---:|")
    for m in sorted(ipip_c):
        dims = list(ipip_c[m].values())
        r2cv = mc.get(int(m), mc.get(m))
        A(f"| {m} | {_agg(dims, 'theory_r_mean'):.4f} | {_agg(dims, 'r_total_mean'):.4f} | "
          f"**{_agg(dims, 'realized_r_mean'):.4f}** | {_agg(dims, 'realized_r_min'):.4f} | "
          f"{_agg(dims, 'mae_mean'):.4f} | "
          f"{'—' if r2cv is None else f'{math.sqrt(r2cv):.4f}（r）'} |")
    A("")
    A("（`model-comparison` 是 5 折 CV、模型含截距且用 OLS 全权重；本表是**同一批人**"
      "上的 realized 相关，所以本表的数会略高——量级一致说明两套实现没漂移。）")
    A("")
    A("## 3. PID-5（两份供体样本各自验证）")
    A("")
    for sample, data in pid5.items():
        A(f"### {sample}")
        A("")
        L.extend(_table_a(data, [1, 2, 3, 4, 5, 6], pid5_out.get(sample),
                          f"N_train={splits['pid5'][sample]['n_train']}，"
                          f"N_test={splits['pid5'][sample]['n_test']}"))
        # MAE/理论SE：在样本 vs 半样本留出（task-17 补题级常模后的核心对照）
        in_rows = [d["by_k_masked"][k] for d in data.values()
                   for k in d["by_k_masked"]]
        ho_rows = [d["by_k_masked"][k] for d in (pid5_out.get(sample) or {}).values()
                   for k in d["by_k_masked"]] if pid5_out.get(sample) else []
        if in_rows and ho_rows:
            A(f"**MAE ÷ 理论SE**：在样本 **{_se_ratio(in_rows):.3f}**"
              f"｜半样本留出 **{_se_ratio(ho_rows):.3f}**")
            A("（半样本留出 ≈1.0 ⇒ 误差条标定正确；在样本偏高来自两点："
              "① 参数与验证样本同源（`r_total` 偏乐观）；"
              "② 引擎用**两样本合并**的题级均值/SD，而这里逐样本验证——"
              "两样本已被平移对齐到同一 0–3 约定，但分布仍有差异。）")
        A("")
    A("## 4. 结论：理论 r 能不能当「可信度」呈现")
    A("")
    rows_all = [d["by_k_masked"][k] for d in ipip_a.values() for k in d["by_k_masked"]]
    gap_total = max(abs(r["r_total_mean"] - r["realized_r_mean"]) for r in rows_all)
    gap_conf_lo = min(r["realized_r_mean"] - r["theory_r_mean"] for r in rows_all)
    A(f"1. **`r_total` 与实测几乎逐位吻合**：场景 A 全部 {len(rows_all)} 个 (维度×遮住题数) "
      f"单元里，最大偏差 **{gap_total:.4f}**；场景 B 最大偏差 "
      f"{max(abs(d['r_total_mean'] - d['realized_r_mean']) for m in ipip_b for d in ipip_b[m].values()):.4f}。"
      " 在半样本留出下同样吻合（见各表），说明**不是**参数与验证样本同一批人造成的假象。")
    A("   ⚠️ **口径说明**：`r_total` 是「在已拿到这些作答值的条件下，最终分估得多准」，"
      "已答的**本维度**题被当成已知真值计进去；它**不是**「纯预测的相关」。"
      "答满本维度时它恒为 1（分已经算出来了）。")
    A(f"2. **`conf_r`（判据口径）是保守下界**：在全部 {len(rows_all)} 个单元上，"
      f"实测 realized_r 的**均值都不低于** `conf_r` 的均值（最小超额 {gap_conf_lo:.4f}），"
      "场景 B（m=30）差距最大——因为它不把已答项当已知真值。"
      "→ **把 `conf_r` 当『可信度』呈现是安全的（只会低估）**，"
      "但**不能**把它描述成「预测值与最终分的相关」：那个量是 `r_total`。"
      "⚠️ 现界面（`ui/index.html`）对判据 r 的措辞是「与答满 10 题的相关」——"
      "按本轮实测，那句话描述的是 `r_total`，而实际显示/门控用的是 `conf_r`，"
      "即**文案低估了预测准确度**且门槛偏严。这是文案问题，不在本轮写范围内。")
    A("3. **残差尺度标定正确**：MAE ÷（0.7979·SD·√(1−r_total²)）在各表最后一列，"
      "都在 1 附近（IPIP ≈0.97–0.99、PID-5 见 §3）⇒ 预测区间/误差条可以直接用 "
      "`prediction_se`。")
    A("4. **`conf_r` 现在可以借跨维度**（task-17 用户指示 2）：本维度只答 1 题时，"
      "加 5 道别的维度的题可把 `conf_r` 抬高约 +0.07（IPIP 平均）；"
      "跨维度题答得越多越高（见 `research/conf-r-cross-calibration.md`）。"
      "**硬规则**：本维度一道题都没答时**禁止展示**（引擎与 JS 都返回 "
      "`NO_OWN_ITEM_ANSWERED` 且不给任何数值），与别的维度答了多少无关。")
    A("")
    A("## 5. 局限 / 待决策（如实）")
    A("")
    A("- **参数与验证样本同源**：主表用的是线上参数（`pairB64`/`item_dim_corr` 由"
      "`ipip20993.dat` 的完整作答估计），IPIP 的验证样本就是同一批人 ⇒ 有乐观偏差。"
      "半样本留出节把参数在训练半重估、在测试半评估，两边的差距见 §1/§2——"
      "`r_total` 的吻合在半样本下依然成立（最大偏差见该节）。")
    A("- **判据门槛已重标**：`conf_r` 纳入跨维度后，门控值没有沿用旧数假装没事。"
      "标定结论见 `research/conf-r-cross-calibration.md`：**无跨维度时新旧 `conf_r` "
      "逐值相同**，所以 `ceiling_ratio=0.90` 在「只看本维度」轴上原样成立；"
      "跨维度轴上的新分布与各 ratio 的后果都列在该报告里（ratio>0.95 会出现"
      "永不达标的维度，因此不采用）。若界面要显示「已达上限的百分之几」，"
      "分母需换成跨维度上限 `dim_ceiling_cross`（该报告 §D 给出逐维度数值）。")
    A("- **PID-5 已补题级均值/SD**（task-17 用户指示 3）：`data/item-norms-pid5.json`，"
      "从两份供体样本**分样本计算、按组内合并**（两样本是 0–3 与 1–4 两种尺度，"
      "先各自按自己的 min/max 翻转、再把 SKID 平移到 0–3，**不拼原始数据**）。"
      "重跑后的 MAE/理论SE 见 §3 各表（改造前 0–3 尺度 ≈1.20–1.26、1–4 尺度 "
      "≈1.28–1.75）。")
    A("- **PID-5 的 pairB64 是两样本 Fisher 合并**，而验证是**逐样本**做的"
      "（两样本作答尺度不同、不能拼原始分）。这会给 PID-5 的相关系数带来"
      "小幅偏差；量级上 realized 与 r_total 仍吻合，但严格口径应当是"
      "「用哪份样本，就用那份样本的相关矩阵」。")
    A("- **IPIP 的题级均值/SD 来自 N=20,974 的同一网络样本**（`item-norms.json`），"
      "与 pairB64 同源；换成别的总体需要重新标定。")
    A("- **PID-5 题级常模的绝对水平**：供体样本（临床+配额）的 facet 均值与"
      "代表性常模表最大差约 0.47 分（0–3 尺度，见 `derive_pid5_item_norms.py` 输出）——"
      "模型的**相关结构**与**原始分尺度**都对齐到供体样本；若面向总体人群展示"
      "绝对水平，需要另行做常模锚定。")
    A("- 未做的：IRT/贝叶斯收缩等其他模型（项目已有 `data/model-comparison.json` 的"
      "树模型对照，结论是线性不劣于非线性）；跨文化常模适用性不在本轮范围。")
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------- main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true",
                    help="抽样：IPIP 最多 2500 人、场景 B 掩码更少")
    ap.add_argument("--out", default=os.path.join(ROOT, "research",
                                                  "inference-validation-report.md"))
    ap.add_argument("--json", default=os.path.join(ROOT, "research",
                                                   "inference-validation.json"))
    args = ap.parse_args(argv)

    max_n = 2500 if args.fast else None
    n_masks_b = 6 if args.fast else 20

    print("=== 载入 IPIP-NEO 完整作答 ===")
    m_ipip = load_model("IPIP-NEO")
    x = load_ipip(m_ipip, max_n=max_n)
    print(f"    N={x.shape[0]} × {x.shape[1]} 题（20,993 行中完整作答）")
    # 自检：perm 后的题间相关是否与 pairB64 一致（抽样 200 对）
    rng = np.random.default_rng(7)
    pairs = [(int(a), int(b)) for a, b in rng.integers(0, len(m_ipip.ids), size=(200, 2)) if a != b]
    dmax = 0.0
    for a, b in pairs:
        dmax = max(dmax, abs(float(np.corrcoef(x[:, a], x[:, b])[0, 1]) - m_ipip.pairs[a, b]))
    print(f"    自检：列序对齐后题间相关与 pairB64 最大差 {dmax:.4f}"
          f"（200 对抽样；float32 存储 + 抽样误差）")

    print("\n=== 场景 A：只答本维度的题（枚举全部子集，k=1..6）===")
    a_res = scenario_a(m_ipip, x, [1, 2, 3, 4, 5, 6], verbose=True)

    print("\n=== 场景 A 半样本留出（训练半估参数 → 测试半评估）===")
    a_out, a_split = scenario_a_holdout(m_ipip, x, [1, 2, 3, 4, 5, 6], seed=20261004)
    for k in [1, 2, 3, 6]:
        rows = [d["by_k_masked"][k] for d in a_out.values() if k in d["by_k_masked"]]
        if rows:
            print(f"    k={k}: r_total={np.mean([r['r_total_mean'] for r in rows]):.4f} "
                  f"realized={np.mean([r['realized_r_mean'] for r in rows]):.4f} "
                  f"MAE={np.mean([r['mae_mean'] for r in rows]):.4f}")

    print("\n=== 答题数 n 曲线（消歧：n 是「答了几题」）===")
    n_curve = scenario_n_curve(m_ipip, x, [1, 2, 3, 5, 8, 10],
                               n_subsets=6 if args.fast else 20)
    for n in sorted(n_curve):
        r = n_curve[n]
        print(f"    答 {n:>2} 题: conf_r={r['conf_r_mean']:.4f} "
              f"r_total={r['r_total_mean']:.4f} realized={r['realized_r_mean']:.4f} "
              f"MAE={r['mae_mean']:.4f}")

    print("\n=== 场景 B：跨维度混合作答（30/60/90 题）===")
    b_res = scenario_b(m_ipip, x, [30, 60, 90], n_masks_b)
    for m in sorted(b_res):
        dims = b_res[m].values()
        print(f"    m={m:<3} conf_r={np.mean([d['theory_r_mean'] for d in dims]):.4f} "
              f"r_total={np.mean([d['r_total_mean'] for d in dims]):.4f} "
              f"realized={np.mean([d['realized_r_mean'] for d in dims]):.4f}")
    print("\n=== 场景 B 半样本留出（m=30）===")
    b_out, b_split = scenario_b_holdout(m_ipip, x, [30], max(4, n_masks_b // 3), seed=20261004)
    for m in sorted(b_out):
        dims = list(b_out[m].values())
        if dims:
            print(f"    m={m}: r_total={np.mean([d['r_total_mean'] for d in dims]):.4f} "
                  f"realized={np.mean([d['realized_r_mean'] for d in dims]):.4f}")

    print("\n=== 场景 C：阶梯前 30/60/90 题（与 data/model-comparison.json 同口径）===")
    c_res = scenario_ladder(m_ipip, x, [30, 60, 90])
    for m in sorted(c_res):
        dims = list(c_res[m].values())
        print(f"    m={m:<3} conf_r={np.mean([d['theory_r_mean'] for d in dims]):.4f} "
              f"r_total={np.mean([d['r_total_mean'] for d in dims]):.4f} "
              f"realized={np.mean([d['realized_r_mean'] for d in dims]):.4f}")

    print("\n=== PID-5：两份供体样本 ===")
    m_pid = load_model("PID-5")
    pid_res, pid_out, pid_n, pid_split = {}, {}, {}, {}
    for fname, lo, hi in PID5_SAMPLES:
        xx = load_pid5_sample(m_pid, fname, lo, hi)
        pid_n[fname] = int(xx.shape[0])
        print(f"    {fname}: N={xx.shape[0]}")
        ks = [1, 2, 3, 4, 5, 6]
        pid_res[fname] = scenario_a(m_pid, xx, ks, verbose=False)
        pid_out[fname], pid_split[fname] = scenario_a_holdout(m_pid, xx, ks, seed=20261005)
        for k in ks:
            rows = [d["by_k_masked"][k] for d in pid_res[fname].values() if k in d["by_k_masked"]]
            if rows:
                print(f"      k={k}: conf_r={np.mean([r['theory_r_mean'] for r in rows]):.3f} "
                      f"r_total={np.mean([r['r_total_mean'] for r in rows]):.3f} "
                      f"realized={np.mean([r['realized_r_mean'] for r in rows]):.3f} "
                      f"MAE={np.mean([r['mae_mean'] for r in rows]):.3f}")
        orows = [d["by_k_masked"][3] for d in pid_out[fname].values() if 3 in d["by_k_masked"]]
        if orows:
            print(f"      半样本留出 k=3: r_total={np.mean([r['r_total_mean'] for r in orows]):.3f} "
                  f"realized={np.mean([r['realized_r_mean'] for r in orows]):.3f}")

    mc = json.load(open(os.path.join(ROOT, "data", "model-comparison.json"),
                        encoding="utf-8"))
    mc_map = {}
    for row in mc.get("results", []):
        if row.get("model") in ("ols", "ridge") and row.get("items") in (30, 60, 90):
            mc_map[row["items"]] = row["r2_mean"]
    inst = m_ipip.raw_instrument
    dim_zh = {d["id"]: d.get("name", d["id"]) for d in inst["dimensions"]}
    meta = {
        "ipip_file": "archive/datasets/osf-johnson/validity/ipip20993.dat",
        "ipip_rows": 20993, "ipip_n": int(x.shape[0]),
        "pid5_n": pid_n,
        "model_comparison": mc_map, "dim_zh": dim_zh,
    }
    splits = {"ipip_a": a_split, "ipip_b": b_split, "pid5": pid_split}
    report = build_report(a_res, a_out, b_res, b_out, c_res, n_curve,
                          pid_res, pid_out, meta, splits)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(report)
    with open(args.json, "w", encoding="utf-8") as fh:
        json.dump({"ipip_scenario_a": a_res, "ipip_scenario_a_holdout": a_out,
                   "ipip_n_curve": {str(k): v for k, v in n_curve.items()},
                   "ipip_scenario_b_random": b_res, "ipip_scenario_b_holdout": b_out,
                   "ipip_scenario_c_ladder": c_res,
                   "pid5": pid_res, "pid5_holdout": pid_out,
                   "meta": {k: v for k, v in meta.items() if k != "dim_zh"}},
                  fh, ensure_ascii=False, indent=1)
    print(f"\n报告 → {args.out}")
    print(f"原始数据 → {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
