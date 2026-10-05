#!/usr/bin/env python3
"""按**重要性**给待译条目排序并分批，支持分组增量翻译。

为什么要按重要性排
==================
2583 条待译里，价值差别很大：

  ① **有常模、有临床意义的完整工具**（PID-5、HEXACO、CAT-PD、VIA、16PF、
     DSM-5-TR 各册）—— 用户真的会用，中文必须准确
  ② **IPIP 派生的短量表** —— 复用率高、单条价值低
  ③ **杂项/娱乐性量表** —— 最低优先

一次翻不完就先翻 ①，这样任何时刻停下来，已翻的都是最该翻的。

同时把每批缩小到 25 条：批次小、单批失败的影响面就小，
而且结果体量小到能直接读回，不必依赖超长输出。
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
DB = os.path.join(ROOT, "data", "text-db", "text-db.json")
OUT_DIR = os.path.join(ROOT, "data", "text-db", "pending")
BATCH = 25

# 优先级 ①：完整、有常模或临床意义的工具（按此顺序先译）
TIER1 = [
    "PID-5", "IPIP-HEXACO", "IPIP-CATPD", "IPIP-VIA", "IPIP-16PF",
    "DSM5TR-L1", "DSM5TR-L2-Anger", "DSM5TR-L2-Anxiety", "DSM5TR-L2-Depression",
    "DSM5TR-L2-Mania", "DSM5TR-L2-Repetitive", "DSM5TR-L2-Sleep",
    "DSM5TR-L2-Somatic", "DSM5TR-L2-Substance",
    "IPIP-NEO", "IPIP-BFAS", "IPIP-Big5-100", "IPIP-Big5-50", "IPIP-EI",
    "PCI", "DASSY", "CESD", "DISS", "SMS", "SVDS", "PAS", "PCOPE", "EWS",
    "SRS", "PROCR", "RNSS", "TSES", "AIDEP", "ADAK22",
]
TIER1_SET = {c.upper() for c in TIER1}


def norm(t: str) -> str:
    s = (t or "").replace("\u2019", "'").replace("\u2018", "'")
    s = s.replace("\u201c", '"').replace("\u201d", '"')
    s = s.replace("-", " ").replace("\u2013", " ").replace("\u2014", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return re.sub(r"[.\s]+$", "", s).lower()


def tier_of(instruments: list[str]) -> int:
    ups = {i.upper() for i in instruments}
    if ups & TIER1_SET:
        return 1
    if any(i.upper().startswith("IPIP") for i in instruments):
        return 2
    return 3


def main() -> int:
    db = json.load(open(DB, encoding="utf-8"))
    entries = db["entries"]

    # 维度名上下文
    ctx: dict[str, str] = {}
    for p in sorted(glob.glob(os.path.join(ROOT, "data", "instruments", "*.json"))):
        if os.path.basename(p) == "catalog.json":
            continue
        d = json.load(open(p, encoding="utf-8"))
        dims = {x["id"]: x.get("name") or x["id"] for x in d["dimensions"]}
        for it in d["items"]:
            k = norm(it["text"])
            if k in entries and k not in ctx:
                dim = (it.get("dimensions") or [None])[0]
                ctx[k] = dims.get(dim) or (dim or "")

    pending = [(k, e) for k, e in entries.items() if not e.get("zh")]
    print(f"待译 {len(pending)} 条")

    ordered = sorted(
        pending,
        key=lambda kv: (tier_of(kv[1].get("instruments") or []),
                        (kv[1].get("instruments") or ["zzz"])[0], kv[0]))
    from collections import Counter
    print("按优先级：", dict(Counter(tier_of(e.get("instruments") or [])
                                    for _k, e in ordered)))

    for f in glob.glob(os.path.join(OUT_DIR, "batch-*.json")):
        os.remove(f)
    os.makedirs(OUT_DIR, exist_ok=True)

    batches = []
    for i in range(0, len(ordered), BATCH):
        chunk = ordered[i:i + BATCH]
        name = f"batch-{i // BATCH:03d}.json"
        rows = [{"key": k, "en": e["en"],
                 "instruments": (e.get("instruments") or [])[:4],
                 "context": ctx.get(k, "")} for k, e in chunk]
        with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8") as fh:
            json.dump({"batch": i // BATCH, "count": len(rows),
                       "tier": tier_of(chunk[0][1].get("instruments") or []),
                       "items": rows}, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
        batches.append({"file": name, "count": len(rows),
                        "tier": tier_of(chunk[0][1].get("instruments") or []),
                        "instruments": sorted({(r["instruments"] or ["?"])[0]
                                               for r in rows})[:5]})

    with open(os.path.join(OUT_DIR, "index.json"), "w", encoding="utf-8") as fh:
        json.dump({"total_pending": len(pending), "batch_size": BATCH,
                   "batches": batches}, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(f"导出 {len(batches)} 批（每批 {BATCH} 条）")
    for b in batches[:8]:
        print(f"  {b['file']} tier{b['tier']}  {b['count']:3} 条  "
              f"{','.join(b['instruments'])[:64]}")
    print("  …")
    print(f"批次清单 → data/text-db/pending/index.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
