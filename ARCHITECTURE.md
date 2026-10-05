# 架构契约：三层解耦（调研 / 数据 / 前端）

**制定**　2026-10-03（2026-10-04 清理过时表述）
**规则与计划**　[`PLAN.md`](PLAN.md)（R1–R4；本文档只讲技术分层）
**配套**　`tools/README.md`（脚本索引）、`CLEANUP-PLAN.md`（工具目录清理的历史口径）
**守卫**　`tools/check_architecture.py`（三条契约的可执行形式）
**基座**　`tools/_root.py`（统一项目根定位）

---

## 0. 这份文档解决什么

这个项目最初只做一套量表（大五人格 / IPIP-NEO-300），现在承载 **342 套量表**。
三件事在同一个 `tools/` 平铺目录里混着做，导致任何一件改动都会牵动另外两件：

| 事项 | 例子 | 被牵动的层 |
|---|---|---|
| **文献调研** | 抓 APA 手册、核对授权、提取题项 | 改题项 → 数据包变 → 界面要重新打包 |
| **统计表格再组织** | 算常模、相关性、分级解锁 | 改算法 → 前端数据包变 → 界面回归全跑 |
| **网页前端交互设计** | 天赋树、分页作答、导出 | 改交互 → 常常回去直接读 `archive/` 找数据 |

解耦不是「把文件分开放」——**分完目录而契约不成立，耦合只是从路径变成了隐性依赖**。
所以本文给出三层的输入/输出契约，以及三条**可被机器检查**的硬契约。

---

## 1. 三层与两个支撑

```
① 调研层
   research/            调研报告（人读）
   tools/survey/        检索、获取、登记、互证、归档
   契约：只读网络与 archive/；可写 research/ 与 archive/；不得写 data/

② 数据层
   archive/             证据链。**原始证据只读、永不改**；其中的派生缓存/派生数据有缺陷时
                        按 PLAN.md R5 + R3 记录→溯源→**完整修复**（修必留痕）
   data/                结构化产物，按来源分子目录
   tools/build/         从 archive 提取、清洗、组织成 data/**
   tools/analyze/       统计与表格再组织（相关性、分级、常模）
   契约：只读 archive/ 与 data/；可写 data/**；不得读 ui/

③ 前端层
   ui/                  界面与生成包
   tools/ui/            前端生成、预览、截图
   契约：只读 data/** 与 ui/**；不得读 archive/

支撑（跨层共用，位置固定）
   engine/              运行时库（schema / scoring），被 ②③ 共用
   tools/_root.py       统一的项目根定位
   tools/               共享库平铺（pdftext、build_scales、item_coding …）
   tools/check/ + tools/check_architecture.py   守卫与测试（只读，不写产物）
```

**可读 / 可写矩阵**（`─` = 不涉及，✅ = 允许，❌ = 契约禁止）：

| 层 | 读网络 | 读 `archive/` | 读 `data/` | 读 `ui/` | 写 `archive/` | 写 `data/` | 写 `research/` | 写 `ui/` |
|---|---|---|---|---|---|---|---|---|
| ① 调研 `tools/survey/` | ✅ | ✅ | ✅（只读参考） | ─ | ✅ | ❌ **C2** | ✅ | ❌ |
| ② 数据 `tools/build/` `tools/analyze/` | ❌ | ✅ | ✅ | ❌ **C3** | ❌ | ✅ | ✅（报告） | ❌（前端包由 `tools/ui/pack_ui_data.py` 打包） |
| ③ 前端 `tools/ui/` `ui/` | ❌ | ❌ **C1** | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ |

**归档口径（与 `PLAN.md` R5 同一条，架构侧的表述）**：`archive/**` 与 `data/**` 都由**两层**构成——
**原始证据**（PDF、官方页面快照、下载件）与**派生层**（提取物、结构化产物、生成物）。
**原始证据只读、永不改**（`tools/check/verify_archive.py` 逐字节校验）；**派生层可修**，
但**修必留痕**：缺陷按 R3 走「记录 → 溯源 → 完整修复」，并保留更正前后的对应关系。
因此上表「写 `archive/`」这一列只指**新增原始件**（入档），**不是**改写已入档原件的字节
——改写原件在两层都禁止（`tools/survey/archive_*.py` 遇到哈希不一致时报错而不覆盖）。

