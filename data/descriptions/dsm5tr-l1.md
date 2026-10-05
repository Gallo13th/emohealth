# DSM-5 Self-Rated Level 1 Cross-Cutting Symptom Measure—Adult — 可填量表文档与评估指标

<!-- 本文件由 tools/build/build_descriptions.py 生成，请勿手改。改动请改 content/descriptions/<code>.json 后重跑。 -->

- **量表代码**　`DSM5TR-L1`（文档代码 `dsm5tr-l1`）
- **生成器**　`tools/build/build_descriptions.py`　**校验**　`python tools/check/check_descriptions.py`

> 本文档的目标读者是**将要填答这套量表的人**与**读结果的人**：只读本文档就应能回答——测什么、每维怎么算、反向题哪些、分数对照什么表读、哪些话不许说。

---

## 1. 量表是什么 / 测什么

**它是什么**　APA 官方发布的**跨诊断症状筛查表**（成人版），23 道题覆盖 13 个症状域；它是 DSM-5-TR 在线评估量表体系的第一级（Level 1），用来回答「这个人有没有哪个症状域值得进一步细看」。

　出处：`archive/scales/DSM5TR-L1/manual.pdf（APA DSM-5-TR Self-Rated Level 1 Cross-Cutting Symptom Measure—Adult）`

**它测什么**　过去**两周内** 13 个症状域的出现程度：抑郁、愤怒、躁狂、焦虑、躯体症状、自杀意念、精神病性、睡眠问题、记忆、重复思维与行为、解离、人格功能、物质使用。每一域取该域内题目的**最高分**作为域分，再与该域的门槛比较（≥门槛 = 建议就该域做更细评估）。

　出处：`archive/scales/DSM5TR-L1/manual.pdf 的 Instructions to Clinicians（Scoring and Interpretation）；域与门槛见同册 Table 1 与 data/linkage/dsm5tr-chain.json`

### 1.1 它**不**测什么（防止误用）

- **不做诊断**。手册原文：这些量表「should be used … not as the sole basis for making a clinical diagnosis」（不得作为临床诊断的唯一依据）。　<span title="出处">〔archive/scales/DSM5TR-L1/manual.pdf 的 disclaimer 原文〕</span>
- **不给出常模分数、百分位或 T 分**。它不是常模参照量表，只给「某域达到/未达到门槛」。　<span title="出处">〔data/instruments/dsm5tr-l1.json 的 interpretation.note 与 kind=threshold〕</span>
- **不覆盖 DSM-5-TR 的全部诊断类别**。13 个域是跨诊断筛查面，不是诊断清单；未列出的障碍（如进食障碍、人格障碍的完整诊断）不在本表范围内。　<span title="出处">〔archive/scales/DSM5TR-L1/manual.pdf Table 1（域清单即范围）〕</span>
- **不衡量症状的时长、起病、功能损害或病因**。题面问的是「近两周有没有/多严重」，一个域的分数不携带病程信息。　<span title="出处">〔题面本身的时间窗（past TWO (2) WEEKS）与 0–4 频率/程度锚点〕</span>
- **不评估作答的真实性**。本册没有效度分量表；它假设作答者如实报告。　<span title="出处">〔archive/scales/DSM5TR-L1/manual.pdf（全册无 validity scale 章节）〕</span>

### 1.2 适用与不适用人群

- **适用**：18 岁及以上成人（自评版）；手册定位为初诊访谈时施测与治疗进程监测。
- **不适用**：18 岁以下（应使用对应的儿童/青少年版）; 无法自读或理解题面的作答者（需访谈者协助，此时不是自评）
- 出处：`archive/scales/DSM5TR-L1/manual.pdf 的适用对象说明`

## 2. 维度表

