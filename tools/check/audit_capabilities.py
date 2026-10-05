#!/usr/bin/env python3
"""能力对账：以「大五人格（IPIP-NEO-300）」为基准，逐项核对每套量表**实际**有哪些能力。

为什么需要这个
==============
用户指出：所有题目应与大五人格**等价地位**，每套量表该有的功能都要对齐。
但「对齐」不能靠感觉，得逐项查。本脚本以 IPIP-NEO-300 的 UI 能力为基准：

  基准（大五人格在界面上有的）
    ① 题目中译          ② 逐题注释        ③ 分页作答
    ④ 天赋树作答        ⑤ 结果与分数      ⑥ 常模/百分位
    ⑦ 单量表导出        ⑧ 情景模式        ⑨ 分级模式
    ⑩ 逐题脚手架（承重词/常见误读/边界）

输出一张**如实**的表：哪些已对齐、哪些没有、缺的原因是什么。
缺的必须列出，不用「看起来一样」糊过去。
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
THRESHOLD = 60


def norm(t: str) -> str:
    s = (t or "").replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
    s = s.replace("-", " ").replace("\u2013", " ").replace("\u2014", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return re.sub(r"[.\s]+$", "", s).lower()


def main() -> int:
    db = json.load(open(os.path.join(ROOT, "data", "text-db", "text-db.json"),
                        encoding="utf-8"))
    entries = db["entries"]
    tree_codes = set()
    ti = os.path.join(ROOT, "ui", "tree-layouts", "index.json")
    if os.path.exists(ti):
        tree_codes = {s["code"] for s in
                      json.load(open(ti, encoding="utf-8"))["scales"]}

    files = [p for p in sorted(glob.glob(
        os.path.join(ROOT, "data", "instruments", "*.json")))
        if os.path.basename(p) != "catalog.json"]

    rows = []
    for p in files:
        d = json.load(open(p, encoding="utf-8"))
        code = d["instrument"]
        n = len(d["items"])
        zh = sum(1 for it in d["items"]
                 if (entries.get(norm(it["text"])) or {}).get("zh"))
        note = sum(1 for it in d["items"]
                   if (entries.get(norm(it["text"])) or {}).get("note")
                   or (entries.get(norm(it["text"])) or {}).get("scaffold"))
        # ⚠️ 常模有两种结构，**都要算**：
        #    · IPIP-NEO：facets/domains 里带 1..99 百分位表
        #    · PID-5：条件常模（scales 里逐 raw 给百分位，按性别×年龄分层）
        #    只认前者会把 PID-5 误报成「无常模」——我第一版就是这样。
        nrm = d.get("norms") or {}
        has_norms = bool(nrm.get("facets") or nrm.get("domains")
                         or nrm.get("scales"))
        rows.append({
            "code": code, "items": n,
            "zh": zh / n if n else 0,
            "note": note / n if n else 0,
            "tree": code in tree_codes,
            "norms": has_norms,
            "scoring": bool(d.get("scoring")),
            "paged": n > 0,
            "export": True,          # 导出是通用实现（按量表范围）
            "scene": code == "IPIP-NEO",
            "tier": code == "IPIP-NEO",
            "scaffold": code == "IPIP-NEO",
        })

    N = len(rows)
    print(f"量表 {N} 套。以 IPIP-NEO-300 为基准逐项对账：\n")
    checks = [
        ("① 中译覆盖 100%", lambda r: r["zh"] >= 0.999),
        ("② 逐题注释覆盖 100%", lambda r: r["note"] >= 0.999),
        ("③ 分页作答", lambda r: r["paged"]),
        ("⑤ 结果与计分", lambda r: r["scoring"]),
        ("⑦ 单量表导出", lambda r: r["export"]),
        ("⑥ 常模/百分位", lambda r: r["norms"]),
        ("④ 天赋树（> 60 题才需要）",
         lambda r: r["tree"] if r["items"] > THRESHOLD else True),
        ("⑧ 情景模式", lambda r: r["scene"]),
        ("⑨ 分级模式", lambda r: r["tier"]),
        ("⑩ 逐题脚手架", lambda r: r["scaffold"]),
    ]
    for name, fn in checks:
        ok = [r for r in rows if fn(r)]
        miss = [r["code"] for r in rows if not fn(r)]
        flag = "✅" if not miss else "⚠️"
        print(f"  {flag} {name:28} {len(ok):3}/{N}"
              + (f"   缺：{', '.join(miss[:6])}{' …' if len(miss) > 6 else ''}"
                 if miss else ""))
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
