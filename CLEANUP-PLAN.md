# CLEANUP-PLAN.md — 工具目录清理（**历史记录，已完成**）

> **状态**：任务已完成（2026-10-03 ~ 10-04）。本文件保留**当时的口径与结果**，供追溯。
> **它不再是规则来源**：规则与计划以 [`PLAN.md`](PLAN.md)（R1–R4）为准；技术分层以
> [`ARCHITECTURE.md`](ARCHITECTURE.md) 为准；当前脚本清单以 [`tools/README.md`](tools/README.md) 为准。
>
> 同期历史账本：[`STALE-CLEANUP.md`](STALE-CLEANUP.md)（失效文件清理）、
> [`SCOPE-REDUCTION.md`](SCOPE-REDUCTION.md)（范围裁剪）。

**当时的执行结果**：153 个脚本移入 `tools/{survey,build,analyze,check,ui,legacy}/`；
记录见 `tools/cleanup_manifest.json`（`{old, new, sha256}`，回滚依据）。
保留平铺：`pdftext.py`、`build_scales.py`、`item_coding.py`（共享库）+
`survey_refs.py`、`survey_tools_layout.py`（测量工具）+ `package.sh`（运维）。
引用点集中修复 65 个文件 / 182 处。**§3 映射有一处按契约改判**：`build_tier_layout.py`
初筛归 build，但它读 `ui/*.js` 数据包、写 `ui/net-layout.js`，放 `tools/build/` 会实测违反 C3
→ 归 `tools/ui/`。定类原则：**初筛用前缀，定案用契约**（见 `tools/README.md` 文首）。

---

## 0. 现状测量（清理前，2026-10-03）

| 目录 | 文件 | 体积 | 性质 |
|---|---|---|---|
| `archive/` | 1987 | 639.2 MB | 证据链（原始 PDF / 数据集） |
| `data/` | 404 | 13.9 MB | 派生产物：26 个顶层 JSON + 5 个子目录，混杂 |
| `research/` | 48 | 3.1 MB | 调研报告 |
| `tools/` | 159 | 1.0 MB | 脚本，四类职责同层摆放 |
| `ui/` | 361 | 7.1 MB | 前端 + 342 个生成包 + 9 个树布局 |
| `content/` | 43 | 1.2 MB | 文案资产（脚手架、构念定义、翻译） |
| `engine/` | 11 | 0.1 MB | 运行时库（schema、scoring） |

`tools/` 的职责分布（`python tools/survey_tools_layout.py` 实测）：

```
survey 28   build 31   analyze 7   check 44   ui 15   other 34      （合计 159）
```

> 本文件初稿曾印 `survey 27`（各项合计 158），与实测差 1；**以工具实测的 28 为准**。

引用测量（`python tools/survey_refs.py`，扫描 569 个文件）：

```
159 个脚本：无引用 95 个、被引用 64 个（这是索引文档建立之前的基线）
```

---

## 3. 迁移映射（当时采用的口径）

| 子目录 | 收录规则 |
|---|---|
| `tools/survey/` | `fetch_*` `extract_*` `probe_*` `list_*` `survey_*` `crosscheck_*` `archive_*` |
| `tools/build/` | `build_*`（除 `build_ui_*`）`convert_*` `attach_*` `clean_*` `fix_*` `exclude_*` `batch_*` `collect_*` `export_*` `derive_*` `import_*` |
| `tools/analyze/` | `analyze_*` `optimize_*` `compute_*` `calibrate_*` `design_*` `compare_*` `diagnose_*` |
| `tools/check/` | `check_*` `test_*` `verify_*` `validate_*` `audit_*` |
| `tools/ui/` | `build_ui_*` `serve_*` `shoot_*` `sync_*` `dev_*` `render_*` |
| `tools/legacy/` | 一次性/演示脚本（`demo_*` 等） |
| `tools/`（**保留平铺**） | 被跨类大量引用的共享库：`pdftext.py`、`build_scales.py`、`item_coding.py` 等 |

**保留平铺的判据**：被 ≥3 个不同文件引用，或本身就是共享库。
逐文件的类别、职责、输入输出见 [`tools/README.md`](tools/README.md)。

---

## 4. 产出与验收（已完成）

* **产物**：`tools/cleanup_manifest.json`、`ARCHITECTURE.md`（三层契约 C1/C2/C3）、
  `tools/README.md`（脚本索引）、`tools/_root.py`（统一根定位）、
  `tools/check_architecture.py`（契约守卫）。
* **引用修复**：迁移后集中修引用点，`survey_refs.py` 复跑到无悬空引用；
  `content/**` 里遗留的旧路径由后续任务修正（见 `STALE-CLEANUP.md`）。
* **验收**：迁移前后 9 项 Python 测试逐项一致；`build_manifest --check` 通过；
  三条契约全绿；档案内容未被改动。
* 当时**只登记、未强改**的跨层动作见 `ARCHITECTURE.md` §5.1。

## 5. 当时的执行顺序（已完成，仅存档）

```
T0 写方案（本文件）              ✔
T1 加固基座：_root.py + 脚本索引   ✔
T2 迁移 survey 类                ✔
T3 迁移 build 类                 ✔
T4 迁移 analyze + ui + legacy 类  ✔
T5 集中修引用点 + 迁移 check 类    ✔
T6 架构守卫 check_architecture.py + ARCHITECTURE.md  ✔
T7 全量验收                      ✔
```
