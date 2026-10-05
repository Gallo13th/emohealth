# 量表档案字段规范（instrument-record schema）

> 版本 **v0.2** · 2026-09-29
> 配套文档：`PLAN.md`
> 状态：**已用真实内容撞击过一轮**（Phase 1，焦虑 facet 全切片），据 8 条撞击结果修订

---

## v0.2 变更记录

v0.1 是纸面设计。Phase 1 用 IPIP-NEO-300 焦虑 facet 的真实内容撞击后，做了 8 处修订：

| # | 变更 | 依据 |
|---|---|---|
| 1 | **新增 `administration_order` 与 `id` 的显式区分 + 强制一致性校验** | 切片初稿误把 id 当作补零的 order，10 个 id 全错。`.osd` 的 id 反映分组顺序（`ipip_neo_001–010` 全是焦虑题），施测顺序把它们打散到第 1/31/…/271 位 |
| 2 | **新增 `text_zh_source` 枚举** | 官方法定译本与项目自译的溯源强度不同，不可混同 |
| 3 | **新增显式 `PENDING` 状态 + `blocker` 字段** | v0.1 遇到取不到的值时，schema 会诱导填估算值。常模分带与 SEM 都曾处于此状态 |
| 4 | **`anchor_semantics` 从量表级降到 facet 级** | 五档阶梯是 facet 特有的（焦虑的"1"与自律的"1"含义不同），v0.1 放在 Group C（量表级施测协议）是错的 |
| 5 | **新增 `reverse_item_note`** | 反向题需额外脚手架；且「是否需要」本身是待认知访谈裁决的问题 |
| 6 | **新增 facet 级档案作为主要载体** | 实测中真正被填充的是 facet 级记录，不是整卷级。整卷级退化为容器 |
| 7 | **新增质量门区块** | 质量门已是 v1 招牌功能，需要自己的字段（含被否决的方法） |
| 8 | **新增源缺陷与源间不一致区块** | 实测遇到三类：机读源悬空引用、源表覆盖空洞、两个已发布文件互相矛盾 |

---

## 0. 这份 schema 的双重身份

1. **产品数据模型** — 驱动引擎的七个步骤（`PLAN.md` §2.6）
2. **调研交付物** — 调研产出直接填入这些字段

**每个字段必须驱动某一步引擎行为。** 无法驱动任何行为的字段应删除。

---

## 1. 层级结构（v0.2 新增）

```
instrument-record（整卷，容器）
├── identity / license / administration / scoring / quality_gate
└── facets[]（facet 级，内容主体）
    ├── construct（定义 + 边界 + 不测什么）
    ├── reference（常模 + SEM + 噪声底线）
    ├── anchor_semantics（facet 特有的五档阶梯）
    └── items[]（题目级）
        └── scaffolding（认知脚手架）
```

**实测结论**：真正承载内容的是 **facet 级**与 **item 级**。整卷级字段少而稳定。

---

## 2. 授权与身份（Group A）

决定"能不能给用户看题目"这个硬闸门。

| 字段 | 类型 | 必填 | 驱动 | 说明 |
|---|---|---|---|---|
| `instrument.id` | string | ✅ | — | 如 `ipip-neo-300` |
| `instrument.name.zh/.en` | string | ✅ | 知情简报 | |
| `instrument.citation` | string | ✅ | 陪伴引用 | 原始发表 |
| `license.status` | enum | ✅ | **档案可用性** | `public_domain` \| `free_attribution` \| `free_research_only` \| `commercial_restricted` \| `unknown` |
| `license.show_items` | bool | ✅ | **硬闸门** | 可否展示题目 |
| `license.translate` | bool | ✅ | **硬闸门** | 可否翻译 |
| `license.redistribute` | bool | ✅ | **硬闸门** | 可否再分发 |
| `license.evidence` | string | ✅ | 授权审计 | **授权声明原文引用 + URL**，不接受二手转述 |
| `sources.*` | object | ✅ | 溯源 | 每个来源文件的路径与角色 |

> `license.show_items = false` 时档案仍可用，但转为"构念描述 + 施测指引 + 官方获取路径"模式，不展示题目。

---

## 3. 施测协议（Group C，量表级）

