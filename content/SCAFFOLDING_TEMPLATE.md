# 题目级认知脚手架：模板与撰写规则

> 版本 v1.0（Phase 1 定稿）· 2026-09-29
> 上游：`../PLAN.md` §2.4、`../instrument-record.schema.md`

---

## 0. 这份模板要解决什么

`PLAN.md` §2.4：**"施测前给一段说明"无效——用户会直接跳过。** 真正缺的是**题目级的即时澄清**。

`PLAN.md` §2.4 给出了本模板的最大风险：**如果脚手架没有认知访谈支撑，它只是编辑意见，不是经验证的解读。**

因此本模板有两个目的：

1. 规定脚手架的**结构**（写什么字段）
2. 规定脚手架的**撰写纪律**（什么能写、什么不能写、来源如何标注）

---

## 1. 理论依据

脚手架不是随意写的提示语，它对应**调查作答的四个认知阶段**（Tourangeau, Rips & Rasinski 2000；归档见 `archive/literature/methodology/jcs2026_tourangeau-face-validity-cognitive-interviewing.pdf` 与 `bmc2024_eq5dy-children-response-model.pdf`）：

| 阶段 | 用户在此阶段会出什么错 | 对应脚手架字段 |
|---|---|---|
| **comprehension** 理解 | 把构念术语按日常语义理解 | `key_term`、`common_misreadings` |
| **retrieval** 提取 | 只回忆最近/最鲜明的经历 | `retrieval_cue`、facet 级 `recall_window` |
| **judgment** 判断 | 不知道模糊体验该归到哪一档 | `counts_as`、`does_not_count_as`、`edge_cases` |
| **response** 作答 | 锚点语义不明，或受社会赞许影响 | facet 级 `anchor_semantics` |

facet 级字段（同一 facet 的 10 题共享）承载 retrieval 与 response；
item 级字段承载 comprehension 与 judgment。

---

## 2. 撰写纪律（强制）

### 2.1 推导，不得创作

`PLAN.md` §2.4：脚手架**只做消歧，不做理论补充**。允许的推导来源，按优先级：

| 优先级 | 来源 | 允许写入 |
|---|---|---|
| 1 | **题目自身的措辞** | 该题的关键词在其字面语义下的精确定义 |
| 2 | **facet 的已发表定义**（Costa & McCrae 1992） | 构念边界 |
| 3 | **官方中文译本的用词**（IPIP-NEO-120 Mandarin） | 中文术语选择 |
| 4 | **facet 间区分度**（`newNEO_FacetsTable.htm` 的收敛/区分数据） | 与相邻 facet 的边界说明 |
| 5 | 编辑判断 | 仅在 1–4 无法覆盖时，且必须标注 |

**禁止**：
- 引入题目与 facet 定义之外的心理学理论
- 给出"这类人通常……"式的泛化人格描述（这是 Barnum 效应的入口）
- 暗示"期望答案"
- 在作答前显示常模分布或他人作答

### 2.2 不得暗示答案

`PLAN.md` §2.1 反 Barnum。脚手架的职责是让用户**准确报告自己**，不是让他们**报告得更像某个类型**。

❌ 错误写法：「如果你经常担心，选 4 或 5。」
✅ 正确写法：「这里问的是**担心的频率**，不是担心是否有正当理由——为真实问题担心也计入。」

### 2.3 每条脚手架必须带溯源标签

`PLAN.md` §2.4。取值：

| 标签 | 含义 |
|---|---|
| `published_definition` | 直接引自已发表的 facet 定义 |
| `editorial_clarification` | 基于题目措辞的编辑性澄清（**默认值，v1 绝大多数属此类**） |
| `cognitive_interview_verified` | 经认知访谈验证（**v1 尚无此项**） |

> **诚实要求**：v1 的脚手架**全部**是 `editorial_clarification`。除非真的做了认知访谈，否则不得使用第三个标签。这条与 `PLAN.md` §2.4 的 ISPOR 第 7 步（Cognitive Debriefing）对应——认知访谈计划在 Phase 2 执行。

