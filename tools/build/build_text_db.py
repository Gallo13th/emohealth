#!/usr/bin/env python3
"""构建统一文本库 ``data/text-db/``（D113 流程的第 ③ 步）。

为什么要有文本库这一层
======================
342 套量表、5000 多道题，题文散在几处：

  · ``data/instruments/*.json``        英文题文（提取器产出）
  · ``data/scene-taxonomy.json``       大五人格的**中译**（``items[*].text_zh``）
  · ``content/facets/*.record.json``   大五人格的**逐题注释**（承重词、常见误读…；
                                       作者级资产是 ``content/item_scaffolding.py``）

前端直接读散落的三处，就会出现「有的量表有中译、有的没有」这种不一致。
所以中间加一层**统一文本库**：以**归一化题文**为键，把各来源合并，
并给每一条打上「译文来源」与「校验状态」。前端只读这一层。

归一化去重为什么重要
====================
同一道题会出现在多套量表里（IPIP 的题被大量复用）。实测 5045 道题里
**不同题文只有约 1800 条**——按题文去重后，翻译与注释的工作量与存储都大幅下降。

产出
====
``data/text-db/text-db.json``：``{entries: {norm_key: {...}}, stats: {...}}``
每条：``en`` / ``zh`` / ``zh_source`` / ``scaffold`` / ``instruments`` / ``codes``
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
from textkey import (INDEX_NAME, build_index, index_collisions,  # noqa: E402
                     render_index)
ROOT = find_root()
OUT = os.path.join(ROOT, "data", "text-db", "text-db.json")
#: 归一化索引（**生成物，不许手改**）：``{norm_key(entry key): entry key}``，
#: **只由 entries 派生**。有它，下游才能用 ``textkey.lookup()`` 拿题文直接查到材料——
#: 否则 ``hang-gliding``/``don’t`` 这类原样保留的 text_en 会对不上抹平了连字符的
#: entry key，**静默查不到**（实测 606 题里 9 题）。放在这里生成，索引就不可能漂移。
#: ⚠️ 索引里**不放**「排版修复后写法」的别名：repaired ↔ verbatim 的对应关系每题自带
#: （``data/items-structured/*.json`` 的 ``text_en_verbatim``），抄进索引就是第二个真相源。
#: 查不到时的回退由 ``textkey.lookup(..., fallbacks=[text_en_verbatim])`` 承担。
INDEX = os.path.join(ROOT, "data", "text-db", INDEX_NAME)
TAX = os.path.join(ROOT, "data", "scene-taxonomy.json")
FACETS_DIR = os.path.join(ROOT, "content", "facets")

#: 中译与脚手架的来源（**数据层源头**，见 ``load_neo_zh``）。
#: 这几条字符串会写进产物的 ``zh_source`` / ``sources``，是**溯源信息**：
#: 改来源必须同步改它们，否则产出里记的就是假出处。
TAXONOMY_REL = "data/scene-taxonomy.json"
ZH_SOURCE = f"{TAXONOMY_REL}（大五人格，已人工核对）"
SCAFFOLD_SOURCE = ("content/facets/*.record.json（大五人格逐题注释；"
                   "作者级资产 content/item_scaffolding.py）")


def stale_source_label(src: str | None) -> bool:
    """旧标签长得像**文件路径**吗——是则说明它记录的是一个已失效的出处。

    上一版把大五中译的出处写成前端生成包 ``ui/emohealth-data.js``。重建时以旧库
    为底继承中译（见 ``load_previous``），这些标签**不会**自动更新；只有把
    「路径形态的旧标签」改写成当前源头，产出里的溯源信息才不会再指着前端包。
    不是路径的标签（例如 ``subagent 初译（待人工复核）``）一律不动：那是真的
    出自别处，改了才是伪造溯源。
    """
    return bool(src) and ("/" in src or "\\" in src)


def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def norm(t: str) -> str:
    """归一化题文做去重键：小写、统一引号、**连字符转空格**、压空白、去尾标点。

    ⚠️ 连字符必须归一：同一道题在不同来源里写法不同（实测
    ``Would never go hang gliding or bungee jumping.`` vs
    ``Would never go hang-gliding or bungee-jumping``），不归一就会漏配 1 条中译。
    """
    s = (t or "").replace("\u2019", "'").replace("\u2018", "'")
    s = s.replace("\u201c", '"').replace("\u201d", '"')
    s = s.replace("-", " ").replace("\u2013", " ").replace("\u2014", " ")
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"[.\s]+$", "", s)
    return s.lower()


def facet_record_files() -> list[str]:
    """大五人格 30 个面向的 record 文件。

    枚举口径与 ``tools/ui/build_ui_bundle.py`` 生成前端包时**完全一致**
    （``content/facet_definitions.FACETS``），所以两边取到的是同一份数据。
    """
    sys.path.insert(0, ROOT)
    from content.facet_definitions import FACETS  # noqa: E402

    files = [os.path.join(FACETS_DIR, f"{f}.record.json") for f in FACETS]
    assert len(files) == 30, f"大五面向应为 30 个，得到 {len(files)}"
    return files


def load_neo_zh() -> tuple[dict[str, str], dict[str, dict]]:
    """从**数据层源头**取大五人格的中译与逐题脚手架。

    来源（正是 ``tools/ui/build_ui_bundle.py`` 生成 ``ui/emohealth-data.js`` 的输入）：
      · 中译     ``data/scene-taxonomy.json`` 的 ``items[*].text_zh``
      · 脚手架   ``content/facets/<facet>.record.json`` 的 ``items[*].scaffolding``
                （作者级资产在 ``content/item_scaffolding.py``，由
                 ``tools/build/build_all_facets.py`` 组装进 record）

    为什么不再读 ``ui/emohealth-data.js``：那是**前端生成包**，数据层读它构成
    C3 反向依赖（改界面 → 数据层输入跟着变），而且当时守卫看不见
    （路径绑在单字母变量 ``p`` 上）。已逐条比对：从这两处源头取出的
    300 条中译、300 条脚手架与前端包**逐字一致**。

    ⚠️ ``scaf`` 的键是**题号**（"1".."300"），不是题文或 code——
    所以要先经 ``order_to_en`` 把题号映射到英文题文，才能按题文对上。
    我第一版拿 ``source_code`` 去查 scaf，结果 300 条一条都没匹配上。
    """
    with open(TAX, encoding="utf-8") as fh:
        tax = json.load(fh)
    zh: dict[str, str] = {}
    order_to_en: dict[str, str] = {}
    for item in (tax.get("items") or {}).values():
        # 形态：{"order": 1, "text_en": "...", "text_zh": "..."}
        en, zhs = item.get("text_en"), item.get("text_zh")
        if not (en and zhs):
            continue
        key = norm(en)
        zh[key] = zhs
        order_to_en[str(item["order"])] = key

    scaf: dict[str, dict] = {}
    for path in facet_record_files():
        with open(path, encoding="utf-8") as fh:
            rec = json.load(fh)
        for it in rec.get("items") or []:
            sc = it.get("scaffolding") or {}
            if sc.get("status") == "PENDING" or not sc.get("asks"):
                continue
            key = order_to_en.get(str(it["administration_order"]))
            if not key:
                continue
            scaf[key] = {
                "asks": sc["asks"],
                "term": sc["key_term"]["term"],
                "sense": sc["key_term"]["sense_here"],
                "not_this": sc["key_term"]["not_this"],
                "mis": [[m["misreading"], m["correction"]]
                        for m in sc.get("common_misreadings", [])],
                "counts": sc.get("counts_as", []),
                "notcount": sc.get("does_not_count_as", []),
                "edge": sc.get("edge_cases"),
                "loc": sc.get("localization_note"),
            }
    return zh, scaf


def load_previous() -> tuple[dict, dict]:
    """读上一次的文本库：``entries`` 用于**继承已有中译**，``stats`` 用于
    继承**下游维护的账目**（见 ``main`` 里 ``translated_batches`` 的说明）。

    ⚠️ 本脚本是「从各来源重建」，重建会覆盖 ``data/text-db/text-db.json``。
    而中译是**增量积累**的（subagent 分 92 批写盘后由
    ``collect_translations_from_disk.py`` 回写），重建时若不继承就会全部丢掉——
    我实测被冲掉过一次（2578 → 300），白跑几十批。

    所以：重建时以旧库为底，再让各来源覆盖/补充。

    ⚠️ **继承字段要列全**：只列 en/zh/zh_source/scaffold 会**静默丢掉**其它键——
    实测 ``zh_note``（人工留档：旧稿、修正原因）就是这么消失过一次。注释、备注
    这类「人写的东西」丢了不会报错，只会让下一次复核失去依据。
    """
    if not os.path.exists(OUT):
        return {}, {}
    try:
        with open(OUT, encoding="utf-8") as fh:
            d = json.load(fh)
        return (d.get("entries") or {}), (d.get("stats") or {})
    except Exception:                                        # noqa: BLE001
        return {}, {}


#: 译文复核记录（AI 逐条 + 仲裁）——修正表与复核状态标签都在这里，是**唯一真相源**
REVIEW_REL = "data/text-db/reviewed-corrections.json"
#: 「还没复核」的状态标签；复核后必须不再出现（见 apply_review）
PENDING_LABEL = "待人工复核"
#: 页脚/授权声明混进题文或译文的特征串——这类残留一律属缺陷（同 task-14 的判据）
CONTAM = re.compile(r"Copyright ©|All Rights Reserved|This material can be reproduced",
                    re.I)
#: 中文字符：用于区分「括号里是中文补充说明」与「括号里又把英文抄了一遍」
CJK = re.compile(r"[\u4e00-\u9fff]")
PAREN = re.compile(r"[（(]([^（()）]*)[)）]")


def strip_parenthetical_english(entries: dict) -> int:
    """去掉 ``zh`` 里**把英文原文又抄一遍**的括号内嵌（D27 实现方式的**反转**）。

    背景（Lead 2026-10-04 决策，选项②）：R2 把「① 英文原文 / ② 中文翻译 /
    ③ 本地化讲解」定为**并列的三部分**。而 ``中文（English）`` 这种内嵌把英文
    又塞回了**用户可见的题面**——既与 ``en`` 字段重复，又让「中译」不再纯粹。
    D27 的**意图**（译法有偏移时便于对照）由 ``en`` 字段本身承担：界面本来就是
    把 ``zh`` 与 ``en`` **并列显示**的，对照功能结构性存在，不需要在同一字段里混排。

    ⚠️ 判据从严，只删「括号内是**纯英文**且确属 ``en`` 的一部分」：
       · 括号内含中文（如 ``（如麦角酸二乙酰胺，LSD）``）→ 正常补充说明，**不动**；
       · 括号内是中文+缩写（``（如 LSD）``）→ 同上（靠 CJK 排除，不是靠长度）；
       · 压紧后短于 3 字符（``（a）`` 之类）→ 不动，避免误伤；
       · 括号里是**别的**英文（并非 ``en`` 的片段）→ 不动，交人工（本库现为 0 条）。
    """
    removed = 0
    for e in entries.values():
        zh = e.get("zh")
        if not zh:
            continue
        en_sq = squash(e.get("en", ""))
        keep, last, hit = [], 0, False
        for m in PAREN.finditer(zh):
            inner = m.group(1)
            if CJK.search(inner):                      # 含中文 → 正常补充说明
                continue
            isq = squash(inner)
            if len(isq) < 3 or isq not in en_sq:       # 不是英文原文的片段 → 不动
                continue
            keep.append(zh[last:m.start()])
            last = m.end()
            hit = True
            removed += 1
        if hit:
            e["zh"] = re.sub(r"\s+", " ", "".join(keep) + zh[last:]).strip()
    return removed



def apply_review(entries: dict) -> dict:
    """套用译文复核结论：更新复核状态标签 + 套用修正表。

    为什么做成**生成器里的一张资产表**，而不是直接改产物：
    ``zh`` 有多个上游（``zh_map`` 来自 ``data/scene-taxonomy.json``、旧库继承、
    批次回写），直接改产物会被下次重跑按上游覆盖。把复核结论落成
    ``data/text-db/reviewed-corrections.json``（含方法、依据、旧值、原因），
    就与 ``zh_map`` 同级、可复现、且**自带溯源**。
    """
    rec = load_json(os.path.join(ROOT, REVIEW_REL)) if os.path.exists(
        os.path.join(ROOT, REVIEW_REL)) else None
    if not rec:
        return {"reviewed": 0, "relabelled": 0, "corrected": 0}
    label = rec.get("label") or "AI 复核"
    label_fix = rec.get("label_corrected") or label

    # ① 复核状态：全部「待人工复核」的条目都已过复核 → 换成如实的状态标签
    relabelled = 0
    for e in entries.values():
        if e.get("zh") and PENDING_LABEL in (e.get("zh_source") or ""):
            e["zh_source"] = label
            relabelled += 1

    # ② 修正表（按 `en` 精确匹配，改完盖上「已按仲裁结论更正」的标签）
    corrected = 0
    for c in rec.get("corrections") or []:
        k = norm(c["en"])
        e = entries.get(k)
        if e is None:
            continue
        if e.get("zh") != c["new_zh"]:
            e["zh"] = c["new_zh"]
            corrected += 1
        e["zh_source"] = label_fix
        note = f"复核更正（{rec.get('reviewed_at','')}）：{c.get('reason','')}"
        if note not in (e.get("zh_note") or ""):
            e["zh_note"] = (note + " " + (e.get("zh_note") or "")).strip()
    return {"reviewed": rec.get("reviewed_count", 0), "relabelled": relabelled,
            "corrected": corrected, "label": label}


def _merge_removed(old: list[dict], new: list[dict]) -> list[dict]:
    """累积清理台账：按 ``key`` 去重，条目只增不减。"""
    seen = {x.get("key") for x in old}
    return list(old) + [x for x in new if x.get("key") not in seen]


def purge_stale(entries: dict, current: set[str]) -> list[dict]:
    """删掉「**同题旧版**」与「**污染残留**」两类孤儿条目（判据从严）。

    背景（R3）：旧库的键原先被**无条件继承**，所以 `task-14` 修好题文之后，
    修复前的旧条目**永久留着**——L1 第 23 题因此同时存在「旧条目（截断英文 + 页脚
    授权句 + 旧译）」与「新条目（完整英文 + 重译）」，复核会审到错的那条（本轮第 3 条）。

    只清两类，**其余孤儿一律保留**（被撤量表的译文是资产）：
      ① **同题旧版**：A 的压紧题文与某条现行题文 B 相同、但原文不同
         （= 只差空格/控制字符/字形的那次题文修正留下的旧键）；
      ② **污染残留**：A 的原文或译文里含页脚授权句（`Copyright © …` 等）
         ——题文里出现授权声明一定是提取缺陷，不可能是题目内容。

    被删条目的旧译**不直接丢**：① 并入现行条目的 ``zh_note``；② 记进
    ``stats.stale_entries_removed``（含完整 en/zh），随时可回查。
    """
    by_squash: dict[str, str] = {}
    for k in current:
        by_squash.setdefault(squash(entries[k].get("en", "")), k)

    removed: list[dict] = []
    for k in list(entries):
        if k in current:                      # 现行题文一律不动
            continue
        e = entries[k]
        en, zh = e.get("en") or "", e.get("zh") or ""
        if not en and not zh:
            continue
        reason = None
        into = None
        # ① 同题旧版
        b = by_squash.get(squash(en)) if en else None
        if b and entries[b].get("en") != en:
            reason = "同题旧版（题文修正前的旧键）"
            into = b
        # ② 污染残留（页脚授权句混进题文/译文）
        elif CONTAM.search(en) or CONTAM.search(zh):
            reason = "污染残留（页脚授权句混进题文/译文）"
            # 这类条目**没有**「压紧同键」的现行版本——它同时还缺了后来补回的从句
            # （L1 第 23 题：旧条目 `…or m Copyright © …` vs 现行完整题文），
            # 所以改用**保守前缀**找同题现行条目：压紧后前 40 字符相同且**唯一**。
            # 找不到就不猜（旧译仍留在 stats 台账里，一样可回查）。
            pre = squash(en)[:40]
            if len(pre) == 40:
                cands = [k2 for k2 in current
                         if squash(entries[k2].get("en", ""))[:40] == pre]
                if len(cands) == 1:
                    into = cands[0]
        if not reason:
            continue
        removed.append({"key": k, "en": en, "zh": zh,
                        "zh_source": e.get("zh_source"), "reason": reason,
                        "merged_into": into})
        if into:
            note = (f"同题旧版/污染残留已清理（{reason}）；旧条目键 {k[:60]}…，"
                    f"旧译留档：{zh or '（无）'}")
            entries[into]["zh_note"] = (note + " "
                                        + (entries[into].get("zh_note") or "")).strip()
        del entries[k]
    return removed


def squash(t: str) -> str:
    """把题文压成「只留字母数字」的形态，用于**跨题文修正**找回中译。

    ⚠️ 2026-10-04 的教训：文本库以**归一化题文**为键，所以**修题文就会换键**——
    `task-14` 修好 DSL-5-TR 的粘连空格 / 截断 / `\\x00` 之后，13 条 DSM 题目的
    中译当场全部落空（新的键在库里没有 zh），而题文修正本身是对的。
    实测这 13 条里有 12 条只是**空格与控制字符**层面的差异，压紧后完全同键，
    所以这条兜底能机械地把中译接回来——**不是猜译**，是同一句原文换了空白。
    """
    return re.sub(r"[^a-z0-9]", "", t.lower())


def main() -> int:
    zh_map, scaf = load_neo_zh()
    prev, prev_stats = load_previous()
    print(f"大五人格中译 {len(zh_map)} 条；脚手架 {len(scaf)} 条；"
          f"上一次文本库 {len(prev)} 条（用于继承中译）")

    # 跨题文修正的中译兜底索引：压紧题文 → 旧条目（仅取带中译的）
    prev_squash: dict[str, dict] = {}
    for e in prev.values():
        if e.get("zh"):
            prev_squash.setdefault(squash(e.get("en", "")), e)

    entries: dict[str, dict] = {}
    for k, e in prev.items():
        # 继承中译 / 注释 / 类别；英文题文以本次重建为准
        entries[k] = {
            "en": e.get("en", ""), "zh": e.get("zh"), "zh_source": e.get("zh_source"),
            "scaffold": e.get("scaffold"), "instruments": [], "codes": [],
            **({"kind": e["kind"]} if e.get("kind") else {}),
            **({"note": e["note"]} if e.get("note") else {}),
            # note_fix 是**数据缺陷修复的留痕**（原文 → 更正 → 依据，见 R3）。
            # 它不是本脚本产生的，必须原样继承：否则重跑一次，修好的说明还在、
            # 「为什么改、依据哪句话」却没了——那等于把溯源记录静默删掉。
            **({"note_fix": e["note_fix"]} if e.get("note_fix") else {}),
            **({"zh_note": e["zh_note"]} if e.get("zh_note") else {}),
        }
    #: 本次从 data/instruments 重建出来的**现行题文**键（同题旧版清理的判据）
    current: set[str] = set()
    files = [p for p in sorted(glob.glob(
        os.path.join(ROOT, "data", "instruments", "*.json")))
        if os.path.basename(p) != "catalog.json"]

    for p in files:
        d = json.load(open(p, encoding="utf-8"))
        code = d["instrument"]
        for it in d["items"]:
            k = norm(it["text"])
            if not k:
                continue
            current.add(k)
            e = entries.setdefault(k, {
                "en": it["text"], "zh": None, "zh_source": None,
                "scaffold": None, "instruments": [], "codes": [],
            })
            # 英文题文以本次重建为准（提取器可能修过题文）
            e["en"] = it["text"]
            # 题项类别：`instruction` = 作答指示语（不是量表题项，可能没有英文原文）
            if it.get("kind") == "instruction" and not e.get("kind"):
                e["kind"] = "instruction"
                e["note"] = ("这是作答指示语，不是量表题项；原文此处为 Instructions "
                             "条目，界面应作为引导语呈现，不参与计分。")
            if code not in e["instruments"]:
                e["instruments"].append(code)
            sc = (it.get("source_code") or "").strip()
            if sc and sc not in e["codes"]:
                e["codes"].append(sc)
            # 中译：先按题文匹配（最可靠）
            if k in zh_map:
                if e["zh"] is None:
                    e["zh"] = zh_map[k]
                # 溯源标签跟着来源走：旧库继承下来的、记着路径的标签已失效，
                # 值一致时改写成当前源头（值不一致就不动，避免张冠李戴）。
                if e["zh"] == zh_map[k] and stale_source_label(e.get("zh_source")):
                    e["zh_source"] = ZH_SOURCE
            if e["scaffold"] is None and k in scaf:
                e["scaffold"] = scaf[k]
            # 中译兜底：题文被**修正过**（空格/控制字符/字形）时键会变，
            # 按「压紧后同键」把旧库的中译接回来（见 squash 的说明）。
            # ⚠️ 只在**内容的非空白部分完全一致**时命中——若修正真的改了字句
            #    （如 L1 第 23 题补回了缺失的从句），压紧键不同，**不会**误接旧译，
            #    该条会以「无中译」暴露出来，由翻译流程重新出稿。
            if e["zh"] is None:
                donor = prev_squash.get(squash(it["text"]))
                if donor:
                    e["zh"] = donor.get("zh")
                    e["zh_source"] = donor.get("zh_source")
                    e["zh_note"] = ("题文修正后按「压紧同键」继承（仅空白/字形差异，"
                                    "字句未变）")

    have_zh = sum(1 for e in entries.values() if e["zh"])
    # ── 同题旧版 / 污染残留清理（R3：错误内容必须清掉，不是留痕）──
    #    必须在统计与写盘**之前**做，否则旧条目仍会被算进覆盖率。
    stale_removed = purge_stale(entries, current)
    # ── 译文复核状态 + 修正表（唯一真相源：data/text-db/reviewed-corrections.json）──
    review = apply_review(entries)
    # ── 去掉 `zh` 里「又把英文原文抄一遍」的括号内嵌（D27 实现方式反转；R2 三部分并列）──
    paren_stripped = strip_parenthetical_english(entries)
    have_zh = sum(1 for e in entries.values() if e["zh"])
    # 中译文本卫生：继承来的旧稿可能带**控制字符**与首尾/连续空白。
    # ⚠️ 实测睡眠册第 1/5 题的旧英文题面里混着 `\x00`（PDF 的选择框字形），
    #    当时的译文**把 `\x00` 一起抄了进去**：`'我难以保持睡眠。 \x00 \x00 \x00 \x00'`。
    #    所以这里同时清控制字符与空白——**不动字词**。
    _CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
    for e in entries.values():
        if e.get("zh"):
            e["zh"] = re.sub(r"\s+", " ", _CTRL.sub(" ", e["zh"])).strip()
    have_scaf = sum(1 for e in entries.values() if e["scaffold"])
    total_items = sum(len(json.load(open(p, encoding="utf-8"))["items"])
                      for p in files)
    print(f"\n量表 {len(files)} 套，题项（含重复）{total_items} 道")
    print(f"去重后不同题文 {len(entries)} 条")
    print(f"  已有中译 {have_zh} 条（{have_zh / len(entries) * 100:.1f}%）")
    print(f"  已有注释 {have_scaf} 条（{have_scaf / len(entries) * 100:.1f}%）")
    if stale_removed:
        print(f"  清理同题旧版/污染残留 {len(stale_removed)} 条"
              f"（其余孤儿保留为中译资产）")
        for x in stale_removed:
            print(f"    · {x['reason']}：{x['en'][:52]!r}")
    if review.get("relabelled"):
        print(f"  译文复核状态更新 {review['relabelled']} 条 → {review['label']!r}"
              f"（本次修正确 {review['corrected']} 条）")
    if paren_stripped:
        print(f"  去掉 zh 里内嵌的英文原文 {paren_stripped} 处"
              f"（R2：英文原文由 `en` 字段并列承担，不再混排进中译）")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump({
            "schema": "text-db/1.0",
            "note": "统一文本库：以归一化英文题文为键去重；zh 为中文题文，"
                    "scaffold 为逐题注释（承重词/常见误读/算不算/边界情形）",
            "sources": {
                "en": "data/instruments/*.json（各自的提取器产物）",
                "zh": ZH_SOURCE,
                "scaffold": SCAFFOLD_SOURCE,
            },
            "stats": {
                "instruments": len(files), "items_total": total_items,
                "entries": len(entries), "with_zh": have_zh,
                "with_scaffold": have_scaf,
                # translated_batches 是 collect_translations_from_disk.py 维护的账目
                # （记「哪些译文批次已回写」），不在本脚本的输入里。
                # 必须原样继承：否则跑一次本脚本就把这份账清空——实测当时
                # data/text-db/pending/ 已无残留文件，collect 只能把空集写回去
                # （92 批的记录瞬间归零）。这是重建脚本的通用规矩：
                # **下游维护的元数据要继承，不能当自己的产物重算**。
                "translated_batches": prev_stats.get("translated_batches") or [],
                # 同题旧版 / 污染残留的清理台账（含完整 en/zh，可回查）。
                # ⚠️ **必须累积继承**：清理是一次性动作，重跑时 `purge_stale` 返回空，
                #    若这里直接写 `stale_removed`，上一轮的记录会被空列表覆盖——
                #    实测就这么丢掉过一次（被删条目的旧译是「留档备查」的，不能丢）。
                "stale_entries_removed": _merge_removed(
                    prev_stats.get("stale_entries_removed") or [], stale_removed),
                "stale_entries_removed_count": len(_merge_removed(
                    prev_stats.get("stale_entries_removed") or [], stale_removed)),
                # 译文复核（AI 逐条 + 仲裁）的账目
                "translation_review": {
                    "source": REVIEW_REL,
                    "reviewed_count": review.get("reviewed", 0),
                    "relabelled": review.get("relabelled", 0),
                    "corrected": review.get("corrected", 0),
                    "label": review.get("label", ""),
                },
            },
            "entries": entries,
        }, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write("\n")
    print(f"\n✓ 已写出 {os.path.relpath(OUT, ROOT)}"
          f"（{os.path.getsize(OUT) / 1024:.0f} KB）")
    _write_index(entries)
    return 0


def _write_index(entries: dict) -> None:
    """顺带生成 ``data/text-db/index-norm.json``（``{norm_key: entry key}``）。

    **只由 entries 派生**（不再有任何别名）：与 text-db.json 同一个 entries 对象 →
    索引不可能与库漂移；确定性序列化（sort_keys + UTF-8 + LF + 结尾换行）→
    重复生成字节一致。查不到时怎么回退，见 ``textkey.lookup`` 的 ``fallbacks``。
    """
    index = build_index(entries)
    with open(INDEX, "wb") as fh:
        fh.write(render_index(entries))
    print(f"✓ 已写出 {os.path.relpath(INDEX, ROOT)}"
          f"（{len(index)} 键 = {len(entries)} 条 entry；{os.path.getsize(INDEX) / 1024:.0f} KB）")
    collisions = index_collisions(entries)
    if collisions:
        print(f"⚠️ 归一化后有 {len(collisions)} 组 entry key 撞车（索引取排序最小的那个，"
              f"查表会命中其中一条）：")
        for nk, keys in list(collisions.items())[:10]:
            print(f"    · {nk!r} ← {keys}")


if __name__ == "__main__":
    sys.exit(main())
