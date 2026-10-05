# 数据层缺陷登记与处置结果

**建立**　2026-10-04（`task-12` 登记缺陷）
**修复**　2026-10-04（`task-14`：按用户 R3「缺陷必须记录 → 溯源 → **完整修复**」）
**性质**　本文件记录**已修之处、修法与依据**，以及**仍未闭合的残余项**。

> 旧版把 4 处数据缺陷记为「只记录、不改动」。**该处置已被用户 R3 推翻**：
> 缺陷（尤其混入错误内容的）不存在「留痕而不改」的说法，必须记录、溯源、修到好。
> 本文件即修复后的台账。

---

## 1. DSM-5-TR：四处题面/选项缺陷（**已全部修复**）

### 1.1 `l1_23` 题面截断 + 混入页脚授权句 ✅ 已修复

| | 内容 |
|---|---|
| **修复前** | `Usingany of the following medicines ON YOUR OWN, … in greater amounts or.g., painkillers … or m Copyright © 2013 American Psychiatric Association. All Rights Reserved. This material can be reproduced without permission by researchers and by clinicians for use with their patients` |
| **修复后** | `Using any of the following medicines ON YOUR OWN, that is, without a doctor's prescription, in greater amounts or longer than prescribed [e.g., painkillers (like Vicodin), stimulants (like Ritalin or Adderall), sedatives or tranquilizers (like sleeping pills or Valium), or drugs like marijuana, cocaine or crack, club drugs (like ecstasy), hallucinogens (like LSD), heroin, inhalants or solvents (like glue), or methamphetamine (like speed)]?` |
| **依据** | `archive/scales/DSM5TR-L1/manual.pdf` 第 2 页第 23 题（PDF 对象 24 的内容流；页脚在 y=33.5 是**独立一行**） |
| **根因①（截断）** | `tools/pdftext.py` 的 TJ 正则 `\[((?:\\.|[^\\\[\]])*)\]\s*TJ` 把 `[`/`]` 排除在字符类外。题面里有**字面串内未转义的方括号**（`[e.g., … ]?`），整个 `[…]TJ` 匹配失败、`finditer` 从串内的 `[` 重新起步，**静默丢字**（不报错、不产生 `\ufffd`、不计数）。修法：把 `(…)` 当整体先吃掉，并加**原子组** `(?>…)` 防灾难性回溯（不加时某 163 KB 流从 0.007 s 涨到 2.3 s，全局抽取变超时）。 |
| **根因②（粘连）** | `pdftext.layout_lines` 里有 `if not text.strip(): continue`，把 PDF 中**独立的空格段**丢掉了。实测空格就在原文里（`x0=247.61 ' '`）。修法：保留空白段，最后再把「整行只有空白」的行滤掉。同一处还修好了 `Drinkingat least`／`Smoking any`／`lotsmore`／`couldn'thear` 等 8 处粘连。 |
| **根因③（授权句）** | 页脚与题项同一内容流，`build_l1_items.item_stream_text` 的 `" ".join(rows)` 把它拼进了**最后一题**。修法：按行的语义剔除页脚（`FOOTER_MARKERS`），并在 `extract()` 加断言。 |
| **防复发** | `tools/check/check_dsm_item_text.py`（题面不得含授权句/控制字符、方括号必须配对、L1 每题必须以 `?` 结尾）；`tools/check/verify_pdftext_brackets.py`（钉死方括号字面串与空白段的提取） |

### 1.2 `dsm5trl2sleep_08` 缺锚点 ✅ 已修复

