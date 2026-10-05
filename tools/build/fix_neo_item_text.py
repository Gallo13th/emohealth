#!/usr/bin/env python3
"""用项目权威产物校正 IPIP-NEO 转换包里的题文（措辞变体 + 一处瑞典语）。

发现过程
========
核对常模兼容性时，按面向比题集发现 6 个面向各差 1–2 题。打印差异后看到两类：

  ① **措辞变体**（同一题的不同英文写法）：
       官方/权威 `Interested in many things.`  vs 转换 `Am interested in many things.`
       `Believe people should fend for themselves.` vs `…that people should…`
       `Do things I later regret.` vs `Do things that I later regret.`
       `Believe that there is no absolute right or wrong.` vs `…right and wrong.`

  ② **语言错误**（真缺陷）：
       转换 `Vill att allt ska vara precis rätt`（**瑞典语**）
       权威 `Want everything to be "just right."`

来源与依据
==========
修复来源用 ``data/ipip-neo-300.json``——它是本项目**已经人工核对过**的产物
（``build_log``/``validation``/``known_defects_repaired`` 字段），且与我这边
独立核出的 148 道反向题完全一致。所以它是可信的英文题文基准，不用再去找新来源。

⚠️ 只改这 7 道题的 ``text``，不动题号、面向归属、计分方向。
改完由 ``tools/check/verify_norms_item_alignment.py`` 复验面向题集是否逐一对齐。
"""

from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
CANON = os.path.join(ROOT, "data", "ipip-neo-300.json")
INST = os.path.join(ROOT, "data", "instruments", "ipip-neo.json")


def norm(s: str) -> str:
    s = s.lower().replace("\u2019", "'").replace("\u2018", "'")
    s = re.sub(r"[^a-z0-9' ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def main() -> int:
    canon = json.load(open(CANON, encoding="utf-8"))
    inst = json.load(open(INST, encoding="utf-8"))

    # 权威产物：面向 → {归一化题文: 原题文}
    by_facet: dict[str, dict[str, str]] = {}
    for it in canon["items"]:
        by_facet.setdefault(it["facet"], {})[norm(it["text"])] = it["text"]

    fixed = []
    for it in inst["items"]:
        fid = it["dimensions"][0]
        pool = by_facet.get(fid, {})
        if not pool:
            continue
        if norm(it["text"]) in pool:
            continue
        # 该面向里找出「一道权威有、而本包没有」的题；按剩余差集处理
        mine = {norm(x["text"]) for x in inst["items"]
                if x["dimensions"] and x["dimensions"][0] == fid}
        missing = [v for k, v in pool.items() if k not in mine]
        if len(missing) == 1:
            old = it["text"]
            it["text"] = missing[0]
            fixed.append((fid, it["order"], old, missing[0]))
            mine = {norm(x["text"]) for x in inst["items"]
                    if x["dimensions"] and x["dimensions"][0] == fid}

    print(f"校正题文 {len(fixed)} 处：")
    for fid, order, old, new in fixed:
        kind = "语言错误" if re.search(r"\b(vill|att|och|inte|ska|vara)\b", old, re.I) \
            else "措辞变体"
        print(f"  [{kind}] {fid} 第 {order} 题")
        print(f"      旧: {old[:70]}")
        print(f"      新: {new[:70]}")

    # ⚠️ 上面的逻辑一次只补「差集恰好为 1」的面向。``liberalism`` 同时有
    #    **两处**措辞变体（差集为 2），所以单独处理——按归一化题文建立等价关系。
    EQUIV = {
        "liberalism": {
            norm("Believe that there is no absolute right and wrong."):
                'Believe that there is no absolute right or wrong.',
            norm("Believe that laws should be strictly enforced."):
                'Believe laws should be strictly enforced.',
        },
    }
    for it in inst["items"]:
        fid = it["dimensions"][0]
        table = EQUIV.get(fid)
        if not table:
            continue
        new = table.get(norm(it["text"]))
        if new and new != it["text"]:
            fixed.append((fid, it["order"], it["text"], new))
            print(f"  [措辞变体·成对] {fid} 第 {it['order']} 题")
            print(f"      旧: {it['text'][:70]}")
            print(f"      新: {new[:70]}")
            it["text"] = new

    if not fixed:
        print("（没有需要校正的题）")
        return 0

    # 记录修订，保持可追
    rev = inst.setdefault("_revisions", [])
    rev.append({
        "at": "2026-10-03",
        "tool": "tools/build/fix_neo_item_text.py",
        "change": f"按权威产物 data/ipip-neo-300.json 校正 {len(fixed)} 道题的题文",
        "reason": "其中 1 道是瑞典语翻译串（真缺陷），6 道是措辞变体；"
                  "权威产物已人工核对，且与独立核出的 148 道反向题一致",
        "items": [{"facet": f, "order": o, "old": a, "new": b}
                  for f, o, a, b in fixed],
    })
    with open(INST, "w", encoding="utf-8") as fh:
        json.dump(inst, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(f"\n已写回 {os.path.relpath(INST, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