---

## 3. 数据结构

### 3.1 facet 级（同 facet 全部题目共享）

```jsonc
{
  "facet_id": "anxiety",
  "facet_name_zh": "焦虑",
  "facet_name_en": "Anxiety",
  "domain": "neuroticism",

  // 构念定义：改述自 Costa & McCrae (1992) 的 facet 定义
  "construct_definition": {
    "text": "……",
    "source": "Costa, P. T., Jr., & McCrae, R. R. (1992). NEO-PI-R Professional Manual.",
    "provenance": "published_definition"
  },

  // 与相邻 facet 的边界：本产品最关键的消歧层
  "boundaries": [
    { "against_facet": "depression", "distinction": "……" },
    { "against_facet": "vulnerability", "distinction": "……" }
  ],

  // 回忆窗口（来自官方指导语）
  "recall_window": {
    "value": "typical",
    "instruction_quote": "Describe yourself as you generally are now, not as you wish to be in the future.",
    "source": "IPIP-NEO-300 官方问卷指导语"
  },

  // 锚点语义：本 facet 特有的五档含义（不是通用量表说明）
  "anchor_semantics": {
    "1": "……", "2": "……", "3": "……", "4": "……", "5": "……"
  },

  "provenance": "editorial_clarification"
}
```

### 3.2 item 级（每题一份）

```jsonc
{
  "order": 1,
  "id": "ipip_neo_001",
  "key": 1,
  "text_en": "Worry about things.",
  "text_zh": "……",
  "text_zh_source": "mandarin_baseline | project_translation",

  "scaffolding": {
    // comprehension
    "asks": "这一题问的是什么（一句话，不含评价）",
    "key_term": {
      "term": "Worry",
      "sense_here": "该词在此题中的精确含义",
      "not_this": "它在日常语义中常被误当成什么"
    },
    "common_misreadings": [
      { "misreading": "……", "correction": "……" }
    ],

    // judgment
    "counts_as":   ["……"],
    "does_not_count_as": ["……"],
    "edge_cases": "……",

    // 仅在题目需要时出现
    "retrieval_cue": "……",

    // 本地化说明：**中文语境下该题特有的读法风险**（D25）
    // 与 common_misreadings 的区别：后者是「任何语言下都可能有的误读」，
    // 前者是「中文读者因语言/文化而额外会有的读法」。无则写 null。
    "localization_note": "……",

    "provenance": "editorial_clarification",
    "evidence_anchor": "本澄清所依据的题目措辞或定义片段"
  }
}
```

---

## 4. 撰写规则细则

### 4.1 `asks` —— 一句话，描述题面在问什么

- 必须能在**不引入构念术语**的情况下读懂
- 不得包含评价（"过度地"、"不健康地"）
- 长度 ≤ 30 字

### 4.2 `key_term` —— 本题的承重词

挑出**唯一一个**决定构念归属的词或短语。多数题目是动词或程度副词。

例（焦虑 facet 的第 1 题 "Worry about things."）：
- 承重词是 **Worry**，不是 "things"
- `sense_here`：反复的、难以停止的思虑
- `not_this`：日常语中的"关心/在意"（如"我关心家人的健康"）

### 4.3 `common_misreadings` —— 每条必须给出修正

只列误读而不给修正是无效的（用户会卡住）。建议每题 1–3 条，优先选择：

1. **日常语义 vs 构念语义**的落差（最高频）
2. **与相邻 facet 的混淆**
3. **频率 vs 强度**的混淆（"有时很强烈"算高还是低？）
4. **状态 vs 特质**的混淆（今天 vs 一贯）

### 4.4 `counts_as` / `does_not_count_as` —— judgment 阶段的核心

这两栏直接对应"我卡在 2 和 3 之间"。写法要求：

- 用**可观察的行为或体验**描述，不用抽象词
- `does_not_count_as` 必须包含**看似符合但实际不符合**的情形（这是它存在的理由）
- 两者不得重复表述同一件事

### 4.5 `edge_cases` —— 仅在边界确实模糊时写

