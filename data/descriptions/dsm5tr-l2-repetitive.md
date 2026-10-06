# Level 2—Repetitive Thoughts and Behaviors—Adult（改编自 FOCI 严重度分量表 Part B） — 可填量表文档与评估指标

<!-- 本文件由 tools/build/build_descriptions.py 生成，请勿手改。改动请改 content/descriptions/<code>.json 后重跑。 -->

- **量表代码**　`DSM5TR-L2-Repetitive`（文档代码 `dsm5tr-l2-repetitive`）
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
| 1 | `l2_repetitive_thoughts_and_behaviors` | 重复思维与行为的严重度 | Repetitive Thoughts and Behaviors | 5 | 0 | `sum` | 这些想法/行为每天占多少时间、带来多少痛苦、有多难控制、让你回避多少事情、让你觉得受到多大妨碍（每题 0–4）。 |

### 2.1 逐维度构念解释（通俗中文 + 定义 + 不测什么）

#### `l2_repetitive_thoughts_and_behaviors`　重复思维与行为的严重度（Repetitive Thoughts and Behaviors）

- **通俗解释**：这些想法/行为每天占多少时间、带来多少痛苦、有多难控制、让你回避多少事情、让你觉得受到多大妨碍（每题 0–4）。
  - 依据：`derived_from_items:dsm5trl2repetitive_01…05`
- **文献定义（改述）**：改编自 Florida Obsessive-Compulsive Inventory（FOCI）严重度分量表 Part B。
  - 出处：`archive/scales/DSM5TR-L2-Repetitive/manual.pdf`
- **本维度不测**：不诊断强迫症；不区分强迫思维与其它侵入性思维；不问症状内容（只问严重度）
- **示例题**：`dsm5trl2repetitive_01` “On average, how much time is occupied by these thoughts or behaviors each day?”；`dsm5trl2repetitive_02` “How much distress do these thoughts or behaviors cause you?”

### 题文与中译状态（能不能照着填）

- **题文**：5 题，英文原文来自量表包（`data/instruments/<code>.json` 的 `items[].text`）。
- **中译**：5/5 题在**数据层**有中译，来源标记为：「AI 逐条复核 + 仲裁（2026-10-04）」× 5。
- **授权与本地化处置（R2，2026-10-04）**：APA 授权写明「may not be modified absent written permission from APA」。本项目**逐字不改原文**，而是把 ① 英文原文、② 中文翻译、③ 本地化内容讲解三者**并列**呈现——中译与讲解是**补充性独立内容**，不是对原文的修改，因此授权条款不构成障碍。各条中译的复核状态见其 `zh_source`（均标「subagent 初译/重译（待人工复核）」），**未人工复核前不得作为定稿中文版发布**。
  - 依据：`archive/scales/DSM5TR-L1/source.json 的授权原文 + 用户 R2`
- ⚠️ **中译复核状态**：逐条见 §3 的题项对照表（`zh_source` 列）。标「subagent 初译/重译（待人工复核）」的条目**尚未人工复核**，可作自填与内部核对，**不得**当作定稿中文版发布。

## 3. 计分方法

- **作答选项**：5 点，0–4；锚点：0 / 1 / 2 / 3 / 4
- **聚合口径**：每个维度由量表包 `scoring` 声明（`sum` / `mean` / `max` / `count_true` …），本文档 §2 表内逐维列出。
- **每册的口径由该册自己的量表包 `scoring` 声明**，不要假设都是求和：PROMIS 四册与躁狂/躯体/重复思维册为 `sum`，物质册为 `count_true`（>0 的项数，**不是总分**）。　<span title="出处">〔data/instruments/dsm5tr-l2-*.json 的 scoring；data/criteria/dsm5tr-l2.json 的 kind〕</span>
- 缺答规则：手册通行要求是缺答超过 25% 时不得使用分数；个别册允许按比例推算（prorated）。　<span title="出处">〔data/criteria/dsm5tr-l2.json 的 missing_rule〕</span>

### 3.1 反向计分题清单（**逐项**，共 0 题）

**无反向题。**（全部题项均为正向计分；本清单由量表包 `items[].key == -1` 逐项导出。）

> 本项目收录的 8 册**都没有反向计分题**（全部题目 key = +1）。注意：这**不等于**「题面都是正向表述」——例如睡眠册第 2/3/7 题（我满意我的睡眠 / 我的睡眠让我恢复精力 / 我睡够了）在原版里是正向表述、按正向计分。