**`archive/` 不入版本控制（2026-10-05 项目所有者决定，见 `.gitignore` 的完整理由）**：
2041 文件 / 755,865,089 B 的原始证据**有意留在 git 之外**——体量会让 `.git` 多出约 490 MB、
任何远端推送都会撞上平台上限，且 archive 只增不改（每份新手册 PDF 都会在历史里永久多存一份）。
它的完整性由**更强的机制**守着：`tools/check/verify_archive.py` 的逐字节校验（每轮必跑第 6 条）。

⚠️ **代价**：git 对 `archive/` 只能**检出被改**，**不能还原**（从未存过其内容）。
因此 archive 需要**独立的物理备份**（另一块盘 / 快照 / 私有归档）——**这件事目前尚未做**。
其中 `archive/ipip/data/OpenScales` 是第三方 git 克隆（`https://github.com/stmueller/OpenScales.git`，
1599 文件 / 53.9 MB），是 archive 里唯一可完全复现的部分。

① 数据层历史上会直接产出 `ui/*.js` 生成包（`adaptive-data.js`、`catalog.js`、
`tier-data.js`、`tree-layouts/**`、`unlock-data.js`）。**已收敛**（2026-10-03，T-CONVERGE-A）：
数据层只写 `data/**`，前端包由前端层的 `tools/ui/pack_ui_data.py` 打包，
守卫 C3 的「写入 ui/」计数已归零。改法、留痕与验收依据见 §5.1。

---

## 2. 三条硬契约

### C1　`tools/ui/**` 与 `ui/**` 不得直接读 `archive/`

**为什么**：`archive/` 是 639 MB 的原始证据链（PDF、98 MB 定宽数据集）。前端若直接读它，
就同时绑定了（a）本地文件系统布局、（b）原始格式、（c）解析逻辑。结果是 `archive/`
里换一个文件名，界面就白屏；而界面又必须能 `file://` 离线打开，根本读不到这些大文件。
**正确路径**：`archive/` → `tools/build|analyze` → `data/**` → 前端数据包 → `ui/`。

**检查什么**：`tools/ui/**`、`ui/**` 下的非生成源码里，出现 `archive/` 路径字面量即违例。
生成产物豁免（其中的 `archive/...` 是写入的溯源证据字符串，不是前端在读档案）：
`ui/instruments/**`、`ui/tree-layouts/**`、`ui/catalog.js`、`ui/instruments.js`。

**怎么改**：把需要的数字在数据层算好、写进 `data/**`，前端只消费数据包。

### C2　`tools/survey/**` 不得写 `data/**`

**为什么**：`data/` 是**已核对过的结构化产物**（342 个量表包、常模、判读口径）。
调研阶段的东西——原始抓取、候选清单、待核对的转换表——性质是「线索」，不是「结论」。
一旦调研脚本直接把线索写进 `data/`，下游会把它当作已核对数据使用，
而「每个数字都要可溯源到内容正确的来源」（`PLAN.md` R1）就断了。

**检查什么**：`tools/survey/**` 下出现对 `data/**` 的**写**操作即违例
（`json.dump`、`open(...,"w")`、`shutil.move`、`os.makedirs` …，含被赋值为 `data/` 路径的变量）。

**怎么改**：写 `research/**`（人读报告、候选清单）或 `archive/**`（原始件 + 溯源）；
需要进入 `data/` 时，由数据层的 `tools/build/` 脚本从 `archive/` 重新产出一遍。

### C3　`tools/build/**` 与 `tools/analyze/**` 不得读 `ui/**`

**为什么**：数据层若依赖前端产物，就出现了反向依赖：改界面 → 数据层的输入变 →
分析结果变。这天花板很低，且很难察觉（脚本仍然跑得通，只是算的东西不一样了）。

