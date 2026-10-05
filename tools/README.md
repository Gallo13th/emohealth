# `tools/` 脚本索引
> ⚠️ **2026-10-05 事故与恢复记录（勿删）**：本文件曾被误清空（0 字节）。
> **主恢复源**：`%TEMP%\note-sandbox\tools\README.md`（74,209 B / 2026-10-05 16:35:50，事故前约 3 小时；另有同内容的保险副本 `%TEMP%\tools-README-RECOVER-74209B-20261005-163550.md`）——正文与 §0–§6 完整，仅缺当天新增的 9 个脚本的索引行，已用 `tools/legacy/autofill_readme_index.py` 按磁盘补齐。
> **兜底恢复源**：`C:\Codes\emohealth-pre-slim-backup-20261004.tar.gz` 内的 `./tools/README.md`（59,280 B / 2026-10-04 10:26），比主源旧、信息更少，仅作备用。
> **恢复程度**：正文与既有职责文字已取回；当天新增脚本的职责行由我（本人的脚本）或各作者补写；
> 本次基底里没有「索引行还在、文件已删」的悬空条目（0 条），§7 因此为空节。


**编制**　2026-10-03
**覆盖**　清理前 `tools/` 下全部 **159 个文件**（125 `.py` / 31 `.js` / 1 `.sh` / 1 `.json` / 1 `.md`），逐条列出
**依据**　每条职责取自脚本**文件头 docstring / 主函数**，不是从文件名猜的；
　　　　类别依据 `CLEANUP-PLAN.md` §3 的迁移映射（现为历史记录），并与 `python tools/survey_tools_layout.py` 的机械分类逐组对账
**配套**　`ARCHITECTURE.md`（三层契约）、`CLEANUP-PLAN.md`（工具目录清理的历史记录）
**迁移状态**　T2–T5 **已执行**（2026-10-03）。§3 的类别就是脚本**现在所在**的目录；
　　　　　　迁移记录（旧路径 / 新路径 / 移动前 sha256）见 `tools/cleanup_manifest.json`，
　　　　　　引用点已集中修复（脚本、根文档、`research/*.md`、`ui/README.md`）。
**后续**　T-CONVERGE-A（2026-10-03）：数据层写 `ui/*.js` 的 **5 个脚本全部收敛**——
　　　　数据层只出 `data/**`，前端包由新增的 `tools/ui/pack_ui_data.py` 打包（见 §3.5）。
　　　　守卫 C3 的「写入 ui/」计数由 10 处归零。

### 定类原则：**初筛用前缀，定案用契约**

目录名只是初筛规则。一旦前缀与**契约**（它读哪一层、写哪一层）冲突，以契约为准，
并且**改判必须留一行记录**——不许悄悄改。本项目已发生的两次改判方向相反、依据相同：

| 脚本 | 前缀初筛 | 实归 | 依据 |
|---|---|---|---|
| `build_tier_ui_data.py` | ui（规则含 `build_tier_ui`） | **build** | 它**读** `archive/…/ipip20993.dat`；放 `tools/ui/` 会违反 C1 |
| `build_tier_layout.py` | build（规则 `build_*`） | **ui** | 它**读** `ui/tier-data.js` 等前端数据包；放 `tools/build/` 会违反 C3 |

---

## 事故记录：2026-10-05 `tools/README.md` 被误清空

* **怎么坏的**：为补一行索引写的一次性片段里写成
  `io.open(p, "w", newline="").write(io.open(p, encoding="utf-8").read())`。
  **求值顺序**：先构造写句柄——**此刻文件已被截断成 0 字节**——再求值 `.write()` 的参数去读同一文件，
  于是读到空串、回写空串。与编码/权限无关。
* **硬规矩**：**永远不要在同一条表达式里既打开写句柄又读同一个文件**；
  改文本文件一律「**先读进内存 → 关掉 → 再写**」，并在写前断言长度不缩水。
* **恢复源（两份，均留痕）**：
  1. **主源** `%TEMP%\note-sandbox\tools\README.md` —— 74,209 B / 2026-10-05 16:35:50
     （保险副本 `%TEMP%\tools-README-RECOVER-74209B-20261005-163550.md`，sha 相同）；
     它是事故前约 3 小时的完整版，正文与 §0–§6 齐全，仅缺当天新增的 9 个脚本的索引行。
     另有 4 份更早副本（`anchor-sandbox` 15:51 / `struct-sandbox` 10-04 17:31 /
     `tools-README-before.md` 10-04 12:33 / `desc-sandbox` 10-04 11:56），逐份比对后未采用。
  2. **兜底** `C:\Codes\emohealth-pre-slim-backup-20261004.tar.gz` → `./tools/README.md`
     —— 59,280 B / 2026-10-04 10:26（比主源少约 15 KB 正文）。
* **本地不可恢复的证据（当时确实无从回滚）**：仓库 git 无任何提交；VS Code/Cursor Local History
  无该文件；工作区内无发行包/副本；DSH 会话存储三种扫法（整文件特征行、read 行号窗口、blob）均无快照。
* **已知、暂不处理（Lead 2026-10-05 决定）**：`check_readme_dups.py` 报**两项 ⚠️**——§3.1 表 46 行 vs 磁盘 42 个、§3.6 表 17 行 vs 磁盘 19 个。它们是 **exit 0 的警告、不是失败**；§3.7 里的「跨小节列举」是**有意**的（平铺工具的说明），抹平反而丢信息。这个文件刚从事故中恢复，**不做「去重 + 搬家」这类带判断的编辑**（上一次尝试曾插出重复，已回退）。**待有明确规则时再处理。**
* **防复发**：新增 `tools/check/check_size_regression.py`（大小回归 + 本文件结构断言），
  并请 `build_manifest --check` 补哈希比对（同一轮内内容改动）。

## 0. 怎么用这份索引

* 想找「某个数字/某套量表是怎么来的」→ 按**输入/输出**列定位脚本。
* 想迁移或改动某个脚本 → 先看它的**类别**（= 清理后的目录），再看 §4 的引用测量。
* 想加一个新脚本 → 先按 §1 的约定决定它属于哪一层，再在对应分组里补一行。

索引里的**输入/输出**取自脚本里的路径常量与读写调用（实测），未标注的细节以脚本自身为准。

---

## 1. 三类职责与目录约定

清理的目标是把「文献调研 / 统计表格再组织 / 网页前端交互设计」三件事分开。
本索引的类别就是**清理后脚本应处的目录**：

| 类别（目录） | 职责 | 读 | 写 | 硬契约 |
|---|---|---|---|---|
| **survey** → `tools/survey/` | 文献调研：检索、获取、登记、互证、归档 | 网络、`archive/` | `research/`、`archive/` | **C2** 不得写 `data/` |
| **build** → `tools/build/` | 数据组织：从 `archive/` 提取、清洗、组织成 `data/**` | `archive/`、`data/` | `data/**`（前端包由 `tools/ui/pack_ui_data.py` 打包） | **C3** 不得读 `ui/` |
| **analyze** → `tools/analyze/` | 统计与表格再组织：相关性、分级、常模、决策路径 | `archive/`、`data/` | `data/**` | **C3** 不得读 `ui/` |
| **check** → `tools/check/` | 守卫与测试：schema 校验、回归、几何/布局断言、契约守卫 | 全部（只读） | 无（少数写校验报告） | 只读不写产物 |
| **ui** → `tools/ui/` | 前端生成、预览、截图、同步 | `data/**`、`content/`、`ui/` | `ui/**`、截图 | **C1** 不得读 `archive/` |
| **legacy** → `tools/legacy/` | 一次性/演示脚本（`demo_*`），保留供追溯 | — | stdout | — |
| **平铺** → `tools/`（原地） | 共享库与跨层基础设施 | — | — | 判据见 §4 |

`engine/`（schema / scoring）被 build、analyze、ui 共用，**位置不变**；
`tools/_root.py`（Python）/`tools/_root.js`（JS 侧同一套判据）、`tools/check_architecture.py`
是本次新增的基座（见 §5）。

---

## 2. 计数与对账

**迁移后实测**（`tools/` 下按目录数文件）：

| 目标目录 | 脚本数 |
|---|---|
| `tools/survey/` | 28（另有 `survey_refs.py`、`survey_tools_layout.py` 按任务要求留平铺 → 合计 30） |
| `tools/build/` | 46 |
| `tools/analyze/` | 10 |
| `tools/check/` | 50 |
| `tools/ui/` | 15 |
| `tools/legacy/` | 4 |
| `tools/`（保留平铺） | 4 个共享库/运维（`pdftext.py`、`build_scales.py`、`item_coding.py`、`package.sh`）
+ 2 个测量工具 + `_root.py`/`_root.js`/`check_architecture.py`/`README.md`/`cleanup_manifest.json` |
| **159 个脚本的落位合计** | **159**（迁移 153 + 原地 6） |

分类与 `python tools/survey_tools_layout.py` 的**前缀初筛**对账
（初筛与实归的两处差异见文首「定类原则」）：

| 前缀初筛 | 数量 | 本索引的调整 |
|---|---|---|
| survey | 28 | 移出 `extract_workflow_results.py`（实际写 `data/text-db/`）；补入 `crosscheck_promis_tables.py`、`mirror_site.py`、`osf_johnson_spec.json` → 30 |
| build | 31 | 移出 `build_scales.py`（共享库，见 §4）、`build_ui_*`（前端产物）、`build_tier_layout.py`（读 `ui/`，见文首定类原则）；补入 `attach_*`、`batch_*`、`clean_*`、`collect_*`、`derive_*`、`exclude_*`、`export_*`、`extract_workflow_results`、`fix_*`、`label_*`、`merge_*`、`parse_uk_norms`、`translate_prompt.md`、`build_tier_ui_data` → 46 |
| analyze | 7 | 补入 `audit_scene_noise.py`、`compare_linear_vs_tree.py`、`diagnose_items.py` → 10 |
| check | 44 | 补入 `audit_capabilities.py`、`find_missing_zh.py`、`run_agent_eval.py`、`show_*`×3 → 50 |
| ui | 15 | 移出 `build_tier_ui_data.py`（读 `archive/`，见 §3.5 注）、补入 `build_tier_layout.py`（见文首定类原则）→ 15 |
| other | 34 | 全部按内容判定归入上述类别 |

> **注意**：`CLEANUP-PLAN.md` §0 印的分布是 `survey 27 / build 31 / analyze 7 / check 44 / ui 15 / other 34`
> （合计 158），而 `survey_tools_layout.py` 迁移前实测输出是 **survey 28**（合计 159）。
> 方案里 survey 少算 1 个，其余一致。


---

## 3. 脚本索引

### 3.1 `tools/survey/`　调研层（42）

