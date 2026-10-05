#!/usr/bin/env python3
"""构建**通用推断数据**：让「基于相关性的允许缺失值推断」不再只对大五生效。

背景与问题
==========
大五人格早已实现了这套推断（在 `ui/index.html` 的 tier 模式里）：答了一部分题之后，
按「已答的全部题目」推算某个面向的估计与完整分的相关 r，达到门槛就提前给结果。
它的数据基础是 `data/correlation-network.json`（题→facet 相关、facet 间相关），
来自 Johnson (2005) 的 **7,325 份完整作答**。

但那段实现**硬编码大五**（读 `ui/emohealth-data.js` 的 `D.facets`、`MIN_OWN=2`），
所以 PID-5 这类量表用不了。本脚本产出**量表级的推断数据**，格式统一，
好让前端只读数据、不认量表。

数据分级（**必须如实标注，不能混用**）
=====================================
  full        题级相关矩阵（220×220 那种）—— 最准，本项目目前只有大五的题→facet 版
  item_level  题→维度相关（实测）—— 大五有；能算较可靠的 r
  structural  只有**维度归属**，题与维度的相关按「同维度内等权」近似，维度间相关取 0
              —— 结论是**结构性的**，不是实证的

⚠️ 铁律：`structural` 级的结果**不得**被呈现为实证推断。前端必须显示级别与依据，
   与树布局那条「这是结构性排布，不是实证的题间相关」是同一个要求。
"""

from __future__ import annotations

import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from _root import find_root  # noqa: E402
ROOT = str(find_root())

INST_DIR = os.path.join(ROOT, "data", "instruments")
OUT_DIR = os.path.join(ROOT, "data", "inference")


def load_inst(code: str):
    for fn in os.listdir(INST_DIR):
        if not fn.endswith(".json") or fn == "catalog.json":
            continue
        d = json.load(open(os.path.join(INST_DIR, fn), encoding="utf-8"))
        if d["instrument"] == code:
            return d
    return None


def structural(inst: dict) -> dict:
    """只靠结构：每题对**本维度**取等权近似，跨维度取 0。"""
    item_dim, item_dim_corr = {}, {}
    for dim in inst["dimensions"]:
        ids = dim.get("items") or []
        k = len(ids)
        # 同维度内等权：单题与维度总分的相关 ≈ 1/sqrt(k)（等权、同向、同质假设下）
        approx = round(1.0 / math.sqrt(k), 4) if k else 0.0
        for iid in ids:
            item_dim[iid] = dim["id"]
            item_dim_corr[iid] = {dim["id"]: approx}
    return {
        "level": "structural",
        "item_dim": item_dim,
        "item_dim_corr": item_dim_corr,
        "dim_corr": {},          # 无来源 → 留空，前端按 0 处理并标注
        "quality": {
            "basis": "仅维度归属（来自量表包的计分键）",
            "item_dim_corr_approx": "同维度内等权假设 1/sqrt(k)",
            "dim_corr": "无来源",
            "warning": "结构性近似，不是实证的题间相关；不得呈现为实证推断",
        },
    }


