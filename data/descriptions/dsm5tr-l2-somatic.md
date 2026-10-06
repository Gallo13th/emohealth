# Level 2—Somatic Symptom—Adult（Patient Health Questionnaire 15 [PHQ-15]） — 可填量表文档与评估指标

<!-- 本文件由 tools/build/build_descriptions.py 生成，请勿手改。改动请改 content/descriptions/<code>.json 后重跑。 -->

- **量表代码**　`DSM5TR-L2-Somatic`（文档代码 `dsm5tr-l2-somatic`）
- **生成器**　`tools/build/build_descriptions.py`　**校验**　`python tools/check/check_descriptions.py`

> 本文档的目标读者是**将要填答这套量表的人**与**读结果的人**：只读本文档就应能回答——测什么、每维怎么算、反向题哪些、分数对照什么表读、哪些话不许说。

---

## 1. 量表是什么 / 测什么

**它是什么**　APA「DSM-5-TR Online Assessment Measures」的第二级：**对 Level 1 已经触发的症状域做更细的评估**。本项目收录 8 册（Anger / Anxiety / Depression / Mania / Repetitive / Sleep / Somatic / Substance），每册是一套**单一维度**的自评量表。

　出处：`archive/scales/DSM5TR-L2-*/manual.pdf（逐册）；总览见 data/criteria/dsm5tr-l2.json 与 data/linkage/dsm5tr-chain.json`

**它测什么**　被 Level 1 触发的那个域在过去 7 天（或各册自定的窗口）内的**症状频度/严重度**。各册的计分口径**互不相同**——PROMIS 四册按手册要求应换算 T 分，躁狂册是 5 组选项求和，躯体册是 0–2 求和，物质册是逐项独立解释。

　出处：`data/criteria/dsm5tr-l2.json 的 note 与逐册 kind/sum_range`

### 1.1 它**不**测什么（防止误用）

- **不做诊断**。与 Level 1 同源的免责声明适用于全部 8 册：结果只能用于临床决策的辅助，不得作为诊断的唯一依据。　<span title="出处">〔data/linkage/dsm5tr-chain.json 的 disclaimer（APA 手册原文）〕</span>
- **不是常模参照量表**（就本项目现有资料而言）：4 册 PROMIS 的 T 分表**均已归档**（Anxiety 7a / Depression 8b / Sleep Disturbance 8a 在 PROMIS 官方 scoring manual 的 Appendix 1，Anger 5a 印在 APA 册内），4 册非 PROMIS 只有手册给出的分带/分界。**8 册都拿不到一般人群的百分位**。　<span title="出处">〔data/criteria/dsm5tr-l2.json 逐册 tscore_table=null / bands / cutoff〕</span>
- **不能跨册比较分数**：8 册来自不同工具（PROMIS 短表、ASRM、FOCI 改编、PHQ-15、NIDA-Modified ASSIST），题数 5–15、量纲 0–2 / 0–4 / 1–5 各不相同。　<span title="出处">〔data/criteria/dsm5tr-l2.json 的 note；题数与量纲见各量表包 structure〕</span>
- **不是诊断访谈**。手册的设计用途是「访谈者施测 + 辅助判断」，本册题目不覆盖病程、功能损害、排除标准与鉴别诊断。　<span title="出处">〔archive/scales/DSM5TR-L2-*/manual.pdf 的 Scoring and Interpretation 段〕</span>

### 1.2 适用与不适用人群

- **适用**：18 岁及以上成人（8 册均为成人版）。
- **不适用**：18 岁以下; 未经 Level 1 触发就直接施测（本册设计上用于细评已触发的域）
- 出处：`archive/scales/DSM5TR-L2-*/manual.pdf（Adult 版）`

## 2. 维度表

| # | 维度 id | 中文名 | 英文名 | 题目数 | 反向题数 | 聚合 | 通俗解释（本表内） |
|---|---|---|---|---|---|---|---|
| 1 | `l2_somatic_symptom` | 躯体症状负荷 | Somatic Symptom | 15 | 0 | `sum` | 过去 7 天被 15 个常见躯体症状（胃痛、背痛、四肢或关节痛、月经问题、头痛、胸痛、头晕、昏厥、心悸、气短、性交疼痛、 |

