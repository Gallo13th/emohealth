#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""英文题干排版修复的守门测试（T-G）。

三条断言
========
1. ``data/items-structured/*.json`` 的用户可见 ``text_en`` 里**不再有排版缺陷**：
   * (1a) ``content/en-repairs.json`` 的 ``repaired`` 必须已经贯通到 ``text_en``
     （T-C 的 task-27 负责灌入）——这是最强的「修复真的落地了」证据；
   * (1b) 对全部 ``text_en`` 跑一遍启发式扫描（下面逐条解释依据），白名单式列举
     已知合法形态，避免误报。
2. 每个 ``repairs`` 条目的 ``verbatim`` 必须能在**上游源文件**里逐字找到
   （``data/instruments/*.json`` 的 ``items[].text`` 或 ``data/text-db/text-db.json``
   的 ``entries[].en``）——证明留痕是抄来的，不是编的。
3. ``data/**``（``data/item-scenes.json`` 除外）的**用户可见字段**里不含
   ``排版噪声`` / ``缺空格`` / ``漏空格`` / ``直译``——用户在界面上不该再看到
   「这是排版噪声」这类解释（界面由 T-H1 负责，数据层由本断言守）。

启发式依据（每条都说明为什么这样判、以及为什么不会误报）
========================================================
H1 **常用词切分（粘连）**：英文里「两个常用词黏在一起」几乎只可能来自排版丢空格
   （``behonest`` = ``be``+``honest``）。判据：一个 token 不在已知词表里、但能切成
   两段都出现在**常用词表 CORE**（约 150 个功能词/高频词）里 → 判为粘连。
   为什么用 CORE 而不是大词典：本仓库没有可离线用的英文词典（无 nltk/hunspell），
   而 archive 的多语词表含 ``ama``/``mein`` 等外语词，会把粘连「洗白」。
   为什么不会误报：CORE 切分会命中 ``into``(in+to)、``something``(some+thing) 这类
   **真词**，因此配一份 ``LEGIT_GLUE`` 白名单（15 个，逐个列出）；该白名单是把
   CORE 切分跑遍全部 606 题后逐一人工核对得到的，本语料内是完备的。
   不做「稀有词也可疑」的放宽：实测会把 ``pointless``/``fish``/``hips``/``pound``
   误判成 ``point|less``/``fi|sh``…，真阳性收益为 0。
   已知一例漏网：``I ama``（``ama`` 在 archive 多语词表里有 3 次，切分检测看不见），
   由 ``content/en-repairs.json`` 的条目（1a）与 text-db 的 note 种子兜底。

H2 **闭引号后缺空格**：``“zone out”and``。判据：``”``/``"`` 前面是字母或标点、
   后面**直接**跟字母 → 缺空格。合法的开引号（``"just right."``）后面跟字母但前面
   不是字母/标点，不命中。

H3 **撇号后缺空格**：``others’things`` / ``peoples’attention``。判据：``’`` 后直接跟
   一个 ≥4 字母的已知词。真缩写（``don’t``/``it’s``/``you’re``）撇号后只有 1–2 个
   字母，且整串在 ``CONTRACTIONS`` 里，不命中。

H4 **标点后缺空格**：``,``/``.``/``;``/``:`` 后直接跟字母。排除 ``e.g.``/``i.e.``
   与首字母缩写（``U.S.``）——判据是「该标点前的 token 恰好是单字母加句点」。

H5 **多余/首尾空白**：连续 2 个以上空格、或首尾有空白。英文题干里没有合法场景。

用法：``python tools/check/check_item_typo_repair.py``（退出码 0 = 全绿）
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
import collections

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402

# Windows 默认控制台是 GBK，直接 print ✅/❌ 会 UnicodeEncodeError 崩掉；
# 统一把 stdout/stderr 切到 UTF-8（errors=replace），保证裸 `python tools/check/...` 可跑。
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = find_root()

# ── 常用词表（功能词 + 高频实词）。用于 H1 的「切分检测」 ────────────────────
CORE = set("""a an the i you he she it we they me him her us them my your his its our their
to of in on at by for with from and or but not no so if then than that this these those
there here when where why how what which who whose is am are was were be been being
do does did have has had will would can could should may might must
up down out off over under again very just only also well more most some any all both
each other others such same too as because while until time life people person thing
things way lot lots make makes made sure keep keeps enjoy honest anxious skip skipped
town activity see seen want know think come go get give take say tell work feel look
little big good bad great new old long right left hard easy high low
""".split())

# ── H1 白名单：能被 CORE 切分、但**本身就是合法英文词**的形态 ────────────────
# （把 CORE 切分跑遍 606 题，逐个人工核对得到；每条都是真词，不是粘连）
LEGIT_GLUE = {
    "anything", "something", "nothing", "everything",   # any+thing / some+thing / no+thing
    "into", "onto", "within", "without",                 # in+to / on+to / with+in / with+out
    "another",                                           # an+other
    "some", "mean",                                      # so+me / me+an
    "away",                                              # a+way
    "become", "overcome",                                # be+come / over+come
    "forget",                                            # for+get
    "somehow",                                           # some+how
    "belong",                                            # be+long
    "anthem",                                            # an+them
    "himself", "herself", "itself", "myself", "yourself",
    "ourselves", "yourselves", "themselves",             # him+self …
    "nobody", "somebody", "anybody", "everybody",        # no+body …
    "upcoming", "output", "input", "outcome", "income",  # out+put / in+put / in+come
}

CONTRACTIONS = set("""don’t doesn’t didn’t isn’t aren’t wasn’t weren’t can’t couldn’t won’t
wouldn’t shouldn’t hasn’t haven’t hadn’t i’m i’ve i’ll i’d you’re you’ve you’ll you’d
he’s he’ll he’d she’s she’ll she’d it’s it’ll we’re we’ve we’ll we’d they’re they’ve
they’ll they’d that’s there’s what’s let’s who’s o’clock ma’am y’all ain’t""".split())

# 断言 3 的「用户可见字段」：UI 真的会渲染的那些（`ui/index.html` 明确把 notes_zh
# 作为「作答注记（默认可见）」渲染，见 index.html:356/1107）。
# `data/text-db/text-db.json` 的 `note` 是**译者备忘**，UI 不读（`ui/` 下零引用）。
# **已裁决（Lead，2026-10-05）：判「不可见」，只警告不计失败。** 依据三层契约：
#   ① `ui/**` 对 text-db 的 `note` 零引用；C3 规定数据层不读 `ui/`，反向 `ui/` 也不该读数据层的 memo。
#   ② T-C 贯通后 `items-structured` 的 `notes_zh` **完全由 `content/scenes/*.json` 覆盖**，
#      text-db 的 `note` 不再进任何界面路径。
#   ③ text-db 的 `note` 本来就**该**保留那类话——它是 **R5 的留痕**（记录「源件这里缺空格」
#      「这里照实直译」）。把它判成「用户可见错误」会逼我们删掉留痕，自相矛盾。
# 判据：**「用户看得见」才算可见；看不见的留痕是证据，不是缺陷。**
TEXTDB_NOTE_IS_VISIBLE = False
RENDERED_KEYS = {"text_en", "text_zh", "label_en", "label_zh", "display_name", "citation",
                 "notes_zh", "why", "title", "sub"}
BANNED = ["排版噪声", "缺空格", "漏空格", "直译"]


def load_json(rel):
    with io.open(os.path.join(ROOT, *rel.split("/")), encoding="utf-8") as fh:
        return json.load(fh)


def split_glue(tok):
    """H1：token 能切成两段都在 CORE 里的词 -> 返回两段，否则 None。"""
    tl = tok.lower()
    if tl in CORE or tl in LEGIT_GLUE or len(tl) < 3:
        return None
    for i in range(1, len(tl)):
        a, b = tl[:i], tl[i:]
        if a in CORE and b in CORE:
            return (a, b)
    return None


def text_defects(text):
    """返回该 text 里命中的排版缺陷列表 [(kind, 片段)]。"""
    out = []
    for m in re.finditer(r"[A-Za-zà-ÿ]+", text):          # H1
        g = split_glue(m.group(0))
        if g:
            out.append(("missing_space", f"{m.group(0)} → {g[0]} {g[1]}"))
    for m in re.finditer(r"(?<=[A-Za-z.,!?])[”\"](?=[A-Za-z])", text):   # H2
        out.append(("punctuation_spacing", text[max(0, m.start() - 16):m.start() + 14]))
    for m in re.finditer(r"([A-Za-z]+)’([a-z]{4,})", text):              # H3
        if m.group(0).lower() in CONTRACTIONS:
            continue
        if m.group(2).lower() in CORE:
            out.append(("apostrophe_placement", m.group(0)))
    for m in re.finditer(r"(?<=[,.;:])(?=[A-Za-z])", text):              # H4
        if re.search(r"\b[A-Za-z]\.$", text[:m.start()]):
            continue
        out.append(("punctuation_spacing", text[max(0, m.start() - 16):m.start() + 14]))
    if re.search(r"  +", text):                                          # H5
        out.append(("extra_space", "连续空格"))
    if text != text.strip():
        out.append(("extra_space", "首尾空白"))
    return out


def main() -> int:
    print("英文题干排版修复守卫（项目根：%s）" % ROOT)
    fails = []

    rep_doc = load_json("content/en-repairs.json")
    if rep_doc.get("schema") != "en-repairs/1.0":
        print("✗ schema 不是 en-repairs/1.0：", rep_doc.get("schema"))
        return 1
    repairs = rep_doc.get("repairs", {})
    review = rep_doc.get("needs_lead_review", {})
    print(f"  content/en-repairs.json：repairs {len(repairs)} 条，"
          f"needs_lead_review {len(review)} 条")
    if review:
        print("  ⚠️ needs_lead_review 非空：", sorted(review))

    # ── 载入三处数据 ──────────────────────────────────────────────
    structured = {}
    for fn in sorted(os.listdir(os.path.join(ROOT, "data", "items-structured"))):
        if not fn.endswith(".json") or fn == "index.json":
            continue
        obj = load_json(f"data/items-structured/{fn}")
        for it in obj.get("items", []):
            structured[it["id"]] = it.get("text_en")
    upstream_instr = {}
    for fn in sorted(os.listdir(os.path.join(ROOT, "data", "instruments"))):
        if not fn.endswith(".json"):
            continue
        obj = load_json(f"data/instruments/{fn}")
        for it in obj.get("items", []) or []:
            if isinstance(it, dict) and "id" in it:
                upstream_instr.setdefault(it["id"], []).append(it.get("text"))
    tdb = load_json("data/text-db/text-db.json")
    upstream_tdb = {e.get("en") for e in tdb.get("entries", {}).values()}

    # ── 断言 1 ────────────────────────────────────────────────────
    print("\n── 断言 1：data/items-structured/*.json 的 text_en 无排版缺陷 ──")
    not_wired = [i for i, r in repairs.items() if structured.get(i) != r["repaired"]]
    if not_wired:
        fails.append(f"断言1a：{len(not_wired)} 条 repairs 的 repaired 尚未贯通到 text_en")
        print(f"  ❌ 1a 未贯通 {len(not_wired)} 条：{sorted(not_wired)[:8]}"
              f"{' …' if len(not_wired) > 8 else ''}")
        for i in sorted(not_wired)[:3]:
            print(f"        [{i}] text_en = {structured.get(i)!r}")
            print(f"             应为   = {repairs[i]['repaired']!r}")
    else:
        print(f"  ✅ 1a {len(repairs)} 条 repaired 已全部贯通到 text_en")

    # 1b：全量启发式 + 由 repairs 派生的黑名单
    defect_frags = set()
    for i, r in repairs.items():
        vt = set(re.findall(r"[A-Za-zà-ÿ’]+", r["verbatim"]))
        rp = set(re.findall(r"[A-Za-zà-ÿ’]+", r["repaired"]))
        defect_frags |= {t for t in vt - rp}
    bad1b = []
    for iid, t in sorted(structured.items()):
        if not isinstance(t, str):
            continue
        for kind, frag in text_defects(t):
            bad1b.append((iid, kind, frag))
        for frag in defect_frags:
            if frag in t:
                bad1b.append((iid, "known_defect_token", frag))
    if bad1b:
        fails.append(f"断言1b：{len(bad1b)} 处残余排版缺陷")
        print(f"  ❌ 1b 残余 {len(bad1b)} 处：")
        for iid, kind, frag in bad1b[:15]:
            print(f"        [{iid}] {kind}: {frag}")
    else:
        print(f"  ✅ 1b 全部 {len(structured)} 条 text_en 通过启发式 + 已知缺陷黑名单")
    print(f"     （H1 常用词切分 / H2 闭引号 / H3 撇号 / H4 标点 / H5 空白；"
          f"白名单 {len(LEGIT_GLUE)} 条；派生黑名单 {len(defect_frags)} 个粘连串）")

    # ── 断言 2 ────────────────────────────────────────────────────
    print("\n── 断言 2：每条 verbatim 都能在上游源文件逐字找到 ──")
    miss2 = []
    for i, r in repairs.items():
        v = r["verbatim"]
        in_instr = v in upstream_instr.get(i, [])
        in_tdb = v in upstream_tdb
        if not (in_instr and in_tdb):
            miss2.append((i, in_instr, in_tdb))
    if miss2:
        fails.append(f"断言2：{len(miss2)} 条 verbatim 不在上游")
        print(f"  ❌ {len(miss2)} 条对不上：")
        for i, a, b in miss2[:10]:
            print(f"        [{i}] instruments={a} text-db={b}")
    else:
        print(f"  ✅ {len(repairs)} 条 verbatim 在 data/instruments/*.json 与 "
              f"data/text-db/text-db.json 里都逐字命中")

    # ── 断言 3 ────────────────────────────────────────────────────
    print("\n── 断言 3：data/** 用户可见字段不含 排版噪声/缺空格/漏空格/直译 ──")
    blocked, warned = [], []
    data_dir = os.path.join(ROOT, "data")
    for base, dirs, files in os.walk(data_dir):
        for f in sorted(files):
            if not f.endswith(".json"):
                continue
            rel = os.path.relpath(os.path.join(base, f), ROOT).replace(os.sep, "/")
            if rel == "data/item-scenes.json":
                continue
            try:
                obj = json.load(io.open(os.path.join(base, f), encoding="utf-8"))
            except Exception:
                continue
            stack = [("", obj)]
            while stack:
                path, cur = stack.pop()
                if isinstance(cur, dict):
                    for k, v in cur.items():
                        stack.append((f"{path}.{k}", v))
                elif isinstance(cur, list):
                    for i, v in enumerate(cur):
                        stack.append((f"{path}[{i}]", v))
                elif isinstance(cur, str):
                    # 可见性取「路径上任一层字段名」：notes_zh[0].text 的字段是
                    # notes_zh（数组元素里的 text 只是它的子键），不能只看最后一层。
                    comps = [c.split("[")[0] for c in path.split(".") if c]
                    visible = any(c in RENDERED_KEYS for c in comps) or (
                        TEXTDB_NOTE_IS_VISIBLE and "note" in comps)
                    for b in BANNED:
                        if b not in cur:
                            continue
                        key = comps[-1] if comps else ""
                        (blocked if visible else warned).append(
                            f"{rel}{path} [{b}]")
    if blocked:
        fails.append(f"断言3：{len(blocked)} 处用户可见字段含禁用词")
        print(f"  ❌ {len(blocked)} 处用户可见字段命中：")
        for h in blocked[:12]:
            print("        ", h)
    else:
        print("  ✅ 用户可见字段干净")
    if warned:
        print(f"  ⚠️ 另有 {len(warned)} 处非可见字段（如 text-db 译者备忘 note）命中，"
              f"不计失败：")
        for h in warned[:6]:
            print("        ", h)

    print("\n" + "=" * 66)
    if fails:
        print("❌ 未通过：")
        for f in fails:
            print("   -", f)
        return 1
    print("✅ 三条断言全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
