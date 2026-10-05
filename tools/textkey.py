#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""题文归一化键（text key）——把「题干英文」与「材料库 key」折到同一个键上。

为什么要有它
============
``data/text-db/text-db.json`` 的 entry key 是从题干派生的（见
``tools/build/build_text_db.py`` 的 ``norm()``）：**连字符/破折号折成空格**、
弯引号统一成直引号、去掉尾标点。而 ``data/items-structured/*.json`` 的
``text_en`` **保留原样**（``hang-gliding``、``soft-hearted``、``don’t``…）。

于是「拿题干英文去查材料」这条最朴素的用法会**静默查不到**——实测 606 题里有
**9 题**（IPIP 3 + PID-5 6）在「保留连字符」的严格查法下查不到，而它们其实都在库里。
这类漏配不报错，只会让下游（情景展示、文案）悄悄少材料。

做法：把归一化抽成**一个**函数（全仓唯一实现），两侧都用它，再用
``data/text-db/index-norm.json``（由 ``build_text_db.py`` 生成、**只由 entries 派生**、
不许手改）做 O(1) 查表：

    lookup(entries, text_en, index, fallbacks=[text_en_verbatim])   # → (entry key, entry)

⚠️ 为什么要「回退」而不是把修复后的写法塞进索引
==============================================
材料库 ``entries`` 的 key 按 R1 **保留源件 verbatim 形态**（``Ikeep my distance…``、
``enjoylife``、``to behonest``），而用户可见的 ``text_en`` 是**排版修过的**形态——
两者不同**不是缺陷，是分层的正确表现**。对应关系每题自带（``data/items-structured/*.json``
的 ``text_en_verbatim`` 字段），所以正确做法是：用 ``text_en`` 查不到时，**改用该题的源件
原文再查一次**（"你要找的是源件那句话，就拿源件的原文去查"）。

反例（别这么做）：把这 23 条映射抄进索引当别名——那等于**第二个真相源**，索引会与
``text_en_verbatim`` 漂移（本项目已因「两个真相源」吃过一次亏）。

⚠️ 必须保留中日韩字符（实测踩到的坑）
====================================
不能写成「白名单 ASCII」的归一化，例如

    re.sub(r"[^a-z0-9 ]", " ", s)          # ← 错的示范，别这么写

那会把**中日韩字整段删掉**。DSM5TR-L2-Mania 的 5 道组干
（``第 1 组：选出最符合你的一句`` … ``第 5 组：…``）在这种写法下都塌成**只剩序号数字**
（``1``…``5``），键里再没有内容：序号相同、中文不同的两条会**互相匹配**——
匹配「成功」但答的不是同一句，这就是**假绿**，比漏配更难发现。

本函数的判据是「**折标点、不折字母数字**」：

* ``ch.isalnum() or ch.isspace()`` 一律保留（``str.isalnum()`` 对 CJK 为真）；
* 连字符与各种破折号显式折成空格（``-``、``‐‑‒–—―−``、软连字符）；
* 弯引号/撇号统一成直引号（``’‘`` → ``'``，``“”`` → ``"``）；
* 其余标点折成空格，最后折叠连续空白。

用法
====
    from textkey import build_index, lookup

    entries = json.load(open("data/text-db/text-db.json", encoding="utf-8"))["entries"]
    index = build_index(entries)                       # 或 load_index("…/index-norm.json")

    key, entry = lookup(entries, "Would never go hang-gliding or bungee-jumping.", index)
    key, entry = lookup(entries, it["text_en"], index,
                        fallbacks=[it.get("text_en_verbatim")])   # 排版修复题走这里
    lookup(entries, "库里没有的一句话", index)                       # → None

``lookup`` 一个候选都不中就返回 ``None``：**不做模糊匹配、不抛异常**。
静默兜底会把「漏配」升级成「错配」，那比漏配更坏。
"""

from __future__ import annotations

import json
import re
import unicodedata

#: 生成物文件名：``data/text-db/index-norm.json``（由 build_text_db.py 写出）
INDEX_NAME = "index-norm.json"

#: 弯引号 / 撇号 → 直引号
_QUOTE_MAP = {
    "\u2018": "'", "\u2019": "'", "\u201a": "'", "\u201b": "'",
    "\u201c": '"', "\u201d": '"', "\u201e": '"', "\u201f": '"',
}

#: 连字符与各种破折号 → 空格（含 U+00AD 软连字符）
_DASHES = frozenset("-\u2010\u2011\u2012\u2013\u2014\u2015\u2212\u00ad")

#: 允许原样保留的非字母数字字符：直引号（统一之后）
_KEEP_PUNCT = frozenset("'\"")


def norm_key(s: str | None) -> str:
    """把题文折成归一化键：NFKC → 小写 → 引号统一 → 连字符/破折号折空格 → 其它标点折空格。

    **中日韩字符必须保留**（见模块 docstring 里那条「假绿」的坑）：
    判据是 ``ch.isalnum()``，它对 CJK 为真；绝不用 ``[^a-z0-9 ]`` 这类白名单。
    """
    if not s:
        return ""
    text = unicodedata.normalize("NFKC", s).lower()
    out: list[str] = []
    for ch in text:
        if ch in _QUOTE_MAP:
            out.append(_QUOTE_MAP[ch])
        elif ch in _DASHES:
            out.append(" ")
        elif ch.isalnum() or ch.isspace() or ch in _KEEP_PUNCT:
            out.append(ch)
        else:
            out.append(" ")
    return re.sub(r"\s+", " ", "".join(out)).strip()


def build_index(entries: dict) -> dict[str, str]:
    """``{norm_key(entry key): entry key}``——供查表用。

    按 entry key 排序后 ``setdefault``，所以同一份 entries 永远得到同一个索引；
    归一化后撞车的键（极少）取**排序最小**的那个 entry key，并由
    ``index_collisions()`` 报出来，不静默吞掉。
    """
    idx: dict[str, str] = {}
    for key in sorted(entries):
        nk = norm_key(key)
        if nk:
            idx.setdefault(nk, key)
    return idx


def index_collisions(entries: dict) -> dict[str, list[str]]:
    """归一化后撞车的 entry key：``{norm_key: [entry key, …]}``（正常应为空）。"""
    seen: dict[str, list[str]] = {}
    for key in sorted(entries):
        nk = norm_key(key)
        if nk:
            seen.setdefault(nk, []).append(key)
    return {nk: keys for nk, keys in seen.items() if len(keys) > 1}


def render_index(entries: dict) -> bytes:
    """确定性序列化索引：``sort_keys=True`` + UTF-8 + **LF** + 结尾换行。

    同一份 entries 重复生成**逐字节一致**（供 `--check` 做字节比对）。
    """
    body = json.dumps(build_index(entries), ensure_ascii=False,
                      sort_keys=True, indent=1)
    return (body + "\n").encode("utf-8")


def load_index(path: str) -> dict[str, str]:
    """读 ``index-norm.json``（生成物；调用方负责确认它与之对应的 entries 同步）。"""
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


#: ``id(entries) → (entries, index)``：避免同一份大字典被反复建索引。
_INDEX_CACHE: dict[int, tuple[dict, dict]] = {}


def _cached_index(entries: dict) -> dict[str, str]:
    hit = _INDEX_CACHE.get(id(entries))
    if hit is not None and hit[0] is entries:
        return hit[1]
    idx = build_index(entries)
    if len(_INDEX_CACHE) >= 8:
        _INDEX_CACHE.pop(next(iter(_INDEX_CACHE)))
    _INDEX_CACHE[id(entries)] = (entries, idx)
    return idx


def lookup(entries: dict, en: str | None = None,
           index: dict[str, str] | None = None,
           fallbacks: tuple | list = ()) -> tuple[str, dict] | None:
    """按 ``norm_key`` **依序**在材料库里查：先 ``en``，再 ``fallbacks``；返回首个命中的 ``(entry key, entry)``。

    为什么要回退（分层，不是兜底）
    ------------------------------
    材料库 key 按 R1 保留**源件 verbatim** 形态；用户可见的 ``text_en`` 是**排版修过**的
    形态，对应关系每题自带（``data/items-structured/*.json`` 的 ``text_en_verbatim``）。
    所以查不到时应当**拿源件原文再查一次**：

        key, entry = lookup(entries, it["text_en"], index,
                            fallbacks=[it.get("text_en_verbatim")])

    而不是把 repaired→verbatim 的映射抄进索引（那是第二个真相源）。

    * ``index`` 可传 ``load_index("data/text-db/index-norm.json")`` 避免重算；
      不传则按 ``entries`` 现场建（带缓存）。
    * 空串 / ``None`` 的候选直接跳过；**一个都不中返回 ``None``**。
    * **不做模糊匹配兜底**——兜底会把「漏配」变成「错配」。
    """
    if index is None:
        index = _cached_index(entries)
    for cand in (en, *fallbacks):
        if not cand:
            continue
        key = index.get(norm_key(cand))
        if key is not None and key in entries:
            return key, entries[key]
    return None