### 2.1 逐维度构念解释（通俗中文 + 定义 + 不测什么）

#### `l2_somatic_symptom`　躯体症状负荷（Somatic Symptom）

- **通俗解释**：过去 7 天被 15 个常见躯体症状（胃痛、背痛、四肢或关节痛、月经问题、头痛、胸痛、头晕、昏厥、心悸、气短、性交疼痛、肠胃问题、恶心胀气、疲乏、睡眠困难）困扰的程度（0=完全没被困扰，2=被困扰很多）。
  - 依据：`derived_from_items:dsm5trl2somatic_01…15`
- **文献定义（改述）**：Patient Health Questionnaire 15（PHQ-15）躯体症状严重度量表，APA 版收录于 DSM-5-TR Level 2。
  - 出处：`archive/scales/DSM5TR-L2-Somatic/manual.pdf`
- **本维度不测**：不排除器质性病因（分数不能用来推断症状是心理来源）；不诊断躯体症状障碍；不评估症状的医学严重度
- **示例题**：`dsm5trl2somatic_01` “Stomach pain”；`dsm5trl2somatic_02` “Back pain”

### 题文与中译状态（能不能照着填）

- **题文**：15 题，英文原文来自量表包（`data/instruments/<code>.json` 的 `items[].text`）。
- **中译**：15/15 题在**数据层**有中译，来源标记为：「AI 逐条复核 + 仲裁（2026-10-04）」× 15。
- **授权与本地化处置（R2，2026-10-04）**：APA 授权写明「may not be modified absent written permission from APA」。本项目**逐字不改原文**，而是把 ① 英文原文、② 中文翻译、③ 本地化内容讲解三者**并列**呈现——中译与讲解是**补充性独立内容**，不是对原文的修改，因此授权条款不构成障碍。各条中译的复核状态见其 `zh_source`（均标「subagent 初译/重译（待人工复核）」），**未人工复核前不得作为定稿中文版发布**。
  - 依据：`archive/scales/DSM5TR-L1/source.json 的授权原文 + 用户 R2`
- ⚠️ **中译复核状态**：逐条见 §3 的题项对照表（`zh_source` 列）。标「subagent 初译/重译（待人工复核）」的条目**尚未人工复核**，可作自填与内部核对，**不得**当作定稿中文版发布。

## 3. 计分方法

- **作答选项**：3 点，0–2；锚点：Not bothered at all / Bothered a little / Bothered a lot
- **时间窗**：past 7 days（出处：`DSM5TR-L2-Somatic` 手册）
- **聚合口径**：每个维度由量表包 `scoring` 声明（`sum` / `mean` / `max` / `count_true` …），本文档 §2 表内逐维列出。
- **每册的口径由该册自己的量表包 `scoring` 声明**，不要假设都是求和：PROMIS 四册与躁狂/躯体/重复思维册为 `sum`，物质册为 `count_true`（>0 的项数，**不是总分**）。　<span title="出处">〔data/instruments/dsm5tr-l2-*.json 的 scoring；data/criteria/dsm5tr-l2.json 的 kind〕</span>
- 缺答规则：手册通行要求是缺答超过 25% 时不得使用分数；个别册允许按比例推算（prorated）。　<span title="出处">〔data/criteria/dsm5tr-l2.json 的 missing_rule〕</span>

### 3.1 反向计分题清单（**逐项**，共 0 题）

**无反向题。**（全部题项均为正向计分；本清单由量表包 `items[].key == -1` 逐项导出。）

> 本项目收录的 8 册**都没有反向计分题**（全部题目 key = +1）。注意：这**不等于**「题面都是正向表述」——例如睡眠册第 2/3/7 题（我满意我的睡眠 / 我的睡眠让我恢复精力 / 我睡够了）在原版里是正向表述、按正向计分。

### 3.2 分值范围

- 0–30（15 题 × 0–2，求和）。　<span title="出处">〔data/criteria/dsm5tr-l2.json 的 DSM5TR-L2-Somatic.sum_range〕</span>

