#!/usr/bin/env python3
"""翻译结果落盘读取器：从 workflow 输出里按批提取并立刻回写文本库。

为什么要有这个「边跑边收」的通道
================================
第一次跑 58 批时，我把所有结果放在一个返回值里读回来——结果**输出太长，
只保留了前 50 KB**，绝大多数批次丢失，白跑一遍。

现在改成：workflow 每批的 raw 都带 ``batch`` 字段，落盘后由本工具**逐批**处理，
每批独立校验、独立回写。任何一批失败都不影响其它批次，
而且可以重复运行（已回写的条目不重复写）。
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


def parse_raw(raw) -> list[dict] | None:
    if isinstance(raw, list):
        return raw
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


def collect(obj, out: list, depth: int = 0) -> None:
    """在任意嵌套结构里找 {batch, raw} 对。"""
    if depth > 8:
        return
    if isinstance(obj, dict):
        if "batch" in obj and "raw" in obj:
            out.append(obj)
            return
        for v in obj.values():
            collect(v, out, depth + 1)
    elif isinstance(obj, list):
        for v in obj:
            collect(v, out, depth + 1)


def main() -> int:
    if len(sys.argv) < 2:
        print("用法：python tools/build/collect_translations.py <workflow输出.txt>")
        return 2
    raw = open(sys.argv[1], encoding="utf-8", errors="replace").read()
    # 抠 JSON
    i = raw.find("Return value:")
    body = raw[i + len("Return value:"):] if i >= 0 else raw
    pairs: list[dict] = []
    dec = json.JSONDecoder()
    j = body.find("{")
    if j >= 0:
        try:
            obj, _ = dec.raw_decode(body[j:].lstrip())
            collect(obj, pairs)
        except json.JSONDecodeError as exc:
            print(f"⚠ 整体解析失败（{exc}），改用逐个对象扫描")
            pairs = []
    if not pairs:
        pos = 0
        while True:
            k = body.find('{\\"batch\\"', pos)
            if k < 0:
                k = body.find('{"batch"', pos)
            if k < 0:
                break
            seg = body[k:]
            seg = seg.replace('\\"', '"').replace("\\n", "\n")
            try:
                obj, end = dec.raw_decode(seg)
            except json.JSONDecodeError:
                pos = k + 8
                continue
            collect(obj, pairs)
            pos = k + end

    uniq: dict[str, dict] = {}
    for p in pairs:
        uniq[str(p.get("batch"))] = p
    print(f"收到 {len(pairs)} 个批次对象，去重后 {len(uniq)} 个")

    db = json.load(open(DB, encoding="utf-8"))
    entries = db["entries"]
    ok = rej = 0
    rejected: list[str] = []
    for b, p in sorted(uniq.items()):
        rows = parse_raw(p.get("raw"))
        if rows is None:
            rejected.append(f"{b}: raw 不是合法 JSON 数组")
            continue
        bp = os.path.join(ROOT, "data", "text-db", "pending", b)
        expect = None
        if os.path.exists(bp):
            expect = {x["key"] for x in json.load(open(bp, encoding="utf-8"))["items"]}
        got = {str(r.get("key", "")) for r in rows if isinstance(r, dict)}
        if expect is not None and (expect - got or got - expect):
            rejected.append(f"{b}: key 不匹配（漏 {len(expect - got)}、"
                            f"多 {len(got - expect)}）")
            continue
        for r in rows:
            k = str(r.get("key", ""))
            zh = str(r.get("zh") or "").strip()
            e = entries.get(k)
            if e is None or not zh:
                rej += 1
                continue
            if zh.lower() == (e.get("en") or "").lower():
                rej += 1
                continue
            e["zh"] = zh
            e["zh_source"] = "subagent 初译（待人工复核）"
            note = str(r.get("note") or "").strip()
            if note:
                e["note"] = note
            ok += 1

    db["stats"]["with_zh"] = sum(1 for e in entries.values() if e.get("zh"))
    db["stats"]["with_note"] = sum(1 for e in entries.values() if e.get("note"))
    with open(DB, "w", encoding="utf-8") as fh:
        json.dump(db, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write("\n")
    print(f"回写 {ok} 条，拒绝 {rej} 条")
    print(f"文本库中译 {db['stats']['with_zh']}/{len(entries)}，"
          f"注释 {db['stats']['with_note']}")
    if rejected:
        print(f"被拒批次 {len(rejected)} 个：")
        for r in rejected[:10]:
            print("  ·", r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