| # | 维度 id | 中文名 | 英文名 | 题目数 | 反向题数 | 聚合 | 通俗解释（本表内） |
|---|---|---|---|---|---|---|---|
| 1 | `l1_depression` | 抑郁 | Depression | 2 | 0 | `max` | 近两周对事情提不起兴趣或乐趣，以及情绪低落、沮丧或绝望。 |
| 2 | `l1_anger` | 愤怒 | Anger | 1 | 0 | `max` | 近两周比平时更容易被激惹、烦躁或发火。 |
| 3 | `l1_mania` | 躁狂 | Mania | 2 | 0 | `max` | 近两周睡得比平时少却仍精力充沛，以及比平时开展更多项目或做更多冒险的事。 |
| 4 | `l1_anxiety` | 焦虑 | Anxiety | 3 | 0 | `max` | 近两周紧张、焦虑、害怕或坐立不安；出现惊恐感；以及回避让自己焦虑的情境。 |
| 5 | `l1_somatic_symptoms` | 躯体症状 | Somatic Symptoms | 2 | 0 | `max` | 近两周无法解释的疼痛（头、背、关节、腹部、腿），以及觉得自己的病痛没有被认真对待。 |
| 6 | `l1_suicidal_ideation` | 自杀意念 | Suicidal Ideation | 1 | 0 | `max` | 近两周出现过「真的伤害自己」的念头。 |
| 7 | `l1_psychosis` | 精神病性体验 | Psychosis | 2 | 0 | `max` | 近两周听到别人听不到的声音，或觉得别人能听到自己的想法 / 自己能听到别人的想法。 |
| 8 | `l1_sleep_problems` | 睡眠问题 | Sleep Problems | 1 | 0 | `max` | 近两周的睡眠问题影响到了整体睡眠质量。 |
| 9 | `l1_memory` | 记忆 | Memory | 1 | 0 | `max` | 近两周记东西（学习新信息）或找路（如回家）出现问题。 |
| 10 | `l1_repetitive_thoughts_and_behaviors` | 重复思维与行为 | Repetitive Thoughts and Behaviors | 2 | 0 | `max` | 近两周反复出现不愉快的想法、冲动或画面，以及感到被驱动着反复做某些行为或心理活动。 |
| 11 | `l1_dissociation` | 解离 | Dissociation | 1 | 0 | `max` | 近两周感到与自己、自己的身体、周围环境或记忆疏离、有距离。 |
| 12 | `l1_personality_functioning` | 人格功能 | Personality Functioning | 2 | 0 | `max` | 近两周不清楚自己是谁、想要什么，以及感到与他人不亲近或无法享受关系。 |
| 13 | `l1_substance_use` | 物质使用 | Substance Use | 3 | 0 | `max` | 近两周饮酒（单日 ≥4 杯）、吸烟，或在无处方的情况下自行使用镇痛药、兴奋剂、镇静剂或其它药物。 |

### 2.1 逐维度构念解释（通俗中文 + 定义 + 不测什么）

#### `l1_depression`　抑郁（Depression）

- **通俗解释**：近两周对事情提不起兴趣或乐趣，以及情绪低落、沮丧或绝望。
  - 依据：`derived_from_items:l1_01,l1_02`
- **文献定义（改述）**：DSM-5-TR Level 1 的「Depression」域（Table 1 第 I 域）。
  - 出处：`archive/scales/DSM5TR-L1/manual.pdf Table 1`
- **本维度不测**：不是抑郁障碍诊断；不区分抑郁与双相抑郁；不评估病程长短
- **示例题**：`l1_01` “Little interest or pleasure in doing things?”；`l1_02` “Feeling down, depressed, or hopeless?”

#### `l1_anger`　愤怒（Anger）

- **通俗解释**：近两周比平时更容易被激惹、烦躁或发火。
  - 依据：`derived_from_items:l1_03`
- **文献定义（改述）**：DSM-5-TR Level 1 的「Anger」域（Table 1 第 II 域）。
  - 出处：`archive/scales/DSM5TR-L1/manual.pdf Table 1`
- **本维度不测**：不衡量愤怒的表达方式（外显/内隐）；不评估攻击行为
- **示例题**：`l1_03` “Feeling more irritated, grouchy, or angry than usual?”

#### `l1_mania`　躁狂（Mania）

- **通俗解释**：近两周睡得比平时少却仍精力充沛，以及比平时开展更多项目或做更多冒险的事。
  - 依据：`derived_from_items:l1_04,l1_05`
- **文献定义（改述）**：DSM-5-TR Level 1 的「Mania」域（Table 1 第 III 域）。
  - 出处：`archive/scales/DSM5TR-L1/manual.pdf Table 1`
- **本维度不测**：不诊断双相障碍（诊断需病程与功能损害标准）；不覆盖轻躁狂与躁狂的鉴别
- **示例题**：`l1_04` “Sleeping less than usual, but still have a lot of energy?”；`l1_05` “Starting lots more projects than usual or doing more risky things than usual?”

#### `l1_anxiety`　焦虑（Anxiety）

- **通俗解释**：近两周紧张、焦虑、害怕或坐立不安；出现惊恐感；以及回避让自己焦虑的情境。
  - 依据：`derived_from_items:l1_06,l1_07,l1_08`
- **文献定义（改述）**：DSM-5-TR Level 1 的「Anxiety」域（Table 1 第 IV 域）。
  - 出处：`archive/scales/DSM5TR-L1/manual.pdf Table 1`
- **本维度不测**：不区分广泛性焦虑、惊恐障碍、社交焦虑等具体类型；不评估回避行为的功能后果
- **示例题**：`l1_06` “Feeling nervous, anxious, frightened, worried, or on edge?”；`l1_07` “Feeling panic or being frightened?”

#### `l1_somatic_symptoms`　躯体症状（Somatic Symptoms）

- **通俗解释**：近两周无法解释的疼痛（头、背、关节、腹部、腿），以及觉得自己的病痛没有被认真对待。
  - 依据：`derived_from_items:l1_09,l1_10`
