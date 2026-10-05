# MMPI-2 指标文档的来源核对

**原则**　MMPI-2 **不收录题项**（UMN Press 明确禁止转载）；
本文件记录「评估指标」每条事实的来源与核对状态：`[已核实:URL]` / `[未核实]`。
**取得时间**　2026-10-04（Windows 直连；Pearson 官网本机 DNS 解析失败，故以 UMN Press 与学术来源为主）

---

## A. 授权与合法获取（逐字引用）

| 事实 | 状态 |
|---|---|
| UMN Press 原文：**"The Press does not allow for the reproduction of test items in dissertations/theses, journal articles, books or online."** | [已核实:https://www.upress.umn.edu/test-division/permissions-and-ordering/] |
| 题册与计分材料由 **Pearson Assessments** 独家发行（页面给出电话/传真/网址） | [已核实:同上] |
| 研究用途需提交 **Student / Non-Student Research Permission Form**；商业转载需填 **Permission to Reproduce Test Materials Form** | [已核实:同上] |
| 使用者资质要求（Pearson "Level C"） | [未核实] — Pearson 官网本机 DNS 解析失败（`getaddrinfo ENOTFOUND`），未能读取其资质页；页面链接见 UMN Press 页（How to order / qualifications） |

> 因此本项目的处理是：**文档里一个字都不给题项**，`data/instruments/mmpi-2.json` **不存在**；
> 只保留「合法获取途径 + 用户自行取得后的本地导入步骤」。

---

## B. 身份与出版信息

| 事实 | 状态 |
|---|---|
| 1989 年由 University of Minnesota Press 出版；2001 年修订 | [已核实:https://www.upress.umn.edu/test-division/mmpi-2/] |
| 2003 年加入 Restructured Clinical（RC）量表；2006 年加入 Symptom Validity（FBS）量表；2009 年出单行本 | [已核实:同上] |
| 用途：临床评估辅助；也用于高风险公共安全岗位选拔与刑事/民事司法鉴定 | [已核实:同上] |
| 567 道题；原始 MMPI 566 题中 16 题重复；MMPI-2 新增 107 题、剔除 90 题 | [已核实:https://media.wiley.com/product_data/excerpt/34/04713453/0471345334.pdf] |
| 作答方式 True/False | [未核实] — 该 PDF 未直接写作答格式；来自通行教科书描述，**本轮未取得可核对页**，故文档只在与量表包无关处不引用它。 |

---

## C. 量表结构

| 事实 | 状态 |
|---|---|
| 效度量表：原版 L / F / K /「未答」；MMPI-2 新增 **FB、VRIN、TRIN**；2001 修订版再加 **Fp、S** | [已核实:https://etd.adm.unipi.it/theses/available/etd-06262017-111100/unrestricted/Bozza_tesi2.pdf（2.3.1 节）] |
| 临床量表 10 个：Hs 疑病、D 抑郁、Hy 癔症、Pd 精神病态偏差、Mf 男性化–女性化、Pa 偏执、Pt 精神衰弱、Sc 精神分裂、Ma 轻躁狂、Si 社会内向 | [已核实:同上（逐量表章节）；量表中译名为本项目对照通用译法] |
| RC 量表：**RCd（Demoralization）+ 8 个与临床量表对应的 RC 量表** | [已核实:同上（RCd 与 8 个临床对应量表）；**具体代号表未逐一核实**] |
| 内容量表 **15 个**（取代原 MMPI 的 13 个 Wiggins 内容量表） | [已核实:Butcher 节选 + Bozza 2.x] |
| Harris–Lingoes 子量表：8 个基本量表中 6 个有（Scale 4 的子量表不再含量表外条目） | [已核实:Butcher 节选] |
| Koss–Butcher / Lachar–Wrobel 关键条目清单保留并扩充（抑郁/自杀、酒精滥用两组） | [已核实:Butcher 节选] |
| **PSY-5**（人格心理病理五维） | [未核实] — 本轮检索未取得可核对来源，**故不列代号** |
| 「MMPI-2 共 131 个量表（VRIN → TRT2）」 | [未核实] — 该数字来自知乎教学文章的转述（`research/ihs-assessment-plan.md`），本轮**未取得**可核对的官方量表清单；故文档不采用该数字 |

---

## D. 常模与 T 分体系

| 事实 | 状态 |
|---|---|
| 重新标准化样本 **2,600**（女 1,462 / 男 1,138），从约 2,900 人中筛出；剔除约 300 人（人口学缺失、MMPI-AX 漏答 > 39 题、F 或实验量表分数过分偏离） | [已核实:https://media.wiley.com/product_data/excerpt/34/04713453/0471345334.pdf] |
| 样本按当时人口普查比例在年龄/教育/婚姻/地域等维度匹配；Butcher 同时指出「与普查值相符不能保证对所有子群体都是可靠标准」 | [已核实:同上] |
| 临床显著性边界由 MMPI 的 **T ≥ 70** 下调为 MMPI-2 的 **T ≥ 65** | [已核实:https://etd.adm.unipi.it/theses/available/etd-06262017-111100/unrestricted/Bozza_tesi2.pdf（2.2 节」è sceso da T ≥ 70 a T ≥ 65」）] |
| MMPI-2 用 **uniform T 分**（非线性 T），以获得各量表可比的百分位分布 | [已核实:同上（转述）+ Tellegen & Ben-Porath (1992) *Psychological Assessment* 4:145–155 书目] |
| T 分的定义式 T = 50 + 10z | [未核实] — 属 T 分尺度的定义（非 MMPI-2 特有），文档只作定义性陈述，不引具体样本页 |
| 逐分量表的 raw→T 对照表 | [未核实/拿不到] — 在购买的手册与计分软件里；**本项目不复制、也不自行换算** |

---

## E. 信度 / 效度证据

| 事实 | 状态 |
|---|---|
| 内部一致性（基本量表）：**0.5–0.96**，均值区间 .60–.90（Graham, 2000，转引） | [已核实:https://etd.adm.unipi.it/theses/available/etd-06262017-111100/unrestricted/Bozza_tesi2.pdf] |
| 重测相关：临床量表 **.49–.73**、补充量表 **.30–.80**、内容量表 **.65–.77**、Harris–Lingoes **.51–.74** | [已核实:同上] |
| Matz et al. (1992)：α 区间 **.39–.91**（中位 .62） | [已核实:同上] |
| Hunsley et al. (1988)：α **.71–.84**、重测 **.63–.86** —— ⚠️ 研究对象是 **MMPI 而非 MMPI-2** | [已核实:同上（文档里已明确标注版本差异）] |
| 常模代表性批评（贫困内城、原住民、流动人口等群体可能系统性偏离） | [已核实:Butcher 节选] |

> **本项目的立场**：二手汇总（转引自学位论文的文献综述）**不能替代**技术手册的逐量表信度表；
> 文档因此把区间写清楚、标明出处，并明确「逐量表 α 表未取得」。

---

## F. 来源索引

1. University of Minnesota Press · MMPI-2 产品页 — <https://www.upress.umn.edu/test-division/mmpi-2/>
2. University of Minnesota Press · Permissions and Ordering（授权原文）— <https://www.upress.umn.edu/test-division/permissions-and-ordering/>
3. Butcher, J. N. *A Beginner's Guide to the MMPI-2*（Wiley 节选 PDF，含 567 题与 2,600 样本构成）— <https://media.wiley.com/product_data/excerpt/34/04713453/0471345334.pdf>
4. Bozza, F. (2017). 学位论文（Università di Pisa；含量表清单、T≥65、信度区间汇总）— <https://etd.adm.unipi.it/theses/available/etd-06262017-111100/unrestricted/Bozza_tesi2.pdf>
5. Tellegen, A., & Ben-Porath, Y. S. (1992). The new uniform T scores for the MMPI-2: rationale, derivation, and appraisal. *Psychological Assessment*, 4, 145–155.
6. Graham, J. R. *MMPI-2: Assessing Personality and Psychopathology* (5th ed.). Oxford University Press. ISBN 978-0-19-537892-4 —— 由 `task-11` 的调研指出；**本轮未取得该书正文**，故其数值只以「转引自 Bozza (2017)」的形式引用。

> 未采用的来源：任何提供 MMPI-2 题面的网页/仓库。项目政策是**不查、不用、不转载**这类来源
> （错误内容风险 + 授权风险）。
