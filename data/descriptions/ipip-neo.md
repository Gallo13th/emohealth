# IPIP-NEO-300（大五人格 300 题） — 可填量表文档与评估指标

<!-- 本文件由 tools/build/build_descriptions.py 生成，请勿手改。改动请改 content/descriptions/<code>.json 后重跑。 -->

- **量表代码**　`IPIP-NEO`（文档代码 `ipip-neo`）
- **生成器**　`tools/build/build_descriptions.py`　**校验**　`python tools/check/check_descriptions.py`

> 本文档的目标读者是**将要填答这套量表的人**与**读结果的人**：只读本文档就应能回答——测什么、每维怎么算、反向题哪些、分数对照什么表读、哪些话不许说。

---

## 1. 量表是什么 / 测什么

**它是什么**　IPIP 版本的大五人格量表：**300 道自评题，30 个 facet（面向）× 每面向 10 题，归入 5 个域**。题项与量表为公有领域（public domain），可自由使用与再分发。本项目的这一份是 OpenScales 归档的 `IPIP-NEO.osd` 转换而来，施测序为官方的「30 面向交错循环」。

　出处：`archive/ipip/data/OpenScales/scales/ipip/IPIP-NEO/IPIP-NEO.osd；转换器 tools/build_scales.py；题序来源见 data/instruments/ipip-neo.json 的 item_order_source`

**它测什么**　五个大五域（神经质、外向性、开放性、宜人性、尽责性）及其下 30 个 facet。作答方式是 1–5 的自我描述准确度评分（1=非常不符合 … 5=非常符合）。每个 facet 分 = 该 facet 10 题（反向题先做 `6 − x` 变换）的**均分**；每个域分 = 其 6 个 facet 分的**均分**。

　出处：`data/norms/ipip-neo-300.json 的 unit（facet_mean_of_10_items）与 domain_unit（mean_of_6_facets）、reverse_transform（6 - v）`

### 1.1 它**不**测什么（防止误用）

