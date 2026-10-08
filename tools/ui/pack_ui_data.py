#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""前端层打包器：把 ``data/**`` 的 JSON 包成前端可加载的 ``ui/**`` 脚本。

为什么需要它
============
``ui/index.html`` 是**纯静态、可 ``file://`` 打开**的页面，数据包只能靠
``<script src>`` 注入，而 ``fetch('x.json')`` 在 ``file://`` 下会被同源策略拒绝。
所以每个数据包都必须是一段会自己挂到 ``window`` 上的 JS：

    window.EMOHEALTH_XXX = {…};

历史上这段包装是**数据层的 build 脚本自己写的**（``build_tier_ui_data``、
``build_unlock_network``、``build_adaptive_data``、``build_catalog``、
``build_tree_layouts``），于是数据层直接产出 ``ui/*.js``——那是跨层依赖：
改界面数据格式要动数据层脚本，数据层产物又散落在前端目录里。

现在把这一步单独抽出来放在**前端层**（``tools/ui/``）：

    数据层：archive/ → data/**.json        （不碰 ui/）
    前端层：data/**.json → ui/**.js          ← 就是本脚本

用法
====
    python tools/ui/pack_ui_data.py                 # 全部打包
    python tools/ui/pack_ui_data.py --only tier     # 只打一个包
    python tools/ui/pack_ui_data.py --check         # 只比对，不写文件（退出码 1 = 有差异）
    python tools/ui/pack_ui_data.py --list          # 列出作业表

设计
====
* **声明式作业表**（``JOBS``）：新增一个包 = 加一条记录，**不写新的打包代码**。
  单文件作业给 ``src``/``dst``/``var``；目录作业给 ``src_dir``/``dst_dir``/
  ``var_from``/``var_prefix``，逐个 json 变成同名 ``.js``。
* **通用包装**：读 json → ``window.<VAR> = <紧凑 JSON>;``。包装格式就这一种，
  没有针对某个包的解析分支。
* **紧凑重排**：用 ``json.dumps(..., ensure_ascii=False, separators=(",", ":"))``
  重新序列化，而不是原样搬运文件文本。这一条是必需的——``data/instruments/catalog.json``
  是 ``indent=1`` 的**人读**格式，而 ``ui/catalog.js`` 要的是紧凑单行。
  对本来就是紧凑格式的源文件（``tier-prefix`` 等），重排结果与源文件**逐字节相同**。
* **二进制 + LF 写出**：文本模式在 Windows 上会把 ``\\n`` 翻译成 ``\\r\\n``，
  于是同一份数据在不同机器上产出不同字节。这里统一按二进制写、行尾只用 LF。
* **注释头**：``ui/catalog.js`` 与 ``ui/tree-layouts/*.js`` 保留「自动生成」注释头
  （架构守卫的生成产物豁免要求有这个标记）。头里的生成者写**本脚本**，
  不写已经不再生成它的数据层脚本。
* ``ui/tree-layouts/index.json`` 是清单（``build_ui_instruments.py`` 直接 ``json.load``
  它），不是 JS，按原字节复制过去。
* **作业 → 输入显式化**（``inputs``）：新鲜度守卫
  ``tools/check/check_pack_freshness.py`` 要**逐 job** 比「最新输入 mtime」与
  「最旧产物 mtime」。写了 ``inputs`` 的作业以它为准，没写的按 ``src`` /
  ``src_dir/*.json`` 推（见 ``job_input_patterns``）。**引擎组装类作业必须显式写**：
  ``inference`` 的 payload 由 ``engine/inference.py`` 现场算，除 ``data/inference/*.json``
  外还读 ``data/instruments/**``、``data/item-norms*.json``、``data/norms/pid-5.json``，
  不写出来守卫就会漏判。

契约位置
========
本脚本属**前端层**：只读 ``data/**``，只写 ``ui/**``，不碰 ``archive/``（C1）。
数据层不再需要写 ``ui/``（C3 的「写入 ui/」计数因此归零）。
"""
from __future__ import annotations

import argparse
import copy
import glob
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root, force_utf8_io  # noqa: E402

ROOT = find_root()


#: 打包作业表。单文件作业：src/dst/var；目录作业：src_dir/dst_dir/var_from/var_prefix。
JOBS: tuple[dict, ...] = (
    {
        "name": "tier",
        "src": "data/tier-prefix.json",
        "dst": "ui/tier-data.js",
        "var": "EMOHEALTH_TIER",
        "inputs": ("data/tier-prefix.json",),
    },
    {
        "name": "unlock",
        "src": "data/unlock-network.json",
        "dst": "ui/unlock-data.js",
        "var": "EMOHEALTH_UNLOCK",
        "inputs": ("data/unlock-network.json",),
    },
    {
        "name": "adaptive",
        "src": "data/adaptive-network.json",
        "dst": "ui/adaptive-data.js",
        "var": "EMOHEALTH_ADAPT",
        "inputs": ("data/adaptive-network.json",),
    },
    {
        "name": "catalog",
        "src": "data/instruments/catalog.json",
        "dst": "ui/catalog.js",
        "var": "EMOHEALTH_CATALOG",
        "inputs": ("data/instruments/catalog.json",),
        "header": "多量表目录（由 tools/ui/pack_ui_data.py 从 "
                  "data/instruments/catalog.json 打包，勿手改）\n"
                  "   只有元信息：题项在各 data/instruments/<code>.json 里，按需加载。",
    },
    {
        "name": "tree-layouts",
        "src_dir": "data/tree-layouts",
        "dst_dir": "ui/tree-layouts",
        # 读 data/inference/*.json（题↔面向相关）与 data/instruments/*.json（题号↔id）
        # 来把「环内选谁」改成实证的——见 ring_order_by_item_dim_corr 的说明。
        "inputs": ("data/tree-layouts/*.json", "data/inference/*.json",
                   "data/instruments/*.json"),
        # 变量名取自布局自己的 meta.instrument（`EMOHEALTH_TREE_<CODE>`），
        # 与界面按需注入的约定一致；文件名用 instrument 的小写形式。
        "var_from": ("meta", "instrument"),
        "var_prefix": "EMOHEALTH_TREE_",
        # 「环内选谁」的判据：实证口径（题↔面向相关）。数据层产出的布局是**结构性**的，
        # 这里按实证重排环序（骨架仍是「每环每面向一题」）。
        "ring_order": "item_dim_corr",
        # ⚠️ 必须是赋值语句，不能是裸 JSON：界面用 <script> 注入，
        #    裸 JSON 会被当语句解析并抛 "Unexpected token ':'"。
        "header": "{instrument} 天赋树布局｜由 tools/ui/pack_ui_data.py 生成，勿手改",
        # 清单不是 JS，原样复制（内容是 {"threshold","count","note","scales"}）
        "copy": ("index.json",),
    },
    # ⚠️ 第 6 个作业 `inference` 曾在「只留最小 UI」那一轮被删除（task-10）。
    #    现在按用户要求（答题界面要展示「各指标预测 + 置信度」）**加回来**。
    {
        # 题面五字段（原文 / 中译 / 情景展示 scenario_zh / 选项情景说明 / 作答注记）→ 按需加载。
        # 数据由 tools/build/build_item_structured.py 产出（606 题，五字段齐全率 100%，
        # 守卫 tools/check/check_item_structured.py）。
        "name": "items-structured",
        "src_dir": "data/items-structured",
        "dst_dir": "ui/items-structured",
        "inputs": ("data/items-structured/*.json",),
        "var_from": ("instrument",),
        "var_prefix": "EMOHEALTH_STRUCT_",
        "header": "{instrument} 题面结构化五字段（原文 / 中译 / 情景展示 scenario_zh / "
                  "选项情景说明 / 作答注记）｜由 tools/ui/pack_ui_data.py 生成，勿手改",
        "manifest": ("ui/items-structured.js", "EMOHEALTH_STRUCTMAP", "items-structured/"),
        "manifest_header": ("题面结构化清单（code → ui/items-structured/<code>.js）"
                            "｜由 tools/ui/pack_ui_data.py 生成，勿手改"),
        # index.json 是给校验器看的总表，不是某一套量表的字段包
        "copy": ("index.json",),
    },
    {
        # 推断参数：**由 engine/inference.py 的 `params_for_js()` 生成**，
        # 不是简单把 `data/inference/*.json` 重排一遍。原因：
        # `ui/lib/inference.js` 需要 `ids` / `item_mean` / `item_sd` / `dim_items` /
        # `dim_agg` / `key_of_item` / `response_min·max` 等参数，其中题级均值与 SD
        # 由 engine 侧解析（IPIP-NEO 取 data/item-norms.json；PID-5 由 facet T 分表
        # 反推）。照抄 data/inference/*.json 会让 JS 侧**缺参数**；在 UI 里再写一遍
        # 组装逻辑就是「两套实现漂移」——本项目明确禁止（见
        # tools/check/test_inference_pyjs_consistency.py 的说明）。
        # 数值全部来自 data/inference/*.json（pairB64 / item_dim_corr / dim_ceiling /
        # dim_ceiling_cross / ceiling_ratio / ceiling_ratio_cross），engine 只做组装。
        # ⚠️ 因此本作业**需要 numpy**（engine/inference.py 的依赖）。缺依赖时**明确报错**，
        #    不会静默留下旧产物。
        "name": "inference",
        "src_dir": "data/inference",
        "dst_dir": "ui/inference",
        # ⚠️ 显式输入：payload 由 engine/inference.py 现场组装，它除了
        #    `data/inference/<code>.json` 还读 `data/instruments/**`（按 instrument 字段找量表包）、
        #    `data/item-norms*.json` / `data/norms/pid-5.json`（题级 mean·SD），
        #    以及 engine 侧代码本身。漏一个，新鲜度守卫就会漏判。
        "inputs": ("data/inference/*.json", "data/instruments/*.json",
                   "data/item-norms.json", "data/item-norms-*.json",
                   "data/norms/pid-5.json", "engine/inference.py",
                   "engine/instrument_schema.py", "engine/scoring.py"),
        "var_from": ("instrument",),
        "var_prefix": "EMOHEALTH_INFER_",
        "header": ("{instrument} 题级推断参数（ids/题→维度相关/题级 mean·SD/"
                   "上限·比例/pairB64）｜由 tools/ui/pack_ui_data.py 调 "
                   "engine/inference.py 生成，勿手改"),
        "manifest": ("ui/inference.js", "EMOHEALTH_INFERMAP", "inference/"),
        "manifest_header": ("推断参数清单（code → ui/inference/<code>.js）"
                            "｜由 tools/ui/pack_ui_data.py 生成，勿手改"),
        "engine_payload": True,
    },
)


def engine_payload(code: str) -> dict:
    """用 `engine/inference.py` 组装某量表的 JS 参数包（与 Python 侧**同一份**）。

    ⚠️ 需要 numpy。缺依赖时抛 RuntimeError 并说明——**不要**退回「只搬 JSON」，
    那样 JS 侧会缺 `item_mean`/`item_sd`/`dim_items` 等参数。
    """
    sys.path.insert(0, ROOT)
    try:
        from engine.inference import load as load_model  # noqa: PLC0415
    except Exception as exc:                              # noqa: BLE001
        raise RuntimeError(
            "inference 作业需要 engine/inference.py（依赖 numpy），"
            f"当前解释器导入失败：{type(exc).__name__}: {exc}"
            "——请用带 numpy 的解释器跑本脚本") from exc
    m = load_model(code)
    inf = load_json(m.inference_json)
    return {
        "instrument": code,
        # 与 engine/inference.py --dump-params 的输出同形：{params, pairB64}
        "params": m.params_for_js(),
        "pairB64": inf["pairB64"],
        # 出处与口径（界面上「为什么能给这个数」要能查到）
        "item_dim_corr_kind": inf.get("item_dim_corr_kind"),
        "ceiling_note": inf.get("ceiling_note", ""),
        "ceiling_cross_note": inf.get("ceiling_cross_note", ""),
        "min_own_removed": inf.get("min_own_removed", ""),
        "level": inf.get("level"),
        "n_respondents": inf.get("n_respondents"),
        "quality": inf.get("quality", {}),
    }


def compact(obj, sort_keys: bool = False) -> str:
    """紧凑序列化：与历史 build 脚本的 ``separators=(',", ':' )`` 口径一致。

    ``sort_keys`` 用于**引擎生成**的作业：`engine/inference.py` 的
    `_resolve_item_stats` 用 `ids = {…}`（集合）建题级均值/SD 字典，集合迭代序
    受 Python 字符串哈希随机化影响 → 同一份数据两次产出**字节不同**（大小相同）。
    排序键即可消除，保证 `--check` 逐字节一致。
    """
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"),
                      sort_keys=sort_keys)


def ident(code: str) -> str:
    """把量表 code 变成合法的 JS 标识符片段（与 build_ui_instruments.py 同规则）。"""
    return re.sub(r"[^A-Za-z0-9]", "_", code).upper()


def render(header: str | None, var: str, obj, sort_keys: bool = False) -> str:
    """通用包装：可选注释头 + ``window.<var> = <紧凑 JSON>;``。"""
    out = f"/* {header} */\n" if header else ""
    return out + f"window.{var} = {compact(obj, sort_keys=sort_keys)};\n"


