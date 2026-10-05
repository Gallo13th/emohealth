# PID-5 — The Personality Inventory for DSM-5（成人版，220 题） — 可填量表文档与评估指标

<!-- 本文件由 tools/build/build_descriptions.py 生成，请勿手改。改动请改 content/descriptions/<code>.json 后重跑。 -->

- **量表代码**　`PID-5`（文档代码 `pid-5`）
- **生成器**　`tools/build/build_descriptions.py`　**校验**　`python tools/check/check_descriptions.py`

> 本文档的目标读者是**将要填答这套量表的人**与**读结果的人**：只读本文档就应能回答——测什么、每维怎么算、反向题哪些、分数对照什么表读、哪些话不许说。

---

## 1. 量表是什么 / 测什么

**它是什么**　APA 发布的**适应不良人格特质**自评量表：220 道题，25 个 facet（每个 4–14 题），归入 5 个域（每个域由 3 个 facet 均分构成）。它是 DSM-5 人格障碍模型（AMPD）里 Criterion B（适应不良特质）的操作化工具。

　出处：`archive/scales/PID-5/manual.pdf（『25 personality trait facets』『five broader trait domains』『each trait facet consisting of 4 to 14 items』）；结构见 data/instruments/pid-5.json 的 structure 与 scoring`

**它测什么**　作答方式是 0–3 的四点自评（0 = very false or often false … 3 = very true or often true）。**facet 分 = 该 facet 内题目的均分**（反向题先做 `3 − x`）；**域分 = 该域 3 个 facet 分的均分**。分数越高表示该适应不良特质越突出。

　出处：`archive/scales/PID-5/manual.pdf 的 Scoring 段（sum then average、prorate）；data/instruments/pid-5.json 的 scoring（facet = mean of items，domain = mean of 3 facets）`

### 1.1 它**不**测什么（防止误用）

- **不是诊断**。高分代表特质突出，不代表符合任何人格障碍的诊断标准；AMPD 的诊断还需要 Criterion A（人格功能损害）与临床判断。　<span title="出处">〔data/instruments/pid-5.json 的 citation（DSM-5 AMPD 框架）与手册的临床使用定位〕</span>
- **不测「正常人格」的常模位置**。它测的是适应不良特质，不是大五式的常态特质分布；PID-5 的百分位不能当作「你在人群中的性格位置」。　<span title="出处">〔archive/norms/pid-5/README.md 与 data/norms/pid-5.json 的 percentile_method（条件百分位，按性别×年龄分层）〕</span>
- **不衡量症状病程、功能损害或严重度分级**。手册不含严重度分级，本项目也没找到可采用的 220 题版临床分界值。　<span title="出处">〔research/pid5_psychometrics_survey.md §2.4 与 §4（通行的分界值不是 220 题版或不是一般人群）〕</span>
- **不测智力、认知能力或器质性因素**。　<span title="出处">〔量表范围（25 个特质 facet 全为适应不良特质）〕</span>
- **不包含效度/装好装坏量表**。作答真实性只能靠外部质量门识别。　<span title="出处">〔本量表包无 validity 维度；质量门见 data/quality-gate-calibration.json〕</span>
- **不是 PID-5-BF**。本项目收录的是 220 题完整版；PID-5-BF（25 题）只用于交叉核对题项归属，不作为本量表的结果口径。　<span title="出处">〔data/instruments/pid-5.json 的 provenance（与 PID-5-BF 25/25 交叉核对）〕</span>

### 1.2 适用与不适用人群

- **适用**：18 岁及以上成人。常模为德国 GESIS Panel 总体代表性样本（N=4,727，条件百分位按性别×年龄分层）。
- **不适用**：18 岁以下; 把结果当诊断依据; 把本量表的百分位当作常态人格的位置
- 出处：`data/norms/pid-5.json 的 n / n_note / conditional / cells`

## 2. 维度表