| 脚本 | 职责 | 输入 | 输出 |
|---|---|---|---|
| `archive_apa_manuals.py` | 把 APA 的 PID-5 系列量表册 PDF 收进归档，记录来源、SHA256、授权原文 | 网络（APA 官方站点） | `archive/scales/<code>/{manual.pdf,source.json}` |
| `archive_dsm5tr_measures.py` | 按官方索引批量收 DSM-5-TR L1/L2 量表册，**逐册**提取授权原文 | `archive/scales/_apa-measures-index.json`、网络 | `archive/scales/<code>/{manual.pdf,source.json}` |
| `call_zhihu_api.py` | 通用知乎开放平台调用器：按 `<接口名> k=v …` 打任意端点，结果落盘便于反复查看（**鉴权须带 `X-Request-Timestamp`**，否则一律 403） | 环境变量 `ZHIHU_KEY`、developer.zhihu.com | `.zhihu_<接口名>.json` + stdout 结构概览 |
| `crosscheck_promis_tables.py` | 从多个独立第三方来源提取 PROMIS 短表转换表并互证 | 归档的第三方 PDF | stdout（互证结论） |
| `extract_dsm5tr_rules.py` | 提取 DSM-5-TR 各册的**判读口径与门槛规则**（不是常模分数） | `archive/scales/DSM5TR-*/manual.pdf` | stdout |
| `extract_l1_table1.py` | 提取 L1 手册 Table 1：13 域 → 门槛 → 对应 L2 量表（**链路的定义**） | `archive/scales/DSM5TR-L1/manual.pdf` | 模块级数据结构（被 `build_dsm5tr_chain.py` 引用） |
| `extract_l2_criteria.py` | 逐册提取 L2 判读口径，判定哪些自足、哪些需外部来源 | `archive/scales/DSM5TR-L2-*/manual.pdf` | stdout |
| `fetch_assets.py` | 通用资产下载器：按 JSON 清单抓取并逐件记录 sha256/来源/字节数 | `--spec` 清单（如 `osf_johnson_spec.json`）、网络 | 目标目录原始件 + `--manifest`（jsonl） |
| `fetch_pid5_norms.py` | 为 PID-5 抓取可溯源的常模资料（先入档，再谈使用） | 网络（Zenodo） | `archive/norms/pid-5/{原始件,source-log.json}` |
| `fetch_promis_manuals.py` | 按当前有效的 URL 模式批量获取 PROMIS 官方 scoring manual | 网络（PROMIS 站点） | `archive/norms/promis/{*.pdf,source-log.json}` |
| `fetch_zhihu_answer.py` | 取问题 518751517 的回答列表并定位目标回答，打印其 `Summary`（约 215 字，**非全文**） | 环境变量 `ZHIHU_KEY`、知乎开放平台 | `.zhihu_qa.json`、`.zhihu_target.txt` |
| `harvest_zhihu_content.py` | **片段收割器**：用 124 条检索式在 `zhihu_search`/`global_search` 上反复换词，把**同一篇内容的不同命中片段**归并去重（API 不给全文，换词重搜是唯一可行路径）；`probe` 另查额度、本人创作列表与「本人全文」端点 | 环境变量 `ZHIHU_KEY`、关键字清单（脚本内 `QUERIES`） | `.zhihu_harvest.json`（临时件）+ stdout 片段清单 |
| `inspect_text_review.py` | 查清中译的**来源层级**（`data/text-db` 的 `zh` 是权威源、还是会被 `zh_map`/批次回写覆盖）＋第 23 题现状，判断「该改源还是改产物」——2026-10-04 译文复核修正表的落点就是据此定的 | `data/text-db/text-db.json`、`data/scene-taxonomy.json` | stdout |
| `list_apa_measures.py` | 列出 APA「DSM-5-TR Online Assessment Measures」页面上的全部量表 PDF 链接 | 网络 | `archive/scales/_apa-measures-index.json` |
| `list_missing_batches.py` | 列出「还没中译的条目」落在哪些批次里，供精确补跑 | `data/text-db/pending/batch-*.json` | stdout（批次清单） |
| `list_tree_scales.py` | 列出题量 > 60、需要天赋树作答的量表（D114 规则） | `data/instruments/*.json` | stdout |
| `mirror_site.py` | 同域站点镜像器：原始字节落盘 + 逐件 sha256 台账 | `--start` URL、`--out` | `archive/ipip/site/**`、`site_manifest.jsonl` |
| `print_zhihu_doc.py` | 打印知乎开放平台**指定文档**的全文（端点、参数、示例），便于查某接口到底支持什么 | 本地 `.zhihu_docs.json` + 文档 key 列表 | stdout（文档全文） |
| `probe_crosscheck_tables.py` | 查交叉核对来源（Glasgow 学位论文）里印出了哪些 PROMIS 转换表 | 归档第三方 PDF | stdout |
| `probe_en_pool.py` | 验证英文池对那几道瑞典语/非英文题的同一 key 是否给出英文原题 | `archive/**/*.osd` | stdout（「可修 / 须排除」的判定） |
| `probe_ipip300_itemkey.py` | 读归档官方 ItemKey，确定 IPIP-NEO-300 的题号 → 正向/反向映射 | 归档 ItemKey（xlsx）、`data/ipip-neo-300.json` | stdout（列序核对结论） |
| `probe_ipip300_layout.py` | 探明 `IPIP300.dat`（98 MB 定宽）的字段布局 | `archive/datasets/osf-johnson/raw/IPIP300.dat` | stdout |
| `probe_mixed_language.py` | 查混合语言量表：本 OSD 自带的 `en` 池里能否取到英文原题 | `archive/**/*.osd` | stdout |
| `probe_pid5_norm_source.py` | 找 PID-5 常模的**机器可读**来源（Zenodo 常模表与分析代码） | 网络（Zenodo） | stdout |
| `probe_promis_tscore.py` | 确认 PROMIS 四册里到底有没有 raw → T 的对照表 | `archive/norms/promis/*.pdf` | stdout |
| `read_zhihu_docs.py` | 抓知乎开发者站**文档 API**（文档是 SPA，桌面/移动页 403，`/console/api/v3/docs` 可通），列出全部接口并抽出鉴权与端点线索 | 网络（developer.zhihu.com/console/api/v3/docs） | `.zhihu_docs.json` + stdout（接口目录、鉴权原文、端点） |
| `survey_anchor_quantification.py` | 测绘 2780 个选项锚点的量化状态（D 有定量 / V 凭自知已声明 / X 模糊无据）；**X 必须为 0**——即每个选项要么给出天数次数、要么明说「没有统一标准」 | `data/items-structured/*.json` | stdout（只测绘，不判退出码） |
| `survey_candidates.js` | 从量表清单里挑「一套完整的量表」（≥20 题、非语言主池等） | `research/scales/inventory.json` | `research/scales/candidates.json` |
| `survey_capability_gaps.py` | 测绘三套核心量表相对大五人格的**数据能力缺口**（A 可直接靠齐 / B 需文献补数据 / C 不适用），决定调研方向 | 见脚本 docstring | 见脚本 docstring |
| `survey_cross_layer.py` | 测绘「跨层动作」：列出数据层写/读 `ui/**` 的全部位置与方向 | `tools/{build,analyze,ui,survey}/**` | stdout（每处的层/脚本/行号/方向/目标） |
| `survey_devfacing_copy.py` | 测绘界面里「开发者/审阅者向」的文案（溯源依据/工程术语/开发者指标/免责声明），为「用户端产品化隐藏」定范围 | 见脚本 docstring | 见脚本 docstring |
| `survey_inference_deps.py` | 测绘前端推断/推荐逻辑对**大五专属数据**的依赖：函数清单、硬编码常量（MIN_OWN/UNLOCK_R/RIDGE）、全局包读取点——为通用化定边界 | 见脚本 docstring | 见脚本 docstring |
| `survey_ipip_conversion.py` | IPIP 家族试转 + 方向核查：找出「计分方向不可信」的维度 | `archive/**/*.osd` | `research/scales/ipip-conversion-report.json` |
| `survey_item_language.py` | 查每套含非英文题项的量表：归档里是否存在**英文**题文可用 | `archive/**/*.osd` | stdout（逐套「修 / 排除」判定） |
| `survey_neo_family.py` | 看归档里有哪些 IPIP-NEO 系列量表、项目里已有哪些 | `archive/**/*.osd`、`data/instruments/` | stdout |
| `survey_note_redundancy.py` | 测绘**提醒冗余**：同一句说明在多少个选项里重复（→ 说明该提到锚点级/量表级）；另扫 `ui/index.html` 里「做研究才会说」的措辞。**判据：最高重复数 ≤2** | `data/items-structured/*.json`（+`ui/index.html` 只读） | stdout（只测绘，不判退出码） |
| `survey_orphans.py` | 测绘范围裁剪的孤儿候选：只提被删量表标识、从不提核心标识的脚本或资产 | 见脚本 docstring | 见脚本 docstring |
| `survey_refs.py` | 测出 `tools/` 下哪些脚本被其它文件引用（能否安全移动的依据） | `tools/`、`engine/`、`content/`、`ui/` + 根文档 | stdout（`--json` 机器可读） |
| `survey_scales.js` | 把每个量表的授权/常模/计分/施测说明**四要素**提取成可判定清单 | `archive/ipip/data/OpenScales/**/*.osd` | `research/scales/inventory.json` |
| `survey_scope_reduction.py` | 测绘「保留 4 个核心、其余全删」的影响面：保留/删除清单与各目录规模 | 见脚本 docstring | 见脚本 docstring |
| `survey_stale_files.py` | 测绘「过时失效文件」候选：临时缓存 / 空文件 / **迁移遗留**（用 `cleanup_manifest.json` 的 old→new 全树比对）/ 悬空路径字面量 | 全树 + `tools/cleanup_manifest.json` | stdout（四类候选，只测不删） |
| `survey_structured_text.py` | 测绘结构化文本的支撑度：606 题的字段现状、选项缺口（当时 585 题无 options）、推断参数齐备度 —— 为「四字段结构化文本 + 事实预测」定范围 | 见脚本 docstring | 见脚本 docstring |
| `survey_tools_layout.py` | 为清理方案做现状测绘：按职责给 `tools/` 全部脚本分类 | `tools/` 目录列表 | stdout |
| `survey_translation_review.py` | 测绘本库中**待复核**的中译（按 `zh_source` 分档、逐条清单），为「继续复核」划定范围与判据——`2026-10-04` 的 337 条逐条复核就是按它的清单做的 | `data/text-db/text-db.json` | stdout |
| `survey_variants.py` | 统计归档里带多语言变体（`variants.sets`）的量表及处理情况 | `archive/**/*.osd` | stdout |
| `osf_johnson_spec.json` | `fetch_assets.py` 的下载清单：OSF Johnson 数据集 4 件（非脚本） | —（数据资产） | 被 `fetch_assets.py --spec` 读取 |

**与机械分类的差异**：`extract_workflow_results.py` 被机械规则判为 survey，但它实测写
`data/text-db/translation-results.json`——按内容归 build（否则迁移后会直接违反 C2）；
`crosscheck_promis_tables.py`、`mirror_site.py`、`osf_johnson_spec.json` 机械规则判为 other，按内容归 survey；
`build_tier_ui_data.py` 机械规则归 ui（规则含 `build_tier_ui`），但它**读** `archive/` 的作答数据集，
按 C1 必须在数据层（详见 §3.5 注与 §4.1）。

### 3.2 `tools/build/`　数据层（组织）（50）

