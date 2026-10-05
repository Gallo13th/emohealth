#!/usr/bin/env python3
"""扫描全部量表包，找出**非英文**题项（例如混进了瑞典语/德语翻译串）。

背景：核对 IPIP-NEO-300 常模兼容性时发现 ``orderliness`` 有一道题的正文是
``Vill att allt ska vara precis rätt``（瑞典语），而不是英文原题。
说明 ``IPIP-NEO.osd`` 的某个题文槽位存的是翻译串，转换器把它当成英文用了。

题面语言错了有两重危害：展示给用户看不懂；而且如果该题还参与计分，
分数仍然算得出来——**界面完全看不出异常**。所以要全库扫一遍。
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

# 各语言的常见功能词组合（出现 ≥2 个就高度可疑）
LANG_PATTERNS = {
    "sv": r"\b(att|och|inte|är|för|med|som|jag|vill|rätt|allt|har|kan|det)\b",
    "de": r"\b(und|nicht|ich|das|ist|mit|für|auf|eine|dass|werden)\b",
    "fr": r"\b(les|des|une|est|que|qui|pour|dans|avec|pas)\b",
    "es": r"\b(los|las|una|que|para|con|por|como|más|pero)\b",
    "nl": r"\b(het|een|niet|van|dat|met|voor|zijn|worden)\b",
    "fi": r"\b(ja|on|ei|se|että|kun|niin|kuin|myös)\b",
}


def main() -> int:
    files = sorted(glob.glob(os.path.join(ROOT, "data", "instruments", "*.json")))
    total_bad = 0
    affected = []
    for p in files:
        if os.path.basename(p) == "catalog.json":
            continue
        d = json.load(open(p, encoding="utf-8"))
        bad = []
        for it in d["items"]:
            t = it["text"]
            for lang, pat in LANG_PATTERNS.items():
                hits = re.findall(pat, t, re.I)
                words = len(re.findall(r"[A-Za-zÀ-ÿ']+", t))
                # ⚠️ 判据不能只看「功能词出现 ≥2 个」：英文句子里也会出现
                #    ``on``（芬兰语 ja/on/ei 里的 on）、``se``、``det`` 等短词。
                #    实测 AIDEP 第 14 题 "…I rely on AI instead of a…" 就被误判成芬兰语。
                #    所以加一条**比例**条件：功能词要占实词数的 18% 以上才算可疑。
                if len(hits) >= 2 and words and (len(hits) / words) >= 0.18:
                    bad.append((lang, it["order"], t, len(hits), words))
                    break
        if bad:
            affected.append(d["instrument"])
            total_bad += len(bad)
            print(f"  {d['instrument']:26} {len(bad):3} 题可疑")
            for lang, order, t, hn, wn in bad[:3]:
                print(f"       [{lang}] 第 {order} 题（功能词 {hn}/{wn} 词）: {t[:58]}")
    print(f"\n受影响量表 {len(affected)} 套，可疑题 {total_bad} 道")
    if affected:
        print("  " + ", ".join(affected[:12]))
    return 1 if total_bad else 0


if __name__ == "__main__":
    sys.exit(main())
