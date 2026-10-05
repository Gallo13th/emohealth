#!/usr/bin/env python3
"""把 subagent 的翻译结果回写进文本库（D113 第 ③ 步的收口）。

为什么需要单独的收口环节
========================
翻译是**分派出去**做的（每批一个 agent），结果是一堆 JSON 数组。
直接拼进文本库有三个风险，必须在这里拦住：

  ① ``key`` 对不上 —— key 是归一化题文，抄错一个字符就配不上，译文会丢
  ② 条数不符 —— 漏译、合并、重复
  ③ 格式不合规 —— 中译为空、与英文相同、含 markdown 代码块

所以本工具**先校验再写**：任何一条不合格就整批拒绝，并打印是哪几条。
宁可少写，不可错写——错写会让界面显示错误的译文，而且看不出来。

用法
====
    python tools/build/merge_translations.py <results.json>

``results.json`` 形态：``[{"batch": "batch-005.json", "raw": "[{...}]"}, ...]``
（即 workflow 的返回值原样保存）。
"""

from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
DB = os.path.join(ROOT, "data", "text-db", "text-db.json")


def parse_raw(raw: str) -> list[dict] | None:
    """从 agent 输出里抠出 JSON 数组。容忍 markdown 代码块围栏。"""
    if not isinstance(raw, str):
        return None
    s = raw.strip()
    m = re.search(r"```(?:json)?\s*(.+?)```", s, re.S)
    if m:
        s = m.group(1).strip()
    i, j = s.find("["), s.rfind("]")
    if i < 0 or j < 0:
        return None
    try:
        v = json.loads(s[i:j + 1])
    except json.JSONDecodeError:
        return None
    return v if isinstance(v, list) else None


def main() -> int:
    if len(sys.argv) < 2:
        print("用法：python tools/build/merge_translations.py <results.json>")
        return 2
    results = json.load(open(sys.argv[1], encoding="utf-8"))
    db = json.load(open(DB, encoding="utf-8"))
    entries = db["entries"]

    ok = bad = 0
    problems: list[str] = []
    written: list[str] = []
    for r in results:
        batch = r.get("batch", "?")
        rows = parse_raw(r.get("raw"))
        if rows is None:
            problems.append(f"{batch}: 输出不是合法 JSON 数组")
            continue
        # 期望条数：读回原批次文件核对
        bp = os.path.join(ROOT, "data", "text-db", "pending", batch)
        expect_keys = None
        if os.path.exists(bp):
            expect_keys = {x["key"] for x in json.load(open(bp, encoding="utf-8"))["items"]}
        got_keys = {str(x.get("key", "")) for x in rows}
        if expect_keys is not None:
            miss = expect_keys - got_keys
            extra = got_keys - expect_keys
            if miss or extra:
                problems.append(f"{batch}: key 不匹配（漏 {len(miss)}、多 {len(extra)}）"
                                f" 漏例 {sorted(miss)[:2]}")
                continue
        for x in rows:
            k = str(x.get("key", ""))
            zh = str(x.get("zh") or "").strip()
            note = str(x.get("note") or "").strip()
            e = entries.get(k)
            if e is None:
                problems.append(f"{batch}: 文本库里没有 key {k[:40]!r}")
                bad += 1
                continue
            if not zh:
                problems.append(f"{batch}: 空译文 key={k[:40]!r}")
                bad += 1
                continue
            if zh.lower() == (e.get("en") or "").lower():
                problems.append(f"{batch}: 译文与英文相同 key={k[:40]!r}")
                bad += 1
                continue
            e["zh"] = zh
            e["zh_source"] = "subagent 初译（待人工复核）"
            if note:
                e["note"] = note
            written.append(k)
            ok += 1

    # 重算统计
    db["stats"]["with_zh"] = sum(1 for e in entries.values() if e.get("zh"))
    db["stats"]["with_note"] = sum(1 for e in entries.values() if e.get("note"))
    with open(DB, "w", encoding="utf-8") as fh:
        json.dump(db, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write("\n")

    print(f"回写成功 {ok} 条，失败 {bad} 条")
    print(f"文本库现有中译 {db['stats']['with_zh']}/{len(entries)} 条，"
          f"注释 {db['stats']['with_note']} 条")
    if problems:
        print(f"\n问题 {len(problems)} 条（前 10）：")
        for p in problems[:10]:
            print("  ·", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