| 脚本 | 职责 | 输入 | 输出 |
|---|---|---|---|
| `attach_linkage.py` | 把链路关系挂进各量表包，供界面做可点跳转 | `data/linkage/dsm5tr-chain.json`、`data/instruments/*.json` | 就地更新量表包 `linkage` 字段 |
| `attach_norms.py` | 把常模挂进 IPIP-NEO-300 包，并给全部量表标注「有无常模」 | `data/norms/ipip-neo-300.json`、`data/instruments/*.json` | 就地更新量表包 `norms`/有无常模 |
| `batch_convert_ipip.py` | 批量转换「干净可转」的 IPIP 家族量表（按转写报告筛风险） | `research/scales/ipip-conversion-report.json` | `data/instruments/*.json`（经 `build_scales.py`） |
| `build_adaptive_data.py` | 为自适应选题打包题-题相关矩阵（信息增益选下一题） | `archive/…/validity/ipip20993.dat`、`data/ipip-neo-300.json` | `data/adaptive-network.json`（前端包 `ui/adaptive-data.js` 由 `tools/ui/pack_ui_data.py` 打包） |
| `build_agent_eval_set.py` | 构建陪伴 agent 评测集：七个压力场景（S1–S7）与提示词 | `engine/agent_contract`、`engine/session` | `research/agent-eval/{index.json,scenarios/*}` |
| `build_all_facets.py` | 把 30 个 facet 组装成完整档案记录（自动部分与人工撰写严格分离） | `data/ipip-neo-300.json`、`data/ipip-neo-120-mandarin.json`、`data/uk-norms.json`、`content/` | `content/facets/<facet>.record.json` |
| `build_catalog.py` | 生成多量表目录（界面入口） | `data/instruments/<code>.json` | `data/instruments/catalog.json`（前端包 `ui/catalog.js` 由 `tools/ui/pack_ui_data.py` 打包） |
| `build_descriptions.py` | 生成「可填量表文档 + 评估指标（含统计学结果）」两件套（`data/descriptions/<code>.md` 六节结构 + `data/norms/<code>.json` 统一 schema + 清单）；每个数字来自机器产物或带 `source` 的人工证据文件，拿不到依据就留白；`--check` 重新生成并逐字节比对 | `data/instruments/*.json`、`data/norms/*.json`、`content/descriptions/*.json` | `data/descriptions/**`、`data/norms/**` |
| `build_dim_ceiling.py` | 把推断数据改成「实时置信度 + 相对面向上限的比例」口径：`item_dim_corr` 改 corrected（去本题）、新增 `dim_ceiling`（答满该面向全部题时的 r）与 `ceiling_ratio=0.90`、移除 `min_own`。**⚠️ D116 起前端已撤下对该口径的消费**（数据保留） | `archive/…/validity/ipip20993.dat`、`data/instruments/*.json`、`data/inference/*.json` | `data/inference/ipip-neo.json`、`data/inference/pid-5.json` |
| `build_dsm5tr_chain.py` | 构建 DSM-5-TR 评估链路：L1 → L2 → PID-5 | `archive/scales/DSM5TR-L1/manual.pdf`、`tools/survey/extract_l1_table1.py` | `data/linkage/dsm5tr-chain.json` |
| `build_inference_data.py` | 构建**量表级推断数据**（题→维度相关 + 维度间相关），让「基于相关性的允许缺失值推断」不再只认大五；带级别保护（不覆盖更高级别） | 见脚本 docstring | 见脚本 docstring |
| `build_ipip_neo300.py` | 交叉两处来源构建规范的 IPIP-NEO-300 数据集（施测序 + 缺失题文） | `archive/datasets/osf-johnson/scoring/*`、`archive/**/IPIP-NEO.osd` | `data/ipip-neo-300.json` |
| `build_item_norms.py` | 题目级常模分布：为情景完成后的基线比较提供原料 | `archive/…/validity/ipip20993.dat`、`data/ipip-neo-300.json` | `data/item-norms.json` |
| `build_item_structured.py` | 把量表文档做成**三级结构化文本**（量表级 `instrument_guide` → 锚点级 `scale_guides[scale_id]` → 选项级 `items[].response.options`）：题文原文与中译逐题、**选项语义与量化状态只在锚点级说一次**、逐题锚点册（ASRM/FOCI）的语义随题走 | `data/instruments/*.json`、`data/text-db/text-db.json`、`content/item-anchors.json`、`content/facets/*.record.json` | `data/items-structured/<code>.json` + `index.json` |
| `build_l1_instrument.py` | 组装 DSM-5-TR L1 成人册量表包（域分 = 域内最高分，`max` 聚合） | `archive/scales/DSM5TR-L1/{items-extracted,source}.json`、`data/linkage/` | `data/instruments/dsm5tr-l1.json` |
| `build_l1_items.py` | 从 L1 手册提取 23 道题与 13 个症状域 | `archive/scales/DSM5TR-L1/manual.pdf` | `archive/scales/DSM5TR-L1/items-extracted.json` |
| `build_l2_criteria.py` | 逐册建立 L2 判读口径（八册口径互不相同） | `archive/scales/DSM5TR-L2-*/manual.pdf` | `data/criteria/dsm5tr-l2.json` |
| `build_l2_instruments.py` | 为 L2 各册生成量表包（含授权原文与计分声明） | `archive/scales/<code>/{items-extracted,source}.json`、`data/criteria/dsm5tr-l2.json` | `data/instruments/dsm5tr-l2-*.json` |
| `build_l2_items.py` | 从 L2 五册（Anger/Anxiety/Depression/Somatic/Sleep）提取题项与作答格式 | `archive/scales/DSM5TR-L2-*/manual.pdf` | `archive/scales/<code>/items-extracted.json` |
| `build_l2_items_rest.py` | 提取 L2 剩余三册（Repetitive/Substance/Mania）的题项 | 同上 | `archive/scales/<code>/items-extracted.json` |
| `build_mandarin_baseline.py` | 构建官方便携中文译本基线（IPIP-NEO-120 Mandarin，唯一规范中译） | `archive/ipip/site/Mandarin_translation_of_IPIP-NEO-120.htm`、`archive/**/*.osd` | `data/ipip-neo-120-mandarin.json` |
| `build_manifest.py` | 重新生成两份清单：逐字节校验与人类可读版 | 全仓文件（含 `archive/`） | `MANIFEST.sha256`、`MANIFEST.txt`（`--check` 只校验） |
| `build_norms_ipip300.py` | 用归档里 Johnson (2005) 的 IPIP-NEO-300 全量作答算常模 | `archive/…/raw/IPIP300.dat`、`archive/…/scoring/` | `data/norms/ipip-neo-300.json` |
| `build_norms_pid5.py` | 把 Zenodo 的 PID-5 常模长表转成项目统一常模格式 | `archive/norms/pid-5/norm_tables_long.csv` | `data/norms/pid-5.json` |
| `build_pid5_instrument.py` | 组装 PID-5 量表包（220 题 + 25 facet/5 域 + 授权） | `archive/scales/PID-5/{items-extracted,source}.json`、`data/pid5-scoring-keys.json` | `data/instruments/pid-5.json` |
| `build_pid5_items.py` | 从 APA 官方 PID-5 手册提取 220 道题（题干 + 0–3 计分） | `archive/scales/PID-5/manual.pdf` | `archive/scales/PID-5/items-extracted.json` |
| `build_pid5_psychometrics.py` | 从 PID-5 的**公开原始作答**（CC-BY-4.0，N=2,148）自算题级参数：220×30 题→维度相关、30×30 维度间相关、各 facet 的 partial 精度 | 见脚本 docstring | 见脚本 docstring |
| `build_pid5_scoring_keys.py` | 生成 PID-5 计分键（facet→题号、反向题、5 个域） | 手册计分表（转录常量） | `data/pid5-scoring-keys.json` |
| `build_quality_gate.py` | 用 20,993 人网络样本标定作答质量指标（可用性门） | `archive/…/validity/ipip20993.dat`、`data/ipip-neo-300.json` | `data/quality-gate-calibration.json` |
| `build_remaining_slices.py` | 组装 selfdiscipline / activitylevel 两个 facet 的档案记录 | `data/ipip-neo-300.json`、自译表、`data/uk-norms.json`、`content/` | `content/pilot/*.record.json` |
| `build_scene_taxonomy.py` | 把 Pass 1 的自由标签人工归并成正式情景分类法 | `data/_scene_cache/pass1.json`、`content/facets/*.record.json` | `data/scene-taxonomy.json` |
| `build_text_db.py` | 构建统一文本库（D113 流程第 ③ 步） | `data/instruments/*.json`、`content/item_scaffolding.py`、**`ui/emohealth-data.js`（读，跨层，见本节末注）** | `data/text-db/text-db.json` |
| `build_tier_ladder.py` | 生成最终分层阶梯，并把「交错性质」作为硬约束保留 | `archive/…/validity/ipip20993.dat`、`data/correlation-network.json`、`data/tier-design.json` | `data/tier-ladder.json` |
| `build_tier_ui_data.py` | 为「分级解锁」打包界面数据（按阶梯序出题、逐层解锁）——**读 `archive/` 的作答数据集，故属数据层**（见 §3.5 注） | `archive/…/validity/ipip20993.dat`、`data/tier-ladder.json`、`data/tier-design.json`、`data/uk-norms.json` | `data/tier-prefix.json`（前端包 `ui/tier-data.js` 由 `tools/ui/pack_ui_data.py` 打包） |
| `build_tree_layouts.py` | 为任意 > 60 题量表生成通用天赋树布局 | `data/instruments/catalog.json`、`data/ipip-neo-300.json` | `data/tree-layouts/<code>.json`、`data/tree-layouts/index.json`（前端包 `ui/tree-layouts/**` 由 `tools/ui/pack_ui_data.py` 打包） |
| `build_unlock_network.py` | 为「网络感知的提前解锁」打包运行时数据 | `archive/…/validity/ipip20993.dat`、`data/ipip-neo-300.json` | `data/unlock-network.json`（前端包 `ui/unlock-data.js` 由 `tools/ui/pack_ui_data.py` 打包） |
| `clean_l2_glyphs.py` | 清掉 L2 已提取数据里的「选择框」私有区字形（就地重写） | `archive/scales/DSM5TR-L2-*/items-extracted.json` | 就地重写同一文件 |
| `collect_translations.py` | 翻译结果落盘读取器：从 workflow 输出按批提取并**立刻**回写文本库 | workflow 输出（边跑边收） | `data/text-db/text-db.json`（回写） |
| `collect_translations_from_disk.py` | 从磁盘读译文文件回写文本库（推荐的收口方式） | `data/text-db/pending/<batch>-zh.json` | `data/text-db/text-db.json`（回写） |
| `derive_antonyms.py` | 从 Johnson 数据推导「心理测量反义题对」，并验证能否复现 RNDCORR | `archive/…/validity/ipip20993.dat`、`data/ipip-neo-300.json` | `data/antonym-pairs.json` |
| `exclude_non_english.py` | 排除「归档里只有非英文题文」的量表，并记录排除原因 | `data/instruments/*.json`、`archive/**/*.osd` | `data/instruments/_excluded/EXCLUSIONS.json`（+ 移动被排除包） |
| `export_pending_translations.py` | 按**重要性**给待译条目排序并分批，支持分组增量翻译 | `data/text-db/text-db.json`、`data/instruments/catalog.json` | `data/text-db/pending/{index.json,batch-*.json}` |
| `extract_workflow_results.py` | 从 workflow 的 spill 输出里抠出翻译结果 JSON（供 `merge_translations.py` 消费） | workflow spill 文本（含 `Return value:` 前缀） | `data/text-db/translation-results.json` |
| `fix_dsm5tr_licenses.py` | 把 L1 与 L2-Somatic 的授权原文补进归档记录（页脚没有，在正文里） | `archive/scales/<code>/manual.pdf`、`source.json` | 就地更新 `archive/scales/<code>/source.json` |
| `fix_neo_item_text.py` | 用项目权威产物校正 IPIP-NEO 转换包题文（措辞变体 + 一处瑞典语） | `data/ipip-neo-300.json`、`data/instruments/ipip-neo.json` | 就地更新 `data/instruments/ipip-neo.json` |
| `label_items_by_scene.py` | 用 embedding + 小模型为 300 道题做「生活情景」标注 | `data/ipip-neo-300.json`、`content/facets/`、硅基流动 API | `data/scene-labeling.json`、`data/item-embeddings.npy` |
| `merge_scenes.py` | 把作者文件 `content/scenes/<scale>.json` 合并成 `data/item-scenes.json`（每题一句情景展示）：全量校验（schema/scale/文件名一致、id 属于该册、不跨文件重复、`notes` ≤1 条、id 集合**恰好等于** 11 册全集）+ 确定性序列化（`--check` 可做字节比对；`--scenes-dir/--out` 供机制验证用） | `content/scenes/*.json`、`data/items-structured/*.json` | `data/item-scenes.json`（`--check` 只比对不写盘） |
| `merge_translations.py` | 把分派出去的翻译结果回写文本库（D113 第 ③ 步收口） | 翻译结果 JSON（每批一个 agent） | `data/text-db/text-db.json`（回写） |
| `parse_uk_norms.py` | 解析 IPIP-NEO-300 的 UK 常模分数带表（.docx，防列错位） | `archive/…/scoring/uk-norms/*.docx` | `data/uk-norms.json` |
| `translate_prompt.md` | 翻译批次的提示词资产：输入文件名 + 翻译要求（非脚本） | `data/text-db/pending/batch-005.json`（示例） | 供翻译 subagent 使用 |

