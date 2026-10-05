#!/usr/bin/env python3
"""把算好的常模挂进 IPIP-NEO-300 量表包，并给全部量表标注「有无常模」。

两件事
======
1. ``data/instruments/ipip-neo.json`` 补上 ``norms`` 字段（面向与域的百分位表）。
   来源与口径都从 ``data/norms/ipip-neo-300.json`` 带过来，界面上显示的
   每个百分位都能追到该文件与它的 sha256。

2. 给**每一套**量表包写 ``norms_status``：``available`` / ``none``，
   并注明原因。这是「界面每个数字可追到出处」的延伸——
   **没有常模时也要说清楚没有**，而不是让用户以为分数有参照系。
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
NORMS_DIR = os.path.join(ROOT, "data", "norms")

# ⚠️ 常模文件里写的 ``instrument`` 是**量表全名**（"IPIP-NEO-300"），
#    而量表包的 ``instrument`` 是归档 code（"IPIP-NEO"）。两者对不上会导致
#    常模静默挂不上（我第一版就是这样：342 套全部被标成「无常模」）。
#    所以用显式映射，不靠字符串猜。
NORMS_TO_CODE = {
    "IPIP-NEO-300": "IPIP-NEO",
}


def main() -> int:
    # 已算好的常模：文件名 → 常模数据
    # ⚠️ 必须跳过「描述层常模记录」（``data/norms/<code>.json``，由
    #    tools/build/build_descriptions.py 生成）。它们有的只是**缺失声明**
    #    （status=unavailable、没有 ``n``），照原样读会 KeyError；有的虽是
    #    available，但只有维度均值/标准差摘要、没有可挂载的百分位表，
    #    若被当成常模挂上去，界面会**静默少掉百分位**。判据用显式字段
    #    ``record_kind``，不靠「有没有 n」猜。
    have = {}
    skipped: list[str] = []
    for p in sorted(glob.glob(os.path.join(NORMS_DIR, "*.json"))):
        d = json.load(open(p, encoding="utf-8"))
        if d.get("record_kind") == "descriptions_norms" or not isinstance(d.get("n"), int):
            skipped.append(os.path.basename(p))
            continue
        code = NORMS_TO_CODE.get(d["instrument"], d["instrument"])
        d["_norms_file"] = os.path.basename(p)
        have[code] = d
    if skipped:
        print(f"跳过描述层常模记录 {len(skipped)} 个（不是可挂载的细表）："
              f"{'、'.join(skipped)}")
    print(f"已有常模的量表：{len(have)} 套")
    for c, d in have.items():
        print(f"  {c:14} ← {d['_norms_file']}（n={d['n']}）")
    print()

    files = [p for p in sorted(glob.glob(
        os.path.join(ROOT, "data", "instruments", "*.json")))
        if os.path.basename(p) != "catalog.json"]

    attached = 0
    for p in files:
        d = json.load(open(p, encoding="utf-8"))
        code = d["instrument"]
        if code in have:
            n = have[code]
            # 两种常模结构都要支持：
            #   · IPIP-NEO 形态：`facets`/`domains` 里各带 `percentiles` 表
            #   · PID-5 形态：**条件常模**（按性别×年龄分层），逐 raw 给百分位
            #     —— 结构与前者不同，硬套会让界面查不到。所以按存在性带字段。
            entry = {
                "source": n["source"],
                "source_files": n["source_files"],
                "n": n["n"],
                "n_note": n.get("n_note", ""),
                "unit": n["unit"],
                "percentile_method": n["percentile_method"],
                "scale_range": n["scale_range"],
                "license": n.get("license", ""),
            }
            for k in ("domain_unit", "reverse_transform", "validation"):
                if k in n:
                    entry[k] = n[k]
            if "facets" in n:
                entry["facets"] = n["facets"]
                entry["facet_names"] = n.get("facet_names", {})
                entry["domains"] = n["domains"]
            if "scales" in n:
                entry["scales"] = n["scales"]
                entry["scale_names"] = n.get("scale_names", {})
                entry["cells"] = n.get("cells", [])
                entry["conditional"] = True
            d["norms"] = entry
            d["norms_status"] = {
                "available": True,
                "n": n["n"],
                "note": n.get("n_note") or f"常模来自 {n['source']}",
                "file": f"data/norms/{n['_norms_file']}",
                "conditional": bool(n.get("cells")),
                "method": n.get("percentile_method", ""),
            }
            attached += 1
        else:
            # 没有常模就明说。原因分两种，别混为一谈：
            #   · 短量表（题量少、多为题库条目簇）本来就没有独立常模
            #   · 其余是归档里确实没找到可溯源的常模数据
            n_items = len(d["items"])
            d["norms_status"] = {
                "available": False,
                "note": ("本项目暂无该量表的可溯源常模数据——界面只显示原始分，"
                         "不显示百分位，也不提供「高于/低于常人」的判断"),
                "reason": ("该量表题量较少（题库条目簇），通常没有独立常模"
                           if n_items < 20 else
                           "归档中未找到可溯源的常模"),
            }
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(d, fh, ensure_ascii=False, indent=1)
            fh.write("\n")

    print(f"量表 {len(files)} 套：挂上常模 {attached} 套，标注「无常模」{len(files) - attached} 套")
    return 0


if __name__ == "__main__":
    sys.exit(main())
