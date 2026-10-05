#!/usr/bin/env python3
"""从 APA 官方 PID-5 手册 PDF 提取 220 道题（题干 + 0–3 计分）。

版面结构（实测，坐标来自 tools/pdftext.py）
==========================================
页高约 792，每道题占一行：

    x≈33                      题号（1..220）
    x≈56                      题干（折行后仍在 x≈56）
    x≈353/405/463/515         选项列的隐藏表单域数字 0/1/2/3 —— **必须剔除**，
                              否则会插进题干中间

三行形态（切题的关键）
======================
    ① ``1I don’t get…``   题号紧贴题干（题干以 I 开头）
    ② ``6``               题号单独成行，题干在下一行
    ③ ``I lose track…``   **折行续行，开头没有数字**

所以判据只有一个：**这一行开头是不是期望的题号**。是就是新题；
不是数字就是上一题的续行；是别的数字（分值/页码）就丢弃。

踩过的坑（都写进注释，别再犯）
==============================
· 不能用前瞻 ``(?=\\D|$)``：``$`` 也匹配位置 0，导致所有字母开头的行都被当成
  数字行丢掉，expect 停在 1，其余全并进第 5 题。
· 不能按 ``BT`` 切内容流：会只提取到 382 字符（实际 112 KB）。
· 不能把不同页混在一起按 y 聚行：坐标系独立，会把不同页的题干拼成一行。
· 空格：PDF 里字词空格**已经写在字符串里**（``( o)``、``(to)``），
  不要去猜「间隙是不是空格」——我那样写过，反而插出 ``Personal ity``。
  唯一要补的是「续行与首行相接处」（``anyone.I lose`` → ``anyone. I lose``）。

自我校验
========
· 题号必须 1..220 连续（分组就是按这个推进的，断号会立刻显出来）
· 每题题干非空、长度合理
· 与 PID-5-BF 的 25 题交叉核对（比较时忽略空白与标点）——
  这是**独立于本提取器**的对照，能发现「提取出了似是而非的文本」
"""

from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pdftext import PdfDoc  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()

# 选项列（隐藏表单域 0/1/2/3）的起始 x。实测选项列在 x≈353 起，
# 而题干最右到 x≈310；取 330 分界，两边都留足余量。
OPTION_X_MIN = 330.0

# 页眉页脚与选项说明文字，不属于题干
NOISE = re.compile(
    r"^(PID|—|Adult \(Full Version\),?|page\s*\d*|Clinician|Use|Item|score|"
    r"Very False|or Often|False|Sometimes|or Somewhat|True|"
    r"The Personal|ity|Inventory for DSM|Name|/ID|Age: ____|Date:_+|"
    r"Instructions.*|This is a list.*|people might say.*|interested in how.*|"
    r"right.*or.*wrong.*|answers\..*|honestly as possible.*|"
    r"like you to take your.*|carefully, selecting.*|Krueger RF.*|"
    r"Copyright.*|American Psychiatric.*|sociation\. All Rights.*|"
    r"This material can be.*|researchers and by.*|clinicians for use.*|"
    r"their patients\.|All Rights Reserved\.|FOR CLINICIAN.*)$", re.I)

# 题项区之后的评分说明开头，用于在第 220 题处截断
TAIL = re.compile(
    r"[.!?”\"]\s+(Personality\s*Trait|Scoring and Interpretation|"
    r"Step \d|FOR CLINICIAN|Instructions to Clinicians|A\. Personality)")

# 每页页眉/指导语的**连写形态**（空格被排版吃掉，所以不能用整行匹配）。
# 题干里一旦出现这些片段，说明已经跨到下一页的页眉了——在那里截断。
# 实测：第 110 题后面粘上了
# 「The Personality Inventory for DSM-5 (PID different people might say aboutthemselves. …」
PAGE_HEAD_BLEED = (
    "The Personality Inventory for DSM",
    "ThePersonality Inventory for DSM",
    "The PersonalityInventory for DSM",
    "different people might say about",
    "differentpeople might say about",
    "We are interested in how you would describe",
    "Instructions to individual receiving care",
    "Instructions to the individual receiving care",
    "Copyright",
    "Krueger RF, Derringer J",
    "Very False Sometimes Sometimes Very True",
    "Personality Trait Facet and Domain",
    "Scoring and Interpretation",
)


def norm_for_compare(s: str) -> str:
    """比较用归一：只留字母。

    PDF 里词间空格分布在字符串内与独立文本段两处，提取结果可能残留
    ``differentpeople`` 这类粘连；**字母序列仍然正确**，而交叉核对要验证的
    正是字母序列。把空白归一掉就与排版细节解耦——否则一个空格问题会
    掩盖真正的提取错误，反过来也会让排版问题伪装成提取失败。
    """
    return re.sub(r"[^a-z]", "", s.lower())