> **已知的跨层动作**（数据层 ↔ 前端层，详见 `ARCHITECTURE.md` §5.1）：
>
> 1. ✅ **已收敛（2026-10-03，T-CONVERGE-A）——写 `ui/*.js` 生成包（5 个脚本，守卫曾报 10 处）**：
>    `build_adaptive_data`（`ui/adaptive-data.js`）、`build_catalog`（`ui/catalog.js`）、
>    `build_tier_ui_data`（`ui/tier-data.js`）、`build_tree_layouts`（`ui/tree-layouts/**`）、
>    `build_unlock_network`（`ui/unlock-data.js`）。
>    改法：数据层只出 `data/**`（新增 `data/tree-layouts/*.json`），前端包由
>    `tools/ui/pack_ui_data.py` 打包；守卫 C3 的「写入 ui/」计数**已归零**。
> 2. **读 `ui/emohealth-data.js`（1 个脚本，守卫漏检）**：`build_text_db.py:63` 用它取大五人格中译。
>    它把路径绑到**单字母变量** `p`，而守卫只跟踪长度 ≥3 或全大写的变量名，
>    所以 C3 报 0 违例**不等于**这一层真的干净。目标形态：改读 `data/**` 的中译来源。


### 3.3 `tools/analyze/`　数据层（统计与表格再组织）（14）

| 脚本 | 职责 | 输入 | 输出 |
|---|---|---|---|
| `analyze_block_and_network.py` | 「按维度分块解锁」是否成立：某维度答 R×6 题时与完整分相关 | `archive/…/validity/ipip20993.dat`、`data/ipip-neo-300.json`、`data/tier-ladder.json` | `data/network-edges.json` |
| `analyze_correlation_network.py` | 相关性网络：一道题能细化哪些分值（三张表） | `archive/…/validity/ipip20993.dat`、`data/ipip-neo-300.json` | `data/correlation-network.json` |
| `analyze_decision_paths.py` | 决策树能否定义「解锁路径」（节点级连接、按已回答组合解锁反馈） | `archive/…/validity/ipip20993.dat`、`data/ipip-neo-300.json` | `data/decision-paths.json` |
| `analyze_partial_administration.py` | 部分施测精度：只答 k 题时估计与完整 10 题分的相关 | `archive/…/validity/ipip20993.dat`、`data/ipip-neo-300.json` | `data/partial-administration.json` |
| `analyze_scene_precision.py` | 情景结构可用性：每个可能子集的估计精度（预先可枚举，运行时查表） | `archive/…/validity/ipip20993.dat`、`data/scene-taxonomy.json` | `data/scene-precision.json` |
| `analyze_tiered_unlock.py` | 分级解锁可行性：粗粒度题库与完整 300 题分的相关是否足够近似 | `archive/…/validity/ipip20993.dat`、`data/ipip-neo-300.json`、`data/uk-norms.json` | `data/tiered-unlock.json` |
| `audit_rtotal_curve.py` | 用「**答题数 n**」直跑引擎给出无歧义曲线（n=1..10），同时打印 `conf_r`（判据）与 `r_total`（估计准确度）、跨维度借用比例；并核对字段名（曾把 `borrowed_from_cross_dim` 读成 `borrowed_ratio`，导致「跨维借用恒为 0」的误判） | `data/inference/*.json`、`data/instruments/*.json` | stdout |
| `audit_rtotal_definition.py` | 审计 `r_total` 的**定义缺陷**：它把「已答本维度题的真实值」当已知量混进预测，所以「答得越多、与完整分的相关反而降低」是定义使然，不代表预测能力变差；给出「纯预测能力」的正确度量 | `data/inference/*.json`、`data/instruments/*.json` | stdout |
| `audit_scene_noise.py` | 噪声核查：用 embedding 找出与所属情景最不像的题 | `data/scene-taxonomy.json`、`data/item-embeddings.npy`、外部 API | `data/scene-noise-audit.json` |
| `compare_linear_vs_tree.py` | 线性 vs 非线性：预测面向完整分时树模型到底有没有用 | `archive/…/validity/ipip20993.dat`、`data/ipip-neo-300.json`、`data/tier-ladder.json` | `data/model-comparison.json` |
| `derive_pid5_item_norms.py` | 补 PID-5 题级均值/SD：两份公开原始作答**分样本**计算（0–3 与 1–4 两种尺度先各自按自己的 min/max 翻转反向题、再把 SKID 平移到 0–3），均值按人数加权、SD 用**组内合并**（不拼原始数据） | `archive/norms/pid-5-psychometrics/zenodo-extracted/data/*.csv`、`data/pid5-reverse-keys.json` | `data/item-norms-pid5.json` |
| `diagnose_items.py` | 题目级诊断：找出最需要脚手架/认知访谈的题目 | `archive/…/validity/ipip20993.dat`、`data/ipip-neo-300.json` | `data/item-diagnostics.json` |
| `optimize_tier_design.py` | 分级解锁的**约束优化**：设计可用的分层题库（保广度） | `archive/…/validity/ipip20993.dat`、`data/ipip-neo-300.json`、`data/uk-norms.json` | `data/tier-design.json` |
| `probe_engine_rtotal.py` | 用引擎直测「只答 1 题」时它报的 `r_total`，与经验 OLS 的 0.68 对照，定位「报告 0.99 vs 经验 0.68」的口径差异（`k`=遮住题数 vs `n`=答题数） | `data/inference/*.json`、`data/instruments/*.json` | stdout |

**与机械分类的差异**：`audit_scene_noise.py` 按 `audit_` 前缀本应归 check，
但它实测**写** `data/scene-noise-audit.json`——check 层的契约是「只读不写产物」，
因此按内容归 analyze。`compare_linear_vs_tree.py`、`diagnose_items.py` 机械规则判为 other，
按 `compare_`/`diagnose_` 与内容归 analyze。

### 3.4 `tools/check/`　守卫与测试（83）

