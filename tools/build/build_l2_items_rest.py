#!/usr/bin/env python3
"""提取 Level 2 剩余三册（Repetitive / Substance / Mania）的题项。

三册形态与本轮已处理的五册都不同，逐个说明：

**Repetitive（重复思维与行为，5 题）**
    每题有**自己的 0–4 标签**，不是统一的 Likert：
      1. 占据多少时间       0=None 1=Mild 2=Moderate 3=Severe 4=Extreme
      2. 造成多少苦恼       0=None 1=Mild 2=Moderate 3=Severe 4=Extreme
      3. 多难控制           0=Complete control … 4=No control（**方向相反**）
      4. 造成多少回避       0=No avoidance … 4=Extreme
      5. （干扰程度）
    所以「作答格式」必须**挂在每题上**，不能用一个统一的 labels 数组。

**Substance（物质使用，10 题）**
    题号是**字母 a–j**（不是数字），0–4 频率（Not at all … Nearly every day）。
    NIDA-Modified ASSIST 改编；该册版权行写明可复制（Courtesy of NIDA）。

**Mania（躁狂，5 题）**
    每题是**一组 5 句陈述**，用户选「最符合自己」的那一句，分值 0–4。
    所以选项**文本各不相同**、且比数字长得多——`options` 要能携带文本。

输出：``archive/scales/<code>/items-extracted.json``
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


def stream_texts(code: str) -> list[str]:
    doc = PdfDoc.load(os.path.join(ROOT, "archive", "scales", code, "manual.pdf"))
    out = []
    for runs in doc.text_runs():
        rows = [r["text"] for r in layout_lines(runs) if r["text"].strip()]
        j = re.sub(r"\s+", " ", " ".join(rows))
        if len(j) > 200:
            out.append(j)
    return out


def pick(streams: list[str], must: str) -> str:
    for s in streams:
        if must in s:
            return s
    return streams[0] if streams else ""


# ── Repetitive ────────────────────────────────────────────────────────
REPETITIVE_LABELS = {
    1: ["None", "Mild", "Moderate", "Severe", "Extreme"],
    2: ["None", "Mild", "Moderate", "Severe", "Extreme"],
    3: ["Complete control", "Much control", "Moderate control",
        "Little control", "No control"],
    4: ["No avoidance", "Mild", "Moderate", "Severe", "Extreme"],
    5: ["None", "Mild", "Moderate", "Severe", "Extreme"],
}
REPETITIVE_QUESTIONS = [
    "On average, how much time is occupied by these thoughts or behaviors each day?",
    "How much distress do these thoughts or behaviors cause you?",
    "How hard is it for you to control these thoughts or behaviors?",
    "How much do these thoughts or behaviors cause you to avoid doing anything, "
    "going anyplace, or being with anyone?",
    "How much do these thoughts or behaviors cause you to feel interfered with "
    "or unable to do things?",
]


def extract_repetitive() -> tuple[list[dict], list[str]]:
    text = pick(stream_texts("DSM5TR-L2-Repetitive"), "On average, how much")
    problems = []
    items = []
    for i, q in enumerate(REPETITIVE_QUESTIONS, 1):
        # 题干在原文里被版式打散，所以用「已核对的题面」+ 原文验在
        key = re.sub(r"[^a-z]", "", q.lower())[:40]
        if key[:28] not in re.sub(r"[^a-z]", "", text.lower()):
            problems.append(f"第 {i} 题的题面在原文里找不到（可能改写过头）")
        items.append({
            "order": i, "text": q,
            "options": [{"v": v, "text": t}
                        for v, t in enumerate(REPETITIVE_LABELS[i])],
        })
    return items, problems


# ── Substance ─────────────────────────────────────────────────────────
SUBSTANCE_ITEMS = [
    ("a", "Painkillers (like Vicodin)"),
    ("b", "Stimulants (like Ritalin, Adderall)"),
    ("c", "Sedatives or tranquilizers (like sleeping pills or Valium)"),
    ("d", "Marijuana"),
    ("e", "Cocaine or crack"),
    ("f", "Club drugs (like ecstasy)"),
    ("g", "Hallucinogens (like LSD)"),
    ("h", "Heroin"),
    ("i", "Inhalants or solvents (like glue)"),
    ("j", "Methamphetamine (like speed)"),
]
SUBSTANCE_LABELS = ["Not at all", "One or two days", "Several days",
                    "More than half the days", "Nearly every day"]


def extract_substance() -> tuple[list[dict], list[str]]:
    text = pick(stream_texts("DSM5TR-L2-Substance"), "Painkillers")
    problems, items = [], []
    norm = re.sub(r"[^a-z]", "", text.lower())
    for i, (letter, label) in enumerate(SUBSTANCE_ITEMS, 1):
        key = re.sub(r"[^a-z]", "", label.lower())
        if key not in norm:
            problems.append(f"第 {i} 项（{letter}. {label}）在原文里找不到")
        items.append({"order": i, "letter": letter, "text": clean_option(label),
                      "options": [{"v": v, "text": t}
                                  for v, t in enumerate(SUBSTANCE_LABELS)]})
    return items, problems


# ── Mania ─────────────────────────────────────────────────────────────
MANIA_OPTION_RE = re.compile(
    r"[\ue000-\uf8ff\u2030\u25a1\u2610\u2611\s]*([0-4])\s*([A-Z][^0-9]{6,220}?)"
    r"(?=[\ue000-\uf8ff\u2030\u25a1\u2610\u2611]{1,3}\s*[0-4]\s|Question\s*\d|$)")


def extract_mania() -> tuple[list[dict], list[str]]:
    text = pick(stream_texts("DSM5TR-L2-Mania"), "Question 1")
    problems, items = [], []
    blocks = re.split(r"Question\s*(\d)", text)
    for k in range(1, len(blocks) - 1, 2):
        num = int(blocks[k])
        body = re.split(r"Question\s*\d|Total|©|Clinician Use", blocks[k + 1])[0]
        # ⚠️ 按「框符 + 分值」切分，而不是用贪婪段落正则去匹配整句。
        #    实测贪婪写法（`([A-Z][^0-9]{6,220}?)` + 前瞻）整段只吃掉一次，
        #    5 个选项变成 1 个。这里改成：先找所有分值的出现位置，
        #    相邻两处之间的文字就是该分值的选项文本。
        marks = list(re.finditer(r"[\ue000-\uf8ff\u2030\u25a1\u2610\u2611]{0,4}\s*([0-4])\s*",
                                 body))
        opts = []
        for i, m in enumerate(marks):
            end = marks[i + 1].start() if i + 1 < len(marks) else len(body)
            t = clean_option(body[m.end():end])
            if len(t) > 6:
                opts.append({"v": int(m.group(1)), "text": t})
        # 只保留首次出现的每个分值，并丢掉明显是残片的短文本
        seen, uniq = set(), []
        for o in sorted(opts, key=lambda o: len(o["text"]), reverse=True):
            if o["v"] not in seen:
                seen.add(o["v"])
                uniq.append(o)
        uniq.sort(key=lambda o: o["v"])
        if len(uniq) != 5:
            problems.append(f"第 {num} 组解析到 {len(uniq)} 个选项（应为 5）")
        # ⚠️ 组内指示语（"Choose the one statement in each group that best
        #    describes…"）**不是量表题项**，PDF 里也不按题号出现，所以这里不编造
        #    英文原文：`text` 用**中文指示语**、`text_zh` 说明它是作答指令，
        #    并明确标出「非英文原文、非计分题」。真英文内容在 options 里，逐句都在。
        #    （我第一版把中文台词写进 text、又把 text 当英文题文，导致文本库
        #      判它「中译与英文相同」——那其实是数据本身没区分开。）
        items.append({
            "order": num,
            "text": f"第 {num} 组：选出最符合你的一句",
            "text_zh": f"第 {num} 组：选出最符合你的一句",
            "text_kind": "instruction",
            "text_source": "由提取器生成的中文作答指示语（原文该处为 Instructions "
                           "第 2 条：Choose the one statement in each group that "
                           "best describes the way you have been feeling for the "
                           "past week.）",
            "options": uniq,
        })
    if len(items) != 5:
        problems.append(f"解析到 {len(items)} 组（应为 5）")
    return items, problems


CASES = {
    "DSM5TR-L2-Repetitive": (extract_repetitive, 5, None),
    "DSM5TR-L2-Substance": (extract_substance, 10, SUBSTANCE_LABELS),
    "DSM5TR-L2-Mania": (extract_mania, 5, None),
}

# 选项文本里可能残留的「选择框」字形。**三类都要清**（2026-10-04）：
#   ① 私有区（Wingdings/Webdings 的框）
#   ② 方框类字符——实测 Mania 选项尾部挂的是 `❑` **U+2751**，
#      它不在私有区，所以只清私有区会漏（数据层实测残留 4/5 组）
#   ③ 控制字符——睡眠册的框是 `\x00‰` 组合，会留下 `\x00`
BOX_GLYPHS = re.compile(
    r"[\ue000-\uf8ff\u2030\u25a1\u2610\u2611\u2612\u2751\u2752\x00-\x1f]+")


def clean_option(t: str) -> str:
    t = BOX_GLYPHS.sub(" ", t)
    return re.sub(r"\s+", " ", t).strip(" .;:·•-")


def main() -> int:
    total_bad = 0
    for code, (fn, expect, labels) in CASES.items():
        items, problems = fn()
        if len(items) != expect:
            problems.append(f"题数 {len(items)}（应为 {expect}）")
        flag = "✓" if not problems else "✗"
        print(f"{flag} {code:26} {len(items):2}/{expect} 题")
        for p in problems[:5]:
            print(f"      {p}")
        for it in items[:6]:
            n = len(it.get("options", []))
            print(f"      {it['order']:2}. [{n} 选项] {it['text'][:66]}")
        total_bad += len(problems)
        out = os.path.join(ROOT, "archive", "scales", code, "items-extracted.json")
        with open(out, "w", encoding="utf-8") as fh:
            json.dump({
                "source_pdf": f"archive/scales/{code}/manual.pdf",
                "extractor": "tools/build/build_l2_items_rest.py",
                "response_format": ({"points": 5, "min": 0, "max": 4,
                                     "labels": labels} if labels else
                                    {"points": 5, "min": 0, "max": 4,
                                     "labels": [], "per_item_options": True}),
                "items": items, "problems": problems,
            }, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
        print()
    print(f"问题合计 {total_bad}")
    return 1 if total_bad else 0


if __name__ == "__main__":
    sys.exit(main())
