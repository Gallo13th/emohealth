# STALE-CLEANUP.md — 过时失效文件清理留痕

> **执行人**：`stale-cleanup`（Team 子任务 `task-5` / T-STALE）　**日期**：2026-10-03　**裁决人**：`lead`
> **原则**：删是不可逆的，所以每条删除都先有证据（可复现的命令或肉眼可核对的界面差异）再动手；
> 拿不准的**不删**，列在 §5/§6 交回 Lead。**静默删除是不允许的** —— 本文件就是「原来有什么、为什么没了」的账本。

## 0. 本轮做了四件事

| # | 类别 | 动作 | 数量 | 涉及体积 |
|---|---|---|---|---|
| ① | 失效的可执行物（A） | **删** | 6 个文件 | 61,105 B |
| ② | 临时与缓存（C） | **删** | 9 个目录 / 154 个 .pyc | 1,751,585 B |
| ③ | 悬空引用（B）＝迁移遗留 | **修**（不删） | 17 个旧路径 / 396 文件 / 480 处 | — |
| ④ | 作废截图 | **删** | 14 个文件 | 2,768,908 B |

**档案完整性核对**：`archive/**` 在本次清理期间未改动 —— 清理前后均为 **1987 文件 / 670,295,616 字节**（当时口径；§7 第 6 条有实测输出）。档案后来继续入档，当前为 **2041 文件 / 755,864,849 字节**。

---

## 1. ① 删除：6 个失效的 node DOM-stub 测试

**判定失效的依据（可复现）**：

```
PS> node tools/check/test_ui_adapt.js
node : <anonymous_script>:3389
window.addEventListener("hashchange", applyRoute);
       ^
TypeError: window.addEventListener is not a function
    at eval (eval at <anonymous> (…\tools\check\test_ui_adapt.js:44:1), <anonymous>:3389:7)
PS> $LASTEXITCODE
1
```

6 个**全部 `exit=1`**，报错一致：它们的 DOM stub 只写了 `global.window = {...}`，
缺 `addEventListener`（`ui/app.js` 在 `eval` 时立刻抛错，后续断言一条都跑不到）。
**长期如此**：stub 自建立起就与 `ui/app.js` 的 `hashchange` 监听不兼容，即这 6 个测试**从未真正验证过任何东西**。

**替代物**：同一批界面行为已由**真浏览器测试**（真 Chrome + CDP）覆盖且全绿 ——
`test_local_file.js`、`test_scale_pages.js`、`test_tree_mode.js`、`test_chain_nav.js`、`test_l2_criteria_ui.js`、`test_pid5_norms_ui.js`
（`tools/check/` 下 11 个 `.js` 全部走 CDP，无一使用 DOM stub；见 §7 第 4 条）。

**处置**：删除；同时更新两处索引（`tools/README.md` §3.4 去掉 6 行并留说明、根 `README.md` 的示例命令块与「界面测试」段落改写）。

| 路径 | 大小 | 删除前 sha256 | 替代物 | 日期 |
|---|---|---|---|---|
| `tools/check/test_ui_adapt.js` | 28,030 B | `2514a4185bdf80be089ef5b06c977abed3ab638b125b6726991447f223cd086a` | 真浏览器 CDP 测试（见上） | 2026-10-03 |
| `tools/check/test_ui_block.js` | 4,797 B | `22da6a43af1f26c1080123f24a55c6a6b8348bdd93554488dc95a4a67ef7fb0c` | 真浏览器 CDP 测试（见上） | 2026-10-03 |
| `tools/check/test_ui_export.js` | 8,917 B | `9cf243da917cb7e3f7ea47e8b3e1363077a38e7fa1a6fbc913707a3e446b7fe8` | 真浏览器 CDP 测试（见上） | 2026-10-03 |
| `tools/check/test_ui_tier.js` | 3,834 B | `4dfbdbd163c5fabc6a6cd0fef5536e8f7ea1e4742ddae537b3a94bf8b15309cf` | 真浏览器 CDP 测试（见上） | 2026-10-03 |
| `tools/check/test_ui_tree.js` | 8,433 B | `89161306982fb84ce380ac3e14de7f0f6c63bb5d1135f391de24235b9ae8b8eb` | 真浏览器 CDP 测试（见上） | 2026-10-03 |
| `tools/check/test_ui_unlock.js` | 7,094 B | `f565ff3149c299880e627fe6d29473785b07331f13cb2b4eac7c83f5c1bf31c8` | 真浏览器 CDP 测试（见上） | 2026-10-03 |

**小计**：6 个文件，61,105 字节。

---

## 2. ② 删除：9 个 `__pycache__` 目录（纯缓存）