| 脚本 | 职责 | 输入 | 输出 |
|---|---|---|---|
| `audit_capabilities.py` | 能力对账：以 IPIP-NEO-300 为基准，逐项核对每套量表实际有哪些能力 | `data/instruments/*.json`、`catalog.json` | stdout |
| `calibrate_ceiling_ratio.py` | 标定「相对该面向上限的比例」门槛：算各面向的 corrected ceiling 与 ratio∈{0.80,0.85,0.90,0.95} 下达门槛所需题量，说明为何选 0.90（绝对门槛 0.85 会让低 ceiling 面向永不达标） | `archive/…/validity/ipip20993.dat`、`data/ipip-neo-300.json` | stdout |
| `calibrate_conf_gate.py` | 重标定 `conf_r`（可借跨维度）的门槛：给出「无跨维度」轴上各 ratio 的达门槛题量/永不达标数（说明 0.90 原样成立）、跨维度轴上的分布与各 ratio 后果、以及界面分母建议值 `dim_ceiling_cross`；`--write` 落盘 `dim_ceiling_cross`／`ceiling_ratio_cross` | `data/inference/*.json`、`data/instruments/*.json` | `research/conf-r-cross-calibration.md`（+ `--write` 写 `data/inference/*.json`） |
| `check_chain_fields.py` | 守卫：**挂载期字段不得被生成器重跑静默抹掉**——量表包必须齐备 `linkage`（L1 起点 + 13 downstream / L2 upstream / PID-5 的 `related.status=inferred`）与 `norms_status`。2026-10-04 实测过一次：重跑 `build_l1_instrument.py` 把这两个字段冲掉，L1 链路条与 PID-5 入口**静默消失**（页面零异常，`test_chain_nav` 才报） | `data/instruments/*.json`、`data/linkage/dsm5tr-chain.json` | stdout；缺失则 exit 1 |
| `check_cli_encoding.py` | **守卫：GBK 控制台下「每轮必跑」命令不许崩**。Win 默认控制台是 GBK，脚本打印 `✓ ✅ ❌ ⚠️` 会抛 `UnicodeEncodeError`，**退出码 1——与「真的发现问题」不可区分**（`pack_ui_data.py` 更糟：崩在写盘之后＝「成功却报错」）。命令清单**从 `PLAN.md` 的「每轮必跑（复现命令）」代码块解析**（不另抄一份；解析不到即报错退出），每条都用 `PYTHONIOENCODING=gbk` 子进程跑；**业务性红（exit≠0）不算失败**，只有崩溃（stderr 含 `UnicodeEncodeError`/`Traceback`）与「命令无法启动」才算 ❌；前一条崩溃会在下一条前打「⚠️ 可能是级联」；清单收录本守卫时跳过自身（防无限递归）。`--selftest` 在去掉兜底的临时副本上证明它会红 | `PLAN.md`（清单唯一来源） | stdout；任一命令崩溃则 exit 1 |
| `check_css_vars.py` | 检查 `ui/index.html` 里被引用但**未定义**的 CSS 自定义属性 | `ui/index.html` | stdout（退出码） |
| `check_deploy.js` | 在 WSL `/emohealth/` 子路径下核对页面真能跑（CDP 直连无头 Chrome） | 部署后的页面 | stdout（断言结果） |
| `check_descriptions.py` | 校验描述文档与常模记录 V1–V9：章节结构、清单一致、**反向题逐项**、常模 schema、α 出处、MMPI-2 版权、生成物未手改（非假绿：7 类破坏植入全部捕获） | 见脚本 docstring | 见脚本 docstring |
| `check_dimension_coverage.py` | 核对每套量表的**每道题都归属某个维度** | `data/instruments/*.json` | stdout |
| `check_dsm_item_text.py` | 守卫：量表包的题面/选项**不得**含控制字符、授权句、方括号不配对、以省略号结尾；并校验 `provenance.item_options` 与 `items[].options` 镜像一致；L1 追加「每题以 `?` 结尾」不变量（截断征兆） | `data/instruments/*.json` | stdout；有污染则 exit 1 |
| `check_index_completeness.py` | 对账：`tools/README.md` 的索引表 vs 磁盘实际文件（未录入 / 悬空条目） | `tools/README.md` + `tools/**` | stdout；不一致则 exit 1 |
| `check_item_language.py` | 扫描全部量表包，找出非英文题项（混进的翻译串） | `data/instruments/*.json` | stdout |
| `check_item_structured.py` | 校验三级结构化文本 V1–V13：**`text_en` 对量表包、`text_zh` 对文本库逐字节一致**、三级齐全、**每个选项都有定量数字或锚点级「凭你自己的判断」声明**（V11/V12）、**同一句在同一量表内重复不得超过 N 个选项**（V13，默认 N=2，防止把高级内容塞进低级选项）、生成物未手改（反例：7 类破坏全部捕获） | `data/items-structured/*.json`、`data/instruments/*.json`、`data/text-db/text-db.json`、`content/item-anchors.json` | stdout（退出码） |
| `check_item_typo_repair.py` | 守卫：606 道英文题干的**排版缺陷**已修、且修复留痕没被破坏。三条断言：① 用户可见 `text_en` 无排版缺陷——`content/en-repairs.json` 的 `repaired` 必须已贯通到 `text_en`，再对全部题跑 **5 条启发式**（H1 常用词切分粘连 / H2 闭引号后缺空格 / H3 撇号后缺空格 / H4 标点后缺空格 / H5 多余与首尾空白）＋由 `repairs` 派生的粘连串黑名单；为防误报，H1 配 **35 条已知合法形态白名单**（`into`/`something`/`become`… 是把切分跑遍 606 题后逐个人工核对得来），并**不做**「稀有词也可疑」的放宽（实测真阳性 0、假阳性 8）。② 每条 `repairs` 的 `verbatim` 必须在**上游源文件**（`data/instruments/*.json` 的 `items[].text` 或 `data/text-db/text-db.json` 的 `entries[].en`）逐字命中——证明留痕不是编的。③ **数据层用户可见字段**不含「排版噪声 / 缺空格 / 漏空格 / 直译」（`data/item-scenes.json` 除外）。口径 `TEXTDB_NOTE_IS_VISIBLE = False`（已裁决）：`data/text-db/text-db.json` 的 `note` 是**不可见留痕**（译者备忘，`ui/` 零引用，属 R5 留痕），只警告、不计失败 | `content/en-repairs.json`、`data/items-structured/*.json`、`data/instruments/*.json`、`data/text-db/text-db.json`、`data/**` | stdout（退出码） |
| `check_pack_freshness.py` | **守卫：`data/**` 改了但 `ui/**` 没重新打包**——对 `pack_ui_data.py` 的**每一条 job** 分别比「最新输入 mtime」与「最旧产物 mtime」（不是全局最大 mtime，避免无关文件一改就误报）；预期产物缺失（新增源文件却没重打包）同样报红。`--selftest` **真的**改一个输入的 mtime 再逐纳秒还原，断言「注入→❌、还原→✅」，并在沙盒里复现「新增源文件未打包→产物缺失」，证明守卫不是空转 | `tools/ui/pack_ui_data.py` 的作业表（`inputs`）、`data/**`、`engine/**`、`ui/**` 的 mtime | stdout；任一 job 过期/产物缺失则 exit 1 |
| `check_readme_dups.py` | 查本索引是否有**同一小节内**的重复条目（跨小节同名属正常引用） | `tools/README.md` + `tools/**` | stdout；有重复则 exit 1 |
| `check_item_truncation.py` | 检查已提取题项里有多少条**在句中截断**（折行续接丢失） | `data/instruments/*.json`、`archive/**/items-extracted.json` | stdout |
| `check_l1_interpretation.py` | 检查 L1 量表包的判读口径是否完整（13 域门槛 + PID-5 接口） | `data/instruments/dsm5tr-l1.json` | stdout |
| `check_l2_criteria.py` | 核对八册 L2 的计分聚合与判读口径是否齐备自洽（Substance 不能是 sum） | `data/criteria/dsm5tr-l2.json`、`data/instruments/dsm5tr-l2-*.json` | stdout |
| `check_l2_fields_persist.py` | 核对 L2 各册**重新生成后**仍保有 linkage 与 criteria 字段 | `data/instruments/dsm5tr-l2-*.json` | stdout |
| `check_l2_glyphs.py` | 确认 L2 题面与选项文本里没有残留的「选择框」字形 | `archive/scales/DSM5TR-L2-*/items-extracted.json` | stdout |
| `check_missing_format.py` | 检查哪些量表缺少作答格式信息（`response_format`） | `data/instruments/*.json` | stdout |
| `check_mobile_layout.js` | **移动端布局门**：用真实浏览器（CDP + `Emulation.setDeviceMetricsOverride`）量三档窄屏（390×844 / 360×640 / 414×896）的**渲染后几何**，断言 9 条体验约束：① 文档/卡片/SVG/选项**都不横向裁切**；② 天赋树图按卡片宽展开（不是被卡死）；③ 图保持 viewBox 比例（720×620）；④ 220 个节点渲染且解锁状态可见；⑤ **预测面板有高度上限**（不许把作答区推走）；⑥ 图在「面板+推荐」后仍能在 2.5 屏内到达；⑦ 经典逐题页同样不裁切；⑧ 首题在 2.5 屏内；⑨ 窄屏点选项能记录作答。`--selftest` 会注入「图卡 300 + 面板不限高」并**要求本检查报错**（防假绿） | `ui/index.html`、`ui/items-structured/*.js`、`ui/inference/*.js`（CDP，`file://`） | stdout（退出码） |
| `check_norms.py` | 核对新算的 IPIP-NEO-300 常模：数值合理性 + 与已有元数据对照 | `data/norms/ipip-neo-300.json`、`ui/emohealth-data.js` | stdout |
| `check_scene_sourcing.py` | **材料可查性哨兵**：对 11 册 606 题逐题确认「材料库里查得到」，按**三条通道**分别统计并打印——① `text_en` 命中；② `text_en_verbatim` 回退命中（展示层修过排版如 `Ikeep`→`I keep`，材料 key 按 R1 保留 verbatim，共 23 题）；③ 两者都不中 ⇒ **红**。归一化只用 `tools/textkey.py::norm_key()`，索引用生成器产出的 `data/text-db/index-norm.json`；另查索引漂移与「比纯派生多出的键」。所有分支统一产出 `(entry key, entry)` 或 `None`：**兜底/判红分支不允许留在崩溃路径上** | `data/items-structured/*.json`、`data/text-db/text-db.json`、`data/text-db/index-norm.json`、`tools/textkey.py` | stdout（有红=1；`--items` 逐题列分类与通道） |
| `check_size_regression.py` | **跨清单重算的缩水哨兵**（与 `build_manifest --check` 分工：那个守**同一轮内的内容改动**（哈希）；本脚本守**跨轮**——MANIFEST 重算后哈希基线随之更新，而「当前大小 vs 上一轮记录」仍能抓出量级缩水）：读 `MANIFEST.txt` 记录的**文件大小**与磁盘比对——文档（.md/.txt/.rst）缩水 >20%、其它文件 >50% ⇒ ❌，逐条列出「文件、记录大小、当前大小、缩水比例」；另加 `tools/README.md` 的结构性断言（非 0 字节、索引表行 ≥200、`### 3.x` ≥6、字节 ≥ 记录的 80%）；已删除文件只提示不判红 | `MANIFEST.txt`、磁盘现状、`tools/README.md` | stdout（有 ❌=1；`-v` 全列） |
| `check_test_targets.py` | 守卫：浏览器测试的默认目标不得指向部署副本（否则对着旧构建假绿） | 见脚本 docstring | 见脚本 docstring |
| `check_text_db.py` | 文本库校验器（D113 第 ④ 步闸门）：不过就不生成前端数据包 | `data/text-db/text-db.json` | stdout（退出码） |
| `check_time_window.py` | 守卫：`data/text-db/text-db.json` 每条 `note` 里的**回忆时间窗**（「过去/近 + 两周/7 天/12 个月…」）必须与该题所属册的**权威时间窗**一致；权威值取自 `data/items-structured/*.json` 的 `instrument_guide.time_frame_zh`（**以生成物为准**，守卫里不另立口径）。裸时间词（「一时」「短时」「日均」）不判；**模糊窗（如「近期」）进「未判定」并列出——不判错也不放过**；不一致则报 `所属册 + entry key + note 片段 + 两个时间窗`。改 `note` 须在 entry 上留 `note_fix`（原文 → 更正 → 依据） | `data/text-db/text-db.json`、`data/items-structured/*.json` | stdout（退出码；`--db` 可指向别的文本库做回归/自测） |
| `check_tree_geometry.py` | 检查树布局几何：内环半径是否足够大、坐标是否铺开 | `ui/tree-layouts/index.json` | stdout |
| `curve_corrected_vs_inflated.py` | 量化 inflated→corrected 对部分施测置信度曲线的影响（答 k 题时 R² 降多少、达 0.85 需几题） | `archive/…/validity/ipip20993.dat`、`data/ipip-neo-300.json` | stdout |
| `diagnose_ipip_recoding.py` | 裁决 `ipip20993.dat` 是否**已预编码**反向题：148 道反向题在未翻转时与同 facet 其余题的相关符号（实测 148/148 为正，中位 +0.536） | 见脚本 docstring | 见脚本 docstring |
| `diagnose_itemfacetr.py` | 比对 `AD.itemFacetR` 与 `NET.item_facet_corr` 是否一致（按名字对齐逐格 + argmax 判据），用于定位列序/口径错位 | 见脚本 docstring | 见脚本 docstring |
| `diagnose_pid5_alpha.py` | 诊断 PID-5 的 α 与已发表值（0.87）的差距：逐 facet 列 α 并标出拉低均值者 | 见脚本 docstring | 见脚本 docstring |
| `explain_minown_gap.py` | 核清大五 `UN.min_own`（写死 2）与 `INF.min_own`（partial 曲线反推）口径不一致的来源与实际后果 | `data/unlock-network.json`、`data/inference/ipip-neo.json`、`data/partial-administration.json` | stdout |
| `find_backtick_in_template.py` | 查模板字符串内部有没有未转义的反引号（会提前闭合模板串，报 missing ) 错） | 见脚本 docstring | 见脚本 docstring |
| `find_missing_zh.py` | 查大五人格 300 题里哪一条没进文本库（中译 299/300） | `data/text-db/text-db.json`、`ui/emohealth-data.js` | stdout |
| `inference_pyjs_compare.js` | Python↔JS 一致性对照的 **JS 侧执行器**（由 `test_inference_pyjs_consistency.py` 调用）：读 fixture、`predict()` 跑 JS 侧、结果写文件而非 stdout（避免管道/编码问题） | fixture JSON（`params` + `pairB64` + cases） | 结果 JSON |
| `inspect_unlock_rel.py` | 看清 `UN.rel` 的结构与取值，判断「去掉 MIN_OWN 后第 1 环会不会误解锁」 | `ui/unlock-data.js`（同源 `data/unlock-network.json`） | stdout |
| `ipip_scene_check.py` | `content/scenes/ipip-neo.json` 自查门：id 与 `data/items-structured/ipip-neo.json` 逐字对齐（300 个不多不少）、每条只能有 `scene`/`notes` 两键、`scene` **20–60 汉字**、禁用词/旧样式 0 命中、与题干不雷同（汉字 bigram 相似度 < 0.60）、必有第二人称「你」、`notes` 每题 ≤1 条 | `content/scenes/ipip-neo.json`、`data/items-structured/ipip-neo.json` | stdout（`--work` 查分批草稿、`--stats` 附统计） |
| `quantify_item_corr_bias.py` | 量化「含本题（inflated）」与「去本题（corrected）」两种题↔面向相关的差距，证明 `MIN_OWN` 是给虚高置信度打的补丁 | `archive/…/validity/ipip20993.dat`、`data/ipip-neo-300.json` | stdout |
| `run_agent_eval.py` | 跑陪伴 agent 评测集：真的调模型，两段式（确定性 C1–C6 + 判断性打分） | `research/agent-eval/index.json`、外部模型 API | `research/agent-eval/{outputs/*,results.json}` |
| `test_agent_contract.py` | 陪伴 agent 契约的不变量测试（固定住评测发现的 A1–A3 类缺陷） | `research/agent-eval/scenarios/*.json`、`engine/` | stdout（退出码） |
| `test_all_instruments.py` | 跨量表回归：对 `data/instruments/` 下每一套量表做统一检查 | `data/instruments/*.json` | stdout（退出码） |
| `test_catalog.py` | 多量表目录自检：条目数 = 实际套数、pack 文件存在 | `data/instruments/catalog.json`、`ui/catalog.js` | stdout（退出码） |
| `test_chain_nav.js` | 链路跳转：L1 → L2 → PID-5 上下游都能点通且推论有标注 | `ui/index.html`（CDP） | stdout（退出码） |
| `test_forecast_gains.js` | 信息增益前瞻的 **node 级**数值测试：① `forecastGains` 的 after 与**同一个** `dimConfidence` 逐值一致（1000+ 组候选×维度）；② 不泄露（入参只有题号；塞假值不影响）；③ 候选池；④ 增益非负、conf_r 只增不减；⑤ 硬规则；⑥ 性能四档 + 退化 `n_slow` 比例；⑦ 与旧「答得最少维度」启发式的实例对比 | `ui/lib/inference.js`、`ui/inference/*.js`、`data/tree-layouts/*.json` | stdout（退出码） |
| `test_inference_engine.py` | `engine/inference.py` 单测：official/inferred 分层、边界（0/1/答满）、`conf_r` 与 `dim_ceiling` 同口径、硬规则 `NO_OWN_ITEM_ANSWERED`、跨维度借用、`ceiling_cross` 显示分母、参数来源与错误处理 | `engine/inference.py`、`data/inference/*.json` | stdout（退出码） |
| `test_inference_pyjs_consistency.py` | Python↔JS 一致性对照：59 组合成作答（含 0 题/1 题/答满/混合/全卷/硬规则/跨维借用）逐字段比对 `ui/lib/inference.js` 与 `engine/inference.py`（容差 1e-6；官方分 4 位小数单独定容差） | `engine/inference.py`、`ui/lib/inference.js`、`inference_pyjs_compare.js` | stdout（退出码） |
| `test_item_coding.py` | 计分方向回归测试（反向题翻转与否取决于数据源编码状态） | `archive/…/validity/ipip20993.dat`、`data/ipip-neo-300.json` | stdout（退出码） |
| `test_l1_instrument.py` | L1 量表包端到端测试，重点验证 `max` 聚合 | `data/instruments/dsm5tr-l1.json`、`engine/` | stdout（退出码） |
| `test_l1_threshold_ui.js` | 验证 L1 门槛型结果页：按门槛判定，**不显示百分位** | `ui/index.html`（CDP） | stdout（退出码） |
| `test_l2_criteria_ui.js` | L2 逐册口径按 kind 呈现（分界/分带/逐项/待补 T 分） | `ui/index.html`（CDP） | stdout（退出码） |
| `test_local_file.js` | `file://` 直开验证：双击 `ui/index.html` 就能用（离线静态是硬约束） | `ui/index.html` | stdout（退出码） |
| `test_mania_options_ui.js` | 切换选项数据源后的回归：Mania 的 5 组 × 5 句陈述必须从**规范位置 `items[].options`** 渲染出来（打印页面 DOM 里的实际选项文本），并覆盖天赋树那条读取路径 | `ui/index.html`、`ui/instruments/dsm5tr-l2-mania.js`（CDP，`file://`） | stdout（退出码） |
| `test_multiscale_fetch.js` | 多量表按需加载实测：目录就位、注入 `<script>` 取数、缓存、错误路径 | `ui/index.html`、`ui/instruments/*.js` | stdout（退出码） |
| `test_pid5_instrument.py` | 验证 PID-5 量表包能端到端计分（含 14 道翻转题、不完整作答） | `data/instruments/pid-5.json`、`engine/scoring` | stdout（退出码） |
| `test_pid5_norms_ui.js` | 验证 PID-5 条件常模在界面上真能算出百分位（不是「—」） | `ui/index.html`、`ui/instruments/pid-5.js` | stdout（退出码） |
| `test_scale_export.js` | 验证子页导出真的产出文件，并核对内容自洽 | `ui/index.html`（CDP） | stdout（退出码） |
| `test_scale_pages.js` | 子页与路由专项：每套一个子页、URL 可直达/后退、导出按本量表范围 | `ui/index.html`（CDP） | stdout（退出码） |
| `test_scene.py` | 情景模式不变量测试（反向题方向语义、k≤2 不给分、过程不含分值） | `engine/scene`、`data/` | stdout（退出码） |
| `test_scene_sourcing_fuzzy.py` | `check_scene_sourcing.py` 的**常驻回归**：守住「兜底/判红路径不许崩」（曾有一个 fuzzy 兜底把 `found` 赋成 entry 字典，走进该分支必崩，而**崩溃退出码与真红同为 1、不可区分**）。合成数据钉三件事：① fuzzy 分支不抛异常且退出码 1、输出无 traceback；② 诊断照常打印（相似度＋疑似同题材料 key）；③ **形态不变量**：AST 断言 `found` 的每次赋值（含元组解包）只能是 `None` 或 `(key, entry)`。自身可被变异体证伪 | `tools/check/check_scene_sourcing.py` | stdout（绿=0 / 红=1） |
| `test_schema_roundtrip.py` | 用已有权威产物检验新 schema 转换器（逐字段比对） | `data/ipip-neo-300.json`、`archive/**/*.osd` | stdout（退出码） |
| `test_scoring.py` | 通用计分器与 schema 的测试（坏报文必被拦、手算期望值对照、跨量表） | `data/instruments/{ipip-catpd,ipip-neo}.json`、`engine/` | stdout（退出码） |
| `test_tree_mode.js` | 天赋树专项：>60 题默认进天赋树、节点可点、答完解锁邻居、可切回逐题 | `ui/index.html`（CDP） | stdout（退出码） |
| `test_item_fields_inference_ui.js` | 答题界面两条：**题面四字段**（`text_en`/`text_zh`/`options[].meaning_zh`/`notes_zh` 同时在 DOM 且与 `ui/items-structured/<code>.js` 逐字一致；IPIP 的 `project_editorial` 必须显示为「项目自撰」）与**各指标预测+置信度**（本维度一题未答→不出现预测与置信度、已答时数值与 `ui/lib/inference.js` 逐值一致、官方分缺失不猜）；并断言首页不加载按需数据包 | `ui/index.html`、`ui/inference/*.js`、`ui/items-structured/*.js`（CDP，`file://`） | stdout（退出码） |
| `test_user_visible_copy.js` | **用户端默认视野**（D118 / task-20）：用「用户实际看到的文字」（关闭的 `<details>` 只算 summary、`display:none`/`visibility:hidden` 不算、SVG `<title>` 不算）扫描开发者/审阅者关键词（`conf_r`/`dim_ceiling`/`ceiling_ratio`/`门槛`/`耗时`/`ms`/`utility`/`信息增益`/`inferred`/`project_editorial`/`manual_verbatim`/`n=`/`r=`/`官方分`/`已达上限` … 命中必须为 0），并断言 ① 用户要的东西仍在（题文四字段/情景说明/作答注记/估计徽章）；② **诚实性文案仍在默认视野**（「这是估计、不是已经测出来的得分」）；③ 打开「依据与出处」后仍能查到（`conf_r`/门槛/样本量/`meaning_source`/布局性质/常模来源与 n）；④ 硬规则仍成立（本维度未答 → 默认视野没有它的估计与可信程度）。同时打印**默认视野清单**供人审。⚠️ 门槛/分带型结果页（L1/L2）的「达到门槛」是**该册的用户语义**，不列入关键词 | `ui/index.html`、`ui/inference/*.js`、`ui/items-structured/*.js`（CDP，`file://`） | stdout（退出码） |
| `test_tree_unlock.js` | 天赋树「节点解锁 + 下一题推荐」专项（CDP 真浏览器）：① 解锁判据**不自创**（`conf_r ≥ dim_ceiling × 0.90`）含边界实测；② **硬规则单独断言**：别的维度全部答满、本维度未答 → 节点不点亮、依据表不出现 r、面板同为 blocked；③ 推荐 = 信息增益（页面 === 直接调 `forecastGains`，并列旧启发式做对照）；④ 不泄露；⑤ 性能四档与退化比例 | `ui/index.html`、`ui/lib/inference.js`、`data/tree-layouts/*.json`（CDP，`file://`） | stdout（退出码） |
| `validate_inference_holdout.py` | 题级预测的留出验证：场景 A（只答本维度、枚举全部子集）、场景 B（随机跨维度混合）、场景 C（阶梯前 m 题）、答题数 n 曲线、PID-5 两样本留出；把 `conf_r`（判据）与 `r_total`（估计准确度）与实测 `realized_r` 对照，并报 MAE ÷ 理论SE | `archive/datasets/osf-johnson/**`、`data/inference/*.json`、`data/norms/pid-5.json`、`data/tier-ladder.json` | `research/inference-validation-report.md`、`research/inference-validation.json` |
| `validate_records.py` | 量表档案校验器：实现 `instrument-record.schema.md` §10 的 V1–V7 | `content/facets/*.record.json`、`data/ipip-neo-*.json`、`data/uk-norms.json` | stdout（`--record` 单档案） |
| `validate_tier_design.py` | 分层设计的**过拟合检验**：拆半挑题/评估 | `archive/…/validity/ipip20993.dat`、`data/tier-ladder.json`、`data/uk-norms.json` | `data/tier-validation.json` |
| `verify_agent_output.py` | 校验陪伴 agent 输出是否守约（C1–C6 六类可测规则） | `--input` 契约输入、`--output` agent 输出 | stdout（退出码） |
| `verify_architecture_guard.py` | 架构守卫的**正反验证**：临时沙盒植入应命中/不应命中/未判定的用例，确认守卫不是「变瞎后假绿」 | 无（自建沙盒） | stdout；17/17 用例符合预期才 exit 0 |
| `verify_archive.py` | 归档完整性：文件真实类型与扩展名一致、核对 manifest 的 SHA-256 | `archive/**`（`--root`） | stdout；`--quarantine` 时移动伪装件 |
| `verify_manifest_check.py` | **`build_manifest.py --check` 的正反验证**：用真脚本副本在沙盒里断言三类差异都被报出**且类别正确**（逐项比对计数，不是「报了就行」）——① 名字不在清单（清单滞后）／② 清单有磁盘无／③ **名字在、内容被改**（正是 2026-10-05 `tools/README.md` 被清空成 0 B、而只比名字的旧版毫无反应的那一格）。三重保险：沙盒自带空 `MANIFEST.sha256` 当根标记、断言报告的是**沙盒规模**、跑完核对真 `MANIFEST.sha256`/`MANIFEST.txt` 未被改动。`--selftest` 把副本的哈希比对退回旧版，断言本测试抓得到 | `tools/build/build_manifest.py`（副本）、临时沙盒；对照真 `MANIFEST.sha256`/`MANIFEST.txt` | stdout；任一用例不符或真清单被改动则 exit 1 |
| `verify_norms_item_alignment.py` | 核对常模与量表包兼容——**按面向比对题集**，不按题号顺序 | `data/norms/ipip-neo-300.json`、`data/instruments/ipip-neo.json`、scoring xlsx | stdout |
| `verify_pairs_permutation.py` | 验证大五 `pairB64` 从 canon 题序重排到量表包题序是**等价置换**（特征值集合相同、仍正定），防止 A 与 b 不同序 | `data/inference/ipip-neo.json`、`data/adaptive-network.json` | stdout |
| `verify_pdftext_brackets.py` | 守卫：`tools/pdftext.py` 必须能取出**含方括号 `[…]` 的 TJ 数组**里的文字——DSM-5-TR L1 第 23 题题面截断的根因回归（词法层，不是提取脚本的业务逻辑） | `tools/pdftext.py`、样例 PDF | stdout（退出码） |
| `verify_pid5_norm_keys.py` | 核对 PID-5 常模量表标识与量表包维度名能否对上（防静默失效） | `data/norms/pid-5.json`、`data/instruments/pid-5.json` | stdout |
| `show_archive_licenses.py` | 列出 DSM-5-TR 各册归档记录里的授权原文，逐册核对 | `archive/scales/*/source.json` | stdout |
| `show_instruments.py` | 汇总 `data/instruments/` 下所有量表包的关键指标 | `data/instruments/*.json` | stdout |
| `show_missing_zh.py` | 列出最后没中译的条目，看是哪些、为什么被跳过 | `data/text-db/text-db.json`、`data/text-db/pending/*-zh.json` | stdout |
| `verify_truncation_guard.py` | 题文截断判据的正反验证：真实数据 0 条可疑 + 固定搭配不误报 | `data/instruments/*.json` + 被测判据 | stdout |

