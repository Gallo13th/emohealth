#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`content/scenes/ipip-neo.json` 自查（task-28 的验收脚本，可复跑）。

查什么
======
1. **id 完全对齐**：与 `data/items-structured/ipip-neo.json` 的 `items[].id` 逐字一致，
   300 个一个不少、不多余（顺序也照抄）。
2. `scene`：**20–60 个汉字**（只数 CJK 汉字，标点/数字/空格不算）。
3. **禁用词 0 命中**：量表/条目/本题/该题/维度/facet/DSM/临床/文献/原文/直译/排版/
   缺空格/漏空格/噪声/scaffold/模板、facet 代码（`E150`/`N1` 这类）、以及「测…」构念标签。
4. `scene` 与 `text_zh` **不相同**，且**不像是把题干换个说法**（汉字 bigram 相似度 < 0.60）。
5. 第二人称「你」必须出现（写作规则 8）；口语化。
6. `notes`：每题 **≤1 条**；不允许出现「常见误读」「中文语境读法风险」这类旧标题与箭头体 `→`。
7. `schema`/`scale` 字段与冻结契约一致。

用法
====
    python tools/check/ipip_scene_check.py            # 全量检查（缺文件/缺 id 会报错）
    python tools/check/ipip_scene_check.py --work P   # 查分批草稿（JSON: id -> {scene,notes}）
    python tools/check/ipip_scene_check.py --stats    # 附统计（notes 占比等）
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = str(find_root())

ITEMS = os.path.join(ROOT, "data", "items-structured", "ipip-neo.json")
SCENES = os.path.join(ROOT, "content", "scenes", "ipip-neo.json")

#: 禁用词（写作规则 5）。逐字面命中即失败。
BANNED = ["量表", "条目", "本题", "该题", "维度", "facet", "DSM", "临床", "文献",
          "原文", "直译", "排版", "缺空格", "漏空格", "噪声", "scaffold", "模板",
          "常见误读", "中文语境读法风险", "测"]
#: 旧样式的痕迹：箭头体
BANNED_RE = [re.compile(r"→"), re.compile(r"\b[A-Z]\d{1,3}\b"), re.compile(r"（[A-Z]\d")]