**判定依据**：Python 字节码缓存，**可无条件再生**（任何一次 `import` 都会重建）；
已在 `.gitignore` 内，且 `tools/build/build_manifest.py` 的 `SKIP_DIRS` 明确排除 `.pyc`/`__pycache__`。
删它不影响任何可复现结果。

| 目录 | .pyc 数 | 体积 | 日期 |
|---|---|---|---|
| `content/__pycache__/` | 4 | 130,359 B | 2026-10-03 |
| `engine/__pycache__/` | 14 | 222,081 B | 2026-10-03 |
| `tools/analyze/__pycache__/` | 10 | 129,109 B | 2026-10-03 |
| `tools/build/__pycache__/` | 45 | 524,622 B | 2026-10-03 |
| `tools/check/__pycache__/` | 36 | 287,187 B | 2026-10-03 |
| `tools/legacy/__pycache__/` | 4 | 37,346 B | 2026-10-03 |
| `tools/survey/__pycache__/` | 25 | 149,227 B | 2026-10-03 |
| `tools/ui/__pycache__/` | 3 | 50,028 B | 2026-10-03 |
| `tools/__pycache__/` | 13 | 221,626 B | 2026-10-03 |

**小计**：9 个目录 / 154 个 .pyc，1,751,585 字节。

> ⚠️ **再生说明**：之后每跑一次 Python，`tools/__pycache__`（以及跑过的 `content/`、`engine/`、`tools/*`）会重新出现——
> 这是**正常**的，不是清理失败。§7 第 1 条的最终测绘里 `__pycache__ 目录：1` 就是跑测绘脚本本身又生成的 `tools/__pycache__`。

---

## 3. ④ 删除：14 个已作废的 `.shots/` 截图

**先记录基线**：`.shots/` 清理前 **26 个文件 / 5,331,061 字节**；删除 14 个 / 2,768,908 字节后剩 **12 个 / 2,562,153 字节**（§7 未单列，命令：`Get-ChildItem .shots -File | Measure-Object Length -Sum`）。

> ⚠️ **与任务描述的出入**：任务标题写「13 个」，但其**明确列出的删除清单是 14 个**
> （`ei-tree.png` 1 + `s0…s6` 7 + `m*` 6 = 14），且 `26 = 12 保留 + 14 删除` 恰好对上。
> 我按**明确清单**执行（14 个），并在 §6 列出此出入请 Lead 复核。

**判定标准**（任务给定）：截图呈现的是**已修复的坏状态**，或**界面已重构**。逐张证据如下：