### 3.2 分值范围

- 0–20（5 题 × 0–4，求和）。原文另有『average total score』口径。　<span title="出处">〔data/criteria/dsm5tr-l2.json 的 DSM5TR-L2-Repetitive（sum_range、notes）〕</span>

### 题项对照：① 英文原文 / ② 中文翻译 / ③ 本地化内容讲解（三部分并列）

- **① 英文原文**：逐字取自量表包 `items[].text`（源头 `archive/scales/<code>/manual.pdf`，见 §5 出处）。
- **② 中文翻译**：取自统一文本库 `data/text-db/text-db.json`，逐条标注 `zh_source`（**复核状态照实写**，未复核就写未复核）。
- **③ 本地化内容讲解**：该题**所属维度**的构念说明，取自 `content/descriptions/*.json` 的 `dimensions[].gloss`（含 `gloss_source`）。它**不是原文的翻译**，而是「这个维度在中文语境下指什么」的补充说明，与①②明确区分。

| 题号 | ① 英文原文 | ② 中文翻译（`zh_source`） | ③ 本地化讲解（维度构念） |
|---|---|---|---|
| 1 | On average, how much time is occupied by these thoughts or behaviors each day?　<br>**本题专属选项**：0=None；1=Mild；2=Moderate；3=Severe；4=Extreme | 平均而言，这些想法或行为每天占用你多少时间？（AI 逐条复核 + 仲裁（2026-10-04）） | 这些想法/行为每天占多少时间、带来多少痛苦、有多难控制、让你回避多少事情、让你觉得受到多大妨碍（每题 0–4）。（derived_from_items:dsm5trl2repetitive_01…05） |
| 2 | How much distress do these thoughts or behaviors cause you?　<br>**本题专属选项**：0=None；1=Mild；2=Moderate；3=Severe；4=Extreme | 这些想法或行为给你带来多大的痛苦？（AI 逐条复核 + 仲裁（2026-10-04）） | 这些想法/行为每天占多少时间、带来多少痛苦、有多难控制、让你回避多少事情、让你觉得受到多大妨碍（每题 0–4）。（derived_from_items:dsm5trl2repetitive_01…05） |
| 3 | How hard is it for you to control these thoughts or behaviors?　<br>**本题专属选项**：0=Complete control；1=Much control；2=Moderate control；3=Little control；4=No control | 你控制这些想法或行为有多困难？（AI 逐条复核 + 仲裁（2026-10-04）） | 这些想法/行为每天占多少时间、带来多少痛苦、有多难控制、让你回避多少事情、让你觉得受到多大妨碍（每题 0–4）。（derived_from_items:dsm5trl2repetitive_01…05） |
| 4 | How much do these thoughts or behaviors cause you to avoid doing anything, going anyplace, or being with anyone?　<br>**本题专属选项**：0=No avoidance；1=Mild；2=Moderate；3=Severe；4=Extreme | 这些想法或行为在多大程度上使你回避做任何事、去任何地方或与任何人相处？（AI 逐条复核 + 仲裁（2026-10-04）） | 这些想法/行为每天占多少时间、带来多少痛苦、有多难控制、让你回避多少事情、让你觉得受到多大妨碍（每题 0–4）。（derived_from_items:dsm5trl2repetitive_01…05） |
| 5 | How much do these thoughts or behaviors cause you to feel interfered with or unable to do things?　<br>**本题专属选项**：0=None；1=Mild；2=Moderate；3=Severe；4=Extreme | 这些想法或行为在多大程度上让你感到受干扰或无法做事？（AI 逐条复核 + 仲裁（2026-10-04）） | 这些想法/行为每天占多少时间、带来多少痛苦、有多难控制、让你回避多少事情、让你觉得受到多大妨碍（每题 0–4）。（derived_from_items:dsm5trl2repetitive_01…05） |

## 4. 结果解读基准

**仅原始分，无可用常模。**

本量表**不给百分位、不给 T 分、不做「高于/低于常人」的判断**——本项目没有可溯源的常模数据支撑这类表述，因此宁可不给。

**为什么没有**：本册按**分界值**判读（改编自 FOCI，总分 0–20）：≥8 提示可考虑对强迫症做更详细的评估。它本身不是常模量表，不给出百分位或 T 分。


**替代读法**（唯一诚实的读法）：把分数当作**该维度上题面描述的频率/强度记录**，只做纵向自比（同一人不同时间、或与自己的其它维度比），**不做人群比较**。