# ------------------------------------------------ 树布局：把「环内选谁」改成实证的

def _order_to_id(code: str) -> dict[str, str]:
    """题号（1-based，字符串）→ 题 id。取自 `data/instruments/<code>.json`（两份都有）。"""
    p = os.path.join(ROOT, "data", "instruments", code.lower() + ".json")
    if not os.path.exists(p):
        return {}
    return {str(it["order"]): it["id"]
            for it in (load_json(p).get("items") or []) if "order" in it and "id" in it}


def ring_order_by_item_dim_corr(layout: dict) -> dict:
    """把结构性树布局的**环序**改成实证的：环内按 ``|item_dim_corr|`` 从高到低。

    「每环每面向一题」的骨架**不变**，只改**环内选谁**：

        第 0 环 = 每个面向信息量最大的那一题（＝「所有方面各答一题」）
        第 r 环 = 每个面向第 r+1 高的那一题（题少的面向在后面的环自然缺席）
        环数   = max(每个面向的题数)

    判据（全部可复算，来源写进 ``meta``）：
      · ``data/inference/<code>.json`` → ``item_dim_corr[<item_id>][<dim_id>]``
        （题↔面向相关，取**绝对值**降序；口径见同文件 ``item_dim_corr_kind``，
        样本量 ``n_respondents``）。反向题已按 ``key_of_item`` 折过，**不再翻一次**。
      · 同文件 ``item_dim[<item_id>]`` → 题的面向归属
      · ``data/instruments/<code>.json`` 的 ``items[].order`` / ``items[].id`` → 题号↔id

    随之重算 ``depth``（界面用 ``depth[key] === 0`` 判「最内环可答」）与 ``support``
    （同簇、更浅一环、xy 最近），并补顶层 ``rings``（界面读 ``layout.rings``）。
    ``xy``（画布坐标）**沿用结构性布局的几何**——本函数只改顺序、不改几何。

    没有推断模型（``data/inference/<code>.json`` 不存在）时**保持结构性**并在 ``meta``
    里如实标注；**不伪造实证口径**。面向集合/题号映射对不上时**直接报错**（两个真相源
    漂移了，静默退回会把错的东西发出去）。
    """
    code = layout["meta"]["instrument"]
    inf_rel = f"data/inference/{code.lower()}.json"
    facets = [c["id"] for c in layout["clusters"]]

    if not os.path.exists(os.path.join(ROOT, *inf_rel.split("/"))):
        out = copy.deepcopy(layout)
        out["meta"] = {**layout["meta"],
                       "layout_basis": "dimension",
                       "basis_note": f"该量表**没有推断模型**（{inf_rel} 不存在），因此保持"
                                     "结构性排布：按量表自身声明的维度成簇，环内顺序**未**按"
                                     "题↔面向相关排序。",
                       "rule": "每环从每个维度各取一题（结构性顺序，未按信息量排序）"}
        return out

    inf = load_json(os.path.join(ROOT, *inf_rel.split("/")))
    idc = inf.get("item_dim_corr") or {}
    item_dim = inf.get("item_dim") or {}
    o2i = _order_to_id(code)
    if not idc or not item_dim or not o2i:
        raise RuntimeError(
            f"tree-layouts/{code}：{inf_rel} 缺 item_dim_corr/item_dim，或 "
            f"data/instruments/{code.lower()}.json 缺 order/id —— 无法按实证口径排序。"
            "（不静默退回结构性：先修数据）")

    datum_facets = set(item_dim.values())
    if set(facets) != datum_facets:
        raise RuntimeError(
            f"tree-layouts/{code}：布局簇 id 与 {inf_rel} 的 item_dim 面向集合不一致——"
            f"仅布局有 {sorted(set(facets) - datum_facets)[:4]}、"
            f"仅数据有 {sorted(datum_facets - set(facets))[:4]}")

    ranked: dict[str, list[int]] = {}
    for c in layout["clusters"]:
        fid = c["id"]
        rows: list[tuple[float, int]] = []
        for order in c["items"]:
            iid = o2i.get(str(order))
            if iid is None:
                raise RuntimeError(f"tree-layouts/{code}：题号 {order} 在 "
                                   f"data/instruments/{code.lower()}.json 里没有对应 id")
            r = (idc.get(iid) or {}).get(fid)
            if r is None:
                raise RuntimeError(f"tree-layouts/{code}：{iid} 对面向 {fid} 没有 item_dim_corr")
            rows.append((abs(float(r)), int(order)))
        rows.sort(key=lambda t: (-t[0], t[1]))      # 相关高→低；同分按题号，保证确定性
        ranked[fid] = [o for _r, o in rows]

    max_rings = max(len(v) for v in ranked.values())
    ring_nodes = [[ranked[fid][r] for fid in facets if len(ranked[fid]) > r]
                  for r in range(max_rings)]

    flat = sorted(o for ring in ring_nodes for o in ring)
    expected = sorted(int(o) for c in layout["clusters"] for o in c["items"])
    if flat != expected:                            # ③ 覆盖完整（不重不漏）
        raise RuntimeError(f"tree-layouts/{code}：环覆盖不完整或有重复"
                           f"（{len(flat)} vs {len(expected)}）")

    depth = {str(o): r for r, ring in enumerate(ring_nodes) for o in ring}

    # ── 几何：**保角度、换半径**（task-44）────────────────────────────────────
    # 旧 `xy` 的**角度**是布局的稳定标识（每个簇占一个扇区、同簇聚在一起、簇间相对
    # 方位不变），**一个都不动**；**半径**按新的环序重新分配：第 r 环 → 第 r 个半径带，
    # 内环在里、外环在外。于是「最内环可答」（`depth === 0`）在图上真的就是中心那一圈。
    #
    # 半径配方沿用数据层 `tools/build/build_tree_layouts.py` 的实测口径（同环相邻节点
    # 的弧长 ≥ 节点直径 `NODE_D=0.055`；相邻环的径向间距 ≥ `MIN_GAP=0.055`），
    # 但**按各自环数归一化**（PID-5 是 14 环、IPIP-NEO 是 10 环，**不写死 10**），
    # 归一到最外环 = 1.0。内半径下限取 `max(0.12, 旧几何的最小半径)`——环数变多会把
    # 半径带整体压扁，若内环跟着变小，中心区会比旧几何**更挤**（实测 PID-5 的节点最小
    # 间距会从 0.0131 掉到 0.0101）；用旧几何的内半径兜底，保证「不因本次改动更挤」。
    # 同一环内所有节点**同一个半径**（成「环」），不加抖动——这样半径带互不穿插，
    # 也不会出现同环两点重合（每环最多每簇一题 ⇒ 同环不同簇 ⇒ 扇区不同）。
    old_xy = layout["xy"]
    old_inner = min(math.hypot(*old_xy[str(o)]) for o in flat)
    NODE_D, MIN_GAP = 0.055, 0.055
    inner_floor = max(0.12, old_inner)
    ring_sizes = [max(1, len(r)) for r in ring_nodes]
    radii: list[float] = []
    prev_r: float | None = None
    for sz in ring_sizes:
        need = sz * NODE_D / (2 * math.pi)      # 该环不重叠所需的最小半径
        need = max(need, inner_floor)           # 内半径下限（见上）
        r = need if prev_r is None else max(need, prev_r + MIN_GAP)
        radii.append(r)
        prev_r = r
    outer = radii[-1] if radii else 1.0
    radii = [r / outer for r in radii]          # 归一到最外环 = 1.0（**归一化后不再设下限**，
                                                # 否则最内两环会被压到同一半径、破坏①②）

    xy: dict[str, list[float]] = {}
    # 角度：**保扇区**——每个簇仍占一个宽度 ∝ 题数的扇区（与数据层同配方，簇的次序与
    # 相对方位一个都不动），簇内**所有题共用该扇区的中心角**，于是同簇的题在图上连成
    # 一条**径向分支**（这也让 `support` 边全部成为相邻环之间的短径向边）。
    #
    # ⚠️ 为什么不「逐题沿用旧角度」（task-44 实测，别退回去）：
    #    旧角度是按「该题在簇内的**次序**」在扇区内铺开的，而新环序是按 `item_dim_corr`
    #    的**排名**——两者一解耦，同一环里相邻两簇的「边界题」就会撞在一起：
    #      · IPIP-NEO 节点最小间距 0.0724 → **0.0127（−82%）**，25 对点距离小于节点直径；
    #      · PID-5 0.0131 → 0.0117，且同簇支撑边变成斜边（最长 0.336）。
    #    收成径向分支后：IPIP-NEO 0.0626、PID-5 0.0343；支撑边一律 ≤ 0.08。
    #    ——动的是**簇内**的角度铺开方式，**扇区本身没动**（下面还有一条断言证明它）。
    total_items = sum(len(c["items"]) for c in layout["clusters"])
    sector_mid: dict[str, float] = {}
    acc_ang = 0.0
    for c in layout["clusters"]:
        w = 2 * math.pi * len(c["items"]) / total_items
        sector_mid[c["id"]] = acc_ang + w / 2
        acc_ang += w
    if abs(acc_ang - 2 * math.pi) > 1e-9:                       # 扇区必须正好铺满一圈
        raise RuntimeError(f"tree-layouts/{code}：扇区宽度合计 {acc_ang:.6f} ≠ 2π")

    dim_of_order = {o: c["id"] for c in layout["clusters"] for o in c["items"]}
    # 证明「扇区没动」：旧角度必须都落在各自簇的扇区内（重建的扇区 = 旧扇区）
    acc_ang = 0.0
    for c in layout["clusters"]:
        w = 2 * math.pi * len(c["items"]) / total_items
        for o in c["items"]:
            ox0, oy0 = old_xy[str(o)]
            if ox0 == 0.0 and oy0 == 0.0:
                continue
            a = math.atan2(oy0, ox0) % (2 * math.pi)
            if not (acc_ang - 1e-6 <= a <= acc_ang + w + 1e-6):
                raise RuntimeError(
                    f"tree-layouts/{code}：题 {o} 的旧角度 {a:.4f} 不在重建的扇区 "
                    f"[{acc_ang:.4f}, {acc_ang + w:.4f}) 内——扇区重建与数据层不一致")
        acc_ang += w

    for ring_idx, ring in enumerate(ring_nodes):
        rad = radii[ring_idx]
        for o in ring:
            ang = sector_mid[dim_of_order[o]]
            xy[str(o)] = [round(rad * math.cos(ang), 4), round(rad * math.sin(ang), 4)]

    # 支撑边：同簇、更浅一环、**新几何下 xy 最近**（半径变了 → 最近关系会变，必须用它重算）
    support: dict[str, list[str]] = {}
    for c in layout["clusters"]:
        members = sorted(int(o) for o in c["items"])
        for o in members:
            ti = depth[str(o)]
            if ti == 0:
                support[str(o)] = []
                continue
            cands = [p for p in members if depth[str(p)] == ti - 1] \
                or [p for p in members if depth[str(p)] < ti]
            if not cands:
                support[str(o)] = []
                continue
            a = xy[str(o)]
            best = min(cands, key=lambda p: (xy[str(p)][0] - a[0]) ** 2
                                           + (xy[str(p)][1] - a[1]) ** 2)
            support[str(o)] = [str(best)]

    kind = inf.get("item_dim_corr_kind")
    n_resp = inf.get("n_respondents")
    # 样本量：优先显式字段；没有就退到 quality.basis（IPIP-NEO 的作答条数记在那里：
    # 「Johnson (2005) 完整作答 7325 条（反向题已还原为同向）」）。都没有就如实不写。
    sample_note = (f"N={n_resp}" if n_resp
                   else ((inf.get("quality") or {}).get("basis") or None))
    meta = dict(layout["meta"])
    meta.update({
        "rings": max_rings,
        "layout_basis": "item_dim_corr",
        "basis_note": (
            "环内顺序按**题↔面向相关** `|item_dim_corr|` 从高到低：第 1 环 = 每个面向信息量"
            "最大的那一题（各面向先各答一题），第 2 环次之……依据 "
            f"`{inf_rel}` 的 `item_dim_corr[<item_id>][<dim_id>]`"
            + (f"（口径 `{kind}`" if kind else "（口径见该文件 `item_dim_corr_kind`")
            + (f"，{sample_note}）" if sample_note else "）")
            + f"；面向归属取自同文件 `item_dim`，题号↔题 id 取自 "
              f"`data/instruments/{code.lower()}.json`。"
              "「每环每面向一题」的骨架不变，**只改环内选谁**。"
              "`xy` 画布坐标已按新环序重算：**角度**沿用结构性布局的簇扇区（同簇同扇区、"
              "簇间相对方位不变），**半径**按第 r 环归一化（同环同半径、内环在里、外环在外，"
              "最外环 = 1.0）；`depth`/`support`/`ringNodes`/`rings` 与之一致。"),
        "rule": "第 r 环 = 每个面向第 r 高信息量的题（题少的面向在后面的环自然缺席）："
                "先把每个面向信息量最大的题各答一题，之后按信息量递减解锁。",
        "ordering_applied_by": "tools/ui/pack_ui_data.py（tree-layouts 作业）",
        "structural_source": f"data/tree-layouts/{code.lower()}.json",
        "order_field": f"{inf_rel} → item_dim_corr[item_id][dim_id]（取绝对值降序）",
    })
    if kind:
        meta["item_dim_corr_kind"] = kind
    if n_resp:
        meta["n_respondents"] = n_resp
    if sample_note:
        meta["sample_provenance"] = sample_note

    out = dict(layout)
    out.update({"meta": meta, "rings": max_rings, "ringNodes": ring_nodes,
                "depth": depth, "xy": xy, "support": support})
    return out