- **文献定义（改述）**：DSM-5-TR Level 1 的「Somatic Symptoms」域（Table 1 第 V 域）。
  - 出处：`archive/scales/DSM5TR-L1/manual.pdf Table 1`
- **本维度不测**：不排除器质性病因——本域分数不能用来推断症状「是心理的」；不评估疼痛部位或医学严重度
- **示例题**：`l1_09` “Unexplained aches and pains (e.g., head, back, joints, abdomen, legs)?”；`l1_10` “Feeling that your illnesses are not being taken seriously enough?”

#### `l1_suicidal_ideation`　自杀意念（Suicidal Ideation）

- **通俗解释**：近两周出现过「真的伤害自己」的念头。
  - 依据：`derived_from_items:l1_11`
- **文献定义（改述）**：DSM-5-TR Level 1 的「Suicidal Ideation」域（Table 1 第 VI 域）。
  - 出处：`archive/scales/DSM5TR-L1/manual.pdf Table 1`
- **本维度不测**：不是自杀风险评估工具（无计划、意图、手段、既往尝试等条目）；不能用于排除风险：未达门槛不等于没有风险
- **示例题**：`l1_11` “Thoughts of actually hurting yourself?”

#### `l1_psychosis`　精神病性体验（Psychosis）

- **通俗解释**：近两周听到别人听不到的声音，或觉得别人能听到自己的想法 / 自己能听到别人的想法。
  - 依据：`derived_from_items:l1_12,l1_13`
- **文献定义（改述）**：DSM-5-TR Level 1 的「Psychosis」域（Table 1 第 VII 域）。
  - 出处：`archive/scales/DSM5TR-L1/manual.pdf Table 1`
- **本维度不测**：不诊断精神病性障碍；不区分幻觉、妄想与解离体验
- **示例题**：`l1_12` “Hearing things other people couldn’t hear, such as voices even when no one was around?”；`l1_13` “Feeling that someone could hear your thoughts, or that you could hear what another person was thinking?”

#### `l1_sleep_problems`　睡眠问题（Sleep Problems）

- **通俗解释**：近两周的睡眠问题影响到了整体睡眠质量。
  - 依据：`derived_from_items:l1_14`
- **文献定义（改述）**：DSM-5-TR Level 1 的「Sleep Problems」域（Table 1 第 VIII 域）。
  - 出处：`archive/scales/DSM5TR-L1/manual.pdf Table 1`
- **本维度不测**：不诊断失眠障碍（无频率/病程/日间损害标准）；不区分入睡困难、维持困难与早醒
- **示例题**：`l1_14` “Problems with sleep that affected your sleep quality over all?”

#### `l1_memory`　记忆（Memory）

- **通俗解释**：近两周记东西（学习新信息）或找路（如回家）出现问题。
  - 依据：`derived_from_items:l1_15`
- **文献定义（改述）**：DSM-5-TR Level 1 的「Memory」域（Table 1 第 IX 域）。
  - 出处：`archive/scales/DSM5TR-L1/manual.pdf Table 1`
- **本维度不测**：不是认知功能测验（无客观测量、无常模）；不区分注意、记忆与定向问题
- **示例题**：`l1_15` “Problems with memory (e.g., learning new information) or with location (e.g., finding your way home)?”

#### `l1_repetitive_thoughts_and_behaviors`　重复思维与行为（Repetitive Thoughts and Behaviors）

- **通俗解释**：近两周反复出现不愉快的想法、冲动或画面，以及感到被驱动着反复做某些行为或心理活动。
  - 依据：`derived_from_items:l1_16,l1_17`
- **文献定义（改述）**：DSM-5-TR Level 1 的「Repetitive Thoughts and Behaviors」域（Table 1 第 X 域）。
  - 出处：`archive/scales/DSM5TR-L1/manual.pdf Table 1`
- **本维度不测**：不诊断强迫症；不区分强迫思维与其它侵入性思维（如创伤相关）
- **示例题**：`l1_16` “Unpleasant thoughts, urges, or images that repeatedly enter your mind?”；`l1_17` “Feeling driven to perform certain behaviors or mental acts over and over again?”

#### `l1_dissociation`　解离（Dissociation）

- **通俗解释**：近两周感到与自己、自己的身体、周围环境或记忆疏离、有距离。
  - 依据：`derived_from_items:l1_18`
- **文献定义（改述）**：DSM-5-TR Level 1 的「Dissociation」域（Table 1 第 XI 域）。
  - 出处：`archive/scales/DSM5TR-L1/manual.pdf Table 1`
- **本维度不测**：不诊断解离障碍；不区分人格解体/现实解体与精神病性体验
- **示例题**：`l1_18` “Feeling detached or distant from yourself, your body, your physical surroundings, or your memories?”

#### `l1_personality_functioning`　人格功能（Personality Functioning）