| # | 维度 id | 中文名 | 英文名 | 题目数 | 反向题数 | 聚合 | 通俗解释（本表内） |
|---|---|---|---|---|---|---|---|
| 1 | `pid5_anhedonia` | 快感缺失 | Anhedonia | 8 | 2 | `mean` | 从活动中难以获得乐趣或满足，对本来喜欢的事提不起兴趣。 |
| 2 | `pid5_anxiousness` | 焦虑性 | Anxiousness | 9 | 1 | `mean` | 强烈的紧张、担心与不安，常伴随对身体感受的警觉。 |
| 3 | `pid5_attention_seeking` | 寻求关注 | Attention Seeking | 8 | 0 | `mean` | 渴望成为注意的焦点，靠行为或外表吸引他人注意。 |
| 4 | `pid5_callousness` | 冷漠无情 | Callousness | 14 | 1 | `mean` | 对他人感受漠不关心，利用他人、缺乏内疚。 |
| 5 | `pid5_deceitfulness` | 欺骗性 | Deceitfulness | 10 | 1 | `mean` | 为私利而撒谎、隐瞒、误导他人。 |
| 6 | `pid5_depressivity` | 抑郁性 | Depressivity | 14 | 0 | `mean` | 持续的低落、无望感与自我贬低，觉得生活没有意义。 |
| 7 | `pid5_distractibility` | 易分心 | Distractibility | 9 | 0 | `mean` | 注意力容易被外界或杂念拉走，难以维持在一件事上。 |
| 8 | `pid5_eccentricity` | 古怪 | Eccentricity | 13 | 0 | `mean` | 行为、言谈或外表显得奇特，与所在文化环境不合拍。 |
| 9 | `pid5_emotional_lability` | 情绪不稳 | Emotional Lability | 7 | 0 | `mean` | 情绪起伏大且变化快，容易因小事被激起。 |
| 10 | `pid5_grandiosity` | 夸大 | Grandiosity | 6 | 0 | `mean` | 觉得自己特殊、优于他人，理应得到特殊对待。 |
| 11 | `pid5_hostility` | 敌意 | Hostility | 10 | 0 | `mean` | 容易生气、易被冒犯，对他人抱有敌意。 |
| 12 | `pid5_impulsivity` | 冲动 | Impulsivity | 6 | 1 | `mean` | 凭一时冲动行动，缺少计划，事后后悔。 |
| 13 | `pid5_intimacy_avoidance` | 回避亲密 | Intimacy Avoidance | 6 | 1 | `mean` | 回避亲密的情感联系或亲密关系。 |
| 14 | `pid5_irresponsibility` | 不负责任 | Irresponsibility | 7 | 1 | `mean` | 不履行承诺与义务，不关心工作或财务上的后果。 |
| 15 | `pid5_manipulativeness` | 操纵性 | Manipulativeness | 5 | 0 | `mean` | 用欺骗、奉承或施压等手段让他人按自己的意愿行事。 |
| 16 | `pid5_perceptual_dysregulation` | 知觉失调 | Perceptual Dysregulation | 12 | 0 | `mean` | 在清醒状态下出现异常的知觉体验（觉得世界不真实、感到自己与身体或思维分离等）。 |
| 17 | `pid5_perseveration` | 固执持续 | Perseveration | 9 | 0 | `mean` | 坚持已经不合时宜的做法，难以转换思路或停止。 |
| 18 | `pid5_restricted_affectivity` | 情感受限 | Restricted Affectivity | 7 | 0 | `mean` | 情绪表达少、情感体验平淡，对事情缺少反应。 |
| 19 | `pid5_rigid_perfectionism` | 刻板完美主义 | Rigid Perfectionism | 10 | 0 | `mean` | 对秩序、细节与完美的严格要求，达到影响任务完成的程度。 |
| 20 | `pid5_risk_taking` | 冒险 | Risk Taking | 14 | 6 | `mean` | 从事有危险、可能造成伤害的活动，不权衡后果。 |
| 21 | `pid5_separation_insecurity` | 分离不安 | Separation Insecurity | 7 | 0 | `mean` | 害怕被重要他人遗弃或离开，对被抛弃的迹象过度敏感。 |
| 22 | `pid5_submissiveness` | 顺从 | Submissiveness | 4 | 0 | `mean` | 在关系中习惯性让渡主导权、顺从他人的意愿。 |
| 23 | `pid5_suspiciousness` | 猜疑 | Suspiciousness | 7 | 2 | `mean` | 怀疑他人的动机，觉得别人可能对自己有恶意。 |
| 24 | `pid5_unusual_beliefs_experiences` | 异常信念与体验 | Unusual Beliefs & Experiences | 8 | 0 | `mean` | 持有与所在文化环境不符的信念，或报告异常的体验。 |
| 25 | `pid5_withdrawal` | 退缩 | Withdrawal | 10 | 0 | `mean` | 偏好独处、回避社交接触与人际互动。 |

### 2.1 逐维度构念解释（通俗中文 + 定义 + 不测什么）

#### `pid5_anhedonia`　快感缺失（Anhedonia）

- **通俗解释**：从活动中难以获得乐趣或满足，对本来喜欢的事提不起兴趣。
  - 依据：`derived_from_items:pid5_anhedonia 的 8 题`
- **本维度不测**：不是抑郁发作本身（不含心境低落或自责条目）
- **示例题**：`pid5_001` “I don’t get as much pleasure out of things as others seem to.”　→ 中译：“我从事情中获得的乐趣不如别人多。”（AI 逐条复核 + 仲裁（2026-10-04））；`pid5_023` “Nothing seems to interest me very much.”　→ 中译：“似乎没有什么能让我很感兴趣。”（AI 逐条复核 + 仲裁（2026-10-04））

#### `pid5_anxiousness`　焦虑性（Anxiousness）

- **通俗解释**：强烈的紧张、担心与不安，常伴随对身体感受的警觉。
  - 依据：`derived_from_items:pid5_anxiousness 的 9 题`
- **本维度不测**：不诊断焦虑障碍（无病程与功能损害标准）
- **示例题**：`pid5_079` “I worry a lot about terrible things that might happen.”　→ 中译：“我非常担心可能发生的可怕事情。”（AI 逐条复核 + 仲裁（2026-10-04））；`pid5_093` “I often worry that something bad will happen due to mistakes I made in the past.”　→ 中译：“我常常担心因为自己过去犯的错会发生不好的事”（AI 逐条复核 + 仲裁（2026-10-04））

#### `pid5_attention_seeking`　寻求关注（Attention Seeking）

- **通俗解释**：渴望成为注意的焦点，靠行为或外表吸引他人注意。
  - 依据：`derived_from_items:pid5_attention_seeking 的 8 题`
- **示例题**：`pid5_014` “I do things to makesure people notice me.”　→ 中译：“我做事是为了让别人注意到我。”（AI 逐条复核 + 仲裁（2026-10-04））；`pid5_043` “I do things so that people just have to admire me.”　→ 中译：“我做事就是为了让别人不得不钦佩我。”（AI 逐条复核 + 仲裁（2026-10-04））

#### `pid5_callousness`　冷漠无情（Callousness）

- **通俗解释**：对他人感受漠不关心，利用他人、缺乏内疚。
  - 依据：`derived_from_items:pid5_callousness 的 14 题`
- **本维度不测**：不等于反社会行为史（无行为记录条目）
- **示例题**：`pid5_011` “I often get into physical fights.”　→ 中译：“我常常和别人动手打架”（AI 逐条复核 + 仲裁（2026-10-04））；`pid5_013` “Being rude and unfriendly is just a part of who I am.”　→ 中译：“粗鲁和不友好就是我这个人的一部分。”（AI 逐条复核 + 仲裁（2026-10-04））