| | 内容 |
|---|---|
| **修复前** | 题面 `My sleep quality was`，**没有该题专属的选项锚点**（其余 7 题用 Not at all…Very much，第 8 题用 Very Poor…Very good，用户不知道对什么评分） |
| **修复后** | 题面不变（`My sleep quality was` —— **核对后确认原文的题干到 "was" 为止是完整的**，后面的 `...` 是排版引出选项），补上**本题专属选项**：`5=Very Poor；4=Poor；3=Fair；2=Good；1=Very good`，落在 `items[8].options`，并带 `options_evidence` |
| **依据** | `archive/scales/DSM5TR-L2-Sleep/manual.pdf` 第 8 页：第 8 题上方一行原文 `Very Poor Poor Fair Good Very good`；该题 5 个框按 `5 4 3 2 1` 排布（与 `reverse_keyed=[2,3,7,8]` 一致） |
| **改法** | `tools/build/build_l2_items.py` 的 `REGISTRY["DSM5TR-L2-Sleep"]["per_item_options"]` 登记锚点，并在 `extract()` 里**先在手册正文中验证锚点词逐字存在**，验不过就报问题（避免凭印象写锚点） |
| **说明** | 原先记作「题面截断」不准确：**截断的不是题干，是选项锚点**。此处如实更正。 |

### 1.3 `dsm5tr-l2-sleep` 题面残留 NUL ✅ 已修复

| | 内容 |
|---|---|
| **修复前** | `dsm5trl2sleep_01` = `'My sleep was restless. \x00 \x00 \x00 \x00'`；`_05` = `'I had trouble staying asleep. \x00 \x00 \x00 \x00'` |
| **修复后** | `'My sleep was restless'`、`'I had trouble staying asleep'` |
| **依据** | 同上手册：这两题的选项框字形是 `\uf071 1 \x00‰ 2 \x00‰ …`，即**两字符组合** `\x00‰`，而其余题是单字符 `\uf071` |
| **根因** | `build_l2_items.strip_options` 的兜底只清私有区（U+E000–F8FF）与 `‰/□` 等，**没把 U+0000 这类控制字符算进「框形字符」**，于是 `\x00` 留了下来 |
| **改法** | 新增 `BOX_CHARS`（控制字符 + 私有区 + `‰` + 各种方框 U+25A1/2610/2611/2612/**2751**/2752），在 `strip_options` 与 `build_l2_items_rest.clean_option` 共用；`extract()` 加「题面不得残留控制字符」断言 |
| **连带修复** | 旧中译**把 `\x00` 一起抄了进去**（`'我难以保持睡眠。 \x00 \x00 \x00 \x00'`）。已在 `tools/build/build_text_db.py` 增加中译卫生（清控制字符 + 压紧空白，**不动字词**），并在 `tools/check/check_text_db.py` 加「中译不得含控制字符/选择框字形」判据 |

### 1.4 `dsm5tr-l2-mania` 选项组放错位置 ✅ 已修复

| | 内容 |
|---|---|
| **修复前** | ASRM 的 5 组 × 5 句陈述只在 `provenance.item_options`；`items[].options` 不存在（按 schema 读的消费者拿不到选项组，界面渲染不出/渲染错）；选项尾部残留选择框字形 `❑`（U+2751，**不在私有区**，所以旧清理规则漏掉）；且有粘连 `cheerfulthanusual` |
| **修复后** | 选项组落在**规范位置 `items[].options`**（5 组 × 5 项，逐条 `{"v","text"}`）；`❑` 已清零；`I often feel happier or more cheerful than usual` |
| **依据** | `archive/scales/DSM5TR-L2-Mania/manual.pdf` 的 `Question 1..5` 各组 |
| **改法** | `tools/build/build_l2_instruments.py` 改为写 `items[].options`（`Item` 数据类没有该字段，故在 `to_dict()` 之后按 order 补——与既有 `kind` 同一手法）；`build_l2_items_rest.BOX_GLYPHS` 补上 **U+2751/2752 与控制字符** |
| **兼容镜像** | `ui/index.html` 目前仍读 `provenance.item_options`（该文件不在 `task-14` 写范围内，且 `task-10` 正在重写它）。因此**两处同时写、内容逐字节相同**，并在 provenance 标注 `item_options_mirror_note`。界面切到 `items[].options` 后应删除镜像（由 `check_dsm_item_text.py` 保证两者一致）。 |
| **原文笔误照实保留** | 手册第 1 组选项 4 原文写作 `I feel happier **of** more cheerful than usual all of the time.`（应为 `or`）。这是**手册自身的笔误**，本项目**逐字保留、不擅自更正**（更正即为修改原文），在此登记供人工复核时判断是否加勘误注。 |

