# EmoHealth · 自测陪伴工具

站在「盲目自测」与「去精神科/心理科找专业医生」之间的 **AI + 专业数据的自测陪伴工具**。

用公开的 **IPIP-NEO-300**（Goldberg 1999，公有领域）+ 已发表的常模与信度数据，
做一份**说得出自己有多准**的人格自测。

> **这不是诊断工具。** 它不诊断任何东西，也不构成任何医疗建议。
> 所有分数都是固定算法从作答算出的，**没有经过任何 AI 改写**。
> 作答只存在你自己的设备上，**没有任何上传路径**。

---

## 现在能做什么

打开 `ui/index.html` 即可（纯静态，无需服务器）。

三种模式：

| 模式 | 做什么 |
|---|---|
| **分级模式**（默认） | **支撑驱动的网状图**。第 1 环 30 题强制答完 → 给 5 个大类；之后**按信息增益自适应选题**，细类逐个解锁。进度看**逐面向的可信度**（r），不看「完成几层」 |
| 情景模式 | 按生活情景分组作答，一个情景答完就给该情景下的结果与基线比较 |
| 经典模式 | 官方 1–300 题序，每 30 题一轮 |

答题过程中**只展示完成度，不展示分值**。有面向变得可解读时，顶部出现
**默认收齐**的折叠区；收起后 10 秒内不能继续作答（防自我强化）。

---

## 两个包

| 包 | 大小 | 含什么 |
|---|---:|---|
| `emohealth-<日期>-full.tar.gz` | 400 MB | 全部，含 `archive/`（1944 个文件）与 `MANIFEST.sha256` |
| `emohealth-<日期>-slim.tar.gz` | 2.8 MB | 不含 `archive/` 与 `vendor/`，够跑界面与大部分测试 |

两个包**都不含 `vendor/`**（197 MB 的平台相关二进制）——新机器上跑 `./bootstrap.sh` 重建。

到新机器后先校验：

```bash
tar -xzf emohealth-*-full.tar.gz && cd emohealth
shasum -a 256 -c MANIFEST.sha256     # 181 个核心文件逐字节
python3 tools/check/verify_archive.py --root archive
```

> 改过文件之后重新生成清单：`python3 tools/build/build_manifest.py`
> （`--check` 只报告差异）。原先生成清单的脚本没入库，手改的结果是清单
> **长期滞后于仓库**——实测补写之前它少了 20 多个文件，
> 「逐字节校验」这句话就少验了一部分。

## 目录

```
content/     题目、翻译、构念定义、脚手架、分带 —— 文本资产
engine/      计分引擎（assess / scene / session / tier / agent_contract）
tools/       分析脚本与测试
ui/          纯静态界面 + 烘好的数据包
data/        分析产物（分层设计、常模、相关网络、精度表…）
research/    研究报告与契约文档
archive/     出处档案（证据链：可溯源；证据本身有误时按 PLAN.md R3 记录→溯源→更正）
PLAN.md      规则与计划：R1–R4 + 阶段计划（**改动前先读这个**）
instrument-record.schema.md   量表记录的模式定义
```

---

## 换机器：三步

```bash
./bootstrap.sh      # 1. 建好分析环境（装依赖到项目内 vendor/）
./run.sh -c "import sklearn; print(sklearn.__version__)"   # 2. 自检
open ui/index.html  # 3. 打开界面（macOS；其他系统用浏览器打开同名文件）
```

**不需要装任何东西也能看界面** —— `ui/` 是纯静态的，数据已经烘进 `ui/*.js`。

### 两个 Python，分工不同

| | 用什么 | 需要什么 |
|---|---|---|
| **界面 + 引擎 + 测试** | 任意 Python ≥3.9 | `numpy`、`pandas` |
| **分析脚本**（`analyze_*` / `build_*` / `optimize_*` / `compare_*`） | 系统 Python + 项目内 `vendor/` | 再加 `scikit-learn` |

分析脚本一律通过 `./run.sh` 跑，它会把 `vendor/` 塞进 `PYTHONPATH`。

> **为什么不用捆绑的 Python 跑分析**：那是一套**加固运行时**，
> 加载不了 pip 装的 `.so`（Team ID 不匹配），ad-hoc 重签与去签名都无效。
> 这不是配置问题，是 macOS 的代码签名约束。

---

## 本地开发与预览

**两种方式，都不需要部署**：

```bash
# ① 最省事：直接打开（file://）
#    双击 ui/index.html 即可。已验证可用（11 套量表包：IPIP 大五 / PID-5 / DSM5TR 链；2026-10-04 瘦身，其余量表已移除、按需加载、天赋树、
#    导出下载都在 file:// 下正常）——项目本来就是离线静态、相对路径。
start ui/index.html

# ② 本地 HTTP（行为与部署后一致，便于对着 URL 调试）
node tools/ui/serve_local.js               # → http://127.0.0.1:8892/ui/
node tools/ui/serve_local.js --port 9000   # 换端口
node tools/ui/serve_local.js --no-open     # 不起浏览器
```

改完 `ui/` 下的文件刷新即生效（服务器不发缓存头）。