### 题项对照：① 英文原文 / ② 中文翻译 / ③ 本地化内容讲解（三部分并列）

- **① 英文原文**：逐字取自量表包 `items[].text`（源头 `archive/scales/<code>/manual.pdf`，见 §5 出处）。
- **② 中文翻译**：取自统一文本库 `data/text-db/text-db.json`，逐条标注 `zh_source`（**复核状态照实写**，未复核就写未复核）。
- **③ 本地化内容讲解**：该题**所属维度**的构念说明，取自 `content/descriptions/*.json` 的 `dimensions[].gloss`（含 `gloss_source`）。它**不是原文的翻译**，而是「这个维度在中文语境下指什么」的补充说明，与①②明确区分。

| 题号 | ① 英文原文 | ② 中文翻译（`zh_source`） | ③ 本地化讲解（维度构念） |
|---|---|---|---|
| 1 | Stomach pain | 胃痛（AI 逐条复核 + 仲裁（2026-10-04）） | 过去 7 天被 15 个常见躯体症状（胃痛、背痛、四肢或关节痛、月经问题、头痛、胸痛、头晕、昏厥、心悸、气短、性交疼痛、肠胃问题、恶心胀气、疲乏、睡眠困难）困扰的程度（0=完全没被困扰，2=被困扰很多）。（derived_from_items:dsm5trl2somatic_01…15） |
| 2 | Back pain | 背痛（AI 逐条复核 + 仲裁（2026-10-04）） | 过去 7 天被 15 个常见躯体症状（胃痛、背痛、四肢或关节痛、月经问题、头痛、胸痛、头晕、昏厥、心悸、气短、性交疼痛、肠胃问题、恶心胀气、疲乏、睡眠困难）困扰的程度（0=完全没被困扰，2=被困扰很多）。（derived_from_items:dsm5trl2somatic_01…15） |
| 3 | Pain in your arms, legs, or joints (knees, hips, etc.) | 手臂、腿部或关节（膝盖、髋部等）的疼痛（AI 逐条复核 + 仲裁（2026-10-04）） | 过去 7 天被 15 个常见躯体症状（胃痛、背痛、四肢或关节痛、月经问题、头痛、胸痛、头晕、昏厥、心悸、气短、性交疼痛、肠胃问题、恶心胀气、疲乏、睡眠困难）困扰的程度（0=完全没被困扰，2=被困扰很多）。（derived_from_items:dsm5trl2somatic_01…15） |
| 4 | Menstrual cramps or other problems with your periods WOMEN ONLY | 痛经或月经其他问题（仅限女性）（AI 逐条复核 + 仲裁（2026-10-04）） | 过去 7 天被 15 个常见躯体症状（胃痛、背痛、四肢或关节痛、月经问题、头痛、胸痛、头晕、昏厥、心悸、气短、性交疼痛、肠胃问题、恶心胀气、疲乏、睡眠困难）困扰的程度（0=完全没被困扰，2=被困扰很多）。（derived_from_items:dsm5trl2somatic_01…15） |
| 5 | Headaches | 头痛（AI 逐条复核 + 仲裁（2026-10-04）） | 过去 7 天被 15 个常见躯体症状（胃痛、背痛、四肢或关节痛、月经问题、头痛、胸痛、头晕、昏厥、心悸、气短、性交疼痛、肠胃问题、恶心胀气、疲乏、睡眠困难）困扰的程度（0=完全没被困扰，2=被困扰很多）。（derived_from_items:dsm5trl2somatic_01…15） |
| 6 | Chest pain | 胸痛（AI 逐条复核 + 仲裁（2026-10-04）） | 过去 7 天被 15 个常见躯体症状（胃痛、背痛、四肢或关节痛、月经问题、头痛、胸痛、头晕、昏厥、心悸、气短、性交疼痛、肠胃问题、恶心胀气、疲乏、睡眠困难）困扰的程度（0=完全没被困扰，2=被困扰很多）。（derived_from_items:dsm5trl2somatic_01…15） |
| 7 | Dizziness | 头晕（AI 逐条复核 + 仲裁（2026-10-04）） | 过去 7 天被 15 个常见躯体症状（胃痛、背痛、四肢或关节痛、月经问题、头痛、胸痛、头晕、昏厥、心悸、气短、性交疼痛、肠胃问题、恶心胀气、疲乏、睡眠困难）困扰的程度（0=完全没被困扰，2=被困扰很多）。（derived_from_items:dsm5trl2somatic_01…15） |
| 8 | Fainting spells | 晕厥发作（AI 逐条复核 + 仲裁（2026-10-04）） | 过去 7 天被 15 个常见躯体症状（胃痛、背痛、四肢或关节痛、月经问题、头痛、胸痛、头晕、昏厥、心悸、气短、性交疼痛、肠胃问题、恶心胀气、疲乏、睡眠困难）困扰的程度（0=完全没被困扰，2=被困扰很多）。（derived_from_items:dsm5trl2somatic_01…15） |
| 9 | Feeling your heart pound or race | 感到心跳剧烈或心跳加速（AI 逐条复核 + 仲裁（2026-10-04）） | 过去 7 天被 15 个常见躯体症状（胃痛、背痛、四肢或关节痛、月经问题、头痛、胸痛、头晕、昏厥、心悸、气短、性交疼痛、肠胃问题、恶心胀气、疲乏、睡眠困难）困扰的程度（0=完全没被困扰，2=被困扰很多）。（derived_from_items:dsm5trl2somatic_01…15） |
| 10 | Shortness of breath | 气短（AI 逐条复核 + 仲裁（2026-10-04）） | 过去 7 天被 15 个常见躯体症状（胃痛、背痛、四肢或关节痛、月经问题、头痛、胸痛、头晕、昏厥、心悸、气短、性交疼痛、肠胃问题、恶心胀气、疲乏、睡眠困难）困扰的程度（0=完全没被困扰，2=被困扰很多）。（derived_from_items:dsm5trl2somatic_01…15） |
| 11 | Pain or problems during sexual intercourse | 性交时的疼痛或问题（AI 逐条复核 + 仲裁（2026-10-04）） | 过去 7 天被 15 个常见躯体症状（胃痛、背痛、四肢或关节痛、月经问题、头痛、胸痛、头晕、昏厥、心悸、气短、性交疼痛、肠胃问题、恶心胀气、疲乏、睡眠困难）困扰的程度（0=完全没被困扰，2=被困扰很多）。（derived_from_items:dsm5trl2somatic_01…15） |
| 12 | Constipation, loose bowels, or diarrhea | 便秘、大便稀溏或腹泻（AI 逐条复核 + 仲裁（2026-10-04）） | 过去 7 天被 15 个常见躯体症状（胃痛、背痛、四肢或关节痛、月经问题、头痛、胸痛、头晕、昏厥、心悸、气短、性交疼痛、肠胃问题、恶心胀气、疲乏、睡眠困难）困扰的程度（0=完全没被困扰，2=被困扰很多）。（derived_from_items:dsm5trl2somatic_01…15） |
| 13 | Nausea, gas, or indigestion | 恶心、胀气或消化不良（AI 逐条复核 + 仲裁（2026-10-04）） | 过去 7 天被 15 个常见躯体症状（胃痛、背痛、四肢或关节痛、月经问题、头痛、胸痛、头晕、昏厥、心悸、气短、性交疼痛、肠胃问题、恶心胀气、疲乏、睡眠困难）困扰的程度（0=完全没被困扰，2=被困扰很多）。（derived_from_items:dsm5trl2somatic_01…15） |
| 14 | Feeling tired or having low energy | 感到疲倦或精力不足（AI 逐条复核 + 仲裁（2026-10-04）） | 过去 7 天被 15 个常见躯体症状（胃痛、背痛、四肢或关节痛、月经问题、头痛、胸痛、头晕、昏厥、心悸、气短、性交疼痛、肠胃问题、恶心胀气、疲乏、睡眠困难）困扰的程度（0=完全没被困扰，2=被困扰很多）。（derived_from_items:dsm5trl2somatic_01…15） |
| 15 | Trouble sleeping | 睡眠困难（AI 逐条复核 + 仲裁（2026-10-04）） | 过去 7 天被 15 个常见躯体症状（胃痛、背痛、四肢或关节痛、月经问题、头痛、胸痛、头晕、昏厥、心悸、气短、性交疼痛、肠胃问题、恶心胀气、疲乏、睡眠困难）困扰的程度（0=完全没被困扰，2=被困扰很多）。（derived_from_items:dsm5trl2somatic_01…15） |

