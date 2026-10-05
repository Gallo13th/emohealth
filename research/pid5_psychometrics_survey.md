# PID-5 题级心理测量参数与判读分界值 · 文献调研报告

**调研目的**　确认文献里是否已有 PID-5（220 题）的**题级**心理测量参数与判读分界值，
以便让 PID-5 向大五人格（IPIP-NEO-300）的数据能力靠齐 —— 即补齐
`item_facet_corr`（题 × 面向相关）、`facet_corr`（面向间相关）与
`partial_administration`（只答 k 题与完整总分的 `r_min`）这三份数据。

**调研日期**　2026-10-04
**执行**　teammate `survey-pid5`（任务 `task-6`）
**网络路径**　Windows 直连 `Invoke-WebRequest -UseBasicParsing`（WSL 未使用）
**入档位置**　`archive/norms/pid-5-psychometrics/`（原始件只增不改；其中的派生件（如 `derived/`）有缺陷时按 R3 更正——见 `PLAN.md` R5）
**登记文件**　`archive/norms/pid-5-psychometrics/source-log.json`（哈希由脚本现算）

---

## 0. 结论先行

| 问题 | 回答 |
|---|---|
| 文献里有没有 **220 题的题级参数**？ | **没有。** 已核验的全部命中来源都只到 **facet 级（25 个值）**，没有 220 个值的题级载荷 / IRT 区分度 / 题间相关矩阵。 |
| 那题级参数能不能拿到？ | **能 —— 但不是从「参数表」，而是从公开的逐题原始作答自己算。** Zenodo [10.5281/zenodo.22280403](https://doi.org/10.5281/zenodo.22280403)（**CC-BY-4.0**）内含两份各 220 题的完整作答数据，合计 **N = 2,471**。 |
| 能拿到什么层级、够做什么？ | 按大五人格同一口径，**题级 × 面向相关（220×25）**、**面向间相关（25×25）**、**只答 k 题的 `r_min`（25 个面向全覆盖）** 全部算得出。已跑通并与已发表 facet 级统计量核对（见 §3）。**足够支撑「允许缺失值的拟实时结果推断」与「推荐答题」。** |
| 判读分界值有没有？ | 有，但**都不是 220 题版 + 通用人群**：一篇是波斯语 220 题版（付费墙），一篇针对 36 题 BF+M。**不能直接采用**（§2.4）。 |

> **一句话**：缺的不是「文献参数」，是「还没算」。原始作答是公开的、可再分发的。

---

## 1. 检索

### 1.1 渠道与检索式

| 渠道 | 检索式 / 入口 | 命中 |
|---|---|---|
| Europe PMC REST（结构化，可复现） | `("PID-5" OR "Personality Inventory for DSM-5") AND ("item response theory" OR "graded response model" OR "IRT")` | 85 |
| 同上 | `… AND ("standardized factor loadings" OR "item loadings" OR "item-level")` | 111 |
| 同上 | `… AND ("cut-off" OR "cutoff" OR "cut score" OR "cut scores")` | 302 |
| 同上 | `… AND ("item-total correlation" OR "item-total")` | 39 |
| 同上 | `… AND ("interfacet" OR "inter-facet" OR "facet intercorrelations")` | 1 |
| 通用检索 | `PID-5 220 items standardized factor loadings supplementary table` / `PID-5 item-level IRT discrimination parameters` / `PID-5 facet correlation matrix` / `PID-5 cut-off scores` | 见下 |
| 数据仓检索 | Zenodo API（记录 22280403）、OSF API（节点 `ba37m`）、GitHub/CRAN（`hitop` 包文档） | 见 §2.2 |
| Crossref API | 用于核实每个 DOI 的**授权条款**（不是转述，读 `license[]` 原文） | — |

检索脚本：`archive/norms/pid-5-psychometrics/derived/epmc_search.py`
（结果落 `derived/epmc/*.tsv`，逐条可核）。

### 1.2 预期的高价值方向与实测结果

任务书提示的三个方向都检索了：

- **Krueger et al. (2012)** 原始验证论文 —— 未找到任何公开的 220 题题级载荷表；
  该文报的是 **25 个 facet** 在 5 个域上的载荷（面向级）。
- **Zimmermann 团队** —— 找到的是**常模**产出（本目录已入档的 Zenodo 记录），
  其价值不在「参数表」而在**原始数据**（§2.2）。
- **报告 CFA 载荷表的大样本研究（含补充材料）** —— 见 §2.1，全部止于 facet 级。

---

## 2. 命中来源逐条评估

层级标注：`题级` = 220 个逐题值；`面向级` = 25 个 facet 值。

### 2.1 §目标①「文献里的题级参数」：**未命中**

| 来源 | 期刊/年 | DOI | 层级 | 实际报了什么 | 可否采用 |
|---|---|---|---|---|---|
| Bach, Sellbom, Bo & Simonsen | *European Psychiatry* 2016, 37:22–27 | [10.1016/j.eurpsy.2016.04.006](https://doi.org/10.1016/j.eurpsy.2016.04.006) | **面向级** | 补充材料 Table S1：25 个 facet 的 α + **25×25 interfacet 相关矩阵**，N=303 | ❌ 授权不允许转存（§6）；且 N 小 |
| Iran 结构效度元分析（2025） | 开放获取，k=8, N=6,489 | [PMC11904744](https://pmc.ncbi.nlm.nih.gov/articles/PMC11904744/) | **面向级** | Table 2/3/4 = **25 个 facet 量表**在 5 域上的**合并**载荷 + α | ❌ 层级不足 |
| 匈牙利版 PID-5（2022） | *PLOS ONE* | [10.1371/journal.pone.0266201](https://doi.org/10.1371/journal.pone.0266201) | **面向级** | Table 4 标题写 “item level CFA”，实为 facet 级拟合指数 + **平均** item-total（`MIT`），非逐题值 | ❌ 层级不足（标题有误导性） |
| 巴西版 PID-5（2022） | *Frontiers in Psychiatry* | [10.3389/fpsyt.2022.976831](https://doi.org/10.3389/fpsyt.2022.976831) | **面向级** | Table 5 = **分域**载荷 | ❌ 层级不足 |
| PID-5 一般因子（2024） | *CIPP* | [10.5114/cipp/163182](https://doi.org/10.5114/cipp/163182) | **面向级** | Table 3 = **25 个量表**在双因子模型上的标准化载荷 | ❌ 层级不足 |
| PID-5-SF DIF（2025） | *AOSIS* | [PMC12505424](https://pmc.ncbi.nlm.nih.gov/articles/PMC12505424/) | 面向项/题目但 SF 版 | IRT/DIF 分析，未公开逐题参数表 | ❌ |

**结论**：文献系统性地只公开发表 **facet 级**汇总。这不是检索不够，而是出版惯例 ——
220 行的载荷表在期刊正文放不下，补充材料也少见。已核验的**最大规模合并分析**
（k=8，N=6,489）仍然只到 25 个值。

### 2.2 §决定性命中：「题级原始作答」是公开的

| 来源 | 授权 | 内容 | 层级 |
|---|---|---|---|
| Zimmermann, Kerber, Kemper & Weweck（2026），*Population-Representative Norms for the PID-5…*，Zenodo [10.5281/zenodo.22280403](https://doi.org/10.5281/zenodo.22280403) | **CC-BY-4.0** | `pid5-norms_code-and-data.zip`（73.4 MB）内含两份**逐题**作答文件 | **题级（原始分）** |
| ↳ `data/donor_kerber2022.csv` | 同上 | **1,243 人 × 220 题**（0–3 计分），共 683 临床 + 560 非临床；含 Sample/Age/Gender；反向题未翻转；缺 794 格（0.29%） | **题级** |
| ↳ `data/SKIDComMet_data.csv` | 同上（原文来自 Krasniqi et al. 2024, [osf.io/ba37m](https://osf.io/ba37m)） | **1,228 人 × 220 题**（1–4 计分），配额样本；另含 SKID_1..SKID_102 访谈项；无缺失 | **题级** |
| `hitop` R 包 0.2.0（Girard），[文档](https://jmgirard.github.io/hitop/reference/ku_pid5sf.html) | GPL-3.0 | `ku_pid5sf`：**386 人 × 100 题**（PID-5-**SF**）真实的 Kansas 大学生作答；另含 `pid_norms` 常模表 | 题级，但仅 SF 100 题 |

**两条独立渠道互证**：OSF 节点 `ba37m` 上的 `SKIDComMet_data.csv` 与 Zenodo 副本
**逐字节相同**（双方 SHA-256 均为 `375d0640…7615`，835,906 B）。
不是「两个看起来像的文件」，是同一个文件在两个仓储里。

**这就是本轮的枢纽**：项目此前的假设是「PID-5 没有原始作答」（`tools/survey/fetch_pid5_norms.py`
的注释如此写）。**该假设不成立**。原始作答是公开的，于是题级参数不必「找」，可以「算」——
与大五人格用 Johnson (2005) 7325 份作答算 `correlation-network.json` 是同一条路。

### 2.3 §目标③「facet 间相关矩阵」

| 来源 | 层级 | 状态 |
|---|---|---|
| Bach et al. (2016) 补充材料 Table S1，N=303 | 面向级 25×25 | 已获取，**授权不允许转存**，未入档；仅作量级核对 |
| 从 §2.2 原始作答自行计算 | 面向级 25×25，N=2,471 | ✅ 已算出并落盘（`derived/pid5_facet_corr_demo.csv`） |

→ **不需要**依赖那份小样本、且不能转存的已发表矩阵。自己算的样本量大 8 倍，
且口径可与大五人格完全对齐。

### 2.4 §目标②「判读分界值」

| 来源 | 期刊/年 | DOI | 它给的 | 层级 | 可否采用 |
|---|---|---|---|---|---|
| Komasi, Rezaei, Hemmati, … Hopwood | *J Clin Psychol* 2024, 80(2):370–390 | [10.1002/jclp.23614](https://doi.org/10.1002/jclp.23614) | **波斯语 220 题版**：ROC + Youden 定 domain/facet 分界；摘要明示「0–3 计分下，任一分域或面向 **>1.5** 提示临床」（N=634 非临床 + 454 临床） | 面向级/域级 | ❌ **NOT OPENLY AVAILABLE**：Wiley 403，付费墙（按归档政策放弃，不绕过）。且分界依人群/患病率而定，摘要自陈「cut points are not universal」 |
| Facon, Dierckx, van Alphen, Surer & Rossi | *Frontiers in Psychology* 2026, 17:1734213 | [10.3389/fpsyg.2026.1734213](https://doi.org/10.3389/fpsyg.2026.1734213) | 按年龄/性别的 **T 分阈限**（≥60 轻度、≥65 临床），荷兰样本 N≈815 | 域级/面向级 | ⚠️ 已入档（CC-BY-4.0），但**针对 PID-5-BF+M（36 题）与 LPFS-BF 2.0，不是 220 题版** —— 见下方「不顶替」说明 |

**明确不顶替**：36 题 BF+M 的 T 分阈限**不能**当作 220 题版的分界值。两者题目集不同、
分数量纲不同，把 BF+M 的 ≥60/≥65 搬到 220 题上就是「看起来差不多」的顶替。

**项目现状**：`data/norms/pid-5.json` 已有 Kassel 代表性样本的**百分位 / T 分常模**，
所以 PID-5 **有百分位参考、无判读分界** —— 与任务书的猜测一致，如实记录。

---

## 3. 可行性验证：把「有」变成「核验过的有」

只说「原始数据存在」不够 —— 项目要求「界面上的每个数字都要能追到出处」（`PLAN.md` R1），
所以「能算」必须是跑过的。脚本：
`archive/norms/pid-5-psychometrics/derived/derive_pid5_item_params_demo.py`
（完整输出：`derived/demo-output.txt`；结果：`derived/pid5_item_params_demo.json`）。

### 3.1 数据可用性

| 文件 | 行 | 列 | 取值域 | 缺失格 |
|---|---|---|---|---|
| `donor_kerber2022.csv` | 1,243 | PID_1..PID_220 | 0–3 | 794（0.29%） |
| `SKIDComMet_data.csv` | 1,228 | PID_1..PID_220（+SKID_1..102） | 1–4 | 0 |
| 合并（平移对齐到 0–3） | **2,471** | 220 | 0–3 | 794 |

### 3.2 外部锚核对（证明算出来的量是对的）

用 `data/pid5-scoring-keys.json` 的 25 个面向计分键 + `data/pid5-reverse-keys.json`
的反向键，与已发表 facet 级统计量对照：

| 指标 | 本项目（N=2,471） | 已发表（N=303）* |
|---|---|---|
| 25 个面向 α 的均值 | **0.860** | 0.87 |
| 面向间相关的均值 | **0.322** | 0.33 |
| 逐面向 α 的 \|Δ\| 中位 / 最大 | **0.017 / 0.085** | — |
| 题与「自己面向」的相关是 25 个里最高的 | **218 / 220** | — |

\* 已发表值为 Bach et al. (2016) 补充材料 Table S1 的注记与表值；该文授权不允许转存，
故归档中无其副本，此处仅为引文级数值对照，不作为项目数据。

三项独立核对同时吻合，说明：题目编号 → 面向的映射正确、反向键处理正确、
算出的相关结构量级合理。

### 3.3 三份目标数据都能产出

| 目标 | 产出 | 规模 | 落盘 |
|---|---|---|---|
| 题级 × 面向相关 | `item_facet_corr` | **220 × 25 = 5,500** 个值（含「每题与自己面向」220 个） | `derived/pid5_item_facet_corr_demo.csv` |
| 面向间相关 | `facet_corr` | **25 × 25** | `derived/pid5_facet_corr_demo.csv` |
| 只答 k 题的一致性 | `partial_administration` | 25 个面向 × (n−1) 个 k，枚举全部 C(n,k) 子集 | `derived/pid5_item_params_demo.json` |

`r_min`（最差子集）示例 —— 这正是「推荐答题」要避免的情况：

| 面向 | 题数 | k=1 的 `r_min` / `r_mean` | k=n−1 的 `r_min` |
|---|---|---|---|
| Deceitfulness | 10 | **0.368** / 0.661 | 0.989 |
| Callousness | 14 | 0.426 / 0.619 | 0.988 |
| Rigid Perfectionism | 10 | 0.467 / 0.670 | 0.990 |
| … | | | |
| Submissiveness | 4 | 0.792 / 0.827 | 0.970 |
| Withdrawal | 10 | 0.712 / 0.771 | 0.993 |

**形态与大五人格一致**：单题最差情形差异很大（0.37–0.79），但 k=n−1 时全部 ≥0.96。
即「缺 1 题几乎无损，只答 1 题风险取决于选哪题」—— 与 IPIP 的 `key_metric = r_min`
设计意图完全对应。

---

## 4. 结论

1. **能拿到 220 题的题级参数 —— 来源是公开的原始作答，不是文献参数表。**
   按大五人格同一口径，三份数据（题级-面向相关、面向间相关、partial-administration）
   全部可计算，且已通过三项外部核对。**PID-5 可以拥有与大五人格同等的数据能力。**
2. **文献里没有题级参数**，这是出版惯例（facet 级汇总才放得下），不是检索失败。
3. **判读分界值：有，但不可直接采用** —— 220 题版的只有波斯语版且付费墙；
   开放获取的那篇针对 36 题 BF+M。项目现状维持「有百分位、无分界」。

---

## 5. 缺口与限制（如实）

| 缺口 | 说明 |
|---|---|
| **没有已发表的 220 题题级参数表** | 检索了 Europe PMC 5 组检索式 + 通用检索 + 数据仓；全部止于 facet 级 |
| **没有可采用的 220 题版判读分界值** | 见 §2.4；不用 BF+M 的阈值顶替 |
| 样本构成不是纯一般人群 | 2,471 人 = 临床 683 + 非临床 560 + 配额 1,228。临床样本会**抬高**题目间相关，与大五人格的社群样本口径不同；建数据时应分样本报告并说明 |
| N 比 IPIP 小（2,471 vs 7,325） | 题级相关的标准误约 0.02，尚可；但 `r_min` 是**极值序统计量**，在有限样本下会被**系统性低估**（选出最差子集本身有选择偏差）。建议下一步同时给出 `r_p05` 或做交叉验证，不要只用 `r_min` |
| 两样本计分域不同（0–3 / 1–4） | 相关与 α 对整体平移不变，所以本轮合并是安全的；但**均值/总分口径**必须先对齐再合并 |
| 本机无 R | 作者拟合缓存 `m1_measurement.rds` 等**未能读取**，故**不声称**其中含题级载荷。若下一步需要，可装 R 读取（记录已入档） |
| 未复核 depositor 自报 md5 | `MANIFEST.txt` 的 md5 已登记备查，本地只算了 SHA-256 |

---

## 6. 一条给下一步的发现：反向键是 16 题，不是 14 题

`data/pid5-reverse-keys.json` 逐字复现手册 Step 1 的清单（14 题）：
35, 58, 87, 90, 96, 97, 98, 131, 142, 155, 164, 177, 210, 215。

但手册的 **facet 表**另有 **7** 与 **30** 两道题标了 `R`，合计 **16 题**。三条独立证据：

| 证据 | 内容 |
|---|---|
| **题目文字**（`archive/scales/PID-5/items-extracted.json`） | 7 = “I avoid risky situations.”（Risk Taking 的反向表述）；30 = “I'm an energetic person.”（Anhedonia 的反向表述） |
| **数据** | 不翻转时，第 7 题与 Risk Taking 总分 **r = −0.685**，第 30 题与 Anhedonia **r = −0.519**；其余 14 题翻转后为 +0.37…+0.74 |
| **信度** | 按 16 题反向：Anhedonia α 0.842 → **0.907**、Risk Taking 0.838 → **0.900**（更贴近已发表的 0.88/0.88）；两面向 `r_min` 由负转正 |

→ **建数据时反向集应为 16 题（14 题清单 ∪ {7, 30}）**。这是本轮顺带发现的、
会直接影响下一步构建正确性的问题，详见 `derived/pid5_item_params_demo.json`
的 `disputed_items_diagnostic`。

---

## 7. 复现

```powershell
# 1. 重新抓取与检索（网络：Windows 直连）
python archive/norms/pid-5-psychometrics/derived/epmc_search.py `
       archive/norms/pid-5-psychometrics/derived/epmc

# 2. 从原始作答算出题级参数（本报告 §3 的全部数字）
python archive/norms/pid-5-psychometrics/derived/derive_pid5_item_params_demo.py

# 3. 重新生成 source-log.json（SHA-256 现算，不手抄）
python archive/norms/pid-5-psychometrics/derived/build_source_log.py
```

入档清单与逐件 SHA-256：`archive/norms/pid-5-psychometrics/source-log.json`。
目录说明与授权分层：`archive/norms/pid-5-psychometrics/README.md`。

---

## 8. 入档摘要

**入档位置**：`archive/norms/pid-5-psychometrics/`（54 件，81.6 MB）

| 类别 | 件数 | 代表件（SHA-256 前 12） |
|---|---|---|
| 采用（CC-BY-4.0） | 19 | `pid5-norms_code-and-data.zip` `56bc74ddae3a`；`donor_kerber2022.csv` `d7bf2e0659c4`；`SKIDComMet_data.csv` `375d06408b53`；`frontiers-fpsyg-2026-1734213.html` `6a8002dcfae0` |
| 旁证（仅判定参数层级） | 5 + 6 | OSF 节点元数据、Europe PMC 书目记录、6 份 OA 全文 |
| 本项目产物（算/检索，登记哈希） | 28 | `pid5_item_params_demo.json`、`pid5_item_facet_corr_demo.csv`、`derive_pid5_item_params_demo.py` |
| **未入档**（记录在案） | 2 | Bach et al. (2016) 补充材料（Cambridge/Elsevier 授权不允许转存，已获取未入档）；Komasi et al. (2024)（Wiley 付费墙，403，未绕过） |

> 按归档政策，受限来源只留「存在但不可用」的记录与授权原文，**不留副本、不留整页转录**。
> `source-log.json` 共登记 58 件，校验 `checked=58 bad=0`。

**互证记录**：`SKIDComMet_data.csv` 在 OSF 与 Zenodo 两侧 SHA-256 相同
（`375d06408b531d6bb0b7715f3160090d4e5dcb66bed364f0ab59871ec0fe7615`）。

---

## 9. 与本项目先前文档的差异（需 Lead 知悉）

| 文档 | 原表述 | 本轮实测 |
|---|---|---|
| `tools/survey/fetch_pid5_norms.py` 注释（路径为调研当时；该目录正被并发整理） | 「PID-5 没有原始作答，只能引用已发表的常模」 | **不成立**：Zenodo 记录内含两份 220 题逐题作答（N=2,471，CC-BY-4.0） |
| `archive/norms/pid-5/source-log.json` | `zenodo-norms` 记为 `ok: false`（HTTP 403） | 403 是 **`urllib` 缺 `Accept` / 非交互 shell 缺 `-UseBasicParsing`** 造成的，**不是 Zenodo 不可达**；本轮 Windows 直连取到全部文件 |
| `data/pid5-reverse-keys.json` | 14 题（Step 1 原文） | 应为 **16 题**（§6） |

以上三条都不需要本轮改动（本轮不动 `data/**`），但会影响下一步构建，故一并报上。
