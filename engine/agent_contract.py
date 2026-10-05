#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""陪伴 agent 的输入契约（`PLAN.md` §2.1、§2.5）。

**核心原则**：agent 不是新的结论来源。它拿到的是**已确定的结论 + 用户语境**，
交回的只能是**表达形式的变化**。

本模块只做一件事：**把引擎已确定的东西，整理成 agent 可以依赖、且能被自动校验的结构**。

三条设计要点：

1. **`grounded_in` 路径制。** agent 每一段文字都要声明它依据输入里的哪些路径。
   校验器检查路径是否真实存在——**这是「不得引入新论断」唯一可自动化的形式**。

2. **数字接地。** 正文里出现的每一个数字，都必须能在输入里找到。
   改写措辞可以，改分数不行。

3. **`notable_items` 是本项目独有的杠杆。** 我们为 300 道题逐题写了脚手架
   （承重词、常见误读、算什么不算什么）。agent 可以据此对**这个人答的这道题**
   给出澄清——「这题问的是 X 不是 Y」。这不是通用模型能编出来的，
   因为它需要逐题的作者级工作。

   ⚠️ 但措辞必须中性：说「这道题问的是 X」，**不说「你误读了这道题」**——
   后者是对这个人的揣测，我们没有证据。
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# ── 危机转介：命中任一条即必须出现在输出里
#
# ⚠️ 这是关键词表，必然有漏。本表**被自己的评测集打脸过一次**：
# S6 场景的用户原话是「最近一直觉得活着没什么意思，做什么都提不起劲」，
# 而初版表里没有任何一条能命中——也就是说走真实代码路径时危机转介根本不会触发。
# 现按「宁可多转介，不可漏转介」的原则扩表：漏转介的代价远大于多转介。
CRISIS_MARKERS = [
    # 明确的自伤/自杀意念
    "自杀", "自伤", "伤害自己", "想死", "不想活", "活不下去", "结束生命",
    "结束这一切", "想消失", "消失了更好", "没有我更好",
    # 活着无意义类表述（初版漏掉的正是这一类）
    "活着没意思", "活着没什么意思", "活着没有意思", "活着没劲",
    "生无可恋", "撑不下去", "熬不住",
    # 绝望类
    "绝望",
]

# 程度较轻、但值得在解读里提一句求助渠道的表述。
# 与 CRISIS_MARKERS 分开：这些不强制转介（否则「最近有点提不起劲」也会触发），
# 但产品可以选择性提示。**不参与 must_survive 判定。**
DISTRESS_MARKERS = [
    "提不起劲", "没什么意思", "情绪低落", "开心不起来", "没动力",
]

# ── 禁止出现在输出里的措辞（可测规则）
# 这些不是「风格建议」，是校验器会拦下来的硬规则。
FORBIDDEN_PATTERNS = [
    # 诊断
    (r"你(患|有|得了|属于).{0,6}(症|障碍|病)\b", "诊断式表述"),
    (r"(确诊|临床诊断|符合.{0,4}诊断标准)", "诊断式表述"),
    # 分型
    (r"(你是|属于).{0,4}(型人格|型|人格类型)", "分型式表述"),
    (r"(INTJ|INTP|ENTJ|ENTP|INFJ|INFP|ENFJ|ENFP|ISTJ|ISFJ|ESTJ|ESFJ|ISTP|ISFP|ESTP|ESFP)", "MBTI 类型"),
    # 过度确定
    (r"(一定|必然|肯定|毫无疑问)(是|会|说明)", "过度确定的推断"),
    (r"证明(了)?你", "把分数当证明"),
    # 越界建议
    (r"(建议|应该)(停药|加药|减药|服药|去看精神科)", "医疗建议"),
    (r"(你的|这是).{0,4}(心理疾病|精神疾病|精神病)", "疾病标签"),
]

# ── 输出必须包含的声明（由输入决定，逐条 id 追踪）
DISCLOSURE_KINDS = {
    "norm_sample": "参照人群的来源与局限",
    "does_not_measure": "这个分数不意味着什么",
    "content_caveat": "面向自身的内容局限",
    "quality_flag": "作答质量的协议偏离",
    "precision": "该面向当前的测量精度",
    "no_diagnosis": "本结果不构成诊断",
}


