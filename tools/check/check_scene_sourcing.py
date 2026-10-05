#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""材料可查性哨兵：606 题**每一题在材料库里能不能查到**。

它防的是什么
============
情景展示（`content/scenes/<scale>.json`）必须**基于材料**写，不能凭空编。
材料在 `data/text-db/text-db.json` 的 `entries` 里，按**英文题干**索引，每条带
`scaffold`（人工核对过的 sense/asks/counts/mis…）或 `note`（只有一段自由文本）。
但两边的写法并不总是逐字节相同（`hang-gliding` vs `hang gliding`、
`I keep` vs `Ikeep`…）。这类差异会让作者**在不知情的情况下**「查不到材料」于是自己编，
而这**不会报错**：界面只是少一块依据，没人会发现。

所以本哨兵只做一件事：**逐题确认「材料在库里查得到」**，并把「查不到」标红。

⚠️ 它**只是材料可查性哨兵**：绿 = 每一题都能找到材料出处；
**不代表情景句的内容正确、不代表作者真的读了材料、也不校验措辞质量**。
内容质量的检查在 `tools/check/ipip_scene_check.py`（IPIP）与后续各册的同类脚本。

查找通道（三条，**回退通道必须被看见**）
======================================
1. **`text_en`**：界面上的题干 → `textkey.norm_key()` 归一化 → 查规范索引；
2. **`text_en_verbatim` 回退**（**仅当该题有这一字段时**）：题干在用户可见层做过
   排版修复（`Ikeep`→`I keep`、`enjoylife`→`enjoy life`…，共 23 题），而材料库 key
   按 R1 **保留源件 verbatim 形态**——所以要用 verbatim 形态才查得到。
   **这不是缺陷，是分层的正确表现**（修过的展示层 ↔ 原始的材料层）。
3. 两条都不中 ⇒ **红**（判红条件不变：材料在库里却查不到）。
输出里**分别统计**三种，回退命中单独成列——否则下次不知道有多少题靠回退才对上。

归一化只有一个真相源
====================
`tools/textkey.py` 的 `norm_key()`（converge-read 落地）：NFKC、小写、弯引号统一、
连字符/破折号折空格、**保留中日韩字符**（⚠️ 用 `[^a-z0-9 ]` 白名单会把 Mania 那 5 题的
中文题干整段删掉、两边都塌成 `1`/`2` 而**假绿**——踩过，别重犯）。
索引 `data/text-db/index-norm.json` 由 `build_text_db.py` 生成、**不许手改**。
本哨兵不自己实现归一化：优先用 `textkey`；索引文件缺失时才现场 `build_index()` 派生；
`textkey` 都不可用时才退回内建（并**明确打印**退回了）。

━━ 历史与根因（留痕，别删）━━
* 2026-10-05 首次跑：**9 题**「材料在库里却按字面英文 key 查不到」——
  `ipip_neo_109/236/300`（hang-gliding / soft-hearted / last-minute）+
  `pid5_045/059/124/125/190/199`（long-lasting / dream-like / day-to-day /
  Sweet-talking / so-called / off-task）。根因：entry key 派生时**抹掉连字符与弯引号**，
  而 `items[].text_en` 保留原样。（我第一版甚至还把连字符直接删掉、误判成「3 题」——
  教训：先验证再下结论。）处置：统一 `norm_key()` + 生成器产出的规范索引。
* **2026-10-05 修掉一个「哨兵自己坏了却伪装成真红」的 bug**：近似（fuzzy）兜底分支
  曾把 `found` 赋成 entry **字典**，而后续按 `(key, entry)` 元组取 `found[1]`，
  于是走进该分支必 `KeyError: 1`；崩溃退出码与「真的发现漏读」同为 1，**不可区分**。
  现在**所有分支统一产出 `(entry key, entry)` 或 `None`**——
  **兜底分支不允许留在崩溃路径上**：它恰恰是发现问题的路径。

用法
====
    python tools/check/check_scene_sourcing.py            # 全量检查（有红 → 退出码 1）
    python tools/check/check_scene_sourcing.py --items    # 额外逐题列出分类与命中通道
    python tools/check/check_scene_sourcing.py --index P  # 仅测试：指定索引（默认规范路径）
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))          # tools/
from _root import find_root, force_utf8_io  # noqa: E402
ROOT = str(find_root())

STRUCT_DIR = os.path.join(ROOT, "data", "items-structured")
TEXT_DB = os.path.join(ROOT, "data", "text-db", "text-db.json")
INDEX_NORM = os.path.join(ROOT, "data", "text-db", "index-norm.json")
#: 相似度兜底：两条通道都不中时，同量表内 ≥ 此值视为「疑似同题但措辞不符」（只作诊断，不改变判红）
FUZZY = 0.85