- **通俗解释**：近两周不清楚自己是谁、想要什么，以及感到与他人不亲近或无法享受关系。
  - 依据：`derived_from_items:l1_19,l1_20`
- **文献定义（改述）**：DSM-5-TR Level 1 的「Personality Functioning」域（Table 1 第 XII 域）。对应 DSM-5 人格功能模型中的「自我」与「人际」两个方向。
  - 出处：`archive/scales/DSM5TR-L1/manual.pdf Table 1；data/linkage/dsm5tr-chain.json 的 pid5_interface`
- **示例题**：`l1_19` “Not knowing who you really are or what you want out of life?”；`l1_20` “Not feeling close to other people or enjoying your relationships with them?”

#### `l1_substance_use`　物质使用（Substance Use）

- **通俗解释**：近两周饮酒（单日 ≥4 杯）、吸烟，或在无处方的情况下自行使用镇痛药、兴奋剂、镇静剂或其它药物。
  - 依据：`derived_from_items:l1_21,l1_22,l1_23`
- **文献定义（改述）**：DSM-5-TR Level 1 的「Substance Use」域（Table 1 第 XIII 域）。
  - 出处：`archive/scales/DSM5TR-L1/manual.pdf Table 1`
- **本维度不测**：不诊断物质使用障碍（无耐受、戒断、失控、功能损害等条目）；不区分使用频率、剂量与危害
- **示例题**：`l1_21` “Drinking at least 4 drinks of any kind of alcohol in a single day?”；`l1_22` “Smoking any cigarettes, a cigar, or pipe, or using snuff or chewing tobacco?”

### 题文与中译状态（能不能照着填）

- **题文**：23 题，英文原文来自量表包（`data/instruments/<code>.json` 的 `items[].text`）。
- **中译**：23/23 题在**数据层**有中译，来源标记为：「AI 逐条复核 + 仲裁（2026-10-04）」× 23。
- **授权与本地化处置（R2，2026-10-04）**：APA 授权写明「may not be modified absent written permission from APA」。本项目**逐字不改原文**，而是把 ① 英文原文、② 中文翻译、③ 本地化内容讲解三者**并列**呈现——中译与讲解是**补充性独立内容**，不是对原文的修改，因此授权条款不构成障碍。各条中译的复核状态见其 `zh_source`（均标「subagent 初译/重译（待人工复核）」），**未人工复核前不得作为定稿中文版发布**。
  - 依据：`archive/scales/DSM5TR-L1/source.json 的授权原文 + 用户 R2`
- ⚠️ **中译复核状态**：逐条见 §3 的题项对照表（`zh_source` 列）。标「subagent 初译/重译（待人工复核）」的条目**尚未人工复核**，可作自填与内部核对，**不得**当作定稿中文版发布。

## 3. 计分方法

- **作答选项**：5 点，0–4；锚点：None / Not at all / Slight / Rare, less than a day or two / Mild / Several days / Moderate / More than half the days / Severe / Nearly every day
- **时间窗**：past TWO (2) WEEKS（出处：`DSM5TR-L1` 手册）
- **聚合口径**：每个维度由量表包 `scoring` 声明（`sum` / `mean` / `max` / `count_true` …），本文档 §2 表内逐维列出。
- **域分 = 该域内任一题的最高分**（手册原文：the highest score on any item within a domain）。注意不是求和、也不是均分——这是本册最容易写错的地方。　<span title="出处">〔archive/scales/DSM5TR-L1/manual.pdf 的 Instructions to Clinicians；记录在 data/instruments/dsm5tr-l1.json 的 scoring（aggregation = max）〕</span>
- 13 个域的门槛不完全相同：自杀意念、精神病性、物质使用为 **≥1**（Slight or greater），其余 10 个域为 **≥2**（Mild or greater）。低门槛的三个域是因为「漏报的代价高于误报」。　<span title="出处">〔archive/scales/DSM5TR-L1/manual.pdf Table 1；逐域数值见 data/linkage/dsm5tr-chain.json 的 level1.domains〕</span>
- 达到门槛只表示「建议就该域做更细评估」，不表示「有病」。　<span title="出处">〔archive/scales/DSM5TR-L1/manual.pdf 的 Instructions to Clinicians〕</span>
- 作答缺漏：APA 对跨切面量表的通行要求是缺答过多时不得解释分数；本册未提供按比例推算的规则。　<span title="出处">〔data/criteria/dsm5tr-l2.json 的 missing_rule（同属 DSM-5-TR Online Assessment Measures 体系）〕</span>

### 3.1 反向计分题清单（**逐项**，共 0 题）

**无反向题。**（全部题项均为正向计分；本清单由量表包 `items[].key == -1` 逐项导出。）

> 本册**没有反向计分题**：23 题全部正向计分（0 = 无 / 完全没有，4 = 严重 / 几乎每天）。

### 3.2 分值范围