def page_rows(doc: PdfDoc) -> list[tuple[float, str]]:
    """返回 ``[(y, 行文本), …]``，按阅读顺序（逐内容流、流内 y 降序）。

    ⚠️ 三条硬约束，都是踩出来的：

    1. **只在流内聚类**。一份 PDF 里除了页面内容流，还有页表单域、注释等
       带文本的流；把它们与页面流混在一起按 y 聚类，会得到「一个流内 y 跨度
       24..774、左侧数字横跨 1..220」这种结果——因为那是**多个坐标系叠在一起**。
       逐流处理、流间按出现顺序拼接即可（题号在流间是递增的）。
    2. **页眉页脚必须剔除**。每页开头都是标题、版权句、指导语、选项说明，
       不剔除就会粘进第 1 题（实测第 1 题后面跟着
       「Anhedonia1, 23, 26, 30R, …」这种评分表内容）。
    3. **不要试图把题号与题干聚成同一行**。它们的 y 可以差 6pt，而相邻题的
       文本也只差 6pt，按 y 分桶无论阈值取多少都会在某一类上出错。
       题号只用来给**区间**，区间内的文本行按 y 顺序拼成题干。
    """
    out: list[tuple[float, str]] = []
    for runs in doc.text_runs():
        cells: list[tuple[float, float, str]] = []
        for x0, _x1, y, _size, text in runs:
            if x0 >= OPTION_X_MIN:          # 选项列的隐藏表单域 —— 不要
                continue
            if text.strip():
                cells.append((x0, y, text))
        rows: list[list[tuple[float, str]]] = []
        rows_y: list[float] = []
        for x0, y, text in sorted(cells, key=lambda r: -r[1]):   # y 降序 = 自上而下
            if rows_y and abs(rows_y[-1] - y) <= 8.0:
                rows[-1].append((x0, text))
                continue
            rows.append([(x0, text)])
            rows_y.append(y)
        for i, group in enumerate(rows):
            line = "".join(t for _x, t in sorted(group, key=lambda c: c[0]))
            line = re.sub(r"[ \t]+", " ", line).strip()
            if line and not NOISE.match(line):
                out.append((rows_y[i], line))
    return out


def slice_items(rows: list[tuple[float, str]]) -> tuple[list[str], list[str]]:
    """按题号把行切成题项：题号给出**区间**，区间内的文本行按 y 顺序拼成题干。"""
    items: list[str] = []
    problems: list[str] = []

    # ① 题号出现的位置。按**阅读顺序**（rows 已是逐流、流内 y 降序）依次取，
    #    只有等于「上一个 +1」的才收，这样分值 0/1/2/3 与页码会被自动排除。
    marks: list[int] = []                      # rows 下标
    got: list[int] = []                        # 对应的题号
    last = 0
    for k, (_y, ln) in enumerate(rows):
        m = re.match(r"^(\d{1,3})(?!\d)", ln)
        if not m:
            continue
        v = int(m.group(1))
        if v == last + 1 and v <= 220:
            marks.append(k)
            got.append(v)
            last = v

    for i, name in enumerate(got, 1):
        if name != i:
            problems.append(f"第 {i} 个题号是 {name}（不连续）")

    # ② 每道题 = 本题号那一行 + 到下一题号之前的所有非数字行
    for idx, k in enumerate(marks):
        end = marks[idx + 1] if idx + 1 < len(marks) else len(rows)
        rest = re.sub(r"^\d{1,3}", "", rows[k][1], count=1).strip()
        frags = [rest] if rest else []
        for _y, ln in rows[k + 1:end]:
            if re.match(r"^\d{1,3}(?!\d)", ln):
                continue                        # 分值 / 页码 / 其它数字行
            frags.append(ln)
        items.append(join_fragments(frags, got[idx] if idx < len(got) else idx + 1))

    for i, t in enumerate(items, 1):
        if not t:
            problems.append(f"第 {i} 题：切出来是空的")
        elif len(t) < 8:
            problems.append(f"第 {i} 题：过短 -> {t!r}")
    return items, problems


