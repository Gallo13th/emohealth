#!/usr/bin/env python3
"""列出「还没中译的条目」落在哪些批次里，供补跑。

背景：92 批是按优先级顺序导出的，只有前面一部分跑完了。
与其重跑全部，不如精确找出**还缺的条目属于哪几批**，只补那几批。
"""

import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
db = json.load(open(os.path.join(ROOT, "data", "text-db", "text-db.json"),
                    encoding="utf-8"))
E = db["entries"]
missing = {k for k, e in E.items() if not e.get("zh")}
print(f"还缺中译 {len(missing)} 条\n")

per_batch = {}
for p in sorted(glob.glob(os.path.join(ROOT, "data/text-db/pending/batch-*.json"))):
    src = json.load(open(p, encoding="utf-8"))
    # ⚠️ 形态不保证：正常情况下是 {items: [...]}，但有个别批次文件被写成了
    #    裸列表。两种都要能吃，否则整个诊断脚本会崩在一批上。
    rows = src.get("items") if isinstance(src, dict) else src
    if not isinstance(rows, list):
        print(f"  ⚠ {os.path.basename(p)}: 形态异常（{type(src).__name__}），跳过")
        continue
    tier = src.get("tier") if isinstance(src, dict) else None
    keys = {x.get("key") for x in rows if isinstance(x, dict)}
    miss = keys & missing
    if miss:
        per_batch[os.path.basename(p)] = (
            len(miss), tier,
            sorted({((x.get("instruments") or ["?"])[0])
                    for x in rows if isinstance(x, dict) and x.get("key") in miss}))
print(f"涉及 {len(per_batch)} 批：")
for b, (n, tier, insts) in sorted(per_batch.items()):
    print(f"  {b}  tier{tier}  缺 {n:2}/25  {','.join(insts)[:64]}")

# 检查是否有条目不在任何批次里（说明导出口径漏了）
allkeys = set()
for p in glob.glob(os.path.join(ROOT, "data/text-db/pending/batch-*.json")):
    src = json.load(open(p, encoding="utf-8"))
    rows = src.get("items") if isinstance(src, dict) else src
    if isinstance(rows, list):
        allkeys |= {x.get("key") for x in rows if isinstance(x, dict)}
orphan = missing - allkeys
print(f"\n不在任何批次里的缺失条目：{len(orphan)}")
for k in sorted(orphan)[:6]:
    print(f"  {k[:80]!r}  {E[k].get('instruments')}")