---

## 1.5 回归：链路字段被生成器重跑抹掉（**已修复 + 已加守卫**）

**这是我（`survey-pid5`）在 R2 收口时自己引入的回归**，按 R3 一并记录、溯源、修复。

| | 内容 |
|---|---|
| **现象** | `node tools/check/test_chain_nav.js` 2 项失败：**L1 没有链路条**、**PID-5 入口少了「推论」标注**。其余 8 项通过（L2 建议列、L2 回退、PID-5 回退都正常）。 |
| **最迷惑的地方** | **页面零异常**。我用 CDP 抓 `Runtime.exceptionThrown` + `Runtime.consoleAPICalled` + `Log.entryAdded`：**0 条**。`test_local_file` / `test_scale_pages` / `test_tree_mode` 也都报「脚本报错: 无」。这就是**静默半渲染**——不是代码抛错，是**数据缺了**。 |
| **根因** | `data/instruments/dsm5tr-l1.json` 的 **`linkage` 与 `norms_status` 消失**。这两个字段**不在 `Instrument` 数据类里**，是后续步骤 `tools/build/attach_linkage.py` / `attach_norms.py` 挂上去的；而我为改 R2 授权措辞**重跑了 `tools/build/build_l1_instrument.py`**，它用 `inst.to_dict()` 整体覆盖，把这两个字段冲掉。`build_l2_instruments.py` 早有同样的继承逻辑，**L1 那份漏了**。 |
| **归因证据** | ① 修复前探针：`pkgDownstream=0`、`chainBar=0`、`hasChainText=false`、`inferred=false`，而 `btns` 里 L2 五册仍在（因为 `interpretation` 未受影响）——与「链路条没了、L2 建议列还在」的失败组合**逐项吻合**。② 备份对比：`%TEMP%\dsm-bak\dsm5tr-l1.json`（回归前）有 `linkage`；当前的没有。③ CDP 零异常 → 排除 UI 代码问题（`items[].options` 那次切换是干净的）。 |
| **不是 UI 改动** | `task-10` 报告 `test_chain_nav` 通过是对的——**回归发生在之后**：我在 R2 收口（改 `content/` 措辞）时重跑了 L1 生成器。UI 侧的 `optMap → items[].options` 切换经 CDP 验证**零异常**，与该失败无关。 |
| **修复** | ① 根因：给 `build_l1_instrument.py` 补上挂载期字段的**继承**（`linkage`/`norms`/`norms_status`/`criteria`/`criteria_source`），与 L2 生成器一致——否则下次重跑又坏。② 数据：跑**权威生产者** `attach_linkage.py`（从 `data/linkage/dsm5tr-chain.json`）+ `attach_norms.py` 恢复；恢复结果与回归前备份**逐字节相同**（`linkage` ✅、`norms_status` ✅、`interpretation` 未动），即**复原而非重造**。 |
| **防复发** | 新增 `tools/check/check_chain_fields.py`：断言 11 套都必须有 `norms_status`；L1 的 `linkage.role=screener` 且 `downstream` 与链路定义**逐条对齐**；8 册 L2 的 `upstream.instrument=DSM5TR-L1`；PID-5 的 `related.status=inferred`（与 L1 人格功能域相接**必须标为推论**）。已做**正反验证**：正向通过；抹掉 L1 的 `linkage`+`norms_status`、抹掉某册 L2 的 `linkage`、把 PID-5 的 `status` 改成 `confirmed` 三种注入**都被抓到并 exit 1**。 |

> 教训（与既有的「静默丢字」同类）：**「挂载期字段」是生成器重跑的盲区**。
> 这类缺陷不报错、不产生异常、不影响大部分功能，只是核心链路悄悄少一块。
> 所以凡「先生成、后挂载」的字段，都必须在检查层被**单独钉住**。

