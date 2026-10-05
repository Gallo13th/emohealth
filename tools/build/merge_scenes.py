#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把作者文件 `content/scenes/*.json` 合并成 `data/item-scenes.json`（每题一句情景展示）。

为什么要有这一层
================
情景句是**人写的文案**（T-D/E/F 三个作者任务产出），而 `data/` 是**已核对的产物**。
两者之间必须有一道机器校验的闸门，否则「写漏了几十题」这类错误会静默通过——
界面只是那几题没有情景块，没人会注意到。所以：

    作者写 content/scenes/<scale>.json  →  本脚本全量校验 + 合并  →  data/item-scenes.json
                                                                    ↓
                                            tools/build/build_item_structured.py
                                                                    ↓
                                                每题写 scenario_zh / notes_zh

冻结的契约（`task-27`，**不要改字段名/层级**）
============================================
作者文件：

    {
      "schema": "scenes/1.0",
      "scale": "pid-5",
      "items": {
        "pid5_040": {"scene": "……情景句……", "notes": ["可选：真正的作答提醒"]}
      }
    }

* `scale` ∈ `ipip-neo` / `pid-5` / `dsm5tr`；文件名必须是 `<scale>.json`。
  `dsm5tr` **一个文件覆盖 L1 + L2 八个域共 9 册**。
* key = `data/items-structured/<code>.json` 里的 `items[].id`
  （`ipip_neo_001`…、`pid5_001`…、`l1_01`…、`dsm5trl2anger_01`…）。
* `notes` 缺省 = 该题**不显示任何提醒**（这是常态，不是错误）；每题最多 1 条。

产物：

    {"schema": "item-scenes/1.0", "generated_by": "tools/build/merge_scenes.py",
     "counts": {"items": 606}, "items": {"pid5_040": {"scene": "…", "notes": []}}}

硬校验（任一不过 → 退出码 1，**不放宽**）
========================================
1. schema / scale / 文件名三者一致；key 必须属于**该 scale 名下**的 id（不串册）；
2. id 不跨文件重复；
3. `scene` 非空；`notes` 是字符串数组、每题 ≤1 条；
4. **完整性**：合并后的 id 集合必须**恰好等于** `data/items-structured/` 里
   11 个量表的 id 全集——缺一个就报错并按册列出，多一个也报错。

幂等
====
`sort_keys=True` + UTF-8 + 结尾换行 + 二进制写出（只用 LF）→ 同一份作者文件
连跑两次**逐字节一致**。这也让 `--check` 可以直接做字节比对。

用法
====
    python tools/build/merge_scenes.py                       # 生成 data/item-scenes.json
    python tools/build/merge_scenes.py --check               # 只比对，不写盘
    python tools/build/merge_scenes.py --scenes-dir .tmp/scenes --out .tmp/item-scenes.json
        ↑ 验证机制用（作者文件还没齐时，用 .tmp/ 下的占位文件试跑，别污染 data/）
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402

ROOT = find_root()
ITEMS_DIR = os.path.join(ROOT, "data", "items-structured")
DEFAULT_SCENES_DIR = os.path.join(ROOT, "content", "scenes")
DEFAULT_OUT = os.path.join(ROOT, "data", "item-scenes.json")

AUTHOR_SCHEMA = "scenes/1.0"
OUT_SCHEMA = "item-scenes/1.0"
GENERATED_BY = "tools/build/merge_scenes.py"
MAX_NOTES_PER_ITEM = 1

#: scale → 它名下的 items-structured 文件（不含 .json）。dsm5tr 一个文件覆盖 9 册。
SCALE_FILES: dict[str, tuple[str, ...]] = {
    "ipip-neo": ("ipip-neo",),
    "pid-5": ("pid-5",),
    "dsm5tr": ("dsm5tr-l1",) + tuple(
        f"dsm5tr-l2-{x}" for x in ("anger", "anxiety", "depression", "mania",
                                   "repetitive", "sleep", "somatic", "substance")),
}

#: 全部 11 个 items-structured 文件 → 它们所属的 scale
CODE_SCALE = {code: scale for scale, codes in SCALE_FILES.items() for code in codes}