**检查什么**：`tools/build/**`、`tools/analyze/**` 下出现对 `ui/**` 的**读**操作即违例
（`open()`、`json.load`、`glob`、`os.walk`、`readFileSync`、`require(` …）。
两种非违例情形会被区分对待：

* **写** `ui/`（例如生成 `ui/net-layout.js`）→ 不计违例，但在输出里计数；
* **纯路径常量定义**（`UI = os.path.join(ROOT, "ui")`）→ 不计违例，其后续读取仍会被抓。

**怎么改**：把需要的输入先落成 `data/**`（由 `tools/build/` 生成），
`tools/analyze/` 只读 `data/**` 与 `archive/**`。

---

## 3. 每层：怎么跑、产物在哪

### ① 调研层

```powershell
python tools/survey/archive_apa_manuals.py --verify    # 抓取 + 溯源（迁移后路径）
python tools/survey_tools_layout.py                    # 现状测绘：脚本职责分类
python tools/survey_refs.py                            # 引用测量：哪些脚本可安全移动
```

* **输入**：网络（官方站点）、`archive/`（已归档原始件）
* **产物**：`research/*.md`、`research/**/*.json`、`archive/**` 新增原始件 + `source.json`/manifest
* **不产出**：`data/**`（C2）、`ui/**`

### ② 数据层

```powershell
python tools/build_scales.py --all                      # OpenScales .osd → data/instruments/*.json（共享库，平铺）
python tools/build/build_manifest.py --check            # MANIFEST 逐字节校验
python tools/analyze/analyze_partial_administration.py  # 部分施测精度 → data/partial-administration.json
```

* **输入**：`archive/**`（原始 PDF / 数据集 / `.osd`）、`data/**`（上游结构化产物）、`content/**`、`engine/**`
* **产物**：`data/**`（量表包、常模、相关性、分级、判读口径）、`MANIFEST.sha256`、`MANIFEST.txt`
* **不读**：`ui/**`（C3）

### ③ 前端层

```powershell
python tools/ui/pack_ui_data.py                         # data/** → ui/*.js（window.* 赋值脚本）
python tools/ui/build_ui_instruments.py                 # 生成 ui/instruments/<code>.js（按需加载）
node tools/ui/serve_local.js                            # 本地起服务预览（file:// 亦可直开）
node tools/ui/shoot_ui.js                               # CDP 截图（开发用）
```

* **输入**：`data/**`（经 `pack_ui_data.py` 落到 `ui/**`）、`content/**`
* **产物**：`ui/instruments/**`、`ui/tree-layouts/**`、`ui/*.js` 生成包、截图
* **不读**：`archive/**`（C1）

### 支撑层

* `engine/`：schema 与计分库，被 ②③ 共用，**位置固定不动**。
* `tools/` 平铺：`pdftext.py`、`build_scales.py`、`item_coding.py` 等共享库
  （判据：被 ≥3 个文件引用，或本身就是库）；外加基座 `_root.py` / `_root.js` 与守卫。
* `tools/check_architecture.py`：本文三条契约的守卫，只读不写。
* `tools/cleanup_manifest.json`：T2–T5 的迁移记录（`{old, new, sha256}`），回滚依据。

---

## 4. 统一根定位：`tools/_root.py`（Python）与 `tools/_root.js`（JS）

**问题**：迁移前脚本普遍用「上退两层」推导项目根：

```python
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # tools/xxx.py
```

文件一旦移进 `tools/survey/xxx.py`，上退两层就落到 `tools/`，**全仓路径静默错位**。
本仓 159 个脚本里被外部引用的有 64 个，逐个改成「数层数」既易错、也经不起以后再移动。

**做法**：向上找含 `MANIFEST.sha256` 的目录，找不到就抛错，不猜。两侧同一判据：

```python
# Python：tools/<cat>/xxx.py
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # tools/
from _root import find_root
ROOT = find_root()                       # 无论脚本在哪一层都正确
```

```javascript
// JS：tools/<cat>/xxx.js —— 原先 17 个脚本写 path.join(__dirname, '..')
const ROOT = require('../_root.js').findRoot(__dirname);
```