def _load(name: str) -> dict:
    with open(os.path.join(ROOT, "data", name), encoding="utf-8") as fh:
        return json.load(fh)


@dataclass
class Contract:
    """把一次会话整理成 agent 输入。"""
    session: object                       # engine.session.Session
    user_context: str = ""                # 用户自述的处境（可为空）
    knowledge_refs: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.s = self.session

    # ─────────────────────────────────────── 主体
    def build(self) -> dict:
        s = self.s
        unlock = s.unlock()
        prog = s.progress()
        results = s.results()

        facets = {}
        for f, u in sorted(unlock.items()):
            rec = _load_record(f)
            entry = {
                "facet": f,
                "name_zh": rec["identity"]["facet_name_zh"],
                "domain_zh": rec["identity"]["domain_zh"],
                "precision": {"k": u["k"], "of": u["total"], "r": u["r"],
                              "tier": u["tier"], "advice": u["advice"]},
                "showable": u["show_score"],
            }
            if u["show_score"] and s.mode == "classic":
                for row in results.get("profile", {}).get("rows", []):
                    if row["facet"] == f:
                        entry["score"] = {
                            "raw": row.get("raw_score"),
                            "band": row.get("band"),
                            "ci95": row.get("ci95"),
                            "sem": row.get("sem"),
                            "possible_range": row.get("possible_range"),
                        }
            entry["does_not_measure"] = rec["construct"]["does_not_measure"]
            entry["interpretation_caveats"] = (
                rec.get("evidence", {}) or {}).get("interpretation_caveats", [])
            facets[f] = entry

        payload = {
            "contract_version": "1.0",
            "mode": s.mode,
            "coverage": {
                "items_answered": prog["items_answered"],
                "items_total": prog["items_total"],
                "pct": prog["pct"],
                **({"scenes_complete": prog["scenes_complete"]} if s.mode == "scene" else
                   {"rounds_done": prog.get("rounds_done")}),
            },
            "facets": facets,
            "facets_showable": sorted(f for f, v in facets.items() if v["showable"]),
            "facets_withheld": sorted(f for f, v in facets.items() if not v["showable"]),
            "scene_results": results.get("scenes") or None,
            "notable_items": self._notable_items(),
            "quality_gate": self._quality(),
            "disclosures": self._disclosures(facets, results),
            "user_context": self.user_context,
            "knowledge_refs": self.knowledge_refs,
            "resources": self._resources(),
            "rules": RULES,
        }
        payload["disclosure_ids"] = [d["id"] for d in payload["disclosures"]]
        return payload

    # ─────────────────────────────────────── 值得澄清的题
    def _notable_items(self) -> list[dict]:
        """找出「答得极端」且「脚手架记录了常见误读」的题。

        这是本项目独有的杠杆：脚手架是逐题写的作者级工作，
        通用模型编不出来。但措辞必须中性——**说这题问什么，不说你误读了**。
        """
        s = self.s
        out = []
        for o, v in sorted(s.responses.items()):
            it = s.sref.items.get(o)
            if it is None:
                continue
            rec = _load_record(it["facet"])
            sc = next((x for x in rec["items"]
                       if x["administration_order"] == o), None)
            if not sc or sc["scaffolding"].get("status") == "PENDING":
                continue
            n = s.sref.norm(o)
            pct = n["option_pct"][v - 1] if it["key"] > 0 else n["option_pct"][5 - v]
            extreme = pct >= 90 or pct <= 10
            mis = sc["scaffolding"].get("common_misreadings") or []
            if not (extreme and mis):
                continue
            out.append({
                "order": o,
                "facet": it["facet"],
                "text_zh": it["text_zh"],
                "response": v,
                "percentile": pct,
                "asks": sc["scaffolding"]["asks"],
                "key_term": sc["scaffolding"]["key_term"],
                "common_misreadings": mis,
                "localization_note": sc["scaffolding"].get("localization_note"),
                "speak_neutrally": "说「这道题问的是 X」。**不要**说「你可能误读了这道题」——"
                                   "那是对这个人的揣测，我们没有证据。",
            })
        out.sort(key=lambda x: -abs(x["percentile"] - 50))
        return out[:12]

    # ─────────────────────────────────────── 质量门
    def _quality(self) -> dict:
        s = self.s
        if s.mode == "classic":
            by_id = {s.ref.by_order[o]["id"]: v for o, v in s.responses.items()}
            from .assess import quality_gate
            q = quality_gate(by_id, s.ref)
            return {"flags": q["flags"], "notes": q.get("notes", []),
                    "reliability_discount": q["reliability_discount"]}
        # 情景模式的作答顺序不是官方交错序，质量门的部分指标不适用
        return {"flags": [], "notes": ["情景模式的作答顺序与常模施测顺序不同，"
                                       "部分质量指标不适用"],
                "reliability_discount": 1.0}

    # ─────────────────────────────────────── 必须存活的声明
    def _disclosures(self, facets: dict, results: dict) -> list[dict]:
        out = [{
            "id": "norm_sample",
            "must_survive": True,
            "text": "参照人群为英国样本，非中国人群；源文件未提供样本量、招募方式与采集年份，"
                    "且分带边界来自对常模表的反推。",
            "why": "常模适用性直接决定分数能不能被当真",
        }, {
            "id": "no_diagnosis",
            "must_survive": True,
            "text": "本结果不构成任何诊断，也不能替代专业评估。",
            "why": "产品定位是自测陪伴，不是筛查工具",
        }]
        # 内容局限：逐个面向
        cavs, dnm = [], []
        for f, v in facets.items():
            if not v["showable"]:
                continue
            for c in v["interpretation_caveats"]:
                cavs.append({"facet": f, "text": c})
            for d in v["does_not_measure"]:
                dnm.append({"facet": f, "text": d})
        if cavs:
            out.append({"id": "content_caveat", "must_survive": True,
                        "items": cavs,
                        "text": "面向自身的内容局限（**不可删减**——删掉它们等于把"
                                "「我们对自己工具的批评」藏起来）",
                        "why": "PLAN.md §2.4：产品对自己的内容做溯源与批评标注"})
        if dnm:
            out.append({"id": "does_not_measure", "must_survive": True,
                        "items": dnm, "text": "这些分数不意味着什么"})
        # 精度：有多少面向还没到可展示
        withheld = [f for f, v in facets.items() if not v["showable"]]
        if withheld:
            out.append({"id": "precision", "must_survive": True,
                        "text": f"有 {len(withheld)} 个面向因题量不足尚未解锁，"
                                f"本次不对它们作任何表述。",
                        "why": "不能因为没数据就默认它「中等」——那是编造"})
        # 危机
        hit = [m for m in CRISIS_MARKERS if m in self.user_context]
        if hit:
            out.append({"id": "crisis_referral", "must_survive": True,
                        "text": "必须给出专业求助渠道，且**不做**危机干预本身。"
                                "可用的渠道见 resources 字段。",
                        "why": "PLAN.md §2.1：危机情形转介",
                        "matched": hit})
        return out

    # ─────────────────────────────────────── 求助资源
    def _resources(self) -> list[dict]:
        """危机时可供引用的求助渠道。

        ⚠️ **号码必须由产品团队从权威来源填入。** 本项目不自行编造热线号码——
        编一个数字的后果比不给号码严重得多。
        这里只给结构；`number` 为空时 agent 应描述渠道而不写具体号码。

        也是因为这条，C3 的数字接地不会拦住号码：号码在输入里，就是接地的。
        """
        if not any(m in self.user_context for m in CRISIS_MARKERS):
            return []
        return [{
            "kind": "hotline",
            "name_zh": "全国统一心理援助热线",
            "number": "",     # ← 由产品从国家卫生健康委等权威来源填入
            "available": "24 小时",
            "note": "号码需由产品从权威来源核实后填入；未填时不要写具体数字，"
                    "改为描述渠道（如「可拨打当地心理援助热线」）。",
        }, {
            "kind": "outpatient",
            "name_zh": "精神科／心理科门诊",
            "number": "",
            "available": "",
            "note": "综合医院精神科或专科医院均可。",
        }, {
            "kind": "emergency",
            "name_zh": "紧急情况",
            "number": "",
            "available": "24 小时",
            "note": "若有立即的伤害自己的风险，就近急诊。",
        }]

    # ─────────────────────────────────────── 提示词
    def prompt(self) -> str:
        return PROMPT_TEMPLATE.format(
            payload=json.dumps(self.build(), ensure_ascii=False, indent=1))