#### `pid5_deceitfulness`　欺骗性（Deceitfulness）

- **通俗解释**：为私利而撒谎、隐瞒、误导他人。
  - 依据：`derived_from_items:pid5_deceitfulness 的 10 题`
- **示例题**：`pid5_041` “I make up stories about things that happened that are totally untrue.”　→ 中译：“我会就发生过的事编造完全不符合事实的说法。”（AI 逐条复核 + 仲裁（2026-10-04））；`pid5_053` “I often make up things about myself to help me get what I want.”　→ 中译：“我常常编造关于自己的事来帮我得到想要的东西”（AI 逐条复核 + 仲裁（2026-10-04））

#### `pid5_depressivity`　抑郁性（Depressivity）

- **通俗解释**：持续的低落、无望感与自我贬低，觉得生活没有意义。
  - 依据：`derived_from_items:pid5_depressivity 的 14 题`
- **本维度不测**：不评估自杀风险
- **示例题**：`pid5_027` “I often feel like nothing I do really matters.”　→ 中译：“我常常觉得我做什么都无关紧要”（AI 逐条复核 + 仲裁（2026-10-04））；`pid5_061` “I’m very dissatisfied with myself.”　→ 中译：“我对自己很不满意。”（AI 逐条复核 + 仲裁（2026-10-04））

#### `pid5_distractibility`　易分心（Distractibility）

- **通俗解释**：注意力容易被外界或杂念拉走，难以维持在一件事上。
  - 依据：`derived_from_items:pid5_distractibility 的 9 题`
- **示例题**：`pid5_006` “I lose track of conversations because other things catch my attention.”　→ 中译：“我会因为其他事物吸引我的注意而跟不上谈话。”（AI 逐条复核 + 仲裁（2026-10-04））；`pid5_029` “I can’t concentrate on anything.”　→ 中译：“我什么事都无法集中注意力。”（AI 逐条复核 + 仲裁（2026-10-04））

#### `pid5_eccentricity`　古怪（Eccentricity）

- **通俗解释**：行为、言谈或外表显得奇特，与所在文化环境不合拍。
  - 依据：`derived_from_items:pid5_eccentricity 的 13 题`
- **示例题**：`pid5_005` “I often have ideas that are too unusual to explain to anyone.”　→ 中译：“我常常有一些离奇得无法向任何人解释的想法”（AI 逐条复核 + 仲裁（2026-10-04））；`pid5_021` “I often say things that others find odd or strange.”　→ 中译：“我常常说些别人觉得古怪或奇怪的话”（AI 逐条复核 + 仲裁（2026-10-04））

#### `pid5_emotional_lability`　情绪不稳（Emotional Lability）

- **通俗解释**：情绪起伏大且变化快，容易因小事被激起。
  - 依据：`derived_from_items:pid5_emotional_lability 的 7 题`
- **示例题**：`pid5_018` “My emotions sometimes change for no good reason.”　→ 中译：“我的情绪有时会毫无缘由地变化。”（AI 逐条复核 + 仲裁（2026-10-04））；`pid5_062` “I have much stronger emotional reactions than almost everyone else.”　→ 中译：“我的情绪反应比几乎所有人都强烈得多。”（AI 逐条复核 + 仲裁（2026-10-04））

#### `pid5_grandiosity`　夸大（Grandiosity）

- **通俗解释**：觉得自己特殊、优于他人，理应得到特殊对待。
  - 依据：`derived_from_items:pid5_grandiosity 的 6 题`
- **示例题**：`pid5_040` “To behonest, I’m just more important than other people.”　→ 中译：“说实话，我就是比别人更重要。”（AI 逐条复核 + 仲裁（2026-10-04））；`pid5_065` “I have outstanding qualities that few others possess.”　→ 中译：“我拥有少数人才具备的出众特质。”（AI 逐条复核 + 仲裁（2026-10-04））

#### `pid5_hostility`　敌意（Hostility）

- **通俗解释**：容易生气、易被冒犯，对他人抱有敌意。
  - 依据：`derived_from_items:pid5_hostility 的 10 题`
- **示例题**：`pid5_028` “I snap at people when they do little things that irritate me.”　→ 中译：“别人做了惹恼我的小事时，我会厉声呵斥他们。”（AI 逐条复核 + 仲裁（2026-10-04））；`pid5_032` “I can be mean when I need to be.”　→ 中译：“必要时我可以很刻薄。”（AI 逐条复核 + 仲裁（2026-10-04））

#### `pid5_impulsivity`　冲动（Impulsivity）

- **通俗解释**：凭一时冲动行动，缺少计划，事后后悔。
  - 依据：`derived_from_items:pid5_impulsivity 的 6 题`
- **示例题**：`pid5_004` “I feel like I act totally on impulse.”　→ 中译：“我觉得自己做事完全是凭一时冲动。”（AI 逐条复核 + 仲裁（2026-10-04））；`pid5_016` “I usually do things on impulse without thinking about what might happen as a result.”　→ 中译：“我通常凭一时冲动做事，不去想可能带来什么后果。”（AI 逐条复核 + 仲裁（2026-10-04））

#### `pid5_intimacy_avoidance`　回避亲密（Intimacy Avoidance）

- **通俗解释**：回避亲密的情感联系或亲密关系。
  - 依据：`derived_from_items:pid5_intimacy_avoidance 的 6 题`
- **示例题**：`pid5_089` “I prefer to keep romance out of my life.”　→ 中译：“我宁愿把恋爱排除在我的生活之外”（AI 逐条复核 + 仲裁（2026-10-04））；`pid5_097` “I enjoy being in love.”　→ 中译：“我喜欢恋爱时的感觉。”（AI 逐条复核 + 仲裁（2026-10-04））

