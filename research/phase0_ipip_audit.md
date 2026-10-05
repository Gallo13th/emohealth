# Phase 0 审计笔记：IPIP 授权、版本与中文溯源

> **D 编号说明**：文中 `D<编号>` 是 2026-10-04 之前决策账本的编号（已并入 [`PLAN.md`](../PLAN.md) §2/§3），只作历史标识。

> 调研日期：2026-09-29
> 方法：直接抓取 `ipip.ori.org` 官方页面（一手来源）
> 上游文档：`../PLAN.md`、`../instrument-record.schema.md`

---

## 0. 结论摘要

| 项 | 结论 | 影响 |
|---|---|---|
| **授权** | ✅ **全绿**。公共领域，明确允许复制/编辑/翻译/任意用途，含商业用途，无需申请 | Group A 三项 redistribution 权限全部为 true |
| **中文翻译** | ⚠️ 官方标记的只有 **IPIP-NEO-120** 的普通话版；**300 题版无中文** | 与我们"锁 300 题"的意图冲突，需决策 |
| **中文常模** | ❌ **不可用**。N=131，70% 女性，平均年龄 20.4，学生样本 | 强化 D5，且应进一步向 IPIP 官方立场靠拢 |
| **中文译本信度** | ⚠️ 域级良好，**facet 级有问题**（E4 活跃度 α=.422） | 反向支持"用 300 题"的直觉 |
| **官方分型立场** | ✅ 明确反对分型 | 直接授权我们的反分型原则 |
| **质量门方法** | ✅ 官方给出四种检测法 + 关键文献，但**同时声明此议题有争议** | 质量门功能可用，但必须同时呈现争议 |
| **数据源** | ✅ 有大规模参照样本可用（OSF / openpsychometrics） | 无需依赖 canned norms |
| **可持续性** | ⚠️ Goldberg 于 2026-03-29 去世；NIMH 资助 2006 年到期；站点靠捐赠 | **必须自行归档所有用到的材料** |

---

## 1. 授权审计（Group A）

### 1.1 授权声明原文

**来源 A：主页** <https://www.ipip.ori.org/>

> "The items and scales are in the public domain, which means that one can **copy, edit, translate, or use them for any purpose without asking permission and without paying a fee**."

**来源 B：Permission 页** <https://www.ipip.ori.org/newPermission.htm>

> "Because the IPIP has been placed in the public domain, permission has **already been automatically granted** for any person to use IPIP items, scales, and inventories for **any purpose, commercial or non-commercial**."
>
> "It is **not necessary to contact** the IPIP site author (Lew Goldberg) or the IPIP Consultant (John A. Johnson) for permission to use IPIP materials."

### 1.2 对应到 schema

| 字段 | 值 |
|---|---|
| `license_status` | `public_domain` |
| `redistribution.show_items` | ✅ true |
| `redistribution.translate` | ✅ true |
| `redistribution.redistribute` | ✅ true |
| `license_evidence` | 上述两段原文 + URL |

**商业用途明确被覆盖**，因此本项目（无论最终是否商业化）无授权障碍。Phase 0 的授权闸门**通过**。

### 1.3 但有一条重要的反向声明

翻译页明确写道：

> "The accuracy of these translations has **not been verified by anyone associated with the IPIP project**."

即：**IPIP 官方对任何第三方译本（含中文）不作准确性背书。** 这一句必须进入 Group A 的溯源字段，不能被省略。

---

## 2. 量表版本谱系（必须区分，此前混淆）

| 量表 | 出处 | 结构 | 中文 |
|---|---|---|---|
| **IPIP-NEO-300** | **Goldberg (1999)** | 30 facet × **10 题** = 300 | ❌ 无 |
| **IPIP-NEO-120** | **Johnson (2014)**, *JRP* 51, 78–89 | 30 facet × **4 题** = 120 | ✅ 有（含信效度+常模） |
| **IPIP-NEO-120 (Maples 版)** | Maples et al. (2014), *Psychol Assess* 26, 1070–1084 | 30 facet × 4 题 | ❌ |
| **IPIP-NEO-60** | **Maples-Keller et al. (2019)**, *JPA* 101, 4–15 | 60 题，**用 IRT 开发** | ❌ |