Python 侧另有两种路径注入，对应本仓现存的两种导入写法，按需调用（不是每个脚本都要）：

```python
from _root import add_tools_to_path, add_root_to_path
add_tools_to_path("survey")              # import pdftext（平铺共享库）需要 tools/ 在 path 上
add_root_to_path()                       # from tools.item_coding import ... 需要根在 path 上
```

| 写法 | 需要谁在 `sys.path` | 现有例子 |
|---|---|---|
| `import pdftext` | `tools/` | `build_l1_items.py`、`archive_dsm5tr_measures.py` |
| `from tools.item_coding import …` | 项目根 | `analyze_tiered_unlock.py`、`build_adaptive_data.py`、`compare_linear_vs_tree.py` |
| `from engine.scoring import …` | 项目根 | `build_l1_instrument.py`、`build_l2_instruments.py` |
| `from test_pid5_instrument import …` | 脚本自身目录（Python 自动加） | `test_l1_instrument.py`、`test_all_instruments.py` |

> 迁移时这四种写法各按各自需要调整；同目录的兄弟模块导入（`from test_x import …`）由
> Python 自动把**脚本所在目录**放进 `sys.path` 解决，不需要额外注入。

自检：

```powershell
python tools/_root.py
node   tools/_root.js
```

断言根下存在 `MANIFEST.sha256`、`ui/index.html`、`data/instruments`。
（`MANIFEST.sha256` 被选作标记，是因为它由本项目自己生成、在仓库里唯一。）

---

## 5. 守卫：怎么跑、判定口径、已知局限

```powershell
python tools/check_architecture.py        # 三条契约各一行 ✅/❌；违例列出 文件:行号
python tools/check_architecture.py -v     # 附每个目录实际扫描的文件
```

* 全部通过 → 退出码 **0**；任一违例 → 退出码 **1**。
* **目录未建立时视为通过**并打印「目录未建立，跳过」——迁移前它让守卫得以先进 CI；
  迁移后目录都在，输出会变成真实扫描行（见 §6）。

**判定口径**（避免误解）：

| 口径 | 说明 |
|---|---|
| 扫描扩展名 | `.py .js .mjs .cjs .ts .html .css .sh .json`；**`.md` 不计**（文档提及路径不构成依赖） |
| 注释与 docstring | **整行注释与 Python docstring 不计违例**（不产生读写）；行尾注释仍在扫描范围内（保守） |
| 路径识别 | **必须锚定顶层目录**：`data/x.json`、`f"{ROOT}/data/x"`、`os.path.join(ROOT, "data", …)`、`Path(ROOT) / "data"`、`os.makedirs("data")`，以及被赋值为这些字面量的变量。`os.path.join(ROOT, "archive", "ipip", "data", …)` 里的 `"data"` **不算**（那只是 `archive/` 下的目录名） |
| 变量跟踪 | 跟踪同文件内**被赋值为路径表达式**的变量，**任何长度**（含单字母 `p`、`d`）；按作用域解析（LEGB），重绑 / `for` 目标 / 参数遮蔽后失效。`db = json.load(open(<路径>))` 这类「**值是内容**」的赋值**不跟**（否则后续 `db[...]` 会被误判成路径依赖）。非 Python 退化为同行赋值启发式 |
| 未判定 | 三类**单独报出、不判违例也不放过**：①跨行拼接被拆成单独成行的路径段（`+ "ui"`）②路径藏进容器（set/list/dict）后取出使用 ③Python 无法解析（退化 + 明说判定失效）。输出 `未判定 N 处`；**`未判定 0 处` 才是收敛完成** |
| 读写判定 | 按同行的调用模式：`json.dump` / `open(...,"w")` / `writeFileSync` / `shutil.move` … 为写；`open()` / `json.load` / `glob` / `os.walk` / `readFileSync` / `require(` … 为读 |
| 日志行 | **不计**（`print` / `console.log` …，含跨行续行）；但 `print(open(p).read())` 这类真的读了文件仍判违例 |
| 路径标签 | **不计**：`e["zh_source"] = "ui/emohealth-data.js（已核对）"` 是把路径当字符串记下，不是读 |
| C3 的保守分支 | 既非读也非写、也非上述豁免的引用，**按依赖计**（例如把 `ui/` 塞进 `sys.path`） |

