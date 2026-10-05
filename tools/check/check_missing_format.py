#!/usr/bin/env python3
"""检查哪些量表缺少作答格式信息（response_format）。

作答格式缺失的影响：界面画不出选项按钮，计分也无从换算。所以这类量表
要么补齐、要么不收录——不能带着「猜一个 1–5」进目录。
"""

import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()

missing = []
for p in sorted(glob.glob(os.path.join(ROOT, "data", "instruments", "*.json"))):
    if os.path.basename(p) == "catalog.json":
        continue
    d = json.load(open(p, encoding="utf-8"))
    rf_struct = (d.get("structure") or {}).get("response_format")
    rf_top = d.get("response_format")
    if not rf_struct and not rf_top:
        missing.append((os.path.basename(p), d["instrument"], len(d["items"]),
                        (d.get("structure") or {}).get("source", "")[:60]))

print(f"缺作答格式的量表 {len(missing)} 套\n")
for f, code, n, src in missing:
    print(f"  {f:34} {code:14} {n:3} 题")
    print(f"      来源字段: {src}")

# 对有问题的两套，看看原始 OSD 里有什么线索
for f, code, n, _src in missing:
    d = json.load(open(os.path.join(ROOT, "data", "instruments", f), encoding="utf-8"))
    print(f"\n── {code} ──")
    print("  display_name:", d.get("display_name", "")[:80])
    print("  前 3 题:", [x["text"][:44] for x in d["items"][:3]])
    print("  维度:", [x["name"] for x in d["dimensions"]][:6])
