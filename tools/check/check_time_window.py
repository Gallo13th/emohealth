#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""时间窗一致性守卫：text-db 的 note 若写了「回忆时间窗」，必须与该题所属册的权威值一致。

为什么需要它
============
`data/text-db/text-db.json` 是**数据资产**（溯源用），它的 `note` 里常常顺手写一句
「问过去 7 天……」。这类句子一旦写错，就把错误的时间窗固化成「有出处的记录」——
而 text-db 是下游（情景/界面文案）的参考来源之一，错的时间窗会顺着传染。
实测已抓到两处真实错误（`l1_08` 写「过去7天」、`dsm5trl2substance_06` 写「过去12个月」，
两处实为**过去两周**），都已修并留痕（entry 上的 `note_fix`）。本脚本防复发。

权威值从哪来
============
`data/items-structured/*.json` 的 `instrument_guide.time_frame_zh`——那是生成物，
**以它为准**，不在本脚本里另立一套口径。

判定口径
========
* 只认**回忆窗表述**：`过去/近/最近 + 时间窗`（如「过去 7 天」「过去两周内」「过去12个月」）。
  裸时间词（「一时」「短时」「日均」「平时」）不是回忆窗，不判。
* 条目所属册由 entry 的 `instruments` 映射到权威表：
  - 映射不到权威值 → **未判定**（可能是尚未纳入 items-structured 的量表）；
  - 一个条目跨多个册且权威时间窗不同 → **未判定**（无法用单一值判）；
  - 权威值本身是「未指定/平时一贯」→ 若 note 写了回忆窗，**未判定**（不猜）。
* 命中多个回忆窗时逐个比对，任一不一致即违例。

用法
====
    python tools/check/check_time_window.py                 # 检查 data/text-db/text-db.json
    python tools/check/check_time_window.py --db <路径>      # 指定文本库（回归/自测用）
退出码：无不一致 0；有不一致 1。「未判定」不改变退出码，但会列出。
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root, force_utf8_io  # noqa: E402

ROOT = find_root()
ITEMS_DIR = os.path.join(ROOT, "data", "items-structured")
DEFAULT_DB = os.path.join(ROOT, "data", "text-db", "text-db.json")

#: 回忆窗表述：只认「过去/近/最近 + 时间窗」。裸时间词不算（见模块注释）。
RECALL_RE = re.compile(
    r"(?:过去|近|最近|在过去的?)\s*"
    r"(两周内?|2\s*周|14\s*天|十四天|7\s*天内?|七天|一周内?|1\s*周|"
    r"一个月|1\s*个月|30\s*天|三个月|3\s*个月|半年|6\s*个月|十二个月|12\s*个月|一年内?)"
)

#: 模糊窗：提了「近期/最近」却不给天数。**不是错误**（不冲突），但也不放过——
#: 计入「未判定」并列出来，免得以后有人用一个模糊词绕开这条守卫。
VAGUE_RE = re.compile(r"(近期|近来|最近|近些天|前段时间|这些天)")

#: 时间窗短语 → 规范类别
KIND_OF_TOKEN = (
    (r"两周|2\s*周|14\s*天|十四天", "2w"),
    (r"7\s*天|七天|一周|1\s*周", "7d"),
    (r"一个月|1\s*个月|30\s*天", "1m"),
    (r"三个月|3\s*个月|半年|6\s*个月|十二个月|12\s*个月|一年", "long"),
)

KIND_LABEL = {
    "2w": "过去两周",
    "7d": "过去 7 天",
    "1m": "过去一个月",
    "long": "长期窗口（3 个月 / 半年 / 12 个月 / 一年）",
    "unspecified": "未指定回忆窗（平时一贯 / 通常情况）",
    "unknown": "无法识别",
}


def token_kind(token: str) -> str:
    # 「过去两周内」「过去 7 天内」的尾缀「内」不影响时间窗本身
    t = token.strip()
    if t.endswith("内"):
        t = t[:-1]
    for pat, kind in KIND_OF_TOKEN:
        if re.fullmatch(pat, t):
            return kind
    return "unknown"


def window_kind(time_frame_zh: str | None) -> str:
    """把 instrument_guide.time_frame_zh 归到规范类别。"""
    tf = (time_frame_zh or "").strip()
    if not tf:
        return "unknown"
    if "两周" in tf or "14 天" in tf or re.search(r"TWO\s*\(2\)\s*WEEKS", tf, re.I):
        return "2w"
    if "7 天" in tf or re.search(r"SEVEN\s*\(7\)|7\s*days", tf, re.I):
        return "7d"
    if "平时" in tf or "未指定" in tf or "通常情况" in tf:
        return "unspecified"
    return "unknown"


def load_authority() -> dict[str, dict]:
    """`{instrument: {file, time_frame_zh, kind}}`，来自 items-structured 生成物。"""
    auth: dict[str, dict] = {}
    for p in sorted(glob.glob(os.path.join(ITEMS_DIR, "*.json"))):
        if os.path.basename(p) == "index.json":
            continue
        d = json.load(open(p, encoding="utf-8"))
        tf = (d.get("instrument_guide") or {}).get("time_frame_zh")
        auth[d["instrument"]] = {
            "file": os.path.relpath(p, ROOT).replace("\\", "/"),
            "time_frame_zh": tf,
            "kind": window_kind(tf),
        }
    return auth