> **此前计划中"IPIP-NEO-300"的出处应修正为 Goldberg (1999)**，而非 Johnson。原计划未标注，需补。

**IPIP-NEO-60 的意外价值**：它是**用项目反应理论（IRT）从题库中选出的**。这意味着 IPIP-NEO 题目**已有 IRT 参数工作**，v2 的 CAT 路线不需要从零开始标定。

### 2.1 其他可用形态（公共领域，后续可评估）

- **DeYoung et al. (2007) 10 Big-Five Aspects (BFAS)** — 介于维度与 facet 之间的中间层
- **Simms et al. (2011) CAT-PD-SF v1.1** — **基于 IPIP 的人格障碍计算机自适应测验**，公共领域
- **Goldberg (1992) 50/100 题 Big-Five Factor Markers** — 词汇学取向，非 NEO 取向
- **Yarkoni (2010) AMBI** — 181 题可计 203 个量表

> **CAT-PD 是未来 Mode B 的重要资产**：它是一条公共领域的人格病理通路，与 AMPD 桥梁天然兼容。v1 不用，但应在 GROUP H 记录。

---

## 3. 中文翻译溯源

官方翻译页列出了多支中文翻译，**彼此独立、质量与方法各异**：

| 译者/团队 | 内容 | 方法 | 备注 |
|---|---|---|---|
| **Zhongyang Xu, Jing Qian, Kunning Chen, Lianxin Zhu, Jianlong Ao**（华东师大心理与认知科学学院，指导：Ya Zhang 博士） | **Johnson (2014) IPIP-NEO-120 全文普通话版** | 前译 + 共识会议 + 回译 + 专家/英语教师/潜在用户审阅 | **唯一带信效度与常模的官方标记中文版**。联系：zx57@illinois.edu |
| Chaoping Li（中国人民大学组织与人力资源研究所） | 针对 16PF / HPI / NEO 构念的 IPIP 普通话版 | 未详述 | 联络中：lichaoping@mparuc.edu.cn |
| Sih-Ci Jhu（台湾东华大学，指导：Yi-Chao Wang 博士） | 50 题 Big-Five Factor Markers **繁体中文** | 前译 + 共识会议 + 回译 + 专家与潜在用户审阅 | 台湾样本信效度 |
| Xian Xu（南佛罗里达大学） | 100 题 Big-Five Factor Markers 普通话版 | 翻译 + 回译 | — |
| Ya-Tzu Wang（台南应用科技大学） | 50 题 Big-Five Factor Markers 中文版 | 未详述 | — |
| Clara To & Evan Choi（香港） | AB5C Toughness facet 12 题 | 未详述 | — |

### 3.1 结论

- **只有 120 题版有官方标记的普通话译本**，且其方法描述最完整（前译/共识/回译/多角色审阅），接近 ISPOR TCA 的精神。
- **300 题版无中文译本**。若要上 300 题，**必须自行翻译**。
- 所有译本均**未经 IPIP 验证**。

---

## 4. 中文常模审计

**来源**：<https://www.ipip.ori.org/ChineseIPIP-120norms.htm>

> N = **131**，30% 男性 / **70% 女性**，平均年龄 **20.4 ± 3.3**

附有五个维度与 30 个 facet 的均值与标准差。

### 4.1 判定：不可作为产品常模

| 问题 | 说明 |
|---|---|
| 样本量 | N=131，SD 估计极不稳定 |
| 性别偏斜 | 70% 女性，无法做性别分层 |
| 年龄极窄 | 平均 20.4，标准差 3.3 → 实质是大学生样本 |
| 代表性 | 便利样本，非概率抽样 |

### 4.2 对 D5 的冲击

原决策 D5 = "采用国际常模 + 显著警示"。

现在必须补一层：**"中文常模"这条备选路径经审计后也不可用**。因此不存在"用国内常模就更准"的退路。这实际上让我们的处境更清晰，也让表述更诚实。

### 4.3 更重要的是：IPIP 官方反对使用 canned norms

**来源**：<https://www.ipip.ori.org/newNorms.htm>