def load(p: str):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def structured_ids() -> dict[str, list[str]]:
    """`{code: [item id, …]}`，直接读 data/items-structured/（id 的**唯一权威**）。"""
    out: dict[str, list[str]] = {}
    for code in sorted(CODE_SCALE):
        p = os.path.join(ITEMS_DIR, f"{code}.json")
        if not os.path.exists(p):
            raise FileNotFoundError(f"缺 data/items-structured/{code}.json（先跑 build_item_structured.py）")
        out[code] = [it["id"] for it in load(p)["items"]]
    return out


def scale_ids(ids_by_code: dict[str, list[str]]) -> dict[str, set[str]]:
    """`{scale: {id, …}}`。"""
    out: dict[str, set[str]] = {s: set() for s in SCALE_FILES}
    for code, ids in ids_by_code.items():
        out[CODE_SCALE[code]] |= set(ids)
    return out


def read_authors(scenes_dir: str, want: dict[str, set[str]],
                 problems: list[str]) -> dict[str, dict]:
    """读 + 校验作者文件，返回 `{id: {"scene":…, "notes":[…]}}`。"""
    if not os.path.isdir(scenes_dir):
        problems.append(f"没有作者目录 {os.path.relpath(scenes_dir, ROOT)}/——"
                        f"情景句还没人写（T-D/E/F 任务产出它）")
        return {}
    names = sorted(f for f in os.listdir(scenes_dir) if f.endswith(".json"))
    if not names:
        problems.append(f"{os.path.relpath(scenes_dir, ROOT)}/ 下没有 *.json 作者文件")
        return {}

    merged: dict[str, dict] = {}
    owner: dict[str, str] = {}                       # id → 来自哪个文件（查重复用）
    for fn in names:
        path = os.path.join(scenes_dir, fn)
        stem = fn[:-5]
        doc = load(path)
        where = f"{os.path.relpath(path, ROOT)}"
        if doc.get("schema") != AUTHOR_SCHEMA:
            problems.append(f"{where}: schema 必须是 {AUTHOR_SCHEMA!r}，实际 {doc.get('schema')!r}")
            continue
        scale = doc.get("scale")
        if scale not in SCALE_FILES:
            problems.append(f"{where}: scale 必须是 {'/'.join(SCALE_FILES)} 之一，实际 {scale!r}")
            continue
        if stem != scale:
            problems.append(f"{where}: 文件名必须是 <scale>.json（scale={scale!r} → {scale}.json）")
            continue
        items = doc.get("items")
        if not isinstance(items, dict) or not items:
            problems.append(f"{where}: items 必须是非空对象")
            continue

        allowed = want[scale]
        for iid, entry in items.items():
            if iid in owner:
                problems.append(f"{where}: id {iid!r} 已出现在 {owner[iid]}（跨文件重复）")
                continue
            if iid not in allowed:
                problems.append(f"{where}: id {iid!r} 不属于 scale {scale!r}"
                                f"（该 scale 有 {len(allowed)} 个合法 id）")
                continue
            if not isinstance(entry, dict):
                problems.append(f"{where}: {iid} 的值必须是对象")
                continue
            scene = entry.get("scene")
            if not isinstance(scene, str) or not scene.strip():
                problems.append(f"{where}: {iid} 缺非空 scene")
                continue
            notes = entry.get("notes", [])
            if notes is None:
                notes = []
            if not isinstance(notes, list) or any(
                    not isinstance(t, str) or not t.strip() for t in notes):
                problems.append(f"{where}: {iid} 的 notes 必须是字符串数组")
                continue
            if len(notes) > MAX_NOTES_PER_ITEM:
                problems.append(f"{where}: {iid} 有 {len(notes)} 条 notes"
                                f"（每题最多 {MAX_NOTES_PER_ITEM} 条：提醒是稀缺品）")
                continue
            owner[iid] = os.path.relpath(path, ROOT)
            merged[iid] = {"scene": scene.strip(),
                           "notes": [t.strip() for t in notes]}
    return merged