### 4.2 判读口径（自动取自 `data/criteria/`，单一真相源）

- **口径类型**：`cutoff`　量表：改编自 FOCI（Florida Obsessive-Compulsive Inventory）
- **总分范围**：0–20
- **分界值**：8

| 分带 | 范围 |
|---|---|
| 低于分界 | 0–7 |
| 可考虑对强迫症做更详细的评估 | 8–20 |
- 说明：原文另有『average total score』口径
- 缺答规则：缺答超过 25% 时不得使用分数；个别册允许按比例推算（prorated）。各册原文均有此说明。
- 出处：`archive/scales/DSM5TR-L2-Repetitive/manual.pdf 的 Scoring and Interpretation 段`

### 4.1 怎么读（本量表的解读规则）

- 手册给出分界：**≤7** 低于分界；**≥8** 可考虑对强迫症做更详细的评估。　<span title="出处">〔data/criteria/dsm5tr-l2.json 的 DSM5TR-L2-Repetitive.cutoff 与 bands〕</span>

## 5. 信度与出处

### 5.1 内部一致性（α）

**未获得可溯源的 α。****这 8 册的手册都没有报告 α。** 4 册 PROMIS 短表的信度在 PROMIS 官方 scoring manual 与相关论文里，但本项目**未入档**该来源（见 evidence_gaps）；照「不编造数字」的规则，本项目不给 α 数值。

- 可核对的替代信息是题源与题数：逐册题数与工具名见 data/criteria/dsm5tr-l2.json 的 scale 字段。　<span title="出处">〔data/criteria/dsm5tr-l2.json〕</span>

### 5.2 来源与授权

- **citation**：American Psychiatric Association. Level 2—Repetitive Thoughts and Behaviors—Adult (Adapted from the Florida Obsessive-Compulsive Inventory [FOCI] Severity Scale [Part B]).
- **license**：`copyright_permitted`（可再分发：True）— American Psychiatric Association
  - 授权证据：`archive/scales/DSM5TR-L2-Repetitive/source.json（sha256 7b58f175b21d4b71…）`
  - 官方链接：https://www.psychiatry.org/getmedia/a451f9f0-40b7-4262-8ef2-e7be2ea004f2/APA-DSM5TR-Level2RepetitiveThoughtsAndBehaviorsAdult.pdf
- **题序来源**：`archive/scales/DSM5TR-L2-Repetitive/manual.pdf 题项顺序`

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
| 量表包 | `data/instruments/dsm5tr-l2-repetitive.json` |
| 常模记录 | `data/norms/dsm5tr-l2-repetitive.json` |
| 题项提取 | archive/scales/DSM5TR-L2-*/items-extracted.json（提取器 tools/build/build_l2_items.py 与 build_l2_items_rest.py） |
| 判读口径 | archive/scales/DSM5TR-L2-*/manual.pdf 的 Scoring and Interpretation 段；整理进 data/criteria/dsm5tr-l2.json |
| 授权原文 | archive/scales/DSM5TR-L2-*/source.json |

### A.1 本项目**没有**拿到依据的地方（如实留白）

- **PROMIS 短表的 raw→T 分表**：**已闭合（2026-10-06）**：4 册的转换表均已在档并入库——Anxiety 7a / Depression 8b / Sleep Disturbance 8a 见 `archive/literature/norms/healthmeasures2023_promis-*-cat-scoring-manual.pdf` 的 Appendix 1，Anger 5a 的表印在 `archive/scales/DSM5TR-L2-Anger/manual.pdf` 第 9 页。逐册均经「raw 全域连续 + 算例查表」自证；**Sleep 一处例外已留档**：APA 册的算例（raw 27 → T 57.3）用的是2014-05-22 改订前的旧表，官方现行表为 59.1，本项目按官方现行表给分。第三方附录（sunnaas 2021、rimed 2021）仍不作为权威转换来源。
- **PROMIS 短表的 α / 信度**：需要 PROMIS 官方 scoring manual 或原始论文；当前未入档，故不给数值。
- **睡眠册第 8 题与物质册题面的完整性**：实测 dsm5trl2sleep_08 题文为「My sleep quality was」**截断**；l2-sleep 部分题面残留 NUL 填充字符；l1_23 尾部混入版权句。均为数据层缺陷，已在 research/descriptions-evidence/known-data-gaps.md 登记，本任务未改动数据。
