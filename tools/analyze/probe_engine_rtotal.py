#!/usr/bin/env python3
"""直接用 `engine/inference.py` 实测：只答 1 题时它报的 `r_total` 是多少？

背景：审计（`tools/analyze/audit_rtotal_definition.py`）用**经验 OLS** 算出
「答 1 题时预测与完整分的相关」≈ **0.68**，而 `task-16` 的报告称 **0.9921**。
两者差 0.31，必须查清是**引擎错**还是**验证脚本口径不同**。
"""

from __future__ import annotations

import io
import json
import os
import sys

sys.path.insert(0, r"C:\Codes\emohealth-20260930-full\emohealth")
sys.path.insert(0, r"C:\Codes\emohealth-20260930-full\emohealth\tools")
from _root import find_root  # noqa: E402
ROOT = str(find_root())

from engine import inference as EI  # noqa: E402

inst = json.load(io.open(os.path.join(ROOT, "data", "instruments", "ipip-neo.json"),
                         encoding="utf-8"))
own = {d["id"]: d.get("items") or [] for d in inst["dimensions"]}
anx = own["anxiety"]
print(f"anxiety 题数 {len(anx)}；前 3 题 {anx[:3]}")

# 找一个可用的入口
print("\n=== engine.inference 的公开 API ===")
print([n for n in dir(EI) if not n.startswith("_")][:30])

# 尝试构造模型 + 预测
try:
    Model = getattr(EI, "InferenceModel", None) or getattr(EI, "Model", None)
    print(f"\nModel class = {Model}")
    if Model:
        print([n for n in dir(Model) if not n.startswith("_")][:30])
except Exception as e:                                        # noqa: BLE001
    print("查 API 失败：", e)
