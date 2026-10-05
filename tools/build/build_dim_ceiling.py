#!/usr/bin/env python3
"""把推断数据改成「**实时置信度 + 相对该面向上限的比例**」口径（方案 b）。

用户的纠正
==========
「没有所谓的可靠题量，应该是实时动态计算当前的答题结果其置信度。」
—— 静态的 `min_own` 是错的概念：答几题够，取决于**答的是哪几题**。

本脚本做三件事
==============
① **`item_dim_corr` 改为 corrected**（题与「**其余题**之和」的相关，去本题）。
   原先用 inflated（含本题，见原 `dimRNote`），会让「自己那一道题」自解释、
   把置信度抬高——`MIN_OWN` 就是为堵这个虚高加的**补丁**。实测差 0.104
   （30 面向平均 0.650 → 0.545）。

② **新增 `dim_ceiling`**：每个维度「答满它自己的题」时的置信度上限。
   这是**维度自身的属性**（衡量这套题最好能测多准），不是题量门槛。
   实测大五最低 activitylevel 0.729、中位 0.839、最高 anger 0.920——正因有这天花板，
   绝对门槛（0.85）对低题质维度**永远不可达**，那是「题目测不准」而非「答得不够」。

③ **移除 `min_own`**（静态题量概念），改为 `ceiling_ratio = 0.90`：
   判据变成 `当前置信度 ≥ ceiling_f × 0.90`，**完全由当前答题组合决定**。

⚠️ **口径必须与前端同源**（第 2 版修的重要 bug）
================================================
第 1 版把两份 PID-5 样本**直接拼接**算 `corrcoef`，而 `pairB64`
（`build_pid5_psychometrics.py`）是**分样本算再 Fisher-z 合并**。
于是 ceiling 与前端实际用的题间相关**不同源**，实测后果：全部 25 个维度
「答满时的 r_full」都超过 ceiling（最多 1.285），`risk_taking` 反而答满也不达标。
**修法**：`A` 直接从 `pairB64` 解码（前端用什么我就用什么），`b` 分样本算 corrected
后 Fisher 合并 → **「答满 → r_full = ceiling」精确成立**。

置信度算式（与前端一致）
========================
  R² = bᵀ A⁻¹ B     A = 已答题的题间相关（来自 `pairB64`）；b = 已答题与完整维度分的相关
  ceiling_f 用该维度**全部题**代入；任意子集用子集代入。

⚠️ 需要 numpy/pandas，用 bundled python 跑：
   C:\\Users\\letgao\\.dsh\\dsh-runtimes\\dsh-primary-runtime\\dependencies\\python\\python.exe
"""

from __future__ import annotations

import base64
import csv
import json
import math
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from _root import find_root  # noqa: E402
ROOT = str(find_root())

CEILING_RATIO = 0.90
MISSING = {"", None, "NA", "na", "NaN", ".", "-"}


def decode_pair(inf: dict) -> np.ndarray:
    """把 `pairB64` 解码成 n×n 题间相关矩阵（行 a=2..n、b=1..a-1 展平）。"""
    n = inf["n_items"]
    buf = np.frombuffer(base64.b64decode(inf["pairB64"]), dtype="<f4")
    A = np.eye(n)
    for a in range(2, n + 1):
        off = (a - 1) * (a - 2) // 2
        for b in range(1, a):
            A[a - 1, b - 1] = A[b - 1, a - 1] = float(buf[off + (b - 1)])
    return A


def fz(pairs) -> float:
    """Fisher-z 按样本量加权合并多个 (r, n)。"""
    num = den = 0.0
    for r, n in pairs:
        r = max(-0.999, min(0.999, r))
        w = max(1.0, n - 3)
        num += w * math.atanh(r)
        den += w
    return math.tanh(num / den) if den else 0.0


def encode_pair(A: np.ndarray) -> str:
    """把 n×n 题间相关矩阵编码回 `pairB64`（与 decode_pair 互逆）。

    ⚠️ 必须**写回**：若只把 A 重排用于算 ceiling、却让文件里的 `pairB64` 保持旧序，
    则文件内 `pairB64`（旧序）与 `item_dim_corr`（按量表包 id）**不同序**，
    前端读出来照样错位。实测后果：大五 30 个维度的「答满 r_full」与 ceiling
    最大差 **0.2714**（PID-5 因为本来就是同序，差 0.00005）。
    """
    n = A.shape[0]
    vals = [float(A[a - 1, b - 1]) for a in range(2, n + 1) for b in range(1, a)]
    return base64.b64encode(np.array(vals, dtype="<f4").tobytes()).decode("ascii")