#### `pid5_irresponsibility`　不负责任（Irresponsibility）

- **通俗解释**：不履行承诺与义务，不关心工作或财务上的后果。
  - 依据：`derived_from_items:pid5_irresponsibility 的 7 题`
- **示例题**：`pid5_031` “Others see me as irresponsible.”　→ 中译：“别人认为我不负责任。”（AI 逐条复核 + 仲裁（2026-10-04））；`pid5_129` “I’m often pretty careless with my own and others’things.”　→ 中译：“我常常对自己和别人的东西相当粗心。”（AI 逐条复核 + 仲裁（2026-10-04））

#### `pid5_manipulativeness`　操纵性（Manipulativeness）

- **通俗解释**：用欺骗、奉承或施压等手段让他人按自己的意愿行事。
  - 依据：`derived_from_items:pid5_manipulativeness 的 5 题`
- **示例题**：`pid5_107` “I’m good at making people do what I want them to do.”　→ 中译：“我擅长让别人按我的意思去做。”（AI 逐条复核 + 仲裁（2026-10-04））；`pid5_125` “Sweet-talking others helps me get what I want.”　→ 中译：“对别人说好话，能帮我得到自己想要的东西。”（AI 逐条复核 + 仲裁（2026-10-04））

#### `pid5_perceptual_dysregulation`　知觉失调（Perceptual Dysregulation）

- **通俗解释**：在清醒状态下出现异常的知觉体验（觉得世界不真实、感到自己与身体或思维分离等）。
  - 依据：`derived_from_items:pid5_perceptual_dysregulation 的 12 题`
- **本维度不测**：不评估器质性或物质所致原因
- **示例题**：`pid5_036` “I can have trouble telling the difference between dreams and waking life.”　→ 中译：“我有时会分不清梦境和清醒时的生活。”（AI 逐条复核 + 仲裁（2026-10-04））；`pid5_037` “Sometimes I get this weird feeling that parts of my body feel like they’re dead or not really me.”　→ 中译：“有时我有种奇怪的感觉，好像身体的某些部分已经死了，或者不真的是我自己的。”（AI 逐条复核 + 仲裁（2026-10-04））

#### `pid5_perseveration`　固执持续（Perseveration）

- **通俗解释**：坚持已经不合时宜的做法，难以转换思路或停止。
  - 依据：`derived_from_items:pid5_perseveration 的 9 题`
- **示例题**：`pid5_046` “It is hard for me to stop an activity, even when it’s time to do so.”　→ 中译：“即使到了该停下的时候，我也很难停止一项活动。”（AI 逐条复核 + 仲裁（2026-10-04））；`pid5_051` “I’ve missed out on things becauseI was busy trying to get something I was doing exactly right.”　→ 中译：“我错过了一些事，因为当时我正忙着把在做的事做到分毫不差。”（AI 逐条复核 + 仲裁（2026-10-04））

#### `pid5_restricted_affectivity`　情感受限（Restricted Affectivity）

- **通俗解释**：情绪表达少、情感体验平淡，对事情缺少反应。
  - 依据：`derived_from_items:pid5_restricted_affectivity 的 7 题`
- **示例题**：`pid5_008` “When it comes to my emotions, people tell me I’m a “cold fish”.”　→ 中译：“说到情绪时，人们说我是个“冷血的人”。”（AI 逐条复核 + 仲裁（2026-10-04））；`pid5_045` “I don’t have very long-lasting emotional reactions to things.”　→ 中译：“我对事情的情绪反应不会持续很久。”（AI 逐条复核 + 仲裁（2026-10-04））

#### `pid5_rigid_perfectionism`　刻板完美主义（Rigid Perfectionism）

- **通俗解释**：对秩序、细节与完美的严格要求，达到影响任务完成的程度。
  - 依据：`derived_from_items:pid5_rigid_perfectionism 的 10 题`
- **示例题**：`pid5_034` “I’ve been told that I spend too much time making sure things are exactly in place.”　→ 中译：“别人说过我花太多时间确认东西都摆在精确的位置上。”（AI 逐条复核 + 仲裁（2026-10-04））；`pid5_049` “People tell me that I focus too much on minor details.”　→ 中译：“人们告诉我，我太关注细枝末节了。”（AI 逐条复核 + 仲裁（2026-10-04））

#### `pid5_risk_taking`　冒险（Risk Taking）

- **通俗解释**：从事有危险、可能造成伤害的活动，不权衡后果。
  - 依据：`derived_from_items:pid5_risk_taking 的 14 题`
- **本维度不测**：不衡量风险判断能力或冒险的动机
- **示例题**：`pid5_003` “People would describe me as reckless.”　→ 中译：“人们会说我这人做事鲁莽。”（AI 逐条复核 + 仲裁（2026-10-04））；`pid5_007` “I avoid risky situations.”　→ 中译：“我会避开有风险的情境。”（AI 逐条复核 + 仲裁（2026-10-04））

#### `pid5_separation_insecurity`　分离不安（Separation Insecurity）

- **通俗解释**：害怕被重要他人遗弃或离开，对被抛弃的迹象过度敏感。
  - 依据：`derived_from_items:pid5_separation_insecurity 的 7 题`
- **示例题**：`pid5_012` “I dread being without someone to love me.”　→ 中译：“我害怕身边没有爱我的人。”（AI 逐条复核 + 仲裁（2026-10-04））；`pid5_050` “I worry a lot about being alone.”　→ 中译：“我非常担心自己会独自一人。”（AI 逐条复核 + 仲裁（2026-10-04））