def from_correlation_network(inst: dict, net: dict) -> dict:
    """大五：用实测的题→facet / 题→domain 相关（都是完整矩阵）。

    ⚠️ **这个函数的难点全在题序对齐**，我为此错了三次，记录清楚：
      · 生成器 `analyze_correlation_network.py` 里：
          行序 = `sorted(canon["items"], key=order)`（canon = `data/ipip-neo-300.json`）
          列序 = `sorted(fo)`（facet 名的**字母序**）
      · 而 **canon 是「轮转」排列**（第1题 anxiety、第2题 friendliness、第3题 imagination…），
        **量表包 `data/instruments/ipip-neo.json` 是「按 facet 分组」排列**
        （前 10 题全是 anxiety）。两个题序**完全不同**。
      · 所以 `ifc[idx]` 配 `inst.items[idx]` 必然错位——实测「题对自己 facet 的相关」
        中位只有 0.045，而文件自己的 headline 是 0.3565。
      · 正确做法：**按题文把 canon 的题对回量表包的 item**，并直接用 canon 每题的
        `facet` 字段（它与 `facets` 列表同源，`facets.index()` 一定命中）。

    另外 2 个维度名与 canon facet 名不同（量表包 `aesthetic_appreciation_artistic_interests`
    的 display name 是「Artistic Interests」、`modesty_humility` 是「Modesty」），
    靠 display name 匹配会失败——用 canon 的 `facet` 字段就绕开了这个问题。
    """
    facets = net["facets"]
    doms = net["domains"]
    ifc = net["item_facet_corr"]
    idc = net["item_domain_corr"]
    fcorr = net["facet_corr"]

    canon = json.load(open(os.path.join(ROOT, "data", "ipip-neo-300.json"),
                           encoding="utf-8"))
    # canon facet 名 → 列下标
    slot = {f: i for i, f in enumerate(facets)}

    def nn(s):
        return "".join(c for c in (s or "").lower() if c.isalnum())

    # 量表象包的题文 → item id
    by_text = {nn(it.get("text")): it["id"] for it in inst["items"]}

    item_dim, item_dim_corr, item_domain_corr = {}, {}, {}
    unmatched = 0
    for idx, c in enumerate(sorted(canon["items"], key=lambda x: x["order"])):
        iid = by_text.get(nn(c.get("text")))
        if iid is None:
            unmatched += 1
            continue
        f = c.get("facet")
        item_dim[iid] = f
        if idx < len(ifc):
            item_dim_corr[iid] = {facets[j]: round(ifc[idx][j], 4)
                                  for j in range(min(len(ifc[idx]), len(facets)))}
        if idx < len(idc):
            item_domain_corr[iid] = {doms[j]: round(idc[idx][j], 4)
                                     for j in range(min(len(idc[idx]), len(doms)))}

    dim_corr = {a: {facets[j]: round(fcorr[i][j], 4)
                    for j in range(min(len(fcorr[i]), len(facets)))}
                for i, a in enumerate(facets) if i < len(fcorr)}
    return {
        "level": "item_level",
        "item_dim": item_dim,
        "item_dim_corr": item_dim_corr,
        "item_domain_corr": item_domain_corr,
        "dim_corr": dim_corr,
        "quality": {
            "basis": net.get("source", ""),
            "question": net.get("question", ""),
            "headline": net.get("headline", {}),
            "note": ("题→facet 与题→domain 均为**实测**矩阵（Johnson 2005 完整作答）；"
                     "题序按题文从 canon 对回量表包"),
            "unmatched_items": unmatched,
            "dim_key": "facet（canon 自带字段，字母序与 correlation-network 同源）",
        },
    }