def load_json(path: str):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def job_files(job: dict) -> list[tuple[str, str, str]]:
    """展开一个作业 → [(源相对路径, 目标相对路径, 要写出的文本)]。"""
    if "src" in job:
        obj = load_json(os.path.join(ROOT, *job["src"].split("/")))
        return [(job["src"], job["dst"],
                 render(job.get("header"), job["var"], obj))]

    src_dir = os.path.join(ROOT, *job["src_dir"].split("/"))
    if not os.path.isdir(src_dir):
        raise FileNotFoundError(f"{job['src_dir']}/ 不存在（先跑数据层脚本产出它）")
    copies = set(job.get("copy", ()))
    out: list[tuple[str, str, str]] = []
    manifest: dict[str, str] = {}
    for fn in sorted(os.listdir(src_dir)):
        if not fn.endswith(".json") or fn in copies:
            continue
        obj = load_json(os.path.join(src_dir, fn))
        code = obj
        for key in job["var_from"]:
            code = code[key]
        payload = engine_payload(code) if job.get("engine_payload") else obj
        if job.get("ring_order") == "item_dim_corr":
            payload = ring_order_by_item_dim_corr(payload)
        header = job["header"].format(instrument=code) if job.get("header") else None
        rel_js = f"{fn[:-len('.json')]}.js"
        out.append((f"{job['src_dir']}/{fn}",
                    f"{job['dst_dir']}/{rel_js}",
                    render(header, job["var_prefix"] + ident(code), payload,
                           sort_keys=bool(job.get("engine_payload")))))
        manifest[code] = (job["manifest"][2] + rel_js) if job.get("manifest") else rel_js
    if job.get("manifest"):
        dst_rel, var, _prefix = job["manifest"]
        # 键排序：同一份数据每次产出同样的字节（--check 要求逐字节一致）
        out.append((f"{job['src_dir']}/*.json（清单）", dst_rel,
                    render(job.get("manifest_header"), var,
                           {k: manifest[k] for k in sorted(manifest)})))
    for fn in job.get("copy", ()):
        with open(os.path.join(src_dir, fn), "rb") as fh:
            raw = fh.read()
        out.append((f"{job['src_dir']}/{fn}", f"{job['dst_dir']}/{fn}",
                    raw.decode("utf-8")))
    return out