#### `pid5_submissiveness`　顺从（Submissiveness）

- **通俗解释**：在关系中习惯性让渡主导权、顺从他人的意愿。
  - 依据：`derived_from_items:pid5_submissiveness 的 4 题`
- **本维度不测**：不衡量文化性的礼貌或情境性的让步
- **示例题**：`pid5_009` “I change what I do depending on what others want.”　→ 中译：“我会根据别人的意愿改变自己的做法。”（AI 逐条复核 + 仲裁（2026-10-04））；`pid5_015` “I usually do what others think I should do.”　→ 中译：“我通常按别人认为我应该做的去做。”（AI 逐条复核 + 仲裁（2026-10-04））

#### `pid5_suspiciousness`　猜疑（Suspiciousness）

- **通俗解释**：怀疑他人的动机，觉得别人可能对自己有恶意。
  - 依据：`derived_from_items:pid5_suspiciousness 的 7 题`
- **示例题**：`pid5_002` “Plenty of people are out to get me.”　→ 中译：“很多人都想害我。”（AI 逐条复核 + 仲裁（2026-10-04））；`pid5_103` “Others would take advantage of me if they could.”　→ 中译：“如果有机会，别人就会占我的便宜。”（AI 逐条复核 + 仲裁（2026-10-04））

#### `pid5_unusual_beliefs_experiences`　异常信念与体验（Unusual Beliefs & Experiences）

- **通俗解释**：持有与所在文化环境不符的信念，或报告异常的体验。
  - 依据：`derived_from_items:pid5_unusual_beliefs_experiences 的 8 题`
- **本维度不测**：不区分文化/宗教语境下的正常信念
- **示例题**：`pid5_094` “I have some unusual abilities, like sometimes knowing exactly what someone is thinking.”　→ 中译：“我有些不同寻常的能力，比如有时能准确知道别人在想什么。”（AI 逐条复核 + 仲裁（2026-10-04））；`pid5_099` “I sometimes have heard things that others couldn’t hear.”　→ 中译：“我有时会听到别人听不到的声音。”（AI 逐条复核 + 仲裁（2026-10-04））

#### `pid5_withdrawal`　退缩（Withdrawal）

- **通俗解释**：偏好独处、回避社交接触与人际互动。
  - 依据：`derived_from_items:pid5_withdrawal 的 10 题`
- **本维度不测**：不等于社交焦虑（后者是焦虑性 facets）
- **示例题**：`pid5_010` “I prefer not to get too close to people.”　→ 中译：“我宁愿不和别人走得太近”（AI 逐条复核 + 仲裁（2026-10-04））；`pid5_020` “I keep to myself.”　→ 中译：“我不与人来往。”（AI 逐条复核 + 仲裁（2026-10-04））

### 上级域（由 facet 均分构成）

| 域 id | 中文名 | 英文名 | 构成 facet | 通俗解释 |
|---|---|---|---|---|
| `pid5_negative_affect` | 负性情感 | Negative Affect | `pid5_emotional_lability`、`pid5_anxiousness`、`pid5_separation_insecurity` | 情绪易波动、焦虑紧张、害怕被抛弃的情感范围。 |
| `pid5_detachment` | 疏离 | Detachment | `pid5_withdrawal`、`pid5_anhedonia`、`pid5_intimacy_avoidance` | 回避社交与亲密关系、难以体验愉快。 |
| `pid5_antagonism` | 对抗 | Antagonism | `pid5_manipulativeness`、`pid5_deceitfulness`、`pid5_grandiosity` | 操纵他人、欺骗、自我夸大。 |
| `pid5_disinhibition` | 去抑制 | Disinhibition | `pid5_irresponsibility`、`pid5_impulsivity`、`pid5_distractibility` | 冲动、不负责任、注意力易被拉走。 |
| `pid5_psychoticism` | 精神病性 | Psychoticism | `pid5_unusual_beliefs_experiences`、`pid5_eccentricity`、`pid5_perceptual_dysregulation` | 异常的信念与体验、行为古怪、知觉失调。 |

出处：`data/pid5-scoring-keys.json 的 domains（手册域表 + 正文『five broader trait domains』）；域分 = 3 个 facet 的均分`

> **APA 的 PID-5 手册没有逐 facet 的构念定义**（它是施测与计分手册，只有 facet 名称、题号与计分规则）。因此上表的「通俗解释」一律标注为依据该 facet 题目内容推导（derived_from_items），**不冒充文献定义**。要在文档里给出「文献定义」，需要 DSM-5-TR 正文 Section III 的 AMPD 章节或 Krueger et al. (2012) 原文——本项目未入档这两份来源，故留白，见 evidence_gaps。

### 题文与中译状态（能不能照着填）

- **题文**：220 题，英文原文来自量表包（`data/instruments/<code>.json` 的 `items[].text`）。
- **中译**：220/220 题在**数据层**有中译，来源标记为：「AI 逐条复核 + 仲裁（2026-10-04）」× 219；「AI 逐条复核 + 仲裁（2026-10-04，已按仲裁结论更正）」× 1。
- **中译的单一真相源**：数据层文本库 `data/text-db/text-db.json`（生成器 `tools/build/build_text_db.py`）——那是中译的源头；连接键是 `items[].source_code` ↔ `entries[*].codes`。界面侧的数据包只是读文本库后的**下游再生成物**，界面回退不会影响这里的中译。
- ⚠️ **中译质量**：220 题中译在数据层**齐全**（`data/text-db/text-db.json`，连接键 `items[].source_code` ↔ `entries[*].codes`），但 `zh_source` 全部标记为「**subagent 初译（待人工复核）**」——即**尚未人工复核**的初稿。因此：本项目的 PID-5 中译可用于自填与内部核对，**不得**当作已定稿的正式中文版对外发布；正式使用前应完成人工复核（术语统一、与 25 个 facet 的构念对齐）。
- ⚠️ **中译复核状态**：逐条见 §3 的题项对照表（`zh_source` 列）。标「subagent 初译/重译（待人工复核）」的条目**尚未人工复核**，可作自填与内部核对，**不得**当作定稿中文版发布。