def _load_record(facet: str) -> dict:
    from .assess import _load_record as lr
    return lr(facet)


# ───────────────────────────────────────────────────────────── 规则（可测）
RULES = {
    "allowed": [
        "改写措辞、语气、详略、段落组织",
        "结合 user_context 里用户自述的处境来组织语言",
        "对 notable_items 里的题目给出**中性的题目澄清**（这题问的是什么）",
        "按需引用 knowledge_refs 里的文献，**必须标注出处**",
    ],
    "forbidden": [
        "引入输入中推导不出的新论断（由 grounded_in 路径制约束）",
        "改变任何数字：分数、常模位置、置信区间、精度、题量",
        "删减 disclosures 里的任何一条",
        "诊断、分型、贴标签",
        "由用户的分数反推量表之外的心理结论",
        "对 facets_withheld 里的面向作任何表述（包括「大概中等」）",
        "把分数说成「证明」了什么",
        "说你误读了自己的答案（可以说这题问的是什么）",
        "给出医疗建议（停药/加药/就诊安排）",
    ],
    "notable_items_scope": "notable_items 里的题目，**只能用来解释这道题问的是什么**。"
                           "不得由这一题反推这个人的特质水平——"
                           "「这表明你可能经常感到低落」是禁止的，"
                           "「这道题问的是情绪基调，不是对具体事件的反应」是可以的。"
                           "理由：单题与完整测量的相关最差只有 0.51。",
    "grounding": "每一段输出都要在 grounded_in 里列出它所依据的输入路径；"
                 "校验器会检查路径真实存在。这是「不得引入新论断」唯一可自动化的形式。",
    "numeric_grounding": "正文里出现的每个阿拉伯数字都必须能在输入里找到。"
                         "改写措辞可以，改分数不行。",
    "citation": "引用知识库时必须给出可核查的出处；无出处的断言不得出现。",
}


