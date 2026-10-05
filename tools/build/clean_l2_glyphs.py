#!/usr/bin/env python3
"""把 Level 2 各册已提取数据里的「选择框」残留字符清掉（就地重写）。

背景
====
PDF 里的选项框在提取后会留下**私有区字形**（实测是 U+F071，Wingdings 的 ❑），
有时还有千分号 ‰（U+2030）。它们本该在提取阶段就被去掉，但两批提取器
（``build_l2_items.py`` 与 ``build_l2_items_rest.py``）各自只清了一部分：

  · Mania 的选项文字里挂着 ``❑``（出图核对时看到）
  · Somatic 的 15 道题干尾部各挂着 3 个 ``❑``（本脚本的检查器发现）

两处是**同一个 bug 的两个实例**。所以这里做一次统一清理，并把它做成
可重复运行的步骤；``tools/check/check_l2_glyphs.py`` 负责在清理后验证。

⚠️ 只改题面与选项的**文本字段**，不动题号、选项分值、授权等任何结构化信息。
"""

from __future__ import annotations

import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()

# 选择框字形：私有区（Wingdings/Webdings）、千分号、各类方框符号
BOX = str.maketrans({})


def clean(s: str) -> str:
    out = []
    for ch in s:
        o = ord(ch)
        if 0xE000 <= o <= 0xF8FF or o in (0x2030, 0x25A1, 0x2610, 0x2611, 0x2612):
            out.append(" ")
        else:
            out.append(ch)
    import re
    return re.sub(r"\s+", " ", "".join(out)).strip(" .;:·•-")


def main() -> int:
    files = sorted(glob.glob(os.path.join(ROOT, "archive", "scales",
                                          "DSM5TR-L2-*", "items-extracted.json")))
    changed_total = 0
    for p in files:
        code = os.path.basename(os.path.dirname(p))
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
        changed = 0
        for it in d["items"]:
            t = clean(it["text"])
            if t != it["text"]:
                it["text"] = t
                changed += 1
            for o in it.get("options", []):
                t2 = clean(o["text"])
                if t2 != o["text"]:
                    o["text"] = t2
                    changed += 1
        if changed:
            # 记录这次清理：派生数据被修正过，就要留下可追的痕迹。
            # （源 PDF 一个字节没动；派生提取物可由「源 PDF + 提取器」复现。）
            hist = d.setdefault("_revisions", [])
            hist.append({
                "at": "2026-10-03",
                "tool": "tools/build/clean_l2_glyphs.py",
                "change": f"清除题面/选项里残留的选择框字形（{changed} 处）",
                "reason": "PDF 选项框留下私有区字形 U+F071 等，在界面上显示为孤立方框",
                "source_pdf_unchanged": True,
            })
            with open(p, "w", encoding="utf-8") as fh:
                json.dump(d, fh, ensure_ascii=False, indent=1)
                fh.write("\n")
        print(f"  {code:24} 清理 {changed} 处")
        changed_total += changed
    print(f"\n合计清理 {changed_total} 处")
    return 0


if __name__ == "__main__":
    sys.exit(main())
