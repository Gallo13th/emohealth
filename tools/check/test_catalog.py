#!/usr/bin/env python3
"""多量表目录的自检。

目录是界面的入口，出错的表现是「量表列表缺项 / 点进去加载不出来」，所以要把
结构性问题在这里拦住：

  · 目录条目数 = ``data/instruments/*.json`` 的实际套数（除目录自身）
  · 每个条目引用的 ``pack`` 文件存在
  · 每个条目都有**授权标签与证据**（本项目要求每个数字可追到出处）
  · 不允许收录授权未明或不可再分发的量表（D20 的界面侧防线）
  · 分组覆盖全部量表，且没有重复归组
  · ``ui/catalog.js`` 与 ``data/instruments/catalog.json`` 内容一致
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()

fail = 0


def ck(name: str, cond: bool, detail: str = "") -> None:
    global fail
    print(f"  {'✅' if cond else '❌'} {name}" + (f"  —— {detail}" if detail else ""))
    if not cond:
        fail += 1


def main() -> int:
    cat_path = os.path.join(ROOT, "data", "instruments", "catalog.json")
    with open(cat_path, encoding="utf-8") as fh:
        cat = json.load(fh)
    inst_files = [p for p in glob.glob(
        os.path.join(ROOT, "data", "instruments", "*.json"))
        if os.path.basename(p) != "catalog.json"]

    print(f"目录条目 {cat['count']}，实际量表包 {len(inst_files)} 套\n")
    ck("条目数与量表包数一致", cat["count"] == len(inst_files),
       f"{cat['count']} vs {len(inst_files)}")
    ck("声明的题项总数与逐条相加一致",
       cat["total_items"] == sum(e["items"] for e in cat["instruments"]),
       str(cat["total_items"]))

    missing_pack, no_label, bad_license, thin_evidence = [], [], [], []
    for e in cat["instruments"]:
        pack = os.path.join(ROOT, "data", "instruments",
                            os.path.basename(e["pack"]))
        if not os.path.exists(pack):
            missing_pack.append(e["code"])
            continue
        lic = e.get("license", {})
        # 目录里只要标签（体积考虑）；但**溯源链必须完整**——
        # 权利人/证据/授权原文都应在数据包里。这条断言正是守这一点：
        # 目录可以精简，信息不能丢。
        if not lic.get("label", "").strip():
            no_label.append(e["code"])
        if lic.get("kind") in ("unknown", None) or lic.get("redistribution") is not True:
            bad_license.append(e["code"])
        with open(pack, encoding="utf-8") as fh:
            full = json.load(fh)
        fl = full.get("license", {})
        if not (fl.get("evidence", "").strip() and fl.get("text", "").strip()
                and fl.get("holder", "").strip()):
            thin_evidence.append(e["code"])

    ck("每个条目的数据包都存在", not missing_pack, str(missing_pack[:5]))
    ck("每个条目都有授权标签", not no_label, str(no_label[:5]))
    ck("没有授权未明或不可再分发的量表（D20 界面侧）",
       not bad_license, str(bad_license[:5]))
    ck("数据包里保留了完整授权（权利人 + 证据 + 原文）",
       not thin_evidence, f"{len(thin_evidence)} 套不全：{thin_evidence[:5]}")

    # 分组覆盖
    grouped = [c for g in cat["groups"] for c in g["codes"]]
    codes = [e["code"] for e in cat["instruments"]]
    ck("分组覆盖全部量表", sorted(grouped) == sorted(codes),
       f"分组 {len(grouped)} 个 / 量表 {len(codes)} 个")
    ck("没有量表被重复归组", len(grouped) == len(set(grouped)))

    # ui/catalog.js 与 json 一致
    js = open(os.path.join(ROOT, "ui", "catalog.js"), encoding="utf-8").read()
    ck("ui/catalog.js 暴露 window.EMOHEALTH_CATALOG",
       "window.EMOHEALTH_CATALOG" in js)
    m = re.search(r"window\.EMOHEALTH_CATALOG\s*=\s*(\{.*\});\s*$", js, re.S)
    ck("ui/catalog.js 内容可解析", bool(m))
    if m:
        try:
            js_cat = json.loads(m.group(1))
            ck("ui/catalog.js 与 catalog.json 内容一致", js_cat == cat)
        except json.JSONDecodeError as exc:
            ck("ui/catalog.js 与 catalog.json 内容一致", False, str(exc))

    print()
    print("✅ 全部通过" if not fail else f"❌ {fail} 项未通过")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