## 3. 计分方法

- **作答选项**：4 点，0–3；锚点：very false or often false / sometimes or somewhat false / sometimes or somewhat true / very true or often true
- **聚合口径**：每个维度由量表包 `scoring` 声明（`sum` / `mean` / `max` / `count_true` …），本文档 §2 表内逐维列出。
- **反向题先做 `3 − x` 变换**（0↔3、1↔2），再按 facet 求均分。　<span title="出处">〔archive/scales/PID-5/manual.pdf（『3 becomes 0, 2 becomes 1, 1 becomes 2, and 0 becomes 3』）；data/pid5-reverse-keys.json 的 scale.transform〕</span>
- **缺答按比例推算（prorate）**：手册允许在该 facet 缺答 ≤25% 时，用「已答题均分 × 题目总数」推算；缺答 >25% 时该 facet 分不应计算。　<span title="出处">〔archive/scales/PID-5/manual.pdf 的 Scoring 段（25% 规则）〕</span>
- **域分是 3 个 facet 分的均分**（不是把全部题加总）。　<span title="出处">〔archive/scales/PID-5/manual.pdf 的 Domain Table；data/instruments/pid-5.json 的 scoring（scope=dimensions）〕</span>
- **注意 `pid5_scoring_keys` 里的 220 题恰好各归一个 facet**（无跨 facet 条目）。　<span title="出处">〔data/pid5-scoring-keys.json 的 extraction_method 与 facets〕</span>

### 3.1 反向计分题清单（**逐项**，共 16 题）

反向题在计分前先做变换（IPIP 系为 `6 − x`，PID-5 为 `3 − x`），再做维度聚合。**下面这个清单与量表包逐项一致**，由 `check_descriptions.py` 强制比对（集合双向相等）。

| # | 题号(order) | 题项 id | 所属维度 |
|---|---|---|---|
| 1 | 7 | `pid5_007` | `pid5_risk_taking` |
| 2 | 30 | `pid5_030` | `pid5_anhedonia` |
| 3 | 35 | `pid5_035` | `pid5_risk_taking` |
| 4 | 58 | `pid5_058` | `pid5_impulsivity` |
| 5 | 87 | `pid5_087` | `pid5_risk_taking` |
| 6 | 90 | `pid5_090` | `pid5_callousness` |
| 7 | 96 | `pid5_096` | `pid5_anxiousness` |
| 8 | 97 | `pid5_097` | `pid5_intimacy_avoidance` |
| 9 | 98 | `pid5_098` | `pid5_risk_taking` |
| 10 | 131 | `pid5_131` | `pid5_suspiciousness` |
| 11 | 142 | `pid5_142` | `pid5_deceitfulness` |
| 12 | 155 | `pid5_155` | `pid5_anhedonia` |
| 13 | 164 | `pid5_164` | `pid5_risk_taking` |
| 14 | 177 | `pid5_177` | `pid5_suspiciousness` |
| 15 | 210 | `pid5_210` | `pid5_irresponsibility` |
| 16 | 215 | `pid5_215` | `pid5_risk_taking` |

**纯 id 清单（便于机器比对）**：

```
pid5_007, pid5_030, pid5_035, pid5_058, pid5_087, pid5_090, pid5_096, pid5_097, pid5_098, pid5_131
pid5_142, pid5_155, pid5_164, pid5_177, pid5_210, pid5_215
```

> PID-5 的反向题**有历史争议**：手册两处原文不一致，本项目采用 16 题（不是 Step 1 正文列的 14 题），逐项清单见 §3.1。

### 3.1b 反向题的历史争议：14 题还是 16 题

PID-5 手册**两处原文自相矛盾**：Step 1 正文列出 14 题，facet 评分表另有 7、30 两题标 `R`（合计 16 题）。本项目采用 **16 题**，并保留三条独立证据：

- **手册 Step 1 正文**逐字列 14 题：35, 58, 87, 90, 96, 97, 98, 131, 142, 155, 164, 177, 210, 215。　<span title="出处">〔archive/scales/PID-5/manual.pdf Step 1；逐字复现于 data/pid5-reverse-keys.json 的 verbatim〕</span>
- **手册 facet 评分表**另有 7、30 两题标 `R`，合计 16 题。　<span title="出处">〔data/pid5-reverse-keys.json 的 reverse_source = manual-facet-table-R〕</span>
- **题面证据**：第 7 题「I avoid risky situations.」是 Risk Taking 的反向表述；第 30 题「I'm an energetic person.」是 Anhedonia 的反向表述。　<span title="出处">〔archive/scales/PID-5/items-extracted.json〕</span>
- **数据证据**（两份独立样本，N=2,471，CC-BY-4.0）：不翻转时第 7 题与 Risk Taking 总分 r = −0.685、第 30 题与 Anhedonia r = −0.519；其余 14 题翻转后为 +0.37…+0.74。　<span title="出处">〔data/pid5-reverse-keys.json 的 evidence.evidence_2_data〕</span>
- **信度证据**：按 16 题翻转后，Anhedonia α .842→**.907**、Risk Taking .838→**.900**（已发表值 .88/.88），两个 facet 的 r_min 由负转正。　<span title="出处">〔data/pid5-reverse-keys.json 的 evidence.evidence_3_reliability〕</span>
- **外部核对**：同 facet 内「自己 facet」相关最高者 218/220；25 facet 的 α 均值 0.860（已发表 0.87）；facet 间相关均值 0.322（已发表 .33）。三项同时吻合。　<span title="出处">〔data/pid5-reverse-keys.json 的 evidence.cross_check；调研报告 research/pid5_psychometrics_survey.md〕</span>