---

## 1.6 译文全量复核（337 条）与「同题旧版」根因（**已修复 + 已加守卫**）

**背景**：Lead 用 workflow 对 `zh_source` 含「待人工复核」的**全部 337 条**中译做了
逐条对抗性审核（每批 20 条 + 独立复核者仲裁压误报）：原始报出 40 条 → 仲裁压掉 36 条误报
→ **确认 4 条**。

| # | 问题 | 处置 |
|---|---|---|
| 1 | `Make demands on others.` 译作「**我**向别人提出要求（Make demands on others.）」 | 改为「向他人提出要求。」——去掉擅加的第一人称（同批 `Leave things unfinished.` / `Mess things up.` 都是无主语条目式），并去掉括号内重复英文 |
| 2 | `Methamphetamine (like speed)` 译作「甲基苯丙胺（如**斯皮德**）」 | 改为「甲基苯丙胺（如**冰毒**）」——生硬音译，且同一种物质在库内必须同译（L1 第 23 题已用「冰毒」） |
| 3 | L1 第 23 题**含 copyright 的旧条目** | **不是译文问题，是修复前旧条目残留**（题文截断在 `or m`、拼进页脚授权句）→ 由 `purge_stale()` 删除；旧译并入现行条目 `zh_note` + 记入 `stats.stale_entries_removed` |
| 4 | `You need to step on some toes…` 句末重复整句英文 | 去掉括号内重复英文 |

**① 根因：旧库键被无条件继承（已修）**
`build_text_db.py` 的 `main()` 原先 `for k, e in prev.items(): entries[k] = …` 把**旧库全部条目**
无条件继承，所以 `task-14` 修好题文后，**修复前的旧条目永久留在库里**——第 23 题因此**同时存在**
旧条目（错误英文 + 旧译）与新条目，复核会审到旧的那条。
新增 `purge_stale()`，**判据从严**，只清两类孤儿：
- **同题旧版**：压紧题文与某条现行题文相同、但原文不同（= 题文修正留下的旧键）→ **12 条**；
- **污染残留**：题文或译文含页脚授权句（`Copyright © …`）→ **1 条**（第 23 题）。
其余**孤儿一律保留**（被撤量表的译文是资产）。被删条目的旧译并入现行条目 `zh_note`，
并完整记入 `stats.stale_entries_removed`（含 en/zh，可回查；台账**累积继承**，
否则重跑时会被空列表覆盖——本轮实测踩过一次并已修）。

**② 三处修正的落点：为什么写在「生成器 + 资产表」而不是直接改产物**
`zh` 有多个上游（`data/scene-taxonomy.json` 的 `zh_map`、旧库继承、批次回写），直接改
`data/text-db/text-db.json` 会被下次重跑按上游覆盖。故把复核结论落成
**`data/text-db/reviewed-corrections.json`**（含方法、依据、旧值、原因），由生成器
`apply_review()` 套用——与 `zh_map` 同级、可复现、自带溯源。

**③ 复核状态（如实）**：337 条全部复核过 → 324 条现存活条目由「subagent 初译/重译（待人工复核）」
改为 **「AI 逐条复核 + 仲裁（2026-10-04）」**，其中 3 条修正过者标「已按仲裁结论更正」。
**这不是「已人工复核」**：复核由 AI 执行，不能单独保证正确，仍以规则校验与抽样兜底。

**④ 防复发（`check_text_db.py` 新增三条判据，均已正反验证）**
题文/译文**不得含页脚授权句**；**不得存在同题旧版残留**（孤儿条目与现行题文压紧同键但原文不同）；
**复核修正表必须已生效**（库里的 zh 要等于记录里的 `new_zh`），且 `stats.translation_review` 必须落盘。
反证：把旧的第 23 题条目塞回 → 报错；把某条修正改回旧译 → 报错。

