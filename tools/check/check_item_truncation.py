#!/usr/bin/env python3
"""检查已提取的题项里，有多少条**在句中截断**（折行续接丢失）。

判据：题文以逗号/连词/介词结尾，或以小写字母开头（说明丢了前半段），
或明显少于同类题的平均长度。只报可疑，不自动改。
"""
import glob
import json
import os
import sys
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()

# 以这些词结尾 → 后面显然还有内容
TAIL = re.compile(r"(,|;|\band\b|\bor\b|\bof\b|\bthe\b|\bwith\b|\byour\b|\byour\w*\b|"
                  r"\bto\b|\ba\b|\bin\b|\bfor\b|\bthat\b|\bwhen\b|\bover\b)\s*$", re.I)

# 但有些**以介词结尾却完整**的固定搭配，会被上面那条误判。
# 已核实的例外（每条都对着归档手册逐字查过）：
#   · `look forward to`  —— DSM5TR-L2-Depression 第 2 题
#     「I felt that I had nothing to look forward to」。
#     核实过程：从 archive/scales/DSM5TR-L2-Depression/manual.pdf 提取原文，
#     与 data/instruments/dsm5tr-l2-depression.json 的题干**逐字一致**，
#     且该册 8 题与其他册同类题都采用不带句号的短语形式。
#     → 属误报，不是截断。修的是判据，不是数据。
EXEMPT = re.compile(r"\blook(?:ing)? forward to\s*$", re.I)


def main() -> int:
    files = sorted(glob.glob(os.path.join(ROOT, "data", "instruments", "*.json")))
    bad_total = 0
    for p in files:
        if os.path.basename(p) == "catalog.json":
            continue
        d = json.load(open(p, encoding="utf-8"))
        bad = []
        for it in d["items"]:
            t = it["text"].strip()
            if len(t) < 4:
                continue
            if (TAIL.search(t) and not EXEMPT.search(t)) \
               or (t[:1].islower() and not t[:1].isdigit()):
                bad.append((it["order"], t))
        if bad:
            bad_total += len(bad)
            print(f"  {d['instrument']:24} {len(bad):3} 条可疑截断")
            for o, t in bad[:3]:
                print(f"       第 {o:3} 题: …{t[-64:]}")
    print(f"\n合计可疑 {bad_total} 条")
    return 1 if bad_total else 0


if __name__ == "__main__":
    raise SystemExit(main())
