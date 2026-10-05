#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 Pass 1 的自由标签**人工归并**成正式的情景分类法。

为什么不复用 Pass 2：小模型（Qwen2.5-14B）在「自由标注」这一步表现很好
（93 个标签，区分度合理），但在「归并成分类法」这一步明显失手——
它把 728 个标签塞进「其他情境」（原始标签总共只有 93 个），
并把「遇到突发事件」「遇到挫折」归进了「决策」。

**人工归并比它准，且只需做一次。** 归并依据：情景必须让用户一眼看懂，
且描述的是**可观察的行为场景**，不是抽象特质。

输入：`data/_scene_cache/pass1.json`（每题一个自由标签）
输出：`data/scene-taxonomy.json`（分类法 + 每题归属 + 质检）
"""
from __future__ import annotations

import glob
import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
P1 = os.path.join(ROOT, "data/_scene_cache/pass1.json")
CANON = os.path.join(ROOT, "data/ipip-neo-300.json")
OUT = os.path.join(ROOT, "data/scene-taxonomy.json")

# ────────────────────────────────── 人工归并：93 个自由标签 → 14 个情景
MAP: dict[str, str] = {}
for raw, scene in [
    # 一般性——不指向特定情境
    ("一般性", "一般性"),

    # 独处
    ("独处时", "独处"), ("独自用餐", "独处"), ("独自做事", "独处"),
    ("安静的环境", "独处"), ("独自做决定", "独处"),

    # 热闹场合
    ("和朋友聚会", "热闹场合"), ("参加大型聚会", "热闹场合"), ("和朋友玩耍", "热闹场合"),
    ("和朋友在一起", "热闹场合"), ("社交聚会", "热闹场合"), ("人多的场合", "热闹场合"),
    ("身处喧闹的人群", "热闹场合"), ("和其他人待在一起", "热闹场合"),

    # 不太熟的人
    ("和人交往时", "不太熟的人"), ("和人交往", "不太熟的人"), ("和人交流时", "不太熟的人"),
    ("和人交往初期", "不太熟的人"), ("和别人相处时", "不太熟的人"),
    ("陌生场合", "不太熟的人"), ("新环境适应", "不太熟的人"), ("复杂社交情境", "不太熟的人"),

    # 任务与学业
    ("工作接到任务", "任务与学业"), ("工作时", "任务与学业"), ("忙碌工作中", "任务与学业"),
    ("接到任务时", "任务与学业"), ("制定计划时", "任务与学业"), ("时间紧迫时", "任务与学业"),
    ("面对紧急任务", "任务与学业"), ("解决难题时", "任务与学业"), ("解决问题时", "任务与学业"),
    ("遇到难题时", "任务与学业"), ("学习时", "任务与学业"), ("学习或讨论时", "任务与学业"),
    ("工作或学习中", "任务与学业"), ("工作或学习时", "任务与学业"),
    ("和人交流工作中", "任务与学业"),

    # 冲突与竞争
    ("和人起冲突", "冲突与竞争"), ("和人谈判", "冲突与竞争"), ("职场竞争", "冲突与竞争"),

    # 助人与共情
    ("帮助他人时", "助人与共情"), ("看到他人遭遇困难", "助人与共情"),
    ("看到他人难过", "助人与共情"), ("遇到流浪汉", "助人与共情"),
    ("需要帮助时", "助人与共情"),

    # 压力与挫折
    ("压力大时", "压力与挫折"), ("遇到突发事件", "压力与挫折"), ("紧急情况", "压力与挫折"),
    ("遇到挫折时", "压力与挫折"), ("遇到重大挫折", "压力与挫折"),
    ("遇到失败后", "压力与挫折"), ("面对困难时", "压力与挫折"),

    # 做决定与自我控制
    ("面对诱惑时", "做决定与自我控制"), ("冲动时", "做决定与自我控制"),
    ("拖延时", "做决定与自我控制"), ("拖延决策时", "做决定与自我控制"),
    ("做决定时", "做决定与自我控制"),

    # 观念与立场
    ("和人讨论时", "观念与立场"), ("和人讨论哲学", "观念与立场"),
    ("讨论法律问题", "观念与立场"), ("宗教讨论", "观念与立场"),
    ("讨论税收政策", "观念与立场"), ("讨论犯罪问题", "观念与立场"),
    ("和人讨论法律", "观念与立场"),
    ("参加选举投票", "观念与立场"), ("参与选举投票", "观念与立场"),
    ("奏国歌时", "观念与立场"),

    # 日常与规律
    ("处理日常事务", "日常与规律"), ("整理房间", "日常与规律"), ("购物时", "日常与规律"),
    ("户外散步", "日常与规律"), ("闲暇时间", "日常与规律"), ("闲暇时光", "日常与规律"),
    ("看演出时", "日常与规律"),

    # 新鲜与冒险
    ("寻求刺激时", "新鲜与冒险"), ("尝试新鲜事物", "新鲜与冒险"),
    ("尝试新事物", "新鲜与冒险"), ("尝试新鲜事物时", "新鲜与冒险"),
    ("尝试新食物时", "新鲜与冒险"), ("冒险时", "新鲜与冒险"), ("旅行时", "新鲜与冒险"),

    # 义务与规矩
    ("报税时", "义务与规矩"), ("履行约定时", "义务与规矩"), ("和人约定后", "义务与规矩"),
    ("考试作弊", "义务与规矩"), ("处理财务事务", "义务与规矩"),
    ("遵守规章制度", "义务与规矩"), ("规避监管时", "义务与规矩"),
    ("利用他人达成目的", "义务与规矩"), ("依赖他人时", "义务与规矩"),

    # 团队与领导
    ("领导开会", "团队与领导"), ("团队合作时", "团队与领导"), ("和人合作时", "团队与领导"),
]:
    MAP[raw] = scene

# 决策 D33：尾部情景（题数 <10）直接并入「杂项」。
# 依据：`data/scene-precision.json` —— 这 7 个情景单独完成时
# 最多只能把 2 个 facet 推到 r≥0.90，达不到可承诺的精度。
TAIL = {"义务与规矩", "新鲜与冒险", "日常与规律", "压力与挫折",
        "做决定与自我控制", "助人与共情", "团队与领导"}

SCENE_ZH = {
    "杂项": "其他各种场合",
    "一般性": "不分场合的你自己",
    "独处": "独处的时候",
    "热闹场合": "热闹的聚会里",
    "不太熟的人": "和不太熟的人打交道",
    "任务与学业": "有任务要做的时候",
    "冲突与竞争": "和人意见不合、有竞争时",
    "助人与共情": "别人需要帮助时",
    "压力与挫折": "出状况、压力大的时候",
    "做决定与自我控制": "要做决定、又容易拖延的时候",
    "观念与立场": "聊到社会话题和立场时",
    "日常与规律": "日常生活与习惯",
    "新鲜与冒险": "尝试新鲜事物时",
    "义务与规矩": "该守规矩、该守信的时候",
    "团队与领导": "和人一起做事、需要有人带头时",
}


# ────────────────────────────── 逐条人工复核后的修正（D34）
# 系统性误标：「提到他人」≠「和陌生人相处」。模型把大量**一般性倾向题**
# （如「关心他人」「我会实话实说」）归进了具体社交情景。逐条复核后修正。
# 另一类：把**内部状态题**（如「情绪起伏很大」）归进了「冲突」等情景。
CORRECTIONS: dict[int, tuple[str, str]] = {
    # 独处 → 一般性（这些是倾向陈述，不是「独处时」才会出现的行为）
    66:  ("一般性", "很容易心烦——情绪基调，不限于独处"),
    135: ("一般性", "听从良心——道德取向，不指向情境"),
    174: ("一般性", "觉得自己很了不起——自我评价，不指向情境"),
    197: ("一般性", "喜欢不慌不忙——节奏偏好，不指向情境"),
    204: ("一般性", "对自己评价很高——自我评价，不指向情境"),
    257: ("一般性", "按自己的节奏——节奏偏好，不指向情境"),
    284: ("一般性", "不愿为他人花时间——对他人的态度，不指向情境"),
    # 独处 → 不太熟的人（涉及他人的社交感受）
    76:  ("不太熟的人", "感觉自己很难接近别人——明确涉及与他人接触"),
    106: ("不太熟的人", "害怕引起他人注意——社交情境中的不适"),
    152: ("不太熟的人", "别人很难了解我——关系中的自我表露"),
    # 独处 → 冲突与竞争（坚持己见属于冲突情境）
    90:  ("冲突与竞争", "坚持自己选定的路——面对分歧时的坚持"),
    # 独处 → 热闹场合（在群体中的位置感，且为反向题，有助该情景的键平衡）
    192: ("热闹场合", "待在幕后、不出头——群体中的位置选择"),
    # 不太熟的人 → 一般性（泛化的待人倾向）
    43:  ("一般性", "感受到他人情绪——共情能力，不指向情境"),
    102: ("一般性", "喜欢影响别人——影响倾向，不指向情境"),
    105: ("一般性", "我会实话实说——诚信取向，不指向情境"),
    194: ("一般性", "对他人感受漠不关心——待人倾向，不指向情境"),
    219: ("一般性", "会假装关心别人——待人方式，不指向情境"),
    264: ("一般性", "吹嘘自己的美德——自我呈现，不指向情境"),
    # 冲突与竞争 → 一般性（内部状态或不指向冲突）
    131: ("一般性", "情绪起伏很大——情绪稳定性，不指向冲突"),
    165: ("一般性", "破坏规则——规则取向，不指向冲突"),
    285: ("一般性", "会歪曲事实——诚信取向，不指向冲突"),
    # 热闹场合 → 一般性
    104: ("一般性", "关心他人——泛化的待人倾向，不限于聚会"),
}


def main() -> int:
    l1 = json.load(open(P1, encoding="utf-8"))
    canon = json.load(open(CANON, encoding="utf-8"))
    by_order = {i["order"]: i for i in canon["items"]}

    zh: dict[int, str] = {}
    for f in glob.glob(os.path.join(ROOT, "content/facets/*.record.json")):
        for it in json.load(open(f, encoding="utf-8"))["items"]:
            zh[it["administration_order"]] = it["text_zh"]

    # 覆盖率检查：未映射的原始标签必须报出来，不能静默丢弃
    raw_counts = Counter(l1.values())
    unmapped = [k for k in raw_counts if k not in MAP]
    if unmapped:
        raise SystemExit(f"❌ 有未归并的原始标签：{unmapped}")

    items = {}
    for o_s, raw in l1.items():
        o = int(o_s)
        _orig = MAP[raw]
        items[str(o)] = {
            "scene_original": _orig,
            "merged_to_tail": _orig in TAIL,
            "order": o,
            "facet": by_order[o]["facet"],
            "text_zh": zh.get(o, by_order[o]["text"]),
            "text_en": by_order[o]["text"],
            "key": by_order[o]["key"],
            "free_label": raw,
            "scene": "杂项" if _orig in TAIL else _orig,
        }

    # 应用人工复核修正
    for o_s, (new_scene, why) in CORRECTIONS.items():
        k = str(o_s)
        if k in items:
            items[k]["scene_original"] = items[k]["scene"]
            items[k]["scene"] = new_scene
            items[k]["correction_reason"] = why

    scene_counts = Counter(v["scene"] for v in items.values())
    # 每个情景内的 facet 分布与键平衡
    quality = {}
    for sc in scene_counts:
        sub = [v for v in items.values() if v["scene"] == sc]
        fc = Counter(v["facet"] for v in sub)
        pos = sum(1 for v in sub if v["key"] > 0)
        quality[sc] = {
            "n_items": len(sub),
            "n_facets": len(fc),
            "max_per_facet": max(fc.values()),
            "facets_with_2plus": sum(1 for c in fc.values() if c >= 2),
            "forward": pos, "reverse": len(sub) - pos,
            "forward_pct": round(pos / len(sub) * 100, 1),
            "missing_facets": 30 - len(fc),
        }

    payload = {
        "method": "Pass1 由 Qwen2.5-14B 自由标注 → 人工归并（Pass2 的小模型归并质量不合格，已弃用）",
        "why_manual_merge": "小模型把 728 个标签塞进「其他情境」（原始标签总共 93 个），"
                            "并把「遇到突发事件」「遇到挫折」归入「决策」",
        "n_scenes": len(scene_counts),
        "scene_names_zh": SCENE_ZH,
        "scene_counts": dict(scene_counts.most_common()),
        "quality": quality,
        "raw_label_map": MAP,
        "manual_corrections": {str(k): {"to": v[0], "why": v[1]}
                               for k, v in CORRECTIONS.items()},
        "n_raw_labels": len(raw_counts),
        "items": items,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)

    print(f"自由标签 {len(raw_counts)} 个 → 归并为 {len(scene_counts)} 个情景")
    print(f"未映射的标签：{len(unmapped)}（应为 0）\n")
    print(f"{'情景':<14}{'题数':>5}{'覆盖facet':>9}{'单facet最多':>10}"
          f"{'正向%':>7}{'缺facet':>8}")
    print("-" * 60)
    for sc, n in scene_counts.most_common():
        q = quality[sc]
        print(f"{sc:<14}{n:>5}{q['n_facets']:>9}{q['max_per_facet']:>10}"
              f"{q['forward_pct']:>7.1f}{q['missing_facets']:>8}")
    print(f"\nwrote {os.path.relpath(OUT, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
