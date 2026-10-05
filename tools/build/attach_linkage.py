#!/usr/bin/env python3
"""把链路关系挂进各量表包，供界面做**可点跳转**。

为什么单独一步
==============
链路定义在 ``data/linkage/dsm5tr-chain.json``（源自手册 Table 1）。界面要做的
跳转有两个方向，缺一不可：

  · **正向**：Level 1 的结果页 → 「建议做 L2—抑郁」→ 点进那一册
  · **反向**：打开 L2 抑郁册时 → 说明「我是 Level 1 的抑郁域触发后的细评工具」
             → 能回到 Level 1

只做正向的话，用户从某份 L2 进来就不知道自己在链路哪一段。
另外「人格功能 → PID-5」这一步要在两侧都**标明是推论**（硬规则③）。

⚠️ 字段名统一用 ``linkage``：L1 用 ``linkage.downstream``（可跳的下游），
L2 用 ``linkage.upstream``（触发它的上游）；PID-5 用 ``linkage.related``。
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
INST = os.path.join(ROOT, "data", "instruments")
CHAIN = os.path.join(ROOT, "data", "linkage", "dsm5tr-chain.json")


def main() -> int:
    chain = json.load(open(CHAIN, encoding="utf-8"))
    l1 = chain["level1"]
    domains = l1["domains"]
    pid5 = chain["pid5_interface"]
    touched = 0

    # ── Level 1：下游可跳转
    p = os.path.join(INST, "dsm5tr-l1.json")
    d = json.load(open(p, encoding="utf-8"))
    d["linkage"] = {
        "role": "screener",
        "label": "跨切面症状筛查（链路起点）",
        "downstream": [{
            "domain": x["name"], "threshold": x["threshold"],
            "to": x["level2"],
            "to_label": (x["level2"] or "").replace("DSM5TR-L2-", "Level 2—")
                        if x["level2"] else None,
        } for x in domains],
        # 人格功能域 → PID-5：**推论**，两侧都要带这个标记
        "inferred_route": {
            "domain": pid5["from_domain"],
            "to": "PID-5",
            "status": pid5["status"],
            "evidence": pid5["evidence"],
            "basis": pid5["basis"],
            "caveat": pid5["caveat"],
        },
        "source": l1["evidence"],
    }
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(d, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    touched += 1
    print(f"  ✓ DSM5TR-L1：{len(domains)} 个域的下游 + 1 条推论路线")

    # ── 各 Level 2：上游是谁触发
    for x in domains:
        if not x["level2"]:
            continue
        p = os.path.join(INST, x["level2"].lower() + ".json")
        if not os.path.exists(p):
            print(f"  ⚠ 找不到 {x['level2']}（跳过）")
            continue
        d = json.load(open(p, encoding="utf-8"))
        d["linkage"] = {
            "role": "level2",
            "label": f"Level 2 细评（对应 Level 1 的「{x['name']}」域）",
            "upstream": {
                "instrument": "DSM5TR-L1",
                "domain": x["name"],
                "domain_roman": x["roman"],
                "threshold": x["threshold"],
                "threshold_label": x["threshold_label"],
            },
            "source": l1["evidence"],
        }
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(d, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
        touched += 1
        print(f"  ✓ {x['level2']:24} ← Level 1「{x['name']}」域")

    # ── PID-5：与链路的推论关系（如实标注）
    p = os.path.join(INST, "pid-5.json")
    d = json.load(open(p, encoding="utf-8"))
    d["linkage"] = {
        "role": "pid5",
        "label": "人格障碍特质评估（DSM-5 Section III AMPD 的 Criterion B）",
        "related": {
            "instrument": "DSM5TR-L1",
            "domain": pid5["from_domain"],
            "status": pid5["status"],
            "evidence": pid5["evidence"],
            "basis": pid5["basis"],
            "caveat": pid5["caveat"],
            "how_to_verify": pid5.get("how_to_verify", ""),
        },
    }
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(d, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    touched += 1
    print(f"  ✓ PID-5：与链路的关系（status={pid5['status']}）")

    print(f"\n共更新 {touched} 个量表包")
    return 0


if __name__ == "__main__":
    sys.exit(main())
