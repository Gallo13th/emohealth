#!/usr/bin/env python3
"""守卫：**非字面表达不得直译**——习语被逐字翻成中文时要报错（task-40）。

为什么要有这条
==============
用户 2026-10-07 指出：
> "Step on someone's toes" is an idiom meaning to offend, upset, or intrude on someone…
> **对于俚语不要直译。**

实测缺陷：`pid5_073`
  EN: You need to step on some toes to get what you want in life.
  ZH: 在生活中，你必须踩到一些人的脚趾，才能得到自己想要的。   ← 逐字直译，中文无此说法
更刺眼的是该条**自己的 note 就写着「非字面义」**——译者知道是修辞，却仍照字面翻了；
而 2026-10-04 那轮 337 条复核也**放过了它**，根因是判据里没有「习语不得直译」。

判据设计（**宁可窄而准，不要宽而假红**）
========================================
只用一张**显式对照表**：只有当**英文命中某条习语**、且**该条中译里出现了这条习语的
字面内容词**时才报错。不靠「像不像习语」的模糊判断，也不做全库通用语义分析。
  · 英文没命中该习语 → 完全不检查（不会因为中文里出现「脚趾」而误红）；
  · 英文命中了，但中译已按含义译出（不含字面词）→ 通过（如 `on edge` → 「坐立不安」）；
  · 英文命中了，中译里仍有字面内容词 → **报错**。

用法：`python tools/check/check_idiom_translation.py`（有问题 exit 1）
      `python tools/check/check_idiom_translation.py --stats` 只看统计
"""

from __future__ import annotations

import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root, force_utf8_io  # noqa: E402

ROOT = find_root()
DB = os.path.join(ROOT, "data", "text-db", "text-db.json")

#: (英文习语正则, 该习语的**字面内容词**正则, 含义说明)
#: 只列**真的会出现或已出现**的习语；表保持可读、可增补。
IDIOMS: list[tuple[str, str, str]] = [
    (r"step on (?:some|someone's|any|a few) toes?",
     r"脚趾|踩(?:到|着)?.{0,4}脚",
     "冒犯/越界/为达目的损害他人利益"),
    (r"\btoot (?:my|your|his|her|one's) own horn\b",
     r"吹(?:自己)?.{0,2}(?:号|喇叭)|号角",
     "自我吹嘘"),
    (r"\bcold fish\b",
     r"冷(?:的)?鱼",
     "情感冷淡、缺乏温情的人"),
    (r"\braw deal\b",
     r"生的(?:交易|买卖)|未加工",
     "不公平的待遇、被亏待"),
    (r"\bdown in the dumps\b",
     r"垃圾(?:场|堆)|倒垃圾",
     "情绪低落"),
    (r"\bon edge\b",
     r"边缘上|在边上",
     "紧张不安、坐立不安"),
    (r"\bzone[sd]? out\b|\bzoning out\b",
     r"区域外|划出去",
     "走神、出神"),
    (r"\bkeep (?:my|your) cool\b|\blose (?:my|your) cool\b",
     r"保持(?:凉|冷)\b|丢掉(?:凉|冷)",
     "保持冷静 / 失去冷静"),
    (r"\bhave a sharp tongue\b",
     r"锋利的舌(?:头)?",
     "说话刻薄"),
    (r"\bhold a grudge\b",
     r"(?:拿|握)着(?:怨恨|怨气)",
     "记仇"),
    (r"\bturn (?:my|your) back on\b",
     r"把背(?:转向|对着)",
     "背弃、置之不理"),
    (r"\btip of the iceberg\b",
     r"冰山(?:的)?(?:尖端|一角)",
     "问题的显见部分（`冰山一角` 是中文对应说法，可用）"),
    (r"\bin the same boat\b",
     r"同(?:一)?(?:条|艘)船",
     "处境相同"),
    (r"\bwalk(?:ing)? on eggshells\b",
     r"走在蛋壳上|踩(?:在)?蛋壳",
     "小心翼翼、如履薄冰"),
    (r"\bmake a mountain out of a molehill\b",
     r"把鼹鼠丘.{0,6}(?:山)|鼹鼠丘",
     "小题大做"),
    (r"\bspill the beans\b",
     r"洒(?:了)?豆子|把豆子",
     "泄密、说漏嘴"),
    (r"\bbeat around the bush\b",
     r"绕着(?:灌木)?.{0,3}丛|敲打灌木",
     "拐弯抹角"),
    (r"\beye for an eye\b",
     r"^(?!.*以眼还眼).*$",          # 中文对应说法就是「以眼还眼」，允许
     "以眼还眼（中文有对应说法，不算直译）"),
]

