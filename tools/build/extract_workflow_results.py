#!/usr/bin/env python3
"""从 workflow 的 spill 输出里抠出翻译结果，存成 merge_translations.py 能吃的 JSON。

为什么需要这一步：58 批的结果太长，工具输出被存成了「格式化后的文本」
（含 ``Return value:`` 前缀），不是纯 JSON。所以这里按前缀定位，再把后面的
JSON 数组解析出来——**不猜、不截断**，解析失败就明确报错。
"""

from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
OUT = os.path.join(ROOT, "data", "text-db", "translation-results.json")


def main() -> int:
    if len(sys.argv) < 2:
        print("用法：python tools/build/extract_workflow_results.py <spill.txt>")
        return 2
    raw = open(sys.argv[1], encoding="utf-8", errors="replace").read()
    print(f"spill 文件 {len(raw)} 字符")

    i = raw.find("Return value:")
    if i < 0:
        print("✗ 找不到 'Return value:' 标记")
        return 1
    body = raw[i + len("Return value:"):]
    # 数组起点
    j = body.find("[")
    if j < 0:
        print("✗ 标记后没有 JSON 数组")
        return 1
    # 用 JSONDecoder.raw_decode 从头解析，天然处理嵌套与转义。
    # ⚠️ spill 文件可能被**截断**（实测只留了前 50 KB，末尾有
    #    "… [truncated: N more characters]"），所以解析失败不能直接判死：
    #    退化为「逐个对象扫描」，把能完整解析的批次收下，其余如实报出来。
    dec = json.JSONDecoder()
    src = body[j:].lstrip()
    truncated = "truncated:" in src[-400:] or "[status:" in src[-200:]
    if truncated:
        print(f"⚠ 输出被截断（末尾有截断标记），改为逐个对象扫描")
        data = []
        pos = 0
        while True:
            k = src.find('{"batch"', pos)
            if k < 0:
                break
            try:
                obj, end = dec.raw_decode(src[k:])
            except json.JSONDecodeError:
                print(f"  在偏移 {k} 处遇到不完整对象，停止扫描")
                break
            data.append(obj)
            pos = k + end
    else:
        try:
            data, end = dec.raw_decode(src)
        except json.JSONDecodeError as exc:
            print(f"✗ JSON 解析失败：{exc}")
            print(f"   出错位置附近：{src[max(0, exc.pos - 80):exc.pos + 80]!r}")
            return 1
    if not isinstance(data, list):
        print(f"✗ 顶层不是数组，而是 {type(data).__name__}")
        return 1
    print(f"解析出 {len(data)} 个批次结果")
    ok = [d for d in data if isinstance(d, dict) and "batch" in d and "raw" in d]
    print(f"  形态正确 {len(ok)} 个")
    bad = [d for d in data if d not in ok]
    if bad:
        print(f"  形态异常 {len(bad)} 个：{str(bad[0])[:120]}")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(ok, fh, ensure_ascii=False)
    print(f"✓ 已写出 {os.path.relpath(OUT, ROOT)}"
          f"（{os.path.getsize(OUT) / 1024:.0f} KB）")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