> **本表于 2026-10-03 从 50 项降为 44 项**：原先的 6 个 node DOM-stub 测试
> （`test_ui_{adapt,block,export,tier,tree,unlock}.js`）因 stub 只定义了 `global.window`
> 而缺 `addEventListener`，6 个**全部 `exit=1`**、报错一致
> `TypeError: window.addEventListener is not a function`，长期无效；
> 它们覆盖的界面行为已被**真浏览器测试**（真 Chrome + CDP：`test_local_file.js`、
> `test_scale_pages.js`、`test_tree_mode.js`、`test_chain_nav.js`、
> `test_l2_criteria_ui.js`、`test_pid5_norms_ui.js` 等）取代，故**已删除**。
> 删除清单、文件大小与删除前 sha256 见 `STALE-CLEANUP.md`。
> 另：`verify_architecture_guard.py`、`verify_truncation_guard.py` 是本次清理轮新增、
> 尚未录入本表（表 44 + 未录 2 = 目录实际 46 个文件，`Get-ChildItem tools/check -File`）。

> `check_*` 里两条边界情形（按内容保留在 check，但要知道它们会写东西）：
> `validate_tier_design.py` 写 `data/tier-validation.json`（校验报告）；
> `verify_archive.py --quarantine` 会在 `archive/` 内移动伪装件（默认只报告）。
> `run_agent_eval.py` 需要联网调模型，写 `research/agent-eval/`——是 check 层里唯一要外网的脚本。