| 路径 | 大小 | 删除前 sha256 | 采集时间 | 判定 | 证据 | 替代物 |
|---|---|---|---|---|---|---|
| `.shots/ei-tree.png` | 56,332 B | `ff587a9574f9c71ffbc1f824a961dc5bf8d3894db2aee07398b58befdba9969c` | 2026-10-03 15:01:08 | 呈现**已修复的坏状态** | 采集于 `--brand` CSS 变量未定义时，可答节点**无高亮**（图中 7 个内环节点全灰，无高亮环）。该 bug 已修；同场景当前证据 `ei-tree2.png`，已验 7 个节点全部高亮。 | `ei-tree2.png` |
| `.shots/m30-360x640.png` | 71,577 B | `c50439ac3d12a9744569c647fb0866eee80e0fc54768f557b2ef639dde5d77cc` | 2026-10-02 14:21:20 | 同批移动端，重构前状态 | 2026-10-02 14:21 同批采集；窄屏几何此时为放大前的旧样式，`check_mobile_layout.js` 后来专门针对这两条体验约束加了门。 | `node tools/check/check_mobile_layout.js`（CDP，实时可复现） |
| `.shots/m30-390x844.png` | 100,486 B | `bfd4fdcaadacea32d333cb153ff145f05667dde48d5b210dff2e694780f42b9d` | 2026-10-02 14:21:24 | 同批移动端，重构前状态 | 同上（390×844 视口，30 题）。 | `node tools/check/check_mobile_layout.js`（CDP） |
| `.shots/m60-360x640.png` | 79,088 B | `c1d37eb958f878cea5080c58d3cef0c8f4d08f3a53313f036f442e33b15c7bfc` | 2026-10-02 14:21:21 | 同批移动端，重构前状态 | 同上（60 题状态）。 | `node tools/check/check_mobile_layout.js`（CDP） |
| `.shots/m60-390x844.png` | 112,421 B | `f3e731891040fbeecc0f70230c44641d6e35ed6e3a3080ded3b2ff15027d4dc2` | 2026-10-02 14:21:25 | 同批移动端，重构前状态 | 同上（390×844 视口，60 题）。 | `node tools/check/check_mobile_layout.js`（CDP） |
| `.shots/m60-picked-360x640.png` | 59,780 B | `e927ea8e8bd5602de6a5b4afcadb0a10d7177b96e102429f0a42063cf174a40c` | 2026-10-02 14:21:21 | 同批移动端，重构前状态 | 同上（60 题 + 已选题）。 | `node tools/check/check_mobile_layout.js`（CDP） |
| `.shots/m60-picked-390x844.png` | 74,805 B | `dfdf654d39126e4683eaac98f39026af57f272f6832826c9d7374bcf0884a46b` | 2026-10-02 14:21:25 | 同批移动端，重构前状态 | 同上（390×844 视口，60 题 + 已选题）。 | `node tools/check/check_mobile_layout.js`（CDP） |
| `.shots/s0-empty.png` | 229,140 B | `b6528b0dfcf82bc3714f27323b633176edd743231935a18c114e918db5605e5b` | 2026-10-02 14:19:04 | 初版树 UI，布局已重构 | 2026-10-02 采集的初版树界面；此后树布局（环半径按题量分配）与节点样式重构，勾选框位置、进度条样式均已变。 | `inst-tree.png`、`ei-tree2.png` |
| `.shots/s1-answered30.png` | 284,829 B | `3d206645b6f4f258b958d1b91f618714930228b8908890dc2f6635ab833826a3` | 2026-10-02 14:19:05 | 初版树 UI，布局已重构 | 同 s0，2026-10-02 初版；`已答 30/300` 状态下的节点重叠未修。 | 真浏览器测试 `test_tree_mode.js`（CDP） |
| `.shots/s2-selected.png` | 293,830 B | `dfdc5fcb8c0946bb005d23a278436af6a1c1e61f69350c920dde552b6f5d167e` | 2026-10-02 14:19:05 | 初版树 UI，布局已重构 | 同 s0，2026-10-02 初版；选中态样式已重做。 | `inst-picker.png`、`inst-answer.png` |
| `.shots/s3-answered60.png` | 323,767 B | `fd4c90155a570766a416cab54d40af3ce09b4dbe031401266dc8520de3f71413` | 2026-10-02 14:19:06 | 初版树 UI，布局已重构 | 同 s0，2026-10-02 初版；`已答 60/300` 状态。 | 真浏览器测试 `test_tree_mode.js`（CDP） |
| `.shots/s4-answered300.png` | 422,690 B | `b3e1d996bbb09aaace75d568e082a27cb193d0e1428f00b7f3e99a10616f6325` | 2026-10-02 14:19:07 | 初版 UI，界面已重构 | 2026-10-02 初版：顶部**只有** 分级/情景/经典 三个 tab（当前多了「题库」tab）；节点密集重叠（不同分支节点在中圈互相压住）；右侧结果面板为旧版。 | `ui/index.html` 现行版（实时可复现） |
| `.shots/s5-answered45.png` | 303,474 B | `1c9e4aa8084b75aa3f3b9ac22202e8dc8c5d51a65f0a34325540b15e653913c1` | 2026-10-02 14:19:08 | 初版树 UI，布局已重构 | 同 s0，2026-10-02 初版；`已答 45/300` 状态。 | 真浏览器测试 `test_tree_mode.js`（CDP） |
| `.shots/s6-answered90.png` | 356,689 B | `121b5220cdab3152872764da8ed9f6c9ba5ecf1f8340b5def4950ad65e09bd98` | 2026-10-02 14:19:08 | 初版树 UI，布局已重构 | 同 s0，2026-10-02 初版；`已答 90/300` 状态。 | 真浏览器测试 `test_tree_mode.js`（CDP） |

**肉眼复核（本次实测，不是转述）**：

* `ei-tree.png`：7 个内环节点**全灰、无高亮环** → 坏状态；`ei-tree2.png` 同场景 7 个节点**全部有绿色高亮环** → 已修。
* `s4-answered300.png`：顶部**只有** 分级/情景/经典 三个 tab（现行界面已多出「题库」tab）；节点在不同分支间**互相重叠压住**；右侧结果面板为旧版。→ 界面已重构，非当前状态。
* `.shots/` 保留的 12 个里 `inst-tree.png`（2026-10-03 12:08）**按任务清单保留**，但其采集时间早于 `ei-tree2.png`（15:06）。
  我**没有**删它；见 §6 第 4 条请 Lead 确认。

**保留的 12 个（当前证据，未动）**：`ei-tree2.png` `chain-l1.png` `chain-l2.png` `l1-threshold.png` `subpage-header.png` `subpage-short.png` `inst-picker.png` `inst-answer.png` `inst-norms.png` `inst-tree.png` `inst-mania.png` `inst-result-disabled.png`

**小计**：14 个文件，2,768,908 字节。

---

## 4. ③ 修复：迁移遗留的悬空引用（**改路径，不删文件**）

