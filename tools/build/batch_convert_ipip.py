#!/usr/bin/env python3
"""批量把「干净可转」的 IPIP 家族量表转成量表包。

依据 ``research/scales/ipip-conversion-report.json``（由
``tools/survey/survey_ipip_conversion.py`` 生成）：只转**没有风险**的那些——
即题项正文齐全、且每个维度的计分方向都明确（无 list 形态未补齐的维度）。

跳过项与原因会在输出里逐条列出，不静默跳过。
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()

SKIP_CODE = re.compile(
    r"^(MISS\d|PX\d|ipip_master|DEMO|5DCR|AHLS)|"
    r"Sickle|Asthma|Epilepsy|Hemophilia|Scoliosis|Respiratory|Hearing|"
    r"Kidney|Visual|Patient Satisfaction|Cannabis|Tobacco", re.I)
# 已单独处理（有各自的提取器与测试）
ALREADY = {
    "IPIP-NEO": "已有 data/ipip-neo-300.json（人工核对的旧 schema 产物）",
    "IPIP-CATPD": "已由 tools/build_scales.py + catpd-reverse-keys.json 处理",
    "IPIP-HEXACO": "已由 tools/build/build_hexaco_direction_evidence.py 补齐方向",
}
MIN_ITEMS = int(os.environ.get("MIN_ITEMS", "4"))


def main() -> int:
    rep_path = os.path.join(ROOT, "research", "scales", "ipip-conversion-report.json")
    with open(rep_path, encoding="utf-8") as fh:
        rep = json.load(fh)

    targets, skipped = [], []
    for c in rep["clean"]:
        code = c["code"]
        if code in ALREADY:
            skipped.append((code, ALREADY[code]))
        elif SKIP_CODE.search(code) or c["items"] < MIN_ITEMS:
            continue
        else:
            targets.append(code)

    print(f"待转换 {len(targets)} 个量表（题量下限 {MIN_ITEMS}）")
    for c, why in skipped:
        print(f"  跳过 {c}：{why}")
    print()

    # 分批调用，避免命令行过长；每批 40 个
    rc = 0
    for i in range(0, len(targets), 40):
        batch = targets[i:i + 40]
        cmd = ["python", os.path.join(ROOT, "tools", "build_scales.py")]
        for t in batch:
            cmd += ["--only", t]
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", cwd=ROOT)
        out = r.stdout + r.stderr
        # 只报每套的一行摘要与失败行
        for ln in out.splitlines():
            if re.match(r"\s*[✓✗]", ln) or "通过" in ln or "失败" in ln:
                print(ln)
        rc = rc or r.returncode
    return rc


if __name__ == "__main__":
    sys.exit(main())