```bash
# 本地直开的回归（file:// 路径）
node tools/check/test_local_file.js           # 目录/按需加载/子页/天赋树/导出
```

> 部署（同步到博客仓库）是**另一件事**，用 `node tools/ui/sync_blog.js`；
> 本地开发不需要它。

---

## 跑测试

> ⚠️ 带 **(需档案)** 的测试要读 `archive/` 里的原始数据。
> 精简包（`*-slim.tar.gz`）不含 `archive/`，这些测试跑不了——
> 其余全部可跑。

```bash
# 引擎
python3 tools/check/test_item_coding.py       # 计分方向回归（5 组）(需档案)
python3 tools/check/test_scene.py             # 情景模式不变量（7 组）
python3 tools/check/test_agent_contract.py    # 契约不变量（6 组）
python3 tools/check/validate_records.py       # 档案校验（V1–V8）
python3 tools/check/verify_archive.py --root archive       # 归档完整性 (需档案)

# 界面（需要 node + 本地 Chrome，走 CDP）—— 见下节「多量表与子页（本地即可跑）」
# 注：原 6 个 node DOM-stub 测试（test_ui_{adapt,block,export,tier,tree,unlock}.js）
#     因 stub 缺 addEventListener 长期 exit=1，已于 2026-10-03 删除（见 STALE-CLEANUP.md），
#     其覆盖的界面行为由下列真浏览器测试接管。
```

### 多量表与子页（本地即可跑）

```bash
# 起本地服务（下面几条默认访问 http://127.0.0.1:8892/ui/）
node tools/ui/serve_local.js --no-open &

node tools/check/test_local_file.js        # file:// 直开：目录/按需加载/子页/天赋树/导出
node tools/check/test_scale_pages.js       # 子页与路由：URL 直达、后退、子页内切换作答方式
node tools/check/test_scale_export.js      # 子页导出：真的落盘后核对文件内容
node tools/check/test_tree_mode.js         # 天赋树：> 60 题的量表、节点/解锁/推荐
node tools/check/test_multiscale_fetch.js  # 按需加载与完整作答流程
node tools/check/check_mobile_layout.js    # 移动端几何（会自动导航到 #/tier）

# 换目标地址（默认本地服务；也可指部署后）
URL=http://127.0.0.1:8892/ui/ node tools/check/test_scale_pages.js
```

### 文本与量表数据

```bash
python3 tools/check/check_text_db.py        # 文本库：结构/覆盖率/译文质量（前端闸门）
python3 tools/check/check_item_language.py  # 题文语言（防混入非英文）
python3 tools/check/check_item_truncation.py# 题文截断（折行续接丢失）
python3 tools/check/test_catalog.py         # 目录与溯源链完整性
```

> **开发工具**（不进 v1 交付链路）：
> - `node tools/ui/dev_check_render.js` —— 语法 + 死代码 + **标注防重叠**。
>   它渲染**宽屏 7 个状态 + 窄屏**、解析 SVG 里每个标注的盒子，有任何互相重叠、
>   压住可见节点、或窄屏几何没放大即失败。**这类问题不报错，只有看图才发现，
>   而看图太慢**——所以做成可判定的检查。
> - `node tools/ui/shoot_ui.js [--mobile]` → `.shots/*.png` —— 用 CDP 驱动无头 Chrome
>   截图，不需要装 puppeteer/playwright。`--w/--h` 可指定视口。
> - `node tools/ui/dev_probe.js` —— 把 `ui/index.html` 的内部函数挂出来，方便临时核查。

界面测试用 `node` 跑，但**要真实浏览器**：`tools/check/*.js` 与 `tools/ui/*.js` 通过 CDP
直连无头 Chrome（环境变量 `$CHROME`），不做 DOM stub。
原先的 6 个 DOM-stub 测试已于 2026-10-03 删除——它们的 stub 只有 `global.window`、
缺 `addEventListener`，6 个全部 `exit=1`、长期无效（见 `STALE-CLEANUP.md`）。

---

## 重新生成数据包

改过 `data/` 或 `content/` 之后，界面数据要重烘：

```bash
python3 tools/ui/build_ui_bundle.py        # → ui/emohealth-data.js

# 数据层：只出 data/（不写 ui/，契约 C3）
./run.sh  tools/build/build_tier_ui_data.py   # → data/tier-prefix.json（约 4 分钟）
./run.sh  tools/build/build_unlock_network.py # → data/unlock-network.json
./run.sh  tools/build/build_adaptive_data.py  # → data/adaptive-network.json
./run.sh  tools/build/build_catalog.py        # → data/instruments/catalog.json
./run.sh  tools/build/build_tree_layouts.py   # → data/tree-layouts/*.json

# 前端层：把 data/ 包成界面可加载的 window.* 赋值脚本
python3   tools/ui/pack_ui_data.py         # → ui/tier-data.js、unlock-data.js、adaptive-data.js、
                                           #   catalog.js、tree-layouts/**（含 index.json）
python3   tools/ui/build_tier_layout.py    # → ui/net-layout.js（网状图坐标 + 支撑边 + 角序）
```

