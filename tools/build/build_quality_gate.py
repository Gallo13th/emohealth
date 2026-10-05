#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""质量门：用 Johnson (2005) 的 20,993 人网络样本标定作答质量指标。

数据来源：`archive/datasets/osf-johnson/validity/ipip20993.dat`
  - 339 个制表符分隔字段：SEX, AGE, I1..I300, 30 个 facet 分, 5 个维度分, RNDSPLIT, RNDCORR
  - 该样本为**网络施测**，正是我们产品面对的作答环境

本脚本做三件事：

1. **独立验证规范数据集**：用「I_n 对应第 n 道施测题」的假设，
   核对 300 个 facet 总分是否与数据自带的分值一致。若吻合，则
   `data/ipip-neo-300.json` 的施测顺序与 facet 归属得到外部数据验证。

2. **计算作答质量指标**：
   - `longstring_raw`：最长连续相同**原始作答**（必须先把反向题还原！）
   - `longstring_recoded`：最长连续相同**已重编码值**（错误做法，仅作对照）
   - `evenodd_r`：facet 内奇偶题相关（一致性指标）
   - 直接取用数据自带的 `RNDSPLIT`（Jackson 分半信度）与 `RNDCORR`（Goldberg 心理测量反义题）

3. **输出分位数**，供产品决定阈值。**不预设切分点**——`PLAN.md` §2.5：
   文献共识是多指标筛查 + 概率化降权，避免单一任意切分点。

⚠️ 关键陷阱（codebook 明确警告）：反向题在施测时**已被重编码**。因此
"统计连续相同作答次数"必须先还原为原始作答类别，否则反向题会被误判为
与相邻正向题一致，longstring 被系统性高估。本脚本同时输出两种口径以便对照。

输出：`data/quality-gate-calibration.json`
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
DATA = os.path.join(ROOT, "archive/datasets/osf-johnson/validity/ipip20993.dat")
CANON = os.path.join(ROOT, "data/ipip-neo-300.json")
OUT = os.path.join(ROOT, "data/quality-gate-calibration.json")

FACET_COL_NAMES = [
    "ANXIETY", "FRIENDLI", "IMAGINAT", "TRUST", "SELFEFFI", "ANGER", "GREGAR",
    "ARTISTIC", "MORALITY", "ORDER", "DEPRESS", "ASSERTIV", "EMOTION", "ALTRUISM",
    "DUTIFUL", "SELFCONS", "ACTIVITY", "ADVENTUR", "COOPERAT", "ACHIEVE",
    "IMMODERA", "EXCITE", "INTELLEC", "MODESTY", "SELFDISC", "VULNERAB",
    "CHEERFUL", "LIBERAL", "SYMPATHY", "CAUTIOUS",
]


def load():
    """返回 (items, age, sex, rndsplit, rndcorr, facet_ref)。

    items 形状 (N, 300)，取值 1–5，缺失（原文件编码为 0 或空白）转为 NaN。
    """
    import pandas as pd

    df = pd.read_csv(DATA, sep="\t", dtype=str, keep_default_na=False)
    item_cols = [f"I{i}" for i in range(1, 301)]
    items = (df[item_cols]
             .replace({"": np.nan, " ": np.nan, "0": np.nan})
             .apply(pd.to_numeric, errors="coerce")
             .to_numpy(dtype=np.float64))
    meta = (df[["AGE", "SEX", "RNDSPLIT", "RNDCORR"]]
            .replace({"": np.nan, " ": np.nan})
            .apply(pd.to_numeric, errors="coerce")
            .to_numpy(dtype=np.float64))
    facet_ref = (df[FACET_COL_NAMES]
                 .replace({"": np.nan, " ": np.nan})
                 .apply(pd.to_numeric, errors="coerce")
                 .to_numpy(dtype=np.float64))
    return items, meta[:, 0], meta[:, 1], meta[:, 2], meta[:, 3], facet_ref