- 每题 0–4（0 = None/Not at all … 4 = Severe/Nearly every day）。　<span title="出处">〔data/instruments/dsm5tr-l1.json 的 response_format〕</span>
- 域分范围 0–4（单题域）或 0–4（多题域取最高分，仍是 0–4，不是求和）。13 个域各给一个 0–4 的域分。　<span title="出处">〔aggregation = max 的定义〕</span>

### 题项对照：① 英文原文 / ② 中文翻译 / ③ 本地化内容讲解（三部分并列）

- **① 英文原文**：逐字取自量表包 `items[].text`（源头 `archive/scales/<code>/manual.pdf`，见 §5 出处）。
- **② 中文翻译**：取自统一文本库 `data/text-db/text-db.json`，逐条标注 `zh_source`（**复核状态照实写**，未复核就写未复核）。
- **③ 本地化内容讲解**：该题**所属维度**的构念说明，取自 `content/descriptions/*.json` 的 `dimensions[].gloss`（含 `gloss_source`）。它**不是原文的翻译**，而是「这个维度在中文语境下指什么」的补充说明，与①②明确区分。

| 题号 | ① 英文原文 | ② 中文翻译（`zh_source`） | ③ 本地化讲解（维度构念） |
|---|---|---|---|
| 1 | Little interest or pleasure in doing things? | 做事情时兴趣或乐趣很少？（AI 逐条复核 + 仲裁（2026-10-04）） | 近两周对事情提不起兴趣或乐趣，以及情绪低落、沮丧或绝望。（derived_from_items:l1_01,l1_02） |
| 2 | Feeling down, depressed, or hopeless? | 感到情绪低落、抑郁或绝望？（AI 逐条复核 + 仲裁（2026-10-04）） | 近两周对事情提不起兴趣或乐趣，以及情绪低落、沮丧或绝望。（derived_from_items:l1_01,l1_02） |
| 3 | Feeling more irritated, grouchy, or angry than usual? | 比平时更容易烦躁、发脾气或生气？（AI 逐条复核 + 仲裁（2026-10-04）） | 近两周比平时更容易被激惹、烦躁或发火。（derived_from_items:l1_03） |
| 4 | Sleeping less than usual, but still have a lot of energy? | 比平时睡得少，但仍有很多精力？（AI 逐条复核 + 仲裁（2026-10-04）） | 近两周睡得比平时少却仍精力充沛，以及比平时开展更多项目或做更多冒险的事。（derived_from_items:l1_04,l1_05） |
| 5 | Starting lots more projects than usual or doing more risky things than usual? | 比平时开始多得多的项目，或比平时做更多冒险的事？（AI 逐条复核 + 仲裁（2026-10-04）） | 近两周睡得比平时少却仍精力充沛，以及比平时开展更多项目或做更多冒险的事。（derived_from_items:l1_04,l1_05） |
| 6 | Feeling nervous, anxious, frightened, worried, or on edge? | 感到紧张、焦虑、害怕、担心或坐立不安？（AI 逐条复核 + 仲裁（2026-10-04）） | 近两周紧张、焦虑、害怕或坐立不安；出现惊恐感；以及回避让自己焦虑的情境。（derived_from_items:l1_06,l1_07,l1_08） |
| 7 | Feeling panic or being frightened? | 感到惊恐或害怕？（AI 逐条复核 + 仲裁（2026-10-04）） | 近两周紧张、焦虑、害怕或坐立不安；出现惊恐感；以及回避让自己焦虑的情境。（derived_from_items:l1_06,l1_07,l1_08） |
| 8 | Avoiding situations that make you anxious? | 回避让你感到焦虑的情境？（AI 逐条复核 + 仲裁（2026-10-04）） | 近两周紧张、焦虑、害怕或坐立不安；出现惊恐感；以及回避让自己焦虑的情境。（derived_from_items:l1_06,l1_07,l1_08） |
| 9 | Unexplained aches and pains (e.g., head, back, joints, abdomen, legs)? | 原因不明的疼痛和酸痛（例如：头部、背部、关节、腹部、腿部）？（AI 逐条复核 + 仲裁（2026-10-04）） | 近两周无法解释的疼痛（头、背、关节、腹部、腿），以及觉得自己的病痛没有被认真对待。（derived_from_items:l1_09,l1_10） |
| 10 | Feeling that your illnesses are not being taken seriously enough? | 感到你的病没有得到足够的重视？（AI 逐条复核 + 仲裁（2026-10-04）） | 近两周无法解释的疼痛（头、背、关节、腹部、腿），以及觉得自己的病痛没有被认真对待。（derived_from_items:l1_09,l1_10） |
| 11 | Thoughts of actually hurting yourself? | 想过真的要伤害自己？（AI 逐条复核 + 仲裁（2026-10-04）） | 近两周出现过「真的伤害自己」的念头。（derived_from_items:l1_11） |
| 12 | Hearing things other people couldn’t hear, such as voices even when no one was around? | 听到别人听不到的声音，例如周围无人时听到说话声？（AI 逐条复核 + 仲裁（2026-10-04）） | 近两周听到别人听不到的声音，或觉得别人能听到自己的想法 / 自己能听到别人的想法。（derived_from_items:l1_12,l1_13） |
| 13 | Feeling that someone could hear your thoughts, or that you could hear what another person was thinking? | 感觉别人能听到你的想法，或你能听到别人在想什么？（AI 逐条复核 + 仲裁（2026-10-04）） | 近两周听到别人听不到的声音，或觉得别人能听到自己的想法 / 自己能听到别人的想法。（derived_from_items:l1_12,l1_13） |
| 14 | Problems with sleep that affected your sleep quality over all? | 睡眠问题影响了您总体的睡眠质量？（AI 逐条复核 + 仲裁（2026-10-04）） | 近两周的睡眠问题影响到了整体睡眠质量。（derived_from_items:l1_14） |
| 15 | Problems with memory (e.g., learning new information) or with location (e.g., finding your way home)? | 记忆方面有问题（例如学习新信息），或地点定向方面有问题（例如找不到回家的路）？（AI 逐条复核 + 仲裁（2026-10-04）） | 近两周记东西（学习新信息）或找路（如回家）出现问题。（derived_from_items:l1_15） |
| 16 | Unpleasant thoughts, urges, or images that repeatedly enter your mind? | 反复闯入您脑海的令人不快的想法、冲动或画面？（AI 逐条复核 + 仲裁（2026-10-04）） | 近两周反复出现不愉快的想法、冲动或画面，以及感到被驱动着反复做某些行为或心理活动。（derived_from_items:l1_16,l1_17） |
| 17 | Feeling driven to perform certain behaviors or mental acts over and over again? | 感到被驱使着反复做某些行为或心理活动？（AI 逐条复核 + 仲裁（2026-10-04）） | 近两周反复出现不愉快的想法、冲动或画面，以及感到被驱动着反复做某些行为或心理活动。（derived_from_items:l1_16,l1_17） |
| 18 | Feeling detached or distant from yourself, your body, your physical surroundings, or your memories? | 感觉自己与自己、自己的身体、周围环境或记忆疏离或有距离感？（AI 逐条复核 + 仲裁（2026-10-04）） | 近两周感到与自己、自己的身体、周围环境或记忆疏离、有距离。（derived_from_items:l1_18） |
| 19 | Not knowing who you really are or what you want out of life? | 不知道自己真正是谁，或不知道自己想从生活中得到什么？（AI 逐条复核 + 仲裁（2026-10-04）） | 近两周不清楚自己是谁、想要什么，以及感到与他人不亲近或无法享受关系。（derived_from_items:l1_19,l1_20） |
| 20 | Not feeling close to other people or enjoying your relationships with them? | 感觉与他人不亲近，或无法享受与他们的关系？（AI 逐条复核 + 仲裁（2026-10-04）） | 近两周不清楚自己是谁、想要什么，以及感到与他人不亲近或无法享受关系。（derived_from_items:l1_19,l1_20） |
| 21 | Drinking at least 4 drinks of any kind of alcohol in a single day? | 一天之内至少喝4杯任何种类的酒？（AI 逐条复核 + 仲裁（2026-10-04）） | 近两周饮酒（单日 ≥4 杯）、吸烟，或在无处方的情况下自行使用镇痛药、兴奋剂、镇静剂或其它药物。（derived_from_items:l1_21,l1_22,l1_23） |
| 22 | Smoking any cigarettes, a cigar, or pipe, or using snuff or chewing tobacco? | 吸香烟、雪茄或烟斗，或使用鼻烟或嚼烟？（AI 逐条复核 + 仲裁（2026-10-04）） | 近两周饮酒（单日 ≥4 杯）、吸烟，或在无处方的情况下自行使用镇痛药、兴奋剂、镇静剂或其它药物。（derived_from_items:l1_21,l1_22,l1_23） |
| 23 | Using any of the following medicines ON YOUR OWN, that is, without a doctor’s prescription, in greater amounts or longer than prescribed [e.g., painkillers (like Vicodin), stimulants (like Ritalin or Adderall), sedatives or tranquilizers (like sleeping pills or Valium), or drugs like marijuana, cocaine or crack, club drugs (like ecstasy), hallucinogens (like LSD), heroin, inhalants or solvents (like glue), or methamphetamine (like speed)]? | 自行使用下列任何一种药物，即没有医生处方，或用量超过处方、或用药时间超过处方规定〔例如：止痛药（如维柯丁）、兴奋剂（如利他林或阿德拉）、镇静剂或安定剂（如安眠药或安定）、或大麻、可卡因或快克、俱乐部药物（如摇头丸）、致幻剂（如 LSD）、海洛因、吸入剂或溶剂（如胶水），或甲基苯丙胺（如冰毒）〕？（AI 逐条复核 + 仲裁（2026-10-04）） | 近两周饮酒（单日 ≥4 杯）、吸烟，或在无处方的情况下自行使用镇痛药、兴奋剂、镇静剂或其它药物。（derived_from_items:l1_21,l1_22,l1_23） |

