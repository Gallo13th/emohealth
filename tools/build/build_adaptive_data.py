#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为「自适应选题」打包题-题相关矩阵。

## 为什么需要

第一环 30 题答完后，接下来答哪题要由**信息增益**决定：

    gain_f(i) = (1 − R²_f) · pcorr(i, f | 已答)²

其中
    R²_f            = 以已答题预测面向 f 完整分的 R²
    pcorr(i, f | 已答) = i 与 f 在剔除已答题影响后的偏相关

把偏相关展开后 **`(1 − R²_f)` 正好约掉**：

    gain_f(i) = (r_if − cᵢᵀ A⁻¹ b_f)² / (1 − cᵢᵀ A⁻¹ cᵢ)

其中
    A   = 已答题之间的相关矩阵
    b_f = 已答题与面向 f 的相关
    cᵢ  = 已答题与候选题 i 的相关
    r_if= 候选题 i 与面向 f 的相关

所以每一步只需**求一次 A⁻¹**，之后每个候选题只做几个点积。

## 需要的数据

  · `r_if`  题 × 面向（300×30）——把**全部** 300 题都算上，
            不再像 unlock-data 那样只留 34 题（选题要看全部候选）
  · `r_ij`  题 × 题（300×300 下三角）——本文件新产出的部分

题-题相关用 **int16（×1000）+ base64** 存，约 88 KB（直存 JSON 要 263 KB）。

输出：`data/adaptive-network.json`（**数据层只到这里**）。

前端包 `ui/adaptive-data.js`（`window.EMOHEALTH_ADAPT`）由前端层的
`tools/ui/pack_ui_data.py` 从这份 JSON 打包——数据层不再写 `ui/`（契约 C3）。
"""
from __future__ import annotations

import base64
import json
import os
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
sys.path.insert(0, ROOT)
from tools.item_coding import as_construct_direction  # noqa: E402

DATA = os.path.join(ROOT, "archive/datasets/osf-johnson/validity/ipip20993.dat")
CANON = os.path.join(ROOT, "data/ipip-neo-300.json")
OUT_JSON = os.path.join(ROOT, "data/adaptive-network.json")


def main() -> int:
    from content.facet_definitions import FACETS  # noqa: E402
    canon = json.load(open(CANON, encoding="utf-8"))
    items = sorted(canon["items"], key=lambda x: x["order"])

    fo: dict[str, list[int]] = defaultdict(list)
    for it in items:
        fo[it["facet"]].append(it["order"])
    for f in fo:
        fo[f].sort()
    DOM_KEY = ["neuroticism", "extraversion", "openness",
               "agreeableness", "conscientiousness"]
    facets = [f for dk in DOM_KEY for f in FACETS if FACETS[f]["domain"] == dk]

    dfr = pd.read_csv(DATA, sep="\t", dtype=str, keep_default_na=False)
    X = (dfr[[f"I{i}" for i in range(1, 301)]]
         .replace({"": np.nan, " ": np.nan, "0": np.nan})
         .apply(pd.to_numeric, errors="coerce").to_numpy(float))
    Xc = X[~np.isnan(X).any(axis=1)]
    R, coding = as_construct_direction(Xc, items, expect_recoded=True)
    n = R.shape[0]

    C = np.corrcoef(R, rowvar=False)            # 300×300
    facet_full = {f: R[:, [o - 1 for o in fo[f]]].sum(axis=1) for f in facets}
    IF = np.zeros((300, len(facets)))
    for j, f in enumerate(facets):
        y = facet_full[f]
        for i in range(300):
            IF[i, j] = float(np.corrcoef(R[:, i], y)[0, 1])

    # 题-题下三角 → int16 → base64
    #
    # ⚠️ 精度必须给够。初版用 ×1000（3 位小数），舍入误差**破坏了正定性**：
    #    30×30 子矩阵求逆后出现**负的残差方差**（-0.1653）甚至 NaN，
    #    进而 R²_f 算出 -0.2129，偏相关飙到 211035。
    #    ×10000（4 位小数）仍在 int16 范围内（±10000），精度足够了。
    # 用 float32 存：int16 无论 3 位还是 4 位小数都会破坏正定性。
    # 样本相关矩阵本是 PSD（XᵀX 缩放而来），坏在**存储舍入**上。
    # float32 的相对误差 ~1e-7，代价是 base64 从 117KB 涨到 ~239KB，值得。
    SCALE = None
    tri = np.zeros(300 * 299 // 2, dtype=np.float32)
    k = 0
    for a in range(1, 300):
        vals = C[a, :a].astype(np.float32)
        tri[k:k + a] = vals
        k += a
    assert k == len(tri), (k, len(tri))
    b64 = base64.b64encode(tri.tobytes()).decode("ascii")
    print(f"  题-题相关：{len(tri):,} 个下三角元素 float32 → base64 {len(b64)/1024:.0f} KB")
    # 校验往返
    back = np.frombuffer(base64.b64decode(b64), dtype=np.float32)
    assert np.array_equal(back, tri), "base64 往返不一致"

    rng = np.random.default_rng(20260930)

    # ── 自检①：往返。行偏移是 (a−1)(a−2)/2，写错会整体错位且**不报错**
    def tri_at(i, j):
        if i == j:
            return 1.0
        a, b2 = max(i, j), min(i, j)
        return float(tri[(a - 1) * (a - 2) // 2 + (b2 - 1)])

    n_bad = 0
    for _ in range(4000):
        i = int(rng.integers(1, 301)); j = int(rng.integers(1, 301))
        if i == j:
            continue
        if abs(tri_at(i, j) - C[i - 1, j - 1]) > 1e-6:
            n_bad += 1
    print(f"  自检①：4000 次随机往返，不符 {n_bad} 次")
    assert n_bad == 0, "三角形索引与相关矩阵不符"

    # ── 自检②：随机抽 30 元子集，检查残差方差
    print("  自检②：随机 30 元子集的最小残差方差…")
    worst = 1.0
    nan_seen = 0
    for _ in range(40):
        idx = rng.choice(300, 30, replace=False)
        Ssub = np.eye(30)
        for a in range(30):
            for b2 in range(a):
                i2, j2 = int(idx[a]) + 1, int(idx[b2]) + 1
                Ssub[a, b2] = Ssub[b2, a] = tri_at(i2, j2)
        try:
            Sinv = np.linalg.inv(Ssub)
        except np.linalg.LinAlgError:
            nan_seen += 1
            continue
        for a in range(30):
            c = Ssub[a].copy()
            di = 1 - c @ Sinv @ c
            if not np.isfinite(di):
                nan_seen += 1
            else:
                worst = min(worst, float(di))
    print(f"     最小残差方差 {worst:.4f}；非有限值 {nan_seen} 次")

    payload = {
        "source": f"Johnson (2005) N={n}；{coding['verdict']}",
        "rule": "gain_f(i) = (r_if − cᵢᵀA⁻¹b_f)² / (1 − cᵢᵀA⁻¹cᵢ)；"
                "对所有面向求和后取最大者。偏相关展开后 (1−R²_f) 约掉。",
        "facets": facets,
        "facetOwn": {f: fo[f] for f in facets},
        "itemFacetR": [[round(float(IF[i, j]), 4) for j in range(len(facets))]
                       for i in range(300)],
        "pairScale": 1.0,   # float32 直存，无需缩放
        "pairB64": b64,
    }
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"数据包 → {os.path.relpath(OUT_JSON, ROOT)}  "
          f"({os.path.getsize(OUT_JSON)/1024:.0f} KB)"
          f"（前端包 ui/adaptive-data.js 由 tools/ui/pack_ui_data.py 打包）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