### 3.5 `tools/ui/`　前端层（15）

| 脚本 | 职责 | 输入 | 输出 |
|---|---|---|---|
| `build_ui_bundle.py` | 为界面打包自包含数据（只嵌用户实际能走到的状态，无需浏览器内近似） | `data/ipip-neo-300.json`、`data/item-norms.json`、`data/scene-precision.json`、`data/uk-norms.json`、`content/facets/` | `ui/emohealth-data.js` |
| `build_ui_instruments.py` | 生成界面按需加载数据包（`<script>` 注入，`file://` 可用） | `data/instruments/catalog.json`、`data/text-db/text-db.json` | `ui/instruments/<code>.js`、`ui/instruments.js` |
| `build_tier_layout.py` | 把 300 题排成由**支撑关系**长出来的图，并定下 30 面向的角序（**按契约归 ui，见文首定类原则**） | `data/adaptive-network.json`、`data/tier-ladder.json`、`data/correlation-network.json`、`ui/tier-data.js`、`ui/adaptive-data.js`、`ui/unlock-data.js` | `ui/net-layout.js` |
| `dev_check_render.js` | 渲染产出的静态检查（语法、死代码、标注重叠几何） | `ui/index.html`、`ui/*.js` | stdout（开发用，不进交付） |
| `dev_probe.js` | 开发期探针：直接 eval `ui/index.html` 脚本，暴露内部函数 | `ui/index.html` | stdout（开发用，不进 v1 交付） |
| `pack_ui_data.py` | **前端打包器**：把 `data/**` 的 JSON 包成界面可加载的 `window.<VAR> = …;` 脚本（声明式作业表，新增包只加一条记录，且每条**显式声明 `inputs`**——job→输入映射，供 `tools/check/check_pack_freshness.py` 逐 job 比 mtime，引擎组装类作业漏写会漏判；`items-structured` 的包装头写明**题面五字段**（原文 / 中译 / 情景展示 `scenario_zh` / 选项情景说明 / 作答注记）；目录作业可加 `manifest` 顺带产出 code→路径的**小清单**供界面按需注入；`inference` 作业由 `engine/inference.py` 组装参数并 `sort_keys` 以保证 `--check` 逐字节一致；`--check` 只比对不写、`--list` 列作业） | `data/tier-prefix.json`、`data/unlock-network.json`、`data/adaptive-network.json`、`data/instruments/catalog.json`、`data/tree-layouts/*.json`、`data/items-structured/*.json`、`data/inference/*.json`（后者经 `engine/inference.py`） | `ui/tier-data.js`、`ui/unlock-data.js`、`ui/adaptive-data.js`、`ui/catalog.js`、`ui/tree-layouts/**`、`ui/items-structured/**` + `ui/items-structured.js`、`ui/inference/**` + `ui/inference.js` |
| `serve_dist.js` | 起极简静态服务，用于核对构建产物 | 构建产物目录 | 本地 HTTP 服务 |
| `serve_local.js` | 本地预览服务（`/ui/xxx` 与 `/xxx` 两种写法，防目录穿越） | `ui/` | 本地 HTTP 服务 |
| `shoot_mania.js` | 给 Mania（每题独立选项：5 组 × 5 句）出图，看选中态 | `ui/index.html`（CDP） | 截图文件 |
| `shoot_multiscale.js` | 给多量表界面出图：选择器、分页作答、结果页 | `ui/index.html`（CDP） | 截图文件 |
| `shoot_norms_result.js` | 给「有常模」的结果页出图（IPIP-NEO 300 题，显示百分位） | `ui/index.html`（CDP） | 截图文件 |
| `shoot_subpage.js` | 给子页出图：子页头部（返回 + 本量表导出）+ 内容 | `ui/index.html`（CDP） | 截图文件 |
| `shoot_tree.js` | 给天赋树出图（PID-5，答若干题后） | `ui/index.html`（CDP） | 截图文件 |
| `shoot_ui.js` | 界面截图工具（CDP 直连无头 Chrome，不需 puppeteer） | `ui/index.html`（CDP） | 截图文件 |
| `sync_blog.js` | 把运行时文件同步到博客仓库 `astro/public/emohealth/` | `ui/**` | `Myblogsource/astro/public/emohealth/**` |

> **注（`build_tier_ui_data.py` 为何不在本组）**：前缀初筛把它归 ui（规则含 `build_tier_ui`），
> 但它**读** `archive/datasets/osf-johnson/validity/ipip20993.dat`
> （98 MB 级作答数据集）——放在 `tools/ui/` 会直接违反 C1（前端层不得读 `archive/`）。
> 因此按内容归 `tools/build/`。它产出的是 `data/tier-prefix.json`（前端包 `ui/tier-data.js`
> 由本组的 `pack_ui_data.py` 打包）。这是**守卫实测**出来的，不是命名推断：见 §4.1。
>
> **注（`pack_ui_data.py` 的运行顺序）**：它读 `data/**`，所以必须排在数据层脚本**之后**；
> 而 `build_tier_layout.py` 与 `build_ui_instruments.py` 都读它产出的 `ui/*.js`
> （后者还读 `ui/tree-layouts/index.json`），所以要排在它**之后**。
>
> **注（`build_tier_layout.py` 为何在本组）**：它是反向的同一判断。前缀初筛归 build，
> 但它**读** `ui/tier-data.js`、`ui/adaptive-data.js`、`ui/unlock-data.js` 三个前端数据包，
> 写 `ui/net-layout.js`——完全在前端层内部工作，**不碰 `archive/`**。
> 留在 `tools/build/` 会实测违反 C3；按契约定案为 `tools/ui/`（见文首「定类原则」）。


### 3.6 `tools/legacy/`　一次性/演示（19）

| 脚本 | 职责 | 输入 | 输出 |
|---|---|---|---|
| `apply_scope_reduction.py` | 执行范围裁剪：删 5 个 IPIP-NEO5-20 与 2 个孤儿脚本，清单写进 SCOPE-REDUCTION.md | 见脚本 docstring | 见脚本 docstring |
| `autofill_readme_index.py` | 把**未录入索引**的脚本自动补进本索引（自动发现、按字母序、**幂等**）；占位职责需人工补写（见本条目） | 见脚本 docstring | 见脚本 docstring |
| `demo_agent_contract.py` | 陪伴 agent 契约演示：证明规则可测（1 份守约 + 6 份各违一条） | `engine/agent_contract`、`tools/check/verify_agent_output.py` | `--out` 目录（input/守约/违规样例 + prompt） |
| `demo_assessment.py` | 端到端演示：从真实样本挑不同作答风格的个体，看质量门能否区分 | `archive/…/validity/ipip20993.dat`、`engine/assess` | stdout |
| `demo_profile.py` | 多面向剖面演示：3 个 facet × 4 类真实作答者 | `archive/…/validity/ipip20993.dat`、`engine/assess` | stdout |
| `demo_scene.py` | 情景模式演示：模拟用户分几次完成情景，打印每步该看到什么 | `engine/scene`、`data/` | stdout（`--effort/--seed`） |
| `dedupe_readme_index.py` | 清本索引**同一小节内**的重复条目，并把错节的条目归回所属小节 | `tools/README.md` + `tools/**` | 本文件（原地改） |
| `fill_devfacing_duty.py` | 补写索引里指定脚本的占位职责（收口用；本脚本自己那条也由它补） | 见脚本 docstring | 见脚本 docstring |
| `fill_last_duties.py` | 补写索引最后几条占位职责（收口用） | 见脚本 docstring | 见脚本 docstring |
| `fill_new_duties.py` | 补写索引里**新录入条目**的占位职责（本脚本自己那条也由它补） | 见脚本 docstring | 见脚本 docstring |
| `fill_survey_duty.py` | 补写索引里指定脚本的占位职责（收口用；本脚本自己那条也由它补） | 见脚本 docstring | 见脚本 docstring |
| `fix_index_after_reduction.py` | 范围裁剪后修索引：删指向已删脚本的悬空条目、补写新脚本职责 | 见脚本 docstring | 见脚本 docstring |
| `fix_js_escape_bug.py` | 修批量正则替换引入的 JS 转义 bug（`replace(/\/g,'/')` 语法错误）——教训：批量替换后必须对产物跑 `node --check` | 见脚本 docstring | 见脚本 docstring |
| `fix_placeholder_duties.py` | 把 `autofill_readme_index.py` 留下的「待补写职责」占位文字替换成真实职责 | `tools/README.md` | `tools/README.md` |
| `fix_test_counts.py` | 把测试里写死的量表套数改为从 catalog 动态读（避免每次裁剪都要手改） | 见脚本 docstring | 见脚本 docstring |
| `fix_test_targets.py` | 批量把测试的默认目标从部署副本改为 file:// 直开工作区 | 见脚本 docstring | 见脚本 docstring |
| `patch_readme_index.py` | 把漏录的脚本补进**本索引**的表格（按字母序插入）并重算 §3.x 标题计数。⚠️ **无幂等检查**，连跑两次会插两遍（已踩过，故配 `dedupe_readme_index.py` 兜底） | 本文件 + `tools/**` 实际文件 | 本文件（原地改） |

### 3.7 `tools/`（保留平铺：共享库与基础设施）（4 个共享件 + 测量工具与基座）

| 文件 | 职责 | 为什么平铺 |
|---|---|---|
| `pdftext.py` | 最小但正确的 PDF 文本提取器（ToUnicode CMap + CID 字宽） | 被 12 个脚本 `import pdftext`（build/analyze/survey 三层都用），是共享库 |
| `build_scales.py` | OpenScales `.osd` → 多量表 schema 的统一转换器（`--all/--only/--list/--check`） | 被 338 个文件提及（含生成包溯源串），是转换入口，移动会牵动大量引用点 |
| `item_coding.py` | 作答数据计分方向的自动判定（反问题翻转取决于数据源编码状态） | 被 8 个脚本 `from tools.item_coding import …`（跨 build/analyze），是共享库 |
| `package.sh` | 打包供换机器使用（顺序有讲究：MANIFEST 必须在内容定稿后生成） | 跨层运维脚本，不属于任一层；生成 MANIFEST 属于基础设施 |
| `survey_refs.py` / `survey_tools_layout.py` | 本次的引用测量 / 布局测绘工具 | 留在 `tools/` 便于以固定命令复现；两者都已改为**递归**遍历新布局 |
| `_root.py` / `_root.js` | 统一的项目根定位（Python / JS 同一判据：向上找 `MANIFEST.sha256`） | 迁移后所有子目录脚本共用，见 §5 |
| `check_architecture.py` | 三条硬契约的守卫 | 只读不写产物；命令固定在 `python tools/check_architecture.py` |


---

## 4. 引用测量与「可安全移动」

**测量**（`python tools/survey_refs.py`，扫描脚本/文档/配置里的 `import`、`tools/xxx.py` 字符串与文件名出现）：

| 时点 | 文件数 | 无引用 | 被引用 | 说明 |
|---|---|---|---|---|
| **清理基线**：本索引与 `ARCHITECTURE.md` 建立之前 | 159 | **95** | **64** | `CLEANUP-PLAN.md` §0 记录的历史口径，已复核一致 |
| 加入 `ARCHITECTURE.md` + 两个新脚本后、本索引建立前 | 161 | 96 | 65 | 新增两脚本各占一格：`_root.py` 被 `check_architecture.py` 引用；`check_architecture.py` 暂无脚本引用 |
| **本索引建立后** | 162 | **0** | **162** | 索引列出了全部脚本名，工具把 `tools/README.md` 记成了**每个**脚本的引用者 → 这个总数**不再可用于判断可移动性** |
| **T2–T5 迁移后**（当前实测） | 164 | **1** | **163** | 递归遍历新布局；唯一「无引用」的是 `tools/cleanup_manifest.json`。索引效应仍在，判可移动性仍须剔除 `.md` 引用者 |