**⑤ R6：`zh` 里的「（英文原文）」内嵌统一删除（Lead 2026-10-04 选②）**
原先 `check_text_db.py` 把 `中文（English）` 记为 **D27 规定格式**（译法有偏移时附原文）。
Lead 判定**落点错了**：R2 把「① 英文原文 / ② 中文翻译 / ③ 本地化讲解」定为**并列三部分**，
英文原文**已由 `en` 字段承担**（界面本就 `zh`/`en` 并列显示），再塞进 `zh` 是同一信息出现两次，
而且会出现在**用户可见的题面**上，让「中译」不再纯粹。
- 新增生成器规则 `strip_parenthetical_english()`，删掉 **29 处**；
- **判据从严**：只删「括号内**纯英文**（无中文）且压紧后确属 `en` 片段（≥3 字符）」。
  `（如麦角酸二乙酰胺，LSD）`、`（如 LSD）`、`（如冰毒）` 这类**正常中文补充一律不动**
  ——靠 **CJK 命中**排除，不是靠长度（我第一版用「连续 6 个字母」判，漏掉了
  `Have a lot of fun` / `Love a good fight` / `I never take risks` 这类英文没有长单词的条目，
  换成「括号内容是否为 `en` 的子串」才捞全）；
- `check_text_db.py` 判据**反转**为「`zh` 不得含括号内嵌英文原文」，**保留**「`zh` 与 `en`
  逐条并列」的判据；反证：塞回一条内嵌英文 → **必须报错**（已实测 exit 1）。

---

## 2. 授权矛盾：已按用户 R2 处置（**不再是矛盾**）

**旧记录**（`task-12` 时期）：APA 授权写「may not be modified absent written permission」，
`source.json` 自述「不提供中译」，因此文档层**不渲染** DSM 中译——86 条中译搁在 `data/text-db` 里不用。

**用户 R2（2026-10-04）**：
> 对于不得修改，**我们提供中英双版即可**，我们给出**英文原文、中文翻译、和完整的本地化内容讲解**，**这是补充，而非修改**。

**处置**：

| 项 | 结果 |
|---|---|
| 授权定性 | 中英双版 + 本地化讲解＝**补充性独立内容**，不是对原文的修改 → 授权条款不构成障碍；原文**逐字未改** |
| 中译启用 | 86 条 DSM 中译**全部启用**（L1 23 + L2 63）；文本库总覆盖 **637/637 = 100.0%**，无一条因修复而丢失 |
| 文档呈现 | DSM-5-TR 各册文档新增「**题项对照：① 英文原文 / ② 中文翻译（含 `zh_source`）/ ③ 本地化内容讲解**」表，逐题三部分并列（见 `data/descriptions/dsm5tr-*.md` §3） |
| 可区分性 | ③ 取自 `content/descriptions/*.json` 的 `dimensions[].gloss`（带 `gloss_source`），并在表头写明「它**不是原文的翻译**，而是该维度在中文语境下指什么的补充说明」 |
| 复核状态 | **照实标注**：`zh_source` 逐条列出；标「subagent 初译（待人工复核）」的一律写明**尚未人工复核、不得当定稿发布** |
| 唯一真实约束 | 内容准确性：译文不得改变原意（第 1.1 节的重译即为一例——旧译对应的是**被截断的英文**） |

**待同步项**：

1. ✅ **已闭合（2026-10-04，Lead 授权）**：`content/descriptions/dsm5tr-{l1,l2}.json` 的
   `translation_unavailable_reason` 与 `display_chinese_items: false` **已删除**，
   改为 `translation_policy`（`stance = supplementary_bilingual`，含 `source` 与
   `supersedes` 说明）；`response_labels_source`、`interpretation_caveats[5]`、
   mania 的 `gloss_source` 中的旧措辞一并更正；
   `data/instruments/dsm5tr-l1.json` 的 `provenance.translation_policy` 与
   `license.notes` 也改为 R2（生成器 `tools/build/build_l1_instrument.py` 同步修）。
   生成器 `build_descriptions.py` 优先读 `translation_policy`，仅在旧字段仍在时才走
   「待同步」分支。