def completeness(merged: dict[str, dict], want: dict[str, set[str]],
                 problems: list[str]) -> None:
    """完整性硬校验：合并后的 id 集合必须**恰好**等于 11 个量表的 id 全集。"""
    all_ids: set[str] = set()
    for s in SCALE_FILES:
        all_ids |= want[s]
    got = set(merged)
    missing = all_ids - got
    extra = got - all_ids
    if missing:
        id_scale = {iid: s for s in SCALE_FILES for iid in want[s]}
        per = []
        for scale in SCALE_FILES:
            n = len(want[scale] - got)
            if n:
                per.append(f"{scale} 缺 {n}")
        problems.append(f"完整性不通过：缺 {len(missing)} 个 id（{'、'.join(per)}）")
        for iid in sorted(missing)[:15]:
            problems.append(f"  缺 id：{iid}（属 {id_scale.get(iid, '?')}）")
        if len(missing) > 15:
            problems.append(f"  …还有 {len(missing) - 15} 个")
    if extra:
        problems.append(f"完整性不通过：多出 {len(extra)} 个不在任何量表里的 id")
        for iid in sorted(extra)[:10]:
            problems.append(f"  多出：{iid}")


def build(scenes_dir: str) -> tuple[dict | None, list[str], dict[str, list[str]]]:
    problems: list[str] = []
    try:
        ids_by_code = structured_ids()
    except FileNotFoundError as exc:
        return None, [str(exc)], {}
    want = scale_ids(ids_by_code)
    merged = read_authors(scenes_dir, want, problems)
    completeness(merged, want, problems)
    if problems:
        return None, problems, ids_by_code
    payload = {
        "schema": OUT_SCHEMA,
        "generated_by": GENERATED_BY,
        "counts": {"items": len(merged)},
        "items": merged,
    }
    return payload, [], ids_by_code


def render(payload: dict) -> bytes:
    """确定性序列化：sort_keys + UTF-8 + 结尾换行（字节可复现）。"""
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=1)
            + "\n").encode("utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="合并 content/scenes/*.json → data/item-scenes.json")
    ap.add_argument("--check", action="store_true", help="只比对，不写盘")
    ap.add_argument("--scenes-dir", default=DEFAULT_SCENES_DIR,
                    help="作者文件目录（默认 content/scenes；验证机制时可指向 .tmp/…）")
    ap.add_argument("--out", default=DEFAULT_OUT,
                    help="产物路径（默认 data/item-scenes.json；验证机制时可指向 .tmp/…）")
    args = ap.parse_args()

    test_mode = (os.path.abspath(args.scenes_dir) != os.path.abspath(DEFAULT_SCENES_DIR)
                 or os.path.abspath(args.out) != os.path.abspath(DEFAULT_OUT))
    print(f"合并情景展示（作者目录：{os.path.relpath(args.scenes_dir, ROOT)}"
          f" → 产物：{os.path.relpath(args.out, ROOT)}）")
    if test_mode:
        print("⚠ 测试模式：路径不是生产默认值，产物不落 data/（仅用于验证机制）")
    print()

    payload, problems, ids_by_code = build(args.scenes_dir)
    if problems:
        print(f"❌ {len(problems)} 处问题：")
        for x in problems[:40]:
            print("  -", x)
        if len(problems) > 40:
            print(f"  …还有 {len(problems) - 40} 处")
        return 1

    assert payload is not None
    total = payload["counts"]["items"]
    with_notes = sum(1 for v in payload["items"].values() if v["notes"])
    print(f"id 全集：{total} 题（11 套量表）")
    for scale in SCALE_FILES:
        n = sum(len(v) for c, v in ids_by_code.items() if CODE_SCALE[c] == scale)
        print(f"  {scale:10} {n:4} 题")
    print(f"有提醒的题：{with_notes}（{with_notes / total * 100:.1f}%）")
    print()

    want_bytes = render(payload)
    if args.check:
        if not os.path.exists(args.out):
            print(f"❌ 缺 {os.path.relpath(args.out, ROOT)} —— 先跑 merge_scenes.py")
            return 1
        cur = open(args.out, "rb").read()
        if cur == want_bytes:
            print(f"✅ {os.path.relpath(args.out, ROOT)} 与作者文件一致"
                  f"（{len(want_bytes)} B，逐字节）")
            return 0
        print(f"❌ {os.path.relpath(args.out, ROOT)} 与作者文件不一致"
              f"（磁盘 {len(cur)} B / 应为 {len(want_bytes)} B）——重跑 merge_scenes.py")
        return 1

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "wb") as fh:                       # 二进制：保证 LF、字节可复现
        fh.write(want_bytes)
    print(f"✅ 已写出 {os.path.relpath(args.out, ROOT)}（{len(want_bytes)} B）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