| 字段 | 类型 | 必填 | 驱动 | 说明 |
|---|---|---|---|---|
| `administration.recall_window.value` | enum | ✅ | 施测 | `past_2_weeks` \| `typical` \| `lifetime` \| `other` |
| `administration.recall_window.instruction_quote` | string | ✅ | 施测 | 官方指导语**原文** |
| `administration.item_count` | int | ✅ | 知情简报 | |
| `administration.estimated_duration_min` | int | ✅ | 知情简报 | 须来自官方材料，非估计 |
| `administration.order_style` | enum | ✅ | **施测** | `interleaved_facet_cycle` \| `grouped_by_facet` \| `other` |
| `administration.response_format` | object | ✅ | 施测 | 点数与各档标签 |

> **`order_style` 是 v0.2 新增的关键字段。** 实测发现官方问卷用交错循环、机读源用按 facet 分组；
> 分组呈现会诱发反应定势、人为抬高内部一致性、增加直线作答。**必须显式记录并采用交错序。**
> 且该字段决定了质量门的 even-odd 能否按位置切分（见 §8）。

---

## 4. Facet 级（内容主体）

| 字段 | 类型 | 必填 | 驱动 | 说明 |
|---|---|---|---|---|
| `facets[].id` | string | ✅ | — | 如 `anxiety` |
| `facets[].code` | string | ✅ | 展示 | 如 `N1` |
| `facets[].name_zh/.name_en` | string | ✅ | 展示 | |
| `facets[].domain` | string | ✅ | 剖面 | 上位维度 |
| `facets[].construct.definition` | object | ✅ | 知情简报 | 含 `basis` 与 `provenance` |
| `facets[].construct.does_not_measure` | string[] | ✅ | **知情简报** | **必填，非可选** |
| `facets[].construct.boundaries[]` | object[] | ✅ | **消歧** | 与相邻 facet 的区分，每条含 `basis` |
| `facets[].evidence.known_critiques` | string[] | ✅ | 档案展示 | 研究记录：全部已知批评 |
| `facets[].evidence.interpretation_caveats` | string[] | ✅ | **解读** | **用户可见义务**：必须出现在解读中的内容局限。与 `known_critiques` 分离——前者是研究记录，后者是产品必须告知用户的东西 |
| `facets[].applicable_population` | string | ✅ | 路由 | |
| `facets[].inapplicable_population` | string[] | ✅ | 路由 | |
| `facets[].anchor_semantics` | object | ✅ | **施测** | **facet 特有的五档行为学阶梯**（v0.1 误置于量表级） |

---

## 5. 题目级（Group D）

| 字段 | 类型 | 必填 | 驱动 | 说明 |
|---|---|---|---|---|
| `items[].id` | string | ✅ | — | **不得可从 id 推断 order** |
| `items[].administration_order` | int | ✅ | **施测** | 在整卷中的呈现位置 |
| `items[].facet` | string | ✅ | 剖面 | |
| `items[].key` | enum | ✅ | 计分 | `+1` \| `-1` |
| `items[].text_en` | string | ✅ | 施测 | 施测用语 |
| `items[].text_master` | string | ❌ | 溯源 | 主表用语（若与施测用语不同） |
| `items[].text_zh` | string | ✅ | 施测 | |
| `items[].text_zh_source` | enum | ✅ | **溯源** | `mandarin_baseline` \| `project_translation` \| `cognitive_interview_verified` |
| `items[].scaffolding` | object | ✅ | **施测** | 见 §5.1 |
| `items[].irt_params` | object | ❌ | v2 CAT | 若已发表则存 |

### 5.1 `items[].scaffolding`

| 字段 | 类型 | 必填 | 对应认知阶段 |
|---|---|---|---|
| `asks` | string | ✅ | comprehension |
| `key_term.{term,sense_here,not_this}` | object | ✅ | comprehension |
| `common_misreadings[].{misreading,correction}` | object[] | ✅ | comprehension |
| `counts_as[]` | string[] | ✅ | judgment |
| `does_not_count_as[]` | string[] | ✅ | judgment |
| `edge_cases` | string\|null | ❌ | judgment |
| `retrieval_cue` | string | ❌ | retrieval |
| `reverse_item_note` | string | ❌ | **v0.2 新增**：反向题专用说明 |
| `provenance` | enum | ✅ | `published_definition` \| `editorial_clarification` \| `cognitive_interview_verified` |
| `evidence_anchor` | string | ✅ | 本澄清所依据的题目措辞或定义片段 |