2. ✅ **已闭合（2026-10-04，Lead 授权后收口）**：`ui/index.html` 两处读取点已切到
   **规范位置 `items[].options`**（`const own = it.options || null`），
   `provenance.item_options` **兼容镜像已删除**（`build_l2_instruments.py` 停止写入，
   9 册量表包已无该字段）。
   **切数据源时的关键坑**：`tools/ui/build_ui_instruments.py` 的 `lean()` 用白名单
   拷贝题项字段，**原先没有拷 `options`** —— 界面之所以还能显示，全靠 `provenance`
   整包透传带出的镜像。镜像一删，Mania 的选项会**静默变空**（不报错、只是没有可选项）。
   已在 `lean()` 补上 `options` / `options_evidence`，并把镜像从透传的 provenance 中剔掉。
   回归：`tools/check/test_mania_options_ui.js`（**新**，打印页面 DOM 里 Mania 5 组 × 5 句
   的实际文本 + 天赋树路径）。守卫判据同时由「镜像一致」改为**「镜像不得存在」**
   （否则删镜像后守卫会因为没有镜像而误判为通过）。

---

## 3. 中译的复核状态（**直接决定能不能叫「可填」**）

实测（`data/text-db/text-db.json`）：

| 量表 | 中译覆盖 | `zh_source` | 能不能当「可用中文题面」？ |
|---|---|---|---|
| IPIP-NEO | **300/300** | `data/scene-taxonomy.json（大五人格，已人工核对）` | ✅ 已人工核对 |
| PID-5 | **220/220** | `AI 逐条复核 + 仲裁（2026-10-04）` | ⚠️ **AI 复核，非人工**：可作自填与内部核对，不得声称人工定稿 |
| DSM-5-TR L1 | **23/23** | 同上（其中**第 23 题**为复核期重译稿） | 同上 |
| DSM-5-TR L2 ×8 | **63/63** | 同上 | 同上 |
| 已修正 | 3 条 | `…（2026-10-04，已按仲裁结论更正）` | 同上，且带 `zh_note` 记明更正原因 |
| **合计** | **624/624（100.0%）** | — | 条目数由 637 → 624：**清理了 13 条同题旧版/污染残留**（见 §1.6） |

> **第 23 题**：旧中译对应的是**被截断的英文**（译稿用「……」略过缺失从句）。
> 补回原文后按**修正后的英文**重出稿；本轮 337 条全量复核时一并审过，
> 状态改为「AI 逐条复核 + 仲裁（2026-10-04）」；**旧条目（含页脚授权句）已删除，
> 其旧译留档在该条目的 `zh_note` 与 `stats.stale_entries_removed`**。
> 这是「内容会错的源」的典型：题面截断会**顺着管道一路污染译文**。

---

## 4. 本次修复对 `task-12` 结论的影响（更新）

* 「只读描述文档就能回答——测什么、每维怎么算、反向题哪些、分数对照什么表读、哪些话不许说」
  → **仍成立**（六节结构 + V1 校验）。
* 「纯粹完整**可供人填写**的量表文档」
  → **英文题面成立**；**中文题面现已可用**（DSM 86/86 有中译，三部分并列渲染），
  且 337 条待复核中译已**全部过 AI 逐条 + 仲裁复核**（3 条更正）。
  但**要如实说**：这是 **AI 复核**，不是人工复核——不得宣称人工定稿。
  原先「DSM-5-TR 的 4 处题面缺陷使个别题目无法照填」→ **已消除**。
* 「DSM 文档不渲染中译」→ **已按 R2 推翻**，改为 ①②③ 并列。

---

## 5. 残余项与不在本任务范围内的依赖