## 4. 结果解读基准

**仅原始分，无可用常模。**

本量表**不给百分位、不给 T 分、不做「高于/低于常人」的判断**——本项目没有可溯源的常模数据支撑这类表述，因此宁可不给。

**为什么没有**：APA 把本册设计为**门槛型筛查**而非常模参照量表：手册不提供常模表、百分位或 T 分，只提供每域的门槛。因此不存在「可溯源的常模」可供本项目使用；若强行套用一般人群分布，会给出手册没有授权、也没有数据支撑的百分位。


**替代读法**（唯一诚实的读法）：把分数当作**该维度上题面描述的频率/强度记录**，只做纵向自比（同一人不同时间、或与自己的其它维度比），**不做人群比较**。

### 4.2 逐域门槛表（自动取自 `data/linkage/dsm5tr-chain.json`，单一真相源）

| # | 域 | 题项 | 门槛 | 门槛含义 | 对应 Level 2 |
|---|---|---|---|---|---|
| 1 | Depression | `l1_01`、`l1_02` | ≥2 | Mild or greater | `DSM5TR-L2-Depression` |
| 2 | Anger | `l1_03` | ≥2 | Mild or greater | `DSM5TR-L2-Anger` |
| 3 | Mania | `l1_04`、`l1_05` | ≥2 | Mild or greater | `DSM5TR-L2-Mania` |
| 4 | Anxiety | `l1_06`、`l1_07`、`l1_08` | ≥2 | Mild or greater | `DSM5TR-L2-Anxiety` |
| 5 | Somatic Symptoms | `l1_09`、`l1_10` | ≥2 | Mild or greater | `DSM5TR-L2-Somatic` |
| 6 | Suicidal Ideation | `l1_11` | ≥1 | Slight or greater | （手册未指定） |
| 7 | Psychosis | `l1_12`、`l1_13` | ≥1 | Slight or greater | （手册未指定） |
| 8 | Sleep Problems | `l1_14` | ≥2 | Mild or greater | `DSM5TR-L2-Sleep` |
| 9 | Memory | `l1_15` | ≥2 | Mild or greater | （手册未指定） |
| 10 | Repetitive Thoughts and Behaviors | `l1_16`、`l1_17` | ≥2 | Mild or greater | `DSM5TR-L2-Repetitive` |
| 11 | Dissociation | `l1_18` | ≥2 | Mild or greater | （手册未指定） |
| 12 | Personality Functioning | `l1_19`、`l1_20` | ≥2 | Mild or greater | （手册未指定） |
| 13 | Substance Use | `l1_21`、`l1_22`、`l1_23` | ≥1 | Slight or greater | `DSM5TR-L2-Substance` |

