# Phase 2 前置调研：认知访谈数据是否可获取

> **D 编号说明**：文中 `D<编号>` 是 2026-10-04 之前决策账本的编号。账本已删除，其内容已并入 [`PLAN.md`](../PLAN.md) §2/§3；编号只作历史标识。

> 调研日期：2026-09-29
> 问题：是否存在可用于 IPIP-NEO-300 中文版的认知访谈数据？若无法获取则放弃该路线。

---

## 0. 结论

| 问题 | 答案 |
|---|---|
| 是否存在 **IPIP-NEO-300 的认知访谈数据**（任何语言）？ | ❌ **不存在** |
| 是否存在**可直接用于我们题目的**认知访谈数据集？ | ❌ **不存在** |
| 是否存在**可复用的认知访谈错误分类框架**（含中文）？ | ✅ **存在，且直接适用** |
| 因此 Phase 2 能否产出 `cognitive_interview_verified` 级脚手架？ | ❌ **不能**，除非自己执行访谈 |

**一句话**：**数据拿不到，框架拿得到。而框架恰恰是我们自己设计访谈时真正需要的东西。**

`PLAN.md` §2.4 与 `SCAFFOLDING_TEMPLATE.md` §2.3 的现状因此不变：
**v1/v2 的脚手架继续全部标记为 `editorial_clarification`**，该标签的纪律不放松。

---

## 1. 为什么数据不存在

认知访谈在方法上就**不是为数据共享设计的**：

| 特征 | 后果 |
|---|---|
| 样本极小（通常 5–30 人） | 不构成可复用数据集 |
| 定性资料（转录稿、观察笔记） | 难以去标识化，伦理审查通常不允许公开 |
| 高度仪器特异 | 只对**那一份问卷**的**那几个题目**有意义 |
| 为**该次适配**服务，事毕即归档 | 没有持续积累的公共语料库 |

检索了 Zenodo、OSF、Dataverse（含 Maastricht、Alberta、Brock 等机构节点）、
以及若干开放数据目录，**未发现任何面向人格量表题目的认知访谈原始数据集**。

### 1.1 最接近的两个，都不适用

**A. Global Flourishing Study 的 22 国认知访谈研究**
（*Quality & Quantity* 2025, 59:575–597）— 已归档
`archive/literature/methodology/gfs2025_cross-national-cognitive-interviews-22-countries.pdf`

- 规模：22 国、116 名受访者
- **但只覆盖 5 个 wellbeing 条目**，非人格量表，更非 IPIP-NEO
- 产出的是**主题归纳**（每个条目一个 overarching theme），不是可复用的题目级判定

**B. Mõttus, Pullmann & Allik (2006) Toward More Readable Big Five Personality Inventories**
（*European Journal of Psychological Assessment*）

- 这是**最接近我们需求**的一项：直接针对大五量表题目的可读性，且其成果我们已归档
  （`archive/ipip/site/EstonianRevisedIPIP-NEOFacets.htm` 与 `EstonianIPIP-NEOFacets.htm`）
- 他们为了让题目"尽可能简单易懂"，把每 facet 从 10 题减到 8 题并改写
- **但它不是认知访谈**：方法是可读性分析与心理测量筛选，不是出声思维
- 且是**爱沙尼亚语**语境

---

## 2. 拿得到的东西：一个直接适用的错误分类框架

**McDowall, A., & Daouk, L. (2013). Using Cognitive Interviewing for the Semantic Enhancement of
Multi-Lingual Versions of Personality Questionnaires. *Journal of Personality Assessment*,
95(4), 407–416.** — 已归档
`archive/literature/methodology/mcdowall2012_cognitive-interviewing-multilingual-personality.pdf`
（作者接受版，City Research Online 机构库开放获取，44 页）

### 2.1 为什么这篇直接适用

> 他们把一份**工作场景人格问卷**从英文适配到 **阿拉伯语、中文（普通话）、西班牙语**，
> 对 **12 名双语者**就 **136 个题目**做了认知访谈（占全部题目的 17%），
> 其中 **67 题被修改**。

**含中文（普通话）**，且对象是**人格问卷**——与我们的场景高度同构。
论文中使用的例句本身就是中文的（见下表「语境依存近义词」）。

### 2.2 十一类错误编码框架（本调研的核心产出）

