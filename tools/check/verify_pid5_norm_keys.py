#!/usr/bin/env python3
"""核对 PID-5 常模里的量表标识与量表包里的维度名能否对上。

对不上就会**静默失效**：界面查不到常模 → 百分位列全空，而且不报错。
我在 IPIP-NEO 上已经踩过一次（面向 id vs 显示名），所以这里先核。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
n = json.load(open(os.path.join(ROOT, "data", "norms", "pid-5.json"),
                   encoding="utf-8"))
inst = json.load(open(os.path.join(ROOT, "data", "instruments", "pid-5.json"),
                      encoding="utf-8"))

norm_scales = set(n["scales"])
dims = inst["dimensions"]
print(f"常模里 {len(norm_scales)} 个量表标识：")
print("  " + ", ".join(sorted(norm_scales)))
print()
print(f"量表包 {len(dims)} 个维度（含域）：")
for d in dims:
    print(f"  id={d['id']:32} name={d['name']}")
print()

def key(s):
    return "".join(ch for ch in s.lower() if ch.isalnum())

norm_keys = {key(s): s for s in norm_scales}
print("=== 逐个维度匹配常模标识 ===")
hit = miss = 0
for d in dims:
    cands = [d["id"], d["name"]]
    got = next((norm_keys[key(c)] for c in cands if key(c) in norm_keys), None)
    if got:
        hit += 1
    else:
        miss += 1
        print(f"  ✗ {d['id']:32} name={d['name']}")
print(f"\n匹配 {hit}/{len(dims)}，未匹配 {miss}")
if miss:
    print("（未匹配的维度在界面上会显示不出百分位——需要映射或补数据）")
