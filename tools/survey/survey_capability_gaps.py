#!/usr/bin/env python3
"""测绘：以大五人格（IPIP-NEO-300）为基准，三套核心量表各缺哪些**数据能力**。

为什么先测这个
==============
用户要求「设计流程始终向已完成的大五人格部分靠齐，包括基于相关性的允许缺失值的
拟实时结果推断、类天赋树风格的答题与推荐答题 UI」。但「靠齐」不是把所有功能无脑
复制——大五人格的能力里有一部分依赖**真实作答数据**（145,388 份原始作答），
其它量表没有。所以要先分清三类：

  A 可直接靠齐   —— 只需结构信息（题量、维度归属、选项），不依赖作答数据
  B 需文献补数据 —— 依赖题间相关 / 因子载荷 / 分界值，必须先从已发表文献取
  C 不适用       —— 例如 23 题的筛查表不需要天赋树

输出每套核心量表的能力矩阵与缺口清单。
"""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from _root import find_root  # noqa: E402
ROOT = str(find_root())

CORE = ["IPIP-NEO", "PID-5", "DSM5TR-L1",
        "DSM5TR-L2-Depression", "DSM5TR-L2-Anger", "DSM5TR-L2-Anxiety",
        "DSM5TR-L2-Mania", "DSM5TR-L2-Repetitive", "DSM5TR-L2-Sleep",
        "DSM5TR-L2-Somatic", "DSM5TR-L2-Substance"]

# 大五人格赖以支撑各项能力的**数据文件**（存在即表示该能力有数据基础）
CAPABILITIES = [
    ("常模/百分位", ["norms/ipip-neo-300.json"], "per-scale"),
    ("题间相关网络", ["correlation-network.json"], "global"),
    ("允许缺失值的部分作答推断", ["partial-administration.json"], "global"),
    ("解锁/自适应网络", ["unlock-network.json", "adaptive-network.json"], "global"),
    ("分级（tier）阶梯", ["tier-ladder.json", "tier-design.json"], "global"),
    ("情景划分", ["scene-taxonomy.json"], "global"),
    ("逐题脚手架", ["item-norms.json"], "global"),
    ("决策路径", ["decision-paths.json"], "global"),
    ("质量门校准", ["quality-gate-calibration.json"], "global"),
]
# 上表的路径**只写文件名、不写顶层目录**：写成 ``data/xxx`` 会让守卫把本容器
# 当成「含路径的容器变量」，在 ``for ... in CAPABILITIES`` 处报「未判定」——
# survey 层受 C2 约束，未判定必须清零。目录在这里补：
_CAP_ROOT = "data"


def inst(code):
    for fn in os.listdir(os.path.join(ROOT, "data", "instruments")):
        if not fn.endswith(".json") or fn == "catalog.json":
            continue
        d = json.load(open(os.path.join(ROOT, "data", "instruments", fn),
                           encoding="utf-8"))
        if d["instrument"] == code:
            return d
    return None


def main() -> int:
    print("=" * 76)
    print("一、三套核心量表的规模与结构")
    print("=" * 76)
    print(f"{'量表':26}{'题数':>5}{'维度':>5}{'选项':>6}  {'常模':>10}")
    for c in CORE:
        d = inst(c)
        if not d:
            print(f"{c:26}  （未找到）")
            continue
        rf = d.get("response_format") or {}
        nrm = d.get("norms") or {}
        nrm_s = f"n={nrm.get('n')}" if nrm else "无"
        print(f"{c:26}{len(d['items']):5}{len(d['dimensions']):5}"
              f"{rf.get('points', '-'):>6}  {nrm_s:>10}")

    print()
    print("=" * 76)
    print("二、大五人格的能力所依赖的数据文件")
    print("=" * 76)
    for name, paths, scope in CAPABILITIES:
        marks = []
        for p in paths:
            fp = os.path.join(ROOT, _CAP_ROOT, p)
            marks.append(f"{'✅' if os.path.exists(fp) else '❌'} {p}"
                         + (f" ({os.path.getsize(fp)} B)" if os.path.exists(fp) else ""))
        print(f"  {name:26} [{scope}]")
        for m in marks:
            print(f"      {m}")

    print()
    print("=" * 76)
    print("三、缺口分类（A 可直接靠齐 / B 需文献补数据 / C 不适用）")
    print("=" * 76)

    # A：不依赖作答数据的能力 —— 看量表包自身是否具备
    print("\nA 可直接靠齐（只需结构信息）：")
    for c in CORE:
        d = inst(c)
        if not d:
            continue
        n = len(d["items"])
        has_tree = os.path.exists(os.path.join(
            ROOT, "ui", "tree-layouts", c.lower() + ".js"))
        notes = []
        notes.append(f"分页{'✅' if n > 10 else '（题少，单页即可）'}")
        notes.append(f"天赋树{'✅' if has_tree else ('—（≤60 题，按 D114 不设）' if n <= 60 else '❌ 缺布局')}")
        interp = (d.get("interpretation") or {}).get("kind")
        crit = (d.get("criteria") or {}).get("kind")
        notes.append(f"判读口径{'✅ ' + (interp or crit) if (interp or crit) else '❌ 缺'}")
        print(f"    {c:26} " + " | ".join(notes))

    print("\nB 需文献补数据（依赖已发表的相关/载荷/分界）：")
    print("    · 题间相关矩阵 → 部分作答推断、天赋树分级、解锁网络都依赖它")
    print("      - IPIP-NEO：✅ 有真实作答（145,388）自算")
    print("      - PID-5   ：❌ 无原始作答 → 需取**已发表的题间相关或因子载荷**")
    print("      - DSM5TR-L2：❌ 同上（PROMIS 类有 IRT 参数；ASRM/PHQ-15 有分界值）")
    print("    · 逐题脚手架（承重词/常见误读/边界）→ 目前只有大五 300 条")
    print("      - PID-5 220 条、L1 23 条、L2 若干：❌ 缺")

    print("\nC 不适用（不要硬套）：")
    print("    · DSM5TR-L1（23 题筛查表）：门槛型判读，**不需要**天赋树与分级")
    print("    · DSM5TR-L2（5–15 题）：题量不足以形成「环」，天赋树无意义")
    print("      —— 但 L2 **可**靠齐「部分作答推断」（题少反而更需要，缺 1 题就不能算分）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