若某题不存在真实边界争议，**留空比硬写更好**。硬写的边界案例会变成新的误导。

### 4.6 `localization_note` —— 中文语境特有的读法风险

**这是本模板最容易被低估的字段。** 它记录的不是「翻译对不对」，而是
**「中文读者会不会按另一种意思去理解同一个词」**。

已有的实例（全部来自真实撰写）：

| 题目 | 中文题面 | 本地化风险 |
|---|---|---|
| cooperation #169 | 喜欢和别人比试 | 中文「比试」偏**竞技、切磋**（中性甚至正面），而英文 `a good fight` 偏**对抗性争辩** |
| modesty #114 | 很少自夸 | 含英文习语 `toot my own horn`，**11 类错误中的「习语」类** |
| modesty #84 | 觉得自己是个普通人 | 中文说自己「普通」常是**客套**，本题要求按内心定位作答 |
| emotionality #163 | 很少动感情 | 中文「动感情」易被读成**恋爱语境**的「动心」 |
| cooperation #19 | 容易满足 | 中文易读成「知足常乐」的生活态度，而本题问**交涉时的让步门槛** |

**判定标准**：如果一句话在中文里会让人想到题目本意之外的东西，就该写进这个字段。

### 4.7 `anchor_semantics` —— facet 特有，不是通用说明

通用写法（❌）：「1 = 非常不准确，5 = 非常准确」——官方指导语已说，重复无益。

facet 特有写法（✅）：说明**本构念在五档上的行为学阶梯**。以焦虑为例：

| 档 | 含义 |
|---|---|
| 1 | 即使事情悬而未决，也很少反复想；能轻易放下 |
| 2 | 偶有担心，但不占据注意力 |
| 3 | 会为一些事担心，通常在事情解决后停止 |
| 4 | 经常担心，且不容易停止 |
| 5 | 几乎持续处于担心状态，难以转移 |

---

## 5. 与施测流程的接口

| 脚手架字段 | 在 UI 中的位置 | 触发方式 |
|---|---|---|
| facet `construct_definition` | 知情简报（施测前） | 自动展示 |
| facet `recall_window` | 知情简报 + 每页页脚 | 自动展示 |
| facet `anchor_semantics` | 首次进入该 facet 时 | 自动展示一次 |
| facet `boundaries` | 知情简报（可折叠） | 用户展开 |
| item `asks` | **题下常驻一行** | 自动展示 |
| item `key_term` / `common_misreadings` | 题目展开层 | 用户点击"这题什么意思" |
| item `counts_as` / `does_not_count_as` | 题目展开层 | 同上 |
| item `edge_cases` | 题目展开层（默认折叠） | 用户二次展开 |

> **设计约束**：`asks` 常驻，其余按需。理由见 `PLAN.md` §2.1——整卷说明会被跳过，
> 但**一行**题目级澄清的阅读成本足够低。

---

## 6. 待 Phase 2 认知访谈校准的问题

记录本模板的已知不确定处，交由真实认知访谈裁决：

1. `asks` 常驻一行是否会造成**作答加速**（用户只读澄清不读原题）？
2. `common_misreadings` 的**最优条数**是多少？过多是否反而引入用户原本没有的困惑？
3. `anchor_semantics` 的五档阶梯由我们拟定，**是否与用户的真实心理刻度一致**？——这需要认知访谈中的"并发出声思维"验证。
4. 反向计分题（key = −1）是否需要**额外的脚手架**？反向题的误读率在文献中被认为更高，但本模板尚未区别对待。
5. `boundaries` 的相邻 facet 选择依据是 `newNEO_FacetsTable.htm` 的**相关矩阵**还是**理论邻近**？两者给出的邻接关系可能不同。

---

## 7. 附：本模板的溯源状态