**已知局限**（守卫不是万能的，以下情形**不在覆盖范围内**）：

1. **跨行拼接的路径**：`p = os.path.join(ROOT, "ui")` / `q = p + "/x.js"` / 下一行 `open(q)`
   ——只认字面量与直接绑定的常量，多级拼接不追。
2. **运行时构造的路径**：`getattr`、配置文件、环境变量拼出的路径。
3. **动态语言特性**：`eval`、`importlib`、字符串拼接的模块名。
4. **行尾注释里的路径**会被计入（保守，可能产生需要改注释的误报）。
5. C1 的生成产物豁免是**白名单**：新增生成文件需同步加入 `GENERATED_ARTIFACTS`，
   判据是「由 `tools/**` 的脚本产出，且头部有自动生成标记」。
6. ~~**单字母变量绑定的路径**（实测踩到）：`p = os.path.join(ROOT, "ui", "x.js")` 之后
   `open(p)` —— `p` 太短，守卫不跟，于是**真实违例漏检**。~~
   **✅ 已修复**（2026-10-03，T-CONVERGE-B）：守卫改为跟踪**任意长度**的路径绑定变量名
   （AST + 作用域感知 LEGB），`tools/build/build_text_db.py` 也不再读 ui 包。
   原漏检形态现在会命中，并由 `tools/check/verify_architecture_guard.py` 逐例兜底
   （对照行明示「旧口径不跟踪 `p` / 新守卫命中 1 条」）。
7. **跨文件传递**（现有）：常量在 `a.py` 定义、`b.py` 里使用 —— 守卫按文件扫描，
   **不追跨文件**。路径若被这样传递，仍可能漏判。目前未发现实例。
8. **路径藏进容器**（现有）：`PATHS = {"ui/a.js"}` 之后再取出使用 → 守卫报
   **「未判定」**，既不判违例也不放过。`未判定 N 处` 不改变退出码，
   但**必须逐条确认才算收敛**——`未判定 0 处` 才是真正的干净。

### 5.1 跨层动作的登记与收敛记录（已完成）

**为什么登记而不隐藏**：把契约改成能过、或者把这些动作从报告里压掉，只会让下一轮
看不见它们。这一节是这批动作的**收敛记录**——记录只是过程，状态列的「已收敛」才是结论。

| # | 动作 | 脚本 | 目标文件 | 守卫怎么看 | 状态 |
|---|---|---|---|---|---|
| 1 | 数据层**写**前端生成包 | `build_adaptive_data`、`build_catalog`、`build_tier_ui_data`、`build_tree_layouts`、`build_unlock_network` | `ui/adaptive-data.js`、`ui/catalog.js`、`ui/tier-data.js`、`ui/tree-layouts/**`、`ui/unlock-data.js` | 收敛前 C3 **计数 10 处，不计违例**；收敛后 **0 处** | ✅ **已收敛**（2026-10-03，T-CONVERGE-A） |
| 2 | 数据层**读**前端生成包 | `build_text_db.py`（原 `:63`） | 读 `ui/emohealth-data.js` 取大五人格中译 | 收敛前 C3 **漏检**（单字母变量 `p`）。收敛后：守卫已改为跟踪任意长度变量，**未判定 0 处** | ✅ **已收敛**（2026-10-03，T-CONVERGE-B） |

**第 2 类的改法与验收（已执行）**：

* **查清的源头**：大五中译在 `data/scene-taxonomy.json` 的 `items[*].text_zh`（键按
  `text_en` 归一化）；逐题脚手架在 `content/facets/<facet>.record.json` 的
  `items[*].scaffolding`（作者级资产 `content/item_scaffolding.py`）。
  **源头都有，不需要迁移资产**——原以为是「人工资产错放在 ui/」，实测不是。
