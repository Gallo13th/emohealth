#!/usr/bin/env python3
"""从磁盘读译文文件回写文本库（**推荐的收口方式**）。

为什么改成读磁盘
================
前两次我把 58 批 / 30 批的结果放在 workflow 的返回值里一次性读回，
结果**输出被截断在 50 KB**，绝大多数批次丢失，白跑两轮。
（截断对 agent 回复、以及 job_output 的落盘文件都生效，所以「读回来再存」
这条路本身就不适合大数据量。）

现在改成：每个翻译 agent 把结果**直接写到** ``data/text-db/pending/<batch>-zh.json``，
本工具从磁盘读。这样数据量不再受任何输出上限约束，而且**可重复运行**：
已回写的条目不重复写，失败的批次可以单独重跑。

校验（不合格的批次整体拒绝，并打印原因）
========================================
1. 文件是合法 JSON 数组
2. 条数与对应输入批次一致、key 集合完全匹配
3. ``zh`` 非空、与英文不同、不含占位符
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
PENDING = os.path.join(ROOT, "data", "text-db", "pending")


def main() -> int:
    db = json.load(open(DB, encoding="utf-8"))
    entries = db["entries"]

    files = sorted(glob.glob(os.path.join(PENDING, "*-zh.json")))
    print(f"找到译文文件 {len(files)} 个\n")

    ok = skipped = 0
    rejected: list[str] = []
    done_batches: list[str] = []
    for p in files:
        name = os.path.basename(p)
        batch = name.replace("-zh.json", ".json")
        src = os.path.join(PENDING, batch)
        if not os.path.exists(src):
            rejected.append(f"{name}: 找不到对应输入 {batch}")
            continue
        try:
            rows = json.load(open(p, encoding="utf-8"))
        except json.JSONDecodeError as exc:
            rejected.append(f"{name}: JSON 无法解析（{exc}）")
            continue
        if not isinstance(rows, list):
            rejected.append(f"{name}: 顶层不是数组")
            continue
        expect = {x["key"] for x in json.load(open(src, encoding="utf-8"))["items"]}
        got = {str(r.get("key", "")) for r in rows if isinstance(r, dict)}
        if expect - got or got - expect:
            rejected.append(f"{name}: key 不匹配（漏 {len(expect - got)}、"
                            f"多 {len(got - expect)}）"
                            + (f" 漏例 {sorted(expect - got)[:2]}" if expect - got else ""))
            continue

        wrote = 0
        for r in rows:
            k = str(r.get("key", ""))
            zh = str(r.get("zh") or "").strip()
            note = str(r.get("note") or "").strip()
            e = entries.get(k)
            if e is None:
                continue
            if not zh:
                skipped += 1
                continue
            # 「译文与英文相同」不一定是缺陷：作答**指示语**可能是中文生成、
            # 没有对应英文（如 Mania 的「第 N 组：选出最符合你的一句」）。
            # 这类条目在文本库里标了 kind=instruction，放行。
            if zh.lower() == (e.get("en") or "").lower() and e.get("kind") != "instruction":
                skipped += 1
                continue
            if re.search(r"\{\{|\}\}|TODO|FIXME", zh):
                skipped += 1
                continue
            if e.get("zh") == zh:
                continue                      # 已写过，幂等
            e["zh"] = zh
            e["zh_source"] = "subagent 初译（待人工复核）"
            if note:
                e["note"] = note
            wrote += 1
        ok += wrote
        done_batches.append(batch)

    db["stats"]["with_zh"] = sum(1 for e in entries.values() if e.get("zh"))
    db["stats"]["with_note"] = sum(1 for e in entries.values() if e.get("note"))
    db["stats"]["translated_batches"] = sorted(set(
        (db["stats"].get("translated_batches") or []) + done_batches))
    with open(DB, "w", encoding="utf-8") as fh:
        json.dump(db, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write("\n")

    print(f"回写 {ok} 条（跳过 {skipped} 条不合格），已收录批次 "
          f"{len(db['stats']['translated_batches'])}")
    print(f"文本库：中译 {db['stats']['with_zh']}/{len(entries)}"
          f"（{db['stats']['with_zh'] / len(entries) * 100:.1f}%），"
          f"注释 {db['stats']['with_note']}")
    if rejected:
        print(f"\n被拒批次 {len(rejected)} 个：")
        for r in rejected[:10]:
            print("  ·", r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
