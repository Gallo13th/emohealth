#!/usr/bin/env python3
"""从 DSM-5-TR Level 1 成人册提取 23 道题与 13 个症状域。

手册结构（实测）
================
* 流 2 是**题项区**：先一段 Instructions to Clinicians，然后是 13 个域的题。
  题号 1..23，域用罗马数字标（I. II. III. … XIII.），域的**名称不在题项区**，
  而在正文那句「consists of 23 questions that assess 13 psychiatric domains,
  including depression, anger, mania, anxiety, somatic symptoms, suicidal
  ideation, psychosis, sleep problems, memory, repetitive thoughts and
  behaviors, dissociation, personality functioning, and substance use.」
* 作答：0=None/Not at all、1=Slight/Rare, less than a day or two、
  2=Mild/Several days、3=Moderate/More than half the days、4=Severe/Nearly every day
* 计分（手册 Instructions to Clinicians 原文）：**每个域的分数 = 该域内题目的最高分**
  （不是求和）。另有「如任一项 ≥2，询问影响程度」的提示。

提取方式：题号 → 题干；罗马数字给出域的边界；域名从正文列举按序对应。
校验：题号 1..23 连续、每题非空、域数 13、域名与正文列举一致。
"""

from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
sys.path.insert(0, os.path.join(ROOT, "tools"))
from pdftext import PdfDoc, layout_lines  # noqa: E402

# 手册正文列举的 13 个域（顺序即域 I..XIII 的顺序）
DOMAIN_NAMES = [
    "Depression", "Anger", "Mania", "Anxiety", "Somatic Symptoms",
    "Suicidal Ideation", "Psychosis", "Sleep Problems", "Memory",
    "Repetitive Thoughts and Behaviors", "Dissociation",
    "Personality Functioning", "Substance Use",
]

ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7,
         "VIII": 8, "IX": 9, "X": 10, "XI": 11, "XII": 12, "XIII": 13}

SCALE = {
    "min": 0, "max": 4, "points": 5,
    "labels": ["None / Not at all", "Slight / Rare, less than a day or two",
               "Mild / Several days", "Moderate / More than half the days",
               "Severe / Nearly every day"],
    "window": "past TWO (2) WEEKS",
}


def item_stream_text(pdf: str) -> tuple[str, str]:
    """返回 (题项区文字, 说明区文字)。

    实测：**题项区是不含「Instructions to Clinicians」的那一流**（流 1），
    说明区含该标题（流 2）。我第一版把「含 Instructions to Clinicians」当成
    题项区的判据，方向正好反了，于是永远找不到题（0 道）。

    ⚠️ **页脚必须剔除**（2026-10-04 修）。页脚是**独立的一行**：
        `Copyright © 2013 American Psychiatric Association. All Rights Reserved.`
        `This material can be reproduced without permission by researchers …`
    它和题项同处一个内容流，`" ".join(rows)` 会把它拼到**最后一题**的末尾——
    实测第 23 题的题面末尾因此挂上了整条授权声明（**错误内容混进题面**，
    用户作答时会读到）。所以这里按行的语义剔除页脚，而不是事后正则擦。
    """
    doc = PdfDoc.load(pdf)
    items_text, note_text = "", ""
    for runs in doc.text_runs():
        rows = [r["text"] for r in layout_lines(runs) if r["text"].strip()]
        rows = [t for t in rows if not _is_footer(t)]
        joined = re.sub(r"\s+", " ", " ".join(rows))
        if "Instructions to Clinicians" in joined:
            if len(joined) > len(note_text):
                note_text = joined
        elif "Little interest" in joined and len(joined) > len(items_text):
            items_text = joined
    return items_text, note_text


FOOTER_MARKERS = ("Copyright ©", "All Rights Reserved",
                  "This material can be reproduced")


def _is_footer(text: str) -> bool:
    return any(m in text for m in FOOTER_MARKERS)