### 3.2 分值范围

- 每题 0–3；facet 分 0–3（均分）；域分 0–3（3 个 facet 均分）。　<span title="出处">〔data/instruments/pid-5.json 的 response_format 与 scoring〕</span>

## 4. 结果解读基准

**本量表有可溯源常模**（解读基准：`percentile_conditional_on_gender_and_age`）。

| 参考样本 | 值 |
|---|---|
| n | 4727 |
| population | 德国 GESIS Panel（总体代表性概率样本） |
| recruitment | 概率抽样面板；完整 220 题的分布由三个全量表供体样本（N=2,471）经贝叶斯桥接投影得到 |
| year | 2026 |
| conditional_cells | 9 个性别×年龄组（如「f [18,35)」） |

- **常模文件**：`data/norms/pid-5.json`（本节的每个数字都取自该文件）
- **细表位置**：`data/norms/pid-5.json`（逐维度百分位 / 逐 raw 百分位与 T 分；本节只摘要）
- ⚠️ **适用性**：常模是**德国总体样本**，不是中国人群；且完整 220 题的百分位是**桥接投影**的结果（4,727 人没有直接做过 220 题）。

### 4.1 怎么读（本量表的解读规则）

- **原始分本身不是百分位。** 来源明确强调（原文重复三次）：得到的是原始分数，**不代表你在人群中的百分比占比**；要看百分位必须查条件常模表（按性别与年龄选 cell）。　<span title="出处">〔archive/norms/pid-5/README.md 与 data/norms/pid-5.json 的 percentile_method〕</span>
- 百分位必须**按性别×年龄**查对应的 cell（9 个 cell）；跨 cell 引用会得到错误的位置。　<span title="出处">〔data/norms/pid-5.json 的 conditional 与 cells〕</span>
- **没有可采用的临床分界值**：文献里 220 题版的分界只见于波斯语版（付费墙），开放获取的那篇是 36 题 BF+M。本项目因此**不给分界、不给分级标签**。　<span title="出处">〔research/pid5_psychometrics_survey.md §2.4 与 §4；data/pid5-reverse-keys.json 的 evidence.survey_report〕</span>

## 5. 信度与出处

### 5.1 内部一致性（α）

| 维度 | α | 来源 |
|---|---|---|
| `Anhedonia` | 0.907 | 本项目自算（N=2471，原始作答 CC-BY-4.0） |
| `Anxiousness` | 0.927 | 本项目自算（N=2471，原始作答 CC-BY-4.0） |
| `Attention Seeking` | 0.869 | 本项目自算（N=2471，原始作答 CC-BY-4.0） |
| `Callousness` | 0.861 | 本项目自算（N=2471，原始作答 CC-BY-4.0） |
| `Deceitfulness` | 0.854 | 本项目自算（N=2471，原始作答 CC-BY-4.0） |
| `Depressivity` | 0.957 | 本项目自算（N=2471，原始作答 CC-BY-4.0） |
| `Distractibility` | 0.911 | 本项目自算（N=2471，原始作答 CC-BY-4.0） |
| `Eccentricity` | 0.942 | 本项目自算（N=2471，原始作答 CC-BY-4.0） |
| `Emotional Lability` | 0.877 | 本项目自算（N=2471，原始作答 CC-BY-4.0） |
| `Grandiosity` | 0.793 | 本项目自算（N=2471，原始作答 CC-BY-4.0） |
| `Hostility` | 0.85 | 本项目自算（N=2471，原始作答 CC-BY-4.0） |
| `Impulsivity` | 0.822 | 本项目自算（N=2471，原始作答 CC-BY-4.0） |
| `Intimacy Avoidance` | 0.856 | 本项目自算（N=2471，原始作答 CC-BY-4.0） |
| `Irresponsibility` | 0.753 | 本项目自算（N=2471，原始作答 CC-BY-4.0） |
| `Manipulativeness` | 0.767 | 本项目自算（N=2471，原始作答 CC-BY-4.0） |
| `Perceptual Dysregulation` | 0.882 | 本项目自算（N=2471，原始作答 CC-BY-4.0） |
| `Perseveration` | 0.842 | 本项目自算（N=2471，原始作答 CC-BY-4.0） |
| `Restricted Affectivity` | 0.82 | 本项目自算（N=2471，原始作答 CC-BY-4.0） |
| `Rigid Perfectionism` | 0.864 | 本项目自算（N=2471，原始作答 CC-BY-4.0） |
| `Risk Taking` | 0.9 | 本项目自算（N=2471，原始作答 CC-BY-4.0） |
| `Separation Insecurity` | 0.854 | 本项目自算（N=2471，原始作答 CC-BY-4.0） |
| `Submissiveness` | 0.845 | 本项目自算（N=2471，原始作答 CC-BY-4.0） |
| `Suspiciousness` | 0.805 | 本项目自算（N=2471，原始作答 CC-BY-4.0） |
| `Unusual Beliefs & Experiences` | 0.809 | 本项目自算（N=2471，原始作答 CC-BY-4.0） |
| `Withdrawal` | 0.922 | 本项目自算（N=2471，原始作答 CC-BY-4.0） |

**口径**：α **由本项目从公开原始作答自算**（N=2,471，两份样本 Fisher z 合并），并与已发表值逐 facet 对照。口径与复现见 archive/norms/pid-5-psychometrics/derived/pid5_item_params_demo.json 与 research/pid5_psychometrics_survey.md。

