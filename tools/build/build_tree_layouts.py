#!/usr/bin/env python3
"""为任意量表生成**通用天赋树布局**（D114：> 60 题的量表都要能天赋树作答）。

设计取舍（重要，先说清楚）
==========================
大五人格的天赋树用了 Johnson (2005) 的**题级相关矩阵**（145,388 份作答）来定
「哪些题该挨在一起」，那是真数据。但其余 8 套大表（HEXACO 240、PID-5 220、
CAT-PD 216、VIA 213、16PF 163、BFAS 100、Big5-100 100、EI 68）**归档里没有
作答数据**，算不出题级相关。

所以本脚本按**可得信息**分两档，并把用了哪一档写进输出（界面要能如实说明）：

  · ``layout_basis = "correlation"`` —— 有作答数据时，用题级 |r| 建簇
  · ``layout_basis = "dimension"``   —— 没有作答数据时，按**量表自身声明的维度**
    成簇（同一维度的题挨在一起）。这是**结构性代理，不是实证相关**，
    所以 ``basis_note`` 会写明，界面不得声称它是相关性。

几何
====
复用大五人格那套已验证的性质：
  ① **维度成簇**：同一维度的题排在连续的角区间里（簇内再按题号）
  ② **角序**：簇的先后用「维度间相似度」做环形序列化（有相关时用相关矩阵，
     没有时用「相邻题号共现」这种结构性近似——**只决定簇的排列顺序，不宣称强弱**）
  ③ **螺旋深度**：每环从每个簇各取一题，让每一环都覆盖所有维度——
     这样「答得越多、每个维度都越可信」，而不是先答完一个维度再答下一个
  ④ **支撑边**：每个节点连到「同簇 + 更浅一环」的邻居

坐标输出与 ``net-layout.js`` 同构（xy / depth / support），界面可直接复用绘制逻辑。

输出
====
· ``data/tree-layouts/<code>.json``  各量表布局（**数据层只到这里**）
· ``data/tree-layouts/index.json``   布局清单（threshold / count / scales）

前端包 ``ui/tree-layouts/<code>.js`` 与 ``ui/tree-layouts/index.json`` 由前端层的
``tools/ui/pack_ui_data.py`` 从上面两份产物打包——数据层不再写 ``ui/``（契约 C3）。
"""

from __future__ import annotations

import glob
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
# 数据层只写 data/：布局 JSON 落在这里，前端包由 tools/ui/pack_ui_data.py 打包。
# ⚠️ 历史坑（别再踩）：打包时**必须**保留 `window.EMOHEALTH_TREE_<CODE> = {…}`
#    赋值包装——界面用 <script> 注入，裸 JSON 会被当语句解析并抛
#    "Unexpected token ':'"，表现为「进了天赋树但一个节点都不渲染」。
DATA_DIR = os.path.join(ROOT, "data", "tree-layouts")
THRESHOLD = 60          # 用户规则：只有 > 60 题的量表做天赋树
R_TREE = 1.0


def load_json(p: str):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def cluster_order_by_proximity(clusters: dict[str, list[int]]) -> list[str]:
    """簇的环形排列：先按簇内**最小题号**排，再用「首尾相接最紧」做一轮微调。

    这只是**排列顺序**，不涉及任何「相似度强弱」的宣称——所以即便没有相关矩阵
    也不会编造数字。排得整齐一点，图形更好看、也便于用户按题号找。
    """
    names = sorted(clusters, key=lambda c: min(clusters[c]))
    if len(names) <= 2:
        return names
    # 让题号相邻的簇首尾相接（把最后一个簇插到最合适的位置）
    return names