def check(db_path: str) -> tuple[list[str], list[str], dict]:
    auth = load_authority()
    db = json.load(open(db_path, encoding="utf-8"))
    entries = db.get("entries") or {}

    violations: list[str] = []
    undetermined: list[str] = []
    stats = {"entries": len(entries), "with_note": 0, "with_recall": 0,
             "with_vague": 0, "ok": 0, "auth": len(auth)}

    for key, e in sorted(entries.items()):
        note = (e.get("note") or "").strip()
        if not note:
            continue
        stats["with_note"] += 1
        tokens = [m.group(1) for m in RECALL_RE.finditer(note)]
        if not tokens:
            vague = VAGUE_RE.search(note)
            if vague:
                stats["with_vague"] += 1
                insts = e.get("instruments") or []
                where = f"{'+'.join(insts) or '(无 instruments)'} :: {key[:52]!r}"
                undetermined.append(
                    f"{where}  模糊窗「{vague.group(0)}」：没给具体天数，与权威值不冲突，"
                    f"不判错也不放过 ｜ note: {note[:70]}")
            continue
        stats["with_recall"] += 1
        insts = e.get("instruments") or []
        mapped = [auth[i] for i in insts if i in auth]
        where = f"{'+'.join(insts) or '(无 instruments)'} :: {key[:52]!r}"

        if not mapped:
            undetermined.append(
                f"{where}  note 写了「{tokens[0]}」，但所属册不在 items-structured 里，无权威值可判"
                f" ｜ note: {note[:70]}")
            continue
        kinds = {m["kind"] for m in mapped}
        if len(kinds) > 1:
            desc = "、".join(f"{i}: {auth[i]['time_frame_zh']}" for i in insts if i in auth)
            undetermined.append(
                f"{where}  条目跨多个册且权威时间窗不同（{desc}）"
                f" ｜ note: {note[:70]}")
            continue
        akind = mapped[0]["kind"]
        atf = mapped[0]["time_frame_zh"]
        if akind in ("unspecified", "unknown"):
            undetermined.append(
                f"{where}  该册权威时间窗={atf!r}（{KIND_LABEL[akind]}），"
                f"note 却写了「{tokens[0]}」→ 无法判定 ｜ note: {note[:70]}")
            continue

        bad = False
        for t in tokens:
            if token_kind(t) != akind:
                bad = True
                violations.append(
                    f"{where}  note 写「{t}」（{KIND_LABEL[token_kind(t)]}），"
                    f"但该册权威是「{atf}」（{KIND_LABEL[akind]}）"
                    f"——依据 {mapped[0]['file']}.instrument_guide.time_frame_zh"
                    f" ｜ note: {note[:90]}")
        if not bad:
            stats["ok"] += 1

    return violations, undetermined, stats


def main() -> int:
    # UTF-8 兜底：唯一实现在 tools/_root.py。Windows 默认控制台是 GBK，下面的 ✅/❌
    # 会让 print 抛 UnicodeEncodeError —— 崩溃点在**输出结果那一行**，退出码 1 与
    # 「真的发现时间窗不一致」不可区分，于是完好的守卫会永远假装变红。
    force_utf8_io()
    ap = argparse.ArgumentParser(description="text-db note 的时间窗 ↔ 各册权威时间窗 一致性守卫")
    ap.add_argument("--db", default=DEFAULT_DB, help="文本库路径（默认 data/text-db/text-db.json）")
    args = ap.parse_args()

    print(f"时间窗一致性守卫（项目根：{ROOT}）")
    print(f"文本库：{os.path.relpath(args.db, ROOT)}")
    print("权威值：data/items-structured/*.json → instrument_guide.time_frame_zh（以生成物为准）")
    auth = load_authority()
    for k, v in sorted(auth.items()):
        print(f"     · {k:22} {str(v['time_frame_zh'])[:44]:46} → {KIND_LABEL[v['kind']]}")
    print()

    violations, undetermined, stats = check(args.db)
    print(f"扫描：条目 {stats['entries']}，其中有 note {stats['with_note']}；"
          f"note 里出现「过去/近+时间窗」表述的 {stats['with_recall']} 条"
          f"（一致 {stats['ok']}，违例 {len(violations)}）；"
          f"模糊窗（近期/最近，未给天数）{stats['with_vague']} 条")
    if undetermined:
        print(f"\n未判定 {len(undetermined)} 处（**未判定 ≠ 通过**）：")
        for u in undetermined:
            print(f"   · {u}")
    if violations:
        print(f"\n❌ 时间窗不一致 {len(violations)} 处：")
        for v in violations:
            print(f"   · {v}")
        print("\n❌ 不通过：note 里的回忆窗必须与该册权威时间窗一致；"
              "改 note 时要在 entry 上留 `note_fix`（原文 → 更正 → 依据）。")
        return 1

    print(f"未判定 {len(undetermined)} 处")
    print("✅ 全部一致：note 里出现的回忆窗都与所属册的权威时间窗相同。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
