#!/usr/bin/env python3
"""IPIP 家族试转 + 方向核查：找出「计分方向不可信」的维度。

背景：OpenScales 的 ``scoring.items`` 有两种形态——
  · dict（``{"ipip_x": 1, "ipip_y": -1}``）：方向明确
  · list（``["ipip_x", "ipip_y"]``）：**没有方向信息**
list 形态若没有官方反向键补齐，就一律按正向处理，那会让维度分**静默算反**。

IPIP 官方的计分键页（ipip.ori.org）给每个量表列出题号与反向标记，
但每个量表的 URL 不同、版式也不同。所以这份脚本先**把问题规模摸清**：
哪些量表有 list 形态的维度、各多少个，再决定逐个补还是只收 dict 完整的。
"""

from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, ROOT)

from build_scales import (  # noqa: E402
    CODES_FILE, EN_TRANSLATIONS, METHOD_MAP, OSD_DIR, VARIANT_SUFFIX,
    build_instrument, load_json,
)

# 优先收录的「完整量表」（排除 IPIP 语言主池与子量表）
SKIP = re.compile(r"^ipip_master", re.I)


def all_osd() -> list[str]:
    out = []
    for base, _dirs, files in os.walk(OSD_DIR):
        if re.search(r"translation", base, re.I):
            continue
        for fn in files:
            if fn.endswith(".osd") and not SKIP.match(fn):
                out.append(fn[:-4])
    return sorted(set(out))


def direction_report(code: str) -> dict:
    """看某量表的 scoring.items 形态分布（dict / list）。"""
    import glob
    hits = glob.glob(os.path.join(OSD_DIR, "**", code + ".osd"), recursive=True)
    if not hits:
        return {}
    with open(hits[0], encoding="utf-8") as fh:
        j = json.load(fh)
    sc = (j.get("definition") or {}).get("scoring") or {}
    dict_dims, list_dims = set(), set()
    for k, v in sc.items():
        base = VARIANT_SUFFIX.sub("", k)
        (dict_dims if isinstance(v.get("items"), dict) else list_dims).add(base)
    return {"code": code, "dict_dims": len(dict_dims), "list_dims": len(list_dims),
            "list_names": sorted(list_dims), "file": os.path.relpath(hits[0], ROOT)}


def main() -> int:
    code_pool = load_json(CODES_FILE).get("code_to_text") or {}
    en_pool = load_json(EN_TRANSLATIONS)
    codes = all_osd()
    print(f"归档里的量表（排除语言主池与 translations）共 {len(codes)} 个\n")

    ok, bad, risky = [], [], []
    for code in codes:
        try:
            inst, warn = build_instrument(code, code_pool=code_pool, en_pool=en_pool)
        except Exception as exc:                                # noqa: BLE001
            bad.append((code, str(exc)[:70]))
            continue
        errs = inst.validate(require_redistributable=True)
        if errs:
            bad.append((code, errs[0][:70]))
            continue
        missing = sum(1 for it in inst.items if it.text.startswith("[缺失正文"))
        rep = direction_report(code)
        if missing or (rep and rep["list_dims"]):
            risky.append((code, missing, rep["list_dims"] if rep else 0,
                          rep["list_names"][:3] if rep else []))
        else:
            ok.append((code, len(inst.items), len(inst.dimensions)))

    print(f"✓ 干净可转：{len(ok)} 个")
    print(f"⚠ 有风险（缺正文 或 方向不可信）：{len(risky)} 个")
    print(f"✗ 无法转换：{len(bad)} 个\n")

    print("=== 有风险的量表（前 30）===")
    print(f"{'代码':30} {'缺正文':>6} {'方向可疑维度':>12}  例")
    for c, m, n, names in sorted(risky, key=lambda x: (-x[2], -x[1]))[:30]:
        print(f"{c:30} {m:6} {n:12}  {','.join(names)[:44]}")

    print("\n=== 无法转换的（前 20）===")
    for c, e in bad[:20]:
        print(f"  {c:30} {e}")

    out = os.path.join(ROOT, "research", "scales", "ipip-conversion-report.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"total": len(codes),
                   "clean": [{"code": c, "items": i, "dims": d} for c, i, d in ok],
                   "risky": [{"code": c, "missing_text": m, "list_dims": n,
                              "examples": names} for c, m, n, names in risky],
                   "unconvertible": [{"code": c, "error": e} for c, e in bad]},
                  fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(f"\n已写出 {os.path.relpath(out, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