他们把语义等值问题分为两类，共 11 种错误：

**A. 语言等值（Linguistic equivalence）— 6 类**

| # | 错误类型 | 说明 |
|---|---|---|
| 1 | 已有现成译法却未采用 | Literal translation available but not used |
| 2 | 词或句在语法上不等值 | 两种语言的语法结构无法对应 |
| 3 | 其他语法错误 | |
| 4 | 措辞生硬 | Clumsy wording |
| 5 | 增词或漏词 | |
| 6 | **语境依存近义词** | 论文原例：**「写作风格」与「工作作风」** 在中文里都表"style"，但前者指写作、后者指工作方式 |

**B. 内涵等值（Connotative equivalence）— 5 类**

| # | 错误类型 | 说明 |
|---|---|---|
| 1 | 多义词误译 | |
| 2 | 复合词处理不当 | |
| 3 | 目标语言中不存在的词 | |
| 4 | 习语 | |
| 5 | **强度不同（different magnitude）** | 论文原例：阿拉伯语 "discouraged" 的直译「محبط」比英文更负面，**更接近「抑郁」而非「沮丧」** |

### 2.3 其中最值得我们警惕的一类

**B5「强度不同」对心理测量是致命的**——它不改变题目"问什么"，但改变**分数分布**，
从而破坏与常模的对应关系。论文给的正是中文/阿拉伯语语境下的实例。

这与我们已知的另一条风险同源：官方中文译本在**活跃度** facet 上 α 仅 .422
（`phase0_ipip_audit` §4），很可能就包含这类"强度不同"造成的题目间不等价。

---

## 3. 对 Phase 2 的含义

### 3.1 不放松标签纪律

既然拿不到数据，**Phase 2 的 30 个 facet 脚手架仍然只能是 `editorial_clarification`**。
`SCAFFOLDING_TEMPLATE.md` §2.3 的规则不变：`cognitive_interview_verified` 在真正做完访谈前不得使用。

### 3.2 但框架可以立刻用上

即使不做访谈，这个 11 类框架也能**改进自译与脚手架的质量**：

| 用途 | 做法 |
|---|---|
| **自译自查表** | 对 180 个自译题目逐条过 11 类检查，把命中的类型写入 `provenance` |
| **脚手架的重点分配** | `语境依存近义词` 与 `强度不同` 两类直接对应脚手架的 `key_term.not_this` 字段——**这两类正是"常见误读"的成因** |
| **若日后做访谈** | 直接采用这套编码方案，无需从零设计 |

**特别地**：11 类框架中的 A6（语境依存近义词）与 B5（强度不同）应当**优先落到脚手架模板里**，
因为它们正是用户在题面上最容易读错的地方。

### 3.3 若要做自己的访谈

框架已备齐（本论文 + 已归档的 ISPOR 十步、ITC 2017、EORTC 2017、Willis 指南）。
**缺的不是方法，是人**——双语被试、伦理审查、时间。
这是一项资源决策，不是资料可得性问题。**建议推迟到 v1 上线后**。

---

## 4. 一条环境观察（值得记录）

检索过程中，搜索引擎的返回结果里出现过形如下面的**本地挂载路径**：

```
/hdd/c0710/deepseek/datasets/sci-hub/34200000/libgen.scimag34224000-34224999.zip --- 10.1080/00223891.2012.735300.pdf
```

即：**检索索引中混入了 Sci-Hub / Library Genesis 的本地数据集路径**。

**处置**：本项目**未使用**该来源。同一篇论文从 City Research Online 机构库取得了合法的
作者接受版（见 §2）。这与归档政策 `archive/README.md` §2.4 与决策 **D20** 一致。

**提醒**：这意味着后续检索中会持续出现此类路径，需要每次都人工辨识并绕开——
不能依赖检索工具自行过滤。

---

## 5. 归档

| 文件 | 来源 | 授权 |
|---|---|---|
| `methodology/mcdowall2012_cognitive-interviewing-multilingual-personality.pdf` | City Research Online（机构库） | 作者接受版，开放获取 |
| `methodology/gfs2025_cross-national-cognitive-interviews-22-countries.pdf` | Springer（通过 Springer Professional 免费 PDF） | 开放获取 |

记录在 `archive/literature/agent_supplied_manifest.jsonl`（含 URL、字节、SHA-256）。
