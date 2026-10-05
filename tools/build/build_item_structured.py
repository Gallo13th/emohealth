#!/usr/bin/env python3
"""把量表文档做成**三级结构化文本**（提示分级：量表级 → 锚点级 → 选项级）。

为什么要分级（`task-22`，用户原话）
==================================
> **不要在每个选项中都注明某些完全相同的注释**。应该做好**提醒的分级**内容，
> **不应该把高级内容放进低级选项里大量重复**。以及进一步清理没有必要写出来的注释，
> 你要以一个**仅仅是来参与量表测评的用户**的角度出发，而非一个**专业的心理学工作者
> 来做量表文本本身研究**的态度出发。

改之前实测：IPIP-NEO 的一句后缀在 **300 个选项**里逐字重复、PID-5 的 4 句各 **220 次**、
2780 个选项只有 211 种说明句。这就是「把高级内容塞进低级选项」。

三级结构
========
① **`instrument_guide`（量表级，整个量表一次）**
   量表性质、总体作答说明、非诊断声明、**按维度**的敏感内容提示、反向计分说明。
② **`scale_guides[scale_id]`（锚点级，每组程度词一次）**
   时间窗、这组程度词的**共同说明**（`anchor_note_zh`）、
   **`quantification_note_zh`**——「本量表没有给量化标准，凭你自己的判断」这类
   对全表相同的话**只说一次**，以及每个选项**特有**的语义 `options[].meaning_zh`。
③ **选项级（每题每选项）**：只留 `v` / `label_en` / `label_zh`；语义与量化状态
   通过 `response.scale_id` 到锚点级取。**逐题锚点**的两册（ASRM 整句陈述 / FOCI 逐题锚点）
   语义本身随题而变，按题写在该题自己的 `options[].meaning_zh` 里。

题文与中译
==========
`text_zh` 逐字节取自 `data/text-db/text-db.json`（唯一中译源），不变。
`text_en` 默认逐字节取自量表包 `items[].text`；**若 `content/en-repairs.json`
登记了该题的纯排版修复**，则 `text_en` 取修复后的文本，并额外写两个**内部字段**
`text_en_verbatim`（源文件原样）与 `text_en_repairs`（逐处改动，如 `["behonest → be honest"]`）。
不涉及修复的题**不写**这两个字段——它们只是留痕，不上界面。

情景与提醒（schema 2.1，`task-27`）
==================================
* **`scenario_zh`（必填）**：每题一句情景展示，来自 `data/item-scenes.json`
  （由 `tools/build/merge_scenes.py` 合并 `content/scenes/*.json` 得到）。
  **缺一条就是错，直接报错退出**——不许用占位符顶上（占位符会一路流到用户眼前）。
* **`notes_zh`：完全由 `data/item-scenes.json` 的 `notes` 覆盖**（不是追加）。
  空 → 该题**不写 `notes_zh` 字段**（界面就不显示）。
  ⚠️ 这里踩过坑：旧的 `notes_zh` 是「先生成、再从 text-db 的 note/scaffold 拼」，
  而 text-db 重跑时那批字段会被覆盖 → 挂上去的提醒**静默消失**（生成器重跑盲区）。
  现在改为**每次由同一份作者文件重新派生**，所以覆盖是幂等的：连跑两次字节一致。

用户视角清理（`task-22`，仍然有效）
==================================
- 删掉「手册为什么没给天数」「按 14 天窗口推算」这类**研究者关心的元说明**；
  它们留在锚点表的 `source` 里（内部核对用），**不进用户界面文本**。
- 但**「没有统一标准、凭你自己的判断」这个事实必须保留**（诚实性，不是研究内容），
  位置从「每个选项」提到「每个锚点表一次」。

依据与不编造（`PLAN.md` R1）
============================
`quantification.basis` 分层不变：`manual_verbatim` / `manual_derived`（该册手册标签 ×
该册手册窗口的算术推导）/ `self_report`（手册未定义，如实声明）。取不到权威锚点就留空 + 标注。

产物
====
    data/items-structured/<code>.json   11 套，三级结构 + scenario_zh
    data/items-structured/index.json    清单：量表 → 锚点表 → 题数 + 覆盖率 + 冗余度

用法
====
    python tools/build/build_item_structured.py            # 生成
    python tools/build/build_item_structured.py --check    # 只比对，不写盘
    python tools/build/build_item_structured.py --scenes .tmp/item-scenes.json \
        --out-dir .tmp/items-structured                    # 验证机制（不落 data/）
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402

ROOT = find_root()
INST_DIR = os.path.join(ROOT, "data", "instruments")
TEXT_DB = os.path.join(ROOT, "data", "text-db", "text-db.json")
ANCHORS = os.path.join(ROOT, "content", "item-anchors.json")
FACETS = os.path.join(ROOT, "content", "facets")
DEFAULT_OUT_DIR = os.path.join(ROOT, "data", "items-structured")
DEFAULT_SCENES = os.path.join(ROOT, "data", "item-scenes.json")
EN_REPAIRS = os.path.join(ROOT, "content", "en-repairs.json")

SCHEMA_VERSION = "2.0"
BANNER = ("本文件由 tools/build/build_item_structured.py 生成，请勿手改；"
          "改动请改 content/item-anchors.json、content/scenes/*.json、"
          "content/en-repairs.json 或上游数据后重跑。")
SCENES_SOURCE = "data/item-scenes.json（由 content/scenes/*.json 合并）"

#: 需要附「非诊断声明」的量表（DSM-5-TR 体系）
NON_DIAGNOSTIC = {"DSM5TR-L1"} | {f"DSM5TR-L2-{x}" for x in
                                 ("Anger", "Anxiety", "Depression", "Mania",
                                  "Repetitive", "Sleep", "Somatic", "Substance")}


def load(p: str):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def instrument_codes() -> list[str]:
    return sorted(f[:-5] for f in os.listdir(INST_DIR)
                  if f.endswith(".json") and f != "catalog.json")


# ------------------------------------------------------------------ 读入

def text_db_index() -> dict[str, dict]:
    idx: dict[str, dict] = {}
    for _k, e in (load(TEXT_DB).get("entries") or {}).items():
        for c in (e.get("codes") or []):
            idx.setdefault(c, e)
    return idx


def facet_records() -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not os.path.isdir(FACETS):
        return out
    for fn in sorted(os.listdir(FACETS)):
        if fn.endswith(".record.json"):
            rec = load(os.path.join(FACETS, fn))
            out[rec["identity"]["id"].split(".")[-1]] = rec
    return out


def load_scenes(path: str) -> dict[str, dict]:
    """读每题一句情景展示（`data/item-scenes.json`）。

    完整性由 `tools/build/merge_scenes.py` 硬校验（id 全集 == 606）；这里只负责
    **再确认一次**——`data/` 不是手改的地方，但生成器不能把「文件被换过」当成没事。
    """
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"缺 {os.path.relpath(path, ROOT)} —— 先跑 tools/build/merge_scenes.py")
    doc = load(path)
    if doc.get("schema") != "item-scenes/1.0":
        raise ValueError(f"{os.path.relpath(path, ROOT)} 的 schema 不是 item-scenes/1.0")
    items = doc.get("items") or {}
    if not isinstance(items, dict):
        raise ValueError(f"{os.path.relpath(path, ROOT)} 的 items 不是对象")
    return items


def load_repairs(path: str) -> tuple[dict[str, dict], dict[str, dict]]:
    """读英文排版修复留痕 → `(repairs, needs_lead_review)`。

    **只应用 `repairs`**；`needs_lead_review` 一律不应用（那是待 Lead 裁决的，
    自动应用等于把「可能改措辞」的改动悄悄落进用户可见文本）。
    文件不存在 = 本轮没有修复（返回空表，不报错）。
    """
    if not os.path.exists(path):
        return {}, {}
    doc = load(path)
    if doc.get("schema") != "en-repairs/1.0":
        raise ValueError(f"{os.path.relpath(path, ROOT)} 的 schema 不是 en-repairs/1.0")
    reps = doc.get("repairs") or {}
    review = doc.get("needs_lead_review") or {}
    if not isinstance(reps, dict) or not isinstance(review, dict):
        raise ValueError(f"{os.path.relpath(path, ROOT)} 的 repairs/needs_lead_review 必须是对象")
    return reps, review


def repair_fragments(verbatim: str, repaired: str) -> list[str]:
    """把一处排版修复写成**可读的逐处改动**（内部留痕，如 `behonest → be honest`）。

    按空白切词做 diff：排版缺陷几乎都发生在词边界上（缺空格/多空格/标点后缺空格），
    按词比既能给出「改了什么」，又不会像按字符比那样产出 `→ ' '` 这种没法读的碎片。
    两侧**相同的边界标点**会被去掉（`behonest, → be honest,` → `behonest → be honest`），
    这样留痕读起来是「改了什么」；标点本身不同则原样保留，不隐瞒。
    """
    import difflib

    def _trim(a: str, b: str) -> tuple[str, str]:
        edge = ",.;:!?、，。；：！？"
        while a and b and a[0] == b[0] and a[0] in edge:
            a, b = a[1:], b[1:]
        while a and b and a[-1] == b[-1] and a[-1] in edge:
            a, b = a[:-1], b[:-1]
        return (a, b) if a and b else (a, b)

    a, b = verbatim.split(), repaired.split()
    frags: list[str] = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if tag == "equal":
            continue
        old, new = " ".join(a[i1:i2]), " ".join(b[j1:j2])
        if old and new:
            old, new = _trim(old, new)
            frags.append(f"{old} → {new}")
        elif new:
            frags.append(f"补入 {new}")
        else:
            frags.append(f"删除 {old}")
    if not frags:                       # 只差空白量（词序列相同）——如实说明，不硬造改动
        frags.append("空白规范化（词序列未变）")
    return frags


# ------------------------------------------------------------------ 锚点表 → 中间表示

def _opt(v, label_en, label_zh, meaning="", q=None):
    return {"v": v, "label_en": label_en, "label_zh": label_zh,
            "meaning_zh": meaning, "quantification": q or {}}


def ipip_scale(anchors: dict, facet: str, rec: dict) -> dict:
    """IPIP：官方英文尺子 + **逐 facet** 的行为学阶梯（facet 档案提供）。

    阶梯文本是**这个 facet 的锚点级说明**（该 facet 的 10 道题共用），因此放在锚点级，
    不逐题复制；「IPIP 没有规定各档具体指什么」这类话也只在锚点级说一次。
    """
    tpl = anchors["ipip_template"]
    sem = (rec.get("administration", {}) or {}).get("anchor_semantics", {}) or {}
    opts = []
    missing = False
    for o in tpl["options"]:
        meaning = sem.get(str(o["v"]), "")
        if not meaning:
            missing = True
        opts.append(_opt(o["v"], o["label_en"], o["label_zh"], meaning,
                         dict(tpl["default_quantification"])))
    return {
        "scale_id": tpl["scale_id_pattern"].replace("{facet}", facet),
        "label": f"{tpl['label']}｜{facet}",
        "type": tpl["type"], "points": tpl["points"],
        "min": tpl["min"], "max": tpl["max"],
        "time_frame_zh": tpl["time_frame_zh"], "time_frame_en": tpl["time_frame_en"],
        "instruction_zh": tpl["question_head_zh"],
        "anchor_note_zh": tpl["anchor_note_zh"],
        "quantification_note_zh": tpl["quantification_note_zh"],
        "reverse_keyed_note_zh": None,
        "options": opts, "item_specific": False,
        "source": tpl["meaning_source"].replace("<facet>", facet),
        "label_source": tpl["label_source"],
        "evidence": tpl["evidence"],
        "incomplete": missing,
    }


def table_scale(anchors: dict, sid: str) -> dict:
    s = anchors["scales"][sid]
    default_q = s.get("default_quantification")
    opts = []
    for o in s["options"]:
        q = dict(o.get("quantification") or default_q or {
            "kind": "self_report", "unit": None, "range": None, "window_days": None,
            "text_zh": None, "basis": "self_report", "source": s.get("meaning_source", "")})
        opts.append(_opt(o["v"], o["label_en"], o.get("label_zh", ""),
                         o.get("meaning_zh", ""), q))
    return {
        "scale_id": sid,
        "label": s["label"], "type": s["type"], "points": s["points"],
        "min": s["min"], "max": s["max"],
        "time_frame_zh": s.get("time_frame_zh", ""),
        "time_frame_en": s.get("time_frame_en", ""),
        "instruction_zh": s.get("question_head_zh", ""),
        "anchor_note_zh": s.get("anchor_note_zh", ""),
        "quantification_note_zh": s.get("quantification_note_zh", ""),
        "reverse_keyed_note_zh": s.get("reverse_keyed_note_zh"),
        "options": opts, "item_specific": False,
        "source": s.get("meaning_source", ""),
        "label_source": s.get("label_source", ""),
        "evidence": s.get("evidence", []),
        "incomplete": any(not o["meaning_zh"] for o in s["options"]),
    }


def item_scale(anchors: dict, sid: str, item: dict, pkg: dict) -> dict:
    """逐题锚点的两册（ASRM 整句陈述 / FOCI 逐题锚点）：语义**随题而变**，按题给。

    ⚠️ 这两册的选项语义**不能**提到锚点级（每题的 5 个选项不同），所以写在题上；
    只要确实逐题不同就不构成「重复」——守卫按「同句在几个选项里重复」检查。
    """
    s = anchors["scales"][sid]
    item_options = item.get("options") or []
    lexicon = (s.get("item_lexicon") or {}).get(item["id"])
    statements = (s.get("statements_zh") or {}).get(item["id"]) or {}
    opts = []
    for o in item_options:
        v, label_en = o["v"], o["text"]
        if statements:                                   # ASRM：整句陈述即选项本身
            label_zh = statements.get(str(v), "")
            opts.append(_opt(v, label_en, label_zh, "", dict(s["default_quantification"])))
        elif lexicon:
            entry = ((s.get("lexicons") or {}).get(lexicon) or {}).get(label_en) or {}
            meaning = (entry.get("meaning_zh") or {}).get(item["id"], "")
            opts.append(_opt(v, label_en, entry.get("label_zh", ""), meaning,
                             dict(entry.get("quantification") or {})))
        else:
            opts.append(_opt(v, label_en, "", "", {}))
    return {
        "scale_id": sid,
        "label": s["label"], "type": s["type"], "points": s["points"],
        "min": s["min"], "max": s["max"],
        "time_frame_zh": s.get("time_frame_zh", ""),
        "time_frame_en": s.get("time_frame_en", ""),
        "instruction_zh": s.get("question_head_zh", ""),
        "anchor_note_zh": s.get("anchor_note_zh", ""),
        "quantification_note_zh": s.get("quantification_note_zh", ""),
        "reverse_keyed_note_zh": None,
        "lexicon": lexicon,
        "options": opts, "item_specific": True,
        "source": s.get("option_meaning_source", ""),
        "label_source": s.get("label_source", ""),
        "evidence": s.get("evidence", []),
        "incomplete": any(not o["label_zh"] for o in opts),
    }


def resolve_scale(anchors: dict, pkg: dict, item: dict, facets: dict,
                  cache: dict) -> dict:
    default_sid = anchors["instrument_map"][pkg["instrument"]]["default_scale"]
    if "{facet}" in default_sid:
        facet = (item.get("dimensions") or [""])[0]
        rec = facets.get(facet)
        if rec is None:
            raise KeyError(f"{pkg['instrument']} 的 {item['id']} 找不到 facet 档案 {facet}")
        return ipip_scale(anchors, facet, rec)
    s = anchors["scales"][default_sid]
    if s.get("options_source") == "item":
        return item_scale(anchors, default_sid, item, pkg)
    return cache.setdefault(default_sid, table_scale(anchors, default_sid))


# ------------------------------------------------------------------ 注释（完全由作者文件覆盖）

def item_notes(scene_entry: dict) -> list[dict]:
    """这道题要显示的提醒——**完全来自 `data/item-scenes.json` 的 `notes`**。

    ⚠️ 这里是**覆盖**，不是追加：上一版从 `data/text-db` 的 `note`/`scaffold` 拼提醒，
    等于把作者文案挂在一个会被上游重跑覆盖的字段上——「先生成、后挂载」的字段是
    生成器重跑盲区，挂上去的东西会静默消失。现在每次都由同一份作者文件重新派生，
    所以**连跑两次字节一致**（幂等）。

    空列表 → 上游不写 `notes_zh` 字段（界面就不显示提醒）。
    """
    return [{"text": t, "source": SCENES_SOURCE}
            for t in (scene_entry.get("notes") or [])]


def instrument_guide(anchors: dict, pkg: dict, scales: dict[str, dict],
                     used_dims: set[str], has_reverse: bool) -> dict:
    pol = anchors["policy"]
    ig: dict = {"name": pkg.get("display_name") or pkg["instrument"],
                "instrument": pkg["instrument"],
                "what_it_is_zh": pkg.get("description", "")}
    # 量表级共同信息（若各锚点表一致就提到量表级，免得在 30 个 facet 里各说一遍）
    for field, key in (("time_frame_zh", "time_frame_zh"),
                       ("instruction_zh", "instruction_zh")):
        vals = {s.get(key) for s in scales.values() if s.get(key)}
        if len(vals) == 1:
            ig[field] = vals.pop()
    if pkg["instrument"] in NON_DIAGNOSTIC:
        nd = pol["non_diagnostic_notice"]
        ig["non_diagnostic_notice_zh"] = nd["text"]
        ig["non_diagnostic_source"] = nd["source"]
    if has_reverse:
        ig["reverse_keyed_note_zh"] = (
            "本量表含**反向计分**题：这些题的分数在统计时会反向折算，"
            "你只需按真实情况作答，不用自己换算。")
        ig["reverse_keyed_source"] = "各题包的 items[].key = -1；折算规则见各册手册的 Scoring 段"
    topics = {}
    for dim in sorted(used_dims):
        st = (pol.get("sensitive_topics") or {}).get(dim)
        if st:
            topics[dim] = {"topic": st["topic"], "text": st["text"], "source": st["source"]}
    if topics:
        ig["topic_notices"] = topics
    return ig


def scale_guide(scale: dict) -> dict:
    g = {k: scale[k] for k in
         ("scale_id", "label", "type", "points", "min", "max",
          "anchor_note_zh", "quantification_note_zh", "label_source", "source")
         if scale.get(k)}
    if scale["item_specific"]:
        g["options_source"] = "item"
        if scale.get("lexicon"):
            g["lexicon"] = scale["lexicon"]
    else:
        g["options"] = [{"v": o["v"], "label_en": o["label_en"], "label_zh": o["label_zh"],
                         "meaning_zh": o["meaning_zh"], "quantification": o["quantification"]}
                        for o in scale["options"]]
    return g


# ------------------------------------------------------------------ 生成

def build_instrument(code: str, anchors: dict, tb_index: dict, facets: dict,
                     scenes: dict[str, dict], repairs: dict[str, dict],
                     problems: list[str]) -> dict:
    pkg = load(os.path.join(INST_DIR, f"{code}.json"))
    cache: dict[str, dict] = {}
    items = []
    used: dict[str, dict] = {}
    used_dims: set[str] = set()
    has_reverse = False
    for it in pkg["items"]:
        iid = it["id"]
        scale = resolve_scale(anchors, pkg, it, facets, cache)
        used.setdefault(scale["scale_id"], scale)
        dims = it.get("dimensions", [])
        used_dims |= set(dims)
        tb = tb_index.get(it.get("source_code", ""))

        # ── 情景句：必填。缺就是错，**不许用占位符顶上**（占位符会流到用户眼前）。
        scene = scenes.get(iid)
        if not scene or not (scene.get("scene") or "").strip():
            problems.append(f"{code}/{iid}: 缺 scenario_zh（{SCENES_SOURCE} 里没有这一题）")
            scene = {"scene": "", "notes": []}

        # ── 英文排版修复：只应用 repairs 里逐字对得上源文的那些；其余原样。
        text_en = it["text"]
        repaired_extra: dict = {}
        rep = repairs.get(iid)
        if rep:
            verbatim = rep.get("verbatim", "")
            fixed = rep.get("repaired", "")
            if verbatim != it["text"]:
                problems.append(
                    f"{code}/{iid}: en-repairs 的 verbatim 与量表包题文不一致"
                    f"（留痕对不上源头，拒绝套用）：{verbatim[:40]!r} ≠ {it['text'][:40]!r}")
            elif fixed and fixed != verbatim:
                text_en = fixed
                repaired_extra = {"text_en_verbatim": verbatim,
                                  "text_en_repairs": repair_fragments(verbatim, fixed)}

        notes = item_notes(scene)
        doc = {
            "id": iid,
            "order": it["order"],
            "text_en": text_en,                           # ① 源文或修复后文本
            **repaired_extra,                             #    仅修复过才有（内部留痕）
            "text_zh": (tb or {}).get("zh", ""),          # ② 文本库唯一中译源
            "text_zh_source": (tb or {}).get("zh_source", ""),
            "dimensions": dims,
            "key": it.get("key", 1),
            "reverse_keyed": it.get("key", 1) == -1,
            "source_code": it.get("source_code", ""),
            "text_source": it.get("text_source", ""),
            # ③ 选项级：只留标签；语义/量化在 scale_guides（逐题锚点的册子除外）
            "response": {
                "scale_id": scale["scale_id"],
                "options": ([{"v": o["v"], "label_en": o["label_en"], "label_zh": o["label_zh"],
                              "meaning_zh": o["meaning_zh"],
                              "quantification": o["quantification"]}
                             for o in scale["options"]]
                            if scale["item_specific"] else
                            [{"v": o["v"], "label_en": o["label_en"], "label_zh": o["label_zh"]}
                             for o in scale["options"]]),
            },
            # ④ 情景展示（用户可见，渲染在题干下方）
            "scenario_zh": scene["scene"].strip(),
        }
        # ⑤ 提醒：**完全覆盖**（不是追加）。空 → 不写字段，界面就不显示。
        if notes:
            doc["notes_zh"] = notes
        if it.get("kind"):
            doc["kind"] = it["kind"]
        if scale.get("lexicon"):
            doc["response"]["lexicon"] = scale["lexicon"]
        has_reverse = has_reverse or doc["reverse_keyed"]
        items.append(doc)

    guides = {sid: scale_guide(s) for sid, s in used.items()}
    for sid, s in used.items():
        if s["item_specific"]:
            guides[sid].pop("options", None)

    n_opt = sum(len(i["response"]["options"]) for i in items)
    # 量化覆盖按**选项实例**统计（2780 个），与 task-21 的口径一致；
    # 语义定义则按锚点表统计（重复的句子不再进选项级）。
    qkind: dict[str, int] = {}
    qbasis: dict[str, int] = {}
    for it in pkg["items"]:
        scale = resolve_scale(anchors, pkg, it, facets, cache)
        for o in scale["options"]:
            q = o.get("quantification") or {}
            k = q.get("kind", "missing")
            qkind[k] = qkind.get(k, 0) + 1
            b = q.get("basis", "missing")
            qbasis[b] = qbasis.get(b, 0) + 1
    per_item_opt = sum(len(i["response"]["options"]) for i in items
                       if any(o.get("meaning_zh") for o in i["response"]["options"]))
    out = {
        "schema_version": SCHEMA_VERSION,
        "_note": BANNER,
        "instrument": pkg["instrument"],
        "code": code,
        "display_name": pkg.get("display_name", ""),
        "anchor_table": "content/item-anchors.json",
        "levels_note": ("三级：instrument_guide（量表级，一次）→ scale_guides[scale_id]（锚点级，一组一次）"
                        "→ items[].response.options（选项级，只留标签/逐题特有语义）。"
                        "语义与量化状态经 response.scale_id 到锚点级取；逐题锚点的册子写在题上。"),
        "counts": {
            "items": len(items),
            "with_text_en": sum(1 for i in items if i["text_en"]),
            "with_text_zh": sum(1 for i in items if i["text_zh"]),
            "with_options": sum(1 for i in items if i["response"]["options"]),
            "options": n_opt,
            "scales": len(used),
            "options_quantified": qkind.get("counted", 0),
            "options_self_report": qkind.get("self_report", 0),
            "items_with_notes": sum(1 for i in items if i.get("notes_zh")),
            "reverse_keyed": sum(1 for i in items if i["reverse_keyed"]),
            "option_level_meanings": per_item_opt,
            # schema 2.1（task-27）：情景必填；提醒来自作者文件，可以为 0
            "with_scenario": sum(1 for i in items if i.get("scenario_zh")),
            "with_notes": sum(1 for i in items if i.get("notes_zh")),
            "text_en_repaired": sum(1 for i in items if i.get("text_en_verbatim")),
        },
        "quantification_kind_counts": qkind,
        "quantification_basis_counts": qbasis,
        "scale_item_counts": {sid: sum(1 for i in items if i["response"]["scale_id"] == sid)
                              for sid in used},
        "scales_used": sorted(used),
        "instrument_guide": instrument_guide(anchors, pkg, used, used_dims, has_reverse),
        "scale_guides": guides,
        "items": items,
    }
    return out


def coverage_problems(scenes: dict[str, dict]) -> list[str]:
    """情景句完整性：11 套的**每一道题**都必须有 `scenario_zh`，且不许有多余 id。

    与 `merge_scenes.py` 的硬校验呼应——那里保证 `data/item-scenes.json` 与
    `data/items-structured/` 的 id 全集相等；这里再对**生成器的输入侧**
    （`data/instruments/`）确认一次，防止有人绕过 merge 手改产物。
    """
    problems: list[str] = []
    want: set[str] = set()
    for code in instrument_codes():
        pkg = load(os.path.join(INST_DIR, f"{code}.json"))
        ids = [it["id"] for it in pkg["items"]]
        want |= set(ids)
        missing = [i for i in ids if not (scenes.get(i) or {}).get("scene", "").strip()]
        if missing:
            problems.append(f"{code}: {len(missing)} 题缺情景句（{missing[:5]}…）")
    extra = set(scenes) - want
    if extra:
        problems.append(f"data/item-scenes.json 多出 {len(extra)} 个不在任何量表里的 id"
                        f"（{sorted(extra)[:5]}…）")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description="生成三级结构化文本")
    ap.add_argument("--check", action="store_true", help="只比对，不写盘")
    ap.add_argument("--scenes", default=DEFAULT_SCENES,
                    help="情景合并产物（默认 data/item-scenes.json；验证机制时可指向 .tmp/…）")
    ap.add_argument("--out-dir", default=DEFAULT_OUT_DIR,
                    help="产物目录（默认 data/items-structured；验证机制时可指向 .tmp/…）")
    ap.add_argument("--en-repairs", default=EN_REPAIRS,
                    help="英文排版修复留痕（默认 content/en-repairs.json；验证机制时可指向 .tmp/…）")
    args = ap.parse_args()

    out_dir = args.out_dir
    test_mode = (os.path.abspath(out_dir) != os.path.abspath(DEFAULT_OUT_DIR)
                 or os.path.abspath(args.scenes) != os.path.abspath(DEFAULT_SCENES)
                 or os.path.abspath(args.en_repairs) != os.path.abspath(EN_REPAIRS))
    if test_mode:
        print("⚠ 测试模式：--scenes/--out-dir 不是生产默认值，产物不落 data/")

    anchors = load(ANCHORS)
    tb_index = text_db_index()
    facets = facet_records()
    try:
        scenes = load_scenes(args.scenes)
    except (FileNotFoundError, ValueError) as exc:
        print(f"❌ {exc}")
        return 1
    repairs, needs_review = load_repairs(args.en_repairs)
    if not repairs:
        print(f"注：{os.path.relpath(args.en_repairs, ROOT)} 不存在或为空 —— 本轮不应用排版修复")
    if needs_review:
        print(f"注：en-repairs 有 {len(needs_review)} 条待 Lead 裁决 —— **一律不应用**")

    problems = coverage_problems(scenes)
    if problems:
        print(f"❌ 情景句不完整（{len(problems)} 项）——不从占位符顶上，直接停下：")
        for x in problems[:12]:
            print("  -", x)
        return 1

    os.makedirs(out_dir, exist_ok=True)

    index = {"schema_version": SCHEMA_VERSION, "_note": BANNER,
             "generator": "tools/build/build_item_structured.py",
             "checker": "tools/check/check_item_structured.py",
             "redundancy_survey": "tools/survey/survey_note_redundancy.py",
             "anchor_table": "content/item-anchors.json",
             "scenes_source": "data/item-scenes.json（合并 content/scenes/*.json）",
             "en_repairs_source": "content/en-repairs.json（只应用 repairs）",
             "levels": ["instrument_guide", "scale_guides", "items[].response.options"],
             "known_gaps": anchors.get("known_gaps", []),
             "instruments": [], "scale_table": {}}
    for sid, s in anchors["scales"].items():
        index["scale_table"][sid] = {
            "label": s["label"], "type": s["type"], "min": s["min"], "max": s["max"],
            "options_source": s.get("options_source", "table"),
            "anchor_note_zh": s.get("anchor_note_zh", ""),
            "quantification_note_zh": s.get("quantification_note_zh", ""),
            "label_source": s.get("label_source", ""),
            "meaning_source": s.get("meaning_source", ""),
            "evidence": s.get("evidence", []),
        }
    tpl = anchors["ipip_template"]
    index["scale_table"]["<ipip>"] = {
        "label": tpl["label"], "type": tpl["type"], "min": tpl["min"], "max": tpl["max"],
        "options_source": "per_dimension",
        "anchor_note_zh": tpl["anchor_note_zh"],
        "quantification_note_zh": tpl["quantification_note_zh"],
        "label_source": tpl["label_source"], "meaning_source": tpl["meaning_source"],
        "evidence": tpl["evidence"],
    }

    INDEX_KEYS = ("items", "with_text_en", "with_text_zh", "with_options",
                  "options", "scales", "options_quantified", "options_self_report",
                  "items_with_notes", "reverse_keyed", "option_level_meanings",
                  "with_scenario", "with_notes", "text_en_repaired")

    written = same = 0
    # 先把 11 套**全部构建完**再落盘：这样任何一处问题都不会留下「写了一半」的产物。
    built_all = [(code, build_instrument(code, anchors, tb_index, facets,
                                         scenes, repairs, problems))
                 for code in instrument_codes()]
    if problems:
        print(f"❌ {len(problems)} 处问题（**未写任何文件**）：")
        for x in problems[:20]:
            print("  -", x)
        return 1

    for code, built in built_all:
        path = os.path.join(out_dir, f"{code}.json")
        cur = load(path) if os.path.exists(path) else None
        if args.check:
            print(f"  {'=' if cur == built else '≠'} {code:22} items={built['counts']['items']:>4}")
            if cur != built:
                return 1
            continue
        if cur != built:
            with open(path, "wb") as fh:              # 二进制写：LF、字节可复现
                fh.write((json.dumps(built, ensure_ascii=False, indent=1)
                          + "\n").encode("utf-8"))
            written += 1
        else:
            same += 1
        c = built["counts"]
        index["instruments"].append({
            "code": code, "instrument": built["instrument"],
            "file": f"data/items-structured/{code}.json",
            **{k: c[k] for k in INDEX_KEYS},
            "quantification_basis_counts": built["quantification_basis_counts"],
            "scales_used": built["scales_used"],
            "scale_item_counts": built["scale_item_counts"],
            "sha256": hashlib.sha256(
                json.dumps(built, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest(),
        })

    if args.check:
        print("✅ 生成物与磁盘一致（--check）")
        return 0

    keys = INDEX_KEYS
    totals = {k: sum(i[k] for i in index["instruments"]) for k in keys}
    qb: dict[str, int] = {}
    for e in index["instruments"]:
        for k, v in (e.get("quantification_basis_counts") or {}).items():
            qb[k] = qb.get(k, 0) + v
    index["quantification_basis_totals"] = qb
    index["en_repairs"] = {"applied": totals["text_en_repaired"],
                           "needs_lead_review": len(needs_review)}
    index["totals"] = totals
    with open(os.path.join(out_dir, "index.json"), "wb") as fh:
        fh.write((json.dumps(index, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    print(f"生成 {len(index['instruments'])} 套（{written} 个文件更新，{same} 个未变）")
    print(f"  题 {totals['items']}｜有题文原文 {totals['with_text_en']}｜有中译 {totals['with_text_zh']}"
          f"｜选项 {totals['options']}｜锚点表 {totals['scales']}")
    print(f"  选项级语义（逐题锚点册）{totals['option_level_meanings']} 个"
          f"｜其余语义在锚点级：有定量 {totals['options_quantified']}"
          f"｜凭自知 {totals['options_self_report']}")
    print(f"  情景展示 {totals['with_scenario']}/{totals['items']}"
          f"｜有提醒 {totals['with_notes']}"
          f"｜英文排版修复 {totals['text_en_repaired']}"
          f"（待 Lead 裁决 {len(needs_review)}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