> 迁移后的复现命令同前：`python tools/survey_refs.py --json`。脚本名在输出里是
> **相对 `tools/` 的路径**（如 `build/build_scales.py`），因为脚本已分居子目录。

复现命令：`python tools/survey_refs.py --json`（第三行起是机器可读 JSON）。

**把「文档引用」与「代码引用」分开**（把 `.md` 引用者剔除后重算）：

* 被**非文档文件**引用：**40** 个——移动这些必须同步改引用点（T5 独占处理）。
* **仅被 `.md` 文档**引用：**25** 个——移动后只需改文档里的命令。

**保留平铺的判据**（`CLEANUP-PLAN.md` §3 的历史口径）：被 ≥3 个不同文件引用，或本身就是共享库。
按该判据排序（引用者数量）：

| 文件 | 引用者数 | 性质 |
|---|---|---|
| `build_ui_instruments.py` | 343 | 数字虚高：`ui/instruments/*.js` 生成的溯源串里写了脚本名（数据提及，非代码依赖） |
| `parse_uk_norms.py` | 35 | `content/facets/*.record.json` 的 provenance 字段提及（数据提及） |
| `build_all_facets.py` | 33 | 同上 |
| `extract_l1_table1.py` | 10 | 被 `build_dsm5tr_chain.py` 与生成包提及 |
| `build_tree_layouts.py` | 10 | `ui/index.html`、`ui/tree-layouts/*.js` 提及 |
| `build_l2_items.py` / `build_l2_items_rest.py` | 各 10 | 被 build 脚本与生成包提及 |
| `validate_records.py` | 7 | 被 `content/` 与文档提及 |
| `textkey.py` | 题文**归一化键**的唯一实现：`norm_key()`（NFKC、小写、弯引号统一、连字符/破折号折空格、**保留中日韩字符**——用 ASCII 白名单会把 Mania 的中文题干删光、让「序号相同而中文不同」的两条塌成同一个键而**假绿**）、`build_index()/index_collisions()/load_index()/render_index()`，以及 `lookup(entries, en=None, index=None, fallbacks=())`（**依序**试候选、返回首个命中的 `(entry key, entry)`，全不中返回 `None`，**不模糊匹配、不抛异常**）；`fallbacks` 承担「材料库 key 保留源件 verbatim、用户可见 `text_en` 已修排版」的分层差异（传该题自带的 `text_en_verbatim`），而不是把映射抄进索引。`data/text-db/index-norm.json` 由 `build_text_db.py` 用它生成（**只由 entries 派生、无别名**）、不许手改 | `data/text-db/text-db.json`（entries）、各题自带 `text_en_verbatim`（回退用） | `data/text-db/index-norm.json`（经 build_text_db） |

> **测量口径的局限**：`survey_refs.py` 按「文件名出现」计数，因此**生成产物与数据文件里
> 的溯源字符串**（`ui/instruments/*.js` 的 `evidence` 字段、`content/facets/*.record.json`
> 的 provenance 字段）会把计数推高。判断能否安全移动时，应看**代码引用**（§4 第 1 类），
> 而不是总数。

### 4.1 迁移前预警（按迁移后的目录结构实测）

方法：把本索引分类出的 155 个脚本**复制**（不移动）进一个临时沙盒，按目标结构摆好
（`tools/{survey,build,analyze,check,ui,legacy}/`，另配 `MANIFEST.sha256`、`ui/`、`data/instruments/`），
再跑 `tools/check_architecture.py`。结果（2026-10-03）：

| 契约 | 结果 | 明细 |
|---|---|---|
| C1 | ✅ 0 条 | 分类修正后（`build_tier_ui_data.py` 移入 `tools/build/`）：`tools/ui/` 14 文件、`ui/` 均不引用 `archive/` |
| C2 | ❌ 1 条 | `survey_scales.js:87` `fs.mkdirSync('data', {recursive: true})` |
| C3 | ❌ 1 条 | `build_tier_layout.py:56` 辅助函数 `load_ui_js()` 读 `ui/*.js` 数据包 |
| C3（写入，不计违例） | ⚠ 11 处 | 数据层写 `ui/*.js` 生成包（见 §3.2 注） |

> 第一次运行时 C1 报了 2 条（都来自 `build_tier_ui_data.py` 读 `archive/`）——
> 这正是把该脚本改归 `tools/build/` 的依据；修正后 C1 归零。

**迁移时处理的真实跨层依赖两条（已处理）**：

1. **`survey_scales.js:87`**（归 `tools/survey/`）——会在项目根创建 `data/`。
   它的实际输出是 `research/scales/inventory.json`（第 11 行 `const OUT`），
   而文件头注释曾写着「输出：data/scale-inventory.json」。
   **一行陈旧代码 + 一处过时注释**：迁移时已删除该 `mkdirSync` 并改正注释（行为不变，C2 归零）。
2. **`build_tier_layout.py:54-60`**——`load_ui_js()` 直接读 `ui/*.js` 前端数据包，属 C3 定义的
   「数据层读前端」。**按契约定案为 `tools/ui/`**（见文首「定类原则」），迁移后 C3 归零。

**已经因此修正分类的一条**：`build_tier_ui_data.py`（见 §3.5 注）——它在模拟里触发 C1，
按内容改归 `tools/build/`，迁移后该 2 条违例自然消失。

**迁移后实测**（2026-10-03，真实布局，不再是沙盒）：

```powershell
python tools/check_architecture.py
# ✅ C1  tools/ui/：15 文件，0 违例；ui/：6 文件，0 违例
# ✅ C2  tools/survey/：28 文件，0 违例
# ✅ C3  tools/build/：45 文件，0 违例，10 处写入 ui/（不计违例）；tools/analyze/：10 文件，0 违例
```

**T-CONVERGE-A 后实测**（2026-10-03，数据层写 `ui/` 的 5 个脚本已收敛）：

```powershell
python tools/check_architecture.py
# ✅ C1  tools/ui/：16 文件，0 违例，未判定 0 处；ui/：6 文件，0 违例，未判定 0 处
# ✅ C2  tools/survey/：29 文件，0 违例，未判定 1 处
# ✅ C3  tools/build/：45 文件，0 违例（**无**「N 处写入 ui/」提示）；tools/analyze/：10 文件，0 违例
# ✅ 三条契约全部通过（未判定 2 处，未判定 ≠ 通过）
```

> C3 那行原先的「10 处写入 ui/（不计违例）」已随收敛消失（该提示只在计数 > 0 时打印）：
> 5 个数据层脚本不再写 `ui/`，前端包改由 `tools/ui/pack_ui_data.py` 打包。见 §3.5。

> **C3 的 0 违例不等于数据层真的不依赖前端**：原 `build_text_db.py:63` 读
> `ui/emohealth-data.js`，但路径绑在单字母变量 `p` 上，旧版守卫看不见
> （`ARCHITECTURE.md` §5 已知局限）。新版守卫已能把它报成「未判定」；
> 这条登记在 §3.2 注与 `ARCHITECTURE.md` §5.1，留给下一轮。

---

## 5. 本次基座新增（不在这 159 个之内）

| 文件 | 作用 |
|---|---|
| `tools/_root.py` | 统一根定位：`find_root()`（向上找 `MANIFEST.sha256`，找不到抛错）、`add_tools_to_path()`、`add_root_to_path()`；`python tools/_root.py` 自检 |
| `tools/_root.js` | **JS 侧的同一套判据**（`require('../_root.js').findRoot(__dirname)`）：原先 17 个 JS 脚本用 `path.join(__dirname, '..')` 推根，迁移后会静默指到 `tools/`；`node tools/_root.js` 自检 |
| `tools/check_architecture.py` | 三条硬契约 C1/C2/C3 的守卫（见 `ARCHITECTURE.md` §5），目录不存在时「跳过并视为通过」 |
| `tools/cleanup_manifest.json` | T2–T5 的迁移记录（`{old, new, sha256}` × 153），回滚依据 |
| `ARCHITECTURE.md`（根目录） | 三层解耦契约、每层怎么跑与产物在哪 |
| `tools/README.md`（本文件） | 本索引 |
| `tools/ui/pack_ui_data.py` | T-CONVERGE-A 新增：**前端打包器**，把 `data/**.json` 包成 `ui/**.js` 的 `window.*` 赋值脚本（见 §3.5） |

因此 `tools/` 当前文件数 = **167** 个（按磁盘实际重算；索引表项 166 = 167 − 本文件自身）：

```
子目录   survey 30 + build 46 + analyze 10 + check 48 + ui 16 + legacy 6 = 156
平铺层   pdftext.py、build_scales.py、item_coding.py、survey_refs.py、
        survey_tools_layout.py、_root.py、_root.js、check_architecture.py、
        cleanup_manifest.json、README.md                             = 10
```

> ⚠️ 两处旧的「当前文件数」均已过期，保留作历史留痕：
> ① 本节原先写「159（脚本）+ 6 + 1 = **166**」——那是 **T2–T5 迁移时点**的快照；
> ② 中间一度写「**163**」——那是 T-STALE 之后、本轮新增脚本之前的快照。
>
> 后续变动：`tools-migrate` 修 ROOT 时新增 `_root.js`；`converge-pack` 新增
> `pack_ui_data.py`；`converge-read` 新增 `verify_architecture_guard.py`；
> `stale-cleanup` **删掉 6 个失效的 `test_ui_*.js`**；本轮新增
> `survey_cross_layer.py`、`survey_stale_files.py`、`check_index_completeness.py`、
> `check_readme_dups.py`、`verify_truncation_guard.py`，并把
> `patch_readme_index.py`、`dedupe_readme_index.py` 归入 `tools/legacy/`。
>
> **§2/§4/§5 其余计数表是历史快照**（保留作迁移留痕）；只有本节与 §3.x 标题按
> 磁盘实际维护——**索引的价值就是与实际一致**，所以「过期计数」改由两个检查持续
> 对账：`tools/check/check_index_completeness.py`（未录入 / 悬空）与
> `tools/check/check_readme_dups.py`（同小节内重复）。

---

## 6. 本索引的副作用与维护约定

1. **副作用（已实测）**：本索引列出了全部脚本名，而 `survey_refs.py` 按「文件名出现」判定引用，
   于是**每个脚本都会多出一个引用者 `tools/README.md`**，`ARCHITECTURE.md` 同理。
   判断「能否安全移动」时，请先把这些文档引用者剔除——`README.md`、`PLAN.md`、`ui/README.md`、
   `ARCHITECTURE.md`、`tools/README.md`、`CLEANUP-PLAN.md`、`instrument-record.schema.md`。
   建立索引前的基线是 **无引用 95 / 被引用 64**（`CLEANUP-PLAN.md` §0 的历史口径；本工作区不是 git 仓库）。
2. **维护**：脚本新增/移动/改名后必须同步本文件对应分组与 §2 计数，
   并跑 `python tools/check_architecture.py` 确认没有把跨层依赖带进来。
3. **不要用文件名反推职责**：新增/修改条目时，请打开脚本读 docstring。本索引的每一条职责
   都来自脚本自身的第一段说明。
4. **落位只在子目录里**：脚本一律放 `tools/<cat>/`；只有共享库与基座平铺在 `tools/`。
   移动脚本时不要改它的根推导写法——用 `from _root import find_root` / `require('../_root.js')`，
   它在哪一层都成立。


## 7. 已删除文件（索引行保留，供追溯）

**本节目前没有条目**：本次恢复所用的基底（2026-10-05 16:35:50）里已经不存在指向「文件已删」的索引行，`check_index_completeness.py` 的悬空条目为 **0**。

留这一节的用途：以后若出现「索引行还在、文件已删」，把该行**从 §3.x 表格里挪到这里**（换成列表形态）——`check_index_completeness.py` 把任何 `| \`name.ext\` |` 表格行都算作索引条目，留在表里就会报悬空；挪成列表既清掉悬空、又保留可追溯的名字。

（更早修订里曾索引过、后由 SCOPE-REDUCTION 等轮次移除的脚本，在本次可用的副本中已无其职责描述，**不在此处臆造**。）
