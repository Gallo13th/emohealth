#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 Johnson (2005) 数据推导「心理测量反义题对」，并验证能否复现 RNDCORR。

背景：IPIP 效度页把「心理测量反义题」（psychometric antonyms）列为四种粗心作答检测法之一。
Johnson 的数据集自带了 `RNDCORR`（Goldberg 算好的结果），但**未给出所用题对**。
若我们要在自建产品里用这个方法，就必须自己推导题对——本脚本做这件事。

方法（对应 IPIP 效度页的描述）：
  1. 在完整作答样本上算题间相关矩阵
  2. 选取**负相关最强**的题对作为反义题对
  3. 逐人计算一致性：把每对题的 (a, b) 转成符号一致的方向，再看该人在全部题对上
     是否呈现稳定的反向关系

验证：把自算指标与数据自带的 RNDCORR 求相关。若高度相关，说明推导正确。
     若不相关，则如实记录为「不可复现」——与 even-odd 的处置一致。

输出：`data/antonym-pairs.json`
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
DATA = os.path.join(ROOT, "archive/datasets/osf-johnson/validity/ipip20993.dat")
CANON = os.path.join(ROOT, "data/ipip-neo-300.json")
OUT = os.path.join(ROOT, "data/antonym-pairs.json")

N_PAIRS = 30          # 取负相关最强的 N 对


def main() -> int:
    canon = json.load(open(CANON, encoding="utf-8"))
    by_order = {i["order"]: i for i in canon["items"]}
    key = np.array([by_order[n]["key"] for n in range(1, 301)], dtype=float)
    facet = np.array([by_order[n]["facet"] for n in range(1, 301)])

    df = pd.read_csv(DATA, sep="\t", dtype=str, keep_default_na=False)
    ic = [f"I{i}" for i in range(1, 301)]
    X = (df[ic].replace({"": np.nan, " ": np.nan, "0": np.nan})
         .apply(pd.to_numeric, errors="coerce").to_numpy(float))
    rndcorr = (df["RNDCORR"].replace({"": np.nan, " ": np.nan})
               .apply(pd.to_numeric, errors="coerce").to_numpy(float))

    cplt = ~np.isnan(X).any(axis=1)
    Xc = X[cplt]
    rc = rndcorr[cplt]
    log = [f"完整记录 {Xc.shape[0]} / 总 {X.shape[0]}"]

    # ---- 1. 题间相关矩阵 ----
    R = np.corrcoef(Xc, rowvar=False)          # 300x300
    log.append(f"题间相关矩阵 {R.shape}，取值范围 {np.nanmin(R):.3f} ~ {np.nanmax(R):.3f}")

    # ---- 2. 取负相关最强的题对 ----
    iu = np.triu_indices(300, k=1)
    rvals = R[iu]
    order = np.argsort(rvals)                  # 升序 -> 最负在前
    pairs = []
    seen = set()
    for idx in order:
        i, j = int(iu[0][idx]), int(iu[1][idx])
        r = float(rvals[idx])
        if r >= 0:
            break
        # 每题只用一次，避免同一题反复出现导致指标被单一题目主导
        if i in seen or j in seen:
            continue
        seen.add(i); seen.add(j)
        pairs.append({
            "a_order": i + 1, "b_order": j + 1,
            "a_id": by_order[i + 1]["id"], "b_id": by_order[j + 1]["id"],
            "a_text": by_order[i + 1]["text"], "b_text": by_order[j + 1]["text"],
            "a_key": int(key[i]), "b_key": int(key[j]),
            "a_facet": facet[i], "b_facet": facet[j],
            "r": round(r, 4),
        })
        if len(pairs) >= N_PAIRS:
            break

    log.append(f"选出 {len(pairs)} 对反义题对；r 范围 "
               f"{pairs[-1]['r']:.3f} ~ {pairs[0]['r']:.3f}")
    same_facet = sum(1 for p in pairs if p["a_facet"] == p["b_facet"])
    log.append(f"其中同一 facet 内的题对：{same_facet}/{len(pairs)}")

    # ---- 3. 逐人指标 ----
    # 每对题先方向对齐：把 (a, b) 转成「高分表示一致」的形式。
    # 一致 = a 高 且 b 低。故 d = z(a) - z(b) 越大越一致。
    A = np.column_stack([Xc[:, p["a_order"] - 1] for p in pairs])
    B = np.column_stack([Xc[:, p["b_order"] - 1] for p in pairs])
    Az = (A - A.mean(0)) / A.std(0)
    Bz = (B - B.mean(0)) / B.std(0)
    D = Az - Bz

    # 三种候选构造，择优（以与 RNDCORR 的相关为准）
    cands = {
        "mean_z_diff": D.mean(axis=1),
        "sign_consistency": (D > 0).mean(axis=1),
        "profile_r": np.array([
            np.corrcoef(A[i], -B[i])[0, 1] if A[i].std() > 0 and B[i].std() > 0 else np.nan
            for i in range(A.shape[0])
        ]),
    }
    results = {}
    for name, v in cands.items():
        m = ~np.isnan(v)
        results[name] = {
            "corr_with_RNDCORR": round(float(np.corrcoef(v[m], rc[m])[0, 1]), 4),
            "mean": round(float(np.nanmean(v)), 4),
            "sd": round(float(np.nanstd(v)), 4),
        }
    log.append("候选构造与 RNDCORR 的相关：" +
               "; ".join(f"{k}={v['corr_with_RNDCORR']:+.3f}" for k, v in results.items()))

    best = max(results, key=lambda k: abs(results[k]["corr_with_RNDCORR"]))
    best_r = results[best]["corr_with_RNDCORR"]
    verdict = ("可复现" if best_r >= 0.7 else
               "部分可复现" if best_r >= 0.4 else "不可复现")

    # 供产品判阈使用的分位数
    bv = cands[best]
    bv = bv[~np.isnan(bv)]
    results[best]["percentiles"] = {
        str(p): round(float(np.percentile(bv, p)), 4)
        for p in [1, 2, 5, 10, 25, 50, 75, 90]
    }
    results[best]["direction"] = "high_is_good"

    payload = {
        "method": "IPIP 效度页所列「心理测量反义题」——取题间负相关最强的题对",
        "source_data": "archive/datasets/osf-johnson/validity/ipip20993.dat",
        "sample_n_complete": int(Xc.shape[0]),
        "n_pairs": len(pairs),
        "selection_rule": "题间相关升序，每题最多入选一次，取负相关最强的对",
        "pairs": pairs,
        "candidate_indices": results,
        "best_candidate": best,
        "best_corr_with_RNDCORR": best_r,
        "verdict": verdict,
        "build_log": log,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)

    print("\n".join(log))
    print(f"\n最佳构造：{best}（与 RNDCORR 相关 {best_r:+.3f}）→ 判定：{verdict}")
    print(f"\n最强的 5 对反义题：")
    for p in pairs[:5]:
        print(f"  r={p['r']:+.3f}  [{p['a_facet']}] {p['a_text'][:42]}")
        print(f"                    [{p['b_facet']}] {p['b_text'][:42]}")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
