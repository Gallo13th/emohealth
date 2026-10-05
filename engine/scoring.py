"""与量表无关的计分器：只吃「量表包」（Instrument）与作答，输出维度分。

为什么不能复用 ``engine/assess.py``
===================================
``assess.py`` 里 ``score_facet`` 是这么取题目的::

    items = [i for i in ref.canonical["items"] if i["facet"] == facet]

也就是「一个量表、30 个 facet、facet 名硬编码在 ``content/facet_definitions.py``」。
要装下 PID-5（5 域 × 25 facet）、CAT-PD（33 维）、DASS-21（3 维总分）这类
层级与聚合方式都不同的量表，计分必须**数据驱动**：规则写在量表包里，
引擎只负责按规则算。这个模块就是那个引擎。

三条与项目硬规则对应的行为
==========================
1. **按声明聚合**：`mean` 取均分、`sum` 取总分、`weighted_sum` 按权重。
   ``rubric.of`` 指向维度时表示「先算子维度再聚合」——PID-5 的域分正是这种形态，
   与「把域下所有题项直接求均分」结果不同（各 facet 题数不等时尤其明显），
   所以必须由量表声明，不能让实现去猜。
2. **反向题按量表的 key 处理**：``key == -1`` 时用 ``(min + max) - v`` 翻转
   （5 级量表即 6 − v），而不是写死 6。
3. **缺失不猜**：某维度只要有题未答就把它标成 ``complete=False`` 并给出已完成题数，
   而不是用已答部分充当全量。答题中不显示分值的约束在这里也顺带满足——
   本模块只被「出结果」的路径调用，不参与作答过程。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# 允许的作答值在量表包里声明；这里只做边界检查，避免把 1..5 写死。

MISSING = -1          # 未作答哨兵（区别于任何合法作答值）


@dataclass
class DimensionScore:
    id: str
    name: str
    value: float | None
    n_answered: int
    n_items: int
    complete: bool
    aggregation: str
    detail: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "name": self.name,
            "value": None if self.value is None else round(self.value, 4),
            "n_answered": self.n_answered, "n_items": self.n_items,
            "complete": self.complete, "aggregation": self.aggregation,
        }


class MissingResponse(KeyError):
    """作答里出现量表之外的题号。"""


def _code_value(value: int, key: int, lo: int, hi: int) -> int:
    """按计分方向把原始作答转成计分值。反向题用 ``(lo + hi) - v`` 翻转，
    这样 1..5 与 0..3 两种量表都能正确翻转（不是写死 6 − v）。"""
    if key >= 0:
        return value
    return (lo + hi) - value


def score_dimension(instrument: Any, dim_id: str, responses: dict[str, int]) -> DimensionScore:
    """算一个维度的分。``instrument`` 是 ``instrument_schema.Instrument``。"""
    dim = next((d for d in instrument.dimensions if d.id == dim_id), None)
    if dim is None:
        raise KeyError(f"量表 {instrument.instrument} 没有维度 {dim_id}")
    rubric = instrument.scoring.get(dim_id)
    if rubric is None:
        raise KeyError(f"维度 {dim_id} 没有计分规则——量表包不完整")

    rf = instrument.response_format
    lo = rf.min if rf else 0
    hi = rf.max if rf else 1
    item_map = {it.id: it for it in instrument.items}

    if rubric.scope == "dimensions":
        # 嵌套：先算子维度，再按声明聚合。
        # ⚠️ 语义决定：**不完全的子维度不参与上级聚合**（否则「3 个 facet 满分 +
        #    1 个 facet 只答了一题」会算出一个偏低的域分，看起来像结果，其实不是）。
        #    只要有一个子维度不完全，上级就标 complete=False，调用方必须自己决定展示与否。
        subs = [score_dimension(instrument, s, responses) for s in rubric.of]
        done = [s for s in subs if s.complete]
        vals = [s.value for s in done if s.value is not None]
        if rubric.aggregation in ("mean", "sum"):
            value = (sum(vals) / len(vals)) if (vals and rubric.aggregation == "mean") \
                else (sum(vals) if vals else None)
        elif rubric.aggregation == "weighted_sum":
            value = sum(vals) if vals else None
        elif rubric.aggregation == "none":
            value = None
        else:
            raise ValueError(f"{dim_id}: 嵌套维度不支持聚合 {rubric.aggregation!r}")
        return DimensionScore(
            id=dim.id, name=dim.name, value=value,
            n_answered=sum(s.n_answered for s in subs),
            n_items=sum(s.n_items for s in subs),
            complete=bool(subs) and all(s.complete for s in subs),
            aggregation=rubric.aggregation,
            detail=[s.to_dict() for s in subs])

    # 叶子：直接算题项
    coded: list[float] = []
    detail: list[dict[str, Any]] = []
    for iid in rubric.of:
        it = item_map.get(iid)
        if it is None:
            raise MissingResponse(f"{dim_id} 引用了不存在的题项 {iid}")
        raw = responses.get(iid)
        if raw is None:
            detail.append({"item": iid, "answered": False})
            continue
        if not (lo <= raw <= hi):
            raise ValueError(f"题项 {iid} 的作答 {raw} 超出 {lo}..{hi}")
        c = _code_value(raw, it.key, lo, hi)
        coded.append(c)
        detail.append({"item": iid, "answered": True, "raw": raw,
                       "key": it.key, "coded": c})

    n_items = len(rubric.of)
    n_ans = len(coded)
    if not coded:
        value = None
    elif rubric.aggregation == "sum":
        value = float(sum(coded))
    elif rubric.aggregation == "max":
        # DSM-5-TR Level 1 的域分口径：**域内最高分**（手册 Instructions to
        # Clinicians 原文），不是求和也不是均分。
        value = float(max(coded))
    elif rubric.aggregation == "weighted_sum":
        value = float(sum(coded))
    elif rubric.aggregation == "mean":
        value = sum(coded) / len(coded)
    elif rubric.aggregation == "count_true":
        value = float(sum(1 for c in coded if c > 0))
    elif rubric.aggregation == "lookup":
        value = None                      # 查表型（如某些筛查）留给上层
    else:
        raise ValueError(f"{dim_id}: 未知聚合 {rubric.aggregation!r}")

    return DimensionScore(
        id=dim.id, name=dim.name, value=value,
        n_answered=n_ans, n_items=n_items, complete=(n_ans == n_items),
        aggregation=rubric.aggregation, detail=detail)


def score_instrument(instrument: Any, responses: dict[str, int], *,
                     require_complete: bool = True) -> dict[str, Any]:
    """算整套量表。

    ``require_complete=True`` 时，任何未答满的维度都会让该维度 ``value`` 为
    **已答部分的均值**但 ``complete=False``——调用方必须自己决定是否展示。
    这是刻意的：让「算了个数」和「这个数可信」在数据结构上就能分开。
    """
    unknown = set(responses) - {it.id for it in instrument.items}
    if unknown:
        raise MissingResponse(f"作答里含量表外的题号：{sorted(unknown)[:5]}")

    scores = {d.id: score_dimension(instrument, d.id, responses)
              for d in instrument.dimensions
              if not d.children}                       # 只算叶子；上级由嵌套规则覆盖
    # 补上「以上级维度为 scope 的规则」（PID-5 的域）
    for rid, rubric in instrument.scoring.items():
        if rubric.scope == "dimensions" and rid not in scores:
            scores[rid] = score_dimension(instrument, rid, responses)

    return {
        "instrument": instrument.instrument,
        "n_items": len(instrument.items),
        "n_answered": sum(1 for it in instrument.items if it.id in responses),
        "dimensions": {k: v.to_dict() for k, v in scores.items()},
        "incomplete": sorted(k for k, v in scores.items() if not v.complete),
    }


def validate_against_declaration(instrument: Any) -> list[str]:
    """独立检查：按量表**自己的声明**重算一遍题项归属，看与 rubric 是否自洽。

    这不是重复劳动——``rubric.of`` 与 ``dimension.items`` 是两处独立记录，
    两处口径漂移是这类项目最容易出的静默错误（原 D78/D96；见 `README.md`「已知的坑」）。
    """
    problems: list[str] = []
    for d in instrument.dimensions:
        if d.children:
            continue
        rubric = instrument.scoring.get(d.id)
        if rubric is None:
            problems.append(f"维度 {d.id} 没有计分规则")
            continue
        if set(rubric.of) != set(d.items):
            only_r = sorted(set(rubric.of) - set(d.items))
            only_d = sorted(set(d.items) - set(rubric.of))
            problems.append(
                f"维度 {d.id}: rubric.of 与 dimension.items 不一致"
                f"（只在 rubric: {only_r[:4]}；只在 dimension: {only_d[:4]}）")
    for rid, rubric in instrument.scoring.items():
        if not any(d.id == rid for d in instrument.dimensions):
            problems.append(f"计分规则 {rid} 没有对应维度")
    return problems