* **等价性已证**：新 `load_neo_zh()` 与旧实现（逐字复制、读 ui 包）比对，
  中译映射 **300/300 完全相同、差异键 0**；脚手架映射 **300/300 完全相同**。
* **改法**：`build_text_db.py` 改读上述源头；`zh_source` / `sources.*` 标签同步改准。
* ⚠️ **一个必须记住的坑（假溯源）**：原逻辑只在 `e["zh"] is None` 时才写
  `zh_source`，而重建以旧库为底继承 300 条中译 → **只改读取源，产出里的标签仍写着
  旧的 ui 包路径**。改源不改标签 = 假溯源，比不改更糟。已加迁移：值一致且旧标签
  呈路径形态（含 `/` 或 `\`）→ 改写成当前源头；非路径标签（如
  `subagent 初译（待人工复核）`）一律不动。
* **附带修复**：`load_previous()` 现在连 `stats` 一起返回，重建不再清空 collect 维护的
  `translated_batches`（实测复现过：跑一次重建会把 92 批账目清零）。
* **守卫增强**：Python 走 AST + 作用域感知（LEGB）绑定，跟任意长度变量名；
  `db = json.load(open(<路径>))` 这类「值是内容」不跟；容器弱绑定、跨行拆段、
  无法解析都报「未判定」而非静默放过。`tools/check/verify_architecture_guard.py`
  **17/17 正反用例通过**（含上一轮漏检的单字母形态，并明示旧口径不跟踪 `p`）。
* **数据未变**：`entries 2583 / with_zh 2583 / with_scaffold 300 / with_note 2283 /
  items_total 4932 / batches 92` 全同；字段级差异仅 300 条 `zh_source` + 2 个
  `sources` 字符串；`zh`/`scaffold`/`en` 值差异 **0**。

**第 1 类的改法与验收（已执行）**：

* **改法**：数据层脚本只写 `data/**`——`data/tier-prefix.json`、`data/adaptive-network.json`、
  `data/unlock-network.json`、`data/instruments/catalog.json` 原本就有，本轮**新增**
  `data/tree-layouts/<code>.json` 与 `data/tree-layouts/index.json`（原先是直接写
  `ui/tree-layouts/*.js`）。新增前端层打包器 `tools/ui/pack_ui_data.py`，按**声明式作业表**
  把 `data/**.json` 包成 `window.<VAR> = …;` 写到 `ui/**`（新增一个包 = 加一条记录，
  不为每个包写特例代码）。
* **验收依据**：
  1. `python tools/check_architecture.py` 的 C3 行由「10 处写入 ui/（不计违例）」变为
     **0 处**（计数为 0 时该提示不打印），三条契约全绿；
  2. 打包器产出与收敛前的 `ui/*.js` **变量名与 JSON payload 逐字节一致**
     （13 个 JS 包：`tier-data`、`unlock-data`、`adaptive-data`、`catalog` + 9 个
     `tree-layouts/*.js`），`python tools/ui/pack_ui_data.py --check` 全绿；
     `ui/tree-layouts/index.json` 逐字节一致；
  3. 数据层 3 个重脚本重跑后 `data/*.json` **逐字节不变**（确定性）。
* **刻意接受的差异（仅注释头，不动 payload）**：`ui/catalog.js` 与 9 个
  `ui/tree-layouts/*.js` 的头部注释把生成者从数据层脚本改成 `pack_ui_data.py`。
  收敛前这些注释**本来就已经陈旧**（迁移时改了脚本里的路径、没重烘产物，差 6 字节），
  本轮顺手改正；行尾也从 CRLF 归一为 LF。变量名与 JSON 内容不受影响，
  `ui/index.html` 的运行时读取处**未改**。
* **取消的动作（留痕）**：原计划新建 `data/tier-ui.json`。复核发现
  `data/tier-prefix.json` 与 `ui/tier-data.js` 的 payload 本已**逐字节相同**
  （且 `engine/tier.py:48` 读的就是它），再造一份等于第二个真相源，
  因此**取消**该新建，打包器直接从 `data/tier-prefix.json` 打包。
* 另一处更早已消解的跨层依赖：`build_tier_layout.py` 读 `ui/*.js`，按契约定案为
  `tools/ui/`（理由与登记见 `tools/README.md` 文首「初筛用前缀，定案用契约」）。


---

## 6. 目录约定与迁移状态

**目标布局**（当时的迁移映射见 `CLEANUP-PLAN.md` §3，脚本清单见 `tools/README.md`）：

```
tools/
├── _root.py / _root.js   统一根定位基座（Python / JS 同一判据）
├── check_architecture.py 三条契约的守卫
├── cleanup_manifest.json 迁移记录（old / new / sha256），回滚依据
├── pdftext.py 等          共享库，保留平铺
├── survey/  build/  analyze/  check/  ui/  legacy/
└── README.md             全量脚本索引（脚本 → 类别 → 职责 → 输入 → 输出）
```

**状态**：T2–T5 **已执行**（2026-10-03，153 个脚本搬家，`tools/cleanup_manifest.json`
记录每条旧/新路径与移动前 sha256）；T-CONVERGE-A（数据层写 `ui/` 收敛）**已执行**。
当前实测（快照 2026-10-03）：

```powershell
python tools/check_architecture.py
# ✅ C1  前端层不得读 archive/
#      · tools/ui/：16 文件，0 违例 ✅，未判定 0 处
#      · ui/：6 文件，0 违例 ✅，未判定 0 处
# ✅ C2  调研层不得写 data/
#      · tools/survey/：29 文件，0 违例 ✅，未判定 1 处
# ✅ C3  数据层不得读 ui/
#      · tools/build/：45 文件，0 违例 ✅，未判定 1 处
#      · tools/analyze/：10 文件，0 违例 ✅，未判定 0 处
# ✅ 三条契约全部通过。
#    未判定 2 处（明细见上，逐一确认后才算收敛）
# 退出码 0
```

> 文件数按「参与扫描的扩展名」计：`tools/survey/` 的 29 个全部入列；
> `tools/build/` 的 46 个里有 1 个是 `translate_prompt.md`（`.md` 不计），故 45。
> C3 那行已**不再出现**「N 处写入 ui/（不计违例）」——该计数只在 > 0 时打印，
> 现在为 0，说明数据层写前端包的动作已收敛（见 §5.1）。
> 「未判定 N 处」是守卫**判不出来**的行，不等于通过；当前 2 处里 1 处来自
> `build_text_db.py`（§5.1 第 2 类，另一轮处理中）。


---

## 7. 常见违规形态 → 正确写法

**C1**：前端脚本里出现 `archive/scales/PID-5/items-extracted.json`
→ 改为由数据层产出 `data/instruments/pid-5.json`，前端只读数据包。

**C2**：调研脚本 `probe_*.py` 里 `json.dump(candidates, open(ROOT/"data/x.json","w"))`
→ 写 `research/scales/candidates.json`；要进 `data/`，由 `tools/build/` 从 `archive/` 重产出。

**C3**：分析脚本读 `ui/net-layout.js` 取坐标
→ 坐标先落成 `data/**`（布局脚本产出），分析只读 `data/**`。

**根定位**：`ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))`
→ `ROOT = find_root()`（见 §4）。

---

## 8. 与其他文档的关系

| 文档 | 作用 |
|---|---|
| `PLAN.md` | **规则与计划（唯一真相源）**：R1–R4 + 阶段计划 + 当前状态 |
| `ARCHITECTURE.md`（本文） | 三层的输入/输出契约 + 三条技术契约 C1/C2/C3 |
| `tools/README.md` | 脚本分类索引（职责 / 输入 / 输出） |
| `instrument-record.schema.md` | 量表档案 schema 与 V1–V7 校验规则 |
| `CLEANUP-PLAN.md` | 工具目录清理的**历史记录**（已完成，不再是规则来源） |
| `STALE-CLEANUP.md` / `SCOPE-REDUCTION.md` | 历史账本（做过什么，只记录事实） |
