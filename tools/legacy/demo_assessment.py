#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""端到端演示：从 Johnson (2005) 真实样本里挑出不同作答风格的个体，
让测评引擎逐个跑一遍，看质量门能否正确区分。

**为什么用真实数据而不是编造**：
  编造的"粗心作答者"是按我们对粗心的想象生成的，会掩盖引擎的真实表现。
  真实样本里有天然的作答风格差异，且带有人家算好的 RNDSPLIT / RNDCORR 作为对照。

演示对象：
  1. 高质量作答者    —— RNDSPLIT 与 RNDCORR 都处于高分位
  2. 粗心作答者      —— 两项都处于低分位
  3. 直线作答者      —— longstring 极长（在原始作答口径下）
  4. 只答单个 facet  —— 展示引擎如何诚实报告"反义题指标无法计算"
"""
from __future__ import annotations

import json
import os
import sys
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
sys.path.insert(0, ROOT)

from engine.assess import Reference, assess  # noqa: E402

DATA = os.path.join(ROOT, "archive/datasets/osf-johnson/validity/ipip20993.dat")
SEP = "=" * 78


def load_frame():
    df = pd.read_csv(DATA, sep="\t", dtype=str, keep_default_na=False)
    ic = [f"I{i}" for i in range(1, 301)]
    items = (df[ic].replace({"": np.nan, " ": np.nan, "0": np.nan})
             .apply(pd.to_numeric, errors="coerce").to_numpy(float))
    meta = (df[["RNDSPLIT", "RNDCORR"]].replace({"": np.nan, " ": np.nan})
            .apply(pd.to_numeric, errors="coerce").to_numpy(float))
    return df, items, meta


def pick(df, items, meta):
    """挑出四类演示对象。"""
    complete = ~np.isnan(items).any(axis=1)
    rs, rc = meta[:, 0], meta[:, 1]
    idx = np.arange(items.shape[0])

    # 1. 高质量：两项都在 p75 以上
    q = idx[complete & (rs >= np.nanpercentile(rs, 75)) & (rc >= np.nanpercentile(rc, 75))]
    good = int(q[0])

    # 2. 粗心：两项都在 p5 以下
    c = idx[complete & (rs <= np.nanpercentile(rs, 5)) & (rc <= np.nanpercentile(rc, 5))]
    bad = int(c[0]) if len(c) else int(idx[complete][np.argmin(rs[complete] + rc[complete])])

    # 3. 直线：原始口径下 longstring 最长
    ref = Reference()
    def longest(row):
        raw = row.copy()
        rev = np.array([ref.by_order[n]["key"] < 0 for n in range(1, 301)])
        raw[rev] = 6 - raw[rev]
        best = cur = 1
        for j in range(1, 300):
            cur = cur + 1 if raw[j] == raw[j - 1] else 1
            best = max(best, cur)
        return best
    ls = np.array([longest(items[i]) for i in idx[complete]])
    straight = int(idx[complete][int(np.argmax(ls))])

    # 4. 只答单个 facet 的（取第 1 位）
    facet_only = good
    return good, bad, straight, int(ls.max()), facet_only


def responses_of(row: np.ndarray, ref: Reference, only_facet: str | None = None) -> dict:
    out = {}
    for n in range(1, 301):
        it = ref.by_order[n]
        if only_facet and it["facet"] != only_facet:
            continue
        v = row[n - 1]
        if not np.isnan(v):
            out[it["id"]] = int(v)
    return out


def show(title: str, meta_row, result: dict) -> None:
    print(f"\n{SEP}\n{title}\n{SEP}")
    print(f"参照（数据自带）：RNDSPLIT={meta_row[0]:.3f}  RNDCORR={meta_row[1]:.3f}")
    q = result["quality_gate"]
    print(f"\n[质量门]")
    print(f"  完整度    : 答 {q['completeness']['answered']} / 预期 {q['completeness']['expected']}")
    ls = q["longstring"]
    if ls.get("value") is None:
        print(f"  longstring: 无法计算 — {ls['blocker']}")
    else:
        print(f"  longstring: {ls['value']}  （参照 p95={ls['p95_reference']} / "
              f"p99={ls['p99_reference']}，{ls['consecutive_pairs']} 个相邻题对）")
    an = q["antonyms"]
    if an.get("value") is None:
        print(f"  反义题    : 无法计算 — {an['blocker']}")
    else:
        print(f"  反义题    : {an['value']:+.3f}（{an['n_pairs']} 对，参照 p5={an['p5_reference']}）")
    print(f"  折扣      : {q['reliability_discount']}")
    for f in q["flags"]:
        print(f"  🚩 {f}")
    for n_ in q["notes"]:
        print(f"  ℹ️  {n_}")

    s = result["score"]
    print(f"\n[计分]")
    if s.get("status") != "OK":
        print(f"  状态：{s['status']} — {s.get('blocker')}")
    else:
        band = s["band"] or "**不落在任何已发布带内**"
        print(f"  原始分 {s['raw_score']} / {s['possible_range']}  →  {band}")
        print(f"  α={s['cronbach_alpha']}  SD(由带反推)={s['sd_from_bands']}  SEM={s['sem']}  "
              f"95%CI={s['ci95']}")
    print(f"\n[解读]\n{result['interpretation'].get('narrative') or result['interpretation']}")


def main() -> int:
    warnings.filterwarnings("ignore")
    ref = Reference()
    df, items, meta = load_frame()
    good, bad, straight, maxls, facet_only = pick(df, items, meta)

    print(f"从 {items.shape[0]} 条真实记录中选出四类演示对象")
    print(f"  高质量 #{good}   粗心 #{bad}   直线 #{straight}（longstring={maxls}）")

    show("① 高质量作答者", meta[good], assess("anxiety", responses_of(items[good], ref), ref))
    show("② 粗心作答者", meta[bad], assess("anxiety", responses_of(items[bad], ref), ref))
    show("③ 直线作答者", meta[straight],
         assess("anxiety", responses_of(items[straight], ref), ref))

    # ④ 只答焦虑 facet 的 10 题
    sub = responses_of(items[good], ref, only_facet="anxiety")
    show("④ 只答焦虑 facet（10 题）", meta[good], assess("anxiety", sub, ref))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