# ------------------------------------------------- 作业 → 输入/产物（路径级，不读内容）
#
# 供 tools/check/check_pack_freshness.py 用：它要**逐 job** 比
# 「最新输入 mtime」与「最旧产物 mtime」，所以这里只算路径、不读文件内容、
# 也不调 engine（否则守卫会变成一次昂贵的打包）。

def job_input_patterns(job: dict) -> tuple[str, ...]:
    """该作业声明的输入（相对路径或 glob）。手工 ``inputs`` 优先。"""
    explicit = job.get("inputs")
    if explicit:
        return tuple(explicit)
    if "src" in job:
        return (job["src"],)
    return (f"{job['src_dir']}/*.json",)


def glob_rel(pattern: str) -> list[str]:
    """展开 glob 为实际存在的文件（相对路径，``/`` 分隔，按名排序）。

    公开给 ``tools/check/check_pack_freshness.py``：它要分辨「声明了但一个都没匹配到」
    （源目录缺失）与「匹配到了」两种情形。
    """
    pat = os.path.join(ROOT, *pattern.split("/"))
    return [os.path.relpath(p, ROOT).replace(os.sep, "/")
            for p in sorted(glob.glob(pat))]


def job_input_paths(job: dict) -> list[str]:
    """该作业**实际存在的输入文件**（只算路径，不读内容）。"""
    out: list[str] = []
    for pattern in job_input_patterns(job):
        out.extend(glob_rel(pattern))
    return out


