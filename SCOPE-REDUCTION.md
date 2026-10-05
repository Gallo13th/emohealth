# 范围裁剪记录（SCOPE-REDUCTION）

> **性质：历史账本（只记录事实）。** 规则与计划以 [`PLAN.md`](PLAN.md) 为准；本文件不含规则。
> 用户授权：保留最小实现 + UI 示例 + 天赋树布局核心思想 + 4 个核心模型（IPIP 大五 / MMPI-2 / PID-5 / DSM-5-TR）相关的内容，其余删除并清理依赖。
> **archive/ 不在范围内**（证据链，未勾选删除）。

## 本轮删除清单（Lead 执行）

| 路径 | 大小 | 依据 |
|---|---|---|
| `data/instruments/ipip-neo5-20-agreeableness.json` | 7276 B | IPIP-NEO5-20 子量表不在核心清单（核心是 IPIP-NEO-300 本体） |
| `data/instruments/ipip-neo5-20-conscientiousness.json` | 6821 B | IPIP-NEO5-20 子量表不在核心清单（核心是 IPIP-NEO-300 本体） |
| `data/instruments/ipip-neo5-20-extraversion.json` | 5014 B | IPIP-NEO5-20 子量表不在核心清单（核心是 IPIP-NEO-300 本体） |
| `data/instruments/ipip-neo5-20-neuroticism.json` | 5665 B | IPIP-NEO5-20 子量表不在核心清单（核心是 IPIP-NEO-300 本体） |
| `data/instruments/ipip-neo5-20-openness-to-experience.json` | 11173 B | IPIP-NEO5-20 子量表不在核心清单（核心是 IPIP-NEO-300 本体） |
| `ui/instruments/ipip-neo5-20-agreeableness.js` | 11562 B | IPIP-NEO5-20 子量表不在核心清单（核心是 IPIP-NEO-300 本体） |
| `ui/instruments/ipip-neo5-20-conscientiousness.js` | 9178 B | IPIP-NEO5-20 子量表不在核心清单（核心是 IPIP-NEO-300 本体） |
| `ui/instruments/ipip-neo5-20-extraversion.js` | 7725 B | IPIP-NEO5-20 子量表不在核心清单（核心是 IPIP-NEO-300 本体） |
| `ui/instruments/ipip-neo5-20-neuroticism.js` | 9411 B | IPIP-NEO5-20 子量表不在核心清单（核心是 IPIP-NEO-300 本体） |
| `ui/instruments/ipip-neo5-20-openness-to-experience.js` | 19256 B | IPIP-NEO5-20 子量表不在核心清单（核心是 IPIP-NEO-300 本体） |
| `tools/survey/fetch_hexaco_keys.py` | 2820 B | HEXACO 专属；该量表数据已删，脚本成孤儿 |
| `tools/ui/shoot_ei_tree.js` | 3025 B | IPIP-EI 专属截图脚本；EI 已删 |

共删 12 个文件。

### 明确保留（易误判为孤儿）

| 路径 | 为什么留 |
|---|---|
| `tools/check/check_tree_geometry.py` | 检查**天赋树几何**（用户要保留的核心思想）；只是 docstring 举了 IPIP-EI 的例子 → 改例子不删文件 |
| `tools/survey/probe_en_pool.py` | 英文池探测，服务**翻译质量**（核心量表的翻译同样需要） |
| `tools/check/check_deploy.js`、`check_mobile_layout.js` | UI 与部署检查，与具体量表无关 |

### research/scales 处理
| 路径 | 处置 | 依据 |
|---|---|---|
| `research/scales/inventory.json` | **保留** | 归档全貌（1096 套量表清单），是「为什么只选 4 个核心」的决策依据，符合可溯源原则 |
| `research/scales/candidates.json` | 删除 | 342 套筛选过程的中间产物，服务已删量表 |
| `research/scales/ipip-conversion-report.json` | 删除 | 同上（354 clean + 96 risky 的转换报告） |

---

# 追加：前端回退到最小 UI（D116）——执行人 `frontend-infer`（task-10）

