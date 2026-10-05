#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""多面向剖面演示：三个 facet × 四类真实作答者。

三个 facet 跨两个维度：
  · 焦虑（anxiety）        — 神经质
  · 自律（selfdiscipline） — 尽责性
  · 活跃度（activitylevel）— 外向性

因此这个剖面本身也演示了一件事：**本量表不是按维度成组呈现的**，
用户在作答时不会意识到"接下来十题都在问同一个东西"。
"""
from __future__ import annotations

import os
import sys
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
sys.path.insert(0, ROOT)

from engine.assess import Reference, assess_profile, render_profile  # noqa: E402

DATA = os.path.join(ROOT, "archive/datasets/osf-johnson/validity/ipip20993.dat")
FACETS = ["anxiety", "selfdiscipline", "activitylevel"]
SEP = "=" * 68


def main() -> int:
    warnings.filterwarnings("ignore")
    ref = Reference()
    df = pd.read_csv(DATA, sep="\t", dtype=str, keep_default_na=False)
    ic = [f"I{i}" for i in range(1, 301)]
    items = (df[ic].replace({"": np.nan, " ": np.nan, "0": np.nan})
             .apply(pd.to_numeric, errors="coerce").to_numpy(float))
    meta = (df[["RNDSPLIT", "RNDCORR"]].replace({"": np.nan, " ": np.nan})
            .apply(pd.to_numeric, errors="coerce").to_numpy(float))

    cplt = ~np.isnan(items).any(axis=1)
    rs, rc = meta[:, 0], meta[:, 1]
    idx = np.arange(items.shape[0])

    good = int(idx[cplt & (rs >= np.nanpercentile(rs, 75))
                   & (rc >= np.nanpercentile(rc, 75))][0])
    bad_pool = idx[cplt & (rs <= np.nanpercentile(rs, 5)) & (rc <= np.nanpercentile(rc, 5))]
    bad = int(bad_pool[0]) if len(bad_pool) else int(idx[cplt][np.argmin(rs[cplt] + rc[cplt])])

    def resp(row):
        return {ref.by_order[n]["id"]: int(row[n - 1])
                for n in range(1, 301) if not np.isnan(row[n - 1])}

    for label, i in (("高质量作答者", good), ("粗心作答者", bad)):
        print(f"\n{SEP}\n{label}（记录 #{i}）\n"
              f"数据自带参照：RNDSPLIT={meta[i,0]:.3f}  RNDCORR={meta[i,1]:.3f}\n{SEP}")
        prof = assess_profile(FACETS, resp(items[i]), ref)
        print(render_profile(prof))

    # 只答三个 facet 的 30 题：展示部分剖面的诚实声明
    i = good
    sub = {k: v for k, v in resp(items[i]).items()
           if ref.by_id[k]["facet"] in FACETS}
    print(f"\n{SEP}\n部分作答：只答三个 facet（30 题）\n{SEP}")
    prof = assess_profile(FACETS, sub, ref)
    print(render_profile(prof))
    print("\n完整解读（焦虑）：")
    print(prof["facets"][0]["interpretation"]["narrative"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