## 4. 结果解读基准

**仅原始分，无可用常模。**

本量表**不给百分位、不给 T 分、不做「高于/低于常人」的判断**——本项目没有可溯源的常模数据支撑这类表述，因此宁可不给。

**为什么没有**：本册按**严重度分带**判读（PHQ-15，总分 0–30）：极轻 0–4、轻 5–9、中 10–14、重 15–30。它本身不是常模量表，不给出百分位或 T 分。


**替代读法**（唯一诚实的读法）：把分数当作**该维度上题面描述的频率/强度记录**，只做纵向自比（同一人不同时间、或与自己的其它维度比），**不做人群比较**。

### 4.2 判读口径（自动取自 `data/criteria/`，单一真相源）

- **口径类型**：`severity_bands`　量表：PHQ-15（躯体症状）
- **总分范围**：0–30

| 分带 | 范围 |
|---|---|
| Minimal（极轻） | 0–4 |
| Low（轻） | 5–9 |
| Medium（中） | 10–14 |
| High（重） | 15–30 |
- 缺答规则：缺答超过 25% 时不得使用分数；个别册允许按比例推算（prorated）。各册原文均有此说明。
- 出处：`archive/scales/DSM5TR-L2-Somatic/manual.pdf 的 Scoring and Interpretation 段`