> ## ⚠️ 后续（D117，task-18）：本节的部分内容已被**重新接回**，读之前先看这段
>
> 用户随后要求「**完善答题界面**：每道题的显示文本（结构化文本各部分）＋ 基于已有答题结果
> 对**各指标值的预测 + 置信度**」，于是：
> - **重新加回**：`tools/ui/pack_ui_data.py` 的 `inference` 打包作业（并新增
>   `items-structured` 作业）、`ui/inference/*.js` + `ui/inference.js`、
>   题面四字段渲染、各指标预测面板（按新口径：`dim_ceiling_cross` 作显示分母、
>   官方分/推断值分层、本维度一题未答不给数）。
> - **仍然撤下**：分级模式/情景模式、大五阶梯（`netR2`/`facetWindowEnd`/信息增益推荐）、
>   冷却机制、旧的「已达上限 X%」大五面板。
> - 本节「删除清单」里 `ui/inference.js` / `ui/inference/*.js` 与「测试处置」里
>   `test_inference_ondemand.js`/`test_pid5_inference_ui.js` 的记录**已成历史**；
>   `test_ui_rolled_back.js` 也已在 D117 删除（它断言的东西又被用户要求做回来了）。
> - `data/**` 与 `archive/` 依然未因 UI 工作改动。

> 用户原话：**「（对已完成的前端工作）回退掉，只留最小 UI」**
> 「现在允许你删除文件，保留最小实现，保留UI示例，保留天赋树布局的核心思想」
> 开发顺序不可颠倒：`文献数据 → 专业手册 → 完整可填量表文档 + 评估指标 → 才设计 UI → 最后才接受缺省值/实时估测`。
> 本次把**推断 / 实时置信度**那套**从 UI 撤下**（它是第 4、5 步的东西）。
> **`data/**` 与 `archive/` 一个字节都没改**——撤的是「界面的消费」，不是数据。

## A1. 规模

| 指标 | 回退前 | 回退后 | 变化 |
|---|---|---|---|
| `ui/index.html` 行数 | 4496 | 1823 | **−2673 行（−59%）** |
| `ui/index.html` 字节 | 235,300 | 95,328 | **−139,972 B（−59%）** |
| 首页前置脚本字节 | 740,263 | **5,531**（catalog 4,606 + instruments 925） | **−734,732 B** |
| 顶层模式 | 4（分级/情景/经典/题库） | **1（题库）** | −3 |

首页前置脚本的构成变化：去掉 `emohealth-data.js`(597,195)、`tier-data.js`(125,002)、
`net-layout.js`(12,350)、`inference.js`(207)；保留 `catalog.js`(4,606)、`instruments.js`(925)
（后者同时提供 `EMOHEALTH_INSTMAP` 与 `EMOHEALTH_TREEMAP`）。

## A2. 删除清单（文件级）

| 路径 | 大小(B) | 判定依据 |
|---|---:|---|
| `ui/inference/ipip-neo.js` | 493,516 | `data/inference/ipip-neo.json` 的打包产物，只有推断面板/判据在用 |
| `ui/inference/pid-5.js` | 331,237 | 同上（PID-5） |
| `ui/inference.js` | 207 | 推断包按需加载清单（`EMOHEALTH_INFERMAP`） |
| `tools/check/test_confidence_dynamic.js` | 12,157 | 只测实时置信度判据（`netR2`/`dim_ceiling`/`ceiling_ratio`/`INF_SCOPE`） |
| `tools/check/test_inference_ondemand.js` | 13,232 | 只测推断包按需加载与推断口径 |
| `tools/check/test_pid5_inference_ui.js` | 11,392 | 只测 PID-5 置信度判据与信息增益推荐 |
| `tools/check/probe_legacy_unlock.js` | 5,413 | 分级模式行为对照探针，依赖已不存在的 `EMOHEALTH_INFER_IPIP_NEO` |

合计 **867,154 B**。

**没有删**：`data/inference/*.json`（`pairB64`/`item_dim_corr`/`dim_corr`/`dim_ceiling`/`ceiling_ratio`，
共 824,451 B）、`ui/tree-layouts/**`、`tools/build/build_tree_layouts.py`、
`ui/emohealth-data.js`/`tier-data.js`/`unlock-data.js`/`adaptive-data.js`/`net-layout.js`
（产物保留，只是首页不预载），以及 7 个读 `data/**`+`archive/**` 的数据侧标定/诊断脚本。

## A3. `ui/index.html` 代码块级变化（摘要）

