# MMPI-2 — Minnesota Multiphasic Personality Inventory-2（评估指标文档，**不含题项**） — 可填量表文档与评估指标

<!-- 本文件由 tools/build/build_descriptions.py 生成，请勿手改。改动请改 content/descriptions/<code>.json 后重跑。 -->

- **量表代码**　`MMPI-2`（文档代码 `mmpi-2`）
- **生成器**　`tools/build/build_descriptions.py`　**校验**　`python tools/check/check_descriptions.py`
- **题项状态**　⚠️ **本量表题项不在本项目收录范围内**（版权限制，见 §3.5 与 §1.3）

> 本文档的目标读者是**将要填答这套量表的人**与**读结果的人**：只读本文档就应能回答——测什么、每维怎么算、反向题哪些、分数对照什么表读、哪些话不许说。

---

## 1. 量表是什么 / 测什么

**它是什么**　MMPI-2 是原始 MMPI（1943）的**重新标准化版本**，由 University of Minnesota Press 于 **1989 年出版、2001 年修订**；2003 年加入 Restructured Clinical（RC）量表，2006 年加入 Symptom Validity（FBS）量表（2009 年单行本）。它是**自评式**临床量表组合，共 **567 道题**（True/False 作答，题项在量表内不重复；原始 MMPI 的 566 题中有 16 题重复；MMPI-2 有 107 道新题、从原题库剔除 90 题）。除临床用途外，也用于高风险公共安全岗位选拔与刑事/民事司法鉴定。

　出处：`https://www.upress.umn.edu/test-division/mmpi-2/（1989 出版、2001 修订、2003 RC、2006 FBS）；Butcher《A Beginner's Guide to the MMPI-2》节选（567 题、107 新题、90 题剔除）https://media.wiley.com/product_data/excerpt/34/04713453/0471345334.pdf`

**它测什么**　它同时测两层：[1] **作答效度**（是否如实、是否随机/矛盾作答、是否夸大或掩饰症状），[2] **临床与人格病理的量表分数**（临床量表、RC 量表、内容量表等）。计分后各量表按 **uniform T 分**换算，**T ≥ 65 表示临床上值得注意的升高**（MMPI 原版的边界是 T ≥ 70，MMPI-2 下调为 65；且 MMPI-2 的 T 分不再是线性 T 分，而是 uniform T 分，以得到各量表之间可比的百分位分布）。

　出处：`T ≥ 65：Bozza (2017) 学位论文（Università di Pisa）2.3 节转述与逐量表判读（https://etd.adm.unipi.it/theses/available/etd-06262017-111100/unrestricted/Bozza_tesi2.pdf）；uniform T：Tellegen, A., & Ben-Porath, Y. S. (1992). The new uniform T scores for the MMPI-2: rationale, derivation, and appraisal. Psychological Assessment, 4, 145–155（书目信息见同一论文参考文献）`

### 1.1 它**不**测什么（防止误用）

- **不做诊断**。MMPI-2 是临床量表组合，分数升高指向「值得进一步评估的临床特征」，不构成任何诊断；诊断需结合访谈、病史与其它资料。　<span title="出处">〔量表性质与通用临床使用规范（UMN Press 对 MMPI-2 的用途描述：aid in the assessment）〕</span>
- **不是常态人格的「性格描述」**。它的量表是按临床组间对比（contrasted groups）建构的病理指向量表，T ≥ 65 是「临床值得注意」而非「性格特点」；用它做 MBTI 式的类型/性格解读是误用。　<span title="出处">〔Butcher 节选：Hathaway 用 contrasted groups 法建构量表；SAGE/教科书对 MMPI 临床量表性质的通行描述〕</span>
- **不测智力或能力**。　<span title="出处">〔量表范围（效度 + 临床/内容量表，无能力测验分量表）〕</span>
- **不能脱离效度指标解释**。若效度量表提示随机作答、矛盾作答或过度掩饰/夸大，临床量表的升高不可解释。　<span title="出处">〔Bozza (2017) 2.3.1 节：效度量表的三类用途（合作态度、夸大、掩饰）〕</span>
- **不使用未经授权的题项来源**。本项目**刻意不提供**任何「免费题面」——那类来源的内容错误风险与授权风险都不可接受。　<span title="出处">〔UMN Press 权限页原文 + 本项目「不用盗版来源」的硬规则（engine/instrument_schema.py 的 D20）〕</span>