### 4.1 怎么读（本量表的解读规则）

- 手册给出四档严重度分带：Minimal 0–4、Low 5–9、Medium 10–14、High 15–30。　<span title="出处">〔data/criteria/dsm5tr-l2.json 的 DSM5TR-L2-Somatic.bands（archive/scales/DSM5TR-L2-Somatic/manual.pdf）〕</span>
- 分带来自 PHQ-15 的原始报告，是**该量表的严重度分带**，不是本册自带的一般人群常模。　<span title="出处">〔PHQ-15 原始文献的分带；本项目未入档 PHQ-15 原始文献，故只引手册给出的分带〕</span>

## 5. 信度与出处

### 5.1 内部一致性（α）

**未获得可溯源的 α。****这 8 册的手册都没有报告 α。** 4 册 PROMIS 短表的信度在 PROMIS 官方 scoring manual 与相关论文里，但本项目**未入档**该来源（见 evidence_gaps）；照「不编造数字」的规则，本项目不给 α 数值。

- 可核对的替代信息是题源与题数：逐册题数与工具名见 data/criteria/dsm5tr-l2.json 的 scale 字段。　<span title="出处">〔data/criteria/dsm5tr-l2.json〕</span>

### 5.2 来源与授权

- **citation**：American Psychiatric Association. Level 2—Somatic Symptom—Adult (Patient Health Questionnaire 15 Somatic Symptom Severity Scale [PHQ-15]).
- **license**：`copyright_permitted`（可再分发：True）— American Psychiatric Association；L2-Somatic 改编自公有领域的 PHQ-15（Pfizer 明确免除版权）
  - 授权证据：`archive/scales/DSM5TR-L2-Somatic/source.json（sha256 708deea559bf7db3…）`
  - 官方链接：https://www.psychiatry.org/getmedia/843c7fa5-9a40-4795-a25e-70208903d88c/APA-DSM5TR-Level2SomaticSymptomAdult.pdf
- **题序来源**：`archive/scales/DSM5TR-L2-Somatic/manual.pdf 题项顺序`

### 5.3 已知批评与局限（known_critiques）