**整块删除**（括号内为原行数）：推断作用域层（~270：`legacyScope`/`buildPackScope`/`activeScope`/
`scopePair`/`dimRAt`/`ensureInfScope` 等）、信息增益选题（~200：`pairR`/`adaptCtx`/`gainOf`/
`totalGain`/`pcorrOf`/`gainCeiling`/`recommend`/`_inv`/`_mv`/`RIDGE`/`MIN_RESID`）、
置信度判据与解锁窗口（~220：`netR2`/`rOf`/`ceilingOf`/`ceilingRatio`/`readyR`/`confReady`/
`facetReady`/`netUnlocked`/`instFacetR`/`instFacetReady`/`ownCount`/`facetWindowEnd`/`ring1Done` 等）、
分级模式图与面板（~380：`renderTierTree`/`renderTierGraph`/`renderTierPanel`/`placeLabels`/
`nqAnswerHtml`/`nextQuestionHtml`/`unlockNote`/`edgeNote`）、情景模式与冷却（~130）、
旧结果页与旧导出（~610：`renderResult`/`classicRows`/`domainBlock`/`bandOf`/`buildReport`/
`disclosures`/`exportMD`/`exportJSON`/`exportCSV` 等，都读 `D`）、旧事件监听与旧 `boot`（~180）。

**改写（保留骨架、去掉推断）**：`<head>` 脚本表、`#modes`（4→1）、导出菜单（去掉「复制报告」）、
`S` 状态、`renderTop`、`instModes`、`renderInstStage`（去掉 `ensureInfScope` 与 tier/scene 分派，
分页作答部分逐字节保留）、`INSTR_MODES`/`parseHash`/`defaultModeFor`（`["classic","tree"]`，
`#/tier`、`#/scene` 回落量表库）、`applyRoute`/`syncModeButtons`、`treeNodeState`（只留布局语义：
已答／最内环／支撑边邻居已答）、`recommendTreeItem`（只留「已答题数最少的维度」启发式）、
`renderInstTree`（只去掉推断面板那一行，**布局渲染逐字节保留**）、`renderStage`、
`saveLocal`/`loadLocal`/`clearLocal`（`emohealth.inst.v1`）、`importJSON`（只认
`emohealth.instrument.v1` 单量表存档）。

**工具层**：`tools/ui/pack_ui_data.py` 删除 `inference` 打包作业（连同我上一轮加的通用 `manifest`
清单能力，回到 5 个作业）；`--check` 从 17 个文件变为 **7 个**，仍逐字节一致。

## A4. 测试处置

| 测试 | 处置 |
|---|---|
| `test_confidence_dynamic.js` / `test_inference_ondemand.js` / `test_pid5_inference_ui.js` | **删除**（只测推断） |
| `probe_legacy_unlock.js` | **删除**（依赖已删的推断全局） |
| `test_scale_pages.js` | 最后一节改成**回退断言**（`#/tier` 回落量表库、顶层只剩 1 个入口） |
| `test_ui_rolled_back.js` | **新增**：反向断言推断已撤下（函数/全局/`ui/inference/*.js` 请求/文案），
同时断言天赋树**布局**仍渲染、经典逐题仍可作答 |

## A5. 判定为「拿不准」而保留的（保布局、撤推断）

1. `ui/tree-layouts/**` 与 `tools/build/build_tree_layouts.py`（用户点名的核心思想）。
2. `renderInstTree` 的环/簇/支撑边/节点状态/就地作答（只删了推断面板调用）。
3. `ui/net-layout.js`（大五支撑网络的离线坐标，是布局产物；当前不加载但保留）。
4. `data/adaptive-network.json`、`data/unlock-network.json`、`data/inference/**`（数据，不删）。
5. `tools/check/calibrate_ceiling_ratio.py` 等 7 个数据侧标定/诊断脚本（读 `data/**`+`archive/**`，
   属数据分析而非 UI 测试；将来复核参数要用）。
6. `#treecard` 容器与相关 CSS（容器保留、内容不再渲染，`renderStage` 会隐藏它）。

## A6. 证据

- `archive/`：**2041 文件 / 755,864,849 字节**（`tools/check/verify_archive.py`：2041 扫描 / 0 可疑 /
  268 清单项 0 问题）。