> "**No norms are available on the IPIP website**, for reasons explained below."
>
> "One should be **very wary of using canned 'norms'** because it isn't obvious that one could ever find a population of which one's present sample is a representative subset. **Most 'norms' are misleading, and therefore they should not be used.**"
>
> "Far more defensible are **local norms**, which one develops oneself."

**这是一个直接挑战 D5 的权威立场。** IPIP 的官方建议不是"用常模+警示"，而是"不要用 canned norms，自建 local norms"。

### 4.4 官方给的替代解读方案

**来源**：<https://www.ipip.ori.org/InterpretingIndividualIPIPScaleScores.htm>

方案一（SD 法）：
- 均值 ±0.5 SD 内 → "average"
- 之外 → "low" / "high"
- 正态下约 38% average、31% low、31% high

方案二（五分位 / quintiles）：
- 最低 20% / 次低 20% / 中间 20% / 次高 20% / 最高 20%
- 标签示例：*introverted / somewhat introverted / average / somewhat extraverted / extraverted*

**这直接给出了 `bands[]` 的权威定义方案**，且解决 schema 待决问题 #3。

---

## 5. IPIP 官方对"分型"的立场（对我们极为有利）

**来源**：同上 Interpreting 页

> "When one conducts statistical analyses, however, one should try **not to pigeon-hole individuals into type categories** like introvert and extravert, given that introversion-extraversion is a **continuum**."
>
> "And even when one provides feedback to participants, one can **show them where their scores lie on the full continuum of scores rather than telling them what type of person they are**."
>
> "In short, **we caution against interpreting IPIP scale scores in terms of categories or sorting respondents into groups based on their scores**."

**我们的反分型原则（`PLAN.md` §2.1）现在有了来自题库作者方的直接授权。** 这与 16Personalities 的做法形成正面冲突，是本项目的核心差异化论据。

---

## 6. IPIP 官方给出的作答质量门方法

**来源**：<https://www.ipip.ori.org/newValidity.htm>

### 6.1 四种检测法（官方列举）

| 代号 | 方法 | 对应我们的质量门 |
|---|---|---|
| (a) | **OVERUSE OF THE SAME RESPONSE OPTION** — 统计每人各选项使用次数，排除过度集中者 | long-string |
| (b) | **COMMONALITY VERSUS DEVIANCY** — 取反应分布最极端的题，计"偏差量表"，排除接近随机作答者 | 随机作答检测 |
| (c) | **SEMANTIC INCONSISTENCY** — 找高正相关（同义）与高负相关（反义）题对，算个人在这些题对上的相关，排除准随机作答者 | 反向题一致性 |
| (d) | **SOCIAL DESIRABILITY** — 用样本各题均值与个人作答求相关，排除负相关/近零/异常高者 | 社会赞许性 |

### 6.2 但官方同时给出强烈警告

> "**This is a most controversial topic, so be warned!** Most inventory developers assume that these are necessary. **BUT, they may well be wrong**: See Piedmont, et al. (2000), Johnson (2005), and Dudley, et al. (2005)."

**这正好是 `PLAN.md` §2.4 的实践**：质量门必须**同时呈现方法与其争议**，不能只当工具卖。

### 6.3 关键文献

- **Niessen, A. S. M., Meijer, R. R., & Tendeiro, J. N. (2016).** Detecting careless respondents in web-based questionnaires: Which method to use? *Journal of Research in Personality*, 63, 1–11. — 各方法敏感度/特异度比较，**首选参考**
- **Johnson, J. A. (2005).** Ascertaining the validity of individual protocols from Web-based personality inventories. *JRP*, 39, 103–129.
- **Kurtz, J. E., & Parrish, C. L. (2001).** Semantic response consistency and protocol validity in structured personality assessment: The case of the NEO-PI-R. *JPA*, 76, 315–332.
- **Piedmont, R. L., McCrae, R. R., Riemann, R., & Angleitner, A. (2000).** On the invalidity of validity scales. *JPSP*, 78, 582–593.
- **Costa & McCrae (1997).** Stability and change in personality assessment. *JPA*, 68, 86–94.
- **Dudley et al. (2005).** Racial differences in socially desirable responding in selection contexts. *JPA*, 85, 50–64.