- **不是临床诊断工具**。它测的是常态人格特质分布，不能用来判断任何精神障碍的有无。　<span title="出处">〔IPIP-NEO 的构念范围（30 个 facet 全为常态特质；量表包无任何临床分界）〕</span>
- **不测智力、能力或成就**。facet 里的「想象力」「思辨」是自评的思维倾向，不是认知能力测验。　<span title="出处">〔content/facets/imagination.record.json 与 intellect.record.json 的 construct.does_not_measure〕</span>
- **不做类型学分类**。大五的分数是连续维度，不存在「你是 INTJ」式的类型；把 facet 分数切成类型是误用。　<span title="出处">〔PLAN.md 的反 Barnum 与反类型学立场；本项目 30 个 facet 均为连续分〕</span>
- **不保证跨文化/跨语言等值**。300 题版**没有任何官方中文译本**（官方法定中译只覆盖 120 题版），本项目的 300 题中译是自译，未做认知访谈或等值检验。　<span title="出处">〔content/facets/*.record.json 的 evidence.chinese_note（逐 facet 一致）〕</span>
- **不衡量作答真实性**。300 题版没有效度分量表；粗心作答只能靠外部质量门（本项目另有 quality-gate 标定）识别，量表本身不报告。　<span title="出处">〔data/quality-gate-calibration.json（质量门独立于本量表）；本量表包无 validity 维度〕</span>
- **不是「20 万人常模」的量表**。常模来自 Johnson (2005) 公开的 IPIP-NEO-300 数据集（N=145,388）；项目早先提到的 N=20,993 是另一个更小的子集，两者不可互换引用。　<span title="出处">〔data/norms/ipip-neo-300.json 的 n 与 n_note〕</span>

### 1.2 适用与不适用人群

- **适用**：成年一般人群（自评）。常模样本为 IPIP 官网的**网络施测志愿者**，不是概率抽样。
- **不适用**：无法理解 300 题长度或自评方式者; 18 岁以下（无青少年常模）; 中国人群的临床判断（常模为国际网络样本，不是中国常模）
- 出处：`data/norms/ipip-neo-300.json 的 source 与 n_note；archive/datasets/osf-johnson/raw/IPIP300.dat`

## 2. 维度表

| # | 维度 id | 中文名 | 英文名 | 题目数 | 反向题数 | 聚合 | 通俗解释（本表内） |
|---|---|---|---|---|---|---|---|
| 1 | `achievementstriving` | 追求成就 | Achievement-Striving | 10 | 3 | `mean` | 设定高目标并为之努力的倾向：抱负的高低、对成就的渴望，以及是否愿意为出色而付出额外努力。 |
| 2 | `activitylevel` | 活跃度 | Activity Level | 10 | 5 | `mean` | 生活节奏与能量输出：做事的速度、同时推进多件事的容量，以及总体上偏好快节奏还是从容节奏。 |
| 3 | `adventurousness` | 冒险 | Adventurousness | 10 | 6 | `mean` | 愿意尝试新活动、新地方与新体验的倾向：对熟悉与变化的偏好，以及是否主动走出舒适区。 |
| 4 | `aesthetic_appreciation_artistic_interests` | 审美 | Artistic Interests | 10 | 5 | `mean` | 被艺术与美打动的倾向：对音乐、绘画、文学、自然之美的敏感与投入，以及是否愿意为此花时间。 |
| 5 | `altruism` | 利他 | Altruism | 10 | 5 | `mean` | 主动为他人付出、关心他人处境的倾向：是否愿意花时间与精力帮助别人，以及是否从助人中获得满足。 |
| 6 | `anger` | 愤怒 | Anger | 10 | 5 | `mean` | 体验愤怒、烦躁与挫败感的倾向：发怒的阈值高低、情绪爆发的强度，以及在受挫时保持冷静的难易。 |
| 7 | `anxiety` | 焦虑 | Anxiety | 10 | 5 | `mean` | 个体体验担忧、恐惧、紧张与神经过敏的倾向：对潜在威胁保持警觉，反复思虑尚未发生或已经过去的事，并在压力下感到绷紧。 |
| 8 | `assertiveness` | 决断性 | Assertiveness | 10 | 5 | `mean` | 在人际情境中主动表达、主导与带头的倾向：是否愿意发声、是否习惯掌控局面、以及在群体中是否自然地成为推动者。 |
| 9 | `cautiousness` | 审慎 | Cautiousness | 10 | 7 | `mean` | 行动前思考与权衡的倾向：是否先想再做、是否回避仓促决定，以及对自己冲动行事的克制程度。 |
| 10 | `cheerfulness` | 开朗 | Cheerfulness | 10 | 2 | `mean` | 体验与表达积极情绪的倾向：快乐、热情、满足的基线水平，以及是否容易感到高兴。 |
| 11 | `cooperation` | 合作 | Cooperation | 10 | 7 | `mean` | 面对分歧与冲突时让步、避免对抗的倾向：是否愿意妥协、是否轻易与人争执，以及是否记仇。 |
| 12 | `depression` | 抑郁 | Depression | 10 | 3 | `mean` | 体验低落、悲伤、无望与自我贬低的倾向：情绪基调是否偏灰、是否容易感到无力与不被喜欢。 |
| 13 | `dutifulness` | 责任心 | Dutifulness | 10 | 5 | `mean` | 重视并履行义务、承诺与规范的倾向：是否守约、是否按规矩办事，以及对自己应尽之事的严肃程度。 |
| 14 | `emotionality` | 情感丰富 | Emotionality | 10 | 5 | `mean` | 对自己内在情绪体验的敏感与重视：能否清晰地觉察情绪、是否认为情绪本身值得关注与探索。 |
| 15 | `excitementseeking` | 追求刺激 | Excitement-Seeking | 10 | 2 | `mean` | 渴求强烈刺激与兴奋体验的倾向：对冒险、喧闹、快节奏活动的偏好，以及对平淡状态的不耐受。 |
| 16 | `friendliness` | 友好 | Friendliness | 10 | 5 | `mean` | 对他人抱有 warmth 与亲近意愿的倾向：是否容易对人产生好感、是否乐意花时间与他人相处、以及是否让身边的人感到被接纳 |
| 17 | `gregariousness` | 合群性 | Gregariousness | 10 | 5 | `mean` | 偏好他人陪伴、喜欢人群与热闹场合的倾向：独处时的感受，以及是否主动寻求社交场合。 |
| 18 | `imagination` | 想象力 | Imagination | 10 | 4 | `mean` | 主动运用想象与幻想的倾向：是否喜欢做白日梦、在脑海中构建画面，以及是否让思绪自由漫游。 |
| 19 | `immoderation` | 放纵 | Immoderation | 10 | 5 | `mean` | 难以抵抗诱惑与冲动的倾向：在饮食、消费、娱乐等方面的自我控制能力，以及是否容易在欲望面前失控。 |
| 20 | `intellect` | 思辨 | Intellect | 10 | 5 | `mean` | 喜欢抽象思考、概念讨论与智力探索的倾向：是否享受思辨本身，以及是否主动接触复杂的观念。 |
| 21 | `liberalism` | 价值开放 | Liberalism | 10 | 7 | `mean` | 愿意重新审视既有价值、传统与权威的倾向：是否对不同的观念保持开放，以及是否倾向于挑战约定俗成。 |
| 22 | `modesty_humility` | 谦逊 | Modesty | 10 | 6 | `mean` | 不自我抬高、不炫耀的倾向：如何看待自己的地位与成就，以及是否倾向于谦虚低调。 |
| 23 | `morality` | 道德 | Morality | 10 | 8 | `mean` | 在人际交往中保持坦诚、直率与守诺的倾向：是否回避欺骗与操纵，以及是否在利益面前仍然诚实。 |
| 24 | `orderliness` | 条理性 | Orderliness | 10 | 5 | `mean` | 偏好环境与事务有序整洁的倾向：物品是否归位、安排是否清楚、以及对杂乱的不适程度。 |
| 25 | `selfconsciousness` | 自我意识 | Self-Consciousness | 10 | 4 | `mean` | 在他人面前感到不自在、容易害羞与困窘的倾向：对他人评价的敏感程度，以及在社交场合中的舒适度。 |
| 26 | `selfdiscipline` | 自律 | Self-Discipline | 10 | 5 | `mean` | 启动并坚持执行任务的倾向：能否在想做之前就动手，能否把自己定下的计划推进下去，以及启动环节的阻力有多大。 |
| 27 | `selfefficacy` | 自我效能 | Self-Efficacy | 10 | 4 | `mean` | 对自己有能力把事情做成的信念：面对任务时是否感到胜任，以及对自己办事效率的评价。 |
| 28 | `sympathy` | 同情 | Sympathy | 10 | 6 | `mean` | 对他人的处境与情绪产生共鸣、并被其打动的倾向：是否容易被他人的困难触动，以及是否关心他人的福祉。 |
| 29 | `trust` | 信任 | Trust | 10 | 4 | `mean` | 对他人动机持正面假设的倾向：是否倾向于相信别人是善意的、值得托付的，还是默认需要防备。 |
| 30 | `vulnerability` | 脆弱性 | Vulnerability | 10 | 5 | `mean` | 在压力下难以应对的倾向：面对高负荷、突发变故或紧急情形时，是否容易慌乱、失去判断力或需要他人支援。 |

### 2.1 逐维度构念解释（通俗中文 + 定义 + 不测什么）

#### `achievementstriving`　追求成就（Achievement-Striving）

- **通俗解释**：设定高目标并为之努力的倾向：抱负的高低、对成就的渴望，以及是否愿意为出色而付出额外努力。
  - 依据：`content/facets/achievementstriving.record.json（改述自 Costa & McCrae (1992) NEO-PI-R 专业手册中该面向的定义）`
- **与相邻维度的边界**：与 selfdiscipline 的边界：追求成就是**想要多高**；自律是**能不能做到**。**想拿第一却从不开始的人，追求成就高、自律低。**；与 selfefficacy 的边界：追求成就是**抱负**；自我效能是**信心**。；与 assertiveness 的边界：追求成就是**对目标的驱动**；决断性是**在人群中的主导**。；与 excitementseeking 的边界：追求成就偏**长期目标**；追求刺激偏**即时唤起**。
- **本维度不测**：不测量实际成就或能力；不测量能否启动与坚持（属 C5 自律）；不测量是否相信自己做得到（属 C1 自我效能）；不测量是否追求**外部认可**——这里问的是**想达到什么水平**
- **示例题**：`ipip_neo_271` “Go straight for the goal.”　→ 中译：“直奔目标”（data/scene-taxonomy.json（大五人格，已人工核对））；`ipip_neo_272` “Work hard.”　→ 中译：“工作努力”（data/scene-taxonomy.json（大五人格，已人工核对））

#### `activitylevel`　活跃度（Activity Level）

- **通俗解释**：生活节奏与能量输出：做事的速度、同时推进多件事的容量，以及总体上偏好快节奏还是从容节奏。
  - 依据：`content/facets/activitylevel.record.json（改述自 Costa & McCrae (1992) NEO-PI-R 专业手册中该面向的定义）`
- **与相邻维度的边界**：与 excitementseeking 的边界：活跃度是**基础节奏**（走得快、做得多）；追求刺激是**对强烈体验的渴求**（冒险、喧闹）。节奏快的人未必爱冒险，爱冒险的人也未必日常忙碌。；与 assertiveness 的边界：决断性是**在人群中主导**；活跃度是**个人节奏**。安静但一天做很多事的人是活跃度高、决断性低。；与 gregariousness 的边界：合群性是**寻求他人陪伴**；活跃度是**活动量**。；与 cheerfulness 的边界：开朗是**积极情绪的强度**；活跃度是**动作的速率**。；与 selfdiscipline 的边界：自律是**能否启动并坚持该做的事**；活跃度是**总体节奏快慢**。被逼着忙碌且拖延的人，活跃度可能不低，自律却低。
- **本维度不测**：不测量对强烈刺激的渴求（属 E5 追求刺激）；不测量社交中的主导性（属 E3 决断性）；不测量是否喜欢与人相处（属 E1 友好、E2 合群）；不测量积极情绪的高低（属 E6 开朗）；不测量工作是否自律（属 C5 自律）
- **示例题**：`ipip_neo_091` “Am always busy.”　→ 中译：“总是很忙碌”（data/scene-taxonomy.json（大五人格，已人工核对））；`ipip_neo_092` “Am always on the go.”　→ 中译：“总是在奔波”（data/scene-taxonomy.json（大五人格，已人工核对））

#### `adventurousness`　冒险（Adventurousness）

- **通俗解释**：愿意尝试新活动、新地方与新体验的倾向：对熟悉与变化的偏好，以及是否主动走出舒适区。
  - 依据：`content/facets/adventurousness.record.json（改述自 Costa & McCrae (1992) NEO-PI-R 专业手册中该面向的定义）`
- **与相邻维度的边界**：与 excitementseeking 的边界：冒险偏**新颖性**（没做过的事）；追求刺激偏**唤起强度**（心跳加速）。去一家没吃过的异国餐厅是冒险但不刺激；蹦极是两者兼具。；与 imagination 的边界：冒险是**实际去做**；想象力是**在心里想**。；与 cautiousness 的边界：审慎是**行动前权衡**；冒险是**对新颖的偏好**。；与 liberalism 的边界：冒险偏**体验与行为**；价值开放偏**观念与立场**。
- **本维度不测**：不测量对强烈刺激的渴求（属 E5 追求刺激）；不测量对新观念的兴趣（属 O6 价值开放）；不测量风险承受能力或胆量；不测量旅行频率（受经济条件限制）
- **示例题**：`ipip_neo_151` “Prefer variety to routine.”　→ 中译：“相比固定的日常安排，我更喜欢有变化”（data/scene-taxonomy.json（大五人格，已人工核对））；`ipip_neo_152` “Like to visit new places.”　→ 中译：“喜欢去没去过的地方”（data/scene-taxonomy.json（大五人格，已人工核对））

#### `aesthetic_appreciation_artistic_interests`　审美（Artistic Interests）

- **通俗解释**：被艺术与美打动的倾向：对音乐、绘画、文学、自然之美的敏感与投入，以及是否愿意为此花时间。
  - 依据：`content/facets/aesthetic_appreciation_artistic_interests.record.json（改述自 Costa & McCrae (1992) NEO-PI-R 专业手册中该面向的定义）`
- **与相邻维度的边界**：与 imagination 的边界：审美是**被外物打动**；想象力是**自己生成画面**。；与 intellect 的边界：审美偏**感受与体验**；思辨偏**分析与推理**。；与 emotionality 的边界：审美有**对象**（作品、自然）；情感丰富是**一般性的情绪强度**。；与 adventurousness 的边界：审美是**感受**新体验；冒险是**去做**新事情。
- **本维度不测**：不测量自己创作的能力；不测量是否懂艺术史或技法；不测量想象力（属 O1 想象力）；不测量对娱乐内容的消费量（看剧刷视频不算审美）
- **示例题**：`ipip_neo_131` “Believe in the importance of art.”　→ 中译：“认为艺术是很重要的”（data/scene-taxonomy.json（大五人格，已人工核对））；`ipip_neo_132` “Like music.”　→ 中译：“喜欢音乐”（data/scene-taxonomy.json（大五人格，已人工核对））

#### `altruism`　利他（Altruism）

- **通俗解释**：主动为他人付出、关心他人处境的倾向：是否愿意花时间与精力帮助别人，以及是否从助人中获得满足。
  - 依据：`content/facets/altruism.record.json（改述自 Costa & McCrae (1992) NEO-PI-R 专业手册中该面向的定义）`
- **与相邻维度的边界**：与 sympathy 的边界：同情是**感受到**他人的处境；利他是**为此做点什么**。可以深深共情但从不行动。；与 cooperation 的边界：利他是**主动给予**；合作是**冲突时让步**。；与 friendliness 的边界：友好是**情感温度**；利他是**行为付出**。；与 trust 的边界：利他是**自己的付出**；信任是**对他人的假设**。
- **本维度不测**：不测量是否喜欢与人相处（属 E1 友好、E2 合群）；不测量道德水平（属 A2 道德）；不测量共情能力（属 A6 同情）；不测量的实际付出量（受资源与处境限制）
- **示例题**：`ipip_neo_201` “Make people feel welcome.”　→ 中译：“让别人感到被欢迎”（data/scene-taxonomy.json（大五人格，已人工核对））；`ipip_neo_202` “Anticipate the needs of others.”　→ 中译：“会预先想到别人的需要”（data/scene-taxonomy.json（大五人格，已人工核对））

#### `anger`　愤怒（Anger）

- **通俗解释**：体验愤怒、烦躁与挫败感的倾向：发怒的阈值高低、情绪爆发的强度，以及在受挫时保持冷静的难易。
  - 依据：`content/facets/anger.record.json（改述自 Costa & McCrae (1992) NEO-PI-R 专业手册中该面向的定义）`
- **与相邻维度的边界**：与 anxiety 的边界：愤怒是烦躁、敌意与挫败；焦虑是警觉与畏惧。两者都伴随生理唤醒，但情绪方向不同。；与 cooperation 的边界：合作管的是**面对冲突时是否让步**；愤怒管的是**是否容易起火**。可以易怒但最终让步。；与 immoderation 的边界：放纵管的是**能否控制冲动**（吃、买、赌）；愤怒管的是**情绪本身**。；与 depression 的边界：抑郁是低落与无望；愤怒是激越与敌意。抑郁症常见易怒，但两者在构念上分开。
- **本维度不测**：不测量担忧与紧张（属 N1 焦虑）；不测量表达愤怒的社交技巧；不测量攻击行为的实际发生（那是行为，不是特质）；不测量对外界不满的合理表达
- **示例题**：`ipip_neo_011` “Get angry easily.”　→ 中译：“很容易生气”（data/scene-taxonomy.json（大五人格，已人工核对））；`ipip_neo_012` “Get irritated easily.”　→ 中译：“容易被激怒”（data/scene-taxonomy.json（大五人格，已人工核对））

#### `anxiety`　焦虑（Anxiety）

- **通俗解释**：个体体验担忧、恐惧、紧张与神经过敏的倾向：对潜在威胁保持警觉，反复思虑尚未发生或已经过去的事，并在压力下感到绷紧。
  - 依据：`content/facets/anxiety.record.json（改述自 Costa & McCrae (1992) NEO-PI-R 专业手册中该面向的定义）`
- **与相邻维度的边界**：与 depression 的边界：焦虑指向未来的威胁（"万一……怎么办"）；抑郁指向已发生的丧失或当下的低落（"我不行了"）。担心 ≠ 难过。；与 selfconsciousness 的边界：焦虑是对各类事情的一般性担忧；自我意识特指担心被他人注视、评价或羞辱。若担忧只出现在社交场合，应归入自我意识。；与 vulnerability 的边界：焦虑是慢性的担忧与紧张；脆弱性是在压力下无法应对、容易慌乱或依赖他人。；与 anger 的边界：两者都属神经质且都伴随唤醒，但焦虑是警觉与畏惧，愤怒是烦躁与敌意。
- **本维度不测**：不测量抑郁或低落（属 N3 抑郁）；不测量对社交评价的在意（属 N4 自我意识）；不测量抗压能力或依赖倾向（属 N6 脆弱性）；不测量易怒与挫败感（属 N2 愤怒）；不构成焦虑障碍的诊断或筛查
- **示例题**：`ipip_neo_001` “Worry about things.”　→ 中译：“为很多事情感到担心”（data/scene-taxonomy.json（大五人格，已人工核对））；`ipip_neo_002` “Fear for the worst.”　→ 中译：“担心会发生最糟糕的情况”（data/scene-taxonomy.json（大五人格，已人工核对））

#### `assertiveness`　决断性（Assertiveness）

- **通俗解释**：在人际情境中主动表达、主导与带头的倾向：是否愿意发声、是否习惯掌控局面、以及在群体中是否自然地成为推动者。
  - 依据：`content/facets/assertiveness.record.json（改述自 Costa & McCrae (1992) NEO-PI-R 专业手册中该面向的定义）`
- **与相邻维度的边界**：与 gregariousness 的边界：决断性是**主导**；合群性是**在场**。可以在人群中安静地待着。；与 selfconsciousness 的边界：决断性是**是否愿意出头**；自我意识是**被注视时是否不适**。两者常反向，但一个不自在的人也可能因责任感而站出来。；与 cooperation 的边界：合作是**面对分歧时是否让步**；决断性是**是否主动定调**。；与 activitylevel 的边界：决断性是**社会性的主导**；活跃度是**一般节奏**。
- **本维度不测**：不测量是否喜欢与人相处（属 E1 友好、E2 合群）；不测量攻击性或支配欲（那更接近 N2 愤怒或 A 维度的对立面）；不测量领导能力或职位；不测量能否坚持己见（那属 C6 审慎的对立面）
- **示例题**：`ipip_neo_081` “Take charge.”　→ 中译：“主动接过主导权”（data/scene-taxonomy.json（大五人格，已人工核对））；`ipip_neo_082` “Try to lead others.”　→ 中译：“我会尝试去领导他人”（data/scene-taxonomy.json（大五人格，已人工核对））

#### `cautiousness`　审慎（Cautiousness）

- **通俗解释**：行动前思考与权衡的倾向：是否先想再做、是否回避仓促决定，以及对自己冲动行事的克制程度。
  - 依据：`content/facets/cautiousness.record.json（改述自 Costa & McCrae (1992) NEO-PI-R 专业手册中该面向的定义）`
- **与相邻维度的边界**：与 selfdiscipline 的边界：审慎是**动手前的思考**；自律是**思考后的执行**。过度审慎会拖慢启动，但动机不同。；与 immoderation 的边界：审慎是**认知上的权衡**；放纵是**欲望上的克制**。；与 anxiety 的边界：审慎是**主动的评估**；焦虑是**被动的担忧**。；与 adventurousness 的边界：审慎是**行动前的谨慎**；冒险是**对新颖的偏好**。
- **本维度不测**：不测量是否焦虑或担忧（属 N1 焦虑）；不测量能否抵抗诱惑（属 N5 放纵）；不测量是否保守（属 O6 价值开放）；不测量决断的速度——这里问的是**想不想就做**，不是**做得快不快**
- **示例题**：`ipip_neo_291` “Avoid mistakes.”　→ 中译：“避免犯错”（data/scene-taxonomy.json（大五人格，已人工核对））；`ipip_neo_292` “Choose my words with care.”　→ 中译：“说话前会斟酌用词”（data/scene-taxonomy.json（大五人格，已人工核对））

#### `cheerfulness`　开朗（Cheerfulness）

- **通俗解释**：体验与表达积极情绪的倾向：快乐、热情、满足的基线水平，以及是否容易感到高兴。
  - 依据：`content/facets/cheerfulness.record.json（改述自 Costa & McCrae (1992) NEO-PI-R 专业手册中该面向的定义）`
- **与相邻维度的边界**：与 depression 的边界：两者是同一情绪维度的两端。开朗高分通常对应抑郁低分，但不必完全互补——可以既常感快乐又偶有低落。；与 activitylevel 的边界：开朗是**情绪的高涨**；活跃度是**行为的速率**。；与 friendliness 的边界：开朗是**自己的情绪状态**；友好是**对他人的温度**。；与 excitementseeking 的边界：开朗是**积极情绪的基线**；追求刺激是**对唤起的需要**。
- **本维度不测**：不测量情绪低落的程度（属 N3 抑郁，但两者是同一维度的两端）；不测量幽默感或社交风趣；不测量生活境遇的好坏；不测量是否爱笑（那是表达习惯，不是情绪体验）
- **示例题**：`ipip_neo_111` “Radiate joy.”　→ 中译：“我的快乐会感染周围的人”（data/scene-taxonomy.json（大五人格，已人工核对））；`ipip_neo_112` “Have a lot of fun.”　→ 中译：“生活里有很多好玩的事”（data/scene-taxonomy.json（大五人格，已人工核对））

#### `cooperation`　合作（Cooperation）

- **通俗解释**：面对分歧与冲突时让步、避免对抗的倾向：是否愿意妥协、是否轻易与人争执，以及是否记仇。
  - 依据：`content/facets/cooperation.record.json（改述自 Costa & McCrae (1992) NEO-PI-R 专业手册中该面向的定义）`
- **与相邻维度的边界**：与 anger 的边界：愤怒是**情绪是否被点燃**；合作是**冲突时是否让步**。可以很生气但最终退让。；与 altruism 的边界：合作是**不争**；利他是**给予**。；与 assertiveness 的边界：合作是**退让**；决断性是**主导**。这两者常反向。；与 morality 的边界：合作是**在冲突中让不让步**；道德是**在利益面前诚不诚实**。
- **本维度不测**：不测量是否愿意帮助他人（属 A3 利他）；不测量是否容易发火（属 N2 愤怒）；不测量谈判或博弈能力；不测量是否有原则——这里问的是**冲突时的行为倾向**
- **示例题**：`ipip_neo_211` “Am easy to satisfy.”　→ 中译：“容易满足”（data/scene-taxonomy.json（大五人格，已人工核对））；`ipip_neo_212` “Can't stand confrontations.”　→ 中译：“受不了当面冲突”（data/scene-taxonomy.json（大五人格，已人工核对））

#### `depression`　抑郁（Depression）

- **通俗解释**：体验低落、悲伤、无望与自我贬低的倾向：情绪基调是否偏灰、是否容易感到无力与不被喜欢。
  - 依据：`content/facets/depression.record.json（改述自 Costa & McCrae (1992) NEO-PI-R 专业手册中该面向的定义）`
- **与相邻维度的边界**：与 anxiety 的边界：抑郁指向已发生的丧失或当下的低落；焦虑指向未来的威胁。；与 selfconsciousness 的边界：抑郁是整体性的自我贬低（"我不够好"）；自我意识特指在他人面前的不自在。；与 vulnerability 的边界：抑郁是情绪基调；脆弱性是压力下的应对能力。；与 cheerfulness 的边界：两者是同一维度的两端——抑郁高分通常对应开朗低分，但不必完全互补。
- **本维度不测**：不构成抑郁症的诊断或筛查（那需要临床评估与专门量表）；不测量焦虑与担忧（属 N1 焦虑）；不测量精力与活动量（属 E4 活跃度）；不测量悲伤情绪的**合理性**——因真实丧失而悲伤同样计入
- **示例题**：`ipip_neo_021` “Often feel blue.”　→ 中译：“时常感到忧郁”（data/scene-taxonomy.json（大五人格，已人工核对））；`ipip_neo_022` “Dislike myself.”　→ 中译：“不喜欢自己”（data/scene-taxonomy.json（大五人格，已人工核对））

#### `dutifulness`　责任心（Dutifulness）

- **通俗解释**：重视并履行义务、承诺与规范的倾向：是否守约、是否按规矩办事，以及对自己应尽之事的严肃程度。
  - 依据：`content/facets/dutifulness.record.json（改述自 Costa & McCrae (1992) NEO-PI-R 专业手册中该面向的定义）`
- **与相邻维度的边界**：与 selfdiscipline 的边界：责任心管**外部规范**（该不该做）；自律管**执行**（做不做得到）。**极守规矩但总要人催才能开工的人，责任心高、自律低。**；与 morality 的边界：责任心是**履行义务**；道德是**在利益面前是否诚实**。；与 orderliness 的边界：责任心是**守规范**；条理性是**环境整齐**。；与 liberalism 的边界：责任心是**履行**规范；价值开放是**质疑**规范。
- **本维度不测**：不测量任务能否及时启动（属 C5 自律）；不测量道德诚信（属 A2 道德）；不测量是否盲从——这里问的是**对自己认同的义务的履行**；不测量工作能力
- **示例题**：`ipip_neo_261` “Try to follow the rules.”　→ 中译：“尽量遵守规则”（data/scene-taxonomy.json（大五人格，已人工核对））；`ipip_neo_262` “Keep my promises.”　→ 中译：“信守承诺”（data/scene-taxonomy.json（大五人格，已人工核对））

#### `emotionality`　情感丰富（Emotionality）

- **通俗解释**：对自己内在情绪体验的敏感与重视：能否清晰地觉察情绪、是否认为情绪本身值得关注与探索。
  - 依据：`content/facets/emotionality.record.json（改述自 Costa & McCrae (1992) NEO-PI-R 专业手册中该面向的定义）`
- **与相邻维度的边界**：与 imagination 的边界：情感丰富是**对情绪的觉察**；想象力是**对场景的构建**。；与 intellect 的边界：情感丰富偏**感受**；思辨偏**概念分析**。；与 sympathy 的边界：情感丰富是**对自己情绪**的觉察；同情是**对他人处境**的关切。；与 depression 的边界：抑郁是**情绪基调偏低**；情感丰富是**对情绪的敏感度**，与情绪是正还是负无关。
- **本维度不测**：不测量情绪的**强度**或波动（那属神经质）；不测量对他人的共情（属 A6 同情）；不测量情绪表达能力；不测量心理反思的习惯（那更接近 O5 思辨）
- **示例题**：`ipip_neo_141` “Experience my emotions intensely.”　→ 中译：“能强烈感受到自己的情绪”（data/scene-taxonomy.json（大五人格，已人工核对））；`ipip_neo_142` “Feel others' emotions.”　→ 中译：“能感受到他人的情绪”（data/scene-taxonomy.json（大五人格，已人工核对））

#### `excitementseeking`　追求刺激（Excitement-Seeking）

- **通俗解释**：渴求强烈刺激与兴奋体验的倾向：对冒险、喧闹、快节奏活动的偏好，以及对平淡状态的不耐受。
  - 依据：`content/facets/excitementseeking.record.json（改述自 Costa & McCrae (1992) NEO-PI-R 专业手册中该面向的定义）`
- **与相邻维度的边界**：与 activitylevel 的边界：追求刺激是**要强度**；活跃度是**要速度与量**。一个每天高效工作十小时但从不冒险的人，活跃度高、追求刺激低。；与 adventurousness 的边界：冒险（O4）偏**体验新事物**（新食物、新地方、新观念）；追求刺激（E5）偏**生理与情绪的唤起强度**（喧闹、速度、危险）。；与 gregariousness 的边界：追求刺激要的是**唤起**，合群性要的是**陪伴**。独自飙车满足前者，安静聚会满足后者。；与 cautiousness 的边界：审慎是**行动前权衡**；追求刺激是**对唤起的偏好**。
- **本维度不测**：不测量日常活动量（属 E4 活跃度）；不测量是否喜欢与人相处（属 E1/E2）；不测量风险判断能力；不测量对刺激的实际承受力
- **示例题**：`ipip_neo_101` “Love excitement.”　→ 中译：“喜欢追求刺激”（data/scene-taxonomy.json（大五人格，已人工核对））；`ipip_neo_102` “Seek adventure.”　→ 中译：“喜欢冒险”（data/scene-taxonomy.json（大五人格，已人工核对））

#### `friendliness`　友好（Friendliness）

- **通俗解释**：对他人抱有 warmth 与亲近意愿的倾向：是否容易对人产生好感、是否乐意花时间与他人相处、以及是否让身边的人感到被接纳。
  - 依据：`content/facets/friendliness.record.json（改述自 Costa & McCrae (1992) NEO-PI-R 专业手册中该面向的定义）`
- **与相邻维度的边界**：与 gregariousness 的边界：友好是**对具体他人的温度**；合群性是**对人群数量的需求**。一个喜欢与一两位密友深谈、但回避大群体的人，友好高、合群性低。；与 altruism 的边界：友好是**情感上的接纳**；利他是**行动上的帮助**。可以对人温暖但不主动做事。；与 selfconsciousness 的边界：友好是主动亲近的意愿；自我意识是**被注视时的不适**。；与 trust 的边界：友好是情感温度；信任是对他人动机的**判断**。
- **本维度不测**：不测量社交场合的数量（属 E2 合群性）；不测量在人群中的自在程度（属 N4 自我意识）；不测量社交技巧或人际能力；不测量是否对陌生人保持警惕（那可能属于审慎）
- **示例题**：`ipip_neo_061` “Make friends easily.”　→ 中译：“很容易交到朋友”（data/scene-taxonomy.json（大五人格，已人工核对））；`ipip_neo_062` “Warm up quickly to others.”　→ 中译：“很快就能和别人熟络起来”（data/scene-taxonomy.json（大五人格，已人工核对））

#### `gregariousness`　合群性（Gregariousness）

- **通俗解释**：偏好他人陪伴、喜欢人群与热闹场合的倾向：独处时的感受，以及是否主动寻求社交场合。
  - 依据：`content/facets/gregariousness.record.json（改述自 Costa & McCrae (1992) NEO-PI-R 专业手册中该面向的定义）`
- **与相邻维度的边界**：与 friendliness 的边界：合群性要的是**人数与热闹**；友好要的是**关系的温度**。可以很合群但关系都浅，也可以朋友很少但都很深。；与 excitementseeking 的边界：合群性是**寻求陪伴**；追求刺激是**寻求强度**。安静的两人对弈是合群不高刺激；喧闹的演唱会两者都高。；与 assertiveness 的边界：合群性是**在场**；决断性是**主导**。可以在人群中很安静。；与 activitylevel 的边界：合群性是**与人在一起的量**；活跃度是**活动总量**。
- **本维度不测**：不测量对具体他人的情感温度（属 E1 友好）；不测量在社交中的自在程度（属 N4 自我意识）；不测量社交能力或受欢迎程度；不测量是否喜欢安静的活动（那属 O 开放性）
- **示例题**：`ipip_neo_071` “Love large parties.”　→ 中译：“喜欢参加大型聚会”（data/scene-taxonomy.json（大五人格，已人工核对））；`ipip_neo_072` “Talk to a lot of different people at parties.”　→ 中译：“在聚会上，我会和很多不同的人交谈”（data/scene-taxonomy.json（大五人格，已人工核对））

#### `imagination`　想象力（Imagination）

- **通俗解释**：主动运用想象与幻想的倾向：是否喜欢做白日梦、在脑海中构建画面，以及是否让思绪自由漫游。
  - 依据：`content/facets/imagination.record.json（改述自 Costa & McCrae (1992) NEO-PI-R 专业手册中该面向的定义）`
- **与相邻维度的边界**：与 aesthetic_appreciation_artistic_interests 的边界：想象力是**自己生成画面**；审美是**被作品打动**。；与 intellect 的边界：想象力偏**图像与场景**；思辨偏**概念与推理**。；与 emotionality 的边界：想象力是**认知性的构建**；情感丰富是**情绪体验的强度**。；与 adventurousness 的边界：想象力发生在**心里**；冒险发生在**行动上**。
- **本维度不测**：不测量创造力或艺术才能；不测量是否务实（那更接近 C 维度的对立面）；不测量对艺术的兴趣（属 O2 审美）；不测量思维的深度（属 O5 思辨）
- **示例题**：`ipip_neo_121` “Have a vivid imagination.”　→ 中译：“有丰富的想象力”（data/scene-taxonomy.json（大五人格，已人工核对））；`ipip_neo_122` “Enjoy wild flights of fantasy.”　→ 中译：“喜欢天马行空地幻想”（data/scene-taxonomy.json（大五人格，已人工核对））

#### `immoderation`　放纵（Immoderation）

- **通俗解释**：难以抵抗诱惑与冲动的倾向：在饮食、消费、娱乐等方面的自我控制能力，以及是否容易在欲望面前失控。
  - 依据：`content/facets/immoderation.record.json（改述自 Costa & McCrae (1992) NEO-PI-R 专业手册中该面向的定义）`
- **与相邻维度的边界**：与 selfdiscipline 的边界：自律是**启动**该做的事；放纵是**停止**想做的事。两者常同向但可分离——一个能高效完成工作却在深夜暴食的人，自律不低、放纵却高。；与 excitementseeking 的边界：追求刺激是**主动寻求**强烈体验；放纵是**抵抗不住**已有的诱惑。；与 cautiousness 的边界：审慎是**行动前的思考**；放纵是**欲望面前的克制**。；与 anger 的边界：愤怒是情绪爆发；放纵是欲望失控。
- **本维度不测**：不测量是否自律地推进任务（属 C5 自律）——自律管的是**该做的事做不做**，放纵管的是**想做的事停不停**；不测量成瘾行为（那是临床范畴）；不测量是否享受美食或消费；不测量情绪性的愤怒冲动（属 N2 愤怒）
- **示例题**：`ipip_neo_041` “Often eat too much.”　→ 中译：“经常吃得过多”（data/scene-taxonomy.json（大五人格，已人工核对））；`ipip_neo_042` “Don't know why I do some of the things I do.”　→ 中译：“不明白自己为什么会做某些事”（data/scene-taxonomy.json（大五人格，已人工核对））

#### `intellect`　思辨（Intellect）

- **通俗解释**：喜欢抽象思考、概念讨论与智力探索的倾向：是否享受思辨本身，以及是否主动接触复杂的观念。
  - 依据：`content/facets/intellect.record.json（改述自 Costa & McCrae (1992) NEO-PI-R 专业手册中该面向的定义）`
- **与相邻维度的边界**：与 imagination 的边界：思辨偏**概念与推理**；想象力偏**图像与情节**。；与 aesthetic_appreciation_artistic_interests 的边界：思辨偏**分析**；审美偏**感受**。；与 emotionality 的边界：思辨偏**认知**；情感丰富偏**情绪**。；与 selfefficacy 的边界：自我效能是**相信自己能解决问题**（属尽责性）；思辨是**享受思考过程本身**。
- **本维度不测**：不测量智力水平或学业成绩；不测量知识储备；不测量想象力（属 O1 想象力）；不测量是否爱读书（那可能只是习惯）
- **示例题**：`ipip_neo_161` “Like to solve complex problems.”　→ 中译：“喜欢解复杂的问题”（data/scene-taxonomy.json（大五人格，已人工核对））；`ipip_neo_162` “Love to read challenging material.”　→ 中译：“喜欢阅读有挑战性的材料”（data/scene-taxonomy.json（大五人格，已人工核对））

#### `liberalism`　价值开放（Liberalism）

- **通俗解释**：愿意重新审视既有价值、传统与权威的倾向：是否对不同的观念保持开放，以及是否倾向于挑战约定俗成。
  - 依据：`content/facets/liberalism.record.json（改述自 Costa & McCrae (1992) NEO-PI-R 专业手册中该面向的定义）`
- **与相邻维度的边界**：与 adventurousness 的边界：价值开放偏**观念与立场**；冒险偏**行为与体验**。；与 morality 的边界：道德（A2）管的是**是否诚实守诺**；价值开放管的是**是否质疑既有规范**。可以非常诚实且非常反传统。；与 dutifulness 的边界：责任心是**履行义务**；价值开放是**质疑义务的正当性**。；与 intellect 的边界：价值开放偏**立场**；思辨偏**思考过程**。
- **本维度不测**：不测量具体的政治立场（左/右、保守/自由）；不测量是否守法或有道德；不测量对新体验的兴趣（属 O4 冒险）；不测量批判性思维的能力
- **示例题**：`ipip_neo_171` “Tend to vote for liberal political candidates.”　→ 中译：“倾向于投票给立场开明的政治人物”（data/scene-taxonomy.json（大五人格，已人工核对））；`ipip_neo_172` “Believe that there is no absolute right or wrong.”　→ 中译：“相信没有绝对的对错之分”（data/scene-taxonomy.json（大五人格，已人工核对））

#### `modesty_humility`　谦逊（Modesty）

- **通俗解释**：不自我抬高、不炫耀的倾向：如何看待自己的地位与成就，以及是否倾向于谦虚低调。
  - 依据：`content/facets/modesty_humility.record.json（改述自 Costa & McCrae (1992) NEO-PI-R 专业手册中该面向的定义）`
- **与相邻维度的边界**：与 selfconsciousness 的边界：自我意识是**在他人面前的不适**；谦逊是**对自己价值的定位**。可以自信却不自夸。；与 assertiveness 的边界：决断性是**主动出头**；谦逊是**不自居高位**。；与 morality 的边界：谦逊是**不抬高自己**；道德是**不欺骗他人**。；与 achievementstriving 的边界：追求成就是**想要多高**；谦逊是**如何看待已有的**。
- **本维度不测**：不测量实际的能力或成就水平；不测量自尊高低（低自尊属神经质）；不测量是否愿意帮助他人（属 A3 利他）；不测量社交中的拘谨（属 N4 自我意识）
- **示例题**：`ipip_neo_221` “Dislike being the center of attention.”　→ 中译：“不喜欢成为关注的焦点”（data/scene-taxonomy.json（大五人格，已人工核对））；`ipip_neo_222` “Dislike talking about myself.”　→ 中译：“不喜欢谈论自己”（data/scene-taxonomy.json（大五人格，已人工核对））

#### `morality`　道德（Morality）

- **通俗解释**：在人际交往中保持坦诚、直率与守诺的倾向：是否回避欺骗与操纵，以及是否在利益面前仍然诚实。
  - 依据：`content/facets/morality.record.json（改述自 Costa & McCrae (1992) NEO-PI-R 专业手册中该面向的定义）`
- **与相邻维度的边界**：与 trust 的边界：道德是**自己的诚实**；信任是**对他人动机的判断**。；与 cooperation 的边界：道德管**诚不诚实**；合作管**让不让步**。；与 dutifulness 的边界：责任心（C3）管**履不履行义务**；道德管**在利益面前是否诚实**。；与 modesty_humility 的边界：道德是**不欺骗**；谦逊是**不自我抬高**。
- **本维度不测**：不测量道德水平或人品（这是自我报告，且构念窄得多）；不测量是否守法；不测量对他人的信任（属 A1 信任）；不测量政治或价值立场（属 O6 价值开放）
- **示例题**：`ipip_neo_191` “Would never cheat on my taxes.”　→ 中译：“绝不会在报税上作假”（data/scene-taxonomy.json（大五人格，已人工核对））；`ipip_neo_192` “Stick to the rules.”　→ 中译：“遵守规则”（data/scene-taxonomy.json（大五人格，已人工核对））

#### `orderliness`　条理性（Orderliness）

- **通俗解释**：偏好环境与事务有序整洁的倾向：物品是否归位、安排是否清楚、以及对杂乱的不适程度。
  - 依据：`content/facets/orderliness.record.json（改述自 Costa & McCrae (1992) NEO-PI-R 专业手册中该面向的定义）`
- **与相邻维度的边界**：与 selfdiscipline 的边界：条理性管**环境与物品**；自律管**行动的启动与推进**。**桌面很乱但任务照做的人，自律高、条理性低**——这是最常见的混淆。；与 dutifulness 的边界：条理性是**物理与事务的整齐**；责任心是**对规范的遵守**。；与 cautiousness 的边界：条理性是**结果的状态**；审慎是**行动前的过程**。；与 achievementstriving 的边界：条理性是**秩序偏好**；追求成就是**目标抱负**。
- **本维度不测**：不测量任务能否按时完成（属 C5 自律）；不测量是否守规矩（属 C3 责任心）；不测量工作能力；不测量对秩序的**需求强度**——这里问的是**实际的有序程度与偏好**
- **示例题**：`ipip_neo_251` “Like order.”　→ 中译：“喜欢秩序”（data/scene-taxonomy.json（大五人格，已人工核对））；`ipip_neo_252` “Like to tidy up.”　→ 中译：“喜欢整洁”（data/scene-taxonomy.json（大五人格，已人工核对））

#### `selfconsciousness`　自我意识（Self-Consciousness）

- **通俗解释**：在他人面前感到不自在、容易害羞与困窘的倾向：对他人评价的敏感程度，以及在社交场合中的舒适度。
  - 依据：`content/facets/selfconsciousness.record.json（改述自 Costa & McCrae (1992) NEO-PI-R 专业手册中该面向的定义）`
- **与相邻维度的边界**：与 anxiety 的边界：自我意识特指社交情境中的不自在；焦虑是一般性的担忧。若担忧不限于社交场合，应归入焦虑。；与 assertiveness 的边界：决断性管的是**在人群中主导**；自我意识管的是**在人群中是否自在**。安静但自在 ≠ 自我意识高。；与 friendliness 的边界：友好是主动亲近他人的意愿；自我意识是被注视时的不适。可以很想亲近人但一被注视就紧张。；与 vulnerability 的边界：自我意识限于社交评价情境；脆弱性是广泛的应对困难。
- **本维度不测**：不测量是否喜欢与人相处（属 E1 友好、E2 合群）；不测量一般性的担忧（属 N1 焦虑）；不测量社交技能的高低；不测量是否在意他人**看法本身**——这里问的是**在他人面前的自在程度**
- **示例题**：`ipip_neo_031` “Am easily intimidated.”　→ 中译：“面对强势的人容易被压住”（data/scene-taxonomy.json（大五人格，已人工核对））；`ipip_neo_032` “Am afraid that I will do the wrong thing.”　→ 中译：“担心自己会做错事”（data/scene-taxonomy.json（大五人格，已人工核对））

#### `selfdiscipline`　自律（Self-Discipline）

- **通俗解释**：启动并坚持执行任务的倾向：能否在想做之前就动手，能否把自己定下的计划推进下去，以及启动环节的阻力有多大。
  - 依据：`content/facets/selfdiscipline.record.json（改述自 Costa & McCrae (1992) NEO-PI-R 专业手册中该面向的定义）`
- **与相邻维度的边界**：与 orderliness 的边界：条理性管**环境与物品**是否有序；自律管**行动**能否启动与推进。桌面很乱但任务照做的人，自律高、条理性低。；与 dutifulness 的边界：责任心管**外部规范**；自律管**执行**。极守规矩但总要人催才能开工的人，责任心高、自律低。；与 achievementstriving 的边界：追求成就管**想要多高**；自律管**能不能做到**。想拿第一却从不开始的人，追求成就高、自律低。；与 selfefficacy 的边界：自我效能是**相信自己能做成**；自律是**真的去做**。；与 immoderation 的边界：自律是**该做的事做不做**；放纵是**想做的事停不停**。
- **本维度不测**：不测量环境是否整洁有序（属 C2 条理性）；不测量是否守规矩、尽义务（属 C3 责任心）；不测量抱负高低与成就动机（属 C4 追求成就）；不测量对自己能力的信心（属 C1 自我效能）；不测量能否抵抗诱惑（属 N5 放纵）
- **示例题**：`ipip_neo_281` “Get chores done right away.”　→ 中译：“把该做的杂事马上做掉”（data/scene-taxonomy.json（大五人格，已人工核对））；`ipip_neo_282` “Am always prepared.”　→ 中译：“我总是有所准备”（data/scene-taxonomy.json（大五人格，已人工核对））

#### `selfefficacy`　自我效能（Self-Efficacy）

- **通俗解释**：对自己有能力把事情做成的信念：面对任务时是否感到胜任，以及对自己办事效率的评价。
  - 依据：`content/facets/selfefficacy.record.json（改述自 Costa & McCrae (1992) NEO-PI-R 专业手册中该面向的定义）`
- **与相邻维度的边界**：与 selfdiscipline 的边界：自我效能是**相信能做成**；自律是**真的去做**。两者常同向但可分离——自信却拖沓是常见的组合。；与 achievementstriving 的边界：自我效能是**对能力的判断**；追求成就是**对目标的抱负**。；与 vulnerability 的边界：自我效能是**能力信心**；脆弱性是**压力承受**。；与 assertiveness 的边界：自我效能是**对自己能力的评价**；决断性是**在人群中的行为**。
- **本维度不测**：不测量实际能力或过往成绩；不测量是否自律地推进（属 C5 自律）；不测量自尊或自我价值（那属神经质）；不测量是否喜欢思考（属 O5 思辨）
- **示例题**：`ipip_neo_241` “Complete tasks successfully.”　→ 中译：“能成功完成任务”（data/scene-taxonomy.json（大五人格，已人工核对））；`ipip_neo_242` “Excel in what I do.”　→ 中译：“在自己所从事的领域出类拔萃”（data/scene-taxonomy.json（大五人格，已人工核对））

#### `sympathy`　同情（Sympathy）

- **通俗解释**：对他人的处境与情绪产生共鸣、并被其打动的倾向：是否容易被他人的困难触动，以及是否关心他人的福祉。
  - 依据：`content/facets/sympathy.record.json（改述自 Costa & McCrae (1992) NEO-PI-R 专业手册中该面向的定义）`
- **与相邻维度的边界**：与 altruism 的边界：同情是**感受到**；利他是**做出来**。可以很受触动但不行动。；与 emotionality 的边界：情感丰富是**对自己情绪**的觉察（属开放性）；同情是**对他人处境**的共鸣。；与 friendliness 的边界：友好是**对人的温度**；同情是**对困境的反应**。；与 trust 的边界：同情是**情感反应**；信任是**认知判断**。
- **本维度不测**：不测量是否实际提供帮助（属 A3 利他）；不测量对自己情绪的觉察（属 O3 情感丰富）；不测量道德水平（属 A2 道德）；不测量的共情准确性——这里问的是**被打动的程度**
- **示例题**：`ipip_neo_231` “Sympathize with the homeless.”　→ 中译：“同情流浪汉”（data/scene-taxonomy.json（大五人格，已人工核对））；`ipip_neo_232` “Feel sympathy for those who are worse off than myself.”　→ 中译：“我同情那些处境不如自己的人”（data/scene-taxonomy.json（大五人格，已人工核对））

#### `trust`　信任（Trust）

- **通俗解释**：对他人动机持正面假设的倾向：是否倾向于相信别人是善意的、值得托付的，还是默认需要防备。
  - 依据：`content/facets/trust.record.json（改述自 Costa & McCrae (1992) NEO-PI-R 专业手册中该面向的定义）`
- **与相邻维度的边界**：与 morality 的边界：信任是**对他人动机的判断**；道德是**自己的行事准则**。；与 altruism 的边界：信任是**认知假设**；利他是**行为付出**。可以信任人但不主动帮人。；与 friendliness 的边界：信任是**判断**；友好是**情感温度**。；与 cautiousness 的边界：信任是对**人**的假设；审慎是对**事**的权衡。
- **本维度不测**：不测量是否容易亲近他人（属 E1 友好）；不测量是否天真或缺乏判断力；不测量实际的被骗经历；不测量是否愿意帮助他人（属 A3 利他）
- **示例题**：`ipip_neo_181` “Trust others.”　→ 中译：“信任其他人”（data/scene-taxonomy.json（大五人格，已人工核对））；`ipip_neo_182` “Believe that others have good intentions.”　→ 中译：“相信他人的出发点是好的”（data/scene-taxonomy.json（大五人格，已人工核对））

#### `vulnerability`　脆弱性（Vulnerability）

- **通俗解释**：在压力下难以应对的倾向：面对高负荷、突发变故或紧急情形时，是否容易慌乱、失去判断力或需要他人支援。
  - 依据：`content/facets/vulnerability.record.json（改述自 Costa & McCrae (1992) NEO-PI-R 专业手册中该面向的定义）`
- **与相邻维度的边界**：与 anxiety 的边界：焦虑是慢性的担忧；脆弱性特指**压力下的应对失效**。可以平时不焦虑，一遇高压就慌。；与 selfefficacy 的边界：自我效能是**相信自己能做成事**（属尽责性）；脆弱性是**压力下的承受力**。两者常同向但可分离。；与 depression 的边界：抑郁是情绪基调；脆弱性是压力反应。；与 cautiousness 的边界：审慎是**事前思考**；脆弱性是**事中承受**。
- **本维度不测**：不测量日常的担忧（属 N1 焦虑）；不测量情绪低落（属 N3 抑郁）；不测量实际的能力或资源——这里问的是**主观的应对感受**；不测量独立性与依赖需求的整体倾向
- **示例题**：`ipip_neo_051` “Panic easily.”　→ 中译：“容易慌张”（data/scene-taxonomy.json（大五人格，已人工核对））；`ipip_neo_052` “Become overwhelmed by events.”　→ 中译：“感到被各种事情压得喘不过气来”（data/scene-taxonomy.json（大五人格，已人工核对））

### 各维度的已知批评/数据说明（逐维度）

- **`achievementstriving`**：**本面向与「成就焦虑」在题面上不易区分**：第 3 题（Work hard）与第 5 题（Do more than expected）指向努力，但难以分辨这份努力来自**抱负**还是**不安**。后者更接近神经质。；**分（成就）与「忙碌」在中文语境下常被混同**，作答者可能按「我是不是很忙」而非「我是不是想做到最好」作答。
- **`activitylevel`**：**本面向是全量表 α 最低的一个（.71）**，且题目在内容上并不单一：；· 行为量：第 1、2、3 题（忙碌、奔波、闲暇充实）；· 处理容量：第 4 题（同时处理多件事）；· 反应速度：第 5、10 题（反应快/慢）；· **偏好**而非行为：第 6、7、8、9 题（喜欢慢慢来、不慌不忙、悠闲、顺其自然）；**「行为」与「偏好」混在同一 facet 内，是这一低信度最可能的解释。**作答者在这些题上可能出现「我实际很快，但我向往从容」之类的真实分离。；**官方便携中文译本在该 facet 上的 α 仅为 .422**（见 phase0_ipip_audit §4），为 30 个 facet 中最低——说明这一内容异质性在翻译后可能被放大。；题目诊断（`data/item-diagnostics.json`）显示本面向平均优先级**排名第一**，与上述内容异质性的判断一致。
- **`adventurousness`**：**第 1 题（Am interested in many things）与 O5 思辨在语义上有交集**，可能被读作「兴趣广泛」而非「愿意尝试」。；第 4 题（Dislike new foods）把「冒险」具体化为饮食偏好，对饮食保守但其他方面爱冒险的人会产生偏差。
- **`aesthetic_appreciation_artistic_interests`**：**题目诊断显示本面向存在明显的天花板效应**：第 3 题（Like music）有 **75.7% 的作答者选了两端**（多为「非常符合」），第 5 题（Do not like concerts，反向）极端值比例也达 48%。这类题目几乎不区分个体，会拉低本面向的有效测量范围。；第 3 题（Like music）在当代几乎人人都会同意，作为测量题目的鉴别力极低——这是内容层面的问题，脚手架无法修复。
- **`altruism`**：**「利他」的行为表现受资源、时间与处境限制**：一个忙于生计的人可能内心很想帮人却没有余力，而题目（如 Love to help others）问的是意愿还是行为并不清晰。；第 5 题（Am concerned about others）与 A6 同情的题目语义交叠，两个面向的边界在题面上不够干净。
- **`anger`**：本面向的题目里含有少量攻击性表述（如 Lose my temper、Yell at people），社会赞许性会使部分作答者压低分数。；第 3 题（Get angry easily）与第 4 题（Get irritated easily）在语义上高度接近，存在题目冗余的可能。
- **`anxiety`**：第 10 题（Adapt easily to new situations）语义偏「情境适应」，与本面向其余 9 题的「担忧强度」主轴略有不同。
- **`assertiveness`**：**本面向与「攻击性」在社会认知上容易被混淆**，尤其在中国文化语境下，「主动表达」有时被读作「爱出风头」。脚手架需明确区分。；第 6 题（Take charge）与第 5 题（Try to lead others）语义高度重叠。
- **`cautiousness`**：**「审慎」与「犹豫不决」在题面上不易区分。**第 6 题（Jump into things without thinking，反向）与第 5 题（Make rash decisions，反向）都指向冲动，但难以分辨**有意的权衡**与**因焦虑而无法决定**。后者更接近神经质。；本面向的计分键为 3 正 / 7 反，方向不平衡，会放大默许倾向（见 `tools/check/validate_records.py` V3 告警）。
- **`cheerfulness`**：**开朗与「是否表达情绪」容易混淆**：有些人内心常感愉快但不外露。IPIP 的题目混有体验类（Am often in a good mood）与表达类（Express my joy），本面向的 α 因此受一定影响。；**开朗与生活境遇高度纠缠**：处在顺境中的人开朗分自然较高，但这未必反映稳定的特质。官方指导语要求按「一贯的自己」作答，实际操作中难以保证。
- **`cooperation`**：**本面向是全量表优先级排名第二的 facet**（`data/item-diagnostics.json`）。第 6 题（Get back at others）**空答率 15.3%，为全库最高**——这类带有报复意味的表述会让相当一部分作答者拒绝回答。；**「合作」在中文里偏正面，而本面向的低分端实际是「好争、记仇」**，名称与低分端的行为描述不匹配，作答者可能按「我是不是个愿意合作的人」作答。；第 1 题（Am easy to satisfy）指向的是**知足**而非**让步**，与其余题目的构念略有偏移。
- **`depression`**：**本面向涉及情绪低落，属于需要谨慎处理的内容。** 产品必须明确它不构成抑郁筛查，并在分数偏高时给出寻求专业帮助的路径（escalation 属 Mode B 范畴，v1 未启用）。；第 1 题（Often feel blue）与第 3 题（Am often down in the dumps）语义重叠。；**「悲伤的合理性」无法被量表区分**：因真实丧失而悲伤的人与因气质而低落的人得分相同。这是本面向固有的局限，必须在解读中说明。
- **`dutifulness`**：**特别值得注意：题目诊断显示 C 维度整体的题目-总分相关低于其他维度**，其中第 5 题（Break rules）与第 6 题（Break my promises）为反向题，但**本面向的计分键为 7 正 / 3 反**，方向不平衡，会放大默许倾向（见 `tools/check/validate_records.py` V3 告警）。；「Break rules」这类表述在不同文化中对「规矩」的所指不同，可能被读作「法律」也可能被读作「不合理的潜规则」。
- **`emotionality`**：**题目诊断显示第 1 题（Enjoy examining myself and my life）的题目-总分相关为全库最低（r=.213）**，说明这一题在中文/英文语境下都可能被读成「自省」或「自我分析」，与本面向的「情绪觉察」不是同一件事。这是本面向最需要在脚手架中澄清的题。；本面向的题目混合了**情绪觉察**（Feel others' emotions 除外）与**自我探索兴趣**（Enjoy examining myself），侧面并不单一。
- **`excitementseeking`**：**本面向在中国的社会语境下容易被读作「不负责任」或「爱玩」**，脚手架需明确它是关于唤起偏好的描述，不含褒贬。；第 4 题（Enjoy being reckless）中的 reckless 带有明显的负面色彩，与其余题目的中性表述不一致，可能影响作答。
- **`friendliness`**：`friendliness` 在模型里对应 NEO 的 E1 Warmth，但 IPIP 的题面偏「友好行为」（Make friends easily、Make people feel welcome），与**情感温度**的原始定义略有偏移。；第 5 题（Am interested in people）与第 1 题（Make friends easily）分别指向兴趣与行为，侧面不完全一致。
- **`gregariousness`**：第 1 题（Love large parties）与第 3 题（Enjoy being part of a group）分别针对大群体与一般群体，对「不喜欢大party但喜欢小圈子」的人可能产生矛盾作答。
- **`imagination`**：第 1 题（Have a vivid imagination）与第 2 题（Enjoy day-dreaming）分别指向能力与偏好，侧面略有不同。
- **`immoderation`**：第 5 题（Go on binges）是唯一直接指向「失控」的题，其余多依赖作答者对「放纵」的自我归因，可能受社会赞许性影响。；本面向的各项放纵行为（饮食、消费、娱乐）之间相关不高，构念可能不够单一。
- **`intellect`**：**本面向的名称在中文里极易被读成「智力」**，而它实际测的是**对思考的喜爱程度**，与智力水平不是一回事。这是本面向最需要在脚手架中澄清的一点。；第 1 题（Am interested in many things）在 O4 冒险中出现过同类表述，两个面向的题目存在语义交叠。
- **`liberalism`**：**本面向是全量表中最受文化语境影响的一个，也是政治色彩最重的一个。**在中文语境下，「自由」一词的联想与英文 liberalism 不完全对应，作答者可能按政治立场而非「对传统的开放度」作答。；**题目诊断显示本面向的计分键严重不平衡（3 正 / 7 反）**（见 `tools/check/validate_records.py` 的 V3 告警），这会放大默许倾向（acquiescence）的污染。；拆解自 NEO 的 O6 Values，但 IPIP 的题面较原始定义更直接地指向政治与宗教立场，构念外延在跨文化语境下不稳定。
- **`modesty_humility`**：**题目诊断显示本面向优先级排名第三。**第 1 题（Seldom toot my own horn）与第 3 题（Know the answers to many questions）的题目-总分相关偏低（.348 / .273），且第 1 题空答率 5.2%——**「toot my own horn」这类习语在跨语言时最易失真**，属于 11 类错误中的「习语」。；**「谦逊」与「自信」在中文语境下高度纠缠**，作答者可能把「不自夸」读成「不自信」，而两者在构念上分属不同维度。；IPIP 把 Modesty 与 Humility 合并为一个面向，但 NEO 原始定义偏 Modesty（不自夸），而 Humility（不认为自己高人一等）是另一个构念。**合并后构念外延不清晰。**
- **`morality`**：**社会赞许性是本面向最大的威胁。** 题目诊断显示第 2 题（Use others for my own ends）与第 6 题（Get back at others）的空答率明显偏高——**第 6 题高达 15.3%**（全库平均约 0.4%，是其 38 倍）。这说明部分作答者**拒答**这类题目，而非答「不符合」。；**本面向的计分键严重不平衡（2 正 / 8 反）**，会显著放大默许倾向的污染（见 `tools/check/validate_records.py` V3 告警）。；「道德」这一名称本身带有强烈的评价色彩，作答者可能按「我是不是个好人」作答，而非按「我在利益面前是否诚实」作答。
- **`orderliness`**：**本面向的中文名「条理性」容易与「自律」混为一谈**——日常语中「有条理」常被用作「做事靠谱」的同义替换，但本面向只覆盖**环境与物品的有序**。这是脚手架必须处理的头号混淆。；**第 3 题（Want everything to be "just right."）在机读源中是悬空引用**（key `ipip_E11` 无法解析），正文由官方问卷第 70 题补齐（见 `research/phase1_findings.md` §1.1）。这是本项目修复过的源缺陷，需在本档案中留痕。
- **`selfconsciousness`**：**官方便携中文译本在本面向上的 α 仅 .602**（见 phase0_ipip_audit §4），为 N 维度内较低的一个，需在解读中说明。；本面向与 E1 友好、E3 决断性存在经验上的负相关，作答者可能把「不喜欢社交」误读为「在社交中不自在」。
- **`selfdiscipline`**：本面向的题目混合了「启动速度」（第 3、4 题）与「持续执行」（第 5 题）两个侧面，以及「是否浪费时间」这一偏结果导向的表述（第 7 题）。α=.85 尚可接受，但侧面并不单一。；第 10 题（Postpone decisions）针对**决策**而非行动，与本面向其余题目的对象不同。
- **`selfefficacy`**：**「自我效能」与「自律」在中文里容易被合称为「靠谱」**，作答者可能把「我做事可靠」读成两者都高，而它们实际是两个独立的面向。；第 1 题（Complete tasks successfully）偏向**事实描述**（我是否完成了任务），而非**信心判断**，与自我效能的构念略有偏移。
- **`sympathy`**：**共情包含「情感共鸣」与「认知理解」两个成分，本面向只覆盖前者。**一个能准确理解他人处境但情绪不被牵动的人，在此得分会偏低，但这不代表他缺乏共情能力。；**社会赞许性同样威胁本面向**：承认「别人的困难不太打动我」在道德上不讨喜。
- **`trust`**：**「信任」在中国的社会语境下与「城府」「防人之心」等评价纠缠**，低信任可能被读作「成熟」，高信任可能被读作「幼稚」。此为脚手架需处理的语境问题。；第 4 题（Believe that people are basically moral）指向的是**道德判断**，与「信任」的行为层面略有偏移。
- **`vulnerability`**：本面向的题目（如 Panic easily、Am overwhelmed by events）与 N1 焦虑在语义上接近，作答者可能难以区分「担心」与「撑不住」。；**「脆弱性」听起来带有贬义**，可能在措辞上影响作答者的自我报告意愿。

### 题文与中译状态（能不能照着填）

- **题文**：300 题，英文原文来自量表包（`data/instruments/<code>.json` 的 `items[].text`）。
- **中译**：300/300 题在**数据层**有中译，来源标记为：「data/scene-taxonomy.json（大五人格，已人工核对）」× 300。
- **中译的单一真相源**：数据层文本库 `data/text-db/text-db.json`（生成器 `tools/build/build_text_db.py`）；连接键是 `items[].source_code` ↔ `entries[*].codes`。界面侧数据包只是读文本库后的下游再生成物。
- ⚠️ **中译质量**：300 题中译的**单一真相源是数据层文本库** `data/text-db/text-db.json`，其 `zh_source` 标记为「data/scene-taxonomy.json（大五人格，已人工核对）」——即已人工核对。但注意：这 300 条里只有约 120 题来自官方普通话译本（每 facet 4 题），其余是项目自译（见 §1.1 与 facet 记录的 `item_status`）。
- ⚠️ **中译复核状态**：逐条见 §3 的题项对照表（`zh_source` 列）。标「subagent 初译/重译（待人工复核）」的条目**尚未人工复核**，可作自填与内部核对，**不得**当作定稿中文版发布。

## 3. 计分方法

- **作答选项**：5 点，1–5；锚点（中译）：非常不符合 / 比较不符合 / 中立 / 比较符合 / 非常符合
  - 中译出处：`content/facets/<facet>.record.json 的 administration.response_format.labels_zh（30 个 facet 一致）`
  - 原版（英文/发行版）锚点：Mycket inexakt / Måttligt inexakt / Varken exakt eller inexakt / Måttligt exakt / Mycket exakt
- **回忆窗口 / 指导语**：请描述你**平时一贯**的样子，而不是今天的样子，也不是你希望成为的样子。（官方指导语原文："Describe yourself as you generally are now, not as you wish to be in the future."）　出处：`IPIP-NEO-300 官方问卷指导语；逐 facet 记录于 content/facets/*.record.json 的 administration.recall_window`
- **聚合口径**：每个维度由量表包 `scoring` 声明（`sum` / `mean` / `max` / `count_true` …），本文档 §2 表内逐维列出。
- **反向题先做 `6 − x` 变换**（1↔5、2↔4），再按 facet 求均分；域分为 6 个 facet 分的均分（不是 60 题的均分——两者结果不同）。　<span title="出处">〔data/norms/ipip-neo-300.json 的 reverse_transform 与 domain_unit；data/instruments/ipip-neo.json 的 scoring（aggregation=mean）〕</span>
- **题序是官方的「30 面向交错循环」**：每连续 30 题覆盖全部 30 个面向各 1 题。本项目保留该顺序（作为已发布施测序），但**不声称**交错序在心理测量上优于分块序——归档里没有这类证据。　<span title="出处">〔data/instruments/ipip-neo.json 的 item_order_source；facet 记录的 administration.order_style〕</span>
- 缺答处理：IPIP-NEO-300 没有官方定义的缺答规则；本项目按「只对已答题求均分」处理，并在结果里标注完成度。　<span title="出处">〔本项目实现在 engine/scoring；本量表包未声明缺答规则〕</span>

### 3.1 反向计分题清单（**逐项**，共 148 题）

反向题在计分前先做变换（IPIP 系为 `6 − x`，PID-5 为 `3 − x`），再做维度聚合。**下面这个清单与量表包逐项一致**，由 `check_descriptions.py` 强制比对（集合双向相等）。

| # | 题号(order) | 题项 id | 所属维度 |
|---|---|---|---|
| 1 | 6 | `ipip_neo_006` | `anxiety` |
| 2 | 7 | `ipip_neo_007` | `anxiety` |
| 3 | 8 | `ipip_neo_008` | `anxiety` |
| 4 | 9 | `ipip_neo_009` | `anxiety` |
| 5 | 10 | `ipip_neo_010` | `anxiety` |
| 6 | 16 | `ipip_neo_016` | `anger` |
| 7 | 17 | `ipip_neo_017` | `anger` |
| 8 | 18 | `ipip_neo_018` | `anger` |
| 9 | 19 | `ipip_neo_019` | `anger` |
| 10 | 20 | `ipip_neo_020` | `anger` |
| 11 | 28 | `ipip_neo_028` | `depression` |
| 12 | 29 | `ipip_neo_029` | `depression` |
| 13 | 30 | `ipip_neo_030` | `depression` |
| 14 | 37 | `ipip_neo_037` | `selfconsciousness` |
| 15 | 38 | `ipip_neo_038` | `selfconsciousness` |
| 16 | 39 | `ipip_neo_039` | `selfconsciousness` |
| 17 | 40 | `ipip_neo_040` | `selfconsciousness` |
| 18 | 46 | `ipip_neo_046` | `immoderation` |
| 19 | 47 | `ipip_neo_047` | `immoderation` |
| 20 | 48 | `ipip_neo_048` | `immoderation` |
| 21 | 49 | `ipip_neo_049` | `immoderation` |
| 22 | 50 | `ipip_neo_050` | `immoderation` |
| 23 | 56 | `ipip_neo_056` | `vulnerability` |
| 24 | 57 | `ipip_neo_057` | `vulnerability` |
| 25 | 58 | `ipip_neo_058` | `vulnerability` |
| 26 | 59 | `ipip_neo_059` | `vulnerability` |
| 27 | 60 | `ipip_neo_060` | `vulnerability` |
| 28 | 66 | `ipip_neo_066` | `friendliness` |
| 29 | 67 | `ipip_neo_067` | `friendliness` |
| 30 | 68 | `ipip_neo_068` | `friendliness` |
| 31 | 69 | `ipip_neo_069` | `friendliness` |
| 32 | 70 | `ipip_neo_070` | `friendliness` |
| 33 | 76 | `ipip_neo_076` | `gregariousness` |
| 34 | 77 | `ipip_neo_077` | `gregariousness` |
| 35 | 78 | `ipip_neo_078` | `gregariousness` |
| 36 | 79 | `ipip_neo_079` | `gregariousness` |
| 37 | 80 | `ipip_neo_080` | `gregariousness` |
| 38 | 86 | `ipip_neo_086` | `assertiveness` |
| 39 | 87 | `ipip_neo_087` | `assertiveness` |
| 40 | 88 | `ipip_neo_088` | `assertiveness` |
| 41 | 89 | `ipip_neo_089` | `assertiveness` |
| 42 | 90 | `ipip_neo_090` | `assertiveness` |
| 43 | 96 | `ipip_neo_096` | `activitylevel` |
| 44 | 97 | `ipip_neo_097` | `activitylevel` |
| 45 | 98 | `ipip_neo_098` | `activitylevel` |
| 46 | 99 | `ipip_neo_099` | `activitylevel` |
| 47 | 100 | `ipip_neo_100` | `activitylevel` |
| 48 | 109 | `ipip_neo_109` | `excitementseeking` |
| 49 | 110 | `ipip_neo_110` | `excitementseeking` |
| 50 | 119 | `ipip_neo_119` | `cheerfulness` |
| 51 | 120 | `ipip_neo_120` | `cheerfulness` |
| 52 | 127 | `ipip_neo_127` | `imagination` |
| 53 | 128 | `ipip_neo_128` | `imagination` |
| 54 | 129 | `ipip_neo_129` | `imagination` |
| 55 | 130 | `ipip_neo_130` | `imagination` |
| 56 | 136 | `ipip_neo_136` | `aesthetic_appreciation_artistic_interests` |
| 57 | 137 | `ipip_neo_137` | `aesthetic_appreciation_artistic_interests` |
| 58 | 138 | `ipip_neo_138` | `aesthetic_appreciation_artistic_interests` |
| 59 | 139 | `ipip_neo_139` | `aesthetic_appreciation_artistic_interests` |
| 60 | 140 | `ipip_neo_140` | `aesthetic_appreciation_artistic_interests` |
| 61 | 146 | `ipip_neo_146` | `emotionality` |
| 62 | 147 | `ipip_neo_147` | `emotionality` |
| 63 | 148 | `ipip_neo_148` | `emotionality` |
| 64 | 149 | `ipip_neo_149` | `emotionality` |
| 65 | 150 | `ipip_neo_150` | `emotionality` |
| 66 | 155 | `ipip_neo_155` | `adventurousness` |
| 67 | 156 | `ipip_neo_156` | `adventurousness` |
| 68 | 157 | `ipip_neo_157` | `adventurousness` |
| 69 | 158 | `ipip_neo_158` | `adventurousness` |
| 70 | 159 | `ipip_neo_159` | `adventurousness` |
| 71 | 160 | `ipip_neo_160` | `adventurousness` |
| 72 | 166 | `ipip_neo_166` | `intellect` |
| 73 | 167 | `ipip_neo_167` | `intellect` |
| 74 | 168 | `ipip_neo_168` | `intellect` |
| 75 | 169 | `ipip_neo_169` | `intellect` |
| 76 | 170 | `ipip_neo_170` | `intellect` |
| 77 | 174 | `ipip_neo_174` | `liberalism` |
| 78 | 175 | `ipip_neo_175` | `liberalism` |
| 79 | 176 | `ipip_neo_176` | `liberalism` |
| 80 | 177 | `ipip_neo_177` | `liberalism` |
| 81 | 178 | `ipip_neo_178` | `liberalism` |
| 82 | 179 | `ipip_neo_179` | `liberalism` |
| 83 | 180 | `ipip_neo_180` | `liberalism` |
| 84 | 187 | `ipip_neo_187` | `trust` |
| 85 | 188 | `ipip_neo_188` | `trust` |
| 86 | 189 | `ipip_neo_189` | `trust` |
| 87 | 190 | `ipip_neo_190` | `trust` |
| 88 | 193 | `ipip_neo_193` | `morality` |
| 89 | 194 | `ipip_neo_194` | `morality` |
| 90 | 195 | `ipip_neo_195` | `morality` |
| 91 | 196 | `ipip_neo_196` | `morality` |
| 92 | 197 | `ipip_neo_197` | `morality` |
| 93 | 198 | `ipip_neo_198` | `morality` |
| 94 | 199 | `ipip_neo_199` | `morality` |
| 95 | 200 | `ipip_neo_200` | `morality` |
| 96 | 206 | `ipip_neo_206` | `altruism` |
| 97 | 207 | `ipip_neo_207` | `altruism` |
| 98 | 208 | `ipip_neo_208` | `altruism` |
| 99 | 209 | `ipip_neo_209` | `altruism` |
| 100 | 210 | `ipip_neo_210` | `altruism` |
| 101 | 214 | `ipip_neo_214` | `cooperation` |
| 102 | 215 | `ipip_neo_215` | `cooperation` |
| 103 | 216 | `ipip_neo_216` | `cooperation` |
| 104 | 217 | `ipip_neo_217` | `cooperation` |
| 105 | 218 | `ipip_neo_218` | `cooperation` |
| 106 | 219 | `ipip_neo_219` | `cooperation` |
| 107 | 220 | `ipip_neo_220` | `cooperation` |
| 108 | 225 | `ipip_neo_225` | `modesty_humility` |
| 109 | 226 | `ipip_neo_226` | `modesty_humility` |
| 110 | 227 | `ipip_neo_227` | `modesty_humility` |
| 111 | 228 | `ipip_neo_228` | `modesty_humility` |
| 112 | 229 | `ipip_neo_229` | `modesty_humility` |
| 113 | 230 | `ipip_neo_230` | `modesty_humility` |
| 114 | 235 | `ipip_neo_235` | `sympathy` |
| 115 | 236 | `ipip_neo_236` | `sympathy` |
| 116 | 237 | `ipip_neo_237` | `sympathy` |
| 117 | 238 | `ipip_neo_238` | `sympathy` |
| 118 | 239 | `ipip_neo_239` | `sympathy` |
| 119 | 240 | `ipip_neo_240` | `sympathy` |
| 120 | 247 | `ipip_neo_247` | `selfefficacy` |
| 121 | 248 | `ipip_neo_248` | `selfefficacy` |
| 122 | 249 | `ipip_neo_249` | `selfefficacy` |
| 123 | 250 | `ipip_neo_250` | `selfefficacy` |
| 124 | 256 | `ipip_neo_256` | `orderliness` |
| 125 | 257 | `ipip_neo_257` | `orderliness` |
| 126 | 258 | `ipip_neo_258` | `orderliness` |
| 127 | 259 | `ipip_neo_259` | `orderliness` |
| 128 | 260 | `ipip_neo_260` | `orderliness` |
| 129 | 266 | `ipip_neo_266` | `dutifulness` |
| 130 | 267 | `ipip_neo_267` | `dutifulness` |
| 131 | 268 | `ipip_neo_268` | `dutifulness` |
| 132 | 269 | `ipip_neo_269` | `dutifulness` |
| 133 | 270 | `ipip_neo_270` | `dutifulness` |
| 134 | 278 | `ipip_neo_278` | `achievementstriving` |
| 135 | 279 | `ipip_neo_279` | `achievementstriving` |
| 136 | 280 | `ipip_neo_280` | `achievementstriving` |
| 137 | 286 | `ipip_neo_286` | `selfdiscipline` |
| 138 | 287 | `ipip_neo_287` | `selfdiscipline` |
| 139 | 288 | `ipip_neo_288` | `selfdiscipline` |
| 140 | 289 | `ipip_neo_289` | `selfdiscipline` |
| 141 | 290 | `ipip_neo_290` | `selfdiscipline` |
| 142 | 294 | `ipip_neo_294` | `cautiousness` |
| 143 | 295 | `ipip_neo_295` | `cautiousness` |
| 144 | 296 | `ipip_neo_296` | `cautiousness` |
| 145 | 297 | `ipip_neo_297` | `cautiousness` |
| 146 | 298 | `ipip_neo_298` | `cautiousness` |
| 147 | 299 | `ipip_neo_299` | `cautiousness` |
| 148 | 300 | `ipip_neo_300` | `cautiousness` |

**纯 id 清单（便于机器比对）**：

```
ipip_neo_006, ipip_neo_007, ipip_neo_008, ipip_neo_009, ipip_neo_010, ipip_neo_016, ipip_neo_017, ipip_neo_018, ipip_neo_019, ipip_neo_020
ipip_neo_028, ipip_neo_029, ipip_neo_030, ipip_neo_037, ipip_neo_038, ipip_neo_039, ipip_neo_040, ipip_neo_046, ipip_neo_047, ipip_neo_048
ipip_neo_049, ipip_neo_050, ipip_neo_056, ipip_neo_057, ipip_neo_058, ipip_neo_059, ipip_neo_060, ipip_neo_066, ipip_neo_067, ipip_neo_068
ipip_neo_069, ipip_neo_070, ipip_neo_076, ipip_neo_077, ipip_neo_078, ipip_neo_079, ipip_neo_080, ipip_neo_086, ipip_neo_087, ipip_neo_088
ipip_neo_089, ipip_neo_090, ipip_neo_096, ipip_neo_097, ipip_neo_098, ipip_neo_099, ipip_neo_100, ipip_neo_109, ipip_neo_110, ipip_neo_119
ipip_neo_120, ipip_neo_127, ipip_neo_128, ipip_neo_129, ipip_neo_130, ipip_neo_136, ipip_neo_137, ipip_neo_138, ipip_neo_139, ipip_neo_140
ipip_neo_146, ipip_neo_147, ipip_neo_148, ipip_neo_149, ipip_neo_150, ipip_neo_155, ipip_neo_156, ipip_neo_157, ipip_neo_158, ipip_neo_159
ipip_neo_160, ipip_neo_166, ipip_neo_167, ipip_neo_168, ipip_neo_169, ipip_neo_170, ipip_neo_174, ipip_neo_175, ipip_neo_176, ipip_neo_177
ipip_neo_178, ipip_neo_179, ipip_neo_180, ipip_neo_187, ipip_neo_188, ipip_neo_189, ipip_neo_190, ipip_neo_193, ipip_neo_194, ipip_neo_195
ipip_neo_196, ipip_neo_197, ipip_neo_198, ipip_neo_199, ipip_neo_200, ipip_neo_206, ipip_neo_207, ipip_neo_208, ipip_neo_209, ipip_neo_210
ipip_neo_214, ipip_neo_215, ipip_neo_216, ipip_neo_217, ipip_neo_218, ipip_neo_219, ipip_neo_220, ipip_neo_225, ipip_neo_226, ipip_neo_227
ipip_neo_228, ipip_neo_229, ipip_neo_230, ipip_neo_235, ipip_neo_236, ipip_neo_237, ipip_neo_238, ipip_neo_239, ipip_neo_240, ipip_neo_247
ipip_neo_248, ipip_neo_249, ipip_neo_250, ipip_neo_256, ipip_neo_257, ipip_neo_258, ipip_neo_259, ipip_neo_260, ipip_neo_266, ipip_neo_267
ipip_neo_268, ipip_neo_269, ipip_neo_270, ipip_neo_278, ipip_neo_279, ipip_neo_280, ipip_neo_286, ipip_neo_287, ipip_neo_288, ipip_neo_289
ipip_neo_290, ipip_neo_294, ipip_neo_295, ipip_neo_296, ipip_neo_297, ipip_neo_298, ipip_neo_299, ipip_neo_300
```

> 本题库的 148 道反向题由**量表包 `items[].key == -1` 逐项导出**，并与 Johnson (2005) 官方计分表逐项核对过：官方 148 项、本项目 148 项、交集 148 项，三者完全一致。

### 3.2 分值范围

- **facet 分：1–5（10 题均分）；域分：1–5（6 个 facet 均分）**。原始分不是求和，不要按 10–50 或 60–300 报告。　<span title="出处">〔data/norms/ipip-neo-300.json 的 unit / domain_unit；data/instruments/ipip-neo.json 的 scoring〕</span>
- UK 常模的分带是按**求和口径**印的（facet 10–50、域 60–300），与本项目的均分口径不同；换算前必须先对齐口径。　<span title="出处">〔content/facets/*.record.json 的 norms.bands_values / domain_bands_values（求和分带）〕</span>

## 4. 结果解读基准

**本量表有可溯源常模**（解读基准：`percentile`）。

| 参考样本 | 值 |
|---|---|
| n | 145388 |
| population | IPIP 官网网络施测志愿者（国际样本，非概率抽样） |
| recruitment | 来源文件为 Johnson (2005) 公开数据集；本项目未获得独立的招募说明（见 evidence_gaps） |
| year | 2005 |
| records_scanned | 307313 |

- **常模文件**：`data/norms/ipip-neo.json`（本节的每个数字都取自该文件）
- **细表位置**：`data/norms/ipip-neo-300.json`（逐维度百分位 / 逐 raw 百分位与 T 分；本节只摘要）
- ⚠️ **适用性**：常模来自国际网络样本（IPIP 官网志愿者），**不是中国人群常模**；且为「平时一贯」自评，与临床样本不可比。

### 4.0 常模摘要（自动取自常模文件）

| 维度 | 单位 | 均值 | 标准差 |
|---|---|---|---|
| `achievementstriving` | facet_mean_of_10_items | 3.2931 | 0.348 |
| `activitylevel` | facet_mean_of_10_items | 3.4469 | 0.3894 |
| `adventurousness` | facet_mean_of_10_items | 3.3277 | 0.3917 |
| `aesthetic_appreciation_artistic_interests` | facet_mean_of_10_items | 3.1613 | 0.3054 |
| `altruism` | facet_mean_of_10_items | 2.9267 | 0.2871 |
| `anger` | facet_mean_of_10_items | 2.9685 | 0.2997 |
| `anxiety` | facet_mean_of_10_items | 3.1619 | 0.3363 |
| `assertiveness` | facet_mean_of_10_items | 3.1014 | 0.3725 |
| `cautiousness` | facet_mean_of_10_items | 3.1037 | 0.5577 |
| `cheerfulness` | facet_mean_of_10_items | 3.398 | 0.5196 |
| `cooperation` | facet_mean_of_10_items | 2.9212 | 0.522 |
| `depression` | facet_mean_of_10_items | 2.8534 | 0.5017 |
| `dutifulness` | facet_mean_of_10_items | 3.0 | 0.2675 |
| `emotionality` | facet_mean_of_10_items | 3.1459 | 0.3988 |
| `excitementseeking` | facet_mean_of_10_items | 3.0472 | 0.5625 |
| `friendliness` | facet_mean_of_10_items | 3.1175 | 0.3002 |
| `gregariousness` | facet_mean_of_10_items | 3.1636 | 0.3481 |
| `imagination` | facet_mean_of_10_items | 3.1062 | 0.3234 |
| `immoderation` | facet_mean_of_10_items | 3.0733 | 0.3804 |
| `intellect` | facet_mean_of_10_items | 2.9762 | 0.3206 |
| `liberalism` | facet_mean_of_10_items | 3.0339 | 0.411 |
| `modesty_humility` | facet_mean_of_10_items | 2.9673 | 0.3918 |
| `morality` | facet_mean_of_10_items | 2.5257 | 0.4978 |
| `orderliness` | facet_mean_of_10_items | 3.2408 | 0.3943 |
| `selfconsciousness` | facet_mean_of_10_items | 3.0724 | 0.3659 |
| `selfdiscipline` | facet_mean_of_10_items | 3.0199 | 0.3342 |
| `selfefficacy` | facet_mean_of_10_items | 3.2213 | 0.3059 |
| `sympathy` | facet_mean_of_10_items | 2.9958 | 0.3499 |
| `trust` | facet_mean_of_10_items | 3.142 | 0.3284 |
| `vulnerability` | facet_mean_of_10_items | 3.2476 | 0.3547 |
| `agreeableness` | mean_of_6_facets | 2.9131 | 0.2304 |
| `conscientiousness` | mean_of_6_facets | 3.1465 | 0.1998 |
| `extraversion` | mean_of_6_facets | 3.2124 | 0.2319 |
| `neuroticism` | mean_of_6_facets | 3.0628 | 0.2306 |
| `openness` | mean_of_6_facets | 3.1252 | 0.1778 |

> 逐百分位表（1..99）在常模文件里；本表只摘要均值/标准差，避免正文与细表出现**两个真相源**。

## 5. 信度与出处

### 5.1 内部一致性（α）

| 维度 | α | 来源 |
|---|---|---|
| `achievementstriving` | 0.78 | OpenScales IPIP-NEO.osd（源自 Goldberg 的 ESCS 数据） |
| `activitylevel` | 0.71 | OpenScales IPIP-NEO.osd（源自 Goldberg 的 ESCS 数据） |
| `adventurousness` | 0.77 | OpenScales IPIP-NEO.osd（源自 Goldberg 的 ESCS 数据） |
| `aesthetic_appreciation_artistic_interests` | 0.84 | OpenScales IPIP-NEO.osd（源自 Goldberg 的 ESCS 数据） |
| `altruism` | 0.77 | OpenScales IPIP-NEO.osd（源自 Goldberg 的 ESCS 数据） |
| `anger` | 0.88 | OpenScales IPIP-NEO.osd（源自 Goldberg 的 ESCS 数据） |
| `anxiety` | 0.83 | OpenScales IPIP-NEO.osd（源自 Goldberg 的 ESCS 数据） |
| `assertiveness` | 0.84 | OpenScales IPIP-NEO.osd（源自 Goldberg 的 ESCS 数据） |
| `cautiousness` | 0.76 | OpenScales IPIP-NEO.osd（源自 Goldberg 的 ESCS 数据） |
| `cheerfulness` | 0.81 | OpenScales IPIP-NEO.osd（源自 Goldberg 的 ESCS 数据） |
| `cooperation` | 0.73 | OpenScales IPIP-NEO.osd（源自 Goldberg 的 ESCS 数据） |
| `depression` | 0.88 | OpenScales IPIP-NEO.osd（源自 Goldberg 的 ESCS 数据） |
| `dutifulness` | 0.71 | OpenScales IPIP-NEO.osd（源自 Goldberg 的 ESCS 数据） |
| `emotionality` | 0.81 | OpenScales IPIP-NEO.osd（源自 Goldberg 的 ESCS 数据） |
| `excitementseeking` | 0.78 | OpenScales IPIP-NEO.osd（源自 Goldberg 的 ESCS 数据） |
| `friendliness` | 0.87 | OpenScales IPIP-NEO.osd（源自 Goldberg 的 ESCS 数据） |
| `gregariousness` | 0.79 | OpenScales IPIP-NEO.osd（源自 Goldberg 的 ESCS 数据） |
| `imagination` | 0.83 | OpenScales IPIP-NEO.osd（源自 Goldberg 的 ESCS 数据） |
| `immoderation` | 0.77 | OpenScales IPIP-NEO.osd（源自 Goldberg 的 ESCS 数据） |
| `intellect` | 0.86 | OpenScales IPIP-NEO.osd（源自 Goldberg 的 ESCS 数据） |
| `liberalism` | 0.86 | OpenScales IPIP-NEO.osd（源自 Goldberg 的 ESCS 数据） |
| `modesty_humility` | 0.77 | OpenScales IPIP-NEO.osd（源自 Goldberg 的 ESCS 数据） |
| `morality` | 0.75 | OpenScales IPIP-NEO.osd（源自 Goldberg 的 ESCS 数据） |
| `orderliness` | 0.82 | OpenScales IPIP-NEO.osd（源自 Goldberg 的 ESCS 数据） |
| `selfconsciousness` | 0.8 | OpenScales IPIP-NEO.osd（源自 Goldberg 的 ESCS 数据） |
| `selfdiscipline` | 0.85 | OpenScales IPIP-NEO.osd（源自 Goldberg 的 ESCS 数据） |
| `selfefficacy` | 0.78 | OpenScales IPIP-NEO.osd（源自 Goldberg 的 ESCS 数据） |
| `sympathy` | 0.75 | OpenScales IPIP-NEO.osd（源自 Goldberg 的 ESCS 数据） |
| `trust` | 0.82 | OpenScales IPIP-NEO.osd（源自 Goldberg 的 ESCS 数据） |
| `vulnerability` | 0.82 | OpenScales IPIP-NEO.osd（源自 Goldberg 的 ESCS 数据） |

**口径**：α 逐 facet 取自 OpenScales `IPIP-NEO.osd`（源自 Goldberg 的 ESCS 数据），**不是本项目自算**。30 个 facet 的 α 范围约 0.71–0.88；facet 记录另给出由 α 与分带反推的 SEM（标注为 DERIVED，含 ±0.5 分舍入不确定性）。

- 测量噪音下限有独立文献依据：Kohút et al. (2020) 报告 facet 层 6 个月重测相关约 .70，facet 记录据此给出「变动小于约 0.15–0.2 SD 属测量噪音」的用户级规则。　<span title="出处">〔archive/literature/interpretation/kohut2020_bfi2-slovak-6month-retest.pdf（逐 facet 记录于 content/facets/*.record.json 的 reliability.noise_floor）〕</span>

### 5.2 来源与授权

- **citation**：Goldberg, L. R. (1999). A broad-bandwidth, public-domain, personality inventory measuring the lower-level facets of several five-factor models. In I. Mervielde, I. Deary, F. De Fruyt, & F. Ostendorf (Eds.), Personality Psychology in Europe (Vol. 7, pp. 7-28). Tilburg University Press.
- **license**：`public_domain`（可再分发：True）— OpenScales Project
  - 授权证据：`archive/ipip/data/OpenScales/scales/ipip/IPIP-NEO/IPIP-NEO.osd（scale_info.license）`
  - 官方链接：https://ipip.ori.org/newNEOKey.htm
- **题序来源**：`archive/ipip/data/OpenScales/scales/ipip/IPIP-NEO/IPIP-NEO.osd → definition.items 顺序`

### 5.3 已知批评与局限（known_critiques）

- 300 题版的**中译是自译**，官方译本只覆盖 120 题版（每 facet 4 题）且 IPIP 官方声明未经其验证；因此「题目 10 题里 4 题用官方译、6 题自译」，跨语言的分数可比性没有证据。
- 常模是**网络志愿者**样本，不是概率抽样；用它做「与一般人比较」时会带上志愿者偏差（教育程度、年龄结构、网络使用倾向）。　<span title="出处">〔data/norms/ipip-neo-300.json 的 n_note 与 source〕</span>
- IPIP-NEO-300 是 IPIP 对 NEO-PI-R 的**公有领域再实现**，不是 NEO-PI-R 本身；两者的 facet 划分与题目不同，不能把本量表的分数直接当作 NEO-PI-R 的分数。　<span title="出处">〔archive/literature/personality/goldberg1999_ipip-300.pdf 与 goldberg2006_ipip-public-domain.pdf〕</span>

## 6. 解读义务（哪些话不许说）

以下为本量表结果解读的**硬约束**。它们不是风格建议：本项目的每一条对外表述都必须满足。

1. **不得**把 facet 或域分数说成「类型」或「人格障碍」（大五是连续特质，不是类型学；临床判断需另用临床工具）。　〔出处：PLAN.md 的反 Barnum 立场〕
2. **不得**用百分位做「你比 X% 的人更…」之外的具体断言（例如「你不适合某职业」）；常模是网络志愿者样本，且职业/临床决策需要专门工具与标准。　〔出处：data/norms/ipip-neo-300.json 的 n_note（非概率抽样）〕
3. **不得**把自译题面的分数与英文原版常模直接比较而不说明翻译风险（facet 记录逐条列出中文语境下的读法风险）。　〔出处：content/facets/*.record.json 的 evidence.chinese_note 与 items[].scaffolding.localization_note〕
4. **不得**把「回答了很多题」当成「结果更准」的证明；每个 facet 只有 10 题，facet 层估计的可靠性有限。　〔出处：content/facets/*.record.json 的 reliability（facet α 0.71–0.88，SEM 为反推值）〕
5. **不得**在缺少完成度信息时给出域分：未答完的 facet 只能按已答题求均分并标注完成度。　〔出处：本项目缺答处理约定（本量表无官方缺答规则）〕

### 6.1 维度级解读义务（逐维度）

下面每一条都是**该维度**特有的解读约束——它们来自 facet 档案的`evidence.interpretation_caveats`，是「这个分数不能这样读」的具体说明。

- **`achievementstriving`**：**这一面向问的是「你想达到多高的水平」，不是「你有多忙」，也不是「你已经做到了多少」。**；它与「自律」不同：**想拿第一，和真的开始去做，是两件事。**抱负很高却迟迟不动手，在这个量表里是常见的组合。
- **`activitylevel`**：**本面向的题目混合了两类不同的东西**：第 1–5、10 题问的是你的**实际节奏与行为**（忙碌、奔波、并行、反应快慢），而第 6–9 题问的是你对从容节奏的**偏好**（喜欢慢慢来、不慌不忙、向往悠闲、顺其自然）。；这是本量表内部一致性最低的面向（α=.71，其余多为 .80 以上）。**如果你的实际节奏与内心偏好并不一致（例如「实际很快，但向往从容」），这个总分无法同时描述这两件事**——请分别看上述两类题目。
- **`adventurousness`**：这一面向问的是**你愿不愿意尝试没做过的事**，与**胆量、风险承受力**无关，也与**能不能去**（时间、金钱、身体条件）无关。请按意愿作答，不按条件作答。；它与「追求刺激」不同：追求刺激要的是**心跳加速**，这一面向要的是**新鲜感**。
- **`aesthetic_appreciation_artistic_interests`**：**注意：「喜欢音乐」这类题在人群中几乎人人同意**，所以它对本面向的区分贡献很小。如果你的总分处在中间地带，可能只是因为部分题目本身区分度低，而不代表你的审美倾向「中庸」。；这一面向问的是**是否被作品与美打动**，不是**是否懂艺术**，也不是**消费了多少内容**。
- **`altruism`**：这一面向问的是**你愿不愿意为他人付出**，不是**你实际付出了多少**。请按意愿作答，不要因为「最近太忙没顾上」而压低分数。；它与「同情」不同：同情是**感受到**别人的处境，这一面向是**为此做点什么**。两者可以不一致。
- **`anger`**：本面向含攻击性表述，**社会赞许性会让一部分人低报**。若你作答时感到「不太想说真话」，这个分数可能偏低。
- **`anxiety`**：第 10 题（容易适应新环境）问的是**情境适应**，与其余 9 题的「担忧强度」主轴略有不同。若你「担忧程度不高、但进入新环境很吃力」，或相反，这个总分可能掩盖这一差异。
- **`assertiveness`**：这一面向问的是**是否主动表达与主导**，**不是攻击性，也不是爱出风头**。它可以表现为「在需要有人拍板时站出来」，而不必然是强势。
- **`cautiousness`**：**这一面向问的是「你会不会先想再做」，不是「你会不会做不了决定」。**有意的权衡（想清楚后就行动）是这一面向；因为担心而迟迟无法决定，那更接近「焦虑」，不属于这里。；另需留意：本面向的题目以反向题为主（7 反 / 3 正），**更容易受到「习惯性同意」这种作答倾向的干扰**。
- **`cheerfulness`**：这一面向问的是**你内心的情绪基调**，不是**你表现出多少**。如果你常感愉快但不爱外露，请按内心状态作答。；同时请留意：**情绪会受到近期境遇的影响**。若你最近经历了较大的好事或坏事，这个分数可能反映的是当下的处境，而不是一贯的你。
- **`cooperation`**：**这一面向的名字（「合作」）与它实际测的东西有落差。**它测的不是「团队协作能力」，而是**在分歧和冲突中是否倾向于让步**。；低分不代表「不合作」，而是**更愿意坚持自己的立场**——这在很多情境下是必要的，不是缺点。；另需留意：其中含有带报复意味的表述，**如果让你不愿意作答，跳过也是有效的反应**。
- **`depression`**：**这个面向不区分「情绪低落的原因」。** 因真实丧失（丧亲、失业、失恋）而悲伤的人，与因气质而长期低落的人，得分可能相同——量表无法分辨这两者。；本面向**不构成抑郁筛查**。若你长期感到低落、失去兴趣或出现伤害自己的念头，请直接寻求专业帮助，而不是依靠这份测评。
- **`dutifulness`**：**这一面向问的是「你有多重视承诺与规范」，不是「你有多能干」，也不是「你有多善良」。**；其中含有「我会打破规则」「我会违背承诺」这类表述——**如果你想到的是某些不合理的规矩，请按你平日里对「承诺」的一般态度作答**，而不是按某个具体情境。
- **`emotionality`**：这一面向问的是**你对情绪的敏感度与重视程度**，**与情绪是正面还是负面无关，也与情绪波动大小无关**。一个情绪稳定但对自己的感受很敏感的人，这一面向可以很高。；注意其中一题问的是「喜欢审视自己与自己的生活」——那更接近**自我探索的兴趣**，与本面向的「情绪觉察」并不完全等同。
- **`excitementseeking`**：**这一面向描述的是对强烈体验的偏好，不含褒贬**——它既不等于勇敢，也不等于不负责任。；它与「活跃度」不是一回事：活跃度问的是**节奏快慢与活动量**，这一面向问的是**是否需要强烈的唤起**。工作高效但从不冒险的人，活跃度可以很高而这一面向很低。
- **`friendliness`**：这一面向问的是**对他人是否有温度**，不是**社交数量**，也不是**社交能力**。如果你只与少数人深交、但关系很暖，这里仍应给高分。
- **`gregariousness`**：这一面向问的是**想不想要人陪、喜不喜欢热闹**，与**和人处得好不好**无关。如果你朋友不多但每一段关系都很深，这里仍可能给低分——那是偏好，不是缺陷。
- **`imagination`**：这一面向问的是**你是否主动使用想象**，与**有没有艺术才能或创造力**无关。
- **`immoderation`**：**「放纵」的具体行为在不同人身上差别很大**（饮食、消费、娱乐、拖延…），而题目并未固定在某一种。这个总分只能粗略反映「是否容易在诱惑前让步」的总体倾向。；这一面向问的是**想做的事能不能停**，与**该做的事做不做**（属「自律」）是两件事。
- **`intellect`**：**这一面向的名字容易误导。它测的是「你喜不喜欢思考」，不是「你有多聪明」。**它不反映智力水平、学历或知识储备。；如果你只是**必要的时候**能把复杂问题想清楚，但并不享受这个过程，这里应给中等分数；享受过程本身才是高分。
- **`liberalism`**：**这一面向是全部 30 个里最容易被误读的一个。** 它问的不是你的政治立场属于左还是右，而是**你在多大程度上愿意重新审视既有的传统、规范与权威**。；它同时受到**文化语境**的强烈影响：同样的题目，在不同社会里被理解成的「开放」并不相同。**请把这里的分数当作一个很粗略的提示，而不是对你价值观的判断。**；另外，本面向的计分方向以反向题为主（7 反 / 3 正），**更容易受到「习惯性同意」这种作答倾向的干扰**。
- **`modesty_humility`**：**这一面向问的是「你会不会抬高自己」，不是「你自不自信」。**它不测量自我价值感，也不测量实际能力。；**它与自信可以并存**：一个人完全可以在心里清楚自己的水平，同时不主动炫耀。两件事在题目里不总能分开，所以这个分数只作粗略参考。；其中一题使用了英文习语（toot my own horn），在翻译时最容易失去原意——若你觉得那题的意思不好把握，可以跳过。
- **`morality`**：**这一面向的名字（「道德」）比它实际测的东西大得多。**它测的只是**在利益面前是否诚实、是否操纵他人**，不涉及你的人品、守法或价值立场。；**它极易受到「希望自己看起来是好人」这一倾向的影响**，所以分数普遍偏高，区分度有限。请把它当作很粗略的提示。；另需留意：其中有题目（如「会利用他人达成自己的目的」）会让人不愿意作答——**跳过不答也是有效的反应**，不必勉强。
- **`orderliness`**：**注意：「条理」在这里只指「环境与物品是否整齐」，不是「做事是否靠谱」。**一个桌面很乱但工作推进得很好的人，这一面向可以很低，而「自律」很高。；另需留意：**本面向的一题在原始机读数据中缺失正文**，我们是用官方问卷补齐的——如果那题的表述让你觉得不太通顺，原因在此。
- **`selfconsciousness`**：**本面向在官方便携中文译本上的内部一致性偏低（α=.602）**，意味着这几道题的中文表述可能没能统一地指向同一个构念。请把它当作粗略提示，而非精确测量。；这一面向问的是**在他人面前是否自在**，不是**是否喜欢与人相处**。如果你乐意和人交往、只是一被注视就紧张，这属于本面向；如果你单纯偏好独处而不紧张，则不属于。
- **`selfdiscipline`**：本面向的题目混合了「**启动速度**」（第 3、4 题）与「**持续执行**」（第 5 题）两个侧面，第 10 题问的则是**决策**而非行动。α=.85 尚可接受，但若你在这几个侧面上差别很大，总分可能掩盖这一差异。
- **`selfefficacy`**：**这一面向问的是「你觉得自己行不行」，不是「你实际行不行」。**它反映的是信心，不反映能力、成绩或经验。；它与「自律」是两件事：**相信自己能把事做好，和真的会去做，可以分开。**自信却拖延，是这个量表里很常见的一种组合。
- **`sympathy`**：**这一面向测的是「你会不会被别人的困难打动」，不是「你有多善良」，也不是「你会不会去帮」。** 它只覆盖共情中的**情感反应**那一半——能理解他人处境但情绪不被牵动的人，这里会得低分，但这不等于缺乏共情能力。；低分尤其容易被自我评判为「冷漠」。**请把它当作一个描述，而不是评价。**
- **`trust`**：这一面向描述的是**你对他人动机的默认假设**，不含褒贬——它既不是「天真」，低分也不是「成熟」。；它与「是否愿意帮助别人」（属「利他」）不是一回事：可以信任所有人但不主动付出。
- **`vulnerability`**：**「脆弱性」一词听起来像负面评价，但这里描述的是压力反应，不是能力评价。** 它问的是在高负荷或突发情形下会不会慌，与你的实际能力、资源、经验都无关。；这一面向问的是**压力下的承受**，与**平时的担忧**（属「焦虑」）不同。平时不焦虑但一遇高压就慌，属于本面向。

---

## 附录 A　证据与溯源

| 项 | 值 |
|---|---|
| 证据文件 | `content/descriptions/ipip-neo.json` |
| 量表包 | `data/instruments/ipip-neo.json` |
| 常模记录 | `data/norms/ipip-neo.json` |
| 量表包 | data/instruments/ipip-neo.json（转换器 tools/build_scales.py，源 archive/ipip/data/OpenScales/scales/ipip/IPIP-NEO/IPIP-NEO.osd） |
| 常模细表 | data/norms/ipip-neo-300.json（生成器 tools/build/build_norms_ipip300.py） |
| facet 档案 | content/facets/<facet>.record.json（30 份，组装器 tools/build/build_all_facets.py） |
| 官方计分表核对 | archive/datasets/osf-johnson/scoring/IPIP-NEO-300_ScoringTool.xlsx（反向题 148/148 一致，记录在 data/norms/ipip-neo-300.json 的 validation） |

### A.1 本项目**没有**拿到依据的地方（如实留白）

- **常模样本的招募方式与采集年份（原始文件）**：本项目只有 Johnson (2005) 的数据文件与论文引用，没有该数据集的招募说明页；因此 §4 的 reference_sample 只写「来源文件为公开数据集」，不写具体招募方式。
- **30 个 facet 的中文 α（自译题面的信度）**：现有 α 是英文原版/OpenScales 的值；自译题面的 α 需要中国样本重新采集，本项目没有该数据。