def job_output_paths(job: dict) -> list[str]:
    """该作业预期的**产物文件**（只算路径，不读内容）。

    目录作业按「源目录里每个 json → 同名 .js」推产物，所以**新增了一个源文件
    却没重打包**时，会得到一个「预期存在但磁盘上没有」的产物——守卫据此报 ❌；
    再加上清单文件与 ``copy`` 目标。
    """
    if "src" in job:
        return [job["dst"]]
    src_dir = os.path.join(ROOT, *job["src_dir"].split("/"))
    copies = set(job.get("copy", ()))
    outs: list[str] = []
    if os.path.isdir(src_dir):
        for fn in sorted(os.listdir(src_dir)):
            if fn.endswith(".json") and fn not in copies:
                outs.append(f"{job['dst_dir']}/{fn[:-len('.json')]}.js")
    if job.get("manifest"):
        outs.append(job["manifest"][0])
    outs.extend(f"{job['dst_dir']}/{fn}" for fn in job.get("copy", ()))
    return outs


def write_text(rel: str, text: str) -> int:
    """二进制写、只用 LF —— 避免 Windows 文本模式把 \\n 变成 \\r\\n。"""
    dst = os.path.join(ROOT, *rel.split("/"))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    data = text.encode("utf-8")
    with open(dst, "wb") as fh:
        fh.write(data)
    return len(data)