---

## 7. 数据源与参照样本

**来源**：<https://www.ipip.ori.org/newNorms.htm>

| 数据源 | 内容 | 可用性 |
|---|---|---|
| **ESCS**（Eugene-Springfield Community Sample） | IPIP 量表多数统计性质的来源 | Harvard Dataverse: <https://dataverse.harvard.edu/dataverse/ESCS-Data>，需先读 "(0) Documentation and Sample Demographics" |
| **Johnson 的 OSF 仓库** | **300 题 IPIP-NEO 与 Johnson 120 题的原始数据** | <https://osf.io/tbmh5/> ✅ 首选 |
| **Open-Source Psychometrics Project** | `IPIP-FFM-data-8Nov2018.zip`，**超过 100 万案例**，含良好文档的 codebook，量表标注正确 | <https://openpsychometrics.org/_rawdata/> ✅ 可用 |
| Open-Source Psychometrics 的 `BIG5` 数据集（19,719 案例） | — | ❌ **官方明确建议避免**：用了 NEO PI-R 标签而非正确词汇学标签，方向不明；计分方法非标准；常模以题目均值呈现，已造成混淆 |

**另据文献表格**，基于 IPIP-NEO-300 的国际数据集样本量可达 **N = 307,313**（该数字来自检索片段，需在正式引用前核对原文）。

### 7.1 对计划的含义

- 我们**可以获得百万级参照分布**，不必依赖 IPIP 站点的 canned norms。
- 但这仍是**英文/西方人群为主**，不能冒充中国常模。
- **v1 的诚实表述应是**："你的分数相对于【明确标注的参照样本】的位置"，而非"相对于中国人的常模"。

---

## 8. 意外发现

### 8.1 CAT-PD（重要）

**Simms, L. J., Goldberg, L. R., Roberts, J. E., Watson, D., Welte, J., & Rotterman, J. H. (2011).** Computerized adaptive assessment of personality disorder: Introducing the CAT-PD project. *Journal of Personality Assessment*, 93, 380–389.

- 基于 IPIP 的**人格障碍计算机自适应测验**
- **公共领域**
- 与 AMPD 桥梁天然兼容

→ 记入 Group H 与 Mode B 路线图（v1 不使用）。

### 8.2 机器可读题目源

**Shane Mueller 的 OpenScales 仓库**：<https://github.com/stmueller/OpenScales>
- `scales/ipip/ipip_item_codes.json` — IPIP 题目主表
- `scales/ipip/translations` — 各语言译本

→ **这是内容生产流水线的直接原料**，比自己抓 HTML 表可靠。

### 8.3 可持续性风险（新风险）

- **Goldberg 于 2026-03-29 去世**（站点公告）
- 建站 NIMH 资助**已于 2006 年到期**
- 站点目前**依靠自愿捐赠**维持
- 页面最后更新 2026-07-02

→ **必须自行归档所有用到的 IPIP 材料（题目表、计分键、翻译、可靠性数据），不得依赖外链。** 新增一条工程要求。

---

## 9. 对计划的冲击：需要决策

### 9.1 【需拍板】300 题 vs 120 题

| | IPIP-NEO-300（Goldberg 1999） | IPIP-NEO-120（Johnson 2014） |
|---|---|---|
| facet 精度 | **10 题/facet** | 4 题/facet |
| facet 信度 | 预期显著更好 | 已知有问题（E4 α=.422） |
| 中文译本 | ❌ 无，需自译 | ✅ 有，方法较规范 |
| 中文常模 | ❌ | ⚠️ 有但 N=131 不可用 |
| 权威出处 | Goldberg (1999) | Johnson (2014) |
| 规模 | 大表（符合 D4） | 已属"提炼版" |

**分析**：中文常模在两边都不可用（第 4 节），所以"120 题有常模"这个优势**实际不存在**。120 题唯一的实质优势是**有现成中文译本**。