def _builtin_norm(s: str) -> str:
    """内建归一化（与 `textkey.norm_key()` 同规则）——**只在 textkey 不可用时**兜底。"""
    s = unicodedata.normalize("NFKC", s or "").lower()
    out = []
    for ch in s:
        if ch in "-\u2010\u2011\u2012\u2013\u2014\u2015\u2212\u00ad":
            out.append(" ")
        elif ch.isalnum() or ch.isspace() or ch in "'\"":
            out.append(ch)
        else:
            out.append(" ")
    return re.sub(r"\s+", " ", "".join(out)).strip()


def _load_tools():
    """归一化函数与索引构造器的来源：优先 `tools/textkey.py`（全项目唯一实现）。"""
    try:
        import textkey  # type: ignore
        if callable(getattr(textkey, "norm_key", None)) \
                and callable(getattr(textkey, "build_index", None)):
            textkey.norm_key("Worry about things.")          # 冒烟
            return textkey, textkey.norm_key, "tools/textkey.py 的 norm_key()（全项目唯一实现）"
    except Exception:
        pass
    return None, _builtin_norm, "内建归一化（⚠️ tools/textkey.py 不可用，已退回）"


def _entry_kind(entry: dict) -> str:
    """材料来源类型：完整脚手架 / 仅自由文本。"""
    sc = entry.get("scaffold")
    if sc and any(v not in (None, "", [], {}) for v in sc.values()):
        return "scaffold"
    return "note"          # 有条目就算「仅自由文本」（最差也有 zh/en）


def _load_index(entries: dict, path: str, textkey):
    """读规范索引；返回 (映射, 漂移条目列表, 比纯派生多出的键数)。索引不存在→(None,[],0)。"""
    if not os.path.exists(path):
        return None, [], 0
    raw = json.load(open(path, encoding="utf-8"))
    m = raw
    if isinstance(raw, dict):
        for k in ("map", "index", "entries", "items"):
            if isinstance(raw.get(k), dict):
                m = raw[k]
                break
    if not isinstance(m, dict):
        return None, [f"结构无法识别：{type(raw).__name__}"], 0
    bad = [k for k, v in m.items() if not isinstance(v, str) or v not in entries]
    extra = 0
    if textkey is not None:
        extra = len(set(m) - set(textkey.build_index(entries)))
    return m, bad, extra