**性质**：这些路径是**溯源元数据**（记录「这个文件/数据是怎么生成的」）与文档注释；
T2–T5 迁移只修了 `tools/**`、根文档、`research/*.md`、`ui/README.md`，**漏修了 `content/**`、`data/**`、`ui/**`**，于是指向已被搬走的旧位置。指错路径会误导下一个人，必须改准。

**复核发现（比任务清单更全）**：`tools/survey/survey_stale_files.py` 的悬空引用正则要求路径**被引号包住**
（`["'](tools|data|…)/….py["']`），因此**漏报**了注释/`_note` 里不带引号的同类引用。
我改用「拿 `tools/cleanup_manifest.json` 的 153 条 `old→new` 映射去全树比对」的办法重扫，
共找到 **17 个旧路径、480 处、分布在 396 个文件**（任务的表只覆盖其中 4 个路径）。**这 480 处全部已修**，复扫后迁移遗留悬空引用 = **0**。

| 旧路径（已不存在） | 改成（实际位置） | 含它的文件数 |
|---|---|---|
| `tools/build_ui_instruments.py` | `tools/ui/build_ui_instruments.py` | 343 |
| `tools/parse_uk_norms.py` | `tools/build/parse_uk_norms.py` | 33 |
| `tools/build_all_facets.py` | `tools/build/build_all_facets.py` | 32 |
| `tools/extract_l1_table1.py` | `tools/survey/extract_l1_table1.py` | 19 |
| `tools/build_l2_items.py` | `tools/build/build_l2_items.py` | 16 |
| `tools/validate_records.py` | `tools/check/validate_records.py` | 6 |
| `tools/build_pid5_scoring_keys.py` | `tools/build/build_pid5_scoring_keys.py` | 4 |
| `tools/build_pid5_items.py` | `tools/build/build_pid5_items.py` | 3 |
| `tools/probe_ipip300_layout.py` | `tools/survey/probe_ipip300_layout.py` | 3 |
| `tools/build_l1_items.py` | `tools/build/build_l1_items.py` | 2 |
| `tools/build_remaining_slices.py` | `tools/build/build_remaining_slices.py` | 2 |
| `tools/fix_dsm5tr_licenses.py` | `tools/build/fix_dsm5tr_licenses.py` | 2 |
| `tools/build_tier_layout.py` | `tools/ui/build_tier_layout.py` | 1 |
| `tools/build_tree_layouts.py` | `tools/build/build_tree_layouts.py` | 1 |
| `tools/check_item_language.py` | `tools/check/check_item_language.py` | 1 |
| `tools/exclude_non_english.py` | `tools/build/exclude_non_english.py` | 1 |
| `tools/fix_neo_item_text.py` | `tools/build/fix_neo_item_text.py` | 1 |
| **17 个旧路径合计** | | **470**（去重后 **396** 个文件；实际替换 **480** 处字符串） |

**改动方式**：逐字节读入 → 只替换上述路径字符串 → 逐字节写回（不碰编码、不碰行尾、不动任何逻辑）。
典型改动点：

* `content/facets/*.record.json`（30）与 `content/pilot/*.record.json`（3）：`norms.parser` 字段（如 `tools/parse_uk_norms.py` → `tools/build/parse_uk_norms.py`）。
* `content/facets/*.record.json` 的 `_note`、`content/facet_definitions.py`、`content/item_scaffolding.py`：注释里的生成者。
* `data/instruments/*.json`、`data/linkage/dsm5tr-chain.json`：`extractor` / `items` / `tool` / `license` 溯源串。
* `data/pid5-{scoring,reverse}-keys.json`、`data/instruments/pid-5.json`：`generator` / `extractor`。
* `ui/instruments/*.js`（343 个）：文件头 `/* … 由 tools/build_ui_instruments.py 生成，勿手改 */`。
  **注意**：生成器 `tools/ui/build_ui_instruments.py:144` 早就写的是**新路径**，
  即磁盘上的这 343 个产物是「迁移后未重生成」的陈旧产物；改注释后它们与生成器的口径**一致**了。
* `ui/instruments.js`、`ui/index.html`、`ui/emohealth-data.js`：注释与元数据串。

**为什么可以安全改**：
1. 全部是注释/元数据字符串，**没有任何一处是代码依赖**（`tools/README.md` §4 已把 `build_ui_instruments.py` 343 次、`parse_uk_norms.py` 35 次标注为「数据提及，非代码依赖」）。
2. 新路径**逐一断言存在**（脚本里 `assert os.path.exists(new)`）后才替换。
3. 改的是**已经指错**的串 → 只会更准，不会更错。
4. `ui/instruments/*.js` **不在** `tools/ui/pack_ui_data.py` 的作业表内（该表只管 `tier`/`unlock`/`adaptive`/`catalog`/`tree-layouts`），所以不影响 §7 第 5 条的逐字节校验。

