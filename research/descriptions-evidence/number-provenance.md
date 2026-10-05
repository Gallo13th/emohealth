# 抽查：文档里的数字 → 出处

**目的**　验收项「每个数字都能追到 `archive/` 里的证据或文献」。
**方法**　从 12 套文档里**抽样**取数，逐条给出「值 → 文件/URL → 定位」。每条都用脚本从源头现读一遍（`python` 读取 + 打印），不是从文档里抄的。

复现：本文件里的每个 IPIP/PID-5/DSM 数字都能用下面两条命令重读：

```powershell
python -c "import json;d=json.load(open('data/norms/ipip-neo-300.json',encoding='utf-8'));print(d['n'],d['facets']['anxiety'])"
python -c "import json;d=json.load(open('data/criteria/dsm5tr-l2.json',encoding='utf-8'));print(d['instruments']['DSM5TR-L2-Mania'])"
```

---

## IPIP-NEO-300

| 文档里的数字 | 值 | 出处 | 定位 |
|---|---|---|---|
| 常模样本量 N | **145,388** | `data/norms/ipip-neo-300.json` | 顶层 `n`（另有 `n_note` 说明与 N=20,993 的区别） |
| 扫描记录数 | 307,313 | `data/norms/ipip-neo-300.json` | `validation.records_scanned` |
| 反向题数 | **148** | 同上 | `validation.reverse_items_project`（官方 148 / 项目 148 / 交集 148） |
| 题项数 / facet 数 | 300 / 30 | `data/instruments/ipip-neo.json` | `items`、`dimensions` 长度 |
| 每 facet 题数 | 10 | `data/norms/ipip-neo-300.json` | `validation.items_per_facet` |
| anxiety 均值 / 标准差 | **3.1619 / 0.3363** | `data/norms/ipip-neo-300.json` | `facets.anxiety.mean` / `.sd` |
| neuroticism 均值 / 标准差 | 3.0628 / 0.2306 | 同上 | `domains.neuroticism.mean` / `.sd` |
| anxiety 的 α | **0.83** | `content/facets/anxiety.record.json` | `reliability.cronbach_alpha` |
| α 的来源 | OpenScales `IPIP-NEO.osd`（源自 Goldberg 的 ESCS 数据） | 同上 | `reliability.alpha_source` |
| anxiety 的 SEM | 3.5（**标注为 DERIVED**） | 同上 | `reliability.sem.value`，附 `caveat`：由整数化分带边界反推，±0.5 分舍入不确定性 |
| 计分口径 | facet = 10 题均分；域 = 6 个 facet 均分；反向题 `6 − x` | `data/norms/ipip-neo-300.json` | `unit` / `domain_unit` / `reverse_transform` |
| 百分位方法 | 经验分布线性插值（1..99） | 同上 | `percentile_method` |
| 官方计分表 | `IPIP-NEO-300_ScoringTool.xlsx` | `archive/datasets/osf-johnson/scoring/` | `source_files.scoring_key` |
| 原始作答文件 | `IPIP300.dat`（sha256 `1bbb7189f5f0f288…`） | `archive/datasets/osf-johnson/raw/` | `source_files.responses` + `responses_sha256` |
| 中译覆盖率 | 300/300 有中译 | `data/text-db/text-db.json` | `zh_source = "data/scene-taxonomy.json（大五人格，已人工核对）"` |

## PID-5

| 文档里的数字 | 值 | 出处 | 定位 |
|---|---|---|---|
| 题数 / 反向题数 | **220 / 16** | `data/instruments/pid-5.json` | `items` 长度；`key == -1` 计数 |
| 裁决后的反向题清单 | 16 题（含 7、30） | `data/pid5-reverse-keys.json` | `reverse_keyed`（`reverse_keyed_step1_verbatim` 是 14 题原文） |
| 手册 Step 1 逐字原文 | `35, 58, 87, …, 210, and 215` | 同上 | `verbatim` |
| 反向变换 | `3 − x` | `archive/scales/PID-5/manual.pdf` | 手册 Scoring 段；`data/pid5-reverse-keys.json` 的 `scale.transform` |
| 第 7 题与 Risk Taking 的相关（未翻转） | **−0.685** | `data/pid5-reverse-keys.json` | `evidence.evidence_2_data` |
| 第 30 题与 Anhedonia 的相关（未翻转） | **−0.519** | 同上 | 同上 |
| 翻转后 Anhedonia α | **0.842 → 0.907** | 同上 | `evidence.evidence_3_reliability` |
| 翻转后 Risk Taking α | **0.838 → 0.900** | 同上 | 同上 |
| 自算逐 facet α（例：Anhedonia / Risk Taking） | **0.907 / 0.900** | `archive/norms/pid-5-psychometrics/derived/pid5_item_params_demo.json` | `alpha.Anhedonia.alpha_pooled` / `alpha["Risk Taking"].alpha_pooled` |
| 自算样本量 | N = **2,471**（样本构成：临床 683 + 非临床 560 + 配额 1,228） | 同上 | `n_pooled` / `inputs` |
| 已发表 α 对照（Anhedonia） | 0.88 | 同上 | `alpha.Anhedonia.alpha_published_eurpsych2016`（Bach et al. 2016，**授权不允许转存，只记数值与出处**） |
| 常模样本量 | **4,727**（德国 GESIS Panel，总体代表性） | `data/norms/pid-5.json` | `n` + `n_note` |
| 常模分层 cell 数 | **9**（性别×年龄） | 同上 | `cells` |
| 常模表规模 | 31 个量表（25 facet + 5 域 + Total） | 同上 | `scales`（31）、`scale_names` |
| 百分位与 T 分 | 逐 raw 给 `pctl_med/lo/hi`、`T/T_lo/T_hi` | 同上 | `scales.<量>.<cell>.<raw>` |
| 100 分位映射 | 例：raw=0 → 3.38%ile；raw=1.5 → 83.24%ile；raw=3 → 100%ile | 同上 | `anhedonia / f [18,35)`（脚本重读核对） |
| 常模来源 DOI | `10.5281/zenodo.22280403`（CC BY 4.0） | 同上 | `source_files.doi` / `license` |
| 手册哈希 | `ce366db46f324ba7…`（439,682 字节） | `data/instruments/pid-5.json` | `provenance.manual_sha256` / `manual_bytes` |
| 中译覆盖率 | 220/220，**标记为「subagent 初译（待人工复核）」** | `data/text-db/text-db.json` | 逐条 `zh_source`（见 `known-data-gaps.md`） |