# ── 样本加载：每个样本带**自己的** min/max（反向题用它翻转）──────
def samples_ipip():
    import pandas as pd
    canon = json.load(open(os.path.join(ROOT, "data", "ipip-neo-300.json"),
                           encoding="utf-8"))
    items = sorted(canon["items"], key=lambda x: x["order"])
    dfr = pd.read_csv(os.path.join(ROOT, "archive/datasets/osf-johnson",
                                   "validity", "ipip20993.dat"),
                      sep="\t", dtype=str, keep_default_na=False)
    X = (dfr[[f"I{i}" for i in range(1, 301)]]
         .replace({"": np.nan, " ": np.nan, "0": np.nan})
         .apply(pd.to_numeric, errors="coerce").to_numpy(float))
    Xc = X[~np.isnan(X).any(axis=1)]
    # 大五：数据**已预编码**（tools/check/diagnose_ipip_recoding.py: 148/148 未翻转即正相关），
    # 所以不翻转。min/max 只用于说明。
    return [(Xc, 1, 5, None)], "Johnson (2005)；完整作答 %d 条" % Xc.shape[0]


def samples_pid5():
    D = os.path.join(ROOT, "archive", "norms", "pid-5-psychometrics",
                     "zenodo-extracted", "data")
    rev = set(json.load(open(os.path.join(ROOT, "data", "pid5-reverse-keys.json"),
                             encoding="utf-8"))["reverse_keyed"])
    out = []
    for fn, lo, hi in (("donor_kerber2022.csv", 0, 3),
                       ("SKIDComMet_data.csv", 1, 4)):
        p = os.path.join(D, fn)
        if not os.path.exists(p):
            continue
        rows = list(csv.DictReader(open(p, encoding="utf-8", newline="")))
        cols = sorted([c for c in rows[0] if c.strip().lower().startswith("pid_")],
                      key=lambda c: int("".join(ch for ch in c if ch.isdigit()) or 0))
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
                    x = (lo + hi) - x          # 各样本用自己的 min/max
                vec.append(x)
            if ok:
                kept.append(vec)
        if kept:
            out.append((np.array(kept, float), lo, hi, fn))
    return out, "两样本 Fisher 合并（donor 0–3 / SKID 1–4，各自翻转）"