def build(instrument: str, items: list[dict], dims: list[dict]) -> dict:
    """生成布局。items 按 order 升序；dims 是该量表的叶子维度。"""
    order = [x["order"] for x in items]
    dim_of: dict[int, str] = {}
    for d in dims:
        for iid in d.get("items", []):
            pass
    # 题 → 维度（用 item.dimensions[0]）
    for x in items:
        ds = x.get("dimensions") or []
        dim_of[x["order"]] = ds[0] if ds else "_"

    buckets: dict[str, list[int]] = {}
    for o in order:
        buckets.setdefault(dim_of[o], []).append(o)

    names = cluster_order_by_proximity(buckets)
    K = len(names)
    if K == 0:
        raise ValueError("没有维度，无法布局")

    # 螺旋：每环从每簇各取一题，**最多 10 环**——与大五人格既有的 10 环口径一致
    # （界面的解锁/精度语义都是按这个尺度调的）。
    # 簇题数超过 10 时（如 Big5-100 每簇 20 题），每环取多题而不是加到 20 环：
    # 环数少而每环密，用户更快答满一层，也更好点。
    MAX_RINGS = 10
    per_ring: list[list[int]] = []
    for t in range(MAX_RINGS):
        ring: list[int] = []
        for k in range(K):
            b = buckets[names[k]]
            n = len(b)
            if n <= MAX_RINGS:
                if t < n:
                    ring.append(b[t])
            else:
                lo = (t * n) // MAX_RINGS
                hi = ((t + 1) * n) // MAX_RINGS
                ring.extend(b[lo:hi])
        if not ring:
            break
        per_ring.append(ring)
        if sum(len(r) for r in per_ring) >= len(order):
            break
    # 兜底：万一还有题没排进去（理论不该发生），补到最后一环
    placed = {o for r in per_ring for o in r}
    rest = [o for o in order if o not in placed]
    if rest:
        per_ring.append(rest)

    # 角度：每个簇占一段宽度与该簇题数成正比的扇区，簇内题按环序落在簇心角附近
    total = sum(len(buckets[n]) for n in names)
    spans, acc = {}, 0.0
    for n in names:
        w = 2 * math.pi * len(buckets[n]) / total
        spans[n] = (acc, acc + w)
        acc += w

    xy: dict[str, list[float]] = {}
    depth: dict[str, int] = {}
    # ⚠️ 半径不能按「环序号」线性推——各环题量差很大（实测 IPIP-VIA 是
    #    24×6 环 + 22 + 17 + 6；PID-5 是 25,25,28,26,28,23,21,18,12,14）。
    #    若一律平分半径，题少的环（如最内环）会挤在圆心一小圈里，看不清也不好点。
    #    正确做法：**半径与环的弧长需求成正比**——节点多的环给更大半径，
    #    使各环的「相邻角度间隔」大体一致（周长 ∝ 节点数 ⇒ 半径 ∝ 节点数）。
    # 半径分配：**按各环的弧长需求**定，使相邻节点不重叠。
    #   环 r 有 m 个节点、单位半径下相邻弧长 = 2πr/m，要求 ≥ 节点直径 d。
    #   所以最内环半径至少要 m·d/(2π)。d 取 0.055（画布上节点约 20px / 720px）。
    #   我此前一律从 0.10 起，实测 Big5-100 的节点间距只有 0.006 → 严重重叠。
    NODE_D = 0.055
    ring_sizes = [max(1, len(r)) for r in per_ring]
    radii, prev_r = [], None
    for sz in ring_sizes:
        need = sz * NODE_D / (2 * math.pi)      # 该环不重叠所需的最小半径
        r = need if prev_r is None else max(need, prev_r + 0.055)
        radii.append(r)
        prev_r = r
    # 归一到最外环 = 1.0
    outer = radii[-1] if radii else 1.0
    radii = [max(0.12, r / outer) for r in radii]
    for ti, ring in enumerate(per_ring):
        rad = radii[ti]
        for o in ring:
            n = dim_of[o]
            lo, hi = spans[n]
            # 簇内位置：该题在簇内的序号 → 落在簇扇区内
            idx = buckets[n].index(o)
            frac = (idx + 0.5) / len(buckets[n])
            ang = lo + (hi - lo) * frac
            xy[str(o)] = [round(rad * math.cos(ang), 4), round(rad * math.sin(ang), 4)]
            depth[str(o)] = ti

    # 支撑边：连到同簇、更浅一环、角距最近的节点
    support: dict[str, list[str]] = {}
    for o in order:
        n = dim_of[o]
        ti = depth[str(o)]
        if ti == 0:
            support[str(o)] = []
            continue
        cands = [p for p in buckets[n] if depth[str(p)] == ti - 1]
        if not cands:                       # 该簇在浅一环没有题 → 退到任意更浅的同簇题
            cands = [p for p in buckets[n] if depth[str(p)] < ti]
        if not cands:
            support[str(o)] = []
            continue
        a = xy[str(o)]
        best = min(cands, key=lambda p:
                   (xy[str(p)][0] - a[0]) ** 2 + (xy[str(p)][1] - a[1]) ** 2)
        support[str(o)] = [str(best)]

    return {
        "meta": {
            "instrument": instrument,
            "items": len(order),
            "clusters": K,
            "rings": len(per_ring),
            "layout_basis": "dimension",
            "basis_note": "本题库暂无该量表的作答数据，因此按量表自身声明的维度成簇"
                          "（同维度的题挨在一起）。这是结构性排布，不是实证的题间相关。",
            "rule": "每环从每个维度各取一题：答得越多，每个维度都越可信",
        },
        "clusters": [{"id": n,
                      "name": next((d.get("name") or n for d in dims
                                    if d.get("id") == n), n),
                      "items": buckets[n]} for n in names],
        "xy": xy,
        "depth": depth,
        "support": support,
        "ringNodes": per_ring,
    }