- `data/inference/ipip-neo.json` = 493,362 B、`pid-5.json` = 331,089 B（与 `MANIFEST.txt` 一致，未写）。
- **浏览器测试**：7 项全绿（105 ✅ / 0 ❌，逐项 `EXIT=0`）——
  `test_local_file` / `test_scale_pages` / `test_tree_mode` / `test_chain_nav` /
  `test_ui_rolled_back`（新增的回退断言）/ `test_l2_criteria_ui` / `test_pid5_norms_ui`；
  另有 `test_multiscale_fetch`(34✅) / `test_scale_export`(19✅) / `test_l1_threshold_ui`(6✅) 也全绿。
- **Python 测试**：`tools/check/` 下 9 项 `test_*.py` 全部 ❌=0、`exit=0`。
- `python tools/ui/pack_ui_data.py --check` → **7 个文件逐字节一致**（作业表由 6 个回到 5 个）。
- `python tools/check/check_index_completeness.py` → **未录入 0 / 悬空 0**；
  `check_readme_dups.py` → exit 0（无同小节重复）；`verify_architecture_guard.py` → 17/17 用例符合预期。
- 前后差异证据：`.shots/rollback-index.diff`（unified diff，190,389 B / 3,492 行）；
  回退前 `ui/index.html` 备份在 `%TEMP%\emohealth-index-pre-rollback-20261004-115045.html`（235,300 B）。
- 测试输出存档：`.shots/rollback-tests.txt`、`.shots/rollback-final.txt`。

### A6.1 架构守卫的**非本轮**问题（如实列出）

- C1（前端不得读 `archive/`）：`ui/` 6 个非生成文件、`tools/ui/` 15 个文件，**0 违例 / 0 未判定** ✅。
- C2（调研不得写 `data/`）：0 违例；**未判定 1 处**——`tools/survey/survey_orphans.py:138`
  （11:08 由其它任务新增，不在本轮写范围）。
- C3（数据层不得读 `ui/`）：**1 违例**——`tools/build/build_descriptions.py:443` 的一句**说明文字**
  里出现字符串 `ui/instruments/*.js`（该文件 11:58:22 由其它任务写入，不在本轮写范围）。
- 结论：本轮回退**自身**没有引入任何跨层引用（C1 全绿；改动的 `ui/index.html`、
  `tools/ui/pack_ui_data.py`、`tools/check/**` 均不在 C2/C3 的扫描范围内）。
  「三契约全绿 + 未判定 0」需要那两个**并行任务**把各自的文件收干净。

## A7. 没做干净 / 需 Lead 裁决

1. **CSS 未瘦身**：分级/情景的样式仍留在 `<style>`（删 CSS 风险大于收益）。
2. **三个数据产物变成无引用**：`ui/emohealth-data.js`、`ui/tier-data.js`、`ui/net-layout.js`
   （保留：将来 UI 阶段的输入；删了会让 `pack_ui_data.py --check` 失败）。
3. **`tools/README.md` 里 `calibrate_ceiling_ratio.py` 一行**仍写「相对上限比例门槛」——
   那是数据层标定，词句未改。
4. **`check_index_completeness.py` 现在是 未录入 0 / 悬空 0**（回退过程中曾短暂出现
   `tools/survey/_zhihu_queries_round2/3.txt` 两条未录入——那是 task-11 正在用的临时检索关键词文件，
   其所有者随后自行删除，我未动它们）。
5. **`.shots/` 里展示分级模式/置信度面板的旧截图**未清理（删除不可逆，且属 `stale-cleanup` 的判定范围）。
6. **两个 `check_*.js` 是坏的（非本轮引入）**：`tools/check/check_deploy.js:10` 与
   `tools/check/check_mobile_layout.js:25` 都有 `replace(/\/g, '/')`（少了一个反斜杠，
   `node --check` 直接语法错误）。两文件 mtime = 10:36:53（早于本轮），不在我改动的文件里；
   我没动它们——修这一行属于它们的作者，或由你决定是否让我顺手修。
7. **`ui/README.md` 只加了「历史文档」警示与两处「该测试已删除」标注**，没有重写 22 KB 正文；
   分级/情景/置信度那些小节仍在（作为设计记录），文首已明确标注「不再描述当前界面」。
