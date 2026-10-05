#!/usr/bin/env python3
"""生成「可填量表文档 + 评估指标（含统计学结果）」—— 本任务的两件套产物。

为什么要有这个脚本（而不是手写 md）
====================================
用户给出的开发顺序是**不可颠倒**的：

    文献数据 → 专业手册 → 纯粹完整的可填量表文档 + 评估指标（含统计学结果）
            → 这些全做完，才开始设计 UI → 最后才接受缺省值 / 实时估测

这一步的产物是后面一切的地基。地基一旦手写就会漂移：常模更新了、反向键改了、
α 换了来源，md 不会自己跟着变，而**它读起来仍然像是对的**。所以：

* **生成物禁止手改**：`data/descriptions/<code>.md` 与 `data/norms/<code>.json`
  由本脚本产出，`tools/check/check_descriptions.py` 会**重新生成一遍并逐字节比对**。
* **每个数字都要能追到出处**：所有事实性内容来自两类来源——
  ① 机器产物（`data/instruments/<code>.json`、`data/norms/*.json`、量表级统计量文件）
  ② 人工核对的证据文件 `content/descriptions/<code>.json`，其中**每一项都带 `source`**
  指向 `archive/` 里的原件或一条可核对的文献引用。
* **拿不到依据就留白**：没有常模就写「仅原始分，无可用常模」；手册没报 α 就写
  「手册未报告 α」。本脚本**不会**用「看起来差不多」的数字顶替。

产物
====
    data/descriptions/<code>.md      六节固定结构的人类可读文档
    data/norms/<code>.json           统一 schema 的常模/解读基准记录
    data/descriptions/index.json     清单（供校验器与前端消费）

注册表在下面 ``INSTRUMENTS``：一套量表一行，显式写清它的量表包、证据文件、
产物路径与常模记录形态。**不靠文件名猜**。

用法
====
    python tools/build/build_descriptions.py            # 生成全部
    python tools/build/build_descriptions.py --only pid-5
    python tools/build/build_descriptions.py --check     # 只比对，不写盘
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root, force_utf8_io  # noqa: E402

ROOT = find_root()

DOCS_DIR = os.path.join(ROOT, "data", "descriptions")
NORMS_DIR = os.path.join(ROOT, "data", "norms")
CONTENT_DIR = os.path.join(ROOT, "content", "descriptions")
INSTR_DIR = os.path.join(ROOT, "data", "instruments")

GENERATED_BANNER = ("<!-- 本文件由 tools/build/build_descriptions.py 生成，请勿手改。"
                    "改动请改 content/descriptions/<code>.json 后重跑。 -->")

#: 常模记录的统一 schema 版本。两种记录形态：
#:   ``descriptions_norms``  本脚本生成的「描述层常模记录」（含缺失声明）
#:   ``detailed_norms``      项目既有的细表（IPIP-NEO / PID-5），字段更全
SCHEMA_VERSION = "1.0"
KIND_ENVELOPE = "descriptions_norms"
KIND_DETAILED = "detailed_norms"

#: 注册表。每套量表一行：
#:   code            产物文件名（data/descriptions/<code>.md、data/norms/<code>.json）
#:   instrument      量表包里的 instrument code（None = 无量表包，纯元数据）
#:   content         人工核对的证据文件
#:   norms           data/norms 下的记录文件名；None = 由本脚本生成
#:   alpha_source    α 的机器来源（None = 证据文件里写）
INSTRUMENTS: list[dict] = [
    {"code": "ipip-neo", "instrument": "IPIP-NEO",
     "content": "ipip-neo.json", "norms": None, "alpha_source": "facet_records"},
    {"code": "pid-5", "instrument": "PID-5",
     "content": "pid-5.json", "norms": "pid-5.json",
     "alpha_source": "pid5_psychometrics"},
    {"code": "dsm5tr-l1", "instrument": "DSM5TR-L1",
     "content": "dsm5tr-l1.json", "norms": None, "alpha_source": None},
    {"code": "dsm5tr-l2-anger", "instrument": "DSM5TR-L2-Anger",
     "content": "dsm5tr-l2.json", "norms": None, "alpha_source": None},
    {"code": "dsm5tr-l2-anxiety", "instrument": "DSM5TR-L2-Anxiety",
     "content": "dsm5tr-l2.json", "norms": None, "alpha_source": None},
    {"code": "dsm5tr-l2-depression", "instrument": "DSM5TR-L2-Depression",
     "content": "dsm5tr-l2.json", "norms": None, "alpha_source": None},
    {"code": "dsm5tr-l2-mania", "instrument": "DSM5TR-L2-Mania",
     "content": "dsm5tr-l2.json", "norms": None, "alpha_source": None},
    {"code": "dsm5tr-l2-repetitive", "instrument": "DSM5TR-L2-Repetitive",
     "content": "dsm5tr-l2.json", "norms": None, "alpha_source": None},
    {"code": "dsm5tr-l2-sleep", "instrument": "DSM5TR-L2-Sleep",
     "content": "dsm5tr-l2.json", "norms": None, "alpha_source": None},
    {"code": "dsm5tr-l2-somatic", "instrument": "DSM5TR-L2-Somatic",
     "content": "dsm5tr-l2.json", "norms": None, "alpha_source": None},
    {"code": "dsm5tr-l2-substance", "instrument": "DSM5TR-L2-Substance",
     "content": "dsm5tr-l2.json", "norms": None, "alpha_source": None},
    {"code": "mmpi-2", "instrument": None,
     "content": "mmpi-2.json", "norms": None, "alpha_source": None},
]


# --------------------------------------------------------------------- 读入

def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def instrument_package(code: str) -> dict | None:
    p = os.path.join(INSTR_DIR, f"{code}.json")
    return load_json(p) if os.path.exists(p) else None


def content_file(code: str, entry: dict) -> dict:
    """读证据文件。一个文件可服务多套量表：顶层共享 + ``instruments[<code>]`` 特化。"""
    raw = load_json(os.path.join(CONTENT_DIR, entry["content"]))
    if "instruments" not in raw:
        return raw
    merged = {k: v for k, v in raw.items() if k != "instruments"}
    sub = raw["instruments"].get(code)
    if sub is None:
        raise KeyError(f"{entry['content']} 里没有 {code} 的条目")
    merged.update(sub)
    return merged


def norms_record(code: str, entry: dict) -> dict | None:
    name = entry["norms"] or f"{code}.json"
    p = os.path.join(NORMS_DIR, name)
    return load_json(p) if os.path.exists(p) else None


def facet_records() -> dict[str, dict]:
    """IPIP-NEO 的 30 个 facet 档案（含构念定义、α 与出处）。"""
    d = os.path.join(ROOT, "content", "facets")
    out: dict[str, dict] = {}
    if not os.path.isdir(d):
        return out
    for fn in sorted(os.listdir(d)):
        if fn.endswith(".record.json"):
            rec = load_json(os.path.join(d, fn))
            out[rec["identity"]["id"].split(".")[-1]] = rec
    return out


def pid5_alpha() -> dict:
    """PID-5 逐 facet α：本项目从公开原始作答（N=2,471）自算，附已发表对照。"""
    p = os.path.join(ROOT, "archive", "norms", "pid-5-psychometrics", "derived",
                     "pid5_item_params_demo.json")
    if not os.path.exists(p):
        return {}
    d = load_json(p)
    return {"alpha": d.get("alpha", {}), "n": d.get("n_pooled")}


_TEXT_DB: dict | None = None


def text_db_index() -> dict[str, dict]:
    """统一文本库：``source_code`` → ``{zh, zh_source, note, scaffold}``。

    为什么用文本库而不是界面产物：中文的**源头在数据层**
    （``data/text-db/text-db.json``，由 ``tools/build/build_text_db.py`` 产出），
    ``ui/instruments/*.js`` 只是 ``tools/ui/build_ui_instruments.py`` 读文本库后的
    下游再生成物。文档引用数据层，界面回退不会影响它。

    连接键是 ``items[].source_code`` ↔ ``entries[*].codes``。
    """
    global _TEXT_DB
    if _TEXT_DB is None:
        p = os.path.join(ROOT, "data", "text-db", "text-db.json")
        idx: dict[str, dict] = {}
        if os.path.exists(p):
            for _key, e in (load_json(p).get("entries") or {}).items():
                for c in (e.get("codes") or []):
                    idx.setdefault(c, e)
        _TEXT_DB = idx
    return _TEXT_DB


def item_text_status(pkg: dict | None) -> dict:
    """统计该量表题项的中译覆盖与复核状态（**如实**，用于文档里的题文可用性说明）。"""
    if not pkg:
        return {}
    idx = text_db_index()
    total = zh = 0
    sources: dict[str, int] = {}
    for it in pkg["items"]:
        total += 1
        e = idx.get(it.get("source_code", ""))
        if e and e.get("zh"):
            zh += 1
            s = e.get("zh_source") or "(未标)"
            sources[s] = sources.get(s, 0) + 1
    return {"total": total, "translated": zh, "sources": sources}


# --------------------------------------------------------------- 派生工具

def reverse_items(pkg: dict) -> list[dict]:
    """量表包里 key == -1 的题（**唯一真相源是量表包本身**）。"""
    return [it for it in pkg["items"] if it.get("key") == -1]


def dim_of_item(pkg: dict) -> dict[str, str]:
    out = {}
    for d in pkg["dimensions"]:
        for i in d.get("items", []):
            out[i] = d.get("id", "")
    return out


def scored_unit(pkg: dict) -> dict[str, str]:
    """维度 → 聚合方式（sum/mean/max/count_true…），取自量表包 scoring。

    以 **rubric id** 为准（本仓约定 rubric id == 维度 id），同时保留按 ``of`` 的展开，
    这样「域分 = 3 个 facet 均分」这类上层规则也能显示出来。
    """
    out: dict[str, str] = {}
    for key, r in pkg.get("scoring", {}).items():
        out[key] = r.get("aggregation", "")
        for ref in r.get("of", []):
            out.setdefault(ref, r.get("aggregation", ""))
    return out


def md_escape(text: str) -> str:
    return (text or "").replace("|", "\\|").strip()


def src_of(obj: dict, *keys: str) -> str:
    for k in keys:
        v = obj.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
        if isinstance(v, dict) and v.get("source"):
            return str(v["source"]).strip()
    return ""


# ------------------------------------------------------------------ 渲染

def render(code: str, entry: dict, content: dict, pkg: dict | None,
           norms: dict | None) -> str:
    L: list[str] = []
    name = content.get("display_name") or (pkg or {}).get("display_name") or code
    L.append(f"# {name} — 可填量表文档与评估指标")
    L.append("")
    L.append(GENERATED_BANNER)
    L.append("")
    L.append(f"- **量表代码**　`{entry['instrument'] or content.get('instrument', code)}`"
             f"（文档代码 `{code}`）")
    L.append(f"- **生成器**　`tools/build/build_descriptions.py`"
             f"　**校验**　`python tools/check/check_descriptions.py`")
    if content.get("items_policy") == "copyright_excluded":
        L.append("- **题项状态**　⚠️ **本量表题项不在本项目收录范围内**"
                 "（版权限制，见 §3.5 与 §1.3）")
    L.append("")
    L.append("> 本文档的目标读者是**将要填答这套量表的人**与**读结果的人**："
             "只读本文档就应能回答——测什么、每维怎么算、反向题哪些、"
             "分数对照什么表读、哪些话不许说。")
    L.append("")
    L.append("---")
    L.append("")

    _sec1(L, content, norms)
    _sec2(L, entry, content, pkg)
    _sec3(L, entry, content, pkg)
    _sec4(L, entry, content, norms)
    _sec5(L, entry, content, pkg)
    _sec6(L, content)
    _sec7(L, entry, content, pkg, norms)
    return "\n".join(L).rstrip() + "\n"


def _bullet(L, text: str, source: str = "") -> None:
    L.append(f"- {text}" + (f"　<span title=\"出处\">〔{source}〕</span>" if source else ""))


def _sec1(L, content: dict, norms: dict | None) -> None:
    L.append("## 1. 量表是什么 / 测什么")
    L.append("")
    wi = content.get("what_it_is", {})
    L.append(f"**它是什么**　{wi.get('text', '（未填写）')}")
    L.append("")
    if wi.get("source"):
        L.append(f"　出处：`{wi['source']}`")
        L.append("")
    wm = content.get("what_it_measures", {})
    L.append(f"**它测什么**　{wm.get('text', '（未填写）')}")
    L.append("")
    if wm.get("source"):
        L.append(f"　出处：`{wm['source']}`")
        L.append("")
    L.append("### 1.1 它**不**测什么（防止误用）")
    L.append("")
    for item in content.get("does_not_measure", []):
        _bullet(L, item["text"], item.get("source", ""))
    L.append("")
    if content.get("applicability"):
        ap = content["applicability"]
        L.append(f"### 1.2 适用与不适用人群")
        L.append("")
        L.append(f"- **适用**：{ap.get('applicable', '—')}")
        L.append(f"- **不适用**：{'; '.join(ap.get('inapplicable', [])) or '—'}")
        if ap.get("source"):
            L.append(f"- 出处：`{ap['source']}`")
        L.append("")
    if content.get("items_policy") == "copyright_excluded":
        L.append("### 1.3 题项为什么不在这里")
        L.append("")
        L.append(content.get("copyright_notice", "（未填写）"))
        L.append("")


def _sec2(L, entry: dict, content: dict, pkg: dict | None) -> None:
    L.append("## 2. 维度表")
    L.append("")
    dims = content.get("dimension_order") or ([d["id"] for d in (pkg or {}).get("dimensions", [])])
    inline = content.get("dimensions", {})
    if not dims and content.get("scales_metadata"):
        _sec2_metadata(L, content)
        return
    agg = scored_unit(pkg) if pkg else {}
    L.append("| # | 维度 id | 中文名 | 英文名 | 题目数 | 反向题数 | 聚合 | 通俗解释（本表内） |")
    L.append("|---|---|---|---|---|---|---|---|")
    for i, did in enumerate(dims, 1):
        d = next((x for x in (pkg or {}).get("dimensions", []) if x["id"] == did), {})
        c = inline.get(did, {})
        n_items = len(d.get("items", []))
        n_rev = len(d.get("reverse_keyed", []))
        L.append(f"| {i} | `{did}` | {c.get('zh', d.get('name', ''))} | "
                 f"{d.get('name', '')} | {n_items} | {n_rev} | `{agg.get(did, '—')}` | "
                 f"{md_escape(c.get('gloss', ''))[:60]} |")
    L.append("")
    L.append("### 2.1 逐维度构念解释（通俗中文 + 定义 + 不测什么）")
    L.append("")
    for did in dims:
        d = next((x for x in (pkg or {}).get("dimensions", []) if x["id"] == did), {})
        c = inline.get(did, {})
        L.append(f"#### `{did}`　{c.get('zh', d.get('name', ''))}"
                 f"（{d.get('name', '')}）")
        L.append("")
        if c.get("gloss"):
            L.append(f"- **通俗解释**：{c['gloss']}")
            if c.get("gloss_source"):
                L.append(f"  - 依据：`{c['gloss_source']}`")
        if c.get("definition"):
            L.append(f"- **文献定义（改述）**：{c['definition']}")
            if c.get("definition_source"):
                L.append(f"  - 出处：`{c['definition_source']}`")
        if c.get("boundaries"):
            L.append("- **与相邻维度的边界**：" + "；".join(c["boundaries"]))
        dn = c.get("does_not_measure") or []
        if dn:
            L.append("- **本维度不测**：" + "；".join(dn))
        if c.get("note"):
            L.append(f"- **说明**：{c['note']}")
        ex = _example_items(pkg, did, show_zh=bool(content.get("display_chinese_items")))
        if ex:
            L.append(f"- **示例题**：{ex}")
        L.append("")
    _example_note(L, pkg)
    if content.get("domain_table"):
        L.append("### 上级域（由 facet 均分构成）")
        L.append("")
        L.append("| 域 id | 中文名 | 英文名 | 构成 facet | 通俗解释 |")
        L.append("|---|---|---|---|---|")
        for d in content["domain_table"]:
            L.append(f"| `{d['id']}` | {d['zh']} | {d['name']} | "
                     f"{'、'.join('`' + c + '`' for c in d['children'])} | {md_escape(d.get('gloss', ''))} |")
        L.append("")
        if content.get("domain_table_source"):
            L.append(f"出处：`{content['domain_table_source']}`")
            L.append("")
    if content.get("dimension_definition_note"):
        L.append(f"> {content['dimension_definition_note']}")
        L.append("")
    dc = content.get("dimension_critiques") or {}
    if dc:
        L.append("### 各维度的已知批评/数据说明（逐维度）")
        L.append("")
        for did, items in dc.items():
            if not items:
                continue
            L.append(f"- **`{did}`**：" + "；".join(items))
        L.append("")
    _translation_note(L, content, pkg)


def _sec2_metadata(L, content: dict) -> None:
    sm = content["scales_metadata"]
    L.append(f"> {sm.get('note', '')}")
    L.append("")
    L.append("| 组 | 代号 | 量表名 | 题目数 | 说明 |")
    L.append("|---|---|---|---|---|")
    for group, rows in sm.get("groups", {}).items():
        for r in rows:
            L.append(f"| {group} | `{r['code']}` | {r['name']} | {r.get('items', '—')} | "
                     f"{md_escape(r.get('note', ''))} |")
    L.append("")
    if sm.get("source"):
        L.append(f"出处：`{sm['source']}`")
        L.append("")


def _example_items(pkg: dict | None, dim_id: str, k: int = 2,
                   show_zh: bool = False) -> str:
    if not pkg:
        return ""
    ids = next((d.get("items", []) for d in pkg["dimensions"] if d["id"] == dim_id), [])
    by_id = {it["id"]: it for it in pkg["items"]}
    idx = text_db_index() if show_zh else {}
    parts = []
    for iid in ids[:k]:
        it = by_id.get(iid, {})
        if not it.get("text"):
            continue
        cell = f"`{iid}` “{it['text']}”"
        if show_zh:
            e = idx.get(it.get("source_code", "")) or {}
            if e.get("zh"):
                cell += f"　→ 中译：“{e['zh']}”（{e.get('zh_source', '未标来源')}）"
        parts.append(cell)
    return "；".join(parts)


def _translation_note(L, content: dict, pkg: dict | None) -> None:
    """题文中译的**可用性与复核状态**：文档要能支撑「照着填」，就必须说清中译从哪来、有没有复核。

    ⚠️ **2026-10-04 的规则变更（用户 R2）**：此前 content 层按旧纪律设了
    `translation_unavailable_reason`（APA「不得修改」→ 连中译也不呈现），
    于是 86 条 DSM 中译只躺在 `data/text-db` 里、文档层不呈现。
    R2 明确：**中英双版 + 本地化讲解是「补充性独立内容」，不是对原文的修改**，
    因此授权条款不构成障碍。此处按 R2 渲染，并把授权原文如实并列（不隐藏）。
    """
    st = content.get("_item_text_status") or item_text_status(pkg)
    if not st or not st.get("total"):
        return
    L.append("### 题文与中译状态（能不能照着填）")
    L.append("")
    L.append(f"- **题文**：{st['total']} 题，英文原文来自量表包"
             f"（`data/instruments/<code>.json` 的 `items[].text`）。")
    auth = content.get("translation_unavailable_reason")   # R2 之前的旧字段（若仍在）
    pol = content.get("translation_policy")                # R2 口径
    if st.get("translated"):
        srcs = "；".join(f"「{k}」× {v}" for k, v in sorted(st["sources"].items()))
        L.append(f"- **中译**：{st['translated']}/{st['total']} 题在**数据层**有中译，"
                 f"来源标记为：{srcs}。")
        if content.get("translation_source_note"):
            L.append(f"- **中译的单一真相源**：{content['translation_source_note']}")
        if content.get("translation_caveat"):
            L.append(f"- ⚠️ **中译质量**：{content['translation_caveat']}")
        if pol:
            text = pol.get("text") if isinstance(pol, dict) else str(pol)
            L.append(f"- **授权与本地化处置（R2，2026-10-04）**：{text}")
            if isinstance(pol, dict) and pol.get("source"):
                L.append(f"  - 依据：`{pol['source']}`")
        elif auth:
            # 旧字段还在（content 层未同步）：**不据它行事**，并如实标注待同步。
            L.append("- **授权的处置（R2，2026-10-04）**：本项目**逐字不改原文**，"
                     "把 **① 英文原文、② 中文翻译、③ 本地化内容讲解**三者**并列**呈现"
                     "——中译与讲解是**补充性独立内容**（不是对原文的修改），各自可溯源。")
            L.append("- ⚠️ **待同步**：`content/descriptions/*.json` 的 "
                     "`translation_unavailable_reason` 仍是 R2 之前的措辞；"
                     "**本文档不据它行事**，该字段应改为 `translation_policy`。")
        L.append("- ⚠️ **中译复核状态**：逐条见 §3 的题项对照表"
                 "（`zh_source` 列）。标「subagent 初译/重译（待人工复核）」的条目"
                 "**尚未人工复核**，可作自填与内部核对，**不得**当作定稿中文版发布。")
    elif auth:
        L.append(f"- ⚠️ **本量表不提供中译**：{auth}")
    L.append("")


def _example_note(L, pkg: dict | None) -> None:
    if pkg and pkg.get("response_format"):
        labels = " / ".join(pkg["response_format"].get("labels", []))
        L.append(f"**选项锚点（原版文字）**：{labels}")
        L.append("")


def _sec3(L, entry: dict, content: dict, pkg: dict | None) -> None:
    L.append("## 3. 计分方法")
    L.append("")
    if content.get("items_policy") == "copyright_excluded":
        L.append("**本题库不收录该量表的题项，因此本项目无法计分。**"
                 "下面记录的是**公开发表的计分体系**，供用户自行取得题项后对照使用。")
        L.append("")
        for line in content.get("scoring_public", []):
            _bullet(L, line["text"], line.get("source", ""))
        L.append("")
        _sec3_local_import(L, content)
        return
    rf = (pkg or {}).get("response_format") or (pkg or {}).get("structure", {}).get("response_format") or {}
    if content.get("response_labels_zh"):
        L.append(f"- **作答选项**：{rf.get('points')} 点，{rf.get('min')}–{rf.get('max')}；"
                 f"锚点（中译）：{' / '.join(content['response_labels_zh'])}")
        if content.get("response_labels_source"):
            L.append(f"  - 中译出处：`{content['response_labels_source']}`")
        L.append(f"  - 原版（英文/发行版）锚点：{' / '.join(rf.get('labels', []))}")
    else:
        L.append(f"- **作答选项**：{rf.get('points')} 点，{rf.get('min')}–{rf.get('max')}；"
                 f"锚点：{' / '.join(rf.get('labels', []))}")
    if content.get("recall_window"):
        rw = content["recall_window"]
        L.append(f"- **回忆窗口 / 指导语**：{rw.get('text', '')}"
                 + (f"　出处：`{rw['source']}`" if rw.get("source") else ""))
    if pkg and pkg.get("structure", {}).get("window"):
        L.append(f"- **时间窗**：{pkg['structure']['window']}"
                 f"（出处：`{entry['instrument']}` 手册）")
    L.append(f"- **聚合口径**：每个维度由量表包 `scoring` 声明"
             f"（`sum` / `mean` / `max` / `count_true` …），本文档 §2 表内逐维列出。")
    if content.get("scoring_notes"):
        for line in content["scoring_notes"]:
            _bullet(L, line["text"], line.get("source", ""))
    L.append("")
    rev = reverse_items(pkg) if pkg else []
    L.append(f"### 3.1 反向计分题清单（**逐项**，共 {len(rev)} 题）")
    L.append("")
    if not rev:
        L.append("**无反向题。**（全部题项均为正向计分；本清单由量表包 `items[].key == -1` 逐项导出。）")
        L.append("")
    else:
        L.append("反向题在计分前先做变换（IPIP 系为 `6 − x`，PID-5 为 `3 − x`），"
                 "再做维度聚合。**下面这个清单与量表包逐项一致**，"
                 "由 `check_descriptions.py` 强制比对（集合双向相等）。")
        L.append("")
        dom = dim_of_item(pkg)
        L.append("| # | 题号(order) | 题项 id | 所属维度 |")
        L.append("|---|---|---|---|")
        for i, it in enumerate(rev, 1):
            L.append(f"| {i} | {it['order']} | `{it['id']}` | `{dom.get(it['id'], '')}` |")
        L.append("")
        L.append("**纯 id 清单（便于机器比对）**：")
        L.append("")
        L.append("```")
        for i in range(0, len(rev), 10):
            L.append(", ".join(it["id"] for it in rev[i:i + 10]))
        L.append("```")
        L.append("")
    if content.get("reverse_note"):
        L.append(f"> {content['reverse_note']}")
        L.append("")
    if entry["instrument"] == "PID-5":
        _sec3_pid5_dispute(L, content)
    if content.get("render_item_options"):
        _item_options(L, pkg)
    L.append("### 3.2 分值范围")
    L.append("")
    for line in content.get("score_ranges", []):
        _bullet(L, line["text"], line.get("source", ""))
    L.append("")
    # R2（2026-10-04）：DSM-5-TR 各册渲染「题项三件套」——① 英文原文
    # ② 中文翻译 ③ 本地化内容讲解，三者并列且各自可溯源。
    # 其它量表暂不渲染（IPIP-NEO 300 题会让文档膨胀数倍），同一渲染器可直接复用。
    if entry["instrument"].startswith("DSM5TR"):
        _item_table(L, content, pkg, entry)


def _sec3_pid5_dispute(L, content: dict) -> None:
    L.append("### 3.1b 反向题的历史争议：14 题还是 16 题")
    L.append("")
    L.append("PID-5 手册**两处原文自相矛盾**：Step 1 正文列出 14 题，"
             "facet 评分表另有 7、30 两题标 `R`（合计 16 题）。"
             "本项目采用 **16 题**，并保留三条独立证据：")
    L.append("")
    for line in content.get("reverse_dispute", []):
        _bullet(L, line["text"], line.get("source", ""))
    L.append("")


def _item_options(L, pkg: dict | None) -> None:
    """本册的「题」是一组陈述（如 ASRM）：把量表包里保存的选项组如实列出。

    选项组的**唯一位置是 `items[].options`**（2026-10-04 缺陷④修正）。
    `provenance.item_options` 兼容镜像同日**已删除**（界面与本生成器都已切换），
    由 `tools/check/check_dsm_item_text.py` 断言其**不存在**。
    """
    opts = {str(it["order"]): it["options"] for it in (pkg or {}).get("items", [])
            if it.get("options")}
    if not opts:
        L.append("### 3.3 逐题选项组")
        L.append("")
        L.append("⚠️ 本册的题目由多句陈述构成，但**量表包里没有保存选项组**"
                 "（`items[].options` 缺失），因此本文档无法列出各组陈述。"
                 "这会直接妨碍「照着填」——已登记为数据缺口。")
        L.append("")
        return
    L.append("### 3.3 逐题选项组（本册每题 = 一组陈述，0–4 分）")
    L.append("")
    L.append("题号 → 选项组（**逐字取自量表包 `items[].options`**）：")
    L.append("")
    for order in sorted(opts, key=lambda k: int(k)):
        L.append(f"**第 {order} 组**")
        L.append("")
        for o in opts[order]:
            L.append(f"- `{o.get('v')}`　{o.get('text', '').strip()}")
        L.append("")


def _item_table(L, content: dict, pkg: dict | None, entry: dict) -> None:
    """题项三件套（DSM-5-TR 各册）：① 英文原文 ② 中文翻译 ③ 本地化内容讲解。

    R2 要求三部分**并列且各自可溯源**：
      ① 来自量表包 `items[].text`（源头是 `archive/…/manual.pdf`）；
      ② 来自 `data/text-db/text-db.json`，逐条带 `zh_source`（复核状态照实写）；
      ③ 来自 `content/descriptions/*.json` 的 `dimensions[].gloss`（带 `gloss_source`），
         **与原文明确区分**——它解释构念在中文语境下指什么，不是原文字句。
    """
    if not pkg or not pkg.get("items"):
        return
    if content.get("items_policy") == "copyright_excluded":
        return
    idx = text_db_index()
    dim_of = dim_of_item(pkg)
    cdim = content.get("dimensions") or {}
    L.append("### 题项对照：① 英文原文 / ② 中文翻译 / ③ 本地化内容讲解（三部分并列）")
    L.append("")
    L.append("- **① 英文原文**：逐字取自量表包 `items[].text`（源头 "
             "`archive/scales/<code>/manual.pdf`，见 §5 出处）。")
    L.append("- **② 中文翻译**：取自统一文本库 `data/text-db/text-db.json`，"
             "逐条标注 `zh_source`（**复核状态照实写**，未复核就写未复核）。")
    L.append("- **③ 本地化内容讲解**：该题**所属维度**的构念说明，取自 "
             "`content/descriptions/*.json` 的 `dimensions[].gloss`（含 `gloss_source`）。"
             "它**不是原文的翻译**，而是「这个维度在中文语境下指什么」的补充说明，"
             "与①②明确区分。")
    L.append("")
    L.append("| 题号 | ① 英文原文 | ② 中文翻译（`zh_source`） | ③ 本地化讲解（维度构念） |")
    L.append("|---|---|---|---|")
    for it in pkg["items"]:
        # 作答指示语通常不列（它不是题项）；但**带选项组的指示语**（Mania 的每组
        # 5 句陈述）必须列——否则本册在这一节是空的，③ 的本地化说明也无处安放。
        if it.get("kind") == "instruction" and not it.get("options"):
            continue
        e = idx.get(it.get("source_code", "")) or {}
        zh = e.get("zh") or "—（无中译条目）"
        zsrc = e.get("zh_source") or "未标来源"
        did = dim_of.get(it["id"], "")
        cd = cdim.get(did) or {}
        gloss = cd.get("gloss") or ""
        gsrc = cd.get("gloss_source") or ""
        note = f"{gloss}（{gsrc}）" if gloss else "—"
        # 逐题的本地化补充说明（③ 的一部分）。例：Mania 第 1 组第 4 句原文
        # `happier **of** more cheerful` 的 of 疑为 or 之误——**原文逐字保留**，
        # 只在 ③ 里说明，不在 ① 里改动（这正是 R2「三部分并列」的用法）。
        loc = (content.get("localization_notes") or {}).get(str(it["order"]))
        if loc:
            note = f"{note}<br>{loc}" if note != "—" else loc
        if it.get("kind") == "instruction":
            en = "（本题是一组陈述，逐句英文原文见 §3.3）"
        else:
            en = md_escape(it.get("text", ""))
            # 每题的**专属选项锚点**也要在能填的地方出现（睡眠册第 8 题的锚点与
            # 其它题不同）。若本册走 §3.3 的整组渲染就不重复。
            if it.get("options") and not content.get("render_item_options"):
                opts = "；".join(f"{o.get('v')}={o.get('text', '')}"
                                 for o in it["options"])
                en += f"　<br>**本题专属选项**：{md_escape(opts)}"
        L.append(f"| {it['order']} | {en} | {zh}（{zsrc}） | {note} |")
    L.append("")


def _sec3_local_import(L, content: dict) -> None:
    L.append("### 3.1 如何合法取得题项并本地导入")
    L.append("")
    for line in content.get("local_import", []):
        L.append(f"{line}")
    L.append("")


def _sec4(L, entry: dict, content: dict, norms: dict | None) -> None:
    L.append("## 4. 结果解读基准")
    L.append("")
    spec = content.get("norms_spec", {})
    status = (norms or {}).get("status") or spec.get("status") or "unavailable"
    basis = (norms or {}).get("interpretation_basis") or spec.get("interpretation_basis", "")
    if status == "available":
        L.append(f"**本量表有可溯源常模**（解读基准：`{basis}`）。")
        L.append("")
        rs = (norms or {}).get("reference_sample") or spec.get("reference_sample") or {}
        if rs:
            L.append("| 参考样本 | 值 |")
            L.append("|---|---|")
            for k, v in rs.items():
                L.append(f"| {k} | {v if v is not None else '（来源未提供）'} |")
            L.append("")
        L.append(f"- **常模文件**：`data/norms/{entry['norms'] or entry['code'] + '.json'}`"
                 f"（本节的每个数字都取自该文件）")
        detail = (norms or {}).get("detail_source") or spec.get("detail_source")
        if detail:
            L.append(f"- **细表位置**：`{detail}`"
                     f"（逐维度百分位 / 逐 raw 百分位与 T 分；本节只摘要）")
        warn = (norms or {}).get("applicability_warning") or spec.get("applicability_warning", "")
        if warn:
            L.append(f"- ⚠️ **适用性**：{warn}")
        L.append("")
        _norm_summary(L, norms, content)
    else:
        if status == "partial":
            L.append("**有部分解读基准，但**没有**可直接使用的常模表。**")
        else:
            L.append("**仅原始分，无可用常模。**")
        L.append("")
        if status == "partial":
            L.append("本量表**没有本项目可用的常模表**：分量的均值/标准差/百分位或 raw→T 对照表都不在本项目入档范围内。"
                     "因此本项目只提供**已公开、可核对的基准事实**，不替用户换算分数。")
        else:
            L.append("本量表**不给百分位、不给 T 分、不做「高于/低于常人」的判断**——"
                     "本项目没有可溯源的常模数据支撑这类表述，因此宁可不给。")
        L.append("")
        reason = ((norms or {}).get("unavailable_reason") or spec.get("unavailable_reason")
                  or content.get("norms_unavailable_reason") or "")
        if reason:
            L.append(f"**为什么没有**：{reason}")
            L.append("")
        if spec.get("partial_basis"):
            L.append(f"**已有部分基准**：{spec['partial_basis']}")
            L.append("")
        rs = spec.get("reference_sample") or {}
        if rs:
            L.append("| 参考样本 | 值 |")
            L.append("|---|---|")
            for k, v in rs.items():
                L.append(f"| {k} | {v} |")
            L.append("")
        for line in spec.get("evidence", []):
            L.append(f"- 依据：`{line}`")
        L.append("")
        L.append(_norm_fallback_text(content, status))
        L.append("")
    _criteria_block(L, content, entry)
    _linkage_block(L, entry)
    if content.get("result_reading"):
        L.append("### 4.1 怎么读（本量表的解读规则）")
        L.append("")
        for line in content["result_reading"]:
            _bullet(L, line["text"], line.get("source", ""))
        L.append("")


def _criteria_block(L, content: dict, entry: dict) -> None:
    """若该量表在 ``data/criteria/*.json`` 里有判读口径，直接渲染（单一真相源，不复制）。

    这解决「常模缺失的册子必须显式写明怎么读」：手册给的分带/分界在这里逐条呈现，
    而 PROMIS 四册的「T 分表待补」也在这里如实标注。
    """
    d = os.path.join(ROOT, "data", "criteria")
    if not os.path.isdir(d) or not entry.get("instrument"):
        return
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json"):
            continue
        blob = load_json(os.path.join(d, fn))
        inst = (blob.get("instruments") or {}).get(entry["instrument"])
        if not inst:
            continue
        L.append("### 4.2 判读口径（自动取自 `data/criteria/`，单一真相源）")
        L.append("")
        L.append(f"- **口径类型**：`{inst.get('kind')}`　量表：{inst.get('scale', '')}")
        if inst.get("items"):
            L.append(f"- **题数**：{inst['items']}")
        if inst.get("sum_range"):
            L.append(f"- **总分范围**：{inst['sum_range'][0]}–{inst['sum_range'][1]}")
        if inst.get("aggregate_label"):
            L.append(f"- **汇总口径**：{inst['aggregate_label']}")
        if inst.get("cutoff") is not None:
            L.append(f"- **分界值**：{inst['cutoff']}")
        if inst.get("bands"):
            L.append("")
            L.append("| 分带 | 范围 |")
            L.append("|---|---|")
            for b in inst["bands"]:
                L.append(f"| {b['label']} | {b['lo']}–{b['hi']} |")
        if inst.get("pending_reason"):
            L.append(f"- ⚠️ **待补**：{inst['pending_reason']}")
        if inst.get("notes"):
            L.append(f"- 说明：{inst['notes']}")
        if blob.get("missing_rule"):
            L.append(f"- 缺答规则：{blob['missing_rule']}")
        if inst.get("evidence"):
            L.append(f"- 出处：`{inst['evidence']}`")
        L.append("")
        return


def _linkage_block(L, entry: dict) -> None:
    """Level 1：逐域门槛表取自 ``data/linkage/dsm5tr-chain.json``（单一真相源）。"""
    p = os.path.join(ROOT, "data", "linkage", "dsm5tr-chain.json")
    if not os.path.exists(p) or not entry.get("instrument"):
        return
    blob = load_json(p)
    l1 = blob.get("level1") or {}
    if l1.get("instrument") != entry["instrument"]:
        return
    L.append("### 4.2 逐域门槛表（自动取自 `data/linkage/dsm5tr-chain.json`，单一真相源）")
    L.append("")
    L.append("| # | 域 | 题项 | 门槛 | 门槛含义 | 对应 Level 2 |")
    L.append("|---|---|---|---|---|---|")
    for d in l1.get("domains", []):
        L.append(f"| {d['index']} | {d['name']} | "
                 f"{'、'.join('`' + i + '`' for i in d['items'])} | "
                 f"≥{d['threshold']} | {d['threshold_label']} | "
                 f"{('`' + d['level2'] + '`') if d.get('level2') else '（手册未指定）'} |")
    L.append("")
    if l1.get("evidence"):
        ev = l1["evidence"]
        L.append(f"出处：`{ev.get('file')}` 的 {ev.get('section')}（解析器 `{ev.get('extractor')}`）")
    L.append("")
    interfaces = blob.get("pid5_interface") or {}
    if interfaces:
        L.append(f"> **与 PID-5 的衔接（{interfaces.get('status')}）**：{interfaces.get('caveat', '')}")
        L.append("")


def _norm_fallback_text(content: dict, status: str) -> str:
    if status == "partial":
        return ("**替代读法**：只做「与自己比」的纵向比较，或与本文档 §4.2 给出"
                "**该量表自己的分带/分界**对照；**不做人群百分位比较**。")
    return ("**替代读法**（唯一诚实的读法）：把分数当作"
            "**该维度上题面描述的频率/强度记录**，只做纵向自比"
            "（同一人不同时间、或与自己的其它维度比），**不做人群比较**。")


def _norm_summary(L, norms: dict | None, content: dict) -> None:
    if not norms:
        return
    ds = norms.get("dimension_summary")
    if not ds:
        return
    L.append("### 4.0 常模摘要（自动取自常模文件）")
    L.append("")
    L.append("| 维度 | 单位 | 均值 | 标准差 |")
    L.append("|---|---|---|---|")
    for did, v in ds.items():
        L.append(f"| `{did}` | {v.get('unit', '')} | {v.get('mean', '—')} | {v.get('sd', '—')} |")
    L.append("")
    L.append("> 逐百分位表（1..99）在常模文件里；本表只摘要均值/标准差，"
             "避免正文与细表出现**两个真相源**。")
    L.append("")


def _sec5(L, entry: dict, content: dict, pkg: dict | None) -> None:
    L.append("## 5. 信度与出处")
    L.append("")
    alpha = content.get("alpha", {})
    L.append("### 5.1 内部一致性（α）")
    L.append("")
    if alpha.get("values"):
        L.append("| 维度 | α | 来源 |")
        L.append("|---|---|---|")
        for did, v in alpha["values"].items():
            if isinstance(v, dict):
                L.append(f"| `{did}` | {v.get('value', '—')} | {v.get('source', '')} |")
            else:
                L.append(f"| `{did}` | {v} | {alpha.get('source', '')} |")
        L.append("")
        L.append(f"**口径**：{alpha.get('note', '')}")
        L.append("")
    else:
        L.append("**未获得可溯源的 α。**" + alpha.get("note", ""))
        L.append("")
    if alpha.get("summary"):
        for line in alpha["summary"]:
            _bullet(L, line["text"], line.get("source", ""))
        L.append("")
    L.append("### 5.2 来源与授权")
    L.append("")
    if pkg:
        L.append(f"- **citation**：{pkg.get('citation', '')}")
        lic = pkg.get("license", {})
        L.append(f"- **license**：`{lic.get('kind')}`"
                 f"（可再分发：{lic.get('redistribution')}）— {lic.get('holder', '')}")
        L.append(f"  - 授权证据：`{lic.get('evidence', '')}`")
        if lic.get("url"):
            L.append(f"  - 官方链接：{lic['url']}")
        if pkg.get("item_order_source"):
            L.append(f"- **题序来源**：`{pkg['item_order_source']}`")
    else:
        L.append(f"- **citation**：{content.get('citation', '')}")
        L.append(f"- **授权**：{content.get('license_note', '')}")
        if content.get("license_evidence"):
            L.append(f"  - 证据：`{content['license_evidence']}`")
    L.append("")
    kc = content.get("known_critiques", [])
    L.append("### 5.3 已知批评与局限（known_critiques）")
    L.append("")
    if kc:
        for line in kc:
            _bullet(L, line["text"], line.get("source", ""))
    else:
        L.append("（本项目未收录到针对本量表的专门批评文献；这不等于「没有局限」。）")
    L.append("")


def _sec6(L, content: dict) -> None:
    L.append("## 6. 解读义务（哪些话不许说）")
    L.append("")
    L.append("以下为本量表结果解读的**硬约束**。它们不是风格建议："
             "本项目的每一条对外表述都必须满足。")
    L.append("")
    for i, c in enumerate(content.get("interpretation_caveats", []), 1):
        L.append(f"{i}. {c['text']}" + (f"　〔出处：{c['source']}〕" if c.get("source") else ""))
    L.append("")
    dc = content.get("dimension_caveats") or {}
    if dc:
        L.append("### 6.1 维度级解读义务（逐维度）")
        L.append("")
        L.append("下面每一条都是**该维度**特有的解读约束——它们来自 facet 档案的"
                 "`evidence.interpretation_caveats`，是「这个分数不能这样读」的具体说明。")
        L.append("")
        for did, items in dc.items():
            L.append(f"- **`{did}`**：" + "；".join(items))
        L.append("")


def _sec7(L, entry: dict, content: dict, pkg: dict | None, norms: dict | None) -> None:
    L.append("---")
    L.append("")
    L.append("## 附录 A　证据与溯源")
    L.append("")
    L.append("| 项 | 值 |")
    L.append("|---|---|")
    L.append(f"| 证据文件 | `content/descriptions/{entry['content']}` |")
    if pkg:
        L.append(f"| 量表包 | `data/instruments/{entry['code']}.json` |")
    nm = entry["norms"] or f"{entry['code']}.json"
    L.append(f"| 常模记录 | `data/norms/{nm}` |")
    for k, v in (content.get("provenance", {}) or {}).items():
        L.append(f"| {k} | {v} |")
    L.append("")
    if content.get("evidence_gaps"):
        L.append("### A.1 本项目**没有**拿到依据的地方（如实留白）")
        L.append("")
        for g in content["evidence_gaps"]:
            L.append(f"- **{g['what']}**：{g['detail']}")
        L.append("")


# ------------------------------------------------------------------ 常模记录

def build_norms_record(entry: dict, content: dict, pkg: dict | None,
                       have: dict | None) -> dict | None:
    """若注册表未指定既有常模文件，则由证据文件生成描述层常模记录。"""
    if entry["norms"]:
        return None                       # 既有细表：不动它
    spec = content.get("norms_spec", {})
    rec = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": KIND_ENVELOPE,
        "instrument": entry["instrument"] or content.get("instrument", ""),
        "code": entry["code"],
        "status": spec.get("status", "unavailable"),
        "interpretation_basis": spec.get("interpretation_basis", "raw_only"),
        "reference_sample": spec.get("reference_sample"),
        "detail_source": spec.get("detail_source"),
        "dimension_summary": spec.get("dimension_summary", {}),
        "source": spec.get("source", {}),
        "applicability_warning": spec.get("applicability_warning", ""),
        "notes": spec.get("notes", ""),
    }
    if rec["status"] != "available":
        rec["unavailable_reason"] = spec.get("unavailable_reason", "")
    return rec


def ipip_neonorms_summary() -> dict:
    """从既有细表派生「维度 → 均值/SD」摘要（不复制百分位表）。"""
    p = os.path.join(NORMS_DIR, "ipip-neo-300.json")
    if not os.path.exists(p):
        return {}
    d = load_json(p)
    out = {}
    unit = d.get("unit", "")
    dunit = d.get("domain_unit", "")
    for k, v in (d.get("facets") or {}).items():
        out[k] = {"unit": unit, "mean": v.get("mean"), "sd": v.get("sd")}
    for k, v in (d.get("domains") or {}).items():
        out[k] = {"unit": dunit, "mean": v.get("mean"), "sd": v.get("sd")}
    return out


# ------------------------------------------------------------------ α 汇总

def _as_text(x) -> str:
    if isinstance(x, str):
        return x
    if isinstance(x, dict):
        return str(x.get("text") or x.get("distinction") or x.get("note") or "")
    return str(x)


def enrich_from_facets(content: dict) -> dict:
    """IPIP-NEO：30 个维度的构念解释/边界/批评**不复制**，直接取 facet 档案。

    ``content/facets/<facet>.record.json`` 已经过项目的人工核对（构念定义、边界、
    does_not_measure、α 与出处、known_critiques、interpretation_caveats）。
    这里把它们搬到生成器需要的位置，**不改写内容**。
    """
    recs = facet_records()
    dims = content.setdefault("dimensions", {})
    crit: dict[str, list[str]] = {}
    cav: dict[str, list[str]] = {}
    for fid, rec in recs.items():
        c = rec.get("construct", {})
        d = c.get("definition", {}) or {}
        cur = dims.setdefault(fid, {})
        cur.setdefault("zh", rec.get("identity", {}).get("facet_name_zh", ""))
        cur.setdefault("gloss", _as_text(d))
        basis = "｜".join(x for x in (d.get("basis", ""), d.get("source", "")) if x)
        cur.setdefault("gloss_source", f"content/facets/{fid}.record.json（{basis}）"
                       if basis else f"content/facets/{fid}.record.json")
        cur["does_not_measure"] = [_as_text(x) for x in c.get("does_not_measure", [])]
        cur["boundaries"] = [
            f"与 {b.get('against_facet')} 的边界：{b.get('distinction')}"
            for b in c.get("boundaries", []) if isinstance(b, dict)]
        crit[fid] = [_as_text(x) for x in rec.get("evidence", {}).get("known_critiques", [])]
        cav[fid] = [_as_text(x) for x in rec.get("evidence", {}).get("interpretation_caveats", [])]
    content["dimension_critiques"] = {k: v for k, v in crit.items() if v}
    content["dimension_caveats"] = {k: v for k, v in cav.items() if v}
    return content


def build_alpha(entry: dict, content: dict) -> dict:
    """α：先取机器来源，取不到就用证据文件里写的。两者都带 source。"""
    src = entry["alpha_source"]
    if src == "facet_records":
        recs = facet_records()
        values = {}
        for fid, rec in sorted(recs.items()):
            rel = rec.get("reliability", {})
            values[fid] = {"value": rel.get("cronbach_alpha"),
                           "source": rel.get("alpha_source", "")}
        return {"values": values, "note": content.get("alpha_note", ""),
                "summary": content.get("alpha_summary", []), "source": "content/facets/*.record.json"}
    if src == "pid5_psychometrics":
        d = pid5_alpha()
        al = d.get("alpha", {})
        values = {}
        for facet, v in al.items():
            values[facet] = {"value": v.get("alpha_pooled"),
                             "source": f"本项目自算（N={d.get('n')}，原始作答 CC-BY-4.0）"}
        out = {"values": values, "note": content.get("alpha_note", ""),
               "summary": content.get("alpha_summary", []),
               "source": "archive/norms/pid-5-psychometrics/derived/pid5_item_params_demo.json"}
        # 已发表对照也列出来（α 的独立外部核对）
        pub = {f: v.get("alpha_published_eurpsych2016") for f, v in al.items()}
        if any(pub.values()):
            out["published_comparison"] = {
                "values": pub,
                "source": "Bach, Sellbom, Bo & Simonsen (2016), European Psychiatry 37:22–27 "
                          "（补充材料 Table S1；授权不允许转存，故只记数值与出处，未入档）",
            }
        return out
    return content.get("alpha", {"values": {}, "note": content.get("alpha_note", "")})


# ------------------------------------------------------------------ 主流程

def build_one(entry: dict) -> dict:
    code = entry["code"]
    content = content_file(code, entry)
    pkg = instrument_package(code) if entry["instrument"] else None
    norms = norms_record(code, entry)
    if entry["alpha_source"] == "facet_records":
        content = enrich_from_facets(content)
    if entry["alpha_source"] in ("facet_records", "pid5_psychometrics"):
        content = dict(content, alpha=build_alpha(entry, content))
    pkg_probe = instrument_package(code) if entry["instrument"] else None
    content = dict(content, _item_text_status=item_text_status(pkg_probe))
    md = render(code, entry, content, pkg, norms)
    rec = build_norms_record(entry, content, pkg, norms)
    text_status = content.get("_item_text_status") or item_text_status(pkg)
    if code == "ipip-neo" and rec is not None:
        rec["dimension_summary"] = ipip_neonorms_summary()
        rec["detail_source"] = "data/norms/ipip-neo-300.json"
    if rec is not None and norms is None and code != "ipip-neo":
        pass
    return {"code": code, "md": md, "norms_record": rec, "content": content,
            "package": pkg, "existing_norms": norms, "text_status": text_status}


def main() -> int:
    force_utf8_io()          # 入口第一件事：GBK 控制台下不许崩（见 tools/_root.py）
    ap = argparse.ArgumentParser(description="生成量表文档与常模记录")
    ap.add_argument("--only", default=None, help="只处理某个 code")
    ap.add_argument("--check", action="store_true", help="只比对，不写盘")
    args = ap.parse_args()

    os.makedirs(DOCS_DIR, exist_ok=True)
    index = {"schema_version": SCHEMA_VERSION,
             "generator": "tools/build/build_descriptions.py",
             "checker": "tools/check/check_descriptions.py",
             "instruments": []}
    written, unchanged = 0, 0
    for entry in INSTRUMENTS:
        if args.only and entry["code"] != args.only:
            continue
        built = build_one(entry)
        md_path = os.path.join(DOCS_DIR, f"{entry['code']}.md")
        cur = open(md_path, encoding="utf-8").read() if os.path.exists(md_path) else None
        same_md = cur == built["md"]
        rec = built["norms_record"]
        rec_path = os.path.join(NORMS_DIR, f"{entry['code']}.json") if rec else None
        same_rec = True
        if rec:
            cur_rec = load_json(rec_path) if os.path.exists(rec_path) else None
            same_rec = cur_rec == rec
        if args.check:
            flag = "=" if (same_md and same_rec) else "≠"
            print(f"  {flag} {entry['code']:20} md={'ok' if same_md else '差异'}"
                  f" norms={'ok' if same_rec else '差异'}")
            if not (same_md and same_rec):
                return 1
            continue
        if not same_md:
            with open(md_path, "w", encoding="utf-8") as fh:
                fh.write(built["md"])
        if rec and not same_rec:
            with open(rec_path, "w", encoding="utf-8") as fh:
                json.dump(rec, fh, ensure_ascii=False, indent=1)
                fh.write("\n")
        written += 1
        unchanged += int(same_md and same_rec)
        index["instruments"].append({
            "code": entry["code"],
            "instrument": entry["instrument"] or built["content"].get("instrument", ""),
            "description": f"data/descriptions/{entry['code']}.md",
            "content_source": f"content/descriptions/{entry['content']}",
            "instrument_package": (f"data/instruments/{entry['code']}.json"
                                   if built["package"] else None),
            "norms": (f"data/norms/{entry['norms']}" if entry["norms"]
                      else (f"data/norms/{entry['code']}.json" if rec else None)),
            "norms_record_kind": (KIND_DETAILED if entry["norms"] else KIND_ENVELOPE),
            "norms_status": ((built["existing_norms"] or rec or {}).get("status")
                             or ("available" if entry["norms"] else "unavailable")),
            "items_policy": built["content"].get("items_policy", "included"),
            "n_items": len(built["package"]["items"]) if built["package"] else 0,
            "n_dimensions": len(built["package"]["dimensions"]) if built["package"] else 0,
            "n_reverse_items": len(reverse_items(built["package"])) if built["package"] else 0,
            "items_translated": built["text_status"].get("translated", 0),
            "items_translation_sources": sorted((built["text_status"].get("sources") or {})),
            "sha256": hashlib.sha256(built["md"].encode("utf-8")).hexdigest(),
        })
    if args.check:
        print("✅ 生成物与磁盘一致（--check）")
        return 0
    idx_path = os.path.join(DOCS_DIR, "index.json")
    with open(idx_path, "w", encoding="utf-8") as fh:
        json.dump(index, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(f"生成 {written} 套：其中 {unchanged} 套与磁盘一致；清单 → data/descriptions/index.json")
    for e in index["instruments"]:
        print(f"  {e['code']:20} {e['n_items']:>4} 题 {e['n_dimensions']:>3} 维 "
              f"反向 {e['n_reverse_items']:>3}　norms={e['norms_status']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
