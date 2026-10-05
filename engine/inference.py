#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""题级线性预测：从**部分作答**预测某个模块特质的**最终得分**，并给出置信度。

它回答的是用户那一句：「按照已有的文献报告、统计文档或计算模型，完成对某一模块
特质**最终得分的事实预测和置信度计算**。」

模型（全部来自项目已有的统计产物，不引入新模型）
================================================
以「已答题」为条件的**线性条件期望**（BLUP / 常规回归预测）：

    T        = 该维度**全部题项**的计分和（facet 总分）
    T_known  = 已答的**本维度**题项之和 —— 已知，不需要推断
    T_U      = 未答的本维度题项之和      —— 需要预测（U = unanswered）
    z_A      = 已答题的标准化计分值（(x - 均值)/SD）
    预测     = T_known + E[T_U | z_A]
             = T_known + Σ_{j∈U} μⱼ + σ_TU · cᵀ Σ_AA⁻¹ z_A
      cᵢ     = Cov(xᵢ, T_U) / (σᵢ σ_TU) = (Σ_{j∈U} σⱼ ρᵢⱼ) / σ_TU
      Σ       = 题间相关矩阵（`pairB64`，来自 `data/inference/<code>.json`）

  这不是新模型：它就是项目一直在用的那套「以已答题为条件的线性预测」。区别只是
  把**已答的本维度题项当成已知量**而不是再预测一遍——否则「全答时预测 ≠ 官方分」
  （验收硬要求），而「答满 10 题时预测必须精确等于官方分」在数学上是必须成立的。

两个置信度，各有各的用途（**不要混用**）
========================================
* `confidence_r`（**判据口径**，corrected）：`r = √(bᵀ Σ_AA⁻¹ b)`，`b` 取
  `item_dim_corr`（题与「其余题之和」的相关，去本题），预测变量**只含该维度自己
  已答的题**。这与前端 `ui/index.html` 的判据、与 `dim_ceiling` 的标定口径逐字一致
  （见 `tools/check/calibrate_ceiling_ratio.py`），所以 `available` 门槛沿用它：
  `confidence_r ≥ dim_ceiling × ceiling_ratio` 才算「可给结果」。
* `r2_total`（**预测准确度口径**）：上面那个预测的期望 R²，
  `R²_total = 1 − σ_TU²(1 − R²_TU) / σ_T²`，`R²_TU = cᵀ Σ_AA⁻¹ c`。
  它把「已答的本维度题项是已知量」算进去，因此 `≥` 判据口径的 r²（全答时恰为 1）。
  界面要呈现「这个预测有多准」时应当用它；呈现「你收集到的**独立**信息够不够」
  时用 `confidence_r`。两者的实测关系见 `research/inference-validation-report.md`。

与官方计分**分层**（用户明确要求）
==================================
`official` 块 = 量表声明口径的官方分，**缺失不猜**：只有该维度答满才给值，
否则 `value = None` + `blocker`。`inferred` 块 = 本模块的预测，**一律带
`inferred: true`**，绝不写回官方分。调用方不得把两者混算（见 `PLAN.md` 与
`engine/scoring.py` 的 `complete` 语义）。

出处（每个参数都能追）
======================
`data/inference/<code>.json`  : `pairB64`（题间相关）、`item_dim_corr`（corrected）、
                                `dim_ceiling`、`ceiling_ratio`
`data/item-norms.json`        : IPIP-NEO 每题的均值/SD（N=20,974，与 pairB64 同源）
`data/norms/pid-5.json`       : PID-5 各 facet 的 T 分表 → 均值/SD（Zimmermann 等 2026）
`data/instruments/<code>.json`: 题项归属、计分键、聚合方式、作答范围
`engine/scoring.py`           : 官方计分（缺失不猜）

用法
====
    python engine/inference.py --instrument IPIP-NEO \
        --responses-json '{"ipip_neo_001": 4, "ipip_neo_031": 2}' --pretty
    python engine/inference.py --dump-params IPIP-NEO --out /tmp/params.json