- 4 册 PROMIS 短表的手册都要求「使用 T-score table」，**四册的表均已归档并入库**为可查的 raw→T 表（Anxiety 7a / Depression 8b / Sleep Disturbance 8a 见 PROMIS 官方 scoring manual 的 Appendix 1；Anger 5a 印在 APA 册子内）。⚠️ 其中 **Sleep 册的算例**用的是**改订前旧表**（官方 2023 表已注明 2014-05-22 改订并要求旧数据重算），算例与其表的这一处不一致已如实留存于该册记录。　<span title="出处">〔data/criteria/dsm5tr-l2.json 逐册 tscore_table / source_of_criteria；复核工具 tools/survey/probe_promis_tscore.py〕</span>
- Level 2 与 PID-5 的衔接**不是**这 9 册手册的原文：已核查 9 册正文一次都没提到 PID-5 或 personality disorder。　<span title="出处">〔data/linkage/dsm5tr-chain.json 的 pid5_interface.caveat〕</span>

## 6. 解读义务（哪些话不许说）

以下为本量表结果解读的**硬约束**。它们不是风格建议：本项目的每一条对外表述都必须满足。

1. **不得**由任一册的结果推出诊断结论。　〔出处：data/linkage/dsm5tr-chain.json 的 disclaimer（APA 手册原文）〕
2. **不得**跨册比较分数，也不得把某册的原始分说成「严重度高于常人」。　〔出处：data/criteria/dsm5tr-l2.json 的 note（八册口径互不相同）〕
3. **不得**把物质使用册的分数当作总分：该册逐项独立解释，「>0 的项数」是严重度/复杂度指标。　〔出处：data/criteria/dsm5tr-l2.json 的 DSM5TR-L2-Substance.aggregate_label〕
4. **不得**用无出处的数字换算 T 分或百分位：T 分只能查**已归档**的转换表（逐册见 data/criteria/dsm5tr-l2.json 的 `tscore_table`）。　〔出处：data/criteria/dsm5tr-l2.json 逐册 tscore_table〕
5. **不得**把本项目的中译当作「官方中文版」发布：APA 授权未许可**修改**原文；本项目提供的是**补充性独立内容**（① 英文原文 + ② 中译 + ③ 本地化讲解），且中译均**未经人工复核**。　〔出处：archive/scales/DSM5TR-L1/source.json 的授权原文（同体系条款）；各册 source.json〕

---

## 附录 A　证据与溯源

| 项 | 值 |
|---|---|
| 证据文件 | `content/descriptions/dsm5tr-l2.json` |
| 量表包 | `data/instruments/dsm5tr-l2-somatic.json` |
| 常模记录 | `data/norms/dsm5tr-l2-somatic.json` |
| 题项提取 | archive/scales/DSM5TR-L2-*/items-extracted.json（提取器 tools/build/build_l2_items.py 与 build_l2_items_rest.py） |
| 判读口径 | archive/scales/DSM5TR-L2-*/manual.pdf 的 Scoring and Interpretation 段；整理进 data/criteria/dsm5tr-l2.json |
| 授权原文 | archive/scales/DSM5TR-L2-*/source.json |

### A.1 本项目**没有**拿到依据的地方（如实留白）

- **PROMIS 短表的 raw→T 分表**：**已闭合（2026-10-06）**：4 册的转换表均已在档并入库——Anxiety 7a / Depression 8b / Sleep Disturbance 8a 见 `archive/literature/norms/healthmeasures2023_promis-*-cat-scoring-manual.pdf` 的 Appendix 1，Anger 5a 的表印在 `archive/scales/DSM5TR-L2-Anger/manual.pdf` 第 9 页。逐册均经「raw 全域连续 + 算例查表」自证；**Sleep 一处例外已留档**：APA 册的算例（raw 27 → T 57.3）用的是2014-05-22 改订前的旧表，官方现行表为 59.1，本项目按官方现行表给分。第三方附录（sunnaas 2021、rimed 2021）仍不作为权威转换来源。
- **PROMIS 短表的 α / 信度**：需要 PROMIS 官方 scoring manual 或原始论文；当前未入档，故不给数值。
- **睡眠册第 8 题与物质册题面的完整性**：实测 dsm5trl2sleep_08 题文为「My sleep quality was」**截断**；l2-sleep 部分题面残留 NUL 填充字符；l1_23 尾部混入版权句。均为数据层缺陷，已在 research/descriptions-evidence/known-data-gaps.md 登记，本任务未改动数据。
