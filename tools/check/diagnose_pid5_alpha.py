#!/usr/bin/env python3
"""诊断：为什么 PID-5 的 α 算出 0.71，而调研报 0.86？

线索：「自己面向最高者 218/220」与调研完全一致 → **题→facet 映射是对的**；
但 α 与面向间相关都系统性偏低约 0.1 → 更像**数据或计分层面的问题**，不是映射。

本脚本对单个 facet（Anhedonia）逐题看：
  · 该 facet 有哪几题、题文
  · 每题与本 facet 其余题之和的相关（翻转后）
  · 哪道题拉低了 α（删掉它 α 会升多少）
  · 两样本分别算，看是否一致
"""

from __future__ import annotations

import csv
import json
import os
import statistics as st
import sys

ROOT = r"C:\Codes\emohealth-20260930-full\emohealth"
DATA = os.path.join(ROOT, "archive", "norms", "pid-5-psychometrics",
                    "zenodo-extracted", "data")
MISSING = {"", None, "NA", "na", "NaN", ".", "-"}


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
    k = len(cols)
    n = len(cols[0])
    iv = sum(st.pvariance(c) for c in cols)
    tot = [sum(cols[i][j] for i in range(k)) for j in range(n)]
    tv = st.pvariance(tot)
    return (k / (k - 1)) * (1 - iv / tv) if tv else 0.0


inst = json.load(open(os.path.join(ROOT, "data", "instruments", "pid-5.json"),
                      encoding="utf-8"))
dims = {d["id"]: list(d.get("items") or []) for d in inst["dimensions"]}
order_of = {it["id"]: it["order"] for it in inst["items"]}
text_of = {it["order"]: it["text"] for it in inst["items"]}
rev = set(json.load(open(os.path.join(ROOT, "data", "pid5-reverse-keys.json"),
                         encoding="utf-8"))["reverse_keyed"])

target = sys.argv[1] if len(sys.argv) > 1 else "pid5_anhedonia"

if target == "all":
    # 全部 25 个 facet 的 α（两个样本各一列）——找出拉低均值的那些
    out = {}
    for fn in ("donor_kerber2022.csv", "SKIDComMet_data.csv"):
        rows = list(csv.DictReader(open(os.path.join(DATA, fn), encoding="utf-8",
                                       newline="")))
        cols = sorted([c for c in rows[0] if c.strip().lower().startswith("pid_")],
                      key=lambda c: int("".join(ch for ch in c if ch.isdigit()) or 0))
        vecs = []
        for r in rows:
            v, ok = [], True
            for o in range(1, 221):
                x = r[cols[o - 1]]
                if x in MISSING:
                    ok = False
                    break
                y = float(x)
                if o in rev:
                    y = 3 - y
                v.append(y)
            if ok:
                vecs.append(v)
        out[fn] = {}
        for d, ids in dims.items():
            if len(ids) < 2:
                out[fn][d] = 0.0
                continue
            cs = [[v[order_of[i] - 1] for v in vecs] for i in ids]
            if not cs or not cs[0]:
                out[fn][d] = 0.0
                continue
            out[fn][d] = alpha(cs)
    print(f"{'facet':34}{'题数':>5}{'donor':>9}{'SKID':>9}{'均值':>9}")
    means = []
    for d in dims:
        a1, a2 = out["donor_kerber2022.csv"][d], out["SKIDComMet_data.csv"][d]
        m = (a1 + a2) / 2
        means.append(m)
        flag = "  ← 低" if m < 0.70 else ""
        print(f"{d:34}{len(dims[d]):>5}{a1:>9.3f}{a2:>9.3f}{m:>9.3f}{flag}")
    print(f"\n25 个 facet 的 α 均值：{st.mean(means):.3f}（已发表 0.87）")
    print(f"低于 0.70 的 facet："
          f"{[(d, round((out['donor_kerber2022.csv'][d] + out['SKIDComMet_data.csv'][d]) / 2, 3)) for d in dims if (out['donor_kerber2022.csv'][d] + out['SKIDComMet_data.csv'][d]) / 2 < 0.70]}")
    sys.exit(0)

ids = dims[target]
print(f"=== {target}（{len(ids)} 题）===")
for i in ids:
    o = order_of[i]
    print(f"   第{o:3}题 {'R' if o in rev else ' '}  {text_of[o][:60]}")

for fn in ("donor_kerber2022.csv", "SKIDComMet_data.csv"):
    rows = list(csv.DictReader(open(os.path.join(DATA, fn), encoding="utf-8",
                                    newline="")))
    cols = sorted([c for c in rows[0] if c.strip().lower().startswith("pid_")],
                  key=lambda c: int("".join(ch for ch in c if ch.isdigit()) or 0))
    vecs = []
    for r in rows:
        v, ok = [], True
        for o in range(1, 221):
            x = r[cols[o - 1]]
            if x in MISSING:
                ok = False
                break
            y = float(x)
            if o in rev:
                y = 3 - y
            v.append(y)
        if ok:
            vecs.append(v)
    cols_of = {i: [v[order_of[i] - 1] for v in vecs] for i in ids}
    a_all = alpha([cols_of[i] for i in ids])
    print(f"\n── {fn}（{len(vecs)} 人）  本 facet α = {a_all:.3f}")
    print(f"   {'题号':>5}{'与本facet其余题相关':>20}{'删掉后 α':>12}")
    for i in ids:
        others = [j for j in ids if j != i]
        comp = [sum(cols_of[j][k] for j in others) for k in range(len(vecs))]
        r_ = corr(cols_of[i], comp)
        a_drop = alpha([cols_of[j] for j in others]) if len(others) > 1 else 0
        flag = "  ← 拉低" if a_drop - a_all > 0.02 else ""
        print(f"   {order_of[i]:>5}{r_:>20.3f}{a_drop:>12.3f}{flag}")
