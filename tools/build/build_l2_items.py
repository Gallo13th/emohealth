#!/usr/bin/env python3
"""从 DSM-5-TR Level 2 各册提取题项与作答格式。

8 册的形态**互不相同**（实测）：

| 册 | 题数 | 作答 | 备注 |
|---|---|---|---|
| Anger / Anxiety / Depression | 5 / 7 / 8 | 1–5（Never…Always） | PROMIS，形态一致 |
| Sleep | 8 | 1–5，但题 2/3/7/8 **反向**（"I was satisfied with my sleep"） | PROMIS |
| Somatic | 15 | 0–2（Not bothered…a lot） | 改编自公有领域 PHQ-15 |
| Mania | 5 组 | 每组一句 0–4 的**选项组** | 不是 Likert 单题 |
| Repetitive | 4 | 每题**各自的 0–4 标签**（时间/苦恼/控制/回避） | Severity 量表 |
| Substance | — | 频率量表 | NIDA-Modified ASSIST |

所以提取器按「题号切题 + 剔除选项框数字」的通用规则走，
**作答格式逐册登记**（不做跨册推断——那正是会出错的地方）。

输出：``archive/scales/<code>/items-extracted.json``
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
sys.path.insert(0, os.path.join(ROOT, "tools"))
from pdftext import PdfDoc, layout_lines  # noqa: E402

# 逐册登记：作答格式 + 期望题数 + 反向题（都来自各册正文）
REGISTRY: dict[str, dict] = {
    "DSM5TR-L2-Anger": {
        "items": 5, "min": 1, "max": 5,
        "labels": ["Never", "Rarely", "Sometimes", "Often", "Always"],
        "reverse": [], "window": "past SEVEN (7) DAYS",
        "dimension": "Anger",
    },
    "DSM5TR-L2-Anxiety": {
        "items": 7, "min": 1, "max": 5,
        "labels": ["Never", "Rarely", "Sometimes", "Often", "Always"],
        "reverse": [], "window": "past SEVEN (7) DAYS",
        "dimension": "Anxiety",
    },
    "DSM5TR-L2-Depression": {
        "items": 8, "min": 1, "max": 5,
        "labels": ["Never", "Rarely", "Sometimes", "Often", "Always"],
        "reverse": [], "window": "past SEVEN (7) DAYS",
        "dimension": "Depression",
    },
    "DSM5TR-L2-Sleep": {
        "items": 8, "min": 1, "max": 5,
        "labels": ["Not at all", "A little bit", "Somewhat", "Quite a bit", "Very much"],
        # 题 2「I was satisfied with my sleep」、3「My sleep was refreshing」、
        # 7「I got enough sleep」、8「My sleep quality was...」在册内按 5→1 排布，
        # 即**高分表示睡得好**，与其余题方向相反。
        "reverse": [2, 3, 7, 8], "window": "past SEVEN (7) DAYS",
        "dimension": "Sleep Disturbance",
        # ⚠️ 第 8 题的**锚点与其他题不同**（其余题用 Not at all…Very much，
        #    第 8 题用 Very Poor…Very good，且册内按 5→1 排布）。不登记它，
        #    该题就只有光秃秃的题干 "My sleep quality was"，用户不知道该对什么评分
        #    ——2026-10-04 定为缺陷②。
        "per_item_options": {
            8: [("Very Poor", 5), ("Poor", 4), ("Fair", 3),
                ("Good", 2), ("Very good", 1)],
        },
        "per_item_options_evidence":
            "手册第 8 题上方一行原文：`Very Poor Poor Fair Good Very good`；"
            "该题 5 个框按 `5 4 3 2 1` 排布（5=Very Poor … 1=Very good）",
    },
    "DSM5TR-L2-Somatic": {
        "items": 15, "min": 0, "max": 2,
        "labels": ["Not bothered at all", "Bothered a little", "Bothered a lot"],
        "reverse": [], "window": "past 7 days",
        "dimension": "Somatic Symptom",
    },
}


def item_region(pdf: str) -> str:
    """取含题项的最小内容流文字。"""
    doc = PdfDoc.load(pdf)
    best, score = "", 0
    for runs in doc.text_runs():
        rows = [r["text"] for r in layout_lines(runs) if r["text"].strip()]
        j = re.sub(r"\s+", " ", " ".join(rows))
        n = len(re.findall(r"(?<![\d.])\d{1,2}\s*\.\s*[A-Z(]", j))
        if n > score:
            best, score = j, n
    return best


# 「选择框」字形集合：私有区（Wingdings/Webdings 的 ❑）、千分号 ‰、
# 各种方框（U+25A1/2610/2611/2612/2751/2752），以及**所有控制字符**。
# 控制字符必须在内：睡眠册的框是 `\x00‰` 两字符组合，漏掉就会留在题面里。
BOX_CHARS = (set(range(0x00, 0x20))
             | {0x2030, 0x25A1, 0x2610, 0x2611, 0x2612, 0x2751, 0x2752})


def strip_options(t: str) -> str:
    """去掉题干后面的选项框数字与表格尾注。

    实测选项框不止一种字形：正文里的 ``❑`` 是**私有区 U+F071**，而睡眠册
    用的是 ``‰``（U+2030）；另外躯体册的选项框没有可提取的字形，只剩空白
    （表现为 ``Stomach pain   ``）。所以清理要覆盖三类：
      ① 私有区/方框/千分号等「框形」字符
      ② 紧跟在框形字符后的选项数字
      ③ 尾部仅剩的空白与残留括号碎片
    """
    # ① + ②：框形字符与数字成组去掉（含无数字的情况）
    t = re.sub(r"[\ue000-\uf8ff\u2030\u25a1\u2610\u2611\u2612\u25cb\u25a0\s]*"
               r"(?:[0-9][\ue000-\uf8ff\u2030\u25a1\u2610\u2611\u2612\u25cb\u25a0\s]*)+",
               " ", t)
    # ③ 尾注截断
    t = re.split(r"Total/Partial Raw Score|Prorated Total|T-Score|©", t)[0]
    t = re.sub(r"\b(Item|Score|Clinician Use|In the past SEVEN)\b.*$", "", t)
    # ④ 残留的孤立括号碎片（如 "periods WOMEN ONLY" 前的空括号）
    t = re.sub(r"\(\s*\)", " ", t)
    # ⑤ 兜底：任何残留的「选择框」字形。**控制字符也要清**——睡眠册第 1/5 题的
    #    框是 `\x00‰` 这种两字符组合，只清私有区会留下 `\x00`，实测题面变成
    #    `My sleep was restless. \x00 \x00 \x00 \x00`（缺陷③，2026-10-04）。
    t = "".join(" " if (0xE000 <= ord(c) <= 0xF8FF or ord(c) in BOX_CHARS) else c
                for c in t)
    return re.sub(r"\s+", " ", t).strip(" .;:·•-")


def extract(code: str, cfg: dict) -> tuple[list[dict], list[str]]:
    pdf = os.path.join(ROOT, "archive", "scales", code, "manual.pdf")
    text = item_region(pdf)
    problems: list[str] = []

    marks = list(re.finditer(r"(?<![\d.])(\d{1,2})\s*\.\s*(?=[A-Z(])", text))
    # 只保留题号递增的候选（后面的 1./2. 常是说明步骤或选项组）
    items: list[dict] = []
    for i, m in enumerate(marks):
        num = int(m.group(1))
        if num != len(items) + 1:
            continue
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        seg = text[m.end():end]
        t = strip_options(seg)
        if len(t) < 4:
            continue
        items.append({"order": num, "text": t})
        if num == cfg["items"]:
            break

    if len(items) != cfg["items"]:
        problems.append(f"题数 {len(items)}（登记为 {cfg['items']}）")

    # ── 逐题锚点（目前只有睡眠册第 8 题）──
    # 登记的是「手册里逐字出现的锚点词」，所以先在手册正文里验一遍，
    # 验不过就报问题——避免把凭印象写的锚点当成原文。
    for order, pairs in (cfg.get("per_item_options") or {}).items():
        for word, _v in pairs:
            if word.lower() not in text.lower():
                problems.append(f"第 {order} 题的锚点 {word!r} 在手册正文里找不到")
        for it in items:
            if it["order"] == order:
                it["options"] = [{"v": v, "text": w} for w, v in pairs]
                it["options_evidence"] = cfg.get("per_item_options_evidence", "")

    for it in items:
        if len(it["text"]) < 6:
            problems.append(f"第 {it['order']} 题过短：{it['text']!r}")
        if re.search(r"\bItem\b|\bScore\b|Total/Partial", it["text"]):
            problems.append(f"第 {it['order']} 题混入表格文字：{it['text'][:60]!r}")
        # ── 防复发（2026-10-04）──
        if any(m in it["text"] for m in ("Copyright ©", "All Rights Reserved",
                                         "This material can be reproduced")):
            problems.append(f"第 {it['order']} 题混入页脚授权句：{it['text'][-60:]!r}")
        if any(ord(c) < 0x20 for c in it["text"]):
            problems.append(f"第 {it['order']} 题残留控制字符：{it['text']!r}")
    return items, problems


def main() -> int:
    only = sys.argv[1:] or list(REGISTRY)
    total_problems = 0
    for code in only:
        cfg = REGISTRY[code]
        items, problems = extract(code, cfg)
        flag = "✓" if not problems else "✗"
        print(f"{flag} {code:24} {len(items):3}/{cfg['items']} 题")
        for p in problems[:4]:
            print(f"      {p}")
        for it in items:
            print(f"      {it['order']:2}. {it['text'][:78]}")
        total_problems += len(problems)
        out = os.path.join(ROOT, "archive", "scales", code, "items-extracted.json")
        with open(out, "w", encoding="utf-8") as fh:
            json.dump({
                "source_pdf": f"archive/scales/{code}/manual.pdf",
                "extractor": "tools/build/build_l2_items.py",
                "response_format": {"points": cfg["max"] - cfg["min"] + 1,
                                    "min": cfg["min"], "max": cfg["max"],
                                    "labels": cfg["labels"]},
                "reverse_keyed": cfg["reverse"],
                "window": cfg["window"],
                "dimension": cfg["dimension"],
                "items": items,
                "problems": problems,
            }, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
        print()
    print(f"问题合计 {total_problems}")
    return 1 if total_problems else 0


if __name__ == "__main__":
    sys.exit(main())