def hanzi(s: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", s or ""))


def bigrams(s: str) -> set:
    h = re.findall(r"[\u4e00-\u9fff]", s or "")
    return {h[i] + h[i + 1] for i in range(len(h) - 1)}


def similarity(a: str, b: str) -> float:
    """汉字 bigram 的 Jaccard：衡量「是不是把题干换个说法」。"""
    A, B = bigrams(a), bigrams(b)
    if not A or not B:
        return 0.0
    return len(A & B) / len(A | B)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=None, help="分批草稿 JSON（id -> {scene, notes}）")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--max-show", type=int, default=40)
    args = ap.parse_args()

    items = json.load(open(ITEMS, encoding="utf-8"))["items"]
    want_ids = [it["id"] for it in items]
    zh = {it["id"]: it["text_zh"] for it in items}

    if args.work:
        got = json.load(open(args.work, encoding="utf-8"))
        data = {"schema": "scenes/1.0", "scale": "ipip-neo", "items": got}
    else:
        if not os.path.exists(SCENES):
            print(f"❌ 缺文件：{os.path.relpath(SCENES, ROOT)}")
            return 1
        data = json.load(open(SCENES, encoding="utf-8"))

    bad: list[str] = []
    warn: list[str] = []
    n_notes = 0
    sims: list[tuple[float, str]] = []
    lens: list[int] = []

    if data.get("schema") != "scenes/1.0":
        bad.append(f"schema 应为 scenes/1.0，实为 {data.get('schema')!r}")
    if data.get("scale") != "ipip-neo":
        bad.append(f"scale 应为 ipip-neo，实为 {data.get('scale')!r}")
    extra_top = set(data.keys()) - {"schema", "scale", "items"}
    if extra_top:
        bad.append(f"顶层多出字段 {sorted(extra_top)}（契约只有 schema/scale/items）")

    got = data.get("items") or {}
    miss = [i for i in want_ids if i not in got]
    extra = [i for i in got if i not in set(want_ids)]
    if miss:
        bad.append(f"缺 {len(miss)} 个 id：{miss[:8]}{'…' if len(miss) > 8 else ''}")
    if extra:
        bad.append(f"多出 {len(extra)} 个 id：{extra[:8]}{'…' if len(extra) > 8 else ''}")

    for iid in want_ids:
        rec = got.get(iid)
        if not rec:
            continue
        scene = rec.get("scene") or ""
        notes = rec.get("notes") or []
        # 冻结契约：每条只能有 scene / notes 两个键，schema 顶层也只能有三个键
        extra_keys = set(rec.keys()) - {"scene", "notes"}
        if extra_keys:
            bad.append(f"{iid}: 多出字段 {sorted(extra_keys)}（契约只有 scene/notes）")
        n = hanzi(scene)
        lens.append(n)
        if not (20 <= n <= 60):
            bad.append(f"{iid}: scene 汉字数 {n}（要求 20–60）")
        for w in BANNED:
            if w in scene:
                bad.append(f"{iid}: scene 命中禁用词「{w}」")
        for rx in BANNED_RE:
            m = rx.search(scene)
            if m:
                bad.append(f"{iid}: scene 命中禁用样式 {m.group(0)!r}")
        if scene.strip() == (zh.get(iid) or "").strip():
            bad.append(f"{iid}: scene 与题干中译完全相同（等于重写题干）")
        sim = similarity(scene, zh.get(iid) or "")
        sims.append((sim, iid))
        if sim >= 0.60:
            bad.append(f"{iid}: scene 与题干过于相似（bigram 相似度 {sim:.2f}）")
        if "你" not in scene:
            bad.append(f"{iid}: scene 没有第二人称「你」")
        for pat in ("你觉得自己", "你认为自己是", "会觉得自己是个"):
            if pat in scene:
                warn.append(f"{iid}: 可能是「自我评价」句式「{pat}」（应写会发生什么）")
        if len(notes) > 1:
            bad.append(f"{iid}: notes 有 {len(notes)} 条（每题最多 1 条）")
        if notes:
            n_notes += 1
            for t in notes:
                tn = hanzi(t)
                if not (8 <= tn <= 70):
                    bad.append(f"{iid}: note 汉字数 {tn}（要求 8–70）")
                for w in ("常见误读", "中文语境读法风险", "→", "facet", "维度", "本题", "该题",
                          "量表", "条目", "DSM", "临床", "文献", "测"):
                    if w in t:
                        bad.append(f"{iid}: note 命中禁用样式「{w}」")
        if not isinstance(notes, list):
            bad.append(f"{iid}: notes 必须是数组")

    sims.sort(reverse=True)
    print("=" * 72)
    print(f"文件：{os.path.relpath(args.work or SCENES, ROOT)}")
    print(f"id 覆盖：{len(got)}/{len(want_ids)}"
          f"（缺 {len(miss)}、多 {len(extra)}）")
    if lens:
        print(f"scene 汉字数：最小 {min(lens)}、中位 {sorted(lens)[len(lens)//2]}、最大 {max(lens)}")
    print(f"notes：{n_notes}/{len(got)} 题（{100*n_notes/max(1,len(got)):.1f}%）")
    print(f"与题干最像的 5 条（bigram 相似度，阈值 0.60）：" +
          "，".join(f"{i}:{s:.2f}" for s, i in sims[:5]))
    print("=" * 72)
    if warn:
        print(f"⚠️ 软警告 {len(warn)} 条（不影响通过）：")
        for w in warn[:args.max_show]:
            print("   " + w)
    if bad:
        print(f"❌ 不合格 {len(bad)} 条：")
        for b in bad[:args.max_show]:
            print("   " + b)
        if len(bad) > args.max_show:
            print(f"   …其余 {len(bad) - args.max_show} 条略")
        return 1
    print("✅ 全部通过：id 全覆盖、20–60 汉字、禁用词 0 命中、与题干不雷同、notes ≤1 条")
    return 0


if __name__ == "__main__":
    sys.exit(main())