- 25 个 facet 的自算 α 均值 0.860，已发表均值约 0.87；facet 间相关均值 0.322，已发表约 .33——两项外部核对吻合。　<span title="出处">〔data/pid5-reverse-keys.json 的 evidence.cross_check〕</span>
- 样本构成不是纯一般人群：临床 683 + 非临床 560 + 配额 1,228。临床样本会抬高题目间相关，故 α 可能略高于一般人群。　<span title="出处">〔archive/norms/pid-5-psychometrics/derived/pid5_item_params_demo.json 的 inputs 与 research/pid5_psychometrics_survey.md §5〕</span>

### 5.2 来源与授权

- **citation**：Krueger RF, Derringer J, Markon KE, Watson D, Skodol AE. The Personality Inventory for DSM-5 (PID-5)—Adult.
- **license**：`copyright_permitted`（可再分发：True）— American Psychiatric Association
  - 授权证据：`archive/scales/PID-5/source.json + PDF 页脚原文 (sha256 ce366db46f324ba7…)`
  - 官方链接：https://www.psychiatry.org/getmedia/594673a6-1b9b-4298-8b52-c4c652c4a4e2/APA-DSM5TR-ThePersonalityInventoryForDSM5FullVersionAdult.pdf
- **题序来源**：`archive/scales/PID-5/manual.pdf 的题项区顺序（题号 1..220）`

### 5.3 已知批评与局限（known_critiques）

- **没有已发表的 220 题题级参数表**：Europe PMC 5 组检索式 + 数据仓检索全部止于 facet 级（25 个值）。本项目改为从公开原始作答自算。　<span title="出处">〔research/pid5_psychometrics_survey.md §1.2 与 §2.1〕</span>
- **常模是桥接投影**：4,727 人的概率样本只做了 34 题短表；220 题的分布来自 2,471 人供体样本的桥接。跨版本桥接的误差未在来源中量化。　<span title="出处">〔data/norms/pid-5.json 的 n_note〕</span>
- **本项目的题级参数样本不是纯一般人群**（含临床样本），且 r_min 是极值序统计量、在 N=2,471 下会被系统性低估。　<span title="出处">〔research/pid5_psychometrics_survey.md §5〕</span>

## 6. 解读义务（哪些话不许说）

以下为本量表结果解读的**硬约束**。它们不是风格建议：本项目的每一条对外表述都必须满足。

1. **不得**把原始分说成百分位或「超过多少比例的人」——来源原文对此重复强调三次。　〔出处：archive/norms/pid-5/README.md；data/norms/pid-5.json 的 percentile_method〕
2. **不得**给出临床分界、严重度分级或「确诊/不确诊」的判断（本项目没有可采用的 220 题版分界值）。　〔出处：research/pid5_psychometrics_survey.md §2.4〕
3. **不得**把 PID-5 的高分直接说成「人格障碍」；AMPD 诊断还需人格功能损害（Criterion A）与临床判断。　〔出处：DSM-5 AMPD 结构；data/linkage/dsm5tr-chain.json 的 pid5_interface〕
4. **不得**把 PID-5 的百分位当作常态人格的位置（它测的是适应不良特质，不是大五）。　〔出处：本量表构念范围（25 个适应不良特质 facet）〕
5. **不得**跨性别/年龄 cell 混用常模，也不得对中国用户直接套用德国常模而不说明。　〔出处：data/norms/pid-5.json 的 conditional 与 n_note〕
6. **不得**在结果里暗示诊断标签的中文译名（如把 Callousness 说成「反社会」）：facets 是特质维度名，不是诊断名。　〔出处：25 个 facet 是特质而非 DSM 诊断类别（手册结构）〕

---

## 附录 A　证据与溯源

| 项 | 值 |
|---|---|
| 证据文件 | `content/descriptions/pid-5.json` |
| 量表包 | `data/instruments/pid-5.json` |
| 常模记录 | `data/norms/pid-5.json` |
| 题项 | archive/scales/PID-5/items-extracted.json（提取器 tools/build/build_pid5_items.py；与 PID-5-BF 25/25 交叉核对） |
| 计分键 | data/pid5-scoring-keys.json（生成器 tools/build/build_pid5_scoring_keys.py） |
| 反向键裁决 | data/pid5-reverse-keys.json（含三条独立证据） |
| 手册哈希 | archive/scales/PID-5/manual.pdf sha256 ce366db46f324ba7…（439,682 字节） |
| 常模 | archive/norms/pid-5/norm_tables_long.csv（Zimmermann et al. 2026，CC BY 4.0） |
| 题级参数 | archive/norms/pid-5-psychometrics/derived/pid5_item_params_demo.json（N=2,471，CC-BY-4.0 原始作答） |

### A.1 本项目**没有**拿到依据的地方（如实留白）

- **25 个 facet 的文献构念定义（DSM-5-TR Section III / Krueger et al. 2012）**：APA 的 PID-5 手册只有 facet 名称与计分表，**不含构念定义**；本项目的通俗解释因此全部标注为「依题目内容推导」。要给出正式文献定义需入档 DSM-5-TR Section III 或原始论文，本轮未取得。
- **220 题的题级已发表参数（载荷 / IRT 区分度 / 题间相关矩阵）**：已系统检索（5 组 Europe PMC 检索式 + 通用检索 + 数据仓），确认文献系统性地只发表 facet 级汇总。本项目改以公开原始作答自算（N=2,471）。
- **可采用的临床分界值**：220 题版的唯一分界来源是波斯语版（付费墙）；开放获取的 36 题 BF+M 阈值不能顶替。故本项目只给百分位、不给分界。
- **中国人群常模**：现有常模为德国总体样本；本项目没有中国样本的 PID-5 常模，也不做跨文化转换。