而用户坚持大表的方法论直觉（`PLAN.md` §2.2、§2.3）是**被信度数据支持的**：E4 α=.422 正是 4 题/facet 的代价。facet 级精度是本产品的核心价值，削弱它等于削弱产品。

**倾向建议**：
- **v1 主路径 = IPIP-NEO-300**，自行翻译
- **以官方 120 题普通话译本作为校准基准**（它是最接近 ISPOR TCA 流程的既有中文资产），而非从零开始
- 对自译部分执行**回译 + 小样本认知访谈**，并把方法写入 `provenance`
- **120 题作为可选短路径**保留（复用现成译本），但**必须标注 E4 信度问题**

### 9.2 【需修订】D5 的表述

原 D5 = "采用国际常模 + 显著警示"。

**建议修订为**：不使用 canned norms；采用**明确标注来源的参照样本分布**（Johnson OSF / openpsychometrics 百万级），配合 IPIP 官方的 SD 法或五分位法呈现；同时诚实说明**不存在可用的中国常模**，并保留自建常模路径。

理由：IPIP 官方立场（4.3）+ 中文常模审计结果（4.1）。

### 9.3 【新增】中文翻译方法学要求

因 300 题无中译本，需自行翻译。方法须对齐 **ISPOR TCA** 与 **ITC Guidelines**，并把每一步写入 `items[].text.translations[].provenance`。

---

## 10. 来源清单

**一手来源（ipip.ori.org）**
- 主页 / 公共领域声明：<https://www.ipip.ori.org/>
- Permission：<https://www.ipip.ori.org/newPermission.htm>
- Norms 与数据源：<https://www.ipip.ori.org/newNorms.htm>
- 解读方法：<https://www.ipip.ori.org/InterpretingIndividualIPIPScaleScores.htm>
- 效度指标与争议：<https://www.ipip.ori.org/newValidity.htm>
- 翻译清册：<https://www.ipip.ori.org/newItemTranslations.htm>
- 多构念量表索引：<https://www.ipip.ori.org/newMultipleconstructs.htm>
- 中文 120 题信度：<https://www.ipip.ori.org/ChineseIPIP-120reliability.htm>
- 中文 120 题常模：<https://www.ipip.ori.org/ChineseIPIP-120norms.htm>

**关键文献**

| 主题 | 文献 |
|---|---|
| 公共领域题库总纲 | Goldberg, L. R., et al. (2006). The international personality item pool and the future of public-domain personality measures. *Journal of Research in Personality*, 40, 84–96. |
| IPIP-NEO-300 | Goldberg, L. R. (1999). A broad-bandwidth, public domain, personality inventory measuring the lower-level facets of several five-factor models. In *Personality psychology in Europe* (Vol. 7, pp. 7–28). |
| IPIP-NEO-120 | Johnson, J. A. (2014). Measuring thirty facets of the Five Factor Model with a 120-item public domain inventory. *JRP*, 51, 78–89. |
| IPIP-NEO-60（IRT） | Maples-Keller, J. L., et al. (2019). Using item response theory to develop a 60-item representation of the NEO PI-R. *JPA*, 101, 4–15. |
| 粗心作答检测 | Niessen, Meijer & Tendeiro (2016). *JRP*, 63, 1–11. |
| 网络量表效度 | Johnson, J. A. (2005). *JRP*, 39, 103–129. |
| 效度量表之争 | Piedmont, R. L., et al. (2000). *JPSP*, 78, 582–593. |
| CAT-PD | Simms, L. J., et al. (2011). *JPA*, 93, 380–389. |

---

## 11. Phase 0 未完成的审计项

- [ ] 完整的中文 120 题信度表（O/A/C 三域的 facet α 未获取，页面被截断）
- [ ] 官方 120 题普通话译本的**具体题目文本**（用于校准 300 题自译）
- [ ] `IPIP-NEO-300` 计分键与题目主表（`newNEOFacetsKey.htm` + OpenScales 仓库）
- [ ] 核对 IPIP-NEO-300 国际数据集 N=307,313 的原始出处
- [ ] 确认 OSF `osf.io/tbmh5/` 的数据许可与可用性
- [ ] IPIP 材料的**本地归档**（应对 8.3 可持续性风险）