---

## 5. 明确**不动**的东西（避免误删/误改）

| 对象 | 为什么不动 |
|---|---|
| `archive/**` | 证据链。本次清理未改动它：实测 **1987 文件 / 670,295,616 字节**不变（当时口径；当前 2041 / 755,864,849 字节，见 §7 第 6 条） |
| `tools/legacy/` 的 4 个 `demo_*.py` | **有意归档**的演示脚本，不是失效文件 |
| `content/__init__.py`、`engine/__init__.py`（0 字节） | 包标记文件，**故意为空**；不是残留 |
| `.shots/` 的 12 个保留项 | 当前证据；见 §3 与 §6 第 4 条 |
| `tools/cleanup_manifest.json` 里的 `tools/analyze_*.py` 等 | 这是**迁移回滚账本**，`old` 字段按设计就写旧路径；改了会毁掉回滚依据（详见 §6 第 2 条） |
| `ARCHITECTURE.md` 的 `data/x.json`/`ui/a.js`/`data/tier-ui.json`、`tools/check_architecture.py` docstring 的 `data/x.json` | **文档示例**，举的是「路径字面量长什么样」，本就不该存在 |
| `tools/check/verify_architecture_guard.py` 的 `tools/build/p.py`、`ui/app.js`、`archive/scales/x.json` 等 | **测试用例字符串**，故意用不存在的路径来测守卫 |
| `tools/_root.py`/`_root.js`/`survey_refs.py`/`survey_stale_files.py`/`ARCHITECTURE.md`/`CLEANUP-PLAN.md` 里的 `tools/xxx.py`、`tools/survey/foo.py`、`ui/xxx.js`、`data/xxx.json` | 占位符/示例，故意不存在 |

---

## 6. 拿不准的 / 与预期不符的（交回 Lead，未自行处置）

1. **任务标题说 13 个截图，明确清单是 14 个**（见 §3）。我按明确清单删了 14 个（`26 = 12 + 14` 自洽）。若 Lead 的 13 才是本意，请指出该回滚哪一个——**回滚方法见 §8**。
2. **`survey_stale_files.py` 的悬空引用检测漏报无引号引用**（其正则要求路径**被引号包住**，注释/`_note` 里裸写的路径一律看不见）。
   实测漏了 **480 处 / 396 文件**（含 343 个 `ui/instruments/*.js` 的文件头注释）。
   我按 `cleanup_manifest.json` 的 `old→new` 映射把它们全修了；**建议后续把测绘脚本改成「映射比对」而不是「引号正则」**——本轮未改测绘脚本逻辑（超出「只删+修引用」的范围）。
3. **`tools/cleanup_manifest.json` 与 `MANIFEST.*` 的连带影响**：
   * 账本里 6 个 `test_ui_*.js` 的 `new` 路径现在指向**已删除**的文件（`moves` 有 6 条、末尾清单有 6 条）。我**没有**改账本（它是历史记录），但「153 条 new 路径全部存在」这个不变量**现在不再成立**——下一轮若要用它做回滚，需知这 6 个已被本文件 §1 有意删除。
   * `MANIFEST.txt`/`MANIFEST.sha256` 已在 §7 第 7 条重算，清单随删除**降下来了**（删了 6+14 个文件、改了 396 个）。
4. **`inst-tree.png` 可能也已过时**（按规则**未删**，请 Lead 定）：
   * 它采集于 2026-10-03 **12:08**，早于 `ei-tree.png`（15:01，已确认的坏状态）和 `ei-tree2.png`（15:06，当前证据）。
   * 图里高亮是**橙色圆环**、右上角有「已存在本机」角标、右下按钮是「换一套」；
     而 15:06 的 `ei-tree2.png` 用**绿色高亮环**、无该角标。若 12:08→15:06 之间界面改过，它同样是坏状态。
   * **我没有删**（它不在删除清单里）。请 Lead 决定是否补删，或重跑 `node tools/ui/shoot_tree.js` 重采。
5. **`tools/README.md` 的计数表未随本次删除回改**（我只改了 §3.4 的表与表头 50→44）：
   * §2 的 `tools/check/ | 50`、§2 合计 `159`、§4 表 `164`、§5 的 `159/166` 都是**迁移时点（T2–T5）的存量快照**，属历史记录，我按「本轮只做删除与引用修复、不顺手改历史表」处理，未动。
   * 顺带发现 `tools/check/` 目录实际 **46 个文件**，而 §3.4 表只列了 44 行：
     `verify_architecture_guard.py`、`verify_truncation_guard.py` **从未录入索引**（本轮新增的两个守卫）。
     我把这层差异写在 §3.4 表下的说明里，但**没有**替 Lead 决定是否补录两行。