| # | 残余项 | 影响 | 需要什么才能闭合 |
|---|---|---|---|
| R1 | ✅ **已闭合（2026-10-04，Lead 授权）**：各册 `archive/scales/<code>/items-extracted.json` 已用修好的提取器**重生成** | — | 已完成：只重生成**派生缓存**，**原始 PDF 未动**（重生成前后 9 份 `manual.pdf` 的 SHA256 逐份比对完全一致）；9 册缓存 `problems` 全为 `[]`；用提取器函数**现场重算**与缓存逐项比对完全一致；一次性桥接脚本 `repair_dsm5tr_items.py` 已**删除** |
| R2 | ✅ **已闭合**：`content/descriptions/dsm5tr-{l1,l2}.json` 已改为 R2 口径 | — | `translation_unavailable_reason`（旧措辞）与 `display_chinese_items:false`（旧开关）**已删除**，改为 `translation_policy`（`stance=supplementary_bilingual`）；`response_labels_source`、`interpretation_caveats`、`gloss_source` 中的旧措辞一并更正；`data/instruments/dsm5tr-l1.json` 的 `provenance.translation_policy` 与 `license.notes` 也改为 R2（生成器 `build_l1_instrument.py` 同步修） |
| R3 | ✅ **已闭合（2026-10-04，Lead 授权收口）**：`ui/index.html` 已切到 `items[].options`，兼容镜像已删除 | — | 两处读取点改为 `it.options \|\| null`；`lean()` 补拷 `options`/`options_evidence` 并从透传 provenance 中剔除镜像；9 册量表包已无 `provenance.item_options`；守卫判据改为**镜像不得存在**；新增 `test_mania_options_ui.js` 回归（打印 Mania 5 组 × 5 句渲染实测） |
| R4 | ✅ **已闭合（2026-10-04 译文复核）**：L1 第 23 题的重译稿已随 **337 条全量逐条复核**一起审过，状态由「subagent 重译（待人工复核）」改为 **「AI 逐条复核 + 仲裁（2026-10-04）」** | — | ⚠️ 措辞是「**AI 复核**」不是「人工复核」：复核由 AI 逐条 + 独立仲裁完成，仍以 `check_text_db.py` 的规则校验与抽样兜底，不得据此宣称人工定稿 |
| R6 | ✅ **已闭合（2026-10-04，Lead 选②）**：`zh` 里的「（英文原文）」内嵌已**统一删除**（29 处） | — | 新增生成器规则 `strip_parenthetical_english()`：只删「括号内**纯英文**且确属 `en` 片段」的写法；`（如麦角酸二乙酰胺，LSD）`、`（如冰毒）` 这类**正常中文补充不动**（判据靠 CJK 排除，不靠长度）。D27 的**意图**由 `en` 字段承担——界面本就 `zh`/`en` 并列显示，对照功能**结构性存在**。`check_text_db.py` 的判据已**反转**（旧注释把内嵌英文记为 D27 规定格式，那是错的落点），并保留「`zh` 与 `en` 逐条并列」的判据 |
| R5 | ✅ **已按 Lead 定调处理**：Mania 第 1 组第 4 句原文 `happier **of** more cheerful` | 笔误是**原文的事实**，属「① 英文原文」 | **不加勘误注、不改原文**；已在**③ 本地化讲解**里加一句「其中 of 疑为 or 之误……仅作说明，不构成对原文的更正」（`instruments["dsm5tr-l2-mania"].localization_notes`） |

---

## 6. 复核命令

```powershell
# 题面/选项污染扫描（控制字符、授权句、方括号、截断；镜像一致性）
python tools/check/check_dsm_item_text.py

# PDF 词法层回归（方括号字面串 + 空白段）
python tools/check/verify_pdftext_brackets.py

# 文本库：结构、覆盖、译文质量、控制字符
python tools/check/check_text_db.py

# 描述文档：六节结构、反向题逐项、生成物未手改
python tools/check/check_descriptions.py

# 索引完整性（新增/删除脚本后）
python tools/check/check_index_completeness.py

# 挂载期字段（链路条 / PID-5 推论接口 / norms_status）——防「重跑生成器抹字段」
python tools/check/check_chain_fields.py
```