### 1.2 适用与不适用人群

- **适用**：成人（18 岁及以上）。原版以**五年级阅读水平**为最低要求（Hathaway 的设定）；重标准化期间做过题目难度研究（最终阅读水平要求见手册，本项目未取得该页）。
- **不适用**：18 岁以下（另用 MMPI-A）; 阅读水平不足且无辅助施测者; 无资质人员单独用于临床或司法决策
- 出处：`Butcher 节选（五年级阅读水平、重标准化期间的题目难度研究）`

### 1.3 题项为什么不在这里

**本量表题项受版权保护，本项目不收录、不提供、不转载任何题面文字。**

University of Minnesota Press Test Division 官方权限页原文：

> "The Press does not allow for the reproduction of test items in dissertations/theses, journal articles, books or online."

题册与计分材料由 Pearson Assessments 独家发行，使用者需具备 Pearson 的相应资质（MMPI-2 属 **Level C** 级别要求：需具备使用相应测验的资质与培训）。本项目只整理**公开发表的评估指标**（量表结构、常模与 T 分体系、信效度证据、判读规则、合法获取途径），不复制题目。

## 2. 维度表

> 以下为**公开发表的量表结构**（名称与代号），用于理解分数对应什么；点明「未核实」的项目在本轮没有取得可核对来源。**不含任何题项文字。**

| 组 | 代号 | 量表名 | 题目数 | 说明 |
|---|---|---|---|---|
| 效度量表 | `?` | Cannot Say（未答题数） | — | 原版即有 |
| 效度量表 | `L` | Lie（说谎） | — | 原版即有 |
| 效度量表 | `F` | Infrequency（频率/稀有作答） | — | 原版即有 |
| 效度量表 | `K` | Correction（校正/防卫） | — | 原版即有 |
| 效度量表 | `FB` | Back F（后段稀有作答） | — | MMPI-2 新增 |
| 效度量表 | `VRIN` | Variable Response Inconsistency（作答不一致） | — | MMPI-2 新增 |
| 效度量表 | `TRIN` | True Response Inconsistency（True 作答倾向） | — | MMPI-2 新增 |
| 效度量表 | `Fp` | Infrequency-Psychopathology | — | 2001 Revised Edition 新增 |
| 效度量表 | `S` | Superlative Self-Presentation | — | 2001 Revised Edition 新增 |
| 临床量表 | `1 Hs` | Hypochondriasis 疑病 | — | 原版量表，MMPI-2 保持 |
| 临床量表 | `2 D` | Depression 抑郁 | — | 同上 |
| 临床量表 | `3 Hy` | Hysteria 癔症（转换） | — | 同上 |
| 临床量表 | `4 Pd` | Psychopathic Deviate 精神病态偏差 | — | 同上 |
| 临床量表 | `5 Mf` | Masculinity–Femininity 男性化–女性化 | — | 同上 |
| 临床量表 | `6 Pa` | Paranoia 偏执 | — | 同上 |
| 临床量表 | `7 Pt` | Psychasthenia 精神衰弱 | — | 同上 |
| 临床量表 | `8 Sc` | Schizophrenia 精神分裂 | — | 同上 |
| 临床量表 | `9 Ma` | Hypomania 轻躁狂 | — | 同上 |
| 临床量表 | `0 Si` | Social Introversion 社会内向 | — | 同上 |
| RC 量表（2003） | `RCd` | Demoralization（去道德化/总体痛苦） | — | RC 量表的一般因子 |
| RC 量表（2003） | `RC1–RC9` | 8 个与临床量表对应的 RC 量表 | — | 已核实存在 RCd + 8 个临床对应的 RC 量表；**具体代号与名称本轮未逐一核实** |
| 内容量表与其它 | `15 个内容量表` | Content Scales（含其成分量表） | — | 取代原 MMPI 的 13 个 Wiggins 内容量表；**具体代号本轮未逐一核实** |
| 内容量表与其它 | `Harris–Lingoes` | 临床量表子量表 | — | 8 个基本量表中 6 个有 Harris–Lingoes 子量表（Scale 4 的子量表不再含量表外条目） |
| 内容量表与其它 | `Koss–Butcher / Lachar–Wrobel` | 关键条目清单（critical items） | — | 保留，并扩充了抑郁/自杀与酒精滥用两组 |
| 内容量表与其它 | `PSY-5` | 人格心理病理五维 | — | **本轮未取得可核对来源，故不列出代号** |