> **`provenance` 必填。** v1 全部脚手架为 `editorial_clarification`；`cognitive_interview_verified`
> 在真正做认知访谈前不得使用。见 `PLAN.md` §2.4（ISPOR 第 7 步）。

---

## 6. 计分与参照（Group E）

| 字段 | 类型 | 必填 | 驱动 | 说明 |
|---|---|---|---|---|
| `facets[].scoring.algorithm` | string | ✅ | 计分 | |
| `facets[].scoring.reverse_items` | string[] | ✅ | 计分 | |
| `facets[].scoring.key_balance` | string | ✅ | 质量门 | 正/反向题数，影响 even-odd 与 longstring 解释 |
| `facets[].reference_system` | enum | ✅ | **解读** | `norm_percentile` \| `clinical_cutoff` \| `ipsative` \| `criterion` |
| `facets[].reliability.cronbach_alpha` | float | ✅ | 解读 | |
| `facets[].reliability.sem` | object | ✅ | **解读** | 见下 |
| `facets[].reliability.noise_floor` | object | ✅ | **解读** | 重测 r 与"小于多少算噪音" |
| `facets[].norms.bands_values` | object | ✅ | **解读** | 按人群分层的分带 |
| `facets[].norms.applicability_caveat` | string | ✅ | **解读** | 常模适用性警示 |

### 6.1 PENDING 状态（v0.2 新增，强制）

**任何取不到的值，必须显式标记，不得估算：**

```jsonc
{
  "value": null,
  "status": "PENDING" | "DERIVED" | "AVAILABLE",
  "blocker": "为什么取不到",
  "derivation": "若为 DERIVED，写明推导过程",
  "caveat": "已知不确定性"
}
```

**依据**：v0.1 遇到取不到的值时，schema 会诱导填一个看起来合理的数字。而常模分带填错是本项目
最严重的可能错误。实践中这条规则救过一次——UK 常模分带曾因解析不可靠而正确地被留为 `PENDING`。

`DERIVED` 用于**可推导但非源文件直给**的值。例：SEM 的 SD 由 σ 分带边界反推，
标注 `DERIVED` 并写明"存在 ±0.5 分舍入不确定性，不是源文件直接给出的 SD"。

---

## 7. 解读（Group F）

| 字段 | 类型 | 必填 | 驱动 |
|---|---|---|---|
| `facets[].interpretation_register` | enum | ✅ | 解读 |
| `facets[].bands[].behavioral_description` | string | ✅ | 解读 |
| `facets[].bands[].does_not_mean` | string[] | ✅ | **解读** |
| `escalation_policy` | object | ✅ | **解读** |

---

## 8. 质量门（v0.2 新增区块）

质量门是 v1 招牌功能，需要自己的字段。**必须同时记录采用与否决的方法**。

```jsonc
{
  "quality_gate": {
    "calibration_source": "Johnson (2005) 网络样本 N=20,993（archive/datasets/osf-johnson/validity/）",
    "indices": [
      {
        "name": "RNDCORR",
        "direction": "high_is_good",
        "distribution": { "p5": 0.13, "p50": 0.49, "p95": 0.77 },
        "source": "数据集自带（Goldberg 心理测量反义题）"
      }
    ],
    "ruled_out": [
      {
        "name": "evenodd_facet",
        "evidence": "与 RNDSPLIT 相关 +0.067、与 RNDCORR +0.056，近乎为零",
        "reason": "每 facet 仅 5 对题，逐人 r 标准误约 0.50，实测 sd 仅 0.16，信噪比不足",
        "verdict": "10 题/facet 下不可用"
      }
    ],
    "policy": "PLAN.md §2.5：多指标筛查 + 概率化降权，不预设单一硬阈值"
  }
}
```

### 8.1 反向题重编码（强制）