def attach_pair_and_minown(data: dict, code: str, inst: dict) -> dict:
    """给推断数据补上 `pairB64`（题间相关三角阵）与 `min_own`（各维度最小可靠题量）。

    为什么这两个字段是「与大五对齐」的最后一块
    ==========================================
    大五的界面推断（`ui/index.html` 的 `pairR` / `adaptCtx`）读 `AD.pairB64`——
    **完整的题间相关矩阵**，用来算偏相关（「已答这些题之后，候选题还能提供多少
    新信息」）。只有「题→维度相关」是算不出条件增益的。
    而 `MIN_OWN` 在大五里写死为 2；PID-5 各 facet 题数 4–14，写死一个值不合理，
    所以改为**从 partial 的 k-曲线推出**（达到 r≥0.8 所需的最小 k）。
    """
    out = dict(data)
    # 题间相关三角阵：大五从 adaptive-network.json 搬（同一份数据，同格式）
    if code == "IPIP-NEO":
        ap = os.path.join(ROOT, "data", "adaptive-network.json")
        if os.path.exists(ap):
            ad = json.load(open(ap, encoding="utf-8"))
            if ad.get("pairB64"):
                out["pairB64"] = ad["pairB64"]
                out["pair_note"] = ("float32 三角阵，按 a=2..n、b=1..a-1 展平；"
                                    "下标 = (a−1)(a−2)/2 + (b−1)。"
                                    "取自 data/adaptive-network.json（同一份数据）。")
    # min_own：从 partial-administration 的 k-曲线推
    pa = os.path.join(ROOT, "data", "partial-administration.json")
    if code == "IPIP-NEO" and os.path.exists(pa):
        d = json.load(open(pa, encoding="utf-8"))
        mo = {}
        for facet, row in (d.get("per_facet") or {}).items():
            # 该文件的 per_facet[facet] 形如 {k: {r_min,...}} 或含 r_min 的列表
            need = None
            if isinstance(row, dict):
                for k in sorted((int(x) for x in row if str(x).isdigit())):
                    v = row[str(k)]
                    r = v.get("r_min") if isinstance(v, dict) else None
                    if r is not None and r >= 0.80:
                        need = k
                        break
            mo[facet] = need or 1
        if mo:
            out["min_own"] = mo
    return out


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    net_path = os.path.join(ROOT, "data", "correlation-network.json")
    net = json.load(open(net_path, encoding="utf-8")) if os.path.exists(net_path) else None

    targets = ["IPIP-NEO", "PID-5"]
    print(f"{'量表':14}{'级别':>14}{'题数':>6}{'维度':>6}  说明")
    built = 0
    for code in targets:
        inst = load_inst(code)
        if not inst:
            print(f"{code:14}  （未找到量表包）")
            continue
        if code == "IPIP-NEO" and net:
            data = from_correlation_network(inst, net)
        else:
            data = structural(inst)
        payload = attach_pair_and_minown({
            "instrument": code,
            "level": data["level"],
            "level_note": {
                "structural": "只有维度归属；题与维度的相关为等权近似，维度间相关无来源",
                "item_level": "有实测的题→维度相关与维度间相关矩阵",
                "full": "有题级相关矩阵",
            }[data["level"]],
            "n_items": len(inst["items"]),
            "n_dims": len(inst["dimensions"]),
            "item_dim": data["item_dim"],
            "item_dim_corr": data["item_dim_corr"],
            "item_domain_corr": data.get("item_domain_corr", {}),
            "dim_corr": data["dim_corr"],
            "quality": data["quality"],
        }, code, inst)
        out = os.path.join(OUT_DIR, code.lower() + ".json")
        # ⚠️ 幂等/优先级保护：PID-5 的 item_level 数据由
        #    `tools/build/build_pid5_psychometrics.py` 从公开原始作答算出（N=2,148），
        #    比本脚本的 structural 近似高一级。若已存在更高级别，**不要覆盖**——
        #    否则「顺手重跑一次」就会把真数据降级成近似值，而且看不出发生过
        #    （这类「重新生成覆盖后加字段/覆盖更优产物」的坑本项目已踩过数次）。
        if os.path.exists(out):
            try:
                old = json.load(open(out, encoding="utf-8"))
                rank = {"structural": 0, "item_level": 1, "full": 2}
                if rank.get(old.get("level"), -1) > rank.get(data["level"], -1):
                    print(f"{code:14}{old['level']:>14}{len(inst['items']):6}"
                          f"{len(inst['dimensions']):6}  ⏭ 已有更高级别，保留不覆盖")
                    continue
            except Exception:                                  # noqa: BLE001
                pass
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
            fh.write("\n")
        built += 1
        print(f"{code:14}{data['level']:>14}{len(inst['items']):6}"
              f"{len(inst['dimensions']):6}  {os.path.getsize(out) / 1024:.0f} KB")
    print(f"\n✓ 写出 {built} 份 → data/inference/")
    print("⚠️ structural 级不得呈现为实证推断；前端必须显示级别与依据。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