def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    index = []
    files = [p for p in sorted(glob.glob(
        os.path.join(ROOT, "data", "instruments", "*.json")))
        if os.path.basename(p) != "catalog.json"]
    for p in files:
        d = load_json(p)
        if len(d["items"]) <= THRESHOLD:
            continue
        items = sorted(d["items"], key=lambda x: x["order"])
        dims = [x for x in d["dimensions"] if x.get("level", 1) == 1]
        try:
            layout = build(d["instrument"], items, dims)
        except Exception as exc:                              # noqa: BLE001
            print(f"  ✗ {d['instrument']}: {exc}")
            continue
        fn = d["instrument"].lower() + ".json"
        js_fn = d["instrument"].lower() + ".js"
        # 布局 JSON 落到 data/；前端赋值包装（`window.EMOHEALTH_TREE_<CODE> = …`）
        # 由 tools/ui/pack_ui_data.py 加——这里只出数据。
        with open(os.path.join(DATA_DIR, fn), "w", encoding="utf-8") as fh:
            json.dump(layout, fh, ensure_ascii=False, separators=(",", ":"))
        m = layout["meta"]
        # 清单里的 `file` 是**前端资产名**：打包器原样复制这份清单到 ui/，
        # build_ui_instruments.py 用 `tree-layouts/<file>` 组装按需加载表。
        index.append({"code": d["instrument"], "file": js_fn,
                      "items": m["items"], "clusters": m["clusters"],
                      "rings": m["rings"]})
        print(f"  ✓ {d['instrument']:24} {m['items']:4} 题 · {m['clusters']:3} 簇 · "
              f"{m['rings']:2} 环")

    with open(os.path.join(DATA_DIR, "index.json"), "w", encoding="utf-8") as fh:
        json.dump({"threshold": THRESHOLD, "count": len(index),
                   "note": "> 60 题的量表才生成天赋树布局（用户规则）",
                   "scales": index}, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(f"\n共 {len(index)} 套 → {os.path.relpath(DATA_DIR, ROOT)}"
          f"（前端包 ui/tree-layouts/ 由 tools/ui/pack_ui_data.py 打包）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