def main() -> int:
    # UTF-8 兜底：唯一实现在 tools/_root.py。Windows 默认控制台是 GBK，下面的 ✅/⚠️/❌
    # 会让 print 抛 UnicodeEncodeError —— 崩溃点在**输出结果那一行**，退出码 1 与
    # 「真的发现漏读」不可区分，于是完好的哨兵在默认控制台上永远假装变红。
    force_utf8_io()
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", action="store_true", help="逐题列出分类与命中通道")
    ap.add_argument("--index", default=INDEX_NORM,
                    help="规范索引路径（默认 data/text-db/index-norm.json；仅供测试）")
    args = ap.parse_args()

    entries = json.load(open(TEXT_DB, encoding="utf-8"))["entries"]
    textkey, norm_key, norm_src = _load_tools()
    idx_norm, idx_bad, idx_extra = _load_index(entries, args.index, textkey)

    if idx_norm is not None:
        idx = idx_norm
        idx_src = f"规范索引 {os.path.relpath(args.index, ROOT)}（{len(idx)} 条）"
    else:
        idx = (textkey.build_index(entries) if textkey is not None else
               {norm_key(k): k for k in sorted(entries) if norm_key(k)})
        idx_src = f"⚠️ 索引文件不存在，现场派生（{len(idx)} 条）"

    n_en = n_vb = 0
    reds = []
    classes = {"scaffold": 0, "note": 0, "无": 0}
    per_scale = {}
    rows = []

    for fn in sorted(os.listdir(STRUCT_DIR)):
        if not fn.endswith(".json") or fn == "index.json":
            continue
        data = json.load(open(os.path.join(STRUCT_DIR, fn), encoding="utf-8"))
        code = data.get("code") or fn[:-5]
        scale_pairs = [(k, v) for k, v in entries.items()
                       if any(str(i).lower() == code.lower()
                              for i in (v.get("instruments") or []))]
        stat = {"n": 0, "scaffold": 0, "note": 0, "无": 0, "en": 0, "vb": 0, "red": 0}
        for it in data.get("items", []):
            stat["n"] += 1
            # ── 三条通道；`found` **永远**是 (entry key, entry) 或 None ──
            found = None
            channel = None
            for field, label in (("text_en", "text_en"),
                                 ("text_en_verbatim", "text_en_verbatim")):
                text = it.get(field)
                if not text:
                    continue
                nk = norm_key(text)
                key = idx.get(nk) if nk else None
                if key is not None and key in entries:
                    found = (key, entries[key])          # ← 统一形态，别处不再拆
                    channel = label
                    break

            fuzzy_hint = None
            if found is None:
                # 诊断用：同量表内是否有高相似材料（只解释「红得像不像漏配」，不改变判红）
                base = norm_key(it.get("text_en"))
                best = (0.0, None, None)
                if base:
                    for k, v in scale_pairs:
                        r = difflib.SequenceMatcher(None, base, norm_key(v.get("en"))).ratio()
                        if r > best[0]:
                            best = (r, k, v)
                if best[0] >= FUZZY:
                    fuzzy_hint = {"ratio": round(best[0], 3), "key": best[1]}

            if found is None:
                kind = "无"
                classes["无"] += 1
                stat["无"] += 1
                stat["red"] += 1
                reds.append({"id": it["id"], "scale": code,
                             "stem": it.get("text_en") or "",
                             "verbatim": it.get("text_en_verbatim"),
                             "hint": fuzzy_hint})
                channel = "红"
            else:
                kind = _entry_kind(found[1])
                classes[kind] += 1
                stat[kind] += 1
                if channel == "text_en":
                    n_en += 1
                    stat["en"] += 1
                else:
                    n_vb += 1
                    stat["vb"] += 1

            if args.items:
                key_shown = found[0] if found else "—"
                rows.append(f"  {it['id']:<22} {kind:<9} {str(channel):<17} {key_shown[:44]}")

        per_scale[code] = stat

    tot = sum(s["n"] for s in per_scale.values())
    print("=" * 104)
    print("材料可查性哨兵（606 题逐题确认「材料在库里查得到」）")
    print("⚠️ 绿只代表**材料可查**，不代表情景内容正确、也不校验措辞质量")
    print("=" * 104)
    print(f"归一化函数：{norm_src}")
    print(f"索引　　　：{idx_src}")
    if idx_extra:
        print(f"    ⚠️ 索引比「纯 entries 派生」多 {idx_extra} 条"
              f"（预期 624 条、无别名；多出的键=已登记别名，撤掉后由 `text_en_verbatim` 回退接管）")
    if idx_bad:
        print(f"    ❌ 索引漂移：{len(idx_bad)} 条指向不存在的 entry key（见下方）")
    print()
    print("① 材料来源类型")
    print(f"   {'量表':<24}{'题数':>6}{'scaffold':>10}{'note':>8}{'无':>6}")
    for code, s in per_scale.items():
        print(f"   {code:<24}{s['n']:>6}{s['scaffold']:>10}{s['note']:>8}{s['无']:>6}")
    print(f"   {'合计':<24}{tot:>6}{classes['scaffold']:>10}{classes['note']:>8}{classes['无']:>6}")
    print()
    print("② 命中通道（回退必须被看见）")
    print(f"   {'量表':<24}{'题数':>6}{'text_en 命中':>14}{'verbatim 回退':>14}{'红':>6}")
    for code, s in per_scale.items():
        print(f"   {code:<24}{s['n']:>6}{s['en']:>14}{s['vb']:>14}{s['red']:>6}")
    print(f"   {'合计':<24}{tot:>6}{n_en:>14}{n_vb:>14}{len(reds):>6}")

    if args.items and rows:
        print("\n③ 逐题分类与命中通道：")
        print("\n".join(rows))

    if idx_bad:
        print(f"\n❌ 索引漂移：{len(idx_bad)} 条指向不存在的 entry key：")
        for k in idx_bad[:20]:
            print(f"   · {k} → {idx_norm.get(k)!r}")
        print("   （索引由 build_text_db.py 生成、不许手改；请重新生成）")

    if reds:
        print(f"\n❌ {len(reds)} 题「材料在库里，但三条通道都查不到」——静默漏读风险：")
        for r in reds:
            print(f"   · {r['id']}（{r['scale']}）")
            print(f"       题干英文　：{r['stem']}")
            if r["verbatim"]:
                print(f"       verbatim ：{r['verbatim']}")
            if r["hint"]:
                print(f"       疑似同题（相似度 {r['hint']['ratio']}）材料 key：{r['hint']['key']}")
        return 1
    print(f"\n✅ {tot} 题全部查得到材料（`text_en` {n_en} + `text_en_verbatim` 回退 {n_vb}），无静默漏读。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
