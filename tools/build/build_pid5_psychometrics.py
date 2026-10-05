#!/usr/bin/env python3
"""用 PID-5 的公开原始作答（N=2,471）算出**题级**推断参数，与大五同口径。

为什么这条路可行（调研结论）
============================
`research/pid5_psychometrics_survey.md` 查明：
  · **文献里没有 220 题的题级参数**（所有已核验来源都止于 facet 级 25 个值）
  · 但 **Zenodo 10.5281/zenodo.22280403（CC-BY-4.0）内含逐题原始作答**：
      donor_kerber2022.csv  1,243 人 × 220 题（0–3；683 临床 + 560 非临床）
      SKIDComMet_data.csv   1,228 人 × 220 题（1–4；配额样本）
    合计 N = 2,471 —— 与大五用的 Johnson (2005) 是同一类材料，口径可以完全对齐。

产出与大五同构（`data/inference/<code>.json`）：
  · `item_dim_corr` 220 × 25 —— 每道题与**全部** 25 个 facet 的相关
  · `dim_corr`      25 × 25  —— facet 间相关
  · `partial`       每个 facet 只答 k 题时与完整分的相关（`r_min` 等）

三项外部核对（调研已做，本脚本复算并打印，作为「映射与反向键都对」的证据）
  · 25 面向 α 均值应 ≈ 0.87（已发表）
  · 面向间相关均值应 ≈ 0.33（已发表）
  · 「自己面向」是 25 个相关中最高的题数应 ≈ 218/220

⚠️ 如实标注
  · 合并样本**不是纯一般人群**（临床 683 + 非临床 560 + 配额 1,228），
    临床样本会抬高题目间相关；
  · `r_min` 是极值序统计量，N=2,471 下会被**系统性低估**（选最差子集有选择偏差），
    所以同时给 `r_p05`；
  · 两样本计分域不同（0–3 / 1–4）：相关与 α 对整体平移不变，合并安全；
    但均值/总分口径须先对齐——这里只算相关，不受影响。
"""

from __future__ import annotations

import csv
import json
import os
import statistics as st
import sys
from itertools import combinations

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from _root import find_root  # noqa: E402
ROOT = str(find_root())

DATA = os.path.join(ROOT, "archive", "norms", "pid-5-psychometrics",
                    "zenodo-extracted", "data")
OUT = os.path.join(ROOT, "data", "inference", "pid-5.json")
MISSING = {"", None, "NA", "na", "NaN", ".", "-"}
MMIN, MMAX = 0, 3


def corr(xs, ys):
    n = len(xs)
    if n < 5:
        return 0.0
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    sxx = sum((a - mx) ** 2 for a in xs) ** 0.5
    syy = sum((b - my) ** 2 for b in ys) ** 0.5
    return sxy / (sxx * syy) if sxx and syy else 0.0


def alpha(cols):
    """K 项 Cronbach α；cols 是 list[list[float]]（每个题一列，同长）。"""
    k = len(cols)
    if k < 2:
        return 0.0
    n = len(cols[0])
    item_var = sum(st.pvariance(c) for c in cols)
    tot = [sum(cols[i][j] for i in range(k)) for j in range(n)]
    tv = st.pvariance(tot)
    return (k / (k - 1)) * (1 - item_var / tv) if tv else 0.0