def main() -> int:
    canon = json.load(open(CANON, encoding="utf-8"))
    by_order = {i["order"]: i for i in canon["items"]}
    keys = np.array([by_order[n]["key"] for n in range(1, 301)], dtype=np.float64)
    item_ids = [by_order[n]["id"] for n in range(1, 301)]

    log: list[str] = []
    items, age, sex, rndsplit, rndcorr, facet_ref = load()
    n = items.shape[0]
    log.append(f"载入 {n} 条记录 × {items.shape[1]} 题")

    # ---------- 1. 独立验证规范数据集 ----------
    facet_of_item = np.array([
        FACET_COL_NAMES.index(_abbrev(by_order[o]["facet"]))
        for o in range(1, 301)
    ])
    complete = ~np.isnan(items).any(axis=1) & ~np.isnan(facet_ref).any(axis=1)
    recomputed = np.zeros((n, 30))
    for f in range(30):
        recomputed[:, f] = np.nansum(items[:, facet_of_item == f], axis=1)
    dev = np.abs(recomputed[complete] - facet_ref[complete])
    max_dev = float(np.nanmax(dev)) if dev.size else float("nan")
    exact = int((dev < 1e-6).all(axis=1).sum())
    n_complete = int(complete.sum())
    missing_items = int(np.isnan(items).sum())
    log.append(f"缺失题值（原文件 0/空白）共 {missing_items} 个，涉及 "
               f"{int((np.isnan(items).any(axis=1)).sum())} 条记录")
    log.append(f"独立验证：facet 总分重算 vs 数据自带 —— 最大偏差 {max_dev:.0f}，"
               f"完全一致记录数 {exact}/{n_complete}（完整记录）")

    # ---------- 2. 还原原始作答（关键） ----------
    raw_resp = items.copy()
    rev = keys < 0
    raw_resp[:, rev] = 6.0 - raw_resp[:, rev]   # 已重编码 -> 还原为 1..5 原始类别

    # ---------- 3. 指标 ----------
    def max_run(arr: np.ndarray) -> np.ndarray:
        """每题最长连续相同值的长度。"""
        n_, m_ = arr.shape
        best = np.ones(n_, dtype=np.int32)
        cur = np.ones(n_, dtype=np.int32)
        for j in range(1, m_):
            same = arr[:, j] == arr[:, j - 1]
            cur = np.where(same, cur + 1, 1)
            best = np.maximum(best, cur)
        return best

    ls_raw = max_run(raw_resp)
    ls_recoded = max_run(items)

    # --- even-odd 一致性 ---
    # 逐 facet 内按奇偶题拆半，算每人的组内相关，再对 30 个 facet 做 Fisher-z 平均。
    # 只在**该 facet 内无缺失**的记录上计算；5 对题的相关系数噪声大，
    # 必须做 z 变换再平均，直接平均 r 会有偏。
    def zavg_evenodd(cols: np.ndarray) -> np.ndarray:
        odd, even = cols[0::2], cols[1::2]
        a, b = items[:, odd], items[:, even]
        ok = ~(np.isnan(a).any(axis=1) | np.isnan(b).any(axis=1))
        out = np.full(n, np.nan)
        if ok.sum() < 2:
            return out
        am = a[ok] - a[ok].mean(axis=1, keepdims=True)
        bm = b[ok] - b[ok].mean(axis=1, keepdims=True)
        num = (am * bm).sum(axis=1)
        den = np.sqrt((am ** 2).sum(axis=1) * (bm ** 2).sum(axis=1))
        with np.errstate(invalid="ignore", divide="ignore"):
            r = np.where(den > 0, num / den, np.nan)
        r = np.clip(r, -0.999, 0.999)
        out[ok] = np.arctanh(r)
        return out

    zs = np.vstack([zavg_evenodd(np.where(facet_of_item == f)[0]) for f in range(30)]).T
    eo_z = np.nanmean(zs, axis=1)
    eo_valid = (~np.isnan(eo_z)).sum()
    eo = np.tanh(eo_z)

    log.append(f"even-odd（facet 内）可计算记录数：{eo_valid}/{n}")

    # --- 实现正确性的独立检验 + 噪声分析 ---
    # 群体层面：把每个 facet 的奇偶两半各自求和，在**人群中**求相关（≈分半信度）。
    # 若该值接近数据自带的 RNDSPLIT，说明我们的奇偶切分方式是对的。
    cplt0 = ~np.isnan(items).any(axis=1)
    Xc = items[cplt0]
    half_r, half_sb = [], []
    for f in range(30):
        cols = np.where(facet_of_item == f)[0]
        a = Xc[:, cols[0::2]].sum(axis=1)
        b = Xc[:, cols[1::2]].sum(axis=1)
        rr = float(np.corrcoef(a, b)[0, 1])
        half_r.append(rr)
        half_sb.append(2 * rr / (1 + rr))          # Spearman-Brown
    half_r = np.array(half_r)
    half_sb = np.array(half_sb)
    log.append(f"群体层面 facet 分半相关：均值 {half_r.mean():.3f}，"
               f"SB 校正后 {half_sb.mean():.3f}（对照 RNDSPLIT 均值 {np.nanmean(rndsplit):.3f}）")

    # 逐人相关的噪声底：n 对题时相关系数的标准误 ≈ 1/sqrt(n-1)
    n_pairs = 5
    noise_se = 1.0 / np.sqrt(n_pairs - 1)
    log.append(f"逐人 even-odd 的噪声底：{n_pairs} 对题 → r 的标准误 ≈ {noise_se:.2f}；"
               f"而实测 sd 仅 {np.nanstd(eo):.3f} → 信号被噪声淹没")

    # 整卷 even-odd（150 vs 150），仅完整记录
    whole = np.full(n, np.nan)
    cplt = ~np.isnan(items).any(axis=1)
    log.append(f"even-odd（整卷）可计算记录数：{int(cplt.sum())}/{n}")
    a_all, b_all = items[cplt][:, 0::2], items[cplt][:, 1::2]
    am = a_all - a_all.mean(axis=1, keepdims=True)
    bm = b_all - b_all.mean(axis=1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        whole[cplt] = ((am * bm).sum(axis=1) /
                       np.sqrt((am ** 2).sum(axis=1) * (bm ** 2).sum(axis=1)))

    def q(a: np.ndarray, name: str) -> dict:
        a = a[~np.isnan(a)]
        return {
            "name": name, "n": int(a.size),
            "mean": round(float(a.mean()), 4), "sd": round(float(a.std()), 4),
            "min": round(float(a.min()), 4), "max": round(float(a.max()), 4),
            "pct": {str(p): round(float(np.percentile(a, p)), 4)
                    for p in [0.5, 1, 2, 5, 10, 25, 50, 75, 90, 95, 99]},
        }

    stats = [
        q(ls_raw.astype(float), "longstring_raw（还原后的原始作答）"),
        q(ls_recoded.astype(float), "longstring_recoded（未还原，错误口径）"),
        q(eo, "evenodd_facet（facet 内奇偶，Fisher-z 平均后转回 r）"),
        q(whole, "evenodd_whole（整卷 150v150，仅完整记录）"),
        q(rndsplit, "RNDSPLIT（Jackson 分半信度，数据自带）"),
        q(rndcorr, "RNDCORR（Goldberg 心理测量反义题，数据自带）"),
        q(age, "AGE"),
    ]

    # 指标间相关（判断是否冗余）
    pairs = {
        "longstring_raw~rndsplit": (ls_raw, rndsplit),
        "longstring_raw~rndcorr": (ls_raw, rndcorr),
        "rndsplit~rndcorr": (rndsplit, rndcorr),
        "evenodd_facet~rndsplit": (eo, rndsplit),
        "evenodd_facet~rndcorr": (eo, rndcorr),
        "evenodd_whole~rndsplit": (whole, rndsplit),
        "evenodd_whole~rndcorr": (whole, rndcorr),
    }
    corr = {}
    for k, (a, b) in pairs.items():
        m = ~(np.isnan(a) | np.isnan(b))
        corr[k] = round(float(np.corrcoef(a[m], b[m])[0, 1]), 4)

    payload = {
        "source": "Johnson, J. A. (2005). Ascertaining the validity of individual protocols "
                  "from Web-based personality inventories. JRP, 39, 103-129.",
        "data_file": "archive/datasets/osf-johnson/validity/ipip20993.dat",
        "sample": {"n": int(n), "setting": "web-administered", "items": 300},
        "validation": {
            "method": "用『I_n = 第 n 道施测题』假设重算 30 个 facet 总分，与数据自带分值比对",
            "max_absolute_deviation": float(max_dev),
            "records_exactly_matching": exact,
            "conclusion": "规范数据集（data/ipip-neo-300.json）的施测顺序与 facet 归属"
                          "在外部数据上得到验证" if max_dev == 0 else "存在偏差，需排查",
        },
        "critical_note": "反向题在施测时已被重编码（见 codebook）。计算连续相同作答必须先还原，"
                         "否则 longstring 被系统性高估。本表同时给出两种口径。",
        "statistics": stats,
        "inter_index_correlations": corr,
        "recommended_indices": [
            {"name": "RNDCORR", "why": "数据自带，Goldberg 心理测量反义题；20,993 人网络样本分布已知",
             "direction": "高=好", "p5": 0.13, "p50": 0.49},
            {"name": "RNDSPLIT", "why": "数据自带，Jackson 分半信度；分布已知",
             "direction": "高=好", "p5": 0.66, "p50": 0.86},
            {"name": "longstring_raw", "why": "自行计算，须先把反向题还原为原始作答类别",
             "direction": "高=差", "p95": 8, "p99": 10},
        ],
        "ruled_out_indices": [
            {"name": "evenodd_facet（逐人 facet 内奇偶相关）",
             "evidence": "与 RNDSPLIT 相关 +0.067、与 RNDCORR 相关 +0.056 —— 近乎为零",
             "reason": "实现本身正确（群体层面 SB 校正后 0.854，与 RNDSPLIT 0.838 吻合），"
                       "但每 facet 仅 5 对题，逐人 r 的标准误约 0.50，而实测 sd 仅约 0.16，"
                       "**信噪比不足**。用它筛人等于随机筛人。",
             "verdict": "10 题/facet 的量表下不可用"},
            {"name": "evenodd_whole（整卷 150v150 按施测位置奇偶切分）",
             "evidence": "与 RNDSPLIT 相关 -0.268、与 RNDCORR 相关 -0.344（方向还是反的）",
             "reason": "施测顺序是 30-facet 交错循环，因此「奇数位」与「偶数位」落在**不同的 facet 上**，"
                       "两半测的不是同一批构念，相关本身无意义。",
             "verdict": "在交错施测顺序下构造错误"}
        ],
        "open_question": "evenodd_whole 的负相关（-0.27/-0.34）超出上述解释。"
                         "已排除反向题方向与作答水平两个候选混淆源（分别在正向题内、反向题内单独计算仍为负）。"
                         "**记录为未解问题**，不投入使用。",
        "policy_note": "PLAN.md §2.5：不预设单一阈值，采用多指标 + 概率化降权。"
                       "本文件只提供分布，阈值需由产品与验证共同决定。",
        "build_log": log,
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)

    print("\n".join(log))
    print("\n=== 指标分布 ===")
    for s in stats:
        if s["name"] == "AGE":
            continue
        print(f"{s['name']}")
        print(f"   mean={s['mean']}  sd={s['sd']}  min={s['min']}  max={s['max']}")
        print(f"   分位: " + "  ".join(f"p{k}={v}" for k, v in s["pct"].items()))
    print("\n=== 指标间相关 ===")
    for k, v in corr.items():
        print(f"   {k:28} {v:+.3f}")
    print(f"\nwrote {OUT}")
    return 0


def _abbrev(facet: str) -> str:
    """规范数据集的 facet id -> 数据文件的 8 字符列名。"""
    return {
        "anxiety": "ANXIETY", "friendliness": "FRIENDLI", "imagination": "IMAGINAT",
        "trust": "TRUST", "selfefficacy": "SELFEFFI", "anger": "ANGER",
        "gregariousness": "GREGAR",
        "aesthetic_appreciation_artistic_interests": "ARTISTIC",
        "morality": "MORALITY", "orderliness": "ORDER", "depression": "DEPRESS",
        "assertiveness": "ASSERTIV", "emotionality": "EMOTION", "altruism": "ALTRUISM",
        "dutifulness": "DUTIFUL", "selfconsciousness": "SELFCONS",
        "activitylevel": "ACTIVITY", "adventurousness": "ADVENTUR",
        "cooperation": "COOPERAT", "achievementstriving": "ACHIEVE",
        "immoderation": "IMMODERA", "excitementseeking": "EXCITE",
        "intellect": "INTELLEC", "modesty_humility": "MODESTY",
        "selfdiscipline": "SELFDISC", "vulnerability": "VULNERAB",
        "cheerfulness": "CHEERFUL", "liberalism": "LIBERAL",
        "sympathy": "SYMPATHY", "cautiousness": "CAUTIOUS",
    }[facet]


if __name__ == "__main__":
    raise SystemExit(main())
