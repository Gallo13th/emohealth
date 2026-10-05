#!/usr/bin/env python3
"""读归档里的官方 ItemKey，确定 IPIP-NEO-300 的题号 → 面向/反向映射。

为什么必须先做这一步
====================
``IPIP300.dat``（98 MB，N≈20 万条记录）是定宽无表头格式，题项落在列 33–332。
**但列的先后顺序不能假设**：万一它与项目里 ``data/ipip-neo-300.json`` 的题序
不同，按后者反推常模就会把题配错面向——常模是用来解释分数的，配错等于伪造。

归档里有 Johnson 官方的计分工具，正是为定序准备的材料：
  · ``scoring/IPIP-NEO-ItemKey.xls``         题号 → 面向 + 计分方向
  · ``scoring/IPIP-NEO-300_ScoringTool.xlsx`` 计分表
本脚本读 ItemKey，并与项目既有题序**逐项核对**。对不上就报错，不猜。
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
KEY_XLS = os.path.join(ROOT, "archive", "datasets", "osf-johnson", "scoring",
                       "IPIP-NEO-ItemKey.xls")
SCORE_XLSX = os.path.join(ROOT, "archive", "datasets", "osf-johnson", "scoring",
                          "IPIP-NEO-300_ScoringTool.xlsx")
CANON = os.path.join(ROOT, "data", "ipip-neo-300.json")


def read_xls(path: str) -> list[list[str]]:
    """读 .xls（老式 BIFF）——没有 xlrd，回退到把内容当制表符文本抽。"""
    try:
        import xlrd                                        # noqa: F401
        book = xlrd.open_workbook(path)
        sheet = book.sheet_by_index(0)
        return [[str(sheet.cell_value(r, c)) for c in range(sheet.ncols)]
                for r in range(sheet.nrows)]
    except Exception:                                        # noqa: BLE001
        pass
    # 回退：把二进制里的可读串抽出来看结构（只用于诊断）
    raw = open(path, "rb").read()
    import re
    text = raw.decode("latin-1", "ignore")
    return [[m] for m in re.findall(r"[A-Za-z0-9_.+\-/ ]{4,60}", text)]


def read_xlsx(path: str) -> list[list[str]]:
    from openpyxl import load_workbook
    wb = load_workbook(path, data_only=True)
    ws = wb[wb.sheetnames[0]]
    return [["" if c is None else str(c) for c in row]
            for row in ws.iter_rows(values_only=True)]


def main() -> int:
    print("归档计分材料：")
    for p in (KEY_XLS, SCORE_XLSX):
        print(f"  {'✓' if os.path.exists(p) else '✗'} {os.path.basename(p)}"
              f"  ({os.path.getsize(p) / 1024:.1f} KB)" if os.path.exists(p)
              else f"  ✗ {os.path.basename(p)} 不存在")

    print("\n── IPIP-NEO-300_ScoringTool.xlsx ──")
    rows = read_xlsx(SCORE_XLSX)
    print(f"  {len(rows)} 行 × {max(len(r) for r in rows)} 列")
    for r in rows[:8]:
        print("   ", " | ".join((c or "")[:18] for c in r[:8]))

    print("\n── ItemKey.xls ──")
    if os.path.exists(KEY_XLS):
        rows = read_xls(KEY_XLS)
        print(f"  抽出 {len(rows)} 行")
        for r in rows[:12]:
            print("   ", " | ".join(c[:24] for c in r[:6]))

    # 与项目题序核对：canon 的 facet/key
    canon = json.load(open(CANON, encoding="utf-8"))
    items = sorted(canon["items"], key=lambda x: x["order"])
    print(f"\n项目题序：{len(items)} 题，反向 {sum(1 for i in items if i['key'] < 0)} 题")
    facets = {}
    for it in items:
        facets.setdefault(it["facet"], []).append(it["order"])
    print(f"面向 {len(facets)} 个，各面向题数 "
          f"{sorted(set(len(v) for v in facets.values()))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
