#!/usr/bin/env python3
"""把 OpenScales 的 ``.osd`` 机读包转成多量表 schema（``data/instruments/<code>.json``）。

为什么用同一个转换器而不是每套量表手写脚本
==========================================
归档里有 1096 个量表包，格式是统一的（``definition`` 下有
``scale_info``/``likert_options``/``dimensions``/``items``/``scoring``）。
既然格式统一，转换逻辑就该只有一份——手写 1096 份必然漂移，而
「同一件事两处口径」正是这个项目反复吃过亏的地方（原 D78、D96；见 `README.md`「已知的坑」）。

题项正文的三种来源（按优先级）
==============================
1. ``item.text`` 直接内嵌（APA 系量表如 PID-5 是这种）
2. ``item.text_key`` → ``ipip_item_codes.json`` 的 ``code_to_text``（剥 ``ipip_`` 前缀）
3. ``item.text_key`` → 该 .osd 的 ``translations`` 池

``dimensions`` 的平铺问题
=========================
IPIP 系 .osd 把 ``nonplanfulness_sum`` 与 ``nonplanfulness_mean`` 当成两个 dimension，
其实是**同一个特质**的两种聚合。转换器把它归一：一个维度 + 一个计分规则，
聚合方式取自 ``scoring[dim_id].method``。``_sum``/``_mean`` 后缀只用于识别同源。

用法
====
    python tools/build_scales.py --list                      # 列出所有可转量表
    python tools/build_scales.py --only IPIP-CATPD           # 转一套
    python tools/build_scales.py --family ipip --all         # 转整个 IPIP 家族
    python tools/build_scales.py --only IPIP-NEO-300 --check # 只校验，不落盘
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.instrument_schema import (  # noqa: E402
    Dimension, Instrument, Item, License, ResponseFormat, Rubric,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OSD_DIR = os.path.join(ROOT, "archive", "ipip", "data", "OpenScales")
OUT_DIR = os.path.join(ROOT, "data", "instruments")
CODES_FILE = os.path.join(OSD_DIR, "scales", "ipip", "ipip_item_codes.json")
EN_TRANSLATIONS = os.path.join(OSD_DIR, "scales", "ipip", "translations",
                               "ipip_master_en.json")

# .osd 的 method → schema 的 aggregation
METHOD_MAP = {
    "sum": "sum",
    "mean": "mean",
    "mean_coded": "mean",
    "mean_score": "mean",
    "count_true": "count_true",
    "weighted_sum": "weighted_sum",
}
# 平铺维度的后缀：同一特质的两种聚合
VARIANT_SUFFIX = re.compile(r"_(sum|mean|mean_coded|count|total|score)$", re.I)


def find_osd(code: str) -> str | None:
    for base, _dirs, files in os.walk(OSD_DIR):
        if code + ".osd" in files:
            return os.path.join(base, code + ".osd")
    return None


def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _pool_lookup(pool: dict, key: str) -> str | None:
    """在翻译池里查键；兼容  带/不带 ipip_ 前缀、尾随空格。"""
    for cand in (key, key.strip(), f"ipip_{key.lstrip('ipip_').strip()}"):
        if cand in pool:
            return pool[cand]
    return None


# 非英文的常见功能词（出现 ≥2 个即判为可疑）。用于**题文语言校验**。
_LANG_PATTERNS = {
    "sv": r"\b(att|och|inte|är|för|med|som|jag|vill|rätt|allt|har|kan|det)\b",
    "de": r"\b(und|nicht|ich|das|ist|mit|für|auf|eine|dass|werden)\b",
    "fr": r"\b(les|des|une|est|que|qui|pour|dans|avec|pas)\b",
    "es": r"\b(los|las|una|que|para|con|por|como|más|pero)\b",
    "nl": r"\b(het|een|niet|van|dat|met|voor|zijn|worden)\b",
    "pt": r"\b(que|para|com|por|como|mais|mas|uma|dos|das)\b",
    "fi": r"\b(ja|on|ei|se|että|kun|niin|kuin|myös)\b",
}


def _looks_foreign(text: str) -> bool:
    """题文是否疑似非英文。

    ⚠️ 判据不能只看「功能词出现 ≥2 个」：英文句子里也会出现 ``on``（芬兰语词表
    里的 on）、``se``、``det`` 等短词——实测 AIDEP 第 14 题
    "…I rely on AI instead of a…" 就被误判成芬兰语。所以再加一条**比例**条件。
    """
    words = len(re.findall(r"[A-Za-zÀ-ÿ']+", text or ""))
    if not words:
        return False
    for pat in _LANG_PATTERNS.values():
        hits = re.findall(pat, text or "", re.I)
        if len(hits) >= 2 and (len(hits) / words) >= 0.18:
            return True
    return False


def _pick_text(candidates: list[str]) -> tuple[str, bool]:
    """从候选题文里挑一个：**优先通过语言校验的**。

    为什么需要：``translations`` 池是**多语言**的（一个 key 有几十种译文）。
    原来的做法是把所有语言池 ``update`` 合并成一个 dict，于是**按字母序靠后的
    语言会覆盖前面的**——实测 ``sv`` 覆盖了 ``en``，导致 IPIP-BFAS 第 54 题
    显示成瑞典语 ``Vill att allt ska vara precis rätt``。
    这里改成：先要语言合格的，没有再退回第一个非空的（并标记为可疑）。
    返回 (题文, 是否语言可疑)。
    """
    clean = [c for c in candidates if c and c.strip()]
    for c in clean:
        if not _looks_foreign(c):
            return c.strip(), False
    if clean:
        return clean[0].strip(), True
    return "", False


def _normalize_rule_items(raw: object) -> dict[str, int]:
    """把 ``scoring[dim].items`` 归一成 ``{item_id: ±1}``。

    ⚠️ 归档里这一步有两种形态（实测都要支持，否则一套量表都转不出来）：
      · dict：``{"ipip_catpd_001": 1, "ipip_catpd_002": -1}``   ← IPIP-CATPD
      · list：``["ipip_neo_001", "ipip_neo_002"]``                ← 别的量表
    list 形态没有方向信息，只能假定全部正向；而**反向计分必须写在别处**，
    所以这种形态要在转换时报警——猜方向是这类项目最危险的静默错误。
    """
    if isinstance(raw, dict):
        return {str(k): (1 if int(v) > 0 else -1) for k, v in raw.items()}
    if isinstance(raw, list):
        out = {}
        for entry in raw:
            if isinstance(entry, str):
                out[entry] = 1
            elif isinstance(entry, dict):
                iid = entry.get("id") or entry.get("item") or entry.get("item_id")
                if iid:
                    out[str(iid)] = 1 if int(entry.get("key", entry.get("weight", 1))) > 0 else -1
        return out
    return {}


def load_reverse_key_overrides(code: str) -> dict[str, list[str]]:
    """读「官方反向键」补充文件（如 data/catpd-reverse-keys.json）。

    为什么需要：归档的 ``IPIP-CATPD.osd`` 里有 12 个维度的 ``scoring.items`` 是
    **无方向的 list**（80 道题），光看归档判断不出哪些题反向计分。而 IPIP 官方的
    计分键页对每道反向题标了 ``(RK)``。实测两者对得上：官方 35 个反向题与归档
    21 个「有方向的维度」里的 35 个**逐维度完全一致**——所以这不是信息缺失，
    只是归档少存了一份，方向由权威来源提供。

    返回 ``{dimension_id: [reverse_item_id, ...]}``；没有该文件时返回空（此后
    list 形态维度的方向仍报警告，不会被静默当作全正向）。
    """
    candidates = [
        os.path.join(ROOT, "data", f"{code.lower()}-reverse-keys.json"),
        os.path.join(ROOT, "data", f"{code.lower().replace('ipip-', '')}-reverse-keys.json"),
    ]
    path = next((p for p in candidates if os.path.exists(p)), None)
    if not path:
        return {}
    data = load_json(path)
    out = {}
    # 形态一：{dimension_id: [反向题 id, …]}（HEXACO 的证据文件）
    #   空列表在这里是**有意义的答案**（官方页该 facet 只有 + keyed）。
    if "dimensions" not in data:
        for did, keys in data.items():
            if did.startswith("_") or did in ("source", "license", "evidence"):
                continue
            if isinstance(keys, list):
                out[did] = list(keys)
        return out
    # 形态二：{"dimensions": {id: {official_parsed: true, reverse_keyed_official: […]}}}
    for did, info in (data.get("dimensions") or {}).items():
        # 只认「确实解析过官方页」的维度。空数组是有意义的答案
        # （=官方声明该维度没有反向题），所以照收，不能因空而跳过。
        if info.get("official_parsed"):
            out[did] = list(info.get("reverse_keyed_official") or [])
    return out


def build_instrument(code: str, *, code_pool: dict, en_pool: dict,
                     text_overrides: dict[str, str] | None = None,
                     reverse_overrides: dict[str, list[str]] | None = None,
                     ) -> tuple[Instrument, list[str]]:
    """返回 (Instrument, 警告列表)。抛异常表示这份 .osd 结构不符合预期。"""
    path = find_osd(code)
    if not path:
        raise FileNotFoundError(f"找不到 {code}.osd")
    j = load_json(path)
    d = j.get("definition") or {}
    si = d.get("scale_info") or {}
    warn: list[str] = []
    text_overrides = text_overrides or {}
    reverse_overrides = reverse_overrides or {}

    # ── 一个已知缺陷：OpenScales 的 README 常报 "Items: 0"，但 definition.items 是全的。
    #    这里以 definition.items 为准，并把差异记进 provenance。
    raw_items = d.get("items") or []
    if not raw_items:
        raise ValueError(f"{code}: definition.items 为空，无法转换")

    # ── 变体选择（**这一步以前漏了，代价很大**）
    #    有些量表的题表里同时装着**多个语言变体**，用 ``variant_when`` 标注适用条件：
    #        57 题 {"selector":"language","value":["de"]}
    #        55 题 {"selector":"language","value":["en"]}
    #    并按 ``variants.sets.<lang>.items`` 给出各变体的题号清单、
    #    ``variants.default`` 给出默认变体。
    #    原来的做法是把 112 题**全部**收进来，于是量表里混着 57 道德文题
    #    （实测 PCI：112 题 = 57 德 + 55 英）。界面会同时显示两种语言的题。
    #    现在按 ``variants.default``（默认 en）只取该变体的题。
    variants = d.get("variants") or {}
    variant_axis = None
    if isinstance(variants, dict) and variants.get("sets"):
        dflt = variants.get("default")
        sets = variants.get("sets") or {}
        ids = None
        if dflt and isinstance(sets.get(dflt), dict):
            ids = sets[dflt].get("items")
        if not ids:                       # 没有 default 就挑 en，再退到第一个集合
            for k in ("en", "En", "EN"):
                if isinstance(sets.get(k), dict) and sets[k].get("items"):
                    dflt, ids = k, sets[k]["items"]
                    break
        if ids:
            allowed = set(ids)
            kept = [x for x in raw_items
                    if isinstance(x, dict) and (x.get("id") in allowed)]
            if kept:
                warn.append(f"按 variants.default={dflt!r} 只取该变体的 {len(kept)} 题"
                            f"（原题表 {len(raw_items)} 题含多语言变体）")
                raw_items = kept
                variant_axis = dflt

    # ── 题项正文
    translations = (j.get("translations") or {})
    tpool: dict = {}
    if isinstance(translations, dict):
        for v in translations.values():
            if isinstance(v, dict):
                tpool.update(v)
    # ⚠️ tpool 是**多语言混合池**，同一 key 的多种译文会互相覆盖（实测 sv 盖住 en）。
    #    所以除了混合池，还要单独拿英文池，让语言校验有得选。
    en_only: dict = {}
    if isinstance(translations, dict):
        for lang, v in translations.items():
            if isinstance(v, dict) and str(lang).lower().startswith("en"):
                en_only.update(v)
    if isinstance(en_pool, dict):
        en_only.update(en_pool)

    items: list[Item] = []
    missing: list[str] = []
    for order, raw in enumerate(raw_items, start=1):
        iid = raw.get("id") or f"{code.lower()}_{order:03d}"
        text = (raw.get("text") or "").strip()
        src = "embedded" if text else ""
        if not text:
            key = (raw.get("text_key") or "").strip()
            if key:
                bare = key[len("ipip_"):] if key.startswith("ipip_") else key
                # 显式列出候选（**英文在前**），再交给 _pick_text 做语言校验。
                # 不用 `or` 链，是因为那会把「第一个非空」当成答案——
                # 而第一个非空可能正是瑞典语。
                cands = [
                    text_overrides.get(key) or "",
                    text_overrides.get(bare) or "",
                    code_pool.get(bare.strip()) or "",
                    _pool_lookup(en_only, key) or "",
                    _pool_lookup(en_pool, key) or "",
                    _pool_lookup(tpool, key) or "",
                ]
                text, foreign = _pick_text(cands)
                if text:
                    src = "ipip_item_codes" if code_pool.get(bare.strip()) else "osd_translations"
                    if foreign:
                        warn.append(f"item {iid}: 题文未能通过语言校验，疑似非英文："
                                    f"{text[:48]!r}")
                else:
                    missing.append(key)
        if not text:
            warn.append(f"item {iid}: 题项正文解析失败（text_key={raw.get('text_key')!r}）")
        items.append(Item(order=order, id=iid, text=text or f"[缺失正文: {iid}]",
                          source_code=(raw.get("text_key") or "").replace("ipip_", "").strip() or None,
                          text_source=src or None))

    if missing:
        warn.append(f"{len(missing)} 个 text_key 在主池与翻译池里都找不到：{missing[:6]}")

    # ── 计分规则 → 维度 + rubric
    scoring_raw = d.get("scoring") or {}
    if not scoring_raw:
        raise ValueError(f"{code}: definition.scoring 为空，无法计分")

    # 归一平铺变体：nonplanfulness_sum / nonplanfulness_mean → base=nonplanfulness
    by_base: dict[str, list[tuple[str, dict]]] = {}
    for dim_id, rule in scoring_raw.items():
        base = VARIANT_SUFFIX.sub("", dim_id)
        by_base.setdefault(base, []).append((dim_id, rule))

    dim_names = {x.get("id"): (x.get("name") or x.get("id"))
                 for x in (d.get("dimensions") or [])}

    dimensions: list[Dimension] = []
    rubrics: dict[str, Rubric] = {}
    claimed: dict[str, int] = {}          # item_id → key（±1），用于回填 Item.key
    for base, variants in sorted(by_base.items()):
        # 聚合方式：优先 mean（对跨长度维度可比），否则取第一条
        chosen_id, chosen = None, None
        for did, rule in variants:
            if METHOD_MAP.get(str(rule.get("method", "")).lower()) == "mean":
                chosen_id, chosen = did, rule
                break
        if chosen is None:
            chosen_id, chosen = variants[0]

        raw_rule_items = chosen.get("items")
        item_keys = _normalize_rule_items(raw_rule_items)
        if isinstance(raw_rule_items, list):
            if base in reverse_overrides:
                # 归档没存方向，但官方计分键给了权威答案（可能是「0 个反向题」）
                official_rk = set(reverse_overrides[base])
                item_keys = {iid: (-1 if iid in official_rk else 1) for iid in item_keys}
                if official_rk:
                    warn.append(
                        f"维度 {base}: 归档 scoring.items 无方向，已用 IPIP 官方计分键"
                        f"补齐 {len(official_rk)} 个反向题")
            else:
                warn.append(
                    f"维度 {base}: 归档 scoring.items 是 list 形态，且官方计分键没有"
                    "可用的答案，已一律按正向处理——**该维度方向不可信，收录前必须补齐**")
        if not item_keys:
            warn.append(f"维度 {base}: 计分规则里没有题项，跳过")
            continue
        # ⚠️ 变体过滤之后，另一种语言的维度可能**一题都不剩**（如 PCI 的德语维度）。
        #    这种维度不能建：它的题项已按 variants.default 被排除，
        #    建出来就会「引用不存在的 item」。所以按**过滤后的题表**再筛一次。
        live_ids = {it.id for it in items}
        live = {k: v for k, v in item_keys.items() if k in live_ids}
        if not live:
            continue
        if len(live) != len(item_keys):
            warn.append(f"维度 {base}: 变体过滤后 {len(item_keys) - len(live)} 题不在"
                        f"{variant_axis!r} 变体里，已从该维度移除")
        item_keys = live
        agg = METHOD_MAP.get(str(chosen.get("method", "")).lower())
        if agg is None:
            warn.append(f"维度 {base}: 未知 method={chosen.get('method')!r}，按 sum 处理")
            agg = "sum"

        members, reverse = [], []
        for iid, key in item_keys.items():
            members.append(iid)
            k = 1 if int(key) > 0 else -1
            if k == -1:
                reverse.append(iid)
            prev = claimed.get(iid)
            if prev is not None and prev != k:
                warn.append(f"题项 {iid} 在不同维度里计分方向不一致（{prev} vs {k}）")
            claimed[iid] = k

        nm = dim_names.get(base) or dim_names.get(chosen_id) or base
        nm = re.sub(r"\s*\((sum|mean)[^)]*\)\s*$", "", nm, flags=re.I).strip()
        dimensions.append(Dimension(
            id=base, name=nm, level=1,
            items=sorted(members, key=lambda x: next(
                (it.order for it in items if it.id == x), 10 ** 9)),
            reverse_keyed=sorted(reverse)))
        rubrics[base] = Rubric(
            id=base, label=nm, aggregation=agg, scope="items",
            of=dimensions[-1].items,
            notes=f"来源 {chosen_id}（method={chosen.get('method')}）"
                  + (f"；同源变体 {[v[0] for v in variants if v[0] != chosen_id]}"
                     if len(variants) > 1 else ""))

    # 回填每道题的反向计分方向（题项自己的 key 必须与维度声明一致）
    for it in items:
        it.key = claimed.get(it.id, 1)

    # 每道题挂上它所属的维度（多归属时全列）
    for dim in dimensions:
        for iid in dim.items:
            for it in items:
                if it.id == iid and dim.id not in it.dimensions:
                    it.dimensions.append(dim.id)

    # ── 作答格式（标签也是键，要解析）
    lo = d.get("likert_options") or {}
    labels = []
    for lb in (lo.get("labels") or []):
        labels.append(_pool_lookup(tpool, lb) or _pool_lookup(en_pool, lb) or str(lb))
    qhead = lo.get("question_head") or ""
    qhead = _pool_lookup(tpool, qhead) or _pool_lookup(en_pool, qhead) or qhead
    # 有些量表是**纯数值刻度**（无文字标签），如 ESS-ITS 的 0–10（11 点）、
    # SECS 的 0–100。它们有 `points`/`min`/`max` 但没有 `labels`。
    # 这类**不能当成缺作答格式排除**——刻度是明确的，只是没有词标签。
    # 做法：用分值数字合成标签，并在 structure 里标注 `numeric_scale`。
    points = lo.get("points")
    lo_min = int(lo.get("min", 0))
    if not points:
        # 没有任何刻度信息时，从 scoring 的 description 里找「Range a–b」
        # （SECS 就属于这种：description 写明 "0-100"）。
        m = re.search(r"\b(\d{1,3})\s*[-–]\s*(\d{1,3})\b",
                      str((d.get("scoring") or {}).get(
                          next(iter(d.get("scoring") or {}), ""), {}).get("description", ""))
                      if d.get("scoring") else "")
        if m:
            lo_min, hi = int(m.group(1)), int(m.group(2))
            points = hi - lo_min + 1
    numeric_scale = False
    if points and not labels:
        numeric_scale = True
        labels = [str(lo_min + i) for i in range(int(points))]
    resp = None
    if points and labels and len(labels) == int(points):
        resp = ResponseFormat(points=int(points), min=lo_min,
                              max=int(lo.get("max", lo_min + int(points) - 1)),
                              labels=labels, question_head=re.sub(r"<[^>]+>", " ", qhead).strip())

    # ── 授权
    lic_field = str(si.get("license") or "").strip()
    impl = d.get("implementation") or {}
    kind, redist = "unknown", False
    if re.search(r"public domain", lic_field, re.I):
        kind, redist = "public_domain", True
    elif re.search(r"CC BY[- ]?NC", lic_field, re.I):
        kind, redist = "cc_by_nc", True          # 可再分发，但禁商用
    elif re.search(r"CC BY", lic_field, re.I):
        kind, redist = "cc_by", True
    elif re.search(r"copyright", lic_field, re.I):
        kind, redist = "copyright_permitted", True
    elif lic_field:
        warn.append(f"授权字段未能归类：{lic_field!r}——按 unknown 处理（默认不可再分发）")
    license_obj = License(
        kind=kind,
        holder=str(impl.get("organization") or si.get("organization") or ""),
        text=lic_field or "(归档未标注)",
        url=str(si.get("url") or ""),
        evidence=f"{os.path.relpath(path, ROOT).replace(os.sep, '/')}"
                 f"（scale_info.license）",
        redistribution=redist,
        notes=f"URL: {si.get('url', '')}" if si.get("url") else "")

    inst = Instrument(
        instrument=code,
        display_name=str(si.get("name") or code),
        citation=str(si.get("citation") or ""),
        license=license_obj,
        structure={
            "dimensions": len(dimensions),
            "items": len(items),
            "source": "OpenScales .osd",
            "description": str(si.get("description") or ""),
        },
        items=items, dimensions=dimensions, scoring=rubrics,
        version=str(si.get("version") or "1.0"),
        response_format=resp,
        item_order_source=f"{os.path.relpath(path, ROOT).replace(os.sep, '/')} "
                          f"→ definition.items 顺序",
        provenance={
            "converter": "tools/build_scales.py",
            "source_file": os.path.relpath(path, ROOT).replace(os.sep, "/"),
            "osd_version": str(j.get("osd_version") or ""),
            "dimension_variants_normalized": {
                base: [v[0] for v in vs] for base, vs in by_base.items() if len(vs) > 1},
            "notes": "IPIP 系 .osd 的 dimensions 把 _sum/_mean 平铺成两项，已归一为单维度",
        })
    return inst, warn


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="列出所有可转量表")
    ap.add_argument("--only", action="append", default=[], help="只转指定 code（可多次）")
    ap.add_argument("--family", choices=["ipip"], help="按家族批量转")
    ap.add_argument("--all", action="store_true", help="转该家族全部")
    ap.add_argument("--check", action="store_true", help="只校验，不落盘")
    ap.add_argument("--limit", type=int, default=0, help="批量时最多转几套")
    args = ap.parse_args()

    code_pool = (load_json(CODES_FILE).get("code_to_text") or {})
    en_pool = load_json(EN_TRANSLATIONS) if os.path.exists(EN_TRANSLATIONS) else {}
    if not isinstance(code_pool, dict):
        raise SystemExit(f"code_to_text 不是对象：{type(code_pool)}")
    if not isinstance(en_pool, dict):
        raise SystemExit(f"翻译池不是对象：{type(en_pool)}")

    if args.list:
        rows = []
        for base, _dirs, files in os.walk(OSD_DIR):
            for fn in files:
                if fn.endswith(".osd"):
                    rows.append((os.path.basename(fn)[:-4],
                                 os.path.relpath(os.path.join(base, fn), ROOT)))
        for c, p in sorted(rows):
            print(f"  {c:28} {p}")
        print(f"\n共 {len(rows)} 个 .osd")
        return 0

    targets = list(args.only)
    if args.family == "ipip" and args.all:
        fam = []
        for base, _dirs, files in os.walk(OSD_DIR):
            if os.sep + "ipip" + os.sep not in base + os.sep:
                continue
            for fn in files:
                if fn.endswith(".osd") and not fn.startswith("ipip_master"):
                    fam.append(fn[:-4])
        targets += sorted(set(fam))
    if args.limit:
        targets = targets[:args.limit]
    if not targets:
        ap.error("没有目标：用 --only CODE 或 --family ipip --all")

    if not args.check:
        os.makedirs(OUT_DIR, exist_ok=True)

    ok = bad = 0
    for code in targets:
        try:
            inst, warn = build_instrument(code, code_pool=code_pool, en_pool=en_pool,
                                          reverse_overrides=load_reverse_key_overrides(code))
        except Exception as exc:                     # noqa: BLE001
            print(f"  ✗ {code}: {exc}")
            bad += 1
            continue
        errs = inst.validate(require_redistributable=True)
        missing_text = sum(1 for it in inst.items if it.text.startswith("[缺失正文"))
        flag = "✓" if not errs else "✗"
        print(f"  {flag} {code:24} {len(inst.items):4} 题 · {len(inst.dimensions):3} 维 · "
              f"{len(inst.scoring):3} 规则 · 缺正文 {missing_text} · "
              f"授权 {inst.license.kind}/{inst.license.redistribution}"
              + (f"  ← {len(errs)} 个问题" if errs else ""))
        for e in errs[:4]:
            print(f"        ! {e}")
        for w in warn[:3]:
            print(f"        · {w}")
        if errs:
            bad += 1
        else:
            ok += 1
            if not args.check:
                out = os.path.join(OUT_DIR, code.lower().replace("-", "-") + ".json")
                with open(out, "w", encoding="utf-8") as fh:
                    json.dump(inst.to_dict(), fh, ensure_ascii=False, indent=1)
                    fh.write("\n")
                print(f"        → {os.path.relpath(out, ROOT)}")

    print(f"\n通过 {ok}，失败 {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
