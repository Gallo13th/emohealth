#!/usr/bin/env python3
"""把两册（L1 与 L2-Somatic）的授权原文补进归档记录。

为什么单独处理：这两册的授权声明**不在 PDF 页脚**，而在正文的
「Rights granted / Rightsholder」段里，所以共享的页脚提取器没抓到。
授权原文必须如实入档——它本身就是证据（`PLAN.md` R5：原始证据可溯源），不能靠推断。

顺带记录一处**授权限制**：Level 1 的授权写明
「This measure may not be modified absent written permission from APA.」
——即**不得修改后分发**。按 `PLAN.md` R2：我们**不动原文**，而是把
「英文原文 + 中译 + 完整本地化讲解」**并列**呈现（补充性独立内容，不是对原文的修改），
因此该条款**不构成**提供中译的障碍。
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
from pdftext import PdfDoc, layout_lines  # noqa: E402

FIXES = {
    "DSM5TR-L1": {
        "grep": r"Rights granted:(.{0,900}?RequestForm/)",
        "restrictions": ["不得修改（may not be modified absent written permission from APA）"],
        "translation_allowed": None,
    },
    # 这三册的授权声明也在正文的「Rights granted」段（不在页脚），
    # 且措辞各不相同（Mania 用 "This measure"、Substance 用 "This Instrument"、
    # Repetitive 被版式打散），所以逐册给正则。
    "DSM5TR-L2-Mania": {
        "grep": r"(This measure\s*can be reproduced without permission.{0,160}?patients\.)",
        "restrictions": [],
        "translation_allowed": None,
    },
    "DSM5TR-L2-Repetitive": {
        "grep": r"(material can be reproduced without permissio.{0,160}?patients\.)",
        "restrictions": [],
        "translation_allowed": None,
    },
    "DSM5TR-L2-Substance": {
        "grep": r"(This Instrument may be reproduced without permission.{0,160}?patients\.)",
        "restrictions": [],
        "translation_allowed": None,
        "extra_holder": "L2-Substance 改编自 NIDA-Modified ASSIST（Courtesy of NIDA）",
    },
    "DSM5TR-L2-Somatic": {
        # 这一册的正文被版式打散（"PHQThis -measurecan be reproduced…"），
        # 所以只匹配那句许可本身，不做长距离抓取。
        "grep": r"(This\s*-?\s*measure\s*can\s*be\s*reproduced\s*without\s*permission"
                r".{0,200}?patients\.)",
        "restrictions": [],
        "translation_allowed": True,
        # 该册改编自公有领域的 PHQ-15（归档内 PHQ15.osd 授权字段=Public Domain）
        "extra_holder": "L2-Somatic 改编自公有领域的 PHQ-15（Pfizer 明确免除版权）",
    },
}


def joined(code: str) -> str:
    pdf = os.path.join(ROOT, "archive", "scales", code, "manual.pdf")
    doc = PdfDoc.load(pdf)
    parts = []
    for runs in doc.text_runs():
        parts.extend(r["text"] for r in layout_lines(runs))
    return re.sub(r"\s+", " ", " ".join(parts))


def main() -> int:
    problems = 0
    for code, cfg in FIXES.items():
        text = joined(code)
        m = re.search(cfg["grep"], text, re.S | re.I)
        if not m:
            print(f"  ✗ {code}: 没找到授权段")
            problems += 1
            continue
        lic = re.sub(r"\s+", " ", m.group(1)).strip()
        rec_path = os.path.join(ROOT, "archive", "scales", code, "source.json")
        with open(rec_path, encoding="utf-8") as fh:
            rec = json.load(fh)
        rec["license"]["text"] = lic
        rec["license"]["redistribution"] = True
        rec["license"]["evidence"] = (
            f"PDF 正文『Rights granted / Rightsholder』段"
            f"（archive/scales/{code}/manual.pdf）；页脚无授权声明")
        rec["license"]["restrictions"] = cfg["restrictions"]
        rec["license"]["translation_allowed"] = cfg["translation_allowed"]
        rec["license"]["holder"] = ("American Psychiatric Association"
                                    + ("；" + cfg["extra_holder"]
                                       if cfg.get("extra_holder") else ""))
        with open(rec_path, "w", encoding="utf-8") as fh:
            json.dump(rec, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
        print(f"  ✓ {code}: 授权已补（{len(lic)} 字符）")
        print(f"      限制：{cfg['restrictions'] or '无'}")
        print(f"      原文：{lic[:200]}")
        print()

    print("✗ 有问题" if problems else "✅ 完成")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
