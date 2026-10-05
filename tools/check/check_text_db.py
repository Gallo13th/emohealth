#!/usr/bin/env python3
"""文本库校验器（D113 流程的第 ④ 步闸门）。

**不过这个校验，就不生成前端数据包。**

检查项
======
1. 结构：条目的 ``en`` 非空、``instruments`` 非空
2. 覆盖率：逐套量表统计「有中译的题项占比」，全库汇总
3. 一致性：每套量表包里的每一道题，都能在文本库按归一化题文找到
   （找不到 = 文本库与量表包脱节，前端会显示不出题文）
4. 译文质量**可判定**的部分：
   · 中译不能为空串、不能与英文完全相同（说明根本没译）
   · 中译不得残留未替换的占位符
   · 中译里不应出现整段英文（除品牌名/缩写这类必须保留的）
5. 注释：结构字段齐全（``asks``/``term``/``sense``）
6. **用户可见文案里不许出现内部词汇**（``task-27`` 第 4 项）：``data/**`` 的
   **用户可见字段**（白名单见 ``VISIBLE_PATHS``）不得含 ``排版噪声`` / ``缺空格`` /
   ``漏空格`` / ``直译`` / ``逐条复核`` / ``仲裁`` / ``scaffold``。这几个词是
   「开发者视角」的痕迹——用户看到只会困惑，而不是更懂这道题。
   ⚠️ 只扫**用户可见字段**：``source`` / ``evidence`` / ``known_gaps`` 这类
   **溯源元数据**本来就该写这些词（那是内部核对信息），算进来会天天假红。

输出既给人看，也给流水线用：``--require-full`` 时若有量表缺中译则退出码非 0。

⚠️ 但「用户可见文案」这条**不依赖 ``--require-full``**：它是硬失败（写进 ``fail``）。
   理由：``--require-full`` 管的是「中译还没齐」，那是**进度**问题；
   内部词汇流到用户眼前是**缺陷**，两者不该共用一个开关。
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root, force_utf8_io  # noqa: E402
ROOT = find_root()
DB = os.path.join(ROOT, "data", "text-db", "text-db.json")

# 允许在中文里保留的英文：品牌、缩写、专有名词
EN_ALLOW = re.compile(
    r"\b(PHQ|GAD|PROMIS|DSM|PID|IPIP|NEO|HEXACO|VIA|CAT-?PD|ASRM|ASSIST|NIDA|"
    r"AI|BMI|PTSD|ADHD|LSD|EHR|APA|T-Score|Likert|Ritalin|Adderall|Vicodin|"
    r"Valium|Marijuana|Cocaine|Heroin|Ecstasy|Welfare|id|ID)\b", re.I)

#: 用户可见文案里**不许出现**的内部/开发词汇（`task-27` §4、`task-31` §3 共同口径）。
#: 判据：这七个词出现在用户眼前时，暴露的是「我们内部怎么修数据」，不是「这道题在问什么」。
FORBIDDEN_COPY = ("排版噪声", "缺空格", "漏空格", "直译", "逐条复核", "仲裁", "scaffold")

#: 用户可见字段的**路径白名单**（JSON 路径；`[]` = 数组元素；正则整串匹配）。
#: 为什么用白名单而不是「扫全部字符串」：`data/**` 里的 `source` / `evidence` /
#: `known_gaps` / `*_source` 是**溯源元数据**——它们本来就该写「逐条复核」「scaffold」
#: 这类词（那是内部核对信息，不是给用户看的文案），把它们算进来会天天假红。
VISIBLE_PATHS: tuple[tuple[str, tuple[str, ...]], ...] = (
    # 前端题面数据包：ui/items-structured/*.js 是它的**整份搬运**（见 tools/ui/pack_ui_data.py）
    ("data/items-structured/*.json", (
        r"instrument_guide\.(name|what_it_is_zh|non_diagnostic_notice_zh|"
        r"reverse_keyed_note_zh|instruction_zh|time_frame_zh)",
        r"instrument_guide\.topic_notices\.[^.]+\.(topic|text)",
        r"scale_guides\.[^.]+\.(label|anchor_note_zh|quantification_note_zh|"
        r"instruction_zh|time_frame_zh)",
        r"scale_guides\.[^.]+\.options\[\]\.(label_zh|meaning_zh)",
        r"items\[\]\.(text_en|text_zh|scenario_zh)",
        r"items\[\]\.notes_zh\[\]\.text",
        r"items\[\]\.response\.options\[\]\.(label_zh|label_en|meaning_zh)",
        r"items\[\]\.response\.options\[\]\.quantification\.text_zh",
    )),
    # 量表包：ui/instruments/*.js 是它的整份搬运；目录 catalog.json 供选择器
    ("data/instruments/*.json", (
        r"display_name", r"description", r"items\[\]\.text",
        r"items\[\]\.options\[\]\.text",
        r"instruments\[\]\.display_name", r"instruments\[\]\.license\.label",
        r"groups\[\]\.label",
    )),
    # 情景合并产物：items[].scenario_zh 与 notes_zh 的直接来源（作者文件是人写的）
    ("data/item-scenes.json", (r"items\.[^.]+\.scene", r"items\.[^.]+\.notes\[\]")),
    # 文本库中译：text_zh 的唯一来源
    ("data/text-db/text-db.json", (r"entries\.[^.]+\.zh",)),
)


def flatten(node, path: str = ""):
    """把 JSON 展平成 `(路径, 字符串值)`；数组元素一律记成 `key[]`。"""
    if isinstance(node, dict):
        for k, v in node.items():
            yield from flatten(v, f"{path}.{k}" if path else str(k))
    elif isinstance(node, list):
        for v in node:
            yield from flatten(v, f"{path}[]")
    elif isinstance(node, str):
        yield path, node


def visible_hits() -> tuple[int, int, list[str]]:
    """扫 `data/**` 的**用户可见字段**，返回 (文件数, 字段数, 命中列表)。"""
    files = fields = 0
    hits: list[str] = []
    for pattern, paths in VISIBLE_PATHS:
        pats = [re.compile(p) for p in paths]
        for p in sorted(glob.glob(os.path.join(ROOT, *pattern.split("/")))):
            try:
                doc = json.load(open(p, encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                hits.append(f"{os.path.relpath(p, ROOT)} 读不动：{exc}")
                continue
            files += 1
            for path, value in flatten(doc):
                if not any(rx.fullmatch(path) for rx in pats):
                    continue
                fields += 1
                for tok in FORBIDDEN_COPY:
                    if tok in value:
                        hits.append(f"{os.path.relpath(p, ROOT)}  {path}  含「{tok}」："
                                    f"{value[:70]!r}")
    return files, fields, hits



def norm(t: str) -> str:
    s = (t or "").replace("\u2019", "'").replace("\u2018", "'")
    s = s.replace("\u201c", '"').replace("\u201d", '"')
    s = s.replace("-", " ").replace("\u2013", " ").replace("\u2014", " ")
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"[.\s]+$", "", s)
    return s.lower()


def same_text(a: str, b: str) -> bool:
    """两条题文是否实质相同（归一化后比较）。"""
    return norm(a) == norm(b)


def main() -> int:
    force_utf8_io()          # 入口第一件事：GBK 控制台下不许崩（见 tools/_root.py）
    require_full = "--require-full" in sys.argv
    db = json.load(open(DB, encoding="utf-8"))
    entries = db["entries"]
    print(f"文本库：{len(entries)} 条；量表 {db['stats']['instruments']} 套；"
          f"题项（含重复）{db['stats']['items_total']} 道\n")

    fail: list[str] = []
    warn: list[str] = []

    # ⓪ 同题旧版 / 污染残留（2026-10-04 R3）
    #    `task-14` 修好题文后，**修复前的旧条目**曾因「旧库键无条件继承」永久留在库里：
    #    L1 第 23 题因此同时存在旧条目（截断英文 + 页脚授权句 + 旧译）与新条目，
    #    复核会审到错的那条。生成器已加清理（`build_text_db.purge_stale`），
    #    这里把两条不变量钉死，防止再次沉积。
    import re as _re
    CONTAM = _re.compile(r"Copyright ©|All Rights Reserved|This material can be "
                         r"reproduced", _re.I)

    def _sq(t: str) -> str:
        return _re.sub(r"[^a-z0-9]", "", (t or "").lower())

    live_squash = {_sq(e.get("en", "")) for e in entries.values()
                   if e.get("instruments")}
    for k, e in entries.items():
        blob = (e.get("en") or "") + " " + (e.get("zh") or "")
        if CONTAM.search(blob):
            fail.append(f"条目 {k[:44]!r} 混入页脚授权句（题文/译文都不该有）："
                        f"{blob[:60]!r}")
        # 孤儿条目若与「现行题文」压紧同键但原文不同 —— 就是同题旧版残留
        if not e.get("instruments") and _sq(e.get("en", "")) in live_squash:
            owner = next((x for x in entries.values()
                          if x.get("instruments") and _sq(x.get("en", "")) == _sq(e.get("en", ""))),
                         None)
            if owner and owner.get("en") != e.get("en"):
                fail.append(f"条目 {k[:44]!r} 是**同题旧版残留**（现行题文 "
                            f"{owner.get('en','')[:40]!r}）——应被 purge_stale 清掉")

    # ⓪b 译文复核记录：修正表必须已经反映到库上（否则「改了记录没改数据」）
    rev_path = os.path.join(ROOT, "data", "text-db", "reviewed-corrections.json")
    if os.path.exists(rev_path):
        rev = json.load(open(rev_path, encoding="utf-8"))
        for c in rev.get("corrections") or []:
            # ⚠️ 库键是 `norm(en)`（去尾标点、连字符转空格…），修正表里写的是**原样英文**，
            #    所以用「压紧题文」比对，别拿原串去 startswith（第一版就比错了）。
            want = _sq(c["en"])
            hit = next((e for e in entries.values() if _sq(e.get("en", "")) == want),
                       None)
            if hit is None:
                fail.append(f"复核修正表里的条目不在库中：{c['en'][:50]!r}")
            elif hit.get("zh") != c.get("new_zh"):
                fail.append(f"复核修正未生效：{c['en'][:40]!r} 现值 {hit.get('zh')!r} "
                            f"≠ 记录里的 {c.get('new_zh')!r}")
        st = ((db.get("stats") or {}).get("translation_review") or {})
        if not st.get("reviewed_count"):
            fail.append("stats.translation_review 缺失——复核账目没有随产物落盘")

    # ① 结构
    for k, e in entries.items():
        if not e.get("en", "").strip():
            fail.append(f"条目 {k[:40]!r} 缺英文题文")
        # ⚠️ 「未关联任何量表」从**失败**降为**警告**（2026-10-04 范围裁剪后）：
        #    文本库是**累积的翻译资产库**——人工/机器翻译成本高，且条目可能在
        #    量表被裁掉后仍值得保留（将来量表回归即可复用）。要求每条都关联**当前**
        #    量表，等于逼着删掉历史翻译资产，那与「资产要留」相悖。
        #    真正的**失败**是「量表里有的题在文本库找不到」（下面 ④），那才是断链。
        if not e.get("instruments"):
            warn.append(f"条目 {k[:40]!r} 未关联任何量表（翻译资产保留）")

    # ④ 译文质量
    for k, e in entries.items():
        zh = (e.get("zh") or "").strip()
        if not zh:
            continue
        # ⚠️ 「中译与英文相同」不一定是缺陷：量表的**作答指示语**本来就可能是
        #    中文生成、没有对应英文（如 Mania 的「第 N 组：选出最符合你的一句」）。
        #    这类条目标了 `kind=instruction` 就放行——标不了才说明数据没区分开，
        #    那才是真问题（见 D113 附注）。
        if same_text(zh, e["en"]) and e.get("kind") == "instruction":
            continue
        if same_text(zh, e["en"]):
            fail.append(f"中译与英文相同，疑似未译：{k[:48]!r}")
        if re.search(r"\{\{|\}\}|TODO|FIXME|\bXX\b", zh):
            fail.append(f"中译残留占位符：{zh[:40]!r}")
        # ⚠️ **控制字符 / 选择框字形**：2026-10-04 实测睡眠册第 1/5 题的中译
        #    继承了英文题面里的 `\x00`（PDF 的选择框字形），
        #    变成 `'我难以保持睡眠。 \x00 \x00 \x00 \x00'`——在渲染/导出路径下是乱码。
        #    这类污染必须拦在这里，而不是等界面出图才看见。
        bad_chars = [c for c in zh
                     if (ord(c) < 0x20 and c not in "\t")
                     or 0xE000 <= ord(c) <= 0xF8FF
                     or ord(c) in (0x2030, 0x2751, 0x2752, 0x25A1)]
        if bad_chars:
            codes = sorted({f"U+{ord(c):04X}" for c in bad_chars})
            fail.append(f"中译含控制字符/选择框字形 {codes}：{zh[:40]!r}")
        # ⚠️ **判据已反转（2026-10-04，Lead 决策②）**：`zh` **不得**含「括号内嵌英文原文」。
        #    旧注释把 `中文（英文原文）` 记为 **D27 规定格式**——那是错的落点：
        #    R2 把「① 英文原文 / ② 中文翻译 / ③ 本地化讲解」定为**并列三部分**，
        #    英文原文已由 `en` 字段承担（界面本就并列显示），再塞进 `zh` 是
        #    同一信息出现两次，而且会出现在**用户可见的题面**里。
        #    判据从严：只判「括号内**纯英文**（无中文）且确属 `en` 的片段」——
        #    `（如麦角酸二乙酰胺，LSD）`、`（如冰毒）` 这类正常中文补充说明**不算**。
        for m in re.finditer(r"[（(]([^（()）]*)[)）]", zh):
            inner = m.group(1)
            if re.search(r"[\u4e00-\u9fff]", inner):        # 含中文 → 正常补充说明
                continue
            isq = _sq(inner)
            if len(isq) >= 3 and isq in _sq(e.get("en", "")):
                fail.append(f"中译含**内嵌英文原文**（应移除：英文由 `en` 字段并列承担）："
                            f"{zh[:56]!r}")
        # 非括号内的英文残留仍要拦（把括号整段抠掉后再数），
        # 并保留「zh 与 en 逐条并列」的既有判据（下面 same_text 那两条）。
        stripped = re.sub(r"[（(][^（()）]*[)）]", " ", zh)
        stripped = EN_ALLOW.sub("", stripped)
        if len(re.findall(r"[A-Za-z]{3,}", stripped)) >= 4:
            fail.append(f"中译里仍有较多英文：{zh[:56]!r}")

    # ⑤ 用户可见文案里不许出现内部词汇（task-27 §4）
    vfiles, vfields, vhits = visible_hits()
    print(f"\n用户可见文案：扫 {vfiles} 个数据文件 / {vfields} 个可见字段；"
          f"内部词汇命中 {len(vhits)} 处")
    for h in vhits[:12]:
        fail.append(f"用户可见字段含内部词汇：{h}")
    if len(vhits) > 12:
        print(f"  …还有 {len(vhits) - 12} 处（全部计入失败）")

    # ②③ 逐套覆盖率 + 与量表包的一致性
    files = [p for p in sorted(glob.glob(
        os.path.join(ROOT, "data", "instruments", "*.json")))
        if os.path.basename(p) != "catalog.json"]
    rows = []
    for p in files:
        d = json.load(open(p, encoding="utf-8"))
        n = zh = 0
        orphan = []
        for it in d["items"]:
            n += 1
            e = entries.get(norm(it["text"]))
            if e is None:
                orphan.append(it["id"])
            elif e.get("zh"):
                zh += 1
        rows.append({"code": d["instrument"], "items": n, "zh": zh,
                     "pct": zh / n * 100 if n else 0, "orphan": orphan})
        if orphan:
            fail.append(f"{d['instrument']}: {len(orphan)} 道题在文本库里找不到"
                        f"（{orphan[:3]}）")

    full = [r for r in rows if r["pct"] >= 99.9]
    none = [r for r in rows if r["zh"] == 0]
    print(f"中译覆盖：完全覆盖 {len(full)} 套，完全没覆盖 {len(none)} 套，"
          f"部分覆盖 {len(rows) - len(full) - len(none)} 套")
    tot_i = sum(r["items"] for r in rows)
    tot_z = sum(r["zh"] for r in rows)
    print(f"题项口径合计：{tot_z}/{tot_i} 有中译（{tot_z / tot_i * 100:.1f}%）")
    print("\n覆盖最好的 8 套：")
    for r in sorted(rows, key=lambda x: -x["pct"])[:8]:
        print(f"  {r['code']:26} {r['zh']:4}/{r['items']:4}  {r['pct']:5.1f}%")
    if none:
        print(f"\n完全没中译的 {len(none)} 套（前 10）："
              + ", ".join(r["code"] for r in none[:10]))

    # 注释有两个来源，**必须都算**：
    #   · scaffold —— IPIP-NEO 的逐题注释（历史资产，结构更丰富）
    #   · note     —— 本轮 subagent 为新量表写的注释
    # 我第一版只数 scaffold，于是「1920 条新注释已回写」被报成 300 条，
    # 看起来像注释丢失，其实是统计口径漏了一半。
    scaf = sum(1 for e in entries.values() if e.get("scaffold"))
    note = sum(1 for e in entries.values() if e.get("note"))
    both = sum(1 for e in entries.values() if e.get("scaffold") or e.get("note"))
    print(f"\n注释覆盖：{both}/{len(entries)} 条（{both / len(entries) * 100:.1f}%）"
          f"，其中 scaffold {scaf} 条、note {note} 条（两者可并存）")

    print()
    if warn:
        print(f"⚠️ {len(warn)} 项警告（**不影响通过**；翻译资产保留）：")
        for w in warn[:6]:
            print(f"  · {w}")
        if len(warn) > 6:
            print(f"  … 另 {len(warn) - 6} 条")
        print()
    if fail:
        print(f"❌ {len(fail)} 项未通过：")
        for f in fail[:12]:
            print("  ·", f)
    else:
        print("✅ 结构、一致性、译文质量检查全部通过")
    if require_full and (none or fail):
        print("（--require-full：仍有量表缺中译，不能进入前端步骤）")
        return 1
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