def check_text(rel: str, text: str) -> tuple[bool, str, int]:
    dst = os.path.join(ROOT, *rel.split("/"))
    if not os.path.exists(dst):
        return False, "缺失", len(text.encode("utf-8"))
    with open(dst, "rb") as fh:
        cur = fh.read()
    want = text.encode("utf-8")
    if cur == want:
        return True, "一致", len(want)
    return False, f"不一致（磁盘 {len(cur)} B / 应为 {len(want)} B）", len(want)


def main(argv: list[str] | None = None) -> int:
    force_utf8_io()          # 入口第一件事：GBK 控制台下不许崩（见函数 docstring）
    ap = argparse.ArgumentParser(
        description="把 data/** 的 JSON 打包成 ui/** 的 window.* 赋值脚本（前端层）")
    ap.add_argument("--only", action="append", metavar="NAME",
                    help="只处理指定作业（可多次；作业名见 --list）")
    ap.add_argument("--check", action="store_true",
                    help="只比对生成结果与磁盘现状，不写文件")
    ap.add_argument("--list", action="store_true", help="列出作业表后退出")
    args = ap.parse_args(argv)

    if args.list:
        for job in JOBS:
            ins = job_input_paths(job)
            outs = job_output_paths(job)
            dst_desc = job.get("dst") or f"{job['dst_dir']}/*.js"
            if job.get("manifest"):
                dst_desc += "、" + job["manifest"][0]
            if job.get("copy"):
                dst_desc += "、" + "、".join(f"{job['dst_dir']}/{c}"
                                            for c in job["copy"])
            print(f"  {job['name']}")
            print(f"    输入 {len(ins):3} 个  ←  " + "、".join(job_input_patterns(job)))
            print(f"    产物 {len(outs):3} 个  →  {dst_desc}")
        return 0

    print(f"前端打包（项目根：{ROOT}）")
    print(f"模式：{'只比对（--check）' if args.check else '写入'}")
    print()

    bad = 0
    total = 0
    for job in JOBS:
        if args.only and job["name"] not in args.only:
            continue
        try:
            files = job_files(job)
        except FileNotFoundError as exc:
            print(f"✗ {job['name']}：{exc}")
            bad += 1
            continue
        print(f"── {job['name']}（{len(files)} 个）")
        for src_rel, dst_rel, text in files:
            total += 1
            if args.check:
                ok, note, nbytes = check_text(dst_rel, text)
                mark = "✓" if ok else "✗"
                if not ok:
                    bad += 1
                print(f"   {mark} {src_rel} → {dst_rel}：{note}")
            else:
                nbytes = write_text(dst_rel, text)
                print(f"   ✓ {src_rel} → {dst_rel}（{nbytes / 1024:.1f} KB）")
        print()

    if args.check:
        if bad:
            print(f"❌ {bad}/{total} 个文件与磁盘现状不一致。")
            return 1
        print(f"✅ {total} 个文件与磁盘现状逐字节一致。")
        return 0
    print(f"✅ 打包 {total} 个文件。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