出处：`效度与临床量表清单：Bozza (2017) 2.3 节（https://etd.adm.unipi.it/theses/available/etd-06262017-111100/unrestricted/Bozza_tesi2.pdf）+ Butcher 节选；RC 量表存在与年份：UMN Press MMPI-2 页（https://www.upress.umn.edu/test-division/mmpi-2/）；内容量表 15 个、Harris–Lingoes、Koss–Butcher/Lachar–Wrobel：Butcher 节选`

## 3. 计分方法

**本题库不收录该量表的题项，因此本项目无法计分。**下面记录的是**公开发表的计分体系**，供用户自行取得题项后对照使用。

- **作答**：567 题，逐题 True/False。　<span title="出处">〔Butcher 节选〕</span>
- **计分**：各量表按题项归属累加（原始分），再换算为 **uniform T 分**（Tellegen & Ben-Porath, 1992）；MMPI-2 的 T 分不是线性 T 分，目的是让不同量表的百分位分布可比。　<span title="出处">〔Tellegen & Ben-Porath (1992) 书目信息与 Bozza (2017) 2.2 节转述〕</span>
- **T 分体系**：T 分以均值 50、标准差 10 为标准尺度（T = 50 + 10 × z）；**T ≥ 65 为临床显著升高的通行边界**（MMPI 原版为 T ≥ 70，MMPI-2 下调到 65）。　<span title="出处">〔Bozza (2017) 2.2 节：『è sceso da T ≥ 70 a T ≥ 65』；逐量表判读处亦以 T ≥ 65 为界。T = 50 + 10z 是 T 分的定义式。〕</span>
- **原始分→T 分的对照表在购买的手册/计分软件里，本项目没有**，因此本项目**不能**替用户把 MMPI-2 的原始分换算成 T 分。　<span title="出处">〔本项目的入档范围（archive/ 内无 MMPI-2 材料）〕</span>

### 3.1 如何合法取得题项并本地导入

**用户若自行取得合法题册与计分材料**，本项目提供本地导入路径（计划中的接口，非本轮交付）：

1. 把题项按量表包 schema 写入 `data/instruments/<code>.json`（本项目的代码即 mmpi-2；`items` 非空、每题带 `key` 与所属维度），
2. 在 `content/descriptions/mmpi-2.json` 里把 `items_policy` 改为 `included` 并补上题序来源，
3. 重跑 `python tools/build/build_descriptions.py --only mmpi-2` 与 `python tools/check/check_descriptions.py`。

⚠️ 题项与计分表**不得**提交到本仓库：授权只对购买者本人/本机构有效，且 UMN Press 明确禁止在网络上转载题项。

## 4. 结果解读基准

**有部分解读基准，但**没有**可直接使用的常模表。**

本量表**没有本项目可用的常模表**：分量的均值/标准差/百分位或 raw→T 对照表都不在本项目入档范围内。因此本项目只提供**已公开、可核对的基准事实**，不替用户换算分数。