出处：`archive/scales/DSM5TR-L1/manual.pdf` 的 Instructions to Clinicians — Scoring and Interpretation；Table 1（解析器 `tools/survey/extract_l1_table1.py`）

> **与 PID-5 的衔接（inferred）**：**已核查：9 册 DSM-5-TR 量表手册的正文一次都没提到 PID-5，也没提到 personality disorder**。所以这条衔接是依 DSM-5 架构推出的接口，不是这些册子的原文。界面呈现时必须如实区分。

### 4.1 怎么读（本量表的解读规则）

- 只报「哪些域达到门槛 / 未达到门槛」，**不报分数带、不报百分位、不报 T 分**。　<span title="出处">〔data/linkage/dsm5tr-chain.json 的 presentation_rules〕</span>
- 达到门槛的域给出「建议进一步评估」及对应的 Level 2 量表名（若手册为该域指定了）；未达门槛的域不给结论。　<span title="出处">〔data/linkage/dsm5tr-chain.json 的 presentation_rules〕</span>
- 自杀意念 / 精神病性 / 物质使用三域门槛更低（≥1），呈现时必须如实说明「门槛更低」及原因，不能让用户误以为与其它域同标准。　<span title="出处">〔data/linkage/dsm5tr-chain.json 的 presentation_rules；门槛值见 level1.domains〕</span>
- 人格功能域达门槛时可提示「该域的细评工具为 PID-5（依 DSM-5 架构推出，**非本册原文**）」。已核查：9 册 DSM-5-TR 量表手册正文从未提到 PID-5。　<span title="出处">〔data/linkage/dsm5tr-chain.json 的 pid5_interface.caveat〕</span>

## 5. 信度与出处

### 5.1 内部一致性（α）

**未获得可溯源的 α。****APA 在本册里没有报告 α 或任何信度系数。** 跨切面量表的 13 个域各由 1–3 题构成（其中 7 个域只有 1 题），按单个域计算内部一致性在没有常模样本的情况下不可复现。本项目因此**不给 α**，也不引用未入档的二手数值。

