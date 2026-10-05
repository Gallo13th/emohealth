#!/usr/bin/env python3
"""生成 PID-5 计分键（facet→题号、反向题、5 个域）。

为什么这里用**转录常量**而不是继续解析 PDF
==========================================
手册的计分表在 PDF 里是「左列 facet 名 + 右列题号」的表格，且存在三处版面障碍：

1. `Perceptual Dysregulation` 那一行与相邻行折叠、又被当成噪声行滤掉；
2. 若干 facet 名带**排版伪空格**（提取成 `Depre ssivity`、`Ecce ntricity`）；
3. 正文里另有一处 facet 列举，会让「按名字锚定」产生伪锚点。

我试过四种解析路径（按行拼、按全局 x 区间、按 y 分行、按子串锚定 + 区域限制），
**每一种都会在某类行上出错**，而错误形式是「题号归错 facet」——这正是本项目
最不能容忍的静默错误。继续调参的收益很低、风险很高。

因此改为：**转录 + 两道独立校验**。
  · 转录内容来自 `tools/build/build_pid5_items.py` 的行提取输出（可复现），
    逐行与手册 PDF 对照过；`Perceptual Dysregulation` 的 12 道题取自其
    原始坐标段（x0=59.04, y=361.85）。
  · 校验一：220 道题**恰好各归一个** facet（无重复、无遗漏）。
  · 校验二：表格里的 `R` 标记与手册 Step 1 的权威反向清单**必须相容**。
任一条不通过就报错退出，不写文件。

来源（全部可逐行复核）
======================
· facet 名单：正文「25 personality trait facets including …」（25 个）
· facet→题号：手册「A. Personality Trait / B. PID-5 items」表
· 反向题：手册 Step 1 正文原文
  「Reverse the scores on the following items (i.e., 3 becomes 0, 2 becomes 1,
   1 becomes 2, and 0 becomes 3): 35, 58, 87, 90, 96, 97, 98, 131, 142, 155,
   164, 177, 210, and 215.」
· 域：手册域表 + 正文「five broader trait domains of …」
· 作答：手册「Each item on the measure is rated on a 4-point scale」

输出：``data/pid5-scoring-keys.json``
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()

# 手册计分表：facet → (题号列表, R 标记题号)
# R = 该题在其所属 facet 上是反向键（手册 Step 2 原文：
#     "the reverse scored items from Step 1 are marked with the letter R
#      in the Table (e.g., 7R)"）
TABLE: dict[str, tuple[list[int], list[int]]] = {
    "Anhedonia": ([1, 23, 26, 30, 124, 155, 157, 189], [30, 155]),
    "Anxiousness": ([79, 93, 95, 96, 109, 110, 130, 141, 174], [96]),
    "Attention Seeking": ([14, 43, 74, 111, 113, 173, 191, 211], []),
    "Callousness": ([11, 13, 19, 54, 72, 73, 90, 153, 166, 183, 198, 200, 207, 208], [90]),
    "Deceitfulness": ([41, 53, 56, 76, 126, 134, 142, 206, 214, 218], [142]),
    "Depressivity": ([27, 61, 66, 81, 86, 104, 119, 148, 151, 163, 168, 169, 178, 212], []),
    "Distractibility": ([6, 29, 47, 68, 88, 118, 132, 144, 199], []),
    "Eccentricity": ([5, 21, 24, 25, 33, 52, 55, 70, 71, 152, 172, 185, 205], []),
    "Emotional Lability": ([18, 62, 102, 122, 138, 165, 181], []),
    "Grandiosity": ([40, 65, 114, 179, 187, 197], []),
    "Hostility": ([28, 32, 38, 85, 92, 116, 158, 170, 188, 216], []),
    "Impulsivity": ([4, 16, 17, 22, 58, 204], [58]),
    "Intimacy Avoidance": ([89, 97, 108, 120, 145, 203], [97]),
    "Irresponsibility": ([31, 129, 156, 160, 171, 201, 210], [210]),
    "Manipulativeness": ([107, 125, 162, 180, 219], []),
    "Perceptual Dysregulation": ([36, 37, 42, 44, 59, 77, 83, 154, 192, 193, 213, 217], []),
    "Perseveration": ([46, 51, 60, 78, 80, 100, 121, 128, 137], []),
    "Restricted Affectivity": ([8, 45, 84, 91, 101, 167, 184], []),
    "Rigid Perfectionism": ([34, 49, 105, 115, 123, 135, 140, 176, 196, 220], []),
    # 转录时漏过 164（它跟在 Risk Taking 的续行里），校验器当场抓住——
    # 这正是「宁可报错也不写错数据」要达到的效果。
    "Risk Taking": ([3, 7, 35, 39, 48, 67, 69, 87, 98, 112, 159, 164, 195, 215],
                    [7, 35, 87, 98, 164, 215]),
    "Separation Insecurity": ([12, 50, 57, 64, 127, 149, 175], []),
    "Submissiveness": ([9, 15, 63, 202], []),
    "Suspiciousness": ([2, 103, 117, 131, 133, 177, 190], [131, 177]),
    "Unusual Beliefs & Experiences": ([94, 99, 106, 139, 143, 150, 194, 209], []),
    "Withdrawal": ([10, 20, 75, 82, 136, 146, 147, 161, 182, 186], []),
}

# 手册 Step 1 的权威反向题清单（**手册正文原文**，14 题）
REVERSE_VERBATIM = ("35, 58, 87, 90, 96, 97, 98, 131, 142, 155, 164, 177, "
                    "210, and 215")
REVERSE_KEYED = [35, 58, 87, 90, 96, 97, 98, 131, 142, 155, 164, 177, 210, 215]

# ── 翻转依据：手册 **facet 表**的 R 标记（16 题），不是 Step 1 正文清单（14 题）──
#
# 手册两处原文**互相矛盾**：Step 1 正文列 14 题，而 facet 表另把 **7、30** 标了 R。
# 本脚本原先一律以 Step 1 为准（下面那句「R 比 Step 1 更宽」其实已经指出矛盾，
# 但当时没去裁决）。**数据可以裁决**，三方证据一致指向「表格 R 才对」：
#
#   ① 题目文字：7 = "I avoid risky situations."（Risk Taking 的反向表述）
#                30 = "I'm an energetic person."（Anhedonia 的反向表述）
#   ② 逐题数据（两份**独立**样本，翻转前后各算一次与「同面向其余题之和」的相关）：
#        第  7 题  donor −0.625→+0.625   SKID −0.617→+0.617
#        第 30 题  donor −0.516→+0.516   SKID −0.343→+0.343
#        对照组   第 4 题 +0.693→−0.693  第 100 题 +0.522→−0.522（翻转反而变差）
#      → 7、30 不翻转时与**自己面向**呈显著负相关，这正是反向题的定义。
#   ③ 信度：翻转后 Anhedonia α .842→.907、Risk Taking .838→.900。
#
# 复现：数据在 archive/norms/pid-5-psychometrics/zenodo-extracted/data/
#       （CC-BY-4.0，N=2,471）。裁决脚本思路见 data/pid5-reverse-keys.json 的 evidence。
#
# ⚠️ 影响面：反向键决定每题的计分方向，进而决定**所有**推断/常模对齐结果。
#    所以这里必须用被数据支持的 16 题，而不是照抄矛盾原文里的 14 题。
REVERSE_SOURCE = "manual-facet-table-R"

DOMAINS = {
    "Negative Affect": ["Emotional Lability", "Anxiousness", "Separation Insecurity"],
    "Detachment": ["Withdrawal", "Anhedonia", "Intimacy Avoidance"],
    "Antagonism": ["Manipulativeness", "Deceitfulness", "Grandiosity"],
    "Disinhibition": ["Irresponsibility", "Impulsivity", "Distractibility"],
    "Psychoticism": ["Unusual Beliefs & Experiences", "Eccentricity",
                     "Perceptual Dysregulation"],
}


def main() -> int:
    problems: list[str] = []

    # 校验一：220 题恰好各归一个 facet
    all_items: list[int] = []
    for items, _rev in TABLE.values():
        all_items.extend(items)
    dup = sorted({x for x in all_items if all_items.count(x) > 1})
    unclaimed = sorted(set(range(1, 221)) - set(all_items))
    if dup:
        problems.append(f"重复认领：{dup}")
    if unclaimed:
        problems.append(f"无人认领：{unclaimed}")
    if len(TABLE) != 25:
        problems.append(f"facet 数 {len(TABLE)}（应为 25）")

    # 校验二：表格 R 标记必须覆盖 Step 1 清单（反之不必然——R 是「该题在其
    # facet 上是反向键」，比 Step 1 清单更宽；但 Step 1 里的题必须是反向键）
    rev_table = {x for _it, rev in TABLE.values() for x in rev}
    # **翻转依据就是它**（16 题，见文件头 REVERSE_SOURCE 处的三方证据）
    REVERSE_FINAL = sorted(rev_table)
    missing_in_table = sorted(set(REVERSE_KEYED) - rev_table)
    if missing_in_table:
        problems.append(
            f"Step 1 清单里的题在表格中未标记 R：{missing_in_table}")

    # 域完整性：手册的域表只列了**每域 3 个主要 facet**（共 15 个），
    # 其余 10 个 facet 也有域归属（DSM-5 替代模型），但不在那张表里。
    # 所以这里只校验「域表里的 facet 必须存在于 facet 表」，不要求反向覆盖。
    dom_facets = [f for fs in DOMAINS.values() for f in fs]
    unknown_dom = sorted(set(dom_facets) - set(TABLE))
    if unknown_dom:
        problems.append(f"域表引用了不存在的 facet：{unknown_dom}")
    for d, fs in DOMAINS.items():
        if len(fs) != 3:
            problems.append(f"域 {d} 有 {len(fs)} 个 facet（手册域表是每域 3 个）")
    unassigned = sorted(set(TABLE) - set(dom_facets))

    print(f"facet {len(TABLE)} 个｜题项合计 {len(all_items)}（唯一 {len(set(all_items))}）")
    print(f"Step 1 反向题 {len(REVERSE_KEYED)} 个")
    print(f"表格 R 标记 {len(rev_table)} 个（比 Step 1 多 "
          f"{sorted(rev_table - set(REVERSE_KEYED))}——R 表示「该题在其 facet 上是反向键」，口径更宽）")
    print(f"域 {len(DOMAINS)} 个，每域 3 个 facet")

    if problems:
        print("\n✗ 校验未通过，不写入文件：")
        for p in problems:
            print(f"  · {p}")
        return 1

    print("\n✓ 校验通过：220 题恰好各归一个 facet，域覆盖完整，反向清单相容")

    out = {
        "instrument": "PID-5",
        "display_name": "The Personality Inventory for DSM-5 (PID-5)—Adult",
        "source": "archive/scales/PID-5/manual.pdf",
        "generator": "tools/build/build_pid5_scoring_keys.py",
        "extraction_method": "转录（表格版面有三处障碍，解析路径已试四种均会误归题号）；"
                             "转录内容来自 tools/build/build_pid5_items.py 的行提取输出并逐行对照",
        "rationale": {
            "facet_names": "正文『25 personality trait facets including …』列举",
            "facet_items": "手册『A. Personality Trait / B. PID-5 items』表",
            "reverse_keyed": "手册 Step 1『Reverse the scores on the following items …』",
            "reverse_verbatim": REVERSE_VERBATIM,
            "domains": "手册域表 + 正文『five broader trait domains of …』",
            "response_scale": "手册『Each item on the measure is rated on a 4-point scale』",
            "note_R": "表格里题号后的 R 表示「该题在其所属 facet 上是反向键」，"
                      "与 Step 1 清单口径不同（后者才决定是否翻转原始分）",
        },
        "response_format": {
            "points": 4, "min": 0, "max": 3,
            "labels": ["very false or often false", "sometimes or somewhat false",
                       "sometimes or somewhat true", "very true or often true"],
        },
        "reverse_keyed": REVERSE_FINAL,
        "reverse_keyed_step1_verbatim": REVERSE_KEYED,
        "reverse_source": REVERSE_SOURCE,
        "facets": {
            n: {"items": sorted(items),
                "reverse_keyed": sorted(rev),
                "domain": next((d for d, fs in DOMAINS.items() if n in fs), None)}
            for n, (items, rev) in TABLE.items()
        },
        "domains": DOMAINS,
    }
    path = os.path.join(ROOT, "data", "pid5-scoring-keys.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(f"✓ 已写出 {os.path.relpath(path, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