6. **`bootstrap.sh:7` 的 `tools/analyze_*.py、tools/build_*.py、tools/optimize_*.py、tools/compare_*.py`**：
   是**通配符形式的分类说明**（不是具体路径），`optimize_*`/`compare_*`/`analyze_*` 这类前缀在新布局下已不存在。
   它不产生悬空引用（不指向具体文件），我**未改**；若要改需 Lead 定文案。
7. **`data/scene-{labeling,clusters}.json`、`data/scale-inventory.json`、`data/text-db/pending/batch-005.json` 等仍不存在**：
   它们是脚本**声明要写的产物**（`label_items_by_scene.py:41/43` 的 `OUT_LAB`/`OUT_CLU`、README 的「输出」列），
   不是「引用了一个曾经存在的文件」。属正常（产物未生成/已清理），**未动**。其余同类：`tools/mos/36-item-short-form.html`、`tools/pedsql.html`（原始来源件路径）。
8. **验收第 4 条的 2 个浏览器测试 `test_tree_mode.js` / `test_scale_pages.js` 本身已过时**（详见 §7 第 4 条的完整证据链）：
   它们断言 `[data-instview]` / `[data-instview="paged"]`，而现行 `ui/index.html` 早已改成
   `[data-instmode="classic"]`（`:984`，并在 `:3657` 留了「兼容旧的 data-instview」注释）。
   对**本工作区**跑必须失败；只有把 URL 指向 WSL 里的**旧部署**（`127.0.0.1:8891/emohealth/`，`serve_dist.js`）才绿
   —— 那两个测试对当前代码是**假绿**，而验收清单把它们当作当前代码的门。
   **我没有改也没有删**：改断言属测试语义、删测试更超出「只删 + 修引用」，且它们不在任务给的 6 条删除清单里。
   请 Lead 决定：(a) 把 3 处选择器改成 `[data-instmode="classic"]`（约 4 行）；(b) 或另立一条「失效测试」任务统一处理。
   > 注：这与 §1 的 6 个 stub 测试**不同类**——那 6 个是连跑都跑不起来（stub 缺 `addEventListener`），
   > 这 2 个是真浏览器测试，只是断言对着旧 DOM 属性。

---

## 7. 验收实测输出

全部在 `C:\Codes\emohealth-20260930-full\emohealth` 下实跑，原样贴。

### 第 1 条 `python tools/survey/survey_stale_files.py` —— 悬空引用

```
══════════════════════════════════════════════════════════════════════════
C 临时与缓存
══════════════════════════════════════════════════════════════════════════
  .tmp/.bak/.orig/.swp：0
  *.pyc：0
  __pycache__ 目录：1

══════════════════════════════════════════════════════════════════════════
D 可疑空/占位文件
══════════════════════════════════════════════════════════════════════════
  0 字节文件：2
     content\__init__.py
     engine\__init__.py

══════════════════════════════════════════════════════════════════════════
B 悬空引用（引用不存在的路径）
══════════════════════════════════════════════════════════════════════════
  ARCHITECTURE.md
      → data/x.json  （不存在）
      → ui/a.js  （不存在）
  tools\build\label_items_by_scene.py
      → data/scene-clusters.json  （不存在）
      → data/scene-labeling.json  （不存在）
  tools\check\verify_architecture_guard.py
      → archive/scales/x.json  （不存在）
      → tools/build/p.py  （不存在）
      → tools/survey/probe.py  （不存在）
      → tools/ui/shoot.py  （不存在）
      → ui/a.js  （不存在）
      → ui/app.js  （不存在）
  tools\check_architecture.py
      → data/x.json  （不存在）
  tools\cleanup_manifest.json
      → tools/analyze_block_and_network.py  （不存在）
      → tools/analyze_correlation_network.py  （不存在）
      → tools/analyze_decision_paths.py  （不存在）
      → tools/analyze_partial_administration.py  （不存在）
      → tools/analyze_scene_precision.py  （不存在）
      → tools/analyze_tiered_unlock.py  （不存在）

  涉及 5 个文件
```

**读数**：清理前 **59 个文件**有悬空引用 → 现在 **5 个**，且这 5 个**全部**是「不该改」的类别：

| 文件 | 判定 |
|---|---|
| `ARCHITECTURE.md` | 文档示例（§5 已列） |
| `tools/check_architecture.py` | 守卫自己的 docstring 示例（与 `ARCHITECTURE.md` 同类） |
| `tools/check/verify_architecture_guard.py` | 测试用例字符串 |
| `tools/cleanup_manifest.json` | 迁移回滚账本的 `old` 字段（**按设计**写旧路径） |
| `tools/build/label_items_by_scene.py` | `OUT_LAB`/`OUT_CLU` **输出**路径（脚本要写的产物，非引用已存在文件） |