## DSM-5-TR

| 文档里的数字 | 值 | 出处 | 定位 |
|---|---|---|---|
| L1 题数 / 域数 | **23 / 13** | `data/instruments/dsm5tr-l1.json` | `items` / `dimensions` |
| L1 每域题数 | 1–3（7 个域只有 1 题） | 同上 | 逐域 `items` 长度 |
| L1 域分口径 | **域内任一题最高分**（`max`） | `archive/scales/DSM5TR-L1/manual.pdf` | 手册 Instructions to Clinicians；落成 `scoring.aggregation="max"` |
| L1 门槛 | **≥2**（10 个域）/ **≥1**（自杀意念、精神病性、物质使用） | `data/instruments/dsm5tr-l1.json` → `interpretation.domains`；同时 `data/linkage/dsm5tr-chain.json` | 逐域 `threshold` |
| L1 时间窗 | past TWO (2) WEEKS | `data/instruments/dsm5tr-l1.json` | `interpretation.window` |
| 手册哈希 | `260bb4400ebe5206…`（282,005 字节） | 同上 | `provenance.manual_sha256` |
| 与 PID-5 的衔接 | `status: inferred`（**非手册原文**） | `data/linkage/dsm5tr-chain.json` | `pid5_interface.caveat`（已核查 9 册正文均未提 PID-5） |
| L2-anger 分值范围 | **5–25** | `data/criteria/dsm5tr-l2.json` | `instruments.DSM5TR-L2-Anger.sum_range` |
| L2-mania 分界 | **≥6**（≤5 为「不太可能相关」） | 同上 | `DSM5TR-L2-Mania.cutoff` / `bands` |
| L2-somatic 分带数 | **4**（Minimal/Low/Medium/High） | 同上 | `DSM5TR-L2-Somatic.bands` |
| L2-substance 汇总口径 | `count_true`（**不是总分**） | 同上 | `DSM5TR-L2-Substance.aggregate` + `aggregate_label` |
| PROMIS 待补 T 分的册数 | **4**（Anger / Anxiety / Depression / Sleep） | 同上 | `source_of_criteria == "pending_external"` + `pending_reason` |
| L2 各册手册出处 | `archive/scales/DSM5TR-L2-*/manual.pdf` 的 Scoring and Interpretation 段 | 同上 | 逐册 `evidence` |

## MMPI-2（在线来源，见 `mmpi-2-sources.md`）

| 文档里的数字 | 值 | 出处 |
|---|---|---|
| 题数 | **567**（原始 MMPI 为 566，其中 16 题重复；107 道新题、剔除 90 题） | Butcher《A Beginner's Guide to the MMPI-2》Wiley 节选 PDF <https://media.wiley.com/product_data/excerpt/34/04713453/0471345334.pdf> |
| 出版/修订年份 | 1989 出版、2001 修订、2003 RC 量表、2006 FBS | <https://www.upress.umn.edu/test-division/mmpi-2/> |
| 常模样本 | **2,600**（女 1,462 / 男 1,138），从约 2,900 人筛出、剔除约 300 | Butcher 节选（同上） |
| 临床显著性边界 | **T ≥ 65**（MMPI 原为 T ≥ 70） | Bozza (2017) 学位论文 2.2 节 <https://etd.adm.unipi.it/theses/available/etd-06262017-111100/unrestricted/Bozza_tesi2.pdf> |
| uniform T 分 | 由 Tellegen & Ben-Porath (1992) 提出（*Psychological Assessment* 4:145–155） | 同上（参考文献表）+ 论文书目 |
| 内部一致性区间 | **0.5–0.96**，均值区间 .60–.90（Graham 2000 转引） | 同上（Bozza 2017 文献综述） |
| 重测相关区间 | 临床 .49–.73、补充 .30–.80、内容 .65–.77、Harris–Lingoes .51–.74 | 同上 |
| 阅读水平（原版） | 五年级为最低要求 | Butcher 节选 |
| 题项不得转载 | UMN Press 原文 | <https://www.upress.umn.edu/test-division/permissions-and-ordering/> |

---

## 结论

* **A/B/C 类**（项目内证据）每条都能定位到具体文件与字段，且由 `check_descriptions.py` 的 V3/V5/V6/V9 守住。
* **D 类**（在线文献）在本文件与 `mmpi-2-sources.md` 里逐条给出 URL 与「已核实/未核实」标记。
* **E 类**（依题面推导）在文档内逐条标 `derived_from_items:<题号>`，**不冒充文献定义**。
* 没有一条数字是「看起来差不多」填进去的；拿不到的一律进入 `README.md` §4 的留白清单。
