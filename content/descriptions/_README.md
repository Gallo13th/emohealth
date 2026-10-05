# `content/descriptions/` —— 文档证据源（人工核对）

这里放的是**量表文档的证据源**：`data/descriptions/<code>.md` 与 `data/norms/<code>.json`
都由 `tools/build/build_descriptions.py` 从本目录 + 机器产物生成。**生成物禁止手改**；
要改文案或补证据，改这里的 JSON 再重跑。

```powershell
python tools/build/build_descriptions.py     # 重新生成文档与常模记录
python tools/check/check_descriptions.py     # 12 套逐项校验（含反向题逐项比对）
```

## 文件

| 文件 | 服务 | 说明 |
|---|---|---|
| `ipip-neo.json` | `ipip-neo` | 量表级事实；30 个维度的构念解释**不在这里复制**，取自 `content/facets/*.record.json` |
| `pid-5.json` | `pid-5` | 量表级事实 + 25 facet 的通俗解释 + 5 域表 + 反向题争议（14 vs 16） |
| `dsm5tr-l1.json` | `dsm5tr-l1` | Level 1：13 域解释、门槛口径、`does_not_measure` |
| `dsm5tr-l2.json` | 8 册 L2 | **一个文件服务 8 套**：顶层共享 + `instruments.<code>` 特化 |
| `mmpi-2.json` | `mmpi-2` | **只有元数据与指标，题项留空**（版权） |

## 字段约定（每一项"事实"都带 `source`）

| 字段 | 含义 |
|---|---|
| `what_it_is` / `what_it_measures` | `{text, source}`；`source` 指向 `archive/` 原件或一条可核对文献 |
| `does_not_measure` | `[{text, source}]`：**明确不测什么**，防误用 |
| `dimension_order` / `dimensions` | 维度顺序与逐维解释；`gloss_source` 只允许两种：`derived_from_items:<题号>`（依题面推导）或指向 `content/facets/...`（已核对档案） |
| `display_chinese_items` | 是否在文档里展示中译题面（**按授权决定**：APA 禁改 → false） |
| `scoring_notes` / `score_ranges` | 计分口径与分值范围，逐条带 `source` |
| `norms_spec` | 常模记录的内容：`status`（available/partial/unavailable）、`interpretation_basis`、`reference_sample`、`evidence`、无则必填 `unavailable_reason` |
| `alpha` / `alpha_note` | α 与其出处；机器可得的（IPIP facet 档案、PID-5 自算）由生成器自动汇总 |
| `known_critiques` / `interpretation_caveats` | 已知批评；**哪些话不许说**（逐条带出处） |
| `evidence_gaps` | **拿不到依据的地方**（如实留白，不许编） |

## 三条纪律

1. **不编造数字**：拿不到写「没有」，并写清「为什么没有」（`evidence_gaps`）。
2. **区分「文献定义」与「依题面推导」**：后者必须写 `derived_from_items:<题号>`，不得冒充文献定义。
3. **授权优先**：题项能否展示、能否附中译，按 `source.json` 的授权原文决定，不由方便决定。
