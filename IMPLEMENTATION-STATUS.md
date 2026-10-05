# IMPLEMENTATION-STATUS.md — 项目实现现状

> 更新日期：2026-10-04。本文档只描述**现状**（做成了什么、还缺什么）。
> **规则与计划以 [`PLAN.md`](PLAN.md) 为准**；技术分层见 [`ARCHITECTURE.md`](ARCHITECTURE.md)。

---

## 一、项目定位

提供心理学测评量表的**专业级自测陪伴**：

1. **缺失值容忍的测评结果**：允许答卷有缺失项，基于统计方法（题—维相关推断、部分施测精度）
   更新结果并**附带置信度**；
2. **本地化专业解读**：依据学术文献与专业手册，提供题目本地化解读与常见误区提醒
   （中英双版 + 内容讲解，见 `PLAN.md` R2）。

定位是「盲目自测」与专业就诊之间的陪伴工具，**不提供诊断**。

---

## 二、当前范围（2026-10-04）

收敛为 **4 个核心模型**：

| 核心模型 | 保留内容 | 状态 |
|---|---|---|
| **IPIP 大五** | `ipip-neo`（300 题全本：常模/推断/天赋树/脚手架全链路） | ✅ 最完整 |
| **PID-5** | `pid-5`（220 题，条件常模 + 题级推断参数 + 树布局） | ✅ 完整 |
| **DSM-5-TR** | `dsm5tr-l1`（13 域门槛）+ 8 册 `dsm5tr-l2-*` + `data/linkage/dsm5tr-chain.json` 链路 | ✅ 完整 |
| **MMPI-2** | **指标文档 + 元数据**（`data/descriptions/mmpi-2.md`）；**题项不入库** | ⬜ 待建成完整链路 |

* `data/instruments/`：**11 套**量表包（IPIP-NEO、PID-5、DSM5TR-L1、8 册 DSM5TR-L2）
* 已删除：非核心量表包及其前端生成包、多余天赋树布局、仅服务被删量表的构建脚本、
  非核心调研报告、文本库孤儿条目。删除清单见 [`SCOPE-REDUCTION.md`](SCOPE-REDUCTION.md)。
* `archive/`：**证据链**（2041 文件 / 720.8 MB），定位是**可溯源**；其中证据本身有误时按
  `PLAN.md` R3 记录 → 溯源 → 更正。

---

## 三、技术栈与架构总览

* **纯静态前端**：`ui/index.html` 单文件自包含应用（hash 路由、数据驱动、无硬编码量表清单），
  `file://` 离线可运行。
* **Python 数据生产与引擎**（≥3.9，numpy/pandas）：`engine/`（运行时评分库）、
  `tools/`（survey / build / analyze / check / ui / legacy 六类）。
* **三层解耦契约**（`tools/check_architecture.py` 守卫）：调研层 → 数据层 → 前端层；
  C1 前端不读 `archive/`、C2 调研不写 `data/`、C3 数据层不读 `ui/`。
* **数据流**：`data/instruments/*.json` → `build_catalog.py` → `build_ui_instruments.py`
  → `pack_ui_data.py` → `ui/*.js`。**改了 `data/` 就要重跑这条链。**

---

## 四、当前实现情况

### 4.1 文档与评估指标（P1，✅ 已完成）

每套量表一套**两件套**，由流水线生成、校验器守门（生成物禁止手改）：

| 产物 | 数量 | 说明 |
|---|---|---|
| `data/descriptions/<code>.md` | **12** | 六节固定结构：测什么 / 维度表 / 计分 / 解读基准 / 信度与出处 / 解读义务 |
| `data/norms/<code>.json` | **12** | 统一 schema；available 2（IPIP-NEO、PID-5）／partial 1（MMPI-2）／unavailable 9（DSM 各册，已逐册写明） |
| `content/descriptions/*.json` | **6** | 人工核对的证据源，每项事实带出处 |
| 证据链 | `research/descriptions-evidence/` | 数字→出处抽查、数据缺陷登记、MMPI-2 来源核实 |

```powershell
python tools/build/build_descriptions.py --check   # 生成物与磁盘一致
python tools/check/check_descriptions.py           # V1–V9 逐项校验（反向题逐项比对、常模明示、α 出处、禁止手改）
```

### 4.2 评分引擎（两代并存）

* **第一代（IPIP-NEO-300 专用）** `engine/assess.py`：`quality_gate()`（完整度、longstring、
  反义一致性、`reliability_discount` 概率化降权——只降解读强度不改分数）；
  `score_facet()`（10 题求和 → 常模带 → SEM=SD×√(1−α) → 95% CI）；
  `interpret()`（强制包含常模适用性警示与 `interpretation_caveats`）。
