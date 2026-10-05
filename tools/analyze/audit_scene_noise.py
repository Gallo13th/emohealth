#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""噪声核查：用 embedding 找出「与自己所属情景最不像」的题。

不靠感觉翻 300 条，而是让数据指出**最可疑的那些**，复核聚焦在它们上面。

三个指标：
  1. 与**本情景质心**的余弦相似度（越低越可疑）
  2. 与本情景内其余题的**平均相似度**
  3. **最近的另一个情景质心**——若它明显比本情景更近，就是重分配的候选

输出：`data/scene-noise-audit.json`（全部 300 题的指标 + 按可疑度排序）
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
EMB = os.path.join(ROOT, "data/item-embeddings.npy")
TAX = os.path.join(ROOT, "data/scene-taxonomy.json")
OUT = os.path.join(ROOT, "data/scene-noise-audit.json")
API_EMB = "https://api.siliconflow.cn/v1/embeddings"
KEY = "sk-logzgepgyfvhjgnowmimulmkrlmyzosdyftfjxiwazoqihav"
MODEL = "BAAI/bge-large-zh-v1.5"


def ensure_embeddings(texts: list[str]) -> np.ndarray:
    if os.path.exists(EMB):
        return np.load(EMB)
    import time
    import urllib.request
    vecs = []
    for i in range(0, len(texts), 32):
        chunk = texts[i:i + 32]
        body = json.dumps({"model": MODEL, "input": chunk}).encode()
        req = urllib.request.Request(
            API_EMB, data=body,
            headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=90) as r:
            d = json.loads(r.read().decode())
        vecs.extend([x["embedding"] for x in d["data"]])
        print(f"  embed {min(i+32, len(texts))}/{len(texts)}", flush=True)
        time.sleep(0.2)
    a = np.array(vecs, dtype=np.float32)
    np.save(EMB, a)
    return a


def main() -> int:
    tax = json.load(open(TAX, encoding="utf-8"))
    items = tax["items"]
    orders = sorted(int(k) for k in items)
    texts = [items[str(o)]["text_zh"] for o in orders]
    E = ensure_embeddings(texts)
    # L2 归一化 → 内积即余弦
    En = E / np.linalg.norm(E, axis=1, keepdims=True)

    scene_of = [items[str(o)]["scene"] for o in orders]
    scenes = sorted(set(scene_of))
    idx_by_scene = defaultdict(list)
    for i, s in enumerate(scene_of):
        idx_by_scene[s].append(i)

    cents = {}
    for s, idxs in idx_by_scene.items():
        cents[s] = En[idxs].mean(axis=0)

    rows = []
    for i, o in enumerate(orders):
        s = scene_of[i]
        own = np.array(idx_by_scene[s])
        peers = own[own != i]
        # 与同情景其余题的平均相似度（本情景只有 1 题时无同伴）
        peer_sim = float((En[peers] @ En[i]).mean()) if len(peers) else None
        sims = {t: float(En[i] @ c) for t, c in cents.items() if len(idx_by_scene[t]) >= 3}
        own_c = sims.get(s)
        others = {t: v for t, v in sims.items() if t != s}
        best_other = max(others.items(), key=lambda x: x[1]) if others else (None, None)
        rows.append({
            "order": o, "facet": items[str(o)]["facet"], "scene": s,
            "text_zh": items[str(o)]["text_zh"], "free_label": items[str(o)]["free_label"],
            "sim_own_centroid": round(own_c, 4) if own_c is not None else None,
            "sim_peer_mean": round(peer_sim, 4) if peer_sim is not None else None,
            "best_other_scene": best_other[0],
            "sim_best_other": round(best_other[1], 4) if best_other[1] is not None else None,
            "margin": round(best_other[1] - own_c, 4)
                     if (best_other[1] is not None and own_c is not None) else None,
        })

    # 可疑度：margin 越大越可疑（另一个情景明显比本情景更像）
    rows.sort(key=lambda r: -(r["margin"] if r["margin"] is not None else -9))
    payload = {
        "method": "bge-large-zh-v1.5 余弦相似度；margin = 最近的其他情景质心 − 本情景质心",
        "note": "margin > 0 意味着「另一个情景比本情景更像它」，是重分配的候选",
        "n_margin_positive": sum(1 for r in rows if (r["margin"] or -9) > 0),
        "items": rows,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)

    print(f"\nmargin > 0（另一个情景更像它）的题：{payload['n_margin_positive']} / 300")
    print("\n=== 可疑度最高的 40 题 ===")
    print(f"{'序':>4} {'当前情景':<12}{'它更像':<12}{'margin':>8}  题面")
    print("-" * 88)
    for r in rows[:40]:
        print(f"{r['order']:>4} {r['scene']:<12}{r['best_other_scene'] or '':<12}"
              f"{(r['margin'] or 0):>8.3f}  {r['text_zh'][:34]}")
    print(f"\nwrote {os.path.relpath(OUT, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
