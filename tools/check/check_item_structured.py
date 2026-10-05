#!/usr/bin/env python3
"""守卫：三级结构化文本（量表级 / 锚点级 / 选项级）必须**可核对**，且不许退回「大量重复」。

为什么要它
==========
这一层是「文档 → 界面」的最后一跳，界面会把这里的每一句话直接显示给用户。三种失败都是**静默**的：

1. `text_en` / `text_zh` 与上游对不上（重新生成时被手工改过，或 join 错位）——
   界面会显示**别人的题文**，不报错，只是错。
2. 同一把尺子（同一 `scale_id`）在各题上不一致——用户会以为刻度变了。
3. **同一句提醒被复制进几百个选项**（`task-22` 用户点名的问题：改前 IPIP 一句 ×300、
   PID-5 四句各 ×220）。这是 V13 的职责：**同一句在同一量表内不得在超过 N 个选项里重复**。

三级结构（`task-22`）
====================
    instrument_guide            量表级：量表性质、作答说明、非诊断声明、按维度的敏感提示、反向计分
    scale_guides[scale_id]      锚点级：时间窗、这组程度词的共同说明、**量化状态说明**（凭自知只说一次）
    items[].response.options    选项级：只留 v / label_en / label_zh（逐题锚点的册子写逐题语义）

校验项（任一不过 → 退出码 1）
============================
V1  11 套文件齐备；题数 / id / order 与量表包一致
V2  `text_en` 与量表包 `items[].text` **逐字节相同**——**除非**该题登记了纯排版修复
    （`content/en-repairs.json` 的 `repairs`）：那时 `text_en` 应等于 `repaired`，
    而 `text_en_verbatim` 必须等于源文原样。
V3  `text_zh` 与 `data/text-db` 的 `zh` **逐字节相同**，`text_zh_source` 与文本库一致
V4  三级齐全：有 `instrument_guide`；每个用到的 `scale_id` 都有 `scale_guide`；
    表级锚点的 guide 必须给全该组每个 v（含 `meaning_zh`）；逐题锚点册的题上必须有 `label_zh`
V5  同一 `scale_id` 内选项集合一致；逐题锚点册逐字等于包内 options
V6  表级锚点的 `label_en` 必须等于包内 `response_format.labels`（IPIP 除外：包内是瑞典语标签）
V7  锚点表完整：用到的 scale 都在清单里；清单里登记的都被用到
V8  字段齐全（id/order/text_en/text_zh/response）；`notes_zh` **可以不存在**（空 = 不显示提醒），
    存在时每条必须有 `text` 与 `source`
V9  生成物未被手改：重新生成并逐字节比对
V10 覆盖率统计（打印，不判失败）
V11 **每个选项都要能回答「大概几天/几次」或「没有统一标准，得我自己判断」**：
    有定量数字 **或** 其所属锚点表的 `quantification_note_zh` 明确声明凭自知；两者都无 → 报错
V12 `quantification` 自洽：counted ⇒ unit/range/text_zh/source 齐全、basis ≠ self_report 且确有数字；
    self_report ⇒ basis=self_report、有 source，且**不得**出现定量数字
V13 **冗余**：同一句话（≥8 字）在同一量表内不得出现在 N 个以上选项里（默认 N=2）；
    逐题注释同理。这条正是防止退回「把高级内容塞进低级选项」

schema 2.1 新增（`task-27`）
===========================
V14 **每题 `scenario_zh` 必填**：非空，且 20–60 个汉字（按 `[\u4e00-\u9fff]` 计数）
V15 `scenario_zh` 不得出现**内部/开发者词汇**（量表 / 条目 / 本题 / 该题 / 维度 / facet /
    DSM / 临床 / 文献 / 原文 / 直译 / 排版 / 缺空格 / 漏空格 / 噪声 / scaffold / 模板 /
    「测……」构念标签 / `E3`、`pid5_xxx` 这类代码），也不得与 `text_zh` 逐字相同或仅差标点
V16 `notes_zh` 每条同样禁内部词汇，且**每题最多 1 条**
V17 `text_en_verbatim` / `text_en_repairs` **只在** `text_en_verbatim != text_en` 时存在；
    `text_en` 不得含**保守可判定**的排版噪声（见 NOISE_* 的判据与白名单说明）
V18 `data/item-scenes.json` 的 id 全集 == 11 个量表的 id 全集（与 merge 的硬校验呼应，
    防「绕过 merge 手改」）

用法
====
    python tools/check/check_item_structured.py
    python tools/check/check_item_structured.py --no-regen
    python tools/check/check_item_structured.py --max-repeat 2
    python tools/check/check_item_structured.py --require-full      # 流水线闸门（D113）
    python tools/check/check_item_structured.py --scenes .tmp/item-scenes.json \
        --out-dir .tmp/items-structured                            # 验证机制（不读 data/）

`--require-full` 与默认模式的区别
================================
默认模式：V1–V18 **全部照报**，任一命中即退出码 1（这是给人看的完整报告）。
`--require-full`：在上面的基础上，把**覆盖率**也当硬失败——每套 `with_scenario` 必须
等于该套题数、11 套 `items` 合计必须等于 `data/instruments/` 的题数、且
`data/item-scenes.json` 必须存在。这是给**流水线闸门**用的口径（沿用 D113）：
打包 `ui/` 前调用它，schema 2.1 没落地就别生成前端数据包。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root, force_utf8_io  # noqa: E402

ROOT = find_root()
INST = os.path.join(ROOT, "data", "instruments")
DEFAULT_OUT = os.path.join(ROOT, "data", "items-structured")
DEFAULT_SCENES = os.path.join(ROOT, "data", "item-scenes.json")
EN_REPAIRS = os.path.join(ROOT, "content", "en-repairs.json")
TEXT_DB = os.path.join(ROOT, "data", "text-db", "text-db.json")
UNAVAILABLE = "未取到权威锚点定义"
MIN_LEN = 8          # 多短的句子不算「重复」（避免「0 次」这类短标签互相干扰）

#: schema 2.1（task-27）：情景句的汉字数区间
SCENE_MIN_HAN, SCENE_MAX_HAN = 20, 60

#: V15/V16：这些词是**给开发者看的**，不该出现在用户可见文案里。
#: 逐条都是「出现在用户眼前会暴露内部视角」的词——不是文风偏好。
BANNED_WORDS = (
    "量表", "条目", "本题", "该题", "维度", "DSM", "临床", "文献",
    "原文", "直译", "排版", "缺空格", "漏空格", "噪声", "scaffold", "模板",
)
#: 「测……」构念标签：只认**从句首开始**的「测」，避免误伤「检测 / 推测 / 测量学」这类正常词。
BANNED_CONSTRUCT_RE = re.compile(r"(?:^|[，。；：、,.;:\s（(])测[\u4e00-\u9fff]{1,8}")
#: facet / 内部代码：E3、N1、pid5_grandiosity、ipip_neo_001、dsm5trl2anger_01
BANNED_CODE_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:[A-Z]\d|(?:ipip_neo|pid5|dsm5trl2[a-z]*)_\d+)(?![A-Za-z0-9_])")
#: 只在 V15 里比对「与 text_zh 逐字相同或仅差标点」时去掉的东西
PUNCT_RE = re.compile(r"[\s，。；：、！？「」『』（）()《》〈〉“”‘’\"'·,.;:!?—–\-…]+")

#: V17 的「排版噪声」保守判据 + 白名单。**先说清楚它不覆盖什么**：
#: 「缺空格」里最难判的一类是 `behonest` / `enjoylife` 这种**全小写长词粘连**——
#: 没有词表就无法判定（`understanding` 也是长词）。那类由 `task-31` 的
#: `tools/check/check_item_typo_repair.py` 做逐条普查与留痕；本守卫只做
#: **不会误报**的那几条，宁可少抓也不产生假红。
NOISE_MIXED_CASE_RE = re.compile(r"[a-zà-ÿ]{2,}[A-Z][a-z]")     # I ama / timeHas
NOISE_SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+[,.;:!?]")         # 词 ,词
NOISE_DOUBLE_SPACE_RE = re.compile(r"[^\s] {2,}[^\s]")           # 词  词
#: 标点后**直接**接字母（数字千分位 `1,000` 因 lookahead 不含数字而天然不匹配）
NOISE_JOINED_PUNCT_RE = re.compile(r"[,;:](?=[A-Za-zà-ÿ])")
#: 撇号后直接接 ≥2 个字母且不是缩写（`peoples'problems`）——注意 `people's`（后接 1 字母）不查
NOISE_APOS_JOINED_RE = re.compile(r"[a-zà-ÿ][’'](?=[a-zà-ÿ]{2,})")
#: 白名单：这些形态**是合法的**，不能被上面几条误报。
NOISE_WHITELIST_RE = re.compile(
    r"\b(?:e\.g|i\.e|etc|vs|U\.S|U\.K|Mr|Mrs|Ms|Dr|St|Inc|Ltd)\.|"
    r"McDonald|iPhone|iPad|eBay|O[’'][A-Z]|Mc[A-Z]|D[’'][A-Z]")
#: 撇号后接字母的**合法**情形：英语缩写（直引号与弯引号都要认——
#: 本库题文用的是弯引号 `’`，只认 `'` 会把 `we’re` 全判成排版噪声）。
NOISE_APOS_OK_RE = re.compile(
    r"(?:n|N)[’']t\b|(?<![A-Za-z])[’'](?:s|re|ve|ll|d|m)\b|[A-Za-z][’'](?:s|re|ve|ll|d|m)\b|"
    r"o[’']clock|y[’']all")



#: V11/V12 判据。**与 tools/survey/ 的两个测绘脚本口径一致**：
#: 「有定量」= 出现**数字+单位**；「凭自知」= 出现明确的自我判断声明。
#: 不看「每天 / 一半」这类**关键词**——手册标签「nearly every day」的中译是「几乎每天」，
#: 它是**未定义**的锚点而不是定量。
NUM_RE = re.compile(
    r"\d+\s*(?:天|日|次|周|月|年|小时|分钟|%|百分比)|"
    r"\d+\s*(?:day|days|time|times|week|month|hour|minute)")
SELF_RE = re.compile(
    r"凭你自己的|自行判断|自己判断|没有统一标准|无统一标准|按你自己的感觉|"
    r"依你自己的|你个人的标准|无量化|未给.{0,6}量化|未提供.{0,6}标准|"
    r"主观判断|取决于你自己")


def load(p: str):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def text_db_index() -> dict[str, dict]:
    idx: dict[str, dict] = {}
    for _k, e in (load(TEXT_DB).get("entries") or {}).items():
        for c in (e.get("codes") or []):
            idx.setdefault(c, e)
    return idx


def pkg_codes() -> list[str]:
    return sorted(f[:-5] for f in os.listdir(INST)
                  if f.endswith(".json") and f != "catalog.json")


# ------------------------------------------------------------------ V1–V3、V8

def check_items(code: str, doc: dict, pkg: dict, tb: dict, problems: list[str],
                repairs: dict[str, dict]) -> None:
    items = doc["items"]
    if len(items) != len(pkg["items"]):
        problems.append(f"V1 {code}: 题数 {len(items)} ≠ 量表包 {len(pkg['items'])}")
    by_id = {i["id"]: i for i in pkg["items"]}
    for it in items:
        src = by_id.get(it["id"])
        if src is None:
            problems.append(f"V1 {code}: {it['id']} 不在量表包里")
            continue
        if it["order"] != src["order"]:
            problems.append(f"V1 {code}: {it['id']} order 不一致")
        # ── V2：text_en 必须等于源文——除非该题登记了**纯排版修复**
        #    那时 text_en = repaired，而 text_en_verbatim 必须等于源文原样。
        verbatim = it.get("text_en_verbatim")
        rep = repairs.get(it["id"])
        if verbatim is None:
            want_en = src["text"]
            if rep and rep.get("repaired") and rep["repaired"] != rep.get("verbatim"):
                problems.append(f"V2 {code}/{it['id']}: en-repairs 登记了修复，"
                                f"但产物里没有 text_en_verbatim（未贯通）")
            if it["text_en"] != want_en:
                problems.append(f"V2 {code}/{it['id']}: text_en 与量表包不一致"
                                f"（{it['text_en'][:30]!r} ≠ {want_en[:30]!r}）")
        else:
            if verbatim != src["text"]:
                problems.append(f"V2 {code}/{it['id']}: text_en_verbatim 与量表包题文不一致"
                                f"（留痕对不上源头）：{verbatim[:30]!r} ≠ {src['text'][:30]!r}")
            want_fixed = (rep or {}).get("repaired")
            if want_fixed and it["text_en"] != want_fixed:
                problems.append(f"V2 {code}/{it['id']}: text_en 不等于 en-repairs 的 repaired")
        e = tb.get(src.get("source_code", ""))
        if it["text_zh"] != (e or {}).get("zh", ""):
            problems.append(f"V3 {code}/{it['id']}: text_zh 与文本库不一致")
        if it["text_zh_source"] != (e or {}).get("zh_source", ""):
            problems.append(f"V3 {code}/{it['id']}: text_zh_source 与文本库不一致")
        if not it.get("text_en") or not it.get("text_zh"):
            problems.append(f"V8 {code}/{it['id']}: 题文原文或中译为空")
        if it.get("reverse_keyed") != (src.get("key", 1) == -1):
            problems.append(f"V8 {code}/{it['id']}: reverse_keyed 与包内 key 不一致")
        # notes_zh 现在**可以不存在**（空 = 界面不显示提醒）；存在则每条要有 text/source
        for n in it.get("notes_zh") or []:
            if not n.get("text") or not n.get("source"):
                problems.append(f"V8 {code}/{it['id']}: 注释缺 text/source")


# ------------------------------------------------------------------ V4–V6

def check_levels(code: str, doc: dict, pkg: dict, problems: list[str]) -> set[str]:
    if not doc.get("instrument_guide"):
        problems.append(f"V4 {code}: 缺 instrument_guide（量表级）")
    guides = doc.get("scale_guides") or {}
    used: set[str] = set()
    by_id = {i["id"]: i for i in pkg["items"]}
    sig: dict[str, tuple] = {}
    for it in doc["items"]:
        sid = (it.get("response") or {}).get("scale_id")
        used.add(sid)
        g = guides.get(sid)
        if g is None:
            problems.append(f"V4 {code}/{it['id']}: scale_guides 里没有 {sid}")
            continue
        opts = (it.get("response") or {}).get("options") or []
        if not opts:
            problems.append(f"V4 {code}/{it['id']}: 没有选项结构")
            continue
        if g.get("options_source") == "item":
            src = by_id[it["id"]]
            got = [(o["v"], o["label_en"]) for o in opts]
            want = [(o["v"], o["text"]) for o in (src.get("options") or [])]
            if got != want:
                problems.append(f"V5 {code}/{it['id']}: 逐题锚点与量表包不一致（{got} ≠ {want}）")
            for o in opts:
                if not o.get("label_zh"):
                    problems.append(f"V4 {code}/{it['id']} v{o['v']}: 缺 label_zh")
        else:
            gv = {o["v"] for o in (g.get("options") or [])}
            if gv != {o["v"] for o in opts}:
                problems.append(f"V4 {code}/{it['id']}: 锚点级 options 的 v 与题上不一致")
            for o in g.get("options") or []:
                if not o.get("meaning_zh"):
                    problems.append(f"V4 {code}/{sid} v{o['v']}: 锚点级缺 meaning_zh")
        key = tuple((o["v"], o["label_en"], o.get("label_zh")) for o in opts)
        # 逐题锚点的册子（ASRM / FOCI）**本来就该逐题不同**，不适用「同一 scale 内一致」
        if g.get("options_source") != "item":
            if sid in sig and sig[sid] != key:
                problems.append(f"V5 {code}/{it['id']}: 同一 scale_id（{sid}）内选项与首题不一致")
            sig.setdefault(sid, key)
    rf = pkg.get("response_format") or (pkg.get("structure") or {}).get("response_format") or {}
    labels = rf.get("labels") or []
    if labels and pkg["instrument"] != "IPIP-NEO":
        for sid, g in guides.items():
            if g.get("options_source") == "item":
                continue
            got = [o["label_en"] for o in (g.get("options") or [])]
            if got and got != labels:
                problems.append(f"V6 {code}: scale {sid} 的 label_en 与包内锚点不一致"
                                f"（{got} ≠ {labels}）")
    return used


# ------------------------------------------------------------------ V11 / V12

def check_quantification(code: str, tag: str, meaning: str, q: dict,
                         scale_note: str, problems: list[str]) -> None:
    """V11：有数字，或其锚点表声明了「凭自知」；V12：quantification 自洽。"""
    if not isinstance(q, dict):
        problems.append(f"V12 {code}/{tag}: 缺 quantification")
        return
    kind = q.get("kind")
    has_num = bool(NUM_RE.search(meaning or ""))
    has_self = bool(SELF_RE.search((scale_note or "") + (meaning or "")))
    if not has_num and not has_self:
        problems.append(f"V11 {code}/{tag}: 既没有定量数字，也没有「凭你自己的判断」声明"
                        f"（退回模糊词了）：{meaning[:48]!r}")
    if kind == "counted":
        missing = [k for k in ("unit", "range", "text_zh", "source") if not q.get(k)]
        if missing:
            problems.append(f"V12 {code}/{tag}: counted 但缺 {missing}")
        if not isinstance(q.get("range"), (list, tuple)) or len(q["range"]) != 2:
            problems.append(f"V12 {code}/{tag}: counted 的 range 必须是 [min, max]")
        if q.get("basis") == "self_report":
            problems.append(f"V12 {code}/{tag}: counted 的 basis 不能是 self_report")
        if not has_num:
            problems.append(f"V12 {code}/{tag}: 标了 counted，但说明里没有数字：{meaning[:48]!r}")
    elif kind == "self_report":
        if q.get("basis") != "self_report":
            problems.append(f"V12 {code}/{tag}: self_report 的 basis 必须是 self_report")
        if not q.get("source"):
            problems.append(f"V12 {code}/{tag}: self_report 必须写明「为什么没有标准」的 source")
        if not has_self:
            problems.append(f"V12 {code}/{tag}: 标了 self_report，但其锚点表没有凭自知声明")
        if has_num:
            problems.append(f"V12 {code}/{tag}: 标了 self_report，说明里却出现定量数字"
                            f"（会被误读成有标准）：{meaning[:48]!r}")
    else:
        problems.append(f"V12 {code}/{tag}: kind 必须是 counted 或 self_report，实际 {kind!r}")


def check_quant_all(code: str, doc: dict, problems: list[str]) -> None:
    guides = doc.get("scale_guides") or {}
    for sid, g in guides.items():
        if g.get("options_source") == "item":
            continue
        note = g.get("quantification_note_zh", "")
        for o in g.get("options") or []:
            eff = (o.get("meaning_zh") or "")
            q = o.get("quantification") or {}
            if q.get("text_zh"):
                eff += "（" + q["text_zh"] + "）"
            check_quantification(code, f"{sid} v{o['v']}", eff, q, note, problems)
    for it in doc["items"]:
        sid = (it.get("response") or {}).get("scale_id")
        g = guides.get(sid) or {}
        if g.get("options_source") != "item":
            continue
        note = g.get("quantification_note_zh", "")
        for o in (it.get("response") or {}).get("options") or []:
            q = o.get("quantification") or {}
            eff = (o.get("meaning_zh") or "") + (o.get("label_zh") or "")
            if q.get("text_zh"):
                eff += "（" + q["text_zh"] + "）"
            check_quantification(code, f"{it['id']} v{o['v']}", eff, q, note, problems)


# ------------------------------------------------------------------ V13 冗余

def collect_option_prose(doc: dict) -> dict[str, Counter]:
    per_scale: dict[str, Counter] = defaultdict(Counter)
    guides = doc.get("scale_guides") or {}
    for it in doc["items"]:
        sid = (it.get("response") or {}).get("scale_id")
        for o in (it.get("response") or {}).get("options") or []:
            for t in (o.get("meaning_zh"), (o.get("quantification") or {}).get("text_zh")):
                if t and len(t.strip()) >= MIN_LEN:
                    per_scale[sid][t.strip()] += 1
        for n in it.get("notes_zh") or []:
            t = (n.get("text") or "").strip()
            if len(t) >= MIN_LEN:
                per_scale[sid][t] += 1
    for sid, g in guides.items():
        if g.get("options_source") == "item":
            continue
        for o in g.get("options") or []:
            t = (o.get("meaning_zh") or "").strip()
            if len(t) >= MIN_LEN:
                per_scale[sid][t] += 1
    return per_scale


def check_redundancy(code: str, doc: dict, n_max: int, problems: list[str]) -> int:
    per_scale = collect_option_prose(doc)
    worst = 0
    for sid, c in per_scale.items():
        for t, n in c.items():
            worst = max(worst, n)
            if n > n_max:
                problems.append(f"V13 {code}/{sid}: 同一句在 {n} 个选项里重复"
                                f"（上限 {n_max}）：{t[:56]!r}")
    # 整册范围：逐题注释也不该跨锚点表重复（时间窗/声明这类必须待在 guide 里）
    allt: Counter = Counter()
    for it in doc["items"]:
        for n in it.get("notes_zh") or []:
            t = (n.get("text") or "").strip()
            if len(t) >= MIN_LEN:
                allt[t] += 1
    for t, n in allt.items():
        worst = max(worst, n)
        if n > n_max:
            problems.append(f"V13 {code}: 逐题注释在 {n} 道题里重复（上限 {n_max}）：{t[:56]!r}")
    return worst


# ------------------------------------------------------------------ V14–V17（schema 2.1）

def han_count(s: str) -> int:
    """汉字数（`[\u4e00-\u9fff]`）。"""
    return len(re.findall(r"[\u4e00-\u9fff]", s or ""))


def banned_hits(s: str) -> list[str]:
    """V15/V16 的内部词汇命中（返回可读的命中列表）。"""
    hits = [w for w in BANNED_WORDS if w in s]
    if BANNED_CONSTRUCT_RE.search(s):
        hits.append("「测……」构念标签")
    if BANNED_CODE_RE.search(s):
        hits.append("facet/内部代码（如 E3、pid5_xxx）")
    return hits


def check_scene(code: str, doc: dict, problems: list[str]) -> None:
    """V14 / V15：情景句必填、长度、以及不许出现内部词汇。"""
    for it in doc["items"]:
        iid = it["id"]
        scene = it.get("scenario_zh")
        if not isinstance(scene, str) or not scene.strip():
            problems.append(f"V14 {code}/{iid}: 缺 scenario_zh（schema 2.1 起必填）")
            continue
        n = han_count(scene)
        if not (SCENE_MIN_HAN <= n <= SCENE_MAX_HAN):
            problems.append(f"V14 {code}/{iid}: scenario_zh 有 {n} 个汉字"
                            f"（要求 {SCENE_MIN_HAN}–{SCENE_MAX_HAN}）：{scene[:40]!r}")
        hits = banned_hits(scene)
        if hits:
            problems.append(f"V15 {code}/{iid}: scenario_zh 出现内部词汇 {hits}：{scene[:48]!r}")
        zh = (it.get("text_zh") or "").strip()
        if zh and PUNCT_RE.sub("", scene) == PUNCT_RE.sub("", zh):
            problems.append(f"V15 {code}/{iid}: scenario_zh 与 text_zh 逐字相同（或仅差标点）"
                            f"——情景必须是题干之外的信息")


def check_notes(code: str, doc: dict, problems: list[str]) -> None:
    """V16：提醒每条禁内部词汇，且每题最多 1 条。"""
    for it in doc["items"]:
        notes = it.get("notes_zh")
        if notes is None:
            continue
        if not isinstance(notes, list):
            problems.append(f"V16 {code}/{it['id']}: notes_zh 必须是数组")
            continue
        if len(notes) > 1:
            problems.append(f"V16 {code}/{it['id']}: notes_zh 有 {len(notes)} 条"
                            f"（每题最多 1 条：提醒是稀缺品）")
        for n in notes:
            t = (n or {}).get("text") if isinstance(n, dict) else n
            hits = banned_hits(t or "")
            if hits:
                problems.append(f"V16 {code}/{it['id']}: 提醒出现内部词汇 {hits}：{(t or '')[:48]!r}")


def check_repairs(code: str, doc: dict, problems: list[str],
                  review: dict[str, dict], stats: dict) -> None:
    """V17：修复留痕只该在**确实改了**的时候存在；`text_en` 不得含保守可判定的排版噪声。

    ⚠️ **已登记在 `needs_lead_review` 的题跳过噪声判定**：那种题的处置权在 Lead
    （`task-31` 明确「一律不应用」），守卫若在这上面报红，等于逼着改一处
    Lead 还没裁决的文本——那是越权。跳过会**计数并打印**，不是静默放过。
    """
    for it in doc["items"]:
        iid = it["id"]
        has_v = "text_en_verbatim" in it
        has_r = "text_en_repairs" in it
        if has_v != has_r:
            problems.append(f"V17 {code}/{iid}: text_en_verbatim / text_en_repairs 必须成对出现")
        if has_v:
            if it["text_en_verbatim"] == it["text_en"]:
                problems.append(f"V17 {code}/{iid}: 有 text_en_verbatim 但它与 text_en 相同"
                                f"（没改就不该留痕）")
            frags = it.get("text_en_repairs")
            if not isinstance(frags, list) or not frags:
                problems.append(f"V17 {code}/{iid}: text_en_repairs 必须是非空数组")
        if iid in review:
            stats["review_skipped"] = stats.get("review_skipped", 0) + 1
            continue
        en = it.get("text_en") or ""
        if NOISE_WHITELIST_RE.search(en):
            # 白名单命中时**整句跳过**噪声判据：形如 "U.S." / "iPhone" 的合法写法
            # 会让 `word.word` 与「小写+大写」这类启发式误报。
            continue
        noise = []
        if NOISE_MIXED_CASE_RE.search(en):
            noise.append("词内缺空格（小写紧接大写，如 I ama）")
        if NOISE_SPACE_BEFORE_PUNCT_RE.search(en):
            noise.append("标点前有多余空格")
        if NOISE_DOUBLE_SPACE_RE.search(en):
            noise.append("词间连续多个空格")
        for m in NOISE_JOINED_PUNCT_RE.finditer(en):
            if NOISE_APOS_OK_RE.search(en[max(0, m.start() - 8):m.start() + 6]):
                continue
            noise.append(f"标点后缺空格（{en[max(0, m.start() - 12):m.start() + 12]!r}）")
            break
        if NOISE_APOS_JOINED_RE.search(en) and not NOISE_APOS_OK_RE.search(en):
            noise.append(f"撇号后缺空格（{en[:40]!r}）")
        if noise:
            problems.append(f"V17 {code}/{iid}: text_en 仍有排版噪声 {noise}：{en[:56]!r}"
                            f"（修不了就登记进 content/en-repairs.json 的 needs_lead_review）")



def check_scenes_coverage(scenes: dict | None, scenes_path: str,
                          want_ids: set[str], problems: list[str]) -> None:
    """V18：`data/item-scenes.json` 的 id 全集 == 11 个量表的 id 全集。

    与 `merge_scenes.py` 的硬校验呼应——即使有人绕过 merge 手改 `data/`，
    这条也会当场抓住（缺 / 多 / schema 不对）。
    """
    rel = os.path.relpath(scenes_path, ROOT)
    if scenes is None:
        problems.append(f"V18 缺 {rel} —— schema 2.1 的情景句没有落地（先跑 merge_scenes.py）")
        return
    got = set(scenes)
    missing, extra = want_ids - got, got - want_ids
    if missing:
        problems.append(f"V18 {rel} 缺 {len(missing)} 个 id（{sorted(missing)[:5]}…）"
                        f"——与 11 个量表的 id 全集不等")
    if extra:
        problems.append(f"V18 {rel} 多出 {len(extra)} 个 id（{sorted(extra)[:5]}…）")


# ------------------------------------------------------------------ V9

def _build_module():
    """导入生成器（复用它的常量与构建函数，避免两套口径漂移）。"""
    sys.path.insert(0, os.path.join(ROOT, "tools", "build"))
    import build_item_structured as B  # noqa: E402
    return B


def load_repairs_for_check(path: str) -> tuple[dict[str, dict], dict[str, dict]]:
    """读 `content/en-repairs.json`（缺失 = 本轮没有修复，返回空表）。"""
    try:
        return _build_module().load_repairs(path)
    except (ValueError, OSError) as exc:                  # 格式坏掉要报出来，不能静默当空
        print(f"⚠ 读 {os.path.relpath(path, ROOT)} 失败：{exc}（按「无修复」继续）")
        return {}, {}


def check_regeneration(problems: list[str], out_dir: str, scenes: dict,
                       repairs: dict[str, dict]) -> None:
    """V9：重新生成一遍，与磁盘逐字节比对（抓「手改生成物」与「生成器已过期」）。

    ⚠️ 生成器现在多了两个输入（情景 + 英文排版修复），这里必须一并喂进去，
    否则重生成结果必然与磁盘不同——那会把真实问题淹在假红里。
    """
    B = _build_module()
    anchors = B.load(B.ANCHORS)
    tb = B.text_db_index()
    facets = B.facet_records()
    for code in B.instrument_codes():
        built = B.build_instrument(code, anchors, tb, facets, scenes, repairs, [])
        p = os.path.join(out_dir, f"{code}.json")
        disk = load(p) if os.path.exists(p) else None
        if disk != built:
            problems.append(f"V9 {code}: 生成物与重新生成的结果不一致（被手改或生成器已过期）")


def main() -> int:
    force_utf8_io()          # 入口第一件事：GBK 控制台下不许崩（见 tools/_root.py）
    ap = argparse.ArgumentParser(description="校验三级结构化文本")
    ap.add_argument("--no-regen", action="store_true", help="跳过 V9 重新生成比对")
    ap.add_argument("--max-repeat", type=int, default=2, help="V13 同一句在几个选项内允许重复")
    ap.add_argument("--require-full", action="store_true",
                    help="流水线闸门模式（D113）：覆盖率也必须满（schema 2.1 未落地就阻断）")
    ap.add_argument("--out-dir", default=DEFAULT_OUT,
                    help="产物目录（默认 data/items-structured；验证机制时可指向 .tmp/…）")
    ap.add_argument("--scenes", default=DEFAULT_SCENES,
                    help="情景合并产物（默认 data/item-scenes.json；验证机制时可指向 .tmp/…）")
    ap.add_argument("--en-repairs", default=EN_REPAIRS,
                    help="英文排版修复留痕（默认 content/en-repairs.json；验证机制时可指向 .tmp/…）")
    args = ap.parse_args()

    problems: list[str] = []
    idx_path = os.path.join(args.out_dir, "index.json")
    if not os.path.exists(idx_path):
        print(f"❌ 缺 {os.path.relpath(idx_path, ROOT)} —— 先跑 build_item_structured.py")
        return 1
    index = load(idx_path)
    tb = text_db_index()
    codes = pkg_codes()

    # 情景合并产物：V18 用；也供 V14–V17 的「作者文件 ↔ 产物」对照
    scenes_doc = load(args.scenes) if os.path.exists(args.scenes) else None
    scenes = (scenes_doc or {}).get("items") if scenes_doc else None
    want_ids: set[str] = set()
    for code in codes:
        pkg = load(os.path.join(INST, f"{code}.json"))
        want_ids |= {it["id"] for it in pkg["items"]}

    print(f"校验 {len(index.get('instruments', []))} 套三级结构化文本"
          f"（V13 上限 {args.max_repeat}）")
    print(f"情景来源：{os.path.relpath(args.scenes, ROOT)}"
          f"（{'已加载' if scenes is not None else '缺失'}）")
    _rep, _review = load_repairs_for_check(args.en_repairs)
    if _review:
        print(f"英文排版修复：应用 {len(_rep)} 条；**待 Lead 裁决 {len(_review)} 条（一律不应用）**")
    elif _rep:
        print(f"英文排版修复：应用 {len(_rep)} 条")
    else:
        print("英文排版修复：无（content/en-repairs.json 不存在或为空）")
    print()

    worst = 0
    stats: dict = {}
    for code in codes:
        p = os.path.join(args.out_dir, f"{code}.json")
        if not os.path.exists(p):
            problems.append(f"V1 {code}: 缺 {os.path.relpath(p, ROOT)}")
            continue
        doc = load(p)
        pkg = load(os.path.join(INST, f"{code}.json"))
        check_items(code, doc, pkg, tb, problems, _rep)
        check_levels(code, doc, pkg, problems)
        check_quant_all(code, doc, problems)
        check_scene(code, doc, problems)
        check_notes(code, doc, problems)
        check_repairs(code, doc, problems, _review, stats)
        worst = max(worst, check_redundancy(code, doc, args.max_repeat, problems))

    # V7 锚点表完整
    IPIP_PREFIX = "ipip-neo.accuracy_1_5."
    used = set()
    for e in index.get("instruments", []):
        used |= set(e.get("scales_used", []))
    declared = set(index["scale_table"])
    for sid in sorted(s for s in used - declared if not s.startswith(IPIP_PREFIX)):
        problems.append(f"V7 用到的 scale 未登记在锚点表：{sid}")
    if "<ipip>" not in declared:
        problems.append("V7 清单里缺 IPIP 锚点模板")

    # V18：情景 id 全集 == 11 个量表的 id 全集
    check_scenes_coverage(scenes, args.scenes, want_ids, problems)

    # --require-full（D113 闸门）：覆盖率不满也算硬失败
    gate: list[str] = []
    if args.require_full:
        t0 = index.get("totals", {})
        n_items = t0.get("items")
        n_scene = t0.get("with_scenario")
        if n_items != len(want_ids):
            gate.append(f"totals.items={n_items} ≠ data/instruments 的 {len(want_ids)} 题")
        if n_scene != n_items:
            gate.append(f"totals.with_scenario={n_scene} ≠ items={n_items}"
                        f"（schema 2.1 情景没有全覆盖）")
        for e in index.get("instruments", []):
            c = e
            if c.get("with_scenario") != c.get("items"):
                gate.append(f"{e['code']}: with_scenario={c.get('with_scenario')}"
                            f" ≠ items={c.get('items')}")

    if not args.no_regen and scenes is not None:
        check_regeneration(problems, args.out_dir, scenes, _rep)

    t = index.get("totals", {})
    print("— 覆盖率 —")
    print(f"  题 {t.get('items')}｜有题文原文 {t.get('with_text_en')}｜有中译 {t.get('with_text_zh')}"
          f"｜选项 {t.get('options')}｜锚点表 {t.get('scales')}")
    print(f"  选项级语义 {t.get('option_level_meanings')} 个（逐题锚点册）"
          f"｜语义在锚点级：有定量 {t.get('options_quantified')}"
          f"｜凭自知 {t.get('options_self_report')}")
    print(f"  情景展示 {t.get('with_scenario')}｜作答提醒 {t.get('with_notes')}"
          f"｜英文排版修复 {t.get('text_en_repaired')}")
    if stats.get("review_skipped"):
        print(f"  V17：跳过 {stats['review_skipped']} 道已登记待 Lead 裁决的题"
              f"（needs_lead_review —— 处置权不在作者/守卫）")
    qbt = index.get("quantification_basis_totals") or {}
    if qbt:
        print("  量化依据分布：" + "、".join(f"{k}={v}" for k, v in sorted(qbt.items())))
    print(f"  选项级冗余度：最高重复 ×{worst}（上限 {args.max_repeat}）")

    gaps = index.get("known_gaps") or []
    if gaps:
        print(f"\n— 已知缺口 {len(gaps)} 条（如实登记）—")
        for g in gaps:
            print(f"  · {g['what'][:70]}")

    print("\n" + "─" * 72)
    if gate:
        problems.extend(f"V18（--require-full）{x}" for x in gate)
    if problems:
        print(f"❌ {len(problems)} 处问题：")
        for x in problems[:40]:
            print("  -", x)
        if len(problems) > 40:
            print(f"  …还有 {len(problems) - 40} 处")
        return 1
    print("✅ 全部通过（V1–V18）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
