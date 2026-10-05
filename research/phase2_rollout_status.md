# Phase 2 铺量状态

> 更新：2026-09-29
> 上游：`PLAN.md` §3、`instrument-record.schema.md`

---

## 0. 一句话状态

**✅ 全部完成：30 个 facet、300 题，中文 100% 覆盖，题目级脚手架 300 / 300。**

---

## 1. 已完成

| 层 | 状态 |
|---|---|
| 整卷结构 | 300 题 / 30 facet / 148 反向题 |
| **中文题面** | **300 / 300**（官方译本 117 + 项目自译 183） |
| **facet 级内容** | **30 / 30**（定义、边界、五档锚点、批评、用户可见局限） |
| 常模分带 | 30 / 30 × 3 个年龄段 |
| SEM | 30 / 30（由分带反推，标 `DERIVED`） |
| 计分 | 30 / 30 |
| **题目级脚手架** | **✅ 300 / 300** |
| 引擎 | 30 / 30 可评分并产出解读 |
| 校验 | V1–V8 全部通过 |

### 1.1 中文题面的来源分层

| 来源 | 数量 | 溯源标签 |
|---|---|---|
| 官方法定译本（华东师大团队，120 题版） | **117** | `mandarin_baseline` |
| 本项目自译 | **183** | `project_translation` |
| 认知访谈验证 | **0** | — |

> ⚠️ 官方译本**未经 IPIP 验证**（IPIP 官方声明），自译部分**未经认知访谈**。
> `cognitive_interview_verified` 标签在真正做完访谈前不得使用
> （见 `research/phase2_cognitive_interview_availability.md`）。

**自译已执行 11 类错误自查**（McDowall & Daouk 2013，见 `SCAFFOLDING_TEMPLATE.md` §8），
其中「强度不同」（B5）在若干题目上做了特别处理并留痕：
`Feel desperate` → 「感到绝望」而非更重的「崩溃」；
`Have a sharp tongue` → 「说话很刻薄」而非更重的「恶毒」。

---

## 2. 铺量顺序由数据决定，不由题号决定

`tools/analyze/diagnose_items.py` 用 Johnson (2005) 的 **20,993 人网络样本**算了五项指标：

| 指标 | 含义 |
|---|---|
| `item_total_r` | 该题与所属 facet 其余 9 题之和的相关；低 = 可能在测别的东西或被误解 |
| `missing_rate` | 空答率；异常高 = 不愿答或看不懂 |
| `extreme_rate` | 选两端（1 或 5）的比例；过高 = 题目过于绝对 |
| `neutral_rate` | 选「中立」的比例；过高 = 题目模糊 |
| `priority_score` | 综合分，越高越该优先 |

> **这是代理指标，不能直接证明某题被误解**——它只提示哪里值得优先投入人力。
> 真正的判定仍需认知访谈。

### 2.1 facet 铺量顺序（前 8）

| 排名 | facet | 平均优先级 | 备注 |
|---|---|---|---|
| 1 | **活跃度** activitylevel | 1.682 | **与手工分析吻合**：「行为 vs 偏好」异质性 |
| 2 | 合作 cooperation | 1.278 | 含报复性表述，空答率异常 |
| 3 | 谦逊 modesty_humility | 1.162 | 含英文习语 `toot my own horn` |
| 4 | 价值开放 liberalism | 1.087 | 计分键 3正/7反 |
| 5 | 放纵 immoderation | 1.007 | |
| 6 | 情感丰富 emotionality | 0.980 | 含全库最低 `item_total_r` 的题 |
| 7 | 道德 morality | 0.953 | 计分键 2正/8反，社会赞许性 |
| 8 | 同情 sympathy | 0.943 | |

### 2.2 诊断发现的三个强信号

| 发现 | 数据 | 含义 |
|---|---|---|
| **`Get back at others`（#259）空答率 15.3%** | 全库均值约 0.4%，**是其 38 倍** | 不是「答不符合」，而是**拒答**。社会赞许性 |
| **`Like music`（#38）极端值 75.7%** | 几乎人人选 5 | **天花板效应**，该题几乎不区分人 |
| **`Enjoy examining myself and my life`（#103）`item_total_r` = .213** | 全库最低 | 很可能被读成「自省」而非本面向的「情绪觉察」 |

---

## 3. 脚手架完成情况

**300 题全部撰写完毕**，每 10 题对应一个 facet，按 `data/item-diagnostics.json` 的
优先级降序推进（活跃度 → 合作 → 谦逊 → 价值开放 → … → 抑郁）。

