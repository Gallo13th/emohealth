#!/usr/bin/env python3
"""从多个独立第三方来源提取 PROMIS 短表转换表，并**互证**。

调研方法
========
PROMIS 官方站点对本次网络环境一律返回错误，旧 URL 也已 404（站点改版）。
所以改用**多来源互证**：若 ≥2 个彼此独立的文献印出同一张转换表且数值一致，
即可作为采用依据（并在采用记录里写明「多来源一致，非官方原件」这一事实）。

已入档的来源
============
  · crosscheck-gla-2026-brock-phd.pdf      Glasgow 学位论文（2026）
  · crosscheck-sunnaas-2021-appendix.pdf   挪威 Sunnaas 医院论文在线附录（2021）
  · crosscheck-rimed-2021-appendix-a.pdf   RIMED 期刊附录 A（2021）

判据
====
把每个流的文本规范化，抽取「Raw → T（可带 SE）」三元组序列；
同一短表若在两个来源里出现 ≥N 组且数值**逐组相同**，记为一致。
数值不一致就如实报出——不一致意味着不能采用。
"""

from __future__ import annotations

import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
sys.path.insert(0, os.path.join(ROOT, "tools"))
from pdftext import PdfDoc, layout_lines  # noqa: E402

SRC = os.path.join(ROOT, "archive", "norms", "promis")
FILES = {
    "gla-2026": "crosscheck-gla-2026-brock-phd.pdf",
    "sunnaas-2021": "crosscheck-sunnaas-2021-appendix.pdf",
    "rimed-2021": "crosscheck-rimed-2021-appendix-a.pdf",
}

# 表标题里的短表名 → 规范名。
# ⚠️ 真实标题形如「Depression 8a -Adult v1.0 Short Form Conversion Table」——
#    中间夹着「-Adult v1.0」，所以表名与 "Conversion Table" 之间必须允许任意字符
#    （我第一版用 `[^A-Za-z]{0,40}` 只容许非字母，直接匹配不到）。
FORM_PAT = re.compile(
    r"(Depression|Anger|Anxiety|Sleep\s*Disturbance|Sleep)\s*[-–]?\s*(\d+)\s*a\b"
    r".{0,80}?Conversion Table", re.I | re.S)
TRIPLE = re.compile(r"\b(\d{1,2})\s+(\d{2}\.\d)\s+(\d\.\d)\b")
PAIR = re.compile(r"\b(\d{1,2})\s+(\d{2}\.\d)\b")


def streams(path: str) -> list[str]:
    """取每个文本流的规范化文字。

    ⚠️ pdftext 的 ``layout_lines`` 用 ``!`` 作为**行分隔符**，而 ``!`` 不是空白
    字符——所以 ``re.sub(r"\\s+", " ", ...)`` 之后行与行、列与列仍被 ``!`` 粘住，
    形如 ``Raw Score!T -Score!SE*! 8!38.2!5.7!``。数字之间的 ``\\s+`` 因此匹配不到，
    转换表会被判定为「未提取到」。必须把 ``!`` 一并当作分隔符。
    """
    doc = PdfDoc.load(path)
    out = []
    for runs in doc.text_runs():
        t = " ".join(r["text"] for r in layout_lines(runs))
        t = re.sub(r"[!\s]+", " ", t)
        out.append(t.strip())
    return out


def extract(path: str) -> dict[str, dict]:
    """返回 {规范名: {raw: (T, SE或None)}}。"""
    res: dict[str, dict] = defaultdict(dict)
    for t in streams(path):
        m = FORM_PAT.search(t)
        if not m:
            continue
        form = (m.group(1) + " " + m.group(2) + "a").replace("  ", " ")
        form = form.replace("Sleep Disturbance", "Sleep Disturbance")
        seg = t[m.end():m.end() + 3000]
        for raw, T, se in TRIPLE.findall(seg):
            res[form].setdefault(int(raw), (T, se))
        if not res[form]:
            for raw, T in PAIR.findall(seg):
                res[form].setdefault(int(raw), (T, None))
    return {k: v for k, v in res.items() if len(v) >= 5}


def main() -> int:
    got = {}
    for key, fn in FILES.items():
        p = os.path.join(SRC, fn)
        if not os.path.exists(p):
            print(f"  ✗ 缺 {fn}")
            continue
        got[key] = extract(p)
        forms = ", ".join(f"{k}({len(v)}点)" for k, v in got[key].items())
        print(f"  {key:14} 提取到：{forms or '（无）'}")

    print("\n=== 互证 ===")
    by_form: dict[str, dict[str, dict]] = defaultdict(dict)
    for src, tables in got.items():
        for form, tbl in tables.items():
            by_form[form][src] = tbl

    consistent, conflict, single = [], [], []
    for form, per_src in sorted(by_form.items()):
        if len(per_src) < 2:
            single.append((form, list(per_src)))
            continue
        names = list(per_src)
        base_name = names[0]
        agree = True
        for other in names[1:]:
            common = set(per_src[base_name]) & set(per_src[other])
            if not common:
                agree = False
                break
            diff = [r for r in common if per_src[base_name][r] != per_src[other][r]]
            if diff:
                agree = False
                print(f"  ✗ {form}: {base_name} 与 {other} 在 raw {diff[:4]} 上不一致")
                for r in diff[:3]:
                    print(f"       raw {r}: {per_src[base_name][r]} vs "
                          f"{per_src[other][r]}")
                break
        (consistent if agree else conflict).append(form)

    print(f"\n多来源一致：{consistent or '（无）'}")
    print(f"存在冲突：{conflict or '（无）'}")
    print(f"仅单一来源（不足以采用）：{single or '（无）'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