**顺序有依赖**：`pack_ui_data.py` 必须排在数据层脚本之后（它读 `data/**`），
而 `build_tier_layout.py` 要读打包好的 `ui/tier-data.js`、`ui/adaptive-data.js`
（题-题相关）与 `data/correlation-network.json`（面向级相关），所以它排最后。
数据层不再直接写 `ui/*.js`：`tier-data.js`、`unlock-data.js`、`adaptive-data.js`、
`catalog.js`、`tree-layouts/**` 全部由 `pack_ui_data.py` 从 `data/` 里的对应物打包
（`--check` 只比对不写，`--list` 列出作业表）。
它一次做完两件事：**30 个面向的角序**（环形序列化，原 `optimize_layout.py`
已并入）与**300 题的位置**（每题挂到「更浅、最相关」的已答内容旁）。

它带自检，任一条不过就返回非零：

- 角序是一个排列，且目标值优于「按维度分扇区」
- 矩阵与标签**绑定正确**：每个面向拿自己的 10 道题去和 30 个面向总分算相关，
  必须「与自己最相关」（实测 30/30）——防 D88 那种「矩阵没错、标签错了」
- 最小节点间距、出界节点数
- **每层平均半径必须单调递增**——这是「离中心越远＝阶梯越深」成立的条件

---

## 规则（`PLAN.md` R1–R4）

工作规则与计划以 [`PLAN.md`](PLAN.md) 为**唯一真相源**。四条规则：

1. **R1｜判据是「内容是否正确」，不是「来源是否正规」。** 挑剔来源的唯一理由是内容可能有误；
   只要内容能与权威版本逐条核对，就采用。每个进入产品的数字都要能指到可核验的出处。
2. **R2｜授权要求原文不动时，出中英双版。** 英文原文 + 中文翻译 + 完整的本地化讲解，
   三件一起给——这是**补充性的独立内容**，不是对原文的改动。
3. **R3｜缺陷必须「记录 → 溯源 → 完整修复」。** 记录只是过程；混入错误内容的缺陷（题面截断、
   混入版式文本、残留控制字符、选项组错位）必须修到好，并补回归断言。
4. **R4｜开发顺序不可颠倒。** 文献数据 → 专业手册 → 完整的可填量表文档 + 评估指标 →
   全部做完才设计 UI → 最后才接受缺省值 / 实时估测。

### 流程规则：先文本库，后前端

新量表一律走四步，**前一步没校验通过，不进入下一步**：

```
① 提取  tools/build/build_*_items.py   → archive/scales/<code>/items-extracted.json
② 清洗  tools/build/clean_l2_glyphs.py → 去残留字形、统一空白、语言校验
③ 文本库 tools/build/build_text_db.py  → data/text-db/*.json（英文题文 + 中译 + 注释，中英成对）
④ 校验  tools/check/check_text_db.py   → 覆盖率、编号连续、译文完整、来源可追
────────────────────────────────────────────────────────────
⑤ 前端  只有 ④ 全绿，才生成 ui/instruments/<code>.js
```

理由：前端出错的代价远高于文本库出错——文本库错了能在校验里拦住，前端错了用户直接看到错题。

### 界面规则：每套量表都支持两种作答方式

和大五人格一样，**每一套**量表都要能：

* **类天赋树**：选择「下一个答哪题」，按相关性推荐，图上看进度
* **经典模式**：逐题翻页作答

两种方式的作答结果必须**同源**（同一份作答状态、同一套计分键）。

---

## 先读什么

| 想知道 | 读 |
|---|---|
| 规则与计划（**唯一真相源**） | `PLAN.md`（R1–R4 + 阶段计划 + 当前状态） |
| 每套量表的可填文档与评估指标 | `data/descriptions/<code>.md`、`data/norms/<code>.json`（证据链见 `research/descriptions-evidence/`） |
| 分级解锁怎么算的 | `research/phase3_tiered_unlock.md` |
| 界面上的数字意味着什么 | `ui/README.md` |
| 题目文案怎么定的 | `research/` 下的翻译与文案报告 |
| 量表的字段定义 | `instrument-record.schema.md` |

---

## 已知的坑（都踩过，别再踩）

这些都是**不报错、只是静默给错数字**的那一类：

- **计分方向**：Johnson 数据**本来就是反向重编码的**，再翻一次是双重翻转。
  判据是「反向题与**正向题加总**的相关符号」，锚点只能用正向题（否则判据循环）。
  见 `tools/item_coding.py`。
- **跨文件顺序**：不同数据包的「第 k 个面向」**未必是同一个面向**。
  已有两次因此贴错标签。改动数据包时务必加顺序断言。
- **三角形索引**：行偏移是 `(a−1)(a−2)/2`，写成 `a(a−1)/2` 会整体错位，
  越界前不报错。见 `tools/build/build_adaptive_data.py` 的自检①。
- **存储精度**：相关矩阵用 int16 存会破坏正定性（残差方差变负、出现 NaN）。
  用 float32，并加岭正则化。
- **门槛一致性**：同一个门槛写在多处会走样（曾出现「解锁了却不给看结果」）。