"""
from __future__ import annotations

import argparse
import base64
import json
import math
import os
import sys
from dataclasses import dataclass, field
from typing import Any

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from engine.instrument_schema import (  # noqa: E402
    Dimension, Instrument, Item, License, ResponseFormat, Rubric,
)
from engine.scoring import score_instrument  # noqa: E402

TOL = 1e-9
#: 近奇异时加在题间相关矩阵对角线上的岭（只在 `np.linalg.solve` 失败后启用）。
RIDGE = 1e-6


# --------------------------------------------------------------------------- 载入
def _load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def find_instrument_json(code: str) -> tuple[str, dict] | tuple[None, None]:
    """按 `instrument` 字段在 `data/instruments/` 里找量表包（与 build 脚本同法）。"""
    d = os.path.join(ROOT, "data", "instruments")
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json") or fn == "catalog.json":
            continue
        p = os.path.join(d, fn)
        try:
            obj = _load_json(p)
        except Exception:                                            # noqa: BLE001
            continue
        if obj.get("instrument") == code:
            return p, obj
    return None, None


def inference_json(code: str) -> str:
    return os.path.join(ROOT, "data", "inference", code.lower() + ".json")


def tri_index(a: int, b: int) -> int:
    """`pairB64` 的展平下标（a=max(i,j)、b=min(i,j)，**1-based 题序**）。"""
    if a < b:
        a, b = b, a
    return (a - 1) * (a - 2) // 2 + (b - 1)


def pair_matrix(pair_b64: str, n: int, orders: list[str],
                order_index: dict[str, int]) -> np.ndarray:
    """解码 `pairB64` → n×n 相关矩阵。

    `pairB64` 的下标是**量表包题序**（= id 末尾数字），而 `orders` 是量表包
    `items[].order` 的顺序；两者在本项目的两份量表包里一致（已核对），这里仍然
    用 `order_index` 显式映射，不假设它们相等。
    """
    raw = np.frombuffer(base64.b64decode(pair_b64), dtype="<f4")
    m = np.eye(n, dtype=np.float64)
    for iid, i in order_index.items():
        for jid, j in order_index.items():
            if i >= j:
                continue
            v = float(raw[tri_index(i + 1, j + 1)])
            m[i, j] = m[j, i] = v
    return m


def _instrument_object(d: dict) -> Instrument:
    """把量表包 JSON 适配成 `engine/instrument_schema.Instrument`（只读适配）。"""
    items = [Item(order=x["order"], id=x["id"], text=x["text"],
                  dimensions=x.get("dimensions", []), key=x.get("key", 1),
                  source_code=x.get("source_code"))
             for x in d["items"]]
    rub = {k: Rubric(id=k, label=v.get("label", k), aggregation=v["aggregation"],
                     scope=v.get("scope", "items"), of=v["of"])
           for k, v in d["scoring"].items()}
    dims = [Dimension(id=x["id"], name=x["name"], level=x.get("level", 1),
                      parent=x.get("parent"), children=x.get("children", []),
                      items=x.get("items") or [],
                      reverse_keyed=x.get("reverse_keyed", []),
                      alpha=x.get("alpha"))
            for x in d["dimensions"]]
    rf = (d.get("structure") or {}).get("response_format")
    return Instrument(
        instrument=d["instrument"], display_name=d["display_name"],
        citation=d["citation"],
        license=License(kind=d["license"]["kind"], text=d["license"]["text"],
                        evidence=d["license"]["evidence"],
                        redistribution=d["license"]["redistribution"]),
        structure=d["structure"], items=items, dimensions=dims, scoring=rub,
        item_order_source=d.get("item_order_source", ""),
        response_format=ResponseFormat(**rf) if rf else None)


def _interp(xs: list[float], ys: list[float], x: float) -> float:
    """线性插值（xs 单调增；超出范围时取端点，不外推）。"""
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for k in range(1, len(xs)):
        if x <= xs[k]:
            t = (x - xs[k - 1]) / (xs[k] - xs[k - 1]) if xs[k] != xs[k - 1] else 0.0
            return ys[k - 1] + t * (ys[k] - ys[k - 1])
    return ys[-1]


# --------------------------------------------------------------------------- 参数
@dataclass
class InferenceModel:
    """一个量表的题级预测参数（只读）。"""

    code: str
    instrument_json: str
    inference_json: str
    instrument: Instrument
    raw_instrument: dict
    pairs: np.ndarray
    order_index: dict[str, int]                 # item id → 0-based 内部下标
    ids: list[str]                              # 内部下标 → item id
    dim_items: dict[str, list[str]]             # 维度 id → 题项 id（量表声明顺序）
    dim_name: dict[str, str]
    dim_agg: dict[str, str]                     # 该维度的官方聚合（mean/sum/…）
    item_dim_corr: dict[str, dict[str, float]]
    dim_ceiling: dict[str, float]
    ceiling_ratio: float
    item_mean: dict[str, float]
    item_sd: dict[str, float]
    stats_source: str
    ceiling_ratio_source: str = "data/inference/<code>.json 的 ceiling_ratio"
    dim_ceiling_cross: dict[str, float] = field(default_factory=dict)
    ceiling_ratio_cross: float = 0.90
    inf_meta: dict[str, Any] = field(default_factory=dict)

    # -- 便捷访问 -----------------------------------------------------------
    def idx(self, item_id: str) -> int:
        return self.order_index[item_id]

    @property
    def dims(self) -> list[str]:
        return list(self.dim_items)

    def dim_scale(self, dim: str) -> float:
        """官方分 → 该量纲的除数：mean 聚合除题数，sum 不减。"""
        return float(len(self.dim_items[dim])) if self.dim_agg[dim] == "mean" else 1.0

    def ceiling_need(self, dim: str) -> float | None:
        c = self.dim_ceiling.get(dim)
        return None if c is None else c * self.ceiling_ratio

    # -- 预测 ---------------------------------------------------------------
    def predict(self, responses: dict[str, int]) -> dict[str, Any]:
        return predict(self, responses)

    def params_for_js(self) -> dict[str, Any]:
        """导出 JS 侧需要的全部参数（`ui/lib/inference.js` 与之一一对应）。"""
        return {
            "instrument": self.code,
            "ids": self.ids,
            "pairB64_source_note": "同 data/inference/<code>.json",
            "dim_items": self.dim_items,
            "dim_name": self.dim_name,
            "dim_agg": self.dim_agg,
            "item_dim_corr": self.item_dim_corr,
            "dim_ceiling": self.dim_ceiling,
            "dim_ceiling_cross": self.dim_ceiling_cross,
            "ceiling_ratio": self.ceiling_ratio,
            "ceiling_ratio_cross": self.ceiling_ratio_cross,
            "ceiling_ratio_source": self.ceiling_ratio_source,
            "item_mean": self.item_mean,
            "item_sd": self.item_sd,
            "stats_source": self.stats_source,
            "key_of_item": {it.id: it.key for it in self.instrument.items},
            "response_min": (self.instrument.response_format.min
                             if self.instrument.response_format else 0),
            "response_max": (self.instrument.response_format.max
                             if self.instrument.response_format else 1),
            "dim_ceiling_note": (self.inf_meta.get("ceiling_note") or ""),
        }


def _norm_name(s: str) -> str:
    return "".join(ch for ch in (s or "").lower() if ch.isalnum())


def _resolve_item_stats(code: str, instrument: dict,
                        dim_items: dict[str, list[str]],
                        dim_name: dict[str, str],
                        pairs: np.ndarray, order_index: dict[str, int]
                        ) -> tuple[dict[str, float], dict[str, float], str]:
    """解析每题的均值/SD（**计分方向**上的）。

    优先级（每一级都写明出处；拿不到就降级并如实标注）：
      ① `data/item-norms.json`（IPIP-NEO；N=20,974，与 pairB64 同源）
      ② `data/item-norms-<code>.json`（PID-5；两份公开原始作答分样本算再合并，
         task-17 补的数据产物，与 pairB64 同源）
      ③ facet 均值/SD + 面内等 SD 假设：`data/norms/pid-5.json` 的 T 分表
         （T = 50 + 10z ⇒ 均值 = T=50 处的原始分、SD = T=60 与 T=50 之差）
      ④ 兜底：均值 0、SD 1，并标 `assumed_unit_sd`

    ⚠️ ③ 是**整表采用或整表不用**：只要有 facet 在常模表里对不上名（PID-5 的
    `scales` 键是缩写：`attention_seek` / `percept_dysreg` / …），就整表降级，
    不混用两种量纲——混用会让同一份报告里的预测尺度不一致。
    """
    ids = {it["id"] for it in instrument["items"]}
    # ① / ② 显式题级统计（先查量表自己的，再查通用的那份）
    #   文件名候选：`item-norms-pid-5.json` / `item-norms-pid5.json` 都认
    #   （代码里有连字符、文件名里常没有——实测就栽在这一个字符上）。
    norm = "".join(ch for ch in code.lower() if ch.isalnum())
    for path, label, note in (
        (os.path.join(ROOT, "data", f"item-norms-{code.lower()}.json"),
         f"data/item-norms-{code.lower()}.json",
         "题级均值/SD（分样本算再按组内合并；与 pairB64 同源）"),
        (os.path.join(ROOT, "data", f"item-norms-{norm}.json"),
         f"data/item-norms-{norm}.json",
         "题级均值/SD（分样本算再按组内合并；与 pairB64 同源）"),
        (os.path.join(ROOT, "data", "item-norms.json"),
         "data/item-norms.json", "题级均值/SD，N=20,974，与 pairB64 同源"),
    ):
        if not os.path.exists(path):
            continue
        d = _load_json(path)
        items = d.get("items") or {}
        by_id = {}
        for v in items.values():
            if isinstance(v, dict) and "id" in v and "mean" in v and "sd" in v:
                by_id[v["id"]] = (float(v["mean"]), float(v["sd"]))
        if ids and ids.issubset(set(by_id)):
            mean = {i: by_id[i][0] for i in ids}
            sd = {i: by_id[i][1] for i in ids}
            return mean, sd, f"{label}（{note}）"

    # ③ facet 均值/SD → 面内等 SD（整表采用；名对不上就整表降级）
    if code == "PID-5":
        p = os.path.join(ROOT, "data", "norms", "pid-5.json")
        if os.path.exists(p):
            norms = _load_json(p)
            scales = norms.get("scales") or {}
            names = {k: _norm_name(v) for k, v in (norms.get("scale_names") or {}).items()}
            mapping: dict[str, str] = {}
            for dim in dim_items:
                nd = _norm_name(dim_name.get(dim, dim))
                hits = [k for k, nv in names.items() if nv and
                        (nd.startswith(nv) or nv.startswith(nd))]
                if not hits:
                    continue
                hits.sort(key=lambda k: -len(names[k]))       # 最长前缀优先
                mapping[dim] = hits[0]
            if len(mapping) == len(dim_items):
                mean, sd = {}, {}
                for dim, item_ids in dim_items.items():
                    cells = (scales[mapping[dim]].get("cells") or {}).get("f [18,35)") or {}
                    pts = sorted((float(v["T"]), float(k)) for k, v in cells.items()
                                 if isinstance(v, dict) and "T" in v and not v.get("extrap"))
                    if len(pts) < 3:
                        break
                    ts = [a for a, _ in pts]
                    vs = [b for _, b in pts]
                    mu = _interp(ts, vs, 50.0)
                    sigma_mean = _interp(ts, vs, 60.0) - mu
                    n = len(item_ids)
                    idx = [order_index[i] for i in item_ids]
                    s_sum = math.sqrt(max(float(pairs[np.ix_(idx, idx)].sum()), TOL))
                    sigma_sum = sigma_mean * n
                    s_item = sigma_sum / s_sum if s_sum else sigma_mean
                    for i in item_ids:
                        mean[i], sd[i] = mu, s_item
                else:
                    return mean, sd, (
                        "data/norms/pid-5.json（facet T 分表插值出均值/SD，"
                        "按面内等 SD 折算到题级；Zimmermann 等 2026）")

    # ③ 兜底
    mean, sd = {}, {}
    for item_ids in dim_items.values():
        for i in item_ids:
            mean.setdefault(i, 0.0)
            sd.setdefault(i, 1.0)
    if code == "IPIP-NEO":
        why = "assumed_unit_sd"
    else:
        why = "assumed_unit_sd（常模表按名对不上或不可用）"
    return mean, sd, why


_MODEL_CACHE: dict[str, InferenceModel] = {}


def load(code: str, *, use_cache: bool = True) -> InferenceModel:
    """载入一个量表的预测参数。"""
    if use_cache and code in _MODEL_CACHE:
        return _MODEL_CACHE[code]
    ipath, inst = find_instrument_json(code)
    if ipath is None:
        raise FileNotFoundError(f"data/instruments/ 里没有量表 {code}")
    jpath = inference_json(code)
    if not os.path.exists(jpath):
        raise FileNotFoundError(
            f"没有题级推断参数 {jpath}；该量表不能用本模型预测（不猜）")
    inf = _load_json(jpath)

    items = sorted(inst["items"], key=lambda x: x["order"])
    ids = [it["id"] for it in items]
    order_index = {iid: k for k, iid in enumerate(ids)}
    n = len(ids)
    pairs = pair_matrix(inf["pairB64"], n, ids, order_index)

    dim_items, dim_name, dim_agg = {}, {}, {}
    scoring = inst.get("scoring") or {}
    for d in inst["dimensions"]:
        rid = d["id"]
        rub = scoring.get(rid)
        if rub is None or rub.get("scope", "items") != "items":
            continue                                   # 域（scope=dimensions）不做题级预测
        of = list(rub.get("of") or d.get("items") or [])
        if not of:
            continue
        dim_items[rid] = of
        dim_name[rid] = d.get("name", rid)
        dim_agg[rid] = rub.get("aggregation", "mean")

    item_dim_corr = {iid: {k: float(v) for k, v in row.items()}
                     for iid, row in (inf.get("item_dim_corr") or {}).items()}
    dim_ceiling = {k: float(v) for k, v in (inf.get("dim_ceiling") or {}).items()}
    # 跨维度上限（界面「已达上限的 X%」的**分母**）：整卷答满时的 conf_r。
    dim_ceiling_cross = {k: float(v) for k, v in (inf.get("dim_ceiling_cross") or {}).items()}
    # 门控比例：优先取重标过的 `ceiling_ratio_cross`（跨维度判据专用），
    # 没有就用原来的 `ceiling_ratio`。两者的标定依据见
    # research/conf-r-cross-calibration.md 与 data/inference/*.json 的 ceiling_note。
    if "ceiling_ratio_cross" in inf:
        ratio = float(inf["ceiling_ratio_cross"])
        ratio_src = "data/inference/<code>.json 的 ceiling_ratio_cross（跨维度判据重标值）"
    else:
        ratio = float(inf.get("ceiling_ratio", 0.90))
        ratio_src = "data/inference/<code>.json 的 ceiling_ratio（未重标）"

    item_mean, item_sd, stats_src = _resolve_item_stats(
        code, inst, dim_items, dim_name, pairs, order_index)
    model = InferenceModel(
        code=code, instrument_json=ipath, inference_json=jpath,
        instrument=_instrument_object(inst), raw_instrument=inst,
        pairs=pairs, order_index=order_index, ids=ids,
        dim_items=dim_items, dim_name=dim_name, dim_agg=dim_agg,
        item_dim_corr=item_dim_corr, dim_ceiling=dim_ceiling, ceiling_ratio=ratio,
        dim_ceiling_cross=dim_ceiling_cross, ceiling_ratio_cross=ratio,
        item_mean=item_mean, item_sd=item_sd, stats_source=stats_src,
        ceiling_ratio_source=ratio_src,
        inf_meta={k: inf.get(k) for k in
                  ("item_dim_corr_kind", "ceiling_note", "min_own_removed",
                   "level", "quality")})
    if use_cache:
        _MODEL_CACHE[code] = model
    return model


# --------------------------------------------------------------------------- 预测
def _solve(a: np.ndarray, b: np.ndarray) -> np.ndarray | None:
    """解 A x = b；近奇异时加岭重试（与 JS 侧同一策略）。"""
    try:
        return np.linalg.solve(a, b)
    except np.linalg.LinAlgError:
        try:
            d = a + RIDGE * np.eye(a.shape[0])
            return np.linalg.solve(d, b)
        except np.linalg.LinAlgError:
            return None


def code_responses(model: InferenceModel, responses: dict[str, int]) -> dict[str, int]:
    """把原始作答按计分键转成**计分值**（反向题 (min+max)−v）。

    模型的一切输入（`pairB64`、`item_dim_corr`、题级均值/SD）都是在**计分方向**上
    算的；所以这一步必须做，而且必须与 `engine/scoring.py` 用同一条规则。
    """
    rf = model.instrument.response_format
    lo = rf.min if rf else 0
    hi = rf.max if rf else 1
    key = {it.id: it.key for it in model.instrument.items}
    out = {}
    for iid, v in responses.items():
        if iid not in key:
            raise KeyError(f"{model.code}: 作答里含量表外的题 {iid}")
        if not (lo <= v <= hi):
            raise ValueError(f"{model.code}: 题 {iid} 的作答 {v} 超出 {lo}..{hi}")
        out[iid] = v if key[iid] >= 0 else (lo + hi) - v
    return out


def dim_confidence(model: InferenceModel, dim: str,
                   coded: dict[str, int]) -> dict[str, Any]:
    """该维度此刻的**判据/可信度口径**置信度。

    用户指示：「**conf_r 计算可以借助别的维度，但当本维度未答题时，禁止展示**」。

    定义（corrected 精神的一般化）
    ------------------------------
        cᵢ = corr(xᵢ, T_f)                若 i 是**别的维度**的题（xᵢ 不在 T_f 里，
                                         不存在自解释，直接用普通相关）
        cᵢ = corr(xᵢ, T_f − xᵢ)          若 i 是**本维度已答**的题（去本题 = corrected，
                                         避免「自己那一道题」自解释）
        confidence_r = √(cᵀ Σ_AA⁻¹ c)     A = 全部已答题，Σ 为题间相关

    性质：
      · 只答本维度的题时，它与旧的 corrected 口径**逐值相同**（没有跨维度项）；
        所以 `dim_ceiling`（答满本维度、无跨维度）仍然是这套判据的锚点。
      · 答了别的维度时可以更高 —— 这就是「借助别的维度」，跨维度借用不再恒为 0。
      · **它不是 `r_total`**：`r_total` 把「已答的本维度题」当成**已知真实值**记进去，
        因此答满本维度时 `r_total=1`；本判据在任何情况下都不把已答项当已知，
        只问「这些已答内容能把该维度估到多准」。

    硬规则：本维度一道题都没答 → 返回 `status="NO_OWN_ITEM_ANSWERED"`、
    `confidence_r=None`（**不给数**，不是给 0）；调用方必须据此禁止展示。
    """
    own = model.dim_items[dim]
    a_own = [i for i in own if i in coded]
    if not a_own:
        return {"dimension": dim, "status": "NO_OWN_ITEM_ANSWERED",
                "confidence_r": None, "confidence_r_own_only": None,
                "cross_dim_borrow_gain": None, "n_own_answered": 0}

    answered = [i for i in model.ids if i in coded]      # 用全部已答题
    s = np.array([model.item_sd.get(i, 1.0) for i in own], dtype=np.float64)
    io = [model.idx(i) for i in own]
    cov = np.outer(s, s) * model.pairs[np.ix_(io, io)]
    sigma_t = math.sqrt(max(float(cov.sum()), TOL))

    own_set = set(own)
    own_pos = {iid: k for k, iid in enumerate(own)}
    c = np.empty(len(answered), dtype=np.float64)
    for k, iid in enumerate(answered):
        if iid in own_set:
            # 本维度已答：用 corrected（去本题）——与旧口径逐值一致
            c[k] = model.item_dim_corr.get(iid, {}).get(dim, 0.0)
        else:
            # 别的维度的题：本题不在 T_f 里，用与完整分的普通相关
            row = model.pairs[model.idx(iid)]
            c[k] = float(sum(s[j] * row[model.idx(own[j])]
                             for j in range(len(own)))) / sigma_t

    ia = [model.idx(i) for i in answered]
    xb = _solve(model.pairs[np.ix_(ia, ia)], c)
    r_all = math.sqrt(max(0.0, min(1.0, float(c @ xb)))) if xb is not None else 0.0

    # 旧口径（只用本维度已答、corrected）——**只作对照，不用于门控**
    ia_own = [model.idx(i) for i in a_own]
    b = np.array([model.item_dim_corr.get(i, {}).get(dim, 0.0) for i in a_own],
                 dtype=np.float64)
    xb_own = _solve(model.pairs[np.ix_(ia_own, ia_own)], b)
    r_own = (math.sqrt(max(0.0, min(1.0, float(b @ xb_own))))
             if xb_own is not None else 0.0)
    return {
        "dimension": dim,
        "status": "OK",
        "confidence_r": r_all,
        "confidence_r_own_only": r_own,
        "cross_dim_borrow_gain": r_all - r_own,
        "n_own_answered": len(a_own),
        "n_pred": len(answered),
    }


def predict(model: InferenceModel, responses: dict[str, int]) -> dict[str, Any]:
    """对**每个维度**给出官方分（缺失不猜）与推断预测（`inferred: true`）。"""
    coded = code_responses(model, responses)
    answered = [i for i in model.ids if i in coded]
    out: dict[str, Any] = {
        "instrument": model.code,
        "model": {
            "name": "conditional_expectation_linear",
            "formula": ("pred = T_known + Σ_{j∈U} μⱼ + σ_TU·cᵀΣ_AA⁻¹z_A；"
                        "confidence_r = √(cᵀΣ_AA⁻¹c)（判据口径：本维度已答的题用 "
                        "corrected（去本题），**别的维度**的已答题用与完整分的普通相关"
                        "——即「可以借助别的维度」；与 r_total 是两个量）"),
            "pair_source": "data/inference/%s.json 的 pairB64" % model.code.lower(),
            "item_dim_corr_kind": model.inf_meta.get("item_dim_corr_kind"),
            "item_stats_source": model.stats_source,
            "ceiling_ratio": model.ceiling_ratio,
            "ceiling_ratio_source": model.ceiling_ratio_source,
            "ceiling_display_denominator": (
                "ceiling_cross（跨维度上限＝整卷答满时的 conf_r）；"
                "判据仍用 ceiling × ceiling_ratio，两者不要混"),
            "hard_rule": ("本维度一道题都没答 → 不展示置信度与预测"
                          "（NO_OWN_ITEM_ANSWERED）"),
        },
        "n_answered_total": len(coded),
        "official": {},
        "inferred": {},
        "layer_note": ("official 为量表声明口径的官方分（缺失不猜）；inferred 为本模型"
                       "预测，带 inferred=true，**不得与官方分混算**。"),
    }

    # ---- 官方分：复用 engine/scoring.py（缺失不猜） ----
    official = score_instrument(model.instrument, responses, require_complete=True)
    for dim in model.dims:
        row = official["dimensions"].get(dim)
        if row is None:
            continue
        complete = bool(row["complete"])
        out["official"][dim] = {
            "value": row["value"] if complete else None,
            "complete": complete,
            "n_answered": row["n_answered"],
            "n_items": row["n_items"],
            "aggregation": row["aggregation"],
            "blocker": None if complete else (
                f"官方分缺失不猜：{row['n_answered']}/{row['n_items']} 题已答"),
        }

    # ---- 推断：逐维度 ----
    for dim in model.dims:
        own = model.dim_items[dim]
        scale = model.dim_scale(dim)
        a_items = [i for i in own if i in coded]          # 已答的本维度题
        u_items = [i for i in own if i not in coded]      # 未答的本维度题
        ceil = model.dim_ceiling.get(dim)
        ceil_cross = model.dim_ceiling_cross.get(dim)
        need = model.ceiling_need(dim)
        block: dict[str, Any] = {
            "dimension": dim,
            "name": model.dim_name[dim],
            "inferred": True,
            "n_answered": len(coded),
            "n_answered_own": len(a_items),
            "n_items": len(own),
            "ceiling": ceil,
            "ceiling_cross": ceil_cross,
            "ceiling_ratio": model.ceiling_ratio,
            "ceiling_need": need,
            "aggregation": model.dim_agg[dim],
        }
        # ---- 硬规则：本维度一道题都没答 → 禁止展示置信度与预测 ----
        if not a_items:
            block.update({
                "status": "NO_DATA" if not coded else "NO_OWN_ITEM_ANSWERED",
                "display_allowed": False,
                "available": False,
                "predicted_score": None,
                "confidence_r": None, "r2": None,
                "r2_total": None, "confidence_r_total": None,
                "confidence_r_own_only": None,
                "cross_dim_borrow_gain": None,
                "ceiling_pct": None, "ceiling_pct_raw": None,
                "prediction_se": None,
                "known_own_sum": None, "predicted_unknown_sum": None,
                "predicted_unknown_shift": None, "sigma_unknown": None,
                "contributions": [], "top_contributions": [],
                "cross_dim_share_of_prediction": None,
                "reason": ("本维度一道题都没答：按用户硬规则**禁止展示**该维度的"
                           "置信度与预测（与其它维度答了多少、r_total 多高无关）"
                           if coded else "整卷尚未作答：无任何输入"),
            })
            out["inferred"][dim] = block
            continue

        # -- 判据口径 confidence_r：可借跨维度信息（本维度已答部分用 corrected）--
        display_ok = True                     # 到这里必然 ≥1 道本维度题已答
        conf = dim_confidence(model, dim, coded)
        conf_r = conf["confidence_r"]
        # -- 预测准确度口径：已知的本维度题 + BLUP 未答题 --
        known = float(sum(coded[i] for i in a_items))
        contributions: list[dict[str, Any]] = []
        if not u_items:
            pred_sum = known                       # 答满：预测 == 官方分（精确）
            r2_total, sigma_sum, sigma_u = 1.0, 0.0, 0.0
            pred_u_sum, pred_u_shift = 0.0, 0.0
        else:
            s = np.array([model.item_sd.get(i, 1.0) for i in own], dtype=np.float64)
            mu = np.array([model.item_mean.get(i, 0.0) for i in own], dtype=np.float64)
            io = [model.idx(i) for i in own]
            sub = model.pairs[np.ix_(io, io)]
            cov = np.outer(s, s) * sub                     # 原始单位协方差
            pos = {iid: k for k, iid in enumerate(own)}
            ku = [pos[i] for i in u_items]
            sigma_u = math.sqrt(max(float(cov[np.ix_(ku, ku)].sum()), TOL))
            # c：每个已答题（全量表范围）与 T_U 的相关
            c_list, a_all = [], answered
            for iid in a_all:
                row = model.pairs[model.idx(iid)]
                num = float(sum(s[k] * row[model.idx(own[k])] for k in ku))
                c_list.append(num / sigma_u)
            c = np.array(c_list, dtype=np.float64)
            ia_all = [model.idx(i) for i in a_all]
            m_aa = model.pairs[np.ix_(ia_all, ia_all)]
            beta = _solve(m_aa, c)
            if beta is None:                               # 保底：只用本维度已答题
                ia = [model.idx(i) for i in a_items]
                m_aa = model.pairs[np.ix_(ia, ia)]
                c2 = np.array([c[a_all.index(i)] for i in a_items])
                beta = _solve(m_aa, c2)
                if beta is None:
                    beta = np.zeros(len(a_items))
                a_all, c = a_items, c2
            z = np.array([(coded[i] - model.item_mean.get(i, 0.0))
                          / (model.item_sd.get(i, 1.0) or 1.0) for i in a_all],
                         dtype=np.float64)
            pred_u_sum = float(mu[ku].sum()) + sigma_u * float(beta @ z)
            pred_sum = known + pred_u_sum
            pred_u_shift = sigma_u * float(beta @ z)      # 由「答了什么」带来的位移
            r2_tu = max(0.0, min(1.0, float(c @ beta)))
            pos_u = [pos[i] for i in u_items]
            sigma_sum = math.sqrt(max(float(cov.sum()), TOL))
            var_u = sigma_u ** 2 * (1.0 - r2_tu)
            r2_total = max(0.0, min(1.0, 1.0 - var_u / (sigma_sum ** 2)))
            # 可解释性：每个已答题对 T_U 预测的贡献（原始单位）
            for iid, w in zip(a_all, beta):
                contrib = float(w) * float(
                    (coded[iid] - model.item_mean.get(iid, 0.0))
                    / (model.item_sd.get(iid, 1.0) or 1.0)) * sigma_u
                contributions.append({
                    "item": iid,
                    "kind": "own" if iid in set(own) else "cross",
                    "dimension_of_item": model.raw_instrument["items"][
                        model.idx(iid)].get("dimensions", []),
                    "coded_value": coded[iid],
                    "weight": float(w),
                    "contribution": contrib,
                })
            contributions.sort(key=lambda x: -abs(x["contribution"]))

        total_abs = sum(abs(x["contribution"]) for x in contributions)
        for x in contributions:
            x["share"] = (abs(x["contribution"]) / total_abs) if total_abs else 0.0
        cross_abs = sum(abs(x["contribution"]) for x in contributions
                        if x["kind"] == "cross")
        predicted = pred_sum / scale
        se_sum = math.sqrt(max(0.0, (sigma_sum ** 2) * (1.0 - r2_total)))
        block.update({
            "status": "OK",
            "display_allowed": True,
            "predicted_score": predicted,
            "confidence_r": conf_r,
            "confidence_r_own_only": conf["confidence_r_own_only"],
            "cross_dim_borrow_gain": conf["cross_dim_borrow_gain"],
            # 界面「已达上限的 X%」：分母用**跨维度上限**（否则跨维度借用会 >100%）
            "ceiling_pct_raw": (conf_r / ceil_cross) if ceil_cross else None,
            "ceiling_pct": (max(0.0, min(1.0, conf_r / ceil_cross))
                            if ceil_cross else None),
            "r2": conf_r ** 2,
            "r2_total": r2_total,
            "confidence_r_total": math.sqrt(r2_total),
            "prediction_se": se_sum / scale,
            # 门槛 = 判据口径 ≥ dim_ceiling × ratio（dim_ceiling 仍以「答满本维度、
            # 无跨维度」为锚点；跨维度的增益体现在 conf_r 里，见 calibration 报告）
            "available": bool(display_ok and need is not None and conf_r >= need),
            "known_own_sum": known,
            "predicted_unknown_sum": pred_u_sum if u_items else 0.0,
            "predicted_unknown_shift": pred_u_shift if u_items else 0.0,
            "sigma_unknown": sigma_u if u_items else 0.0,
            "contributions": contributions,
            "top_contributions": contributions[:5],
            "cross_dim_share_of_prediction": (cross_abs / total_abs) if total_abs else 0.0,
            "note": ("答满该维度全部题：预测 = 官方分（精确）" if not u_items else
                     "已知部分已计入；未答部分由已答题的条件期望给出"),
        })
        out["inferred"][dim] = block
    return out


def predict_code(code: str, responses: dict[str, int]) -> dict[str, Any]:
    return predict(load(code), responses)


# --------------------------------------------------------------------------- CLI
def _fmt(v: Any, nd: int = 4) -> str:
    if isinstance(v, float):
        return f"{v:.{nd}f}"
    return str(v)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="题级线性预测 + 置信度")
    ap.add_argument("--instrument", required=True,
                    help="量表代码，如 IPIP-NEO / PID-5")
    ap.add_argument("--responses-json", default=None,
                    help='作答 JSON：{"item_id": value, ...}')
    ap.add_argument("--responses-file", default=None)
    ap.add_argument("--dim", default=None, help="只看某一个维度")
    ap.add_argument("--dump-params", action="store_true",
                    help="导出 JS 侧参数（配 --out）")
    ap.add_argument("--out", default=None)
    ap.add_argument("--pretty", action="store_true")
    args = ap.parse_args(argv)

    model = load(args.instrument)
    if args.dump_params:
        payload = {"params": model.params_for_js(),
                   "pairB64": _load_json(model.inference_json)["pairB64"]}
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        if args.out:
            with open(args.out, "w", encoding="utf-8") as fh:
                fh.write(text)
            print(f"参数 → {args.out}（{len(text)} B）")
        else:
            print(text)
        return 0

    if args.responses_file:
        # utf-8-sig：Windows 上记事本/PowerShell 写出的 JSON 常带 BOM，
        # 用 utf-8 读会直接 JSONDecodeError（实测踩过）。
        with open(args.responses_file, encoding="utf-8-sig") as fh:
            responses = json.load(fh)
    elif args.responses_json:
        responses = json.loads(args.responses_json)
    else:
        print("需要 --responses-json 或 --responses-file（或用 --dump-params）",
              file=sys.stderr)
        return 2

    result = predict_code(args.instrument, responses)
    if args.pretty:
        dims = result["inferred"] if not args.dim else {args.dim: result["inferred"][args.dim]}
        print(f"量表 {result['instrument']}｜已答 {result['n_answered_total']} 题")
        print(f"题级参数来源：{result['model']['item_stats_source']}")
        print(f"{'维度':<22}{'官方分':>8}{'预测':>8}{'r(判据)':>9}"
              f"{'r_total':>9}{'可给':>6}{'跨维借用':>9}")
        for k, b in dims.items():
            off = result["official"].get(k, {}).get("value")
            print(f"{b['name'][:20]:<22}"
                  f"{('—' if off is None else _fmt(off, 3)):>8}"
                  f"{('—' if b['predicted_score'] is None else _fmt(b['predicted_score'], 3)):>8}"
                  f"{_fmt(b['confidence_r'], 3):>9}{_fmt(b['confidence_r_total'], 3):>9}"
                  f"{('是' if b['available'] else '否'):>6}"
                  f"{_fmt(b['borrowed_from_cross_dim'] * 100, 1) + '%':>9}")
    else:
        print(json.dumps(result, ensure_ascii=False,
                         indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    sys.exit(main())