| 项 | 状态 |
|---|---|
| 四阶段模型依据 | ✅ 已归档（Tourangeau 四阶段经 JCS 2026 / BMC 2024 引述） |
| ISPOR 第 7 步（认知访谈）对应关系 | ✅ 已归档（`methodology/ispor2005_tca-guidelines.pdf`） |
| facet 定义来源 | ⚠️ Costa & McCrae (1992) 手册为商业出版物，**未归档**；定义以改述形式引用并标注出处 |
| 中文术语基准 | ✅ 官方便携译本（`data/ipip-neo-120-mandarin.json`），覆盖全部 30 facet |
| 认知访谈验证 | ❌ **未做**。v1 全部脚手架为 `editorial_clarification` |

---

## 7b. 翻译政策：偏移不可避免时怎么办（D27）

有些题目**无论怎么翻译都会偏移**——尤其是英文习语（`toot my own horn`）、
中文没有对应词的词（`binge`）、以及中英强度不对等的词（`seek danger`）。

**政策**（三步，缺一不可）：

1. 选一个**相对最好**的译法
2. **括号中写入英文原文**
3. 在补充说明里写清**真实含义与对应的语境/情境**

**成品示例**：

| 项 | 内容 |
|---|---|
| 覆盖后题面 | `主动接过主导权（Take charge）` |
| 命中类型 | 语义偏移（A6 语境依存近义词） |
| 补充说明 | 原意是**在需要有人拍板时主动接过指挥权**。官方译本「承担责任」偏向 take responsibility（承担后果），丢了「掌权、主导」这一核心义。**情境：团队没人决定方向时，你会不会站出来说「那就这样办」。** |

**溯源要求**：若被覆盖的是**官方法定译本**，原译必须保留在 `text_zh_official_ref`
字段中，不得丢失——这是 `PLAN.md` §2.4 在翻译层的落实。

**已收录**：`content/translation_overrides.py`（12 条）。校验规则 **V4b** 强制三项齐备。

---

## 8. 自译与脚手架的自查表（D24）

`research/phase2_cognitive_interview_availability.md` 的调研结论：**认知访谈数据拿不到**，
但 McDowall & Daouk (2013) 提供了一个**含普通话**的 11 类错误编码框架，可直接用于自查。

该框架把语义等值问题分为两类共 11 种错误。**其中两类与脚手架直接相关**：

### 8.1 优先落地的两类

| 错误类型 | 是什么 | 对应脚手架字段 |
|---|---|---|
| **A6 语境依存近义词** | 两个词在日常语中都表同一概念，但适用语境不同。论文原例：**「写作风格」与「工作作风」** 都表 style | `key_term.not_this` |
| **B5 强度不同** | 译词在目标语中比源语**更重或更轻**。论文原例：阿拉伯语 "discouraged" 的直译更接近**抑郁**而非沮丧 | `key_term.sense_here` + `common_misreadings` |

**为什么是这两类**：它们**不改变题目"问什么"的表象，却改变作答者的实际理解或分数分布**。
B5 尤其危险——它破坏与常模的对应关系（分带是按原始英文版的分布算出来的）。

### 8.2 完整自查清单（自译 180 题时逐条过）

**A. 语言等值（6 类）**

1. 已有现成译法却未采用
2. 词或句在语法上不等值
3. 其他语法错误
4. 措辞生硬
5. 增词或漏词
6. **语境依存近义词** ← 优先

**B. 内涵等值（5 类）**

1. 多义词误译
2. 复合词处理不当
3. 目标语言中不存在的词
4. 习语
5. **强度不同** ← 优先

### 8.3 记录要求

自查命中的错误类型**应写入该题的 `provenance` 说明**，而非默默改掉。
理由与 `PLAN.md` §2.4 一致：**产品对自己的内容做溯源标注**——
"这题改过、因为「强度不同」"本身就是要保留的信息。

### 8.4 仍然不得使用的标签

> 自查**不是**认知访谈。即使 11 类全部过检，脚手架仍只能是 `editorial_clarification`。
> `cognitive_interview_verified` 在真正做完出声思维访谈前不得使用。

若日后自行执行访谈，方法论已备齐（本文档 §1 + 上述框架 + 已归档的 ISPOR 十步、
ITC 2017、EORTC 2017、Willis 指南）。**缺的不是方法，是人**——建议推迟到 v1 上线后。