* **第二代（数据驱动，通用）** `engine/instrument_schema.py` + `engine/scoring.py`：
  dimension（可嵌套）→ item → rubric；聚合白名单 `{sum, mean, count_true, weighted_sum, lookup, none, max}`；
  `validate_against_declaration()` 独立重算防口径漂移。PID-5、DSM5TR 链走此路径。

### 4.3 缺失值与置信度

* **计分语义「缺失不猜」**：任一维度有题未答 → `complete=False`，不参与聚合；
  `assess.py` 部分作答返回 `INCOMPLETE`。
* **推断基础设施已就绪**：`data/inference/ipip-neo.json`、`pid-5.json`
  （`item_dim_corr` corrected 去本题口径、`pairB64` 题间相关、`dim_ceiling` 置信度上限）；
  `data/partial-administration.json`（前缀子集精度 r）。
* **判据**：实时置信度 ≥ `dim_ceiling × 0.90` 才采信（无题量门槛）；`item_dim_corr` 用 corrected 口径。
* **缺口**：尚无「缺失值 → 插补得分 + 置信区间」的正式引擎输出路径（推断目前止步于解锁/展示）。

### 4.4 内容与本地化解读

* `content/facets/*.record.json`（30 个 IPIP facet 档案）：license、construct（`does_not_measure`）、
  锚点语义、信度、常模警示、`interpretation_caveats`。
* `content/item_scaffolding.py`（300 题认知脚手架）：`asks` / `key_term` / `mis`（常见误读→修正）/
  `counts` / `notcount` / `edge` / `loc`（中文语境读法风险）。
* `content/translations.py` + `translation_overrides.py`；`data/text-db/`（606 条中英题面，
  `check_text_db.py` 闸门）。**中译复核状态分档**：IPIP-NEO 300 条已人工核对；
  PID-5 220 条与 DSM 86 条为「初稿待复核」。
* PID-5 与 DSM5TR 链**尚无**题目级脚手架与解读义务文本——待建（见 `PLAN.md` P4）。

### 4.5 前端

* 数据驱动：目录/清单/路由来自 `EMOHEALTH_CATALOG`/`EMOHEALTH_INSTMAP`，
  按需加载 `ui/instruments/<code>.js`。
* 作答模式：**分级**（天赋树网状图 + 信息增益自适应，仅 IPIP-NEO 开放）、**情景**（精度分层）、
  **经典**；答题中只给完成度不给分值。
* 核心硬编码仅 2 处且均属保留集：`DEFAULT_TREE_SCALE="IPIP-NEO"`、tier 模式仅对 IPIP-NEO 开放。
* **UI 不调 Python**：计分/推断在 JS 重新实现（双实现耦合，见 `PLAN.md` P3）。

### 4.6 测试现状

* Python（`tools/check/`）：`test_scoring`、`test_all_instruments`、`test_scene`、`test_catalog`、
  `check_text_db`、`check_dimension_coverage`、`check_item_truncation`、`check_tree_geometry`、
  `check_architecture`（C1–C3）、`check_descriptions`（V1–V9）、`check_index_completeness`。
* JS/CDP（headless Chrome 真浏览器）：`test_local_file`、`test_scale_pages`、`test_tree_mode`、
  `test_confidence_dynamic`、`test_inference_ondemand`、`test_pid5_inference_ui`、`test_pid5_norms_ui`、
  `test_l1_threshold_ui`、`test_l2_criteria_ui`、`test_chain_nav`、`test_multiscale_fetch`、
  `test_scale_export`、`check_mobile_layout`。
* 已知行为：DSM5TR-L2 中需 T 分转换的册（如 Anger）结果页**明示转换缺口、不渲染分数表**——
  这是「没有可核对来源就不给数字」（`PLAN.md` R1）的体现。

---

## 五、遗留与待办

| # | 事项 | 归属 |
|---|---|---|
| 1 | MMPI-2 完整链路（题项方案 + 评分接入 + UI） | `PLAN.md` P4 |
| 2 | DSM-5-TR 4 处题面数据缺陷（截断、混入授权句、NUL、选项组位置） | 已派 task-14（R3：修到好） |
| 3 | PID-5 中译 220 条人工复核 | 待派单 |
| 4 | 4 册 PROMIS 短表缺 raw→T 转换表 | 待派单（继续按 R1 找可核对来源） |
| 5 | 双实现耦合与两代引擎并存 | `PLAN.md` P2/P3 |
| 6 | 账本刷新（`tools/README.md` 计数、`MANIFEST.*`、`ARCHITECTURE.md` 数量） | 随 P3 |
| 7 | 代码与调研报告里约 40 处 `PLAN.md §x` 旧锚点 | 按 `PLAN.md` §7.1 映射表逐步改为实际锚点 |