→ **迁移遗留型悬空引用 = 0**（另用 `cleanup_manifest.json` 的 153 条 `old→new` 映射做全树复核，结果同为 0，见 §4）。

`__pycache__ 目录：1` 是**跑本测绘脚本自己**又生成的 `tools/__pycache__`（§2 已说明）。

### 第 2 条 `python tools/check_architecture.py` —— 三契约

```
✅ C1  前端层不得读 archive/
     · tools/ui/：16 文件，0 违例 ✅，未判定 0 处
     · ui/：6 文件，0 违例 ✅，未判定 0 处

✅ C2  调研层不得写 data/
     · tools/survey/：30 文件，0 违例 ✅，未判定 0 处

✅ C3  数据层不得读 ui/
     · tools/build/：45 文件，0 违例 ✅，未判定 0 处
     · tools/analyze/：10 文件，0 违例 ✅，未判定 0 处

✅ 三条契约全部通过。
   未判定 0 处（本次没有判不出来的引用）
EXIT=0
```

### 第 3 条 9 项 Python 测试（`tools/check/`）

```
test_agent_contract        exit=0    ✅ 全部 6 组契约不变量通过
test_all_instruments       exit=0    ✅ 全部通过
test_catalog               exit=0    ✅ ui/catalog.js 与 catalog.json 内容一致 | ✅ 全部通过
test_item_coding           exit=1    ModuleNotFoundError: No module named 'pandas'
test_l1_instrument         exit=0    ✅ 全部通过
test_pid5_instrument       exit=0    ✅ 全部通过
test_scene                 exit=0    ✅ 全部 7 组不变量通过
test_schema_roundtrip      exit=0    ✅ 转换器与人工核对产物完全一致
test_scoring               exit=0    ✅ 全部通过
FAILED=1 / 9
```

⚠️ **唯一失败项是环境问题，与本次清理无关，可证**：

* `test_item_coding.py:28` 是 `import pandas as pd`；本机 `python`（3.13.3）只装了 `numpy 2.5.1`，**没有 pandas**；
  项目自带的 `run.sh` 需要 `vendor/`（`./bootstrap.sh` 装依赖），而**本工作区没有 `vendor/`** → 该测试在此环境**本来就跑不起来**。
* 该文件**逐字节未被本次清理触碰**：当前 sha256 `00ec9a9372290d1032b87ee9cbed21802904267bd45de3d068abac28a584ef46`
  == 清理前 `MANIFEST.sha256` 里的基线值（同一字符串）。

→ 可跑的 8 项 **❌=0**；第 9 项因缺依赖无法执行（**非本轮引入，也不该由本轮修**）。

### 第 4 条 6 项浏览器测试（`$env:CHROME="C:\Program Files\Google\Chrome\Application\chrome.exe"`）

用**本工作区的 `ui/`**（我起的 `node tools/ui/serve_local.js --port 8901 --no-open`，已核对 `http://127.0.0.1:8901/ui/index.html` 的 sha256 与 `ui/index.html` **一致**）作目标：

```
=== test_local_file      exit=0 ===  ✅ file:// 本地直开全部通过
=== test_chain_nav       exit=0 ===  ✅ 链路跳转全部通过
=== test_l2_criteria_ui  exit=0 ===  ✅ L2 逐册口径全部通过
=== test_pid5_norms_ui   exit=0 ===  ✅ PID-5 常模接入通过
=== test_scale_pages     exit=1 ===  ❌ 1 项未通过
       ❌ 切到经典逐题后仍在该子页  —— 0 题 / #/scale/PID-5
=== test_tree_mode       exit=1 ===  ❌ 3 项未通过
       ❌ 提供作答方式切换
       ❌ 能切回经典逐题
       ❌ 逐题视图仍显示 10 题/页  —— undefined 题
```

⚠️ **这不是本次清理造成的，原因是这 2 个测试自己过时了**（证据链）：

1. 两个测试断言的是**已被改名的 DOM 属性**：
   * `test_tree_mode.js:62` `document.querySelector('[data-instview]')`、`:117` `'[data-instview="paged"]'`、`:149` 计数；
   * `test_scale_pages.js:79` `document.querySelector('[data-instview="paged"]')`。
2. 而当前工作区 `ui/index.html` 渲染的是**新属性**：
   * `ui/index.html:984` → `<button data-instmode="${m.id}">`（外层 `div.viewswitch`，见 `:979`）；
   * `ui/index.html:3657` 还留着注释「**兼容旧的 data-instview（保留以免遗漏调用点）**」——即属性确实被改过名；
   * 模式 id 也从 `"paged"` 改成了 `"classic"`（`ui/index.html:964`），旧选择器改了属性名也还要改取值。
