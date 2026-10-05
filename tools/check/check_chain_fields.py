#!/usr/bin/env python3
"""守卫：**「挂上去的字段」不得被生成器重跑静默抹掉**（链路条 / PID-5 入口 / 常模状态）。

为什么要有这条守卫
==================
2026-10-04 实测发生过一次**静默半渲染**：

* `build_l1_instrument.py`（改 R2 授权措辞时被重跑）用 `Instrument.to_dict()` 覆盖了
  `data/instruments/dsm5tr-l1.json`，而 **`linkage` 与 `norms_status` 不在数据类里**，
  是后续步骤（`tools/build/attach_linkage.py` / `attach_norms.py`）挂上去的
  → 重跑后这两个字段**消失**。
* 后果：L1 页面的**链路条没了、PID-5 入口的「推论」标注没了**（`test_chain_nav` 2 项失败），
  但页面**不报任何异常**——`Runtime.exceptionThrown` 0 条、console 0 条
  （我用 CDP 抓过）。这就是「静默半渲染」：大部分还能用，核心链路悄悄没了。
* `build_l2_instruments.py` 早有同样的继承逻辑，**L1 那份漏了**（现已在
  `build_l1_instrument.py` 补上）。

所以这条守卫只做一件事：把**挂载期字段的必须存在**钉死。谁再重跑生成器而忘了继承，
这里立刻失败，不必等浏览器测试才发现。

判据（来自 `data/linkage/dsm5tr-chain.json` 的链路定义）：
  · L1        → `linkage.role == "screener"`，且 `downstream` 条数与链路定义一致
  · 8 册 L2   → `linkage.upstream.instrument == "DSM5TR-L1"`，域能与链路对上
  · PID-5     → `linkage.related.status == "inferred"`（与 L1 人格功能域相接，标为推论）
  · 全部量表  → 必须有 `norms_status`（界面据此决定显示百分位还是「仅原始分」）

用法：`python tools/check/check_chain_fields.py`（有问题则 exit 1）
"""

from __future__ import annotations

import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402

ROOT = find_root()
INST = os.path.join(ROOT, "data", "instruments")
CHAIN = os.path.join(ROOT, "data", "linkage", "dsm5tr-chain.json")


def load(p: str) -> dict:
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def main() -> int:
    bad: list[str] = []
    chain = load(CHAIN) if os.path.exists(CHAIN) else {}
    # 链路定义在 `level1.domains`（每个域含 threshold / level2 / level2_label）
    domains = ((chain.get("level1") or {}).get("domains")) or []
    l2_have = {d["level2"] for d in domains if d.get("level2")}

    pkgs = {os.path.basename(p)[:-5]: load(p)
            for p in sorted(glob.glob(os.path.join(INST, "*.json")))
            if not p.endswith("catalog.json")}

    # ① 每套都必须有 norms_status
    for code, d in pkgs.items():
        if not d.get("norms_status"):
            bad.append(f"{code}: 缺 norms_status（界面无法判断该显示百分位还是「仅原始分」）"
                       f"——多半是生成器重跑时没继承被挂上去的字段")

    # ② L1：链路起点 + downstream
    l1 = pkgs.get("dsm5tr-l1") or {}
    lk = l1.get("linkage")
    if not lk:
        bad.append("dsm5tr-l1: 缺 linkage —— L1 的**链路条与 PID-5 入口都会消失**"
                   "（test_chain_nav 会失败，但页面不报错）")
    else:
        if lk.get("role") != "screener":
            bad.append(f"dsm5tr-l1: linkage.role 应为 screener，实测 {lk.get('role')!r}")
        down = lk.get("downstream") or []
        if len(down) != len(domains):
            bad.append(f"dsm5tr-l1: downstream {len(down)} 条，链路定义 {len(domains)} 条")
        got = {x.get("to") for x in down if x.get("to")}
        miss = l2_have - got
        if miss:
            bad.append(f"dsm5tr-l1: downstream 缺下游量表 {sorted(miss)}")

    # ③ 8 册 L2：upstream 指回 L1 且域对得上
    for code, d in pkgs.items():
        if not code.startswith("dsm5tr-l2-"):
            continue
        up = ((d.get("linkage") or {}).get("upstream") or {})
        if not up:
            bad.append(f"{code}: 缺 linkage.upstream —— L2 的「细评 / 回到 Level 1」条会消失")
            continue
        if up.get("instrument") != "DSM5TR-L1":
            bad.append(f"{code}: upstream.instrument 应为 DSM5TR-L1，实测 {up.get('instrument')!r}")
        # ⚠️ 比对要用**量表包里的 instrument 码**（`DSM5TR-L2-Sleep`），
        #    不是文件名 stem（`dsm5tr-l2-sleep`）——大小写不同，第一版就比错了。
        inst_code = d.get("instrument", code)
        if inst_code not in l2_have:
            bad.append(f"{code}: 不在链路定义的 level2 列表里（{inst_code}）")

    # ④ PID-5：与 L1 人格功能域相接，且必须标为推论
    rel = ((pkgs.get("pid-5") or {}).get("linkage") or {}).get("related") or {}
    if not rel:
        bad.append("pid-5: 缺 linkage.related —— 与 L1 的接口标注会消失")
    elif rel.get("status") != "inferred":
        bad.append(f"pid-5: related.status 应为 inferred（手册未指定 L2，属**推论**），"
                   f"实测 {rel.get('status')!r}")

    print(f"检查 {len(pkgs)} 个量表包的挂载期字段（linkage / norms_status）")
    for b in bad:
        print("  ❌ " + b)
    if bad:
        print(f"\n❌ {len(bad)} 处")
        return 1
    print("✅ 链路字段（L1 起点 / L2 上游 / PID-5 推论接口）与 norms_status 齐备")
    return 0


if __name__ == "__main__":
    sys.exit(main())