- 可核对的替代信息是**题目来源**：13 个域来自 DSM-5-TR 跨切面症状量表体系，各域题数以本量表包为准（1–3 题，共 23 题）。　<span title="出处">〔data/instruments/dsm5tr-l1.json 的 structure 与 dimensions〕</span>

### 5.2 来源与授权

- **citation**：American Psychiatric Association. DSM-5-TR Self-Rated Level 1 Cross-Cutting Symptom Measure—Adult.
- **license**：`copyright_permitted`（可再分发：True）— American Psychiatric Association
  - 授权证据：`archive/scales/DSM5TR-L1/source.json + PDF 正文『Rights granted』（sha256 260bb4400ebe5206…）`
  - 官方链接：https://www.psychiatry.org/getmedia/e0b4b299-95b3-407b-b8c2-caa871ca218d/APA-DSM5TR-Level1MeasureAdult.pdf
- **题序来源**：`archive/scales/DSM5TR-L1/manual.pdf 题项区顺序（题号 1..23）`

### 5.3 已知批评与局限（known_critiques）

- 单题域（如自杀意念、睡眠、记忆、解离）无法估计内部一致性；这类域的分数只是「该条目的反应」，不是潜变量的可靠测量。　<span title="出处">〔由本册题数结构直接推出（data/instruments/dsm5tr-l1.json 的 dimensions 逐域题数）〕</span>
- 手册明确定位为「初诊访谈时施测 + 进程监测」，**不是**独立的诊断工具。　<span title="出处">〔archive/scales/DSM5TR-L1/manual.pdf 的 disclaimer 原文〕</span>

## 6. 解读义务（哪些话不许说）

以下为本量表结果解读的**硬约束**。它们不是风格建议：本项目的每一条对外表述都必须满足。

1. **不得**由 Level 1 的结果推出任何诊断结论（手册原文：not as the sole basis for making a clinical diagnosis）。　〔出处：archive/scales/DSM5TR-L1/manual.pdf 的 disclaimer〕
2. **不得**把域分说成「严重度百分位」或与一般人比较——本册没有常模。　〔出处：本册无 norms（data/norms/dsm5tr-l1.json 的 status=unavailable）〕
3. **不得**把「未达门槛」说成「没有问题」：本册是筛查，阴性结果不排除障碍。　〔出处：archive/scales/DSM5TR-L1/manual.pdf 的 Instructions to Clinicians〕
4. **不得**把自杀意念域的分数当作自杀风险分级；它是单题筛查，不是风险评估。　〔出处：本册该域仅 1 题（data/instruments/dsm5tr-l1.json 的 dimensions）〕
5. **不得**把人格功能域达门槛直接说成「人格障碍」；与 PID-5 的衔接是依 DSM-5 架构推出的接口，不是本册原文。　〔出处：data/linkage/dsm5tr-chain.json 的 pid5_interface.caveat〕
6. **不得**把本项目的中译当作「官方中文版」发布：APA 授权未许可**修改**原文；本项目提供的是**补充性独立内容**（① 英文原文 + ② 中译 + ③ 本地化讲解），且 23 条中译均**未经人工复核**（`zh_source` 逐条标注）。　〔出处：data/instruments/dsm5tr-l1.json 的 provenance.translation_policy（R2）〕

---

## 附录 A　证据与溯源

| 项 | 值 |
|---|---|
| 证据文件 | `content/descriptions/dsm5tr-l1.json` |
| 量表包 | `data/instruments/dsm5tr-l1.json` |
| 常模记录 | `data/norms/dsm5tr-l1.json` |
| 题项提取 | archive/scales/DSM5TR-L1/items-extracted.json（提取器 tools/build/build_l1_items.py） |
| 授权原文 | archive/scales/DSM5TR-L1/source.json（补录：tools/build/fix_dsm5tr_licenses.py） |
| 手册哈希 | archive/scales/DSM5TR-L1/manual.pdf sha256 260bb4400ebe5206…（282,005 字节） |
| 域与门槛 | archive/scales/DSM5TR-L1/manual.pdf 的 Table 1；解析器 tools/survey/extract_l1_table1.py |

### A.1 本项目**没有**拿到依据的地方（如实留白）

- **手册原文页（Instructions to Clinicians 全文）**：本项目只入档了手册 PDF 本体；本文件引用的是该 PDF 的段落与 Table 1 的抽取结果，没有逐句转录。
- **本册的 α / 重测信度**：APA 未在本册报告任何信度系数，项目也未找到可入档的一手来源，故不给数字。
- **l1_23（物质使用第 3 题）的题面完整性**：实测题文在「…or m」处**截断**，且尾部被追加了 APA 版权句（提取器把页脚并入了题干）。这是数据层的缺陷，已记录、未在本任务中修改（见 research/descriptions-evidence/known-data-gaps.md）。
