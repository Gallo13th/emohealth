#!/usr/bin/env python3
"""把自动录入索引时留下的「待补写职责」占位文字，替换成真实职责。

`autofill_readme_index.py` 只能发现「哪个文件没录入」，说不出它干什么
（那要求读懂脚本）。所以它留占位并明确提示。本脚本把这些条目补成真实描述。

值可以只给职责（字符串），也可以给 ``(职责, 输入, 输出)`` 三元组——
后者的输入/输出列不必再写「见脚本 docstring」。
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, r"C:\Codes\emohealth-20260930-full\emohealth\tools")
from _root import find_root  # noqa: E402
ROOT = str(find_root())
MD = os.path.join(ROOT, "tools", "README.md")

REAL = {
    "survey_capability_gaps.py":
        "测绘三套核心量表相对大五人格的**数据能力缺口**（A 可直接靠齐 / "
        "B 需文献补数据 / C 不适用），决定调研方向",
    "build_inference_data.py":
        "构建**量表级推断数据**（题→维度相关 + 维度间相关），让「基于相关性的"
        "允许缺失值推断」不再只认大五；带级别保护（不覆盖更高级别）",
    "build_pid5_psychometrics.py":
        "从 PID-5 的**公开原始作答**（CC-BY-4.0，N=2,148）自算题级参数："
        "220×30 题→维度相关、30×30 维度间相关、各 facet 的 partial 精度",
    "diagnose_pid5_alpha.py":
        "诊断 PID-5 的 α 与已发表值（0.87）的差距：逐 facet 列 α 并标出拉低均值者",
    "autofill_readme_index.py":
        "把**未录入索引**的脚本自动补进本索引（自动发现、按字母序、**幂等**）；"
        "占位职责需人工补写（见本条目）",
    # ── 答题界面（D117）──
    # 历史：D115 有 `test_inference_ondemand.js` / `test_pid5_inference_ui.js`（推断通用化），
    #       D116 随「只留最小 UI」删掉，并加过 `test_ui_rolled_back.js`（反向断言推断已撤下）。
    #       D117 用户明确要求「完善答题界面：题面四字段 + 各指标预测与置信度」，
    #       推断消费被**按新口径重新接回**，故 `test_ui_rolled_back.js` 已删除，
    #       由下面这条覆盖（它同时断言「按需加载没被破坏」）。
    "test_item_fields_inference_ui.js": (
        "答题界面（D117/D118）：题面四字段（`text_en`/`text_zh`/`options[].meaning_zh`/"
        "`notes_zh`）同时在 DOM 且与结构化数据逐字一致、`project_editorial`「项目自撰」"
        "只在默认折叠的「选项说明的出处」里可查；各维度的估计+可信程度遵守硬规则"
        "（本维度一题未答→不出现估计与可信程度）、`data-r`/`data-pred` 与 "
        "`ui/lib/inference.js` 逐值一致、默认文案仍说清「这是估计，不是已经测出来的得分」；"
        "首页不加载三个按需数据包",
        "`ui/index.html`、`ui/inference/*.js`、`ui/items-structured/*.js`、`ui/lib/inference.js`（CDP，`file://`）",
        "stdout（退出码）"),
    # ── 用户端产品化（D118 / task-20；D119 / task-23 分级 + 删研究性措辞）──
    # 文件名按 Lead 2026-10-05 裁决⑥：它测的是「可见文案」，故不叫 *_ux。
    "test_user_visible_copy.js": (
        "**用户端默认视野 + 三档提醒分级**：用「用户实际看到的文字」（关闭的 `<details>` 只算 "
        "summary、`display:none`/`visibility:hidden` 不算、SVG `<title>` 不算）扫描开发者/审阅者"
        "关键词（`conf_r`/门槛/耗时/utility/信息增益/`project_editorial`/手册原文/项目自撰/推论/"
        "判据/算式/口径/出处/已核查/推算 … 必须 0 命中）；断言用户要的东西仍在、**诚实性文案仍在"
        "默认视野**、打开「依据」后仍可查；硬规则仍成立（含展开「其余 N 个维度」后仍无 "
        "`data-r`/`data-pred`）；量表级每册 1 次、**同一把尺子连续 10 题锚点说明只 1 次**、"
        "选项级不重复上级句子；`scale_guides[*].source` 等内部字段整份 DOM 都不出现；"
        "页脚可见一行授权署名；并打印默认视野清单",
        "`ui/index.html`、`ui/inference/*.js`、`ui/items-structured/*.js`（CDP，`file://`）",
        "stdout（退出码）"),
}

md = open(MD, encoding="utf-8").read()
n = 0
for name, spec in REAL.items():
    duty, ins, outs = (spec if isinstance(spec, tuple)
                       else (spec, "见脚本 docstring", "见脚本 docstring"))
    old = (f"| `{name}` | （**待补写职责**——自动录入，请打开脚本读 docstring "
           f"后改这里） | 见脚本 | 见脚本 |")
    new = f"| `{name}` | {duty} | {ins} | {outs} |"
    if old in md:
        md = md.replace(old, new)
        n += 1
        print(f"  ✓ {name}")
    else:
        print(f"  · {name}（占位已不在，可能已被改过）")
open(MD, "w", encoding="utf-8").write(md)
print(f"\n替换 {n} 条")