**已有部分基准**：T 分体系与常模样本的构成可以在公开文献核对（下表的样本量与构成已核实）；但**逐分量表的原始分→T 分对照表在购买的手册/计分软件里**，本项目没有该表，因此**不能**替用户换算 T 分，也不能给出各分量的均值/标准差表。

| 参考样本 | 值 |
|---|---|
| n | 2600 |
| composition | 1,462 名女性 + 1,138 名男性 |
| recruitment | 重新标准化（restandardization）期间收集，样本从约 2,900 人中筛出；剔除约 300 人（人口学信息缺失、MMPI-AX 漏答 > 39 题、F 量表或实验量表分数过分偏离） |
| year | 1989 |
| note | 样本按当时人口普查比例在年龄、教育、婚姻、地域等维度上做过匹配；Butcher 同时指出「与普查值相符并不能保证对所有子群体都是可靠标准」（如贫困内城、原住民、流动人口等） |


**替代读法**：只做「与自己比」的纵向比较，或与本文档 §4.2 给出**该量表自己的分带/分界**对照；**不做人群百分位比较**。

### 4.1 怎么读（本量表的解读规则）

- 先读**效度量表**再读临床量表：VRIN/TRIN 提示随机或矛盾作答，L/K/S 提示过度自我美化，F/FB/Fp 提示夸大症状；效度不成立时不得解释临床升高。　<span title="出处">〔Bozza (2017) 2.3.1 节（效度量表的三类用途）〕</span>
- 临床量表以 **T ≥ 65** 为「值得注意」的通行边界；T 分是 uniform T，可按百分位解释。**本项目没有 raw→T 对照表**，故不能替用户换算。　<span title="出处">〔Bozza (2017)；本记录的 norms_spec.status = partial〕</span>
- 量表名的中文译名（如 Pd →「精神病态偏差」）**不是诊断标签**；不得由单个量表升高推出诊断。　<span title="出处">〔MMPI-2 为临床量表组合，非诊断工具（UMN Press 对其用途的描述：aid in the assessment）〕</span>

## 5. 信度与出处

### 5.1 内部一致性（α）

**未获得可溯源的 α。**本项目**不逐个量表给 α**（逐量表 α 表在购买手册/技术单行本里，未入档）。下面给出的是**文献中可核对的区间**，逐条标注来源；区间本身不能替代分量表的信度表。

- **内部一致性（基本量表）**：Graham (2000) 报告 MMPI-2 基本量表的内部一致性在 **0.5–0.96** 之间，均值区间 .60–.90（转引自 Bozza (2017) 学位论文）。　<span title="出处">〔https://etd.adm.unipi.it/theses/available/etd-06262017-111100/unrestricted/Bozza_tesi2.pdf（原出处 Graham, 2000, MMPI-2 解释手册）〕</span>
- **重测信度**：报告区间为临床量表 **.49–.73**、补充量表 **.30–.80**、内容量表 **.65–.77**；Harris–Lingoes 子量表 **.51–.74**（转引自同一学位论文）。　<span title="出处">〔同上（Bozza 2017 的文献综述表）〕</span>
- **另一组较早的汇总**（Hunsley et al., 1988，针对 **MMPI** 而非 MMPI-2）：内部一致性 α .71–.84，重测相关系数 .63–.86。　<span title="出处">〔同上（原研究对象为 MMPI，不能当作 MMPI-2 的值）〕</span>
- Matz et al. (1992) 报告 α 区间 **.39–.91（中位数 .62）**。　<span title="出处">〔同上〕</span>

### 5.2 来源与授权

- **citation**：Butcher, J. N., Dahlstrom, W. G., Graham, J. R., Tellegen, A., & Kaemmer, B. (1989). MMPI-2: Manual for administration and scoring. Minneapolis: University of Minnesota Press.（2001 Revised Edition；RC 量表 2003、FBS 2006/2009 单行本）
- **授权**：UMN Press（量表出版方）+ Pearson Assessments（发行方，需资质）；研究用途需向 UMN Press 提交 Research Permission 表单。
  - 证据：`https://www.upress.umn.edu/test-division/permissions-and-ordering/ （2026-10-04 取得，原文见上）`

