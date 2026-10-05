#!/usr/bin/env python3
"""测绘：现有数据能否支撑「结构化文本」的 4 个字段 + 推断所需参数。

用户要求的结构化文本字段
========================
  ① 题文原文            （en）
  ② 提问本地化翻译       （zh）
  ③ 选项程度的完整情景说明 （**新内容**：每个选项到底意味着什么）
  ④ 其它需要提醒的注释文案 （注意事项）

本脚本查清每套量表现在**已有什么**、**缺什么**，为定 schema 与派工提供依据。
"""

from __future__ import annotations

import io
import json
import os
import sys
from collections import Counter

sys.path.insert(0, r"C:\Codes\emohealth-20260930-full\emohealth\tools")
from _root import find_root  # noqa: E402
ROOT = str(find_root())
INST = os.path.join(ROOT, "data", "instruments")


def load(fn):
    return json.load(io.open(os.path.join(INST, fn), encoding="utf-8"))


print("=" * 74)
print("一、各量表包的题目字段（决定 ① ② ③ ④ 已有哪些）")
print("=" * 74)
keys_seen = Counter()
opts_by_code = {}
for fn in sorted(os.listdir(INST)):
    if not fn.endswith(".json") or fn == "catalog.json":
        continue
    d = load(fn)
    items = d.get("items") or []
    ks = Counter()
    with_opts = 0
    for it in items:
        ks.update(it.keys())
        if it.get("options"):
            with_opts += 1
    keys_seen.update(ks)
    opts_by_code[d["instrument"]] = (len(items), with_opts,
                                     bool(d.get("response_options")),
                                     bool(d.get("options_scale")))
    print(f"  {d['instrument']:26}{len(items):4} 题｜有 options {with_opts:4}"
          f"｜顶层 response_options {bool(d.get('response_options'))}")

print("\n  题目字段频次（全部量表合计）：")
for k, n in keys_seen.most_common(20):
    print(f"    {k:26}{n}")

print()
print("=" * 74)
print("二、选项长什么样（抽 3 套看结构）")
print("=" * 74)
for code, fn in (("PID-5", "pid-5.json"), ("DSM5TR-L2-Mania", "dsm5tr-l2-mania.json"),
                 ("DSM5TR-L1", "dsm5tr-l1.json")):
    p = os.path.join(INST, fn)
    if not os.path.exists(p):
        continue
    d = load(fn)
    print(f"\n--- {code}")
    for k in ("response_options", "options_scale", "options", "anchors"):
        if k in d:
            print(f"  顶层 {k}: {json.dumps(d[k], ensure_ascii=False)[:220]}")
    for it in (d.get("items") or [])[:2]:
        print(f"  题 {it.get('id')}: text={str(it.get('text'))[:56]}")
        for k in ("options", "options_evidence", "kind"):
            if k in it:
                print(f"     {k}: {json.dumps(it[k], ensure_ascii=False)[:180]}")

print()
print("=" * 74)
print("三、文本库字段（能否提供 ① ②）")
print("=" * 74)
db = json.load(io.open(os.path.join(ROOT, "data", "text-db", "text-db.json"),
                       encoding="utf-8"))
e0 = next(iter(db["entries"].values()))
print(f"  条目字段：{sorted(e0.keys())}")
print(f"  样例：{json.dumps({k: (str(v)[:60] if v else v) for k, v in e0.items()}, ensure_ascii=False)}")

print()
print("=" * 74)
print("四、推断所需参数（能否支撑「事实预测 + 置信度」）")
print("=" * 74)
INF = os.path.join(ROOT, "data", "inference")
for fn in sorted(os.listdir(INF)):
    d = json.load(io.open(os.path.join(INF, fn), encoding="utf-8"))
    print(f"  {fn:16} level={d.get('level'):11} "
          f"pairB64={'有' if d.get('pairB64') else '无'} "
          f"item_dim_corr={len(d.get('item_dim_corr') or {})} 题 "
          f"dim_ceiling={len(d.get('dim_ceiling') or {})} 维 "
          f"ratio={d.get('ceiling_ratio')} "
          f"partial={'有' if d.get('partial') else '无'}")

print("\n  === 已有文献报告 / 统计文档 ===")
for sub in ("research",):
    for fn in sorted(os.listdir(os.path.join(ROOT, sub))):
        p = os.path.join(ROOT, sub, fn)
        if os.path.isfile(p) and fn.endswith(".md"):
            print(f"    {sub}/{fn}  ({os.path.getsize(p) // 1024} KB)")
