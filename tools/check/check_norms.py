#!/usr/bin/env python3
"""核对新算的 IPIP-NEO-300 常模：数值合理性 + 与项目已有元数据对照。"""
import json
import os
import sys
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
n = json.load(open(os.path.join(ROOT, "data", "norms", "ipip-neo-300.json"),
                   encoding="utf-8"))
print(f"n={n['n']}｜面向 {len(n['facets'])}｜域 {len(n['domains'])}")
print(f"来源：{n['source']}\n")

print(f"{'面向':26} {'均值':>6} {'SD':>6} {'P10':>6} {'P50':>6} {'P90':>6}")
for f, v in sorted(n["facets"].items()):
    p = v["percentiles"]
    print(f"{f:26} {v['mean']:6.3f} {v['sd']:6.3f} {p['10']:6.3f} {p['50']:6.3f} {p['90']:6.3f}")

print(f"\n{'域':22} {'均值':>6} {'SD':>6} {'P10':>6} {'P50':>6} {'P90':>6}")
for d, v in sorted(n["domains"].items()):
    p = v["percentiles"]
    print(f"{d:22} {v['mean']:6.3f} {v['sd']:6.3f} {p['10']:6.3f} {p['50']:6.3f} {p['90']:6.3f}")

# 合理性：1–5 量表、均分，均值应落在 2–4；百分位必须单调
bad = []
for grp in ("facets", "domains"):
    for k, v in n[grp].items():
        if not (2.0 <= v["mean"] <= 4.0):
            bad.append(f"{grp}/{k} 均值 {v['mean']} 超出 2–4")
        ps = [v["percentiles"][str(i)] for i in range(1, 100)]
        if ps != sorted(ps):
            bad.append(f"{grp}/{k} 百分位不单调")
        if not (1.0 <= v["min"] <= v["max"] <= 5.0):
            bad.append(f"{grp}/{k} 取值范围异常 {v['min']}–{v['max']}")
print(f"\n合理性检查：{'✅ 全部通过' if not bad else '❌ ' + str(len(bad)) + ' 处'}")
for b in bad[:6]:
    print("  ", b)

# 与项目已有元数据里的样本量对照。
# ⚠️ 原先读 ui/emohealth-data.js（前端生成包）。检查层不应依赖前端产物，而且那是
#    **有损瘦身变换**后的包，`N=` 只是被搜出来的字符串。改为读**权威来源**
#    data/norms/ipip-neo-300.json 的 n / n_note（常模文件本来的字段）。
np = os.path.join(ROOT, "data", "norms", "ipip-neo-300.json")
if os.path.exists(np):
    nm = json.load(open(np, encoding="utf-8"))
    print(f"\n常模文件里的样本量：{nm.get('n')}")
    if nm.get("n_note"):
        print(f"  说明：{str(nm['n_note'])[:200]}")
    print(f"本次实际使用的有效作答：{n['n']:,}")