| 指标 | 数量 |
|---|---|
| 已撰脚手架 | **300 / 300** |
| 含**本地化说明**（`localization_note`） | **268 题（89%）** |
| 误读-修正对合计 | **594 条** |
| 标记了边界情形（`edge_cases`） | 65 题 |
| 仍为 PENDING | **0** |

**89% 的题目需要本地化说明**——这个比例本身就是结论：**中文读者对这批英文题目的
理解偏差是普遍现象，不是个别题的问题。**

### 3.1 撰写过程中发现的内容层面问题（已全部留痕）

按优先级推进的价值在于：它把内容问题按严重程度排了出来。实际发现：

| 类型 | 实例 |
|---|---|
| **翻译语义偏移** | `Take charge` 官方译为「承担责任」，丢了「接主导权」的核心义（**官方译本问题，未擅改**） |
| **天花板效应** | `Like music` 75.7% 选极端值，几乎不区分人 |
| **拒答** | `Get back at others` 空答率 15.3%（常态约 0.4%，38 倍） |
| **构念偏移** | `Have a rich vocabulary`（词汇量）实为语言能力，本面向测的是「享受思考」 |
| **混入其他成分** | `Have frequent mood swings`（情绪起伏）更接近情绪不稳而非抑郁 |
| **操作化过窄** | `Dislike new foods` 把「冒险」窄化为饮食开放度 |
| **题目冗余** | 冒险面向的 `Dislike changes` 与 `Don't like the idea of change` 近乎同义 |
| **习语风险** | `toot my own horn`、`a good fight` 等英文习语在中文无对应 |

**这些不是脚手架能修复的问题**——它们是题目内容本身的局限。脚手架能做的是
**在题目级如实告诉用户「这题的问法和别的题不太一样」**，而不是假装澄清一下就好了。

### 3.2 新增校验规则

本轮踩过两次同一个坑（`mis` 写成单字符串而非「误读-修正」对），已固化为 **V5b**：
`counts_as` / `does_not_count_as` 不得为空，`misreading` / `correction` 不得为空串。

## 4. 架构：自动化与人工撰写严格分离

```
data/                              ← 全自动，来自归档与计算
├── ipip-neo-300.json              id / order / key / 英文题面 / α
├── ipip-neo-120-mandarin.json     官方法定中文（117 题）
├── uk-norms.json                  分带常模
├── quality-gate-calibration.json  质量门标定（N=20,993）
├── antonym-pairs.json             反义题对（自推导，r=+0.846 对照）
└── item-diagnostics.json          ★ 题目优先级

content/                           ← 人工撰写
├── facet_definitions.py           30 个 facet 的面向级内容
├── translations.py                183 题自译
├── item_scaffolding.py            ★ 题目级脚手架（逐步补齐）
├── facets/                        生成的 30 个档案
└── SCAFFOLDING_TEMPLATE.md        撰写规范

tools/build/build_all_facets.py          ← 把两者组装成档案
tools/check/validate_records.py          ← V1–V8 强制校验
```

**为什么这样分**：如果脚手架由脚本批量生成，就会产出 300 段套话——
看似完整，实则把「专业性」这个卖点做成空的。
**未撰写的题目显式标记 `PENDING` 并写明 blocker**（`instrument-record.schema.md` §6.1），
宁可留空也不充数。

---

## 5. 继续铺量的方式

1. 取 `data/item-diagnostics.json` 的 `items_priority_order`
2. 按序在 `content/item_scaffolding.py` 中增加条目（格式见该文件头部注释）
3. 跑 `python3 tools/build/build_all_facets.py` 重新生成
4. 跑 `python3 tools/check/validate_records.py` 校验（V5 会检查缺字段与 provenance）

**每道题的必填字段**：`asks` / `key_term`（承重词、此题含义、日常误读）/
`mis`（误读与修正）/ `counts`（什么算）/ `notcount`（什么不算）/ `edge`（边界，可空）。

---

## 6. 与认知访谈的关系

用户已明确排序：**先把量表的使用标准化，再基于真实用户数据分析**，然后才做访谈。
这与 `research/phase2_cognitive_interview_availability.md` 的结论一致——
数据拿不到，但方法论与 11 类错误框架已备齐，**缺的是人，不是资料**。

**未来的访谈目标可以由产品数据挑选**：`item-diagnostics.json` 的指标
（尤其**「用户在哪一题点了『这题什么意思』」**这类真实交互数据）
正是挑选访谈题目的天然依据——这比凭空选更省，也更准。
