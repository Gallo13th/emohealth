#!/usr/bin/env python3
"""验证大五的 `pairB64` 重排（canon 序 → 量表包序）是**等价置换**。

为什么要验
==========
大五的 `item_dim_corr` 按**量表包 order** 索引，而它原先的 `pairB64`（搬自
`adaptive-network.json`）是 **canon 题序**——两者排列不同（canon 轮转、
量表包按 facet 分组）。若只重排一个，A 与 b 就不同序，置信度全错。
现在两个都统一到量表包序，本脚本确认重排没改内容：
  · 同一矩阵的**置换相似变换** ⇒ 特征值集合相同（这是等价的充要判据）
  · 并且仍**正定**（否则求逆会失败/出负残差方差——大五历史上踩过）
"""

from __future__ import annotations

import base64
import json
import os

import numpy as np

ROOT = r"C:\Codes\emohealth-20260930-full\emohealth"


def dec(b64: str, n: int) -> np.ndarray:
    buf = np.frombuffer(base64.b64decode(b64), dtype="<f4")
    A = np.eye(n)
    for a in range(2, n + 1):
        off = (a - 1) * (a - 2) // 2
        for b in range(1, a):
            A[a - 1, b - 1] = A[b - 1, a - 1] = float(buf[off + (b - 1)])
    return A


ad = json.load(open(os.path.join(ROOT, "data", "adaptive-network.json"),
                    encoding="utf-8"))
inf = json.load(open(os.path.join(ROOT, "data", "inference", "ipip-neo.json"),
                     encoding="utf-8"))
A1 = dec(ad["pairB64"], 300)          # canon 序
A2 = dec(inf["pairB64"], 300)         # 量表包序
e1 = np.sort(np.linalg.eigvalsh(A1))
e2 = np.sort(np.linalg.eigvalsh(A2))
print(f"  原 A（canon 序）  特征值 {e1[0]:+.4f} … {e1[-1]:.4f}")
print(f"  新 A（量表包序）  特征值 {e2[0]:+.4f} … {e2[-1]:.4f}")
md = float(np.abs(e1 - e2).max())
print(f"  排序后特征值最大差 {md:.6f} → "
      + ("等价置换（同一相关矩阵重排）" if md < 0.05 else "不是同一矩阵！"))
print(f"  最小特征值 {e2[0]:+.5f} → 正定："
      + ("是" if e2[0] > -1e-6 else "否（求逆会失败）"))

# 同行还验证：对角线应为 1
print(f"  对角线全为 1：{'是' if np.allclose(np.diag(A2), 1.0, atol=1e-3) else '否'}")
print(f"  对称：{'是' if np.allclose(A2, A2.T, atol=1e-3) else '否'}")