### 5.3 已知批评与局限（known_critiques）

- **常模样本的代表性争议**：与人口普查值相符不等于对所有子群体都可靠；Butcher 本人即指出贫困内城、原住民、流动农业人口、无家可归者等群体可能系统性偏离。　<span title="出处">〔Butcher 节选：『Mere correspondence to census values cannot guarantee … reliable normative standard』〕</span>
- **量表异质性**：临床量表由 contrasted groups 法建构，单个量表内部包含多种症状内容（因此才有 Harris–Lingoes 子量表与 RC 量表来拆解）。　<span title="出处">〔Butcher 节选（contrasted groups 方法）与 RC 量表的存在理由（UMN Press 2003 年加入 RC）〕</span>
- **信度区间很宽**：内部一致性低至 0.5、重测低至 .30（见上），说明部分量表的分数稳定性有限；解释单个低信度量表需谨慎。　<span title="出处">〔同上（Graham 2000 / Bozza 2017 汇总）〕</span>

## 6. 解读义务（哪些话不许说）

以下为本量表结果解读的**硬约束**。它们不是风格建议：本项目的每一条对外表述都必须满足。

1. **不得**把 MMPI-2 的结果说成诊断；它是临床决策的辅助工具。　〔出处：UMN Press / Pearson 对 MMPI-2 用途的定位〕
2. **不得**省略效度量表的解读，也不得在效度不成立时解释临床量表。　〔出处：Bozza (2017) 2.3.1 节〕
3. **不得**把 T ≥ 65 说成「确诊」；它只是「临床值得注意」的通行边界。　〔出处：Bozza (2017) 逐量表判读均以 T ≥ 65 为「需注意」而非诊断〕
4. **不得**在缺少 raw→T 对照表的情况下自行换算 T 分或百分位。　〔出处：本记录 norms_spec.status = partial〕
5. **不得**收录、转载或展示任何 MMPI-2 题项文字（包括「示例题」）。　〔出处：UMN Press 权限页原文〕
6. **不得**用 MMPI-2 做性格类型解读（它与大五/类型学不是同一用途）。　〔出处：量表为临床病理指向的 contrasted-groups 量表〕

---

## 附录 A　证据与溯源

| 项 | 值 |
|---|---|
| 证据文件 | `content/descriptions/mmpi-2.json` |
| 常模记录 | `data/norms/mmpi-2.json` |
| 量表结构 | Bozza, F. (2017) 学位论文（Università di Pisa，etd-06262017-111100）2.2–2.3 节；Butcher 节选；UMN Press MMPI-2 页 |
| 常模与 567 题 | Butcher《A Beginner's Guide to the MMPI-2》Wiley 节选 PDF（media.wiley.com） |
| 授权 | https://www.upress.umn.edu/test-division/permissions-and-ordering/（2026-10-04 取得） |
| 发行与资质 | Pearson Assessments（UMN Press 指定发行方，Level C 资质） |

### A.1 本项目**没有**拿到依据的地方（如实留白）

- **逐分量表的原始分→T 分对照表**：在购买的手册与计分软件里，本项目未购买也未入档。因此无法换算 T 分。
- **MMPI-2 技术手册中的逐量表 α 与重测系数表**：本轮只取得二手汇总区间（Graham 2000 转引），未取得技术单行本原文。
- **RC 量表与 15 个内容量表的具体代号与名称**：已核实其存在与数量，但本轮未取得可核对的完整代号表（需 RC 单行本或内容量表手册）。
- **PSY-5 的维度数与代号**：本轮检索未取得可核对来源，故不列出。
- **官方中文版的存在与授权状态**：本轮未核实（不作断言）。
- **阅读水平的最终等级**：已核实原版以五年级为最低要求、重标准化期间做过题目难度研究；最终等级需手册该页。
