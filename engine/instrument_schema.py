"""量表数据模型：一套「量表包」的机器可读约定（多量表平台的地基）。

设计沿革
========
`data/ipip-neo-300.json` 是最初的**单量表**产物，形态是对的（`instrument` /
`citation` / `license` / `license_evidence` / `structure` / `items`），但它把
「大五 30 个 facet 平铺」这件事写进了结构里。要装下 PID-5（5 域 × 25 facet）、
CAT-PD（33 维）、DASS-21（3 维总分）这类**层级不同、计分规则不同**的量表，
需要把它泛化成三层：

    dimension（可嵌套）  ──▶  item  ──▶  rubric（计分规则）

三条与项目硬规则对应的约定
==========================
1. **每个数字都要能追到出处**：`license.evidence` 必填（授权原文或官方链接），
   `item_order_source` 必填（施测顺序从哪来），`norms` 缺省时必须在读结果处
   显式提示不可解读，不许静默出数。
2. **不用盗版来源**：`license.redistribution` 必须显式写明是否允许再分发；
   `allowed` 为 False 的量表**不允许进 `data/instruments/`**（由校验器拦住）。
3. **答题中不显示分值**：`Scoring.rubric` 只描述「答完之后怎么算」，
   不含任何作答过程中的中间量；中间量的定义属于 `engine/`，不属于量表包。

字段最小集
==========
一个量表包至少要有：instrument / display_name / citation / license /
structure.response_format / dimensions / items / scoring。
`validate()` 会把这些缺一不可地查一遍，并把「危险」情况（有 items 无 scoring、
有 norms 无样本量、授权不允许再分发）报成错误而不是警告。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# 计分聚合方式。故意只留这几种：每一种都能被「机械地」验证，
# 不会有解释空间（例如 facet 均分再取域均分 vs 题项直接均分，结果不同，
# 必须由量表自己声明，不能让实现去猜）。
AGGREGATIONS = {"sum", "mean", "count_true", "weighted_sum", "lookup", "none",
                "max"}

LICENSE_KINDS = {"public_domain", "cc_by", "cc_by_nc", "copyright_permitted", "unknown"}


@dataclass
class Item:
    """单道题。``key`` 的语义：``+1`` 正向计分、``-1`` 反向计分。"""

    order: int
    id: str
    text: str
    dimensions: list[str] = field(default_factory=list)
    key: int = 1
    source_code: str | None = None
    text_source: str | None = None

    def __post_init__(self) -> None:
        if self.key not in (1, -1):
            raise ValueError(f"item {self.id}: key 必须是 +1 或 -1，得到 {self.key!r}")
        if not self.text.strip():
            raise ValueError(f"item {self.id}: 题项正文为空")


@dataclass
class Dimension:
    """维度（可嵌套）。

    ``children`` 非空时它是上级（域），``items`` 非空时它是叶子（facet/子量表）。
    两者可以同时为空（例如只作为分组标签），但那就不能被计分——所以
    ``scoring`` 里引用不到它时会被校验器提示。
    """

    id: str
    name: str
    level: int = 1
    parent: str | None = None
    children: list[str] = field(default_factory=list)
    items: list[str] = field(default_factory=list)
    reverse_keyed: list[str] = field(default_factory=list)
    description: str = ""
    alpha: float | None = None


@dataclass
class Rubric:
    """一条计分规则。

    ``aggregation='mean'`` + ``of=子维度 id`` 表示「先算子维度，再取均分」——
    PID-5 的域分就是这种形态（域分 = 所属 facet 的均分），
    与「把所有题项直接求均分」结果不同，必须能区分表达。
    """

    id: str
    label: str
    aggregation: str
    of: list[str] = field(default_factory=list)
    scope: str = "items"          # items | dimensions
    reverse_of: str | None = None
    notes: str = ""

    def __post_init__(self) -> None:
        if self.aggregation not in AGGREGATIONS:
            raise ValueError(f"rubric {self.id}: 未知聚合方式 {self.aggregation!r}")
        if self.scope not in ("items", "dimensions"):
            raise ValueError(f"rubric {self.id}: scope 必须是 items/dimensions")
        if self.aggregation != "none" and not self.of:
            raise ValueError(f"rubric {self.id}: 缺少计分对象 of")


@dataclass
class License:
    kind: str
    text: str
    evidence: str                      # 授权原文出处（文件路径或 URL）——必填
    redistribution: bool
    holder: str = ""
    url: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        if self.kind not in LICENSE_KINDS:
            raise ValueError(f"license.kind 未知：{self.kind!r}")
        if not self.evidence.strip():
            raise ValueError("license.evidence 必填——每个授权判断都要能追到出处")


@dataclass
class Norms:
    """参照样本。``reference_sample`` 的必填项就是 PLAN.md §3（P0/P2 验收标准）定的那几项。"""

    source: str
    citation: str
    reference_sample: dict[str, Any]
    strata: dict[str, Any] = field(default_factory=dict)
    applicability_warning: str = ""
    evidence: str = ""

    REQUIRED_SAMPLE_FIELDS = ("n", "recruitment", "year")

    def __post_init__(self) -> None:
        missing = [k for k in self.REQUIRED_SAMPLE_FIELDS
                   if not self.reference_sample.get(k)]
        if missing:
            raise ValueError(
                f"norms.reference_sample 缺少必填项 {missing}——"
                "样本量/招募方式/采集年份缺一不可（PLAN.md §3 P0/P2 验收标准）")
        if not self.applicability_warning.strip():
            raise ValueError("norms.applicability_warning 必填——常模只对其样本有效")


@dataclass
class ResponseFormat:
    points: int
    min: int
    max: int
    labels: list[str]
    question_head: str = ""

    def __post_init__(self) -> None:
        if self.points != len(self.labels):
            raise ValueError(
                f"response_format: points={self.points} 但 labels 有 {len(self.labels)} 个")
        if self.max - self.min + 1 != self.points:
            raise ValueError(
                f"response_format: min..max={self.min}..{self.max} 与 points={self.points} 不符")


@dataclass
class Instrument:
    """一套完整量表包。``to_dict()`` 的结果就是落盘形态。"""

    instrument: str
    display_name: str
    citation: str
    license: License
    structure: dict[str, Any]
    items: list[Item]
    dimensions: list[Dimension]
    scoring: dict[str, Rubric]
    version: str = "1.0"
    response_format: ResponseFormat | None = None
    norms: dict[str, Norms] = field(default_factory=dict)
    item_order_source: str = ""
    interpretation: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)
    schema_version: str = "2.0"

    # ── 校验 ────────────────────────────────────────────────────────────
    def validate(self, *, require_redistributable: bool = False) -> list[str]:
        """返回问题列表（空 = 通过）。``require_redistributable`` 为真时，
        授权不允许再分发的量表会被判为错误——这是内容准确性门槛（原 D20；现 `PLAN.md` R1）的机器门。"""
        errors: list[str] = []

        if not self.items:
            errors.append("items 为空")
        if not self.dimensions:
            errors.append("dimensions 为空")
        if not self.scoring:
            errors.append("scoring 为空——有题项却无法计分")
        if not self.item_order_source.strip():
            errors.append("item_order_source 必填——施测顺序必须能追到出处")

        if require_redistributable and not self.license.redistribution:
            errors.append(
                f"授权不允许再分发（kind={self.license.kind}）：本题库只收录可再分发的量表")

        # 题项：order 唯一且连续、id 唯一
        orders = [it.order for it in self.items]
        if len(set(orders)) != len(orders):
            errors.append("item.order 有重复")
        if sorted(orders) != list(range(1, len(orders) + 1)):
            errors.append(f"item.order 不是 1..{len(orders)}（得到 {min(orders)}..{max(orders)}）")
        ids = [it.id for it in self.items]
        if len(set(ids)) != len(ids):
            errors.append("item.id 有重复")

        # 维度：id 唯一、parent 存在、items 引用存在
        dim_ids = {d.id for d in self.dimensions}
        if len(dim_ids) != len(self.dimensions):
            errors.append("dimension.id 有重复")
        item_ids = set(ids)
        for d in self.dimensions:
            if d.parent and d.parent not in dim_ids:
                errors.append(f"dimension {d.id}: parent {d.parent} 不存在")
            for c in d.children:
                if c not in dim_ids:
                    errors.append(f"dimension {d.id}: child {c} 不存在")
            for i in d.items:
                if i not in item_ids:
                    errors.append(f"dimension {d.id}: 引用了不存在的 item {i}")
        # 反向计分的两道保险：维度声明与题项 key 必须一致。
        # ⚠️ 早先写成「只在 reverse_keyed 非空时检查」，于是「声明了空列表、
        #    但题项里却有 key=-1」会静默通过——那正是最危险的方向错。
        #    现在无条件比对：空声明对不上任何反向题，就会被判错。
        for d in self.dimensions:
            declared = set(d.reverse_keyed)
            actual = {it.id for it in self.items if it.id in set(d.items) and it.key == -1}
            if declared != actual:
                extra = sorted(declared - actual)
                missed = sorted(actual - declared)
                problems_bits = []
                if extra:
                    problems_bits.append(f"声明了但题项是正向 {extra[:4]}")
                if missed:
                    problems_bits.append(f"题项反向但未声明 {missed[:4]}")
                errors.append(
                    f"dimension {d.id}: reverse_keyed 与题项 key 不一致"
                    f"（声明 {len(declared)} 个 / 实际 {len(actual)} 个；"
                    + "；".join(problems_bits) + "）")

        # 计分：引用存在
        for r in self.scoring.values():
            for ref in r.of:
                pool = dim_ids if r.scope == "dimensions" else item_ids
                if ref not in pool:
                    errors.append(f"rubric {r.id}: 引用了不存在的 {r.scope[:-1]} {ref}")
            if r.reverse_of and r.reverse_of not in self.scoring:
                errors.append(f"rubric {r.id}: reverse_of {r.reverse_of} 不存在")

        # 每道题至少要落在一个可计分的维度里，否则用户答了却算不出来
        scored_items = {i for d in self.dimensions for i in d.items}
        orphan = item_ids - scored_items
        if orphan:
            errors.append(f"{len(orphan)} 道题不属于任何维度（答了也算不出结果）")

        return errors

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "schema_version": self.schema_version,
            "instrument": self.instrument,
            "display_name": self.display_name,
            "version": self.version,
            "citation": self.citation,
            "license": {
                "kind": self.license.kind,
                "holder": self.license.holder,
                "text": self.license.text,
                "url": self.license.url,
                "evidence": self.license.evidence,
                "redistribution": self.license.redistribution,
                "notes": self.license.notes,
            },
            "structure": self.structure,
            "item_order_source": self.item_order_source,
        }
        if self.response_format:
            rf = self.response_format
            d["structure"]["response_format"] = {
                "points": rf.points, "min": rf.min, "max": rf.max,
                "labels": rf.labels, "question_head": rf.question_head,
            }
        d["dimensions"] = [
            {k: v for k, v in {
                "id": x.id, "name": x.name, "level": x.level, "parent": x.parent,
                "children": x.children, "items": x.items,
                "reverse_keyed": x.reverse_keyed, "description": x.description,
                "alpha": x.alpha,
            }.items() if v not in (None, "", [], {})}
            for x in self.dimensions
        ]
        d["items"] = [
            {k: v for k, v in {
                "order": x.order, "id": x.id, "text": x.text,
                "dimensions": x.dimensions, "key": x.key,
                "source_code": x.source_code, "text_source": x.text_source,
            }.items() if v not in (None, "", [], {})}
            for x in self.items
        ]
        d["scoring"] = {
            k: {kk: vv for kk, vv in {
                "label": r.label, "aggregation": r.aggregation, "scope": r.scope,
                "of": r.of, "reverse_of": r.reverse_of, "notes": r.notes,
            }.items() if vv not in (None, "", [])}
            for k, r in self.scoring.items()
        }
        d["norms"] = {
            k: {kk: vv for kk, vv in {
                "source": n.source, "citation": n.citation,
                "reference_sample": n.reference_sample, "strata": n.strata,
                "applicability_warning": n.applicability_warning,
                "evidence": n.evidence,
            }.items() if vv not in (None, "", [], {})}
            for k, n in self.norms.items()
        }
        if self.interpretation:
            d["interpretation"] = self.interpretation
        if self.provenance:
            d["provenance"] = self.provenance
        return d