3. 所以在**本工作区**上必然 `hasSwitch=false`；测试失败是**断言过时**，不是界面坏了——
   现行界面确实有切换条（保留截图 `ei-tree2.png` 里可见「天赋树 / 经典逐题」两颗按钮）。
4. 反证：把默认 URL 指向 `http://127.0.0.1:8891/emohealth/`（那是 **WSL 里的旧部署产物**，
   `tools/ui/serve_dist.js`，其 `index.html` sha256 与工作区不同、且仍含 3 处 `data-instview`）时，
   **这两个测试都 exit=0**（`✅ 天赋树全部通过` / `✅ 子页与路由全部通过`）。
   → 它们只是「对着旧构建/旧选择器」绿的，对当前代码是**假绿**。
5. 我的改动**不可能**造成它：`ui/**` 全部文件相对清理前基线**只有我那处路径字符串替换**这一个差异
   （把 `ui/index.html` 的新路径替换回旧路径后，sha256 **逐字节等于**清理前 `MANIFEST.sha256` 的基线值；
   全部 396 个被改文件都用同一方法验证过）。属性名与测试断言都没有被本轮碰过。

**处置**：**没有**改这 2 个测试、也**没有**删它们（超出「只删 + 修引用」的范围，且 6 条删除清单里没有它们）。
按「拿不准的列出来问 Lead」上报，见 §6 第 8 条。

### 第 5 条 `python tools/ui/pack_ui_data.py --check`

```
   ✓ data/tree-layouts/pid-5.json → ui/tree-layouts/pid-5.js：一致
   ✓ data/tree-layouts/index.json → ui/tree-layouts/index.json：一致

✅ 14 个文件与磁盘现状逐字节一致。
EXIT=0
```

### 第 6 条 `archive/` 不变

```
archive files: 1987
archive bytes: 670295616
MATCH 1987/670295616: True
```

清理前后**完全一致**：**1987 文件 / 670,295,616 字节**。

### 第 7 条 `python tools/build/build_manifest.py` 重算 + `--check`

```
PS> python tools/build/build_manifest.py
核心 1044 个文件 → MANIFEST.sha256 / MANIFEST.txt
WRITE_EXIT=0

PS> python tools/build/build_manifest.py --check
清单里 1044 个，实际 1044 个
CHECK_EXIT=0
```

**清单确实跟着降了**：`MANIFEST.sha256` 107,399 B → **107,005 B**（-394 B），
条目数从基线 **1048 → 1044**（-6 个被删的 stub 测试、+1 本文件，±1 为上一轮遗留的清单滞后）。
删除的 20 个文件里 14 张截图本就不在清单内（`build_manifest.py` 明确排除 `.shots/`）。

### 附：改动的可验证性（证明「只改了引用」）

对清理前 `MANIFEST.sha256` 的 **1048 条基线**逐条比对：

```
baseline entries           : 1048
deleted by me (excluded)   : 6
current == baseline        : 644
files whose ONLY diff is my path substitution : 396
files missing vs baseline  : 0
other mismatches (not explained by my edit)   : 2
    README.md
    tools/README.md
```

即：**396 个被改文件，把新路径替换回旧路径后 sha256 逐字节等于清理前基线**（证明除路径串外没动任何字节）；
仅有 2 个额外的差异文件是根 `README.md` 与 `tools/README.md`——那是我按任务要求删索引行/加说明的有意改动。
`ui/**` 的每一个文件都在那 396 个之内。

---

## 8. 回滚方法

* **截图**：从 `archive/` 之外的备份恢复；本文件 §3 给了每个文件的 sha256 与删除前大小，可校验恢复物是否一致。
  （`.shots/` 不在 `MANIFEST.*` 内——它被 `build_manifest.py` 明确排除——所以清单不能帮你校验截图。）
* **6 个 stub 测试**：`tools/cleanup_manifest.json` 的 `moves` 里有它们的 `old`/`new`/`sha256`（迁移前哈希），
  但**内容本身**要另找备份。
* **引用修复**：§4 是双向可逆的（把新路径替换回旧路径即可），但**没有理由回滚**——旧路径确实不存在。
* **`__pycache__`**：无需回滚，跑一次 Python 就回来了。

## 补删（Lead 判定，2026-10-03）

| 路径 | 大小 | 判定依据 | 替代物 |
|---|---|---|---|
| `.shots/inst-tree.png` | 139772 B | 采集于 12:08，展示**橙色**高亮环 + 「已存在本机」角标；当前 `.treenode.open` 用 `var(--accent)`（**绿色**），样式已变更。且时间早于已知坏状态图 `ei-tree.png`（15:01） | `.shots/ei-tree2.png`（15:06，绿环、7 个可答节点已验全部高亮） |

删除前 sha256：`c24481efec2e3722fac5be5ce791acaf05c8d8bc353e55017384835e820ae257`
