#!/usr/bin/env python3
"""检查树布局的几何：内环半径是否足够大、坐标是否铺开。

背景：IPIP-EI 的 7 个可答节点曾挤在圆心一小圈里（半径 ~0.30），
照这样渲染出来几乎看不出、也不好点。改成「半径 ∝ 环的题量」后再查一次。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
TL = os.path.join(ROOT, "ui", "tree-layouts")
idx = json.load(open(os.path.join(TL, "index.json"), encoding="utf-8"))

print(f"{'量表':14} {'内环半径':>12} {'最外半径':>10} {'节点间最小间距':>14}")
for s in idx["scales"]:
    p = os.path.join(TL, os.path.basename(s["file"]))
    src = open(p, encoding="utf-8").read()
    d = json.loads(src[src.index("=") + 1:].rstrip().rstrip(";"))
    pts = [(k, v) for k, v in d["xy"].items()]
    r = {k: (v[0] ** 2 + v[1] ** 2) ** 0.5 for k, v in pts}
    inner = [k for k in r if d["depth"][k] == 0]
    ir = [r[k] for k in inner]
    # 最小节点间距（只抽样，避免 O(n²) 太慢）
    step = max(1, len(pts) // 120)
    sub = pts[::step]
    mind = 9e9
    for i in range(len(sub)):
        for j in range(i + 1, len(sub)):
            (a, va), (b, vb) = sub[i], sub[j]
            dd = ((va[0] - vb[0]) ** 2 + (va[1] - vb[1]) ** 2) ** 0.5
            if dd < mind:
                mind = dd
    print(f"{s['code']:14} {min(ir):6.3f}..{max(ir):5.3f} {max(r.values()):10.3f} "
          f"{mind:14.4f}")