PROMPT_TEMPLATE = """你是 EmoHealth 结果解读的**表达层润色**助手。

你的输入是一份**已经确定的**测评结果。你的输出**只能是表达形式的变化**，
不得成为新的结论来源。

## 输入（这是你能依赖的全部事实）

```json
{payload}
```

## 你可以做

1. 改写措辞、语气、详略与段落组织，让解读**更贴合这位用户**
2. 结合 `user_context` 里用户自述的处境来组织语言
3. 对 `notable_items` 里的题目给出**中性的题目澄清**——说明这道题问的是什么、
   常见的另一种读法是什么。**这是本项目独有的资产**（300 道题逐题写了脚手架），
   请用足它
4. 引用 `knowledge_refs` 里的文献，**必须标注出处**

## 你绝不能做

1. 引入输入里推导不出的新论断
2. 改变任何数字
3. 删减 `disclosures` 里的任何一条
4. 诊断、分型、贴标签
5. 对 `facets_withheld` 里的面向作任何表述（包括「大概是中等水平」）
   —— 也**包括借 notable_items 里的单题去描述该面向**
6. 说用户「误读」了自己的答案——可以说「这道题问的是 X」，但不要揣测用户怎么想的
7. 给医疗建议

## 输出格式（严格 JSON，不要 markdown 代码块）

```json
{{
  "sections": [
    {{
      "heading": "小节标题",
      "text": "正文。所有数字必须与输入一致。",
      "grounded_in": ["facets.anxiety.score.raw", "notable_items.0.asks"],
      "citations": ["作者 (年份). 标题. 期刊."]
    }}
  ],
  "notable_items_surfaced": [12, 259],
  "disclosures_kept": ["norm_sample", "no_diagnosis", "content_caveat"],
  "refusals": [{{"asked": "用户问了什么", "why": "为什么超出边界"}}]
}}
```

`grounded_in` 用的是输入 JSON 的点分路径。校验器会逐条检查这些路径是否存在——
**写不存在的路径等同于引入新论断，会被拦下。**
"""


def build_contract(session, user_context: str = "",
                   knowledge_refs: list[dict] | None = None) -> dict:
    return Contract(session, user_context, knowledge_refs or []).build()


def build_prompt(session, user_context: str = "",
                 knowledge_refs: list[dict] | None = None) -> str:
    return Contract(session, user_context, knowledge_refs or []).prompt()