def main() -> int:
    inst = json.load(open(os.path.join(ROOT, "data", "instruments", "pid-5.json"),
                          encoding="utf-8"))
    dims = [d["id"] for d in inst["dimensions"]]
    by_id = {d["id"]: d for d in inst["dimensions"]}
    dim_items = {d["id"]: list(d.get("items") or []) for d in inst["dimensions"]}
    order_of = {it["id"]: it["order"] for it in inst["items"]}

    # ⚠️ PID-5 的 30 个「维度」里，**25 个是 facet（带 items）、5 个是域（level=2，
    #    items 为空，只有 children）**。我第一版直接对全部 30 个算 α，
    #    5 个空域算出 α=0，把均值从 **0.852 拉低到 0.713**——明明接近已发表的 0.87，
    #    却看起来像方法错了。所以：
    #      · α **只对 facet 算**（域是 facet 的聚合，α 不是可加的）
    #      · 域的总分列用其 children 的题合计（相关与缩放无关）
    def underlying(did: str) -> list[str]:
        """维度（含域）底下的题 id；域递归到 facet。"""
        node = by_id[did]
        if node.get("items"):
            return list(node["items"])
        out: list[str] = []
        for c in node.get("children") or []:
            out.extend(underlying(c))
        return out

    FACETS = [d for d in dims if by_id[d].get("items")]
    rev = set(json.load(open(os.path.join(ROOT, "data", "pid5-reverse-keys.json"),
                             encoding="utf-8"))["reverse_keyed"])

    # 读两份样本。⚠️ 必须**按人对齐**：α 与矩阵都要求同一批人、同一批题。
    #    我第一版按题各自收集有效值再截断到最短——那样第 j 个值不是同一个人，
    #    长度也不齐（`alpha` 直接 IndexError）。改为只保留「220 题全答」的人。
    #
    # ⚠️ 另一个更隐蔽的坑：**不能把两组样本直接拼在一起算相关**。
    #    两组人群不同（临床 683 + 非临床 560 vs 配额样本）、计分域也不同（0–3 vs 1–4），
    #    拼起来后组间差异变成噪音，会**稀释**题间相关——实测 α 均值掉到 0.729，
    #    而已发表是 0.87。正确做法是**各样本内先算相关，再用 Fisher z 加权合并**。
    samples: list[tuple[str, list[list[float]]]] = []
    used = []
    for fn in ("donor_kerber2022.csv", "SKIDComMet_data.csv"):
        p = os.path.join(DATA, fn)
        if not os.path.exists(p):
            print(f"  ✗ 缺 {fn}")
            continue
        rows = list(csv.DictReader(open(p, encoding="utf-8", newline="")))
        cols = sorted([c for c in rows[0] if c.strip().lower().startswith("pid_")],
                      key=lambda c: int("".join(ch for ch in c if ch.isdigit()) or 0))
        if len(cols) != 220:
            print(f"  ✗ {fn} 题列 {len(cols)}（应 220）")
            continue
        kept = []
        for r in rows:
            vec, ok = [], True
            for o in range(1, 221):
                v = r[cols[o - 1]]
                if v in MISSING:
                    ok = False
                    break
                x = float(v)
                if o in rev:
                    x = (MMIN + MMAX) - x
                vec.append(x)
            if ok:
                kept.append(vec)
        samples.append((fn, kept))
        used.append(fn)
        # 该样本内的 α 均值（独立报告，便于与已发表 0.87 对照）
        # ⚠️ 只对 **facet** 算：域（level=2，items 为空）算进去会得 α=0 并把均值拉低
        #    （实测 0.855 → 0.713，看起来像方法错了）
        a_s = [alpha([[v[order_of[i] - 1] for v in kept] for i in dim_items[d]])
               for d in FACETS]
        print(f"  ✓ {fn}：{len(rows)} 人 × 220 题，全答 {len(kept)} 人"
              f"，本样本 α 均值 {st.mean(a_s):.3f}")

    n_total = sum(len(k) for _f, k in samples)
    print(f"\n两样本合计完整作答者：{n_total} 人（**分样本计算后再合并**）")
    series = {}          # 仅为兼容下面 partial 的写法保留：合并后的原始列（未用）

    # 题 → 25 个 facet 的相关（**分样本算，再 Fisher z 加权合并**）
    print("\n=== 计算题级参数（220 × 25）===")
    import math

    def calc(vecs):
        """在一个样本内算：题→维度相关（含域）、维度间相关、维度总分列。"""
        s = {o: [v[o - 1] for v in vecs] for o in range(1, 221)}
        ff = {d: [sum(s[order_of[iid]][j] for iid in underlying(d))
                  for j in range(len(vecs))] for d in dims}
        idc = {}
        for it in inst["items"]:
            idc[it["id"]] = {d: corr(s[it["order"]], ff[d]) for d in dims}
        dc = {a: {b: corr(ff[a], ff[b]) for b in dims} for a in dims}
        return s, ff, idc, dc

    per = [(len(vecs), *calc(vecs)) for _f, vecs in samples]

    def fz(rs_ns):
        """Fisher z 加权合并多个 (r, n)。"""
        num = den = 0.0
        for r, n in rs_ns:
            r = max(-0.999, min(0.999, r))
            w = max(1.0, n - 3)
            num += w * math.atanh(r)
            den += w
        return math.tanh(num / den) if den else 0.0

    item_dim_corr, item_dim = {}, {}
    for it in inst["items"]:
        # 「归属」记到 **facet**（不是域）——域是聚合层
        mydim = next((d for d in FACETS if it["id"] in dim_items[d]), None)
        item_dim[it["id"]] = mydim
        item_dim_corr[it["id"]] = {
            d: round(fz([(p[3][it["id"]][d], p[0]) for p in per]), 4) for d in dims}

    dim_corr = {a: {b: round(fz([(p[4][a][b], p[0]) for p in per]), 4)
                    for b in dims} for a in dims}

    # 三项外部核对
    # α **不能**用 Fisher 合并（它不是相关系数），所以分样本各算一次、报告均值。
    alpha_by_sample = {}
    for fn, vecs in samples:
        a_s = [alpha([[v[order_of[i] - 1] for v in vecs] for i in dim_items[d]])
               for d in FACETS]
        alpha_by_sample[fn] = round(st.mean(a_s), 3)
    off = [dim_corr[a][b] for i, a in enumerate(dims) for b in dims[i + 1:]]
    own_best = sum(1 for it in inst["items"]
                   if max(item_dim_corr[it["id"]], key=item_dim_corr[it["id"]].get)
                   == item_dim[it["id"]])
    a_mean = st.mean(alpha_by_sample.values())
    print(f"  25 面向 α 均值        {a_mean:.3f}  （已发表 0.87）"
          f"  分样本：{alpha_by_sample}")
    print(f"  面向间相关均值        {st.mean(off):.3f}  （已发表 0.33）")
    print(f"  「自己面向」最高者    {own_best}/220")

    # partial：每个 facet 只答 k 题时与完整分的相关（含 r_min 与 r_p05）。
    # 枚举子集需要原始作答，故**分样本算后按样本量加权平均**（与相关矩阵同口径）。
    partial = {}
    for d in FACETS:
        ids = dim_items[d]
        acc: dict[str, list[tuple[float, float, float, int]]] = {}
        for _fn, vecs in samples:
            s = {o: [v[o - 1] for v in vecs] for o in range(1, 221)}
            full = [sum(s[order_of[iid]][j] for iid in ids)
                    for j in range(len(vecs))]
            n = len(vecs)
            for k in range(1, len(ids)):
                rs = [corr([sum(s[order_of[i]][j] for i in sub)
                            for j in range(n)], full)
                      for sub in combinations(ids, k)]
                rs.sort()
                acc.setdefault(str(k), []).append(
                    (st.mean(rs), rs[0],
                     rs[max(0, int(len(rs) * 0.05) - 1)], n))
        partial[d] = {
            k: {
                "r_mean": round(sum(a * n for a, _m, _p, n in rows) / sum(n for *_x, n in rows), 4),
                "r_min": round(min(m for _a, m, _p, _n in rows), 4),
                "r_p05": round(min(p for _a, _m, p, _n in rows), 4),
                "subsets": sum(1 for _ in rows),
            } for k, rows in acc.items()
        }

    # ── 题间相关三角阵（pairB64）────────────────────────────────────────
    # 这是与大五**真正对齐**的关键：大五的推断（ui/index.html 的 pairR/adaptCtx）
    # 读的是 `AD.pairB64`——一个完整的**题间相关矩阵**，用来做偏相关
    # （「已答这些题之后，候选题还能提供多少新信息」）。只给「题→维度相关」
    # 是不够的：那只能算简单的加权，不能算条件增益。
    #
    # 格式必须与大五**逐位一致**（界面 `pairR` 的偏移公式写死了）：
    #   · float32 三角阵，按 a=2..n、b=1..a-1 的顺序展平
    #   · `pairR(i,j)` 取下标 `(a-1)(a-2)/2 + (b-1)`，a=max(i,j)、b=min(i,j)
    #   · base64 编码后存 `pairB64`
    # ⚠️ 大五的注释记着一个坑：曾用 int16×1000 存，舍入破坏正定性 →
    #    负残差方差与 NaN。所以这里**必须 float32 直存**。
    print("\n=== 题间相关三角阵（220×220 → pairB64）===")
    import base64
    import struct

    def tri_of(vecs):
        n, p = len(vecs), 220
        cols = [[v[o] for v in vecs] for o in range(p)]
        mu = [sum(c) / n for c in cols]
        sd = [(sum((x - m) ** 2 for x in c) / n) ** 0.5 for c, m in zip(cols, mu)]
        out = []
        for a in range(1, p):
            ca, ma, sa = cols[a], mu[a], sd[a]
            for b in range(a):
                cb, mb, sb = cols[b], mu[b], sd[b]
                s = sum((ca[k] - ma) * (cb[k] - mb) for k in range(n))
                out.append(s / (n * sa * sb) if sa and sb else 0.0)
        return out, n

    tris = []
    for _fn, vecs in samples:
        t, n = tri_of(vecs)
        tris.append((t, n))
    # Fisher z 加权合并两个样本的三角阵
    import math
    merged = []
    for k in range(len(tris[0][0])):
        num = den = 0.0
        for t, n in tris:
            r = max(-0.999, min(0.999, t[k]))
            w = max(1.0, n - 3)
            num += w * math.atanh(r)
            den += w
        merged.append(math.tanh(num / den) if den else 0.0)
    buf = b"".join(struct.pack("<f", v) for v in merged)
    pair_b64 = base64.b64encode(buf).decode("ascii")
    print(f"  {len(merged)} 个系数 → float32 {len(buf)} B → base64 {len(pair_b64)} B")

    # 每题的「本维度最小可靠题量」：从 partial 曲线反推
    # （大五把 MIN_OWN 写死为 2；这里改成**由数据推**，PID-5 各 facet 的题数
    #   差别大（4–14），写死一个值对 4 题的 facet 与 14 题的 facet 同样不合理）
    min_own = {}
    for d in FACETS:
        pk = partial[d]
        need = None
        for k in sorted((int(x) for x in pk), reverse=True):
            if pk[str(k)]["r_min"] >= 0.80:
                need = k
            else:
                break
        min_own[d] = need if need else 1
    print(f"  partial 推出的最小可靠题量："
          f"{sorted(set(min_own.values()))}（各 facet 1–{max(min_own.values())}）")

    payload = {
        "instrument": "PID-5",
        "level": "item_level",
        "level_note": "有实测的题→facet 相关与 facet 间相关矩阵（从公开原始作答自算）",
        "n_items": 220,
        "n_dims": len(dims),
        "n_respondents": n_total,
        "item_dim": item_dim,
        "item_dim_corr": item_dim_corr,
        "item_domain_corr": {},
        "dim_corr": dim_corr,
        "partial": partial,
        "min_own": min_own,
        # 题间相关三角阵（与大五 adaptive-network 的 pairB64 同格式、同用途）
        "pairB64": pair_b64,
        "pair_note": ("float32 三角阵，按 a=2..n、b=1..a-1 展平；"
                      "下标 = (a−1)(a−2)/2 + (b−1)，a=max(i,j)、b=min(i,j)。"
                      "两样本 Fisher z 加权合并。与大五同一格式与用途。"),
        "quality": {
            "basis": ("从 Zenodo 10.5281/zenodo.22280403（CC-BY-4.0）内含的逐题原始作答自算："
                      + " + ".join(used)),
            "sample_note": ("N=2,471（临床 683 + 非临床 560 + 配额 1,228）——"
                            "**不是纯一般人群**，临床样本会抬高题目间相关"),
            "reverse_keys": f"{len(rev)} 题（含手册 facet 表另标的 7、30；见 data/pid5-reverse-keys.json 的 evidence）",
            "external_checks": {
                "alpha_mean": round(a_mean, 3),
                "alpha_by_sample": alpha_by_sample,
                "alpha_published": 0.87,
                "interfacet_mean": round(st.mean(off), 3),
                "interfacet_published": 0.33,
                "own_facet_strongest": f"{own_best}/220",
            },
            "caveats": [
                "r_min 是极值序统计量，N=2,471 下会被系统性低估（选最差子集有选择偏差），故同时给 r_p05",
                "两样本计分域不同（0–3 / 1–4）：相关与 α 对整体平移不变，合并安全；均值/总分口径须先对齐",
                "文献里没有 220 题的题级参数，本数据是**自算**而非引用——它的可信度来自三项外部核对同时吻合",
            ],
            "survey_report": "research/pid5_psychometrics_survey.md",
        },
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write("\n")
    print(f"\n✓ 已写出 data/inference/pid-5.json（{os.path.getsize(OUT) / 1024:.0f} KB）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