def join_fragments(frags: list[str], num: int) -> str:
    """把一道题的各行拼成题干。"""
    keep = [f for f in frags if f and not re.fullmatch(r"[0-3]+", f) and not NOISE.match(f)]
    if not keep:
        return ""
    txt = " ".join(keep)
    txt = re.sub(r"\s+", " ", txt).strip()
    # 续行与首行直接相接时中间没有空格（`…for anyone.I lose track…`），补一个。
    # 只要求后面跟一个**完整单词**（首字母大写 + 至少一个小写字母），
    # 这样 "mein" → "me in" 能修好，而 "me" + "In…" 这种真词首不会被误拆。
    txt = re.sub(r"(?<=[.!?])(?=[A-Z])", " ", txt)
    txt = re.sub(r"(?<=[a-z])(?=[A-Z][a-z])", " ", txt)
    # 题项区之后的内容会粘在最后一道题后面（实测第 220 题带上了
    # 「PersonalityTrait Facet…Scoring」），在评分段开头处截断。
    m = TAIL.search(txt)
    if m and m.start() > 20:
        txt = txt[:m.start() + 1]
    # 跨页时下一页的页眉会滚进题干（实测第 110 题），在页眉片段处截断。
    # 页眉的空格被排版吃掉，所以按片段匹配而不是整行。
    for frag in PAGE_HEAD_BLEED:
        pos = txt.find(frag)
        if pos > 20:
            txt = txt[:pos]
            break
    txt = re.sub(r"\s+([.,;:])", r"\1", txt)
    return txt.replace(" ’ ", "’").replace(" ' ", "'").strip()


def extract_items(pdf_path: str) -> tuple[list[str], list[str], dict]:
    doc = PdfDoc.load(pdf_path)
    rows = page_rows(doc)
    items, problems = slice_items(rows)
    stats = {"pages": len(doc.text_runs()), "rows": len(rows),
             "items": len(items), "chars": sum(len(t) for t in items)}
    return items, problems, stats


def main() -> int:
    pdf = os.path.join(ROOT, "archive", "scales", "PID-5", "manual.pdf")
    items, problems, stats = extract_items(pdf)
    print(f"页 {stats['pages']} 个 → 行 {stats['rows']} 行，"
          f"切出题项 {len(items)} 道（{stats['chars']} 字符）")

    ok = True
    if len(items) != 220:
        print(f"  ✗ 题数应为 220，实际 {len(items)}")
        ok = False
    for p in problems[:10]:
        print(f"  ✗ {p}")
        ok = False

    # 结构自检：重复、异常长度、非 ASCII
    norm = [norm_for_compare(t) for t in items]
    dup = {n for n in norm if norm.count(n) > 1}
    if dup:
        print(f"  ✗ 有 {len(dup)} 道题重复：{sorted(dup)[:3]}")
        ok = False
    lens = [len(t) for t in items]
    print(f"  题干长度：最短 {min(lens)}，中位 {sorted(lens)[len(lens) // 2]}，"
          f"最长 {max(lens)}")
    non_ascii = [t for t in items if any(ord(c) > 0x2500 for c in t)]
    if non_ascii:
        print(f"  ! {len(non_ascii)} 道题含非预期字符：{non_ascii[0][:60]!r}")

    print("\n=== 前 10 题 ===")
    for i, t in enumerate(items[:10], 1):
        print(f"  {i:3}. {t[:96]}")
    print("\n=== 第 216–220 题 ===")
    for i, t in enumerate(items[215:220], 216):
        print(f"  {i:3}. {t[:96]}")

    # 独立对照：PID-5-BF 的 25 题必须能在完整版里找到
    bf_pdf = os.path.join(ROOT, "archive", "scales", "PID-5-BF", "manual.pdf")
    bf_items: list[str] = []
    if os.path.exists(bf_pdf):
        bf_items, bf_problems, bf_stats = extract_items(bf_pdf)
        print(f"\n=== 与 PID-5-BF 交叉核对（BF 切出 {len(bf_items)} 题）===")
        pool = {norm_for_compare(t) for t in items}
        miss = [t for t in bf_items if norm_for_compare(t) not in pool]
        print(f"  BF 的 {len(bf_items)} 题中，{len(bf_items) - len(miss)} 题能在"
              f"完整版 220 题里找到（比较时忽略空白与标点）")
        for t in miss[:6]:
            print(f"    ✗ 对不上：{t[:80]}")
        if miss:
            print("    ⚠ 字母序列对不上，必须查清——不能带病收录")
            ok = False

    out = os.path.join(ROOT, "archive", "scales", "PID-5", "items-extracted.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({
            "source_pdf": "archive/scales/PID-5/manual.pdf",
            "extractor": "tools/build/build_pid5_items.py",
            "stats": stats,
            "items": [{"order": i, "text": t} for i, t in enumerate(items, 1)],
            "cross_check": {"with": "PID-5-BF",
                            "bf_items": len(bf_items),
                            "matched": len(bf_items) - sum(
                                1 for t in bf_items
                                if norm_for_compare(t) not in
                                {norm_for_compare(x) for x in items})},
        }, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(f"\n已写出 {os.path.relpath(out, ROOT)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