def extract(pdf: str) -> tuple[list[dict], list[dict], list[str]]:
    text, note = item_stream_text(pdf)
    problems: list[str] = []

    # 域名齐全性：用**已知的 13 个名字**在正文列举里核对。
    # ⚠️ 不能按 " and " 拆——"Repetitive thoughts and behaviors" 里就有 and，
    #    拆开会得到 14 个（实测）。
    listed = [n for n in DOMAIN_NAMES if n.lower() in note.lower()]

    # 题项区：从第一个罗马数字标记开始
    start = re.search(r"\bI\.\s*\d", text)
    body = text[start.start():] if start else text

    # 按题号切段。实测两种形态：
    #   · 每个域的**第一题**带罗马数字：`I.1.Little interest…`
    #   · 同域内的后续题**不带**罗马数字：`2.Feeling down,…`
    # 所以标记写成「可选罗马数字 + 题号 + .」。漏掉后者会只拿到 13 题（每域首题）。
    marks = []
    for m in re.finditer(
            r"(?:(?<![A-Za-z])(XIII|XII|XI|IX|VIII|VII|VI|IV|V|III|II|X|I)[.\s]*)?"
            r"(\d{1,2})\s*\.(?=\s*[A-Z(])", body):
        roman, num = m.group(1), int(m.group(2))
        # 只接受「罗马数字+题号」或「起首题号」；其余数字（选项 01234 等）跳过
        if roman or m.start() == 0 or not body[max(0, m.start() - 1)].isalnum():
            marks.append((m, roman, num))
    items: list[dict] = []
    domains: list[dict] = []
    for i, (mk, roman, num) in enumerate(marks):
        dom = ROMAN.get(roman) if roman else None
        end = marks[i + 1][0].start() if i + 1 < len(marks) else len(body)
        seg = body[mk.end():end]
        # 题干切到「选项数字 01234」或「Part B / 影响调查」为止。
        head, rest = re.split(r"(?:\b0\s*1\s*2\s*3\s*4\b)", seg, maxsplit=1)[:2] \
            if re.search(r"\b0\s*1\s*2\s*3\s*4\b", seg) else (seg, "")
        # ⚠️ 折行续接：题文在 PDF 里会折行，而**选项数字出现在折行之前**，例如
        #      「18.Feeling detached or distant from yourself, yourbody, yourphysical
        #        01234 surroundings, or yourmemories?」
        #    只取选项数字之前的部分就会把句子拦腰截断——实测 9 道题这样丢了后半句。
        #    所以数字之后、下一个题号之前的那一段，属于**本题的续文**，要接回来。
        if rest:
            tail = re.split(r"(?:\bPART\b|How much have these)", rest)[0]
            tail = re.sub(r"\s+", " ", tail).strip(" .;:")
            if len(tail) > 1:
                head = head.rstrip() + " " + tail
        t = re.sub(r"\s+", " ", head).strip(" .;:")
        if num != len(items) + 1:
            problems.append(f"题号不连续：期望 {len(items) + 1}，得到 {num}")
        items.append({"order": num, "dom": dom, "text": t})

    # 域的归属：题号按序落入 13 个域；带罗马数字的题开启新域
    cur_dom = None
    for it in items:
        if it["dom"]:
            cur_dom = it["dom"]
        it["dom"] = cur_dom

    for d in range(1, 14):
        members = [it["order"] for it in items if it["dom"] == d]
        domains.append({"index": d, "name": DOMAIN_NAMES[d - 1] if d <= len(DOMAIN_NAMES) else f"Domain {d}",
                        "items": members})

    if len(items) != 23:
        problems.append(f"题数 {len(items)}（应为 23）")
    for it in items:
        t = it["text"]
        if len(t) < 6:
            problems.append(f"第 {it['order']} 题题干过短：{t!r}")
        # ── 防复发（2026-10-04）──
        # 三条例外情形都在真实数据里出现过，必须**在提取时就报错**，
        # 而不是等界面/文档里看到才发现：
        if any(m in t for m in FOOTER_MARKERS):
            problems.append(f"第 {it['order']} 题混入页脚授权句：{t[-60:]!r}")
        if t.count("[") != t.count("]"):
            problems.append(f"第 {it['order']} 题方括号不配对（题面被截断）：{t[-60:]!r}")
        if not t.endswith("?"):
            problems.append(f"第 {it['order']} 题不以问号结尾（疑似截断）：{t[-60:]!r}")
    if len(listed) != 13:
        problems.append(f"正文列举的域名 {len(listed)} 个（应为 13）：{listed}")
    return items, domains, problems


def main() -> int:
    pdf = os.path.join(ROOT, "archive", "scales", "DSM5TR-L1", "manual.pdf")
    items, domains, problems = extract(pdf)
    print(f"题项 {len(items)} 道，域 {len(domains)} 个")
    for p in problems[:10]:
        print(f"  ✗ {p}")
    print()
    for d in domains:
        print(f"  域 {d['index']:2} {d['name']:32} 题 {d['items']}")
        for o in d["items"]:
            t = next(x["text"] for x in items if x["order"] == o)
            print(f"        {o:2}. {t[:84]}")

    out = os.path.join(ROOT, "archive", "scales", "DSM5TR-L1", "items-extracted.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({
            "source_pdf": "archive/scales/DSM5TR-L1/manual.pdf",
            "extractor": "tools/build/build_l1_items.py",
            "response_format": SCALE,
            "scoring_rule": "每个域的分数 = 该域内题目的**最高分**（手册 Instructions to "
                            "Clinicians）；任一项 ≥2 时询问影响程度",
            "domains": domains,
            "items": items,
            "problems": problems,
        }, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(f"\n已写出 {os.path.relpath(out, ROOT)}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