**数据源可能在施测时已重编码反向题**（IPIP-NEO-300 即是）。因此：

> **计算"连续相同作答"（longstring）前，必须先把反向题还原为原始作答类别。**
> 否则反向题会被误判为与相邻正向题一致，longstring 被系统性高估。
> 实测最大 longstring：还原后 14，未还原 17 —— 差 3 题，足以误伤正常作答者。

该约束应写入 `items[].key` 的消费方，而非依赖各实现自行记得。

---

## 9. 源缺陷与源间不一致（v0.2 新增区块）

实测遇到三类源问题。**必须记录 → 溯源 → 完整修复**（不要静默修补：任何改动都要留痕可追）。

```jsonc
{
  "source_defects": {
    "repaired": [
      { "defect": "机读源 text_key 'ipip_E11' 为悬空引用",
        "impact": "该题无正文",
        "repair": "由官方问卷第 70 题补齐",
        "cross_check": "两来源互为补全" }
    ],
    "recorded_not_repaired": [
      { "item": "Friendliness",
        "anomaly": "全部三个年龄段均缺 43 分——该分不属于任何带",
        "action": "如实记录；产品需处理无归属分数的落带" }
    ],
    "cross_source_discrepancy": [
      { "between": ["TRAITS 文件", "FACETS 文件"],
        "where": "CONSCIENTIOUSNESS / 14-17 的 High↔Average 边界（205–207 归属）",
        "verified": "已核对原始 XML，两边各自内部连续，属源数据分歧而非解析错误",
        "resolution": "统一采用 FACETS 文件，保证 facet 与维度同源",
        "required": "产品使用常模时必须声明采用哪一份" }
    ]
  }
}
```

---

## 10. 强制校验规则（v0.2 新增）

Phase 1 的实际教训：**肉眼不可见的错误会污染计分。** 以下校验必须自动化：

| # | 校验 | 理由 |
|---|---|---|
| V1 | `items[].id` ↔ `administration_order` ↔ `key` **三者一致** | 切片初稿 10 个 id 全错，肉眼完全看不出 |
| V2 | 题目数 = facet 数 × 每 facet 题数 | |
| V3 | `scoring.reverse_items` 与 `key == -1` 的集合一致 | |
| V4 | 每个 facet 的 `text_zh` 非空，且 `text_zh_source` 与实际来源相符 | |
| V5 | 脚手架必填字段齐全；`provenance` ∈ 允许枚举 | |
| V6 | 分带：带间不交、带序单调（**硬错误**）；覆盖空洞与空带（**源数据异常，记录而非修正**） | |
| V7 | 跨来源交叉比对（如 TRAITS ↔ FACETS-OVERALL） | 实测 73/75 吻合，是解析正确性的最强证据 |
| **V8** | `evidence.interpretation_caveats` 必须存在；若 `known_critiques` 非空而它为空则告警 | **研究记录不会自动变成用户告知**。实测引擎曾把 7 条批评一条都不输出。内容局限必须显式分诊到用户可见层，否则会静默丢失 |

> **V6 的区分至关重要**：带间重叠只可能是解析错误；覆盖空洞则是源表本身的特征。
> 把后者当错误去"修正"，等于伪造数据。

---

## 11. 待下一轮撞击的问题

1. **`escalation_policy` 尚未被真实内容填充**——Mode B 的量表才会真正用到它。
2. **`bands[]` 与 `norms.bands_values` 的关系**：前者是行为学描述，后者是分数区间，两者的键如何对齐？当前按带名（Very High/…）隐式对齐，未在 schema 中固定。
3. **`known_critiques` 的粒度**：构念级还是题目级？部分批评（反应偏差、faking）是跨量表的，可能需要独立于档案的**共性问题库**（v0.1 遗留问题，本轮未解决）。
4. **`anchor_semantics` 降到 facet 级后，量表级是否还需要一个通用锚点说明？** 当前认为不需要（官方指导语已覆盖），但未经用户检验。
5. **润色层的接口未定义**——`PLAN.md` §2.5 要求 agent 润色只作用于表达层，但 schema 中没有任何字段约束它。可能需要在 `bands[].behavioral_description` 上标注「可润色」与「不可改动」的部分。