#: 已确认的直译**黑名单**（与上面表互补：这条不看英文，直接禁）。
#: 用于「已经踩过一次」的表达，防回归。
BLACKLIST: list[tuple[str, str]] = [
    (r"踩(?:到|着)?.{0,6}脚趾", "`step on someone's toes` 的逐字直译（2026-10-07 已更正为「得罪一些人」）"),
]


def main() -> int:
    # UTF-8 兜底：唯一实现在 tools/_root.py。Windows 默认控制台是 GBK，下面的 ✅/❌/✗
    # 会让 print 抛 UnicodeEncodeError —— 崩溃点在**输出结果那一行**，退出码 1 与
    # 「真的发现习语被直译」不可区分，于是完好的守卫在默认控制台上永远假装变红。
    #
    # 这一类的**实测崩溃**已多次发生（本条是最近一例）；有记录的例子：
    #   pack_ui_data / check_pack_freshness（见 check_cli_encoding.py 的 docstring）
    #   check_architecture / check_text_db / check_item_structured /
    #   check_index_completeness / build_descriptions / check_descriptions
    #   （由 converge-pack 的 check_cli_encoding 静态+运行时实跑抓到）
    #   check_size_regression / check_readme_dups / check_scene_sourcing /
    #   check_time_window / check_idiom_translation（本条）
    # ⚠️ `verify_archive.py` **不在**此列——它只印 ASCII JSON，当时并未崩，
    #    是**预防性**补的兜底。把"预防"写成"已崩"就是不实陈述。
    # 不带总数：总数要能复核，追这个数字的地方是 check_cli_encoding.py（静态扫 + 运行时）。
    force_utf8_io()
    stats_only = "--stats" in sys.argv
    if not os.path.exists(DB):
        print(f"✗ 找不到 {os.path.relpath(DB, ROOT)}")
        return 1
    entries = json.load(io.open(DB, encoding="utf-8"))["entries"]

    bad: list[str] = []
    hit_idioms = 0
    checked = 0
    for k, v in sorted(entries.items()):
        zh = v.get("zh") or ""
        if not zh:
            continue
        checked += 1
        en = v.get("en") or ""
        for en_re, zh_re, meaning in IDIOMS:
            if not re.search(en_re, en, re.I):
                continue
            hit_idioms += 1
            m = re.search(zh_re, zh)
            if m:
                bad.append(f"习语被直译：EN 命中 /{en_re}/，中译里出现字面词 {m.group(0)!r}"
                           f"（含义应为「{meaning}」）\n      EN: {en[:80]}\n      ZH: {zh[:80]}")
        for zh_re, why in BLACKLIST:
            m = re.search(zh_re, zh)
            if m:
                bad.append(f"命中直译黑名单 {m.group(0)!r}：{why}\n      ZH: {zh[:80]}")

    print(f"扫 {checked} 条有中译的条目；英文命中习语表 {hit_idioms} 处")
    if stats_only:
        return 0
    for b in bad:
        print("  ❌ " + b)
    if bad:
        print(f"\n❌ {len(bad)} 处非字面表达被直译")
        return 1
    print("✅ 习语/比喻未被直译（命中习语表的条目都已按含义译出）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