def main() -> int:
    for code, loader in (("IPIP-NEO", samples_ipip), ("PID-5", samples_pid5)):
        p = os.path.join(ROOT, "data", "inference", code.lower() + ".json")
        if not os.path.exists(p):
            print(f"  ✗ {code}：缺 {p}")
            continue
        inf = json.load(open(p, encoding="utf-8"))
        inst = None
        for fn in os.listdir(os.path.join(ROOT, "data", "instruments")):
            if fn.endswith(".json") and fn != "catalog.json":
                q = json.load(open(os.path.join(ROOT, "data", "instruments", fn),
                                   encoding="utf-8"))
                if q["instrument"] == code:
                    inst = q
                    break
        order_of = {it["id"]: it["order"] for it in inst["items"]}
        by_dim = {}
        for d in inst["dimensions"]:
            if d.get("items"):
                by_dim[d["id"]] = sorted(order_of[i] for i in d["items"])
        dims = sorted(by_dim)

        samp, src = loader()
        # **A 与前端同源**：直接用 pairB64，不自己算题间相关
        A = decode_pair(inf)
        # ⚠️ **题序对齐**：`pairB64` 的题序与「量表包 items[].order」不一定一致。
        #    · PID-5：`build_pid5_psychometrics.py` 就是按量表包 order 排的 → 一致
        #    · 大五：`pairB64` 搬自 `adaptive-network.json`，是 **canon 题序**
        #      （`data/ipip-neo-300.json`，**轮转**排列），而量表包是**按 facet 分组**
        #      排列 —— 两者题序完全不同！直接用会让 A 整体错位。
        #      实测错位后果：30 个 ceiling 掉到 0.109–0.698（应 0.729–0.920）。
        if code == "IPIP-NEO":
            canon = json.load(open(os.path.join(ROOT, "data", "ipip-neo-300.json"),
                                   encoding="utf-8"))

            def nn(s):
                return "".join(c for c in (s or "").lower() if c.isalnum())

            by_text = {nn(it["text"]): it["id"] for it in inst["items"]}
            # 量表包 order → canon order
            pkg2canon = {}
            for c in sorted(canon["items"], key=lambda x: x["order"]):
                iid = by_text.get(nn(c.get("text")))
                if iid is not None:
                    pkg2canon[order_of[iid]] = c["order"]
            miss = len(order_of) - len(pkg2canon)
            perm = [pkg2canon.get(i) for i in range(1, inf["n_items"] + 1)]
            if any(p is None for p in perm):
                print(f"  ✗ {code}：有 {sum(1 for p in perm if p is None)} 题无法对回 canon，放弃")
                continue
            idx = [p - 1 for p in perm]
            A = A[np.ix_(idx, idx)]          # 重排成量表包序
            print(f"  {code}：pairB64 已从 canon 序重排为量表包序"
                  f"（{len(perm)} 题，未匹配 {miss}）")
        print(f"  {code}：{len(samp)} 个样本｜{len(dims)} 维度｜A 来自 pairB64")

        # b：分样本算 corrected，再 Fisher 合并。
        # ⚠️ 原始数据的列序 = **数据自身的题序**（大五是 canon 序、PID-5 是量表包序），
        #    所以索引用 `dord()` 转换后的题号，不能直接用量表包 order。
        dord = (lambda o: pkg2canon[o]) if code == "IPIP-NEO" else (lambda o: o)
        by_dim_d = {d: sorted(dord(x) for x in os_) for d, os_ in by_dim.items()}
        new_idc = {}
        for iid, o in order_of.items():
            od = dord(o)
            row = {}
            for d in dims:
                pairs = []
                for X, _lo, _hi, _fn in samp:
                    others = [x for x in by_dim_d[d] if x != od]
                    if od not in by_dim_d[d] or not others:
                        continue
                    total_wo = X[:, [x - 1 for x in others]].sum(axis=1)
                    r = float(np.corrcoef(X[:, od - 1], total_wo)[0, 1])
                    pairs.append((r, X.shape[0]))
                row[d] = round(fz(pairs), 4) if pairs else 0.0
            new_idc[iid] = row

        # ceiling：用同一对 (A, b)
        ceil = {}
        for d in dims:
            idx = [x - 1 for x in by_dim[d]]
            b = np.array([new_idc[iid][d] for iid in order_of
                          if order_of[iid] in by_dim[d]])
            try:
                x = np.linalg.solve(A[np.ix_(idx, idx)], b)
                ceil[d] = round(max(0.0, min(1.0, float(b @ x))) ** 0.5, 4)
            except np.linalg.LinAlgError:
                ceil[d] = 0.0

        inf["item_dim_corr"] = new_idc
        # 把（可能重排过的）A 写回 pairB64，保证文件内两字段**同序**
        inf["pairB64"] = encode_pair(A)
        inf["pair_note"] = (inf.get("pair_note") or "") + \
            "；本次已重排为**量表包题序**，与 item_dim_corr 同序"
        inf["item_dim_corr_kind"] = ("corrected（题与「其余题之和」的相关，**去本题**）"
                                    "——避免自解释使置信度虚高")
        inf["dim_ceiling"] = ceil
        inf["ceiling_ratio"] = CEILING_RATIO
        inf["ceiling_note"] = (
            f"维度自身的置信度上限（答满该维度的题时 r，用 **pairB64 的题间相关** 与 "
            f"corrected 的题↔维度相关算出，与前端同源）。判据："
            f"当前置信度 ≥ ceiling × {CEILING_RATIO} —— 完全由当前答题组合决定，"
            f"**没有题量门槛**。标定见 tools/check/calibrate_ceiling_ratio.py。")
        inf.pop("min_own", None)
        inf["min_own_removed"] = ("已移除：不存在「可靠题量」——答几题够取决于**答的是哪几题**。"
                                  "判据改为「相对该维度置信度上限的比例」")
        inf.setdefault("quality", {})["ceiling_source"] = src
        inf["quality"]["pair_source"] = "dim_ceiling 与 item_dim_corr 都与 pairB64 同口径"
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(inf, fh, ensure_ascii=False, separators=(",", ":"))
            fh.write("\n")
        cs = sorted(ceil.values())
        print(f"    ✓ ceiling 最低 {cs[0]:.3f} 中位 {cs[len(cs)//2]:.3f} "
              f"最高 {cs[-1]:.3f}｜ratio {CEILING_RATIO}｜min_own 已移除")
    return 0


if __name__ == "__main__":
    sys.exit(main())
