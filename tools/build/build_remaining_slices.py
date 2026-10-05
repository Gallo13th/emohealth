#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""组装 selfdiscipline 与 activitylevel 两个 facet 的档案记录。

**为什么要用脚本组装而不是手写 JSON**：Phase 1 首个切片曾因手写 id 而出错——
`.osd` 的 id 反映分组顺序，与施测顺序无关，肉眼完全看不出。
本脚本从 `data/ipip-neo-300.json` 取 id/order/key/英文题面，
从自译表取中文，从常模产物取分带，**只把脚手架文本留作人工撰写**。

自译部分遵循 `PLAN.md` §2.4：以官方便携译本的既有用词为基准
（"拖很久才开始做一件事" → 复用"拖延/开始"的语体；"喜欢慢慢来" → 复用"慢慢来"）。
"""
from __future__ import annotations

import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
BANDS = ["Very High", "High", "Average", "Low", "Very Low"]


def load(name: str) -> dict:
    with open(os.path.join(ROOT, "data", name), encoding="utf-8") as fh:
        return json.load(fh)


def norm(s: str) -> str:
    return s.lower().replace(" ", "").replace("-", "").replace("_", "")


# ============================================================ 中文（自译 6 + 官方 4）
ZH = {
    # --- selfdiscipline ---
    "selfdiscipline": {
        25:  ("把该做的杂事马上做掉", "project_translation"),
        55:  ("我总是有所准备", "mandarin_baseline"),
        85:  ("立刻开始做事", "project_translation"),
        115: ("马上动手干活", "project_translation"),
        145: ("能执行自己制定的计划", "mandarin_baseline"),
        175: ("很难静下心来开始做事", "project_translation"),
        205: ("浪费时间", "mandarin_baseline"),
        235: ("需要别人推一把才能开始", "project_translation"),
        265: ("拖很久才开始做一件事", "mandarin_baseline"),
        295: ("把决定往后拖", "project_translation"),
    },
    # --- activitylevel ---
    "activitylevel": {
        17:  ("总是很忙碌", "mandarin_baseline"),
        47:  ("总是在奔波", "mandarin_baseline"),
        77:  ("我的闲暇时间非常充实", "mandarin_baseline"),
        107: ("能同时处理很多事情", "project_translation"),
        137: ("反应很快", "project_translation"),
        167: ("喜欢慢慢来", "mandarin_baseline"),
        197: ("喜欢不慌不忙", "project_translation"),
        227: ("喜欢悠闲的生活方式", "project_translation"),
        257: ("让事情按自己的节奏进行", "project_translation"),
        287: ("反应较慢", "project_translation"),
    },
}

# ============================================================ 脚手架（人工撰写）
SC = {
"selfdiscipline": {
 25: dict(
  asks="该做的事，你是否会立刻动手而不是往后拖",
  key_term=("chores", "日常该做但没什么乐趣的琐事", "只指需要花力气的正事，把琐事排除在外"),
  mis=[("把\"杂事\"理解成\"大事\"",
        "这里问的恰恰是没什么成就感的小事。大事往往有外部压力推着，小事才考验自律。"),
       ("认为\"马上做\"等于\"一次做完\"",
        "立刻开始 ≠ 一次做完。先动手就算符合，中间休息不影响。")],
  counts=["该做的事一出现就动手，不用先给自己做心理建设",
          "不用等到\"状态好\"才开始"],
  notcount=["因为这件事本身有趣所以立刻去做",
            "被截止日期逼着立刻做"],
  edge="如果某类事你能立刻做、另一类总拖，按占多数的情形作答。",
 ),
 55: dict(
  asks="你平时是否处于\"已经准备好\"的状态",
  key_term=("prepared", "事情到来之前已完成必要准备", "不是\"能力上能应付\""),
  mis=[("把\"有准备\"理解成\"能力强\"",
        "这里问的是有没有提前做准备，不是能不能做好。能力强但从不预习的人，这题应给低分。"),
       ("想到自己\"随时能应付突发情况\"就选高分",
        "临时应对不算准备。区别在于事情发生前你是否已经动过手。")],
  counts=["出门前会提前收拾好东西",
          "事情还没到截止时间就已经开始推进"],
  notcount=["对自己的应变能力有信心",
            "事情来了才现做，但做得不错"],
  edge=None,
 ),
 85: dict(
  asks="面对任务，你是否马上开始而不是先搁一搁",
  key_term=("right away", "从\"知道要做\"到\"开始做\"之间的延迟很短", "不是\"做得快\""),
  mis=[("把\"马上开始\"等同于\"很快做完\"",
        "这里只问开始得早不早。开始得早但做得慢，仍算符合。"),
       ("因为任务本身紧急所以马上做，也算高分吗",
        "如果只在被逼急时才马上开始，平时都拖，那反映的是外部压力而非自律，应给低分。")],
  counts=["任务一到手就着手，不需要缓冲期",
          "想到要做就去做，中间不插入别的事"],
  notcount=["因为有人催才马上做",
            "把开始时间排在计划里的较后位置，但确实按计划执行"],
  edge="若你习惯\"先想清楚再动手\"，而想清楚只需要很短时间，仍算马上开始；若想的过程本身在拖延，则不算。",
 ),
 115: dict(
  asks="需要动手时，你是否能立刻进入工作状态",
  key_term=("at once", "从\"决定做\"到\"实际动手\"几乎无间隔", "不是\"工作时的投入程度\""),
  mis=[("与第 3 题（立刻开始做事）混为一谈",
        "第 3 题问\"开始得早不早\"，这题问\"启动时顺不顺\"。有人开始得早但要磨蹭很久才真正进入，两题答案可以不同。"),
       ("把\"进入状态\"理解成\"进入心流\"",
        "这里不要求沉浸，只要求动手。")],
  counts=["坐下来就能开始，不需要先刷手机、先整理桌子",
          "决定做之后立刻付诸动作"],
  notcount=["需要很长时间的仪式感才能开工",
            "身体坐下了但一直没真正动手"],
  edge=None,
 ),
 145: dict(
  asks="你自己定的计划，是否真能执行下去",
  key_term=("plans", "自己主动定下的、非他人强加的安排", "不是\"别人交代的任务\""),
  mis=[("把\"完成任务\"当成\"执行计划\"",
        "别人交办的任务有外部约束，执行它不代表自律。这里的关键是**你自己定的**计划。"),
       ("只有完整执行才算吗",
        "大部分执行、偶尔调整也算符合。这一题问的是趋势，不是零失误。")],
  counts=["自己定的作息、学习、锻炼安排能坚持",
          "计划有变动也会补上，不让它整体垮掉"],
  notcount=["只完成别人安排的事，自己定的计划总是搁置",
            "计划定得很宽松所以总能完成"],
  edge=None,
 ),
 175: dict(
  asks="（反向题）你是否难以让自己进入工作状态",
  key_term=("get down to work", "真正坐下来开始干活这一步", "不是\"工作过程辛苦\""),
  mis=[("把它理解成\"工作很累\"",
        "这里卡在\"开始\"这一步，不是过程的疲惫。工作轻松但迟迟不开始，才符合这一题。"),
       ("没注意是反向题",
        "这题说的是\"难以开始\"。越符合，自律越低。照实作答即可，系统会反向计分。")],
  counts=["总要先做很多别的事，才肯开始正事",
          "明知该做却反复推迟动手"],
  notcount=["开始得慢但一旦开始就很投入（那属第 4 题的范围）",
            "任务本身难度大导致需要更多准备时间"],
  edge=None, rev=True,
 ),
 205: dict(
  asks="（反向题）你的时间是否常被浪费掉",
  key_term=("waste", "事后回看觉得本可以用得更好的时间", "不是\"休息\""),
  mis=[("把休息也算成浪费",
        "主动安排的休息不是浪费。这里指事后你自己都觉得可惜的那些时间。"),
       ("因为\"谁都会刷手机\"就选中间值",
        "这一题问的是程度。每天几小时与偶尔十分钟，差别很大。")],
  counts=["一天结束时说不出时间花在哪",
          "经常在无目的地滑动中度过较长时间"],
  notcount=["有计划的休息与放空",
            "时间花在了计划外但有价值的事情上"],
  edge=None, rev=True,
 ),
 235: dict(
  asks="（反向题）开始做事前，你是否需要别人推动",
  key_term=("a push", "来自外部的启动推力", "不是\"需要建议或方向\""),
  mis=[("把\"需要建议\"当成\"需要推动\"",
        "需要别人告诉你做什么 ≠ 需要别人推你才肯做。后者才是这一题。"),
       ("认为\"有人提醒也正常\"",
        "偶尔提醒正常。这一题问的是否**总要**有人推。")],
  counts=["没人催就一直不动",
          "需要外部压力才能启动"],
  notcount=["自己启动，只是偶尔接受提醒",
            "需要的是信息或资源，不是推力"],
  edge=None, rev=True,
 ),
 265: dict(
  asks="（反向题）你从\"该做\"到\"开始做\"之间是否拖得很久",
  key_term=("difficulty starting", "启动环节的阻力", "不是\"做得慢\""),
  mis=[("把\"做得慢\"当成\"开始得慢\"",
        "开始得快但做得慢，不符合这一题。"),
       ("认为只有严重拖延才算",
        "经常拖上几天就已属明显。这一题问的是启动阻力的大小。")],
  counts=["任务到手后总要搁置一段时间才开始",
          "启动前有明显的心理阻力"],
  notcount=["开始得快但过程慢",
            "为完成任务预留了准备期，且确实按计划开始"],
  edge=None, rev=True,
 ),
 295: dict(
  asks="（反向题）你是否习惯把决定往后推",
  key_term=("postpone decisions", "决断本身的推迟", "不是\"深思熟虑\""),
  mis=[("把\"谨慎决策\"当成\"拖延决策\"",
        "有明确理由、有时间表的等待不算推后。这里指没有理由的搁置。"),
       ("与\"拖延做事\"混同",
        "这一题特指**决定**这一环。事可以照做，但决定一直不下。")],
  counts=["明知该定下来，仍一再往后放",
          "把选择拖到不得不做时才做"],
  notcount=["为了等关键信息而有意等待",
            "决策快但执行慢（那是另一回事）"],
  edge=None, rev=True,
 ),
},

"activitylevel": {
 17: dict(
  asks="你平时是否处于忙碌状态",
  key_term=("busy", "手头持续有事情在推进", "不是\"被迫应付\""),
  mis=[("把\"被安排满\"当成\"活跃\"",
        "如果忙碌完全来自外部摊派、而你本人并不想动，那反映的是处境而非特质。请按\"一贯的自己\"作答。"),
       ("认为只有工作忙才算",
        "照顾家庭、社交、爱好都算占用与推进。")],
  counts=["日常总是有事在做，闲不下来",
          "即使没有外部要求，也会给自己找事"],
  notcount=["这段时间被临时任务填满（阶段性）",
            "被迫忙碌但内心很想停下来"],
  edge="请以\"平时的你\"为基准，不要用最忙的那个月作答。",
 ),
 47: dict(
  asks="你是否总是在不同的事情之间奔走",
  key_term=("on the go", "地点或事项的频繁切换", "不是\"爱出门\""),
  mis=[("把\"爱出门玩\"当成\"奔波\"",
        "这一题问的是节奏与切换频率，不是社交意愿。宅在家但一直在做事，也算符合。"),
       ("认为\"奔波\"含有辛苦的意思",
        "这里不含褒贬，只描述节奏。")],
  counts=["一天里在多项事务间来回切换",
          "很少长时间停在单一状态"],
  notcount=["一天只做一件事但做得很久",
            "喜欢出门但节奏缓慢"],
  edge=None,
 ),
 77: dict(
  asks="空闲时间里你是否做很多事",
  key_term=("do a lot", "闲暇中被填进去的活动量", "不是\"闲不下来\"这种焦虑式忙碌"),
  mis=[("把\"休息\"当成\"没做事\"",
        "有内容的休息（看片、散步、读书）都算活动。这一题只问量。"),
       ("因为工作忙就选高分",
        "这一题限定在**空闲时间**。工作忙不等于闲暇也充实。")],
  counts=["闲暇时间安排得比较满",
          "休息日也会做不少事"],
  notcount=["把工作挤占的时间算进来",
            "空闲时主要是躺着恢复"],
  edge=None,
 ),
 107: dict(
  asks="你能否同时处理好几件事",
  key_term=("at the same time", "并行处理的容量", "不是\"被迫多线程\""),
  mis=[("把\"被迫同时应付\"当成\"擅长并行\"",
        "被逼着多线程且手忙脚乱，不符合这一题。这里问的是能不能应付得来。"),
       ("与第 1 题（忙碌）混同",
        "忙碌是量，并行是容量。有人事很多但只能一件件做。")],
  counts=["能同时推进多项事务而不乱",
          "被打断后能快速回到多条线里"],
  notcount=["事情多到超出负荷、频频出错",
            "只能串行处理，一次一件"],
  edge=None,
 ),
 137: dict(
  asks="你的反应速度是否偏快",
  key_term=("react quickly", "对外界刺激做出回应的速度", "不是\"决定得快\""),
  mis=[("把\"反应快\"当成\"性子急\"",
        "反应快是速度，性子急是情绪。两者可以分开。"),
       ("认为反应快总是优点",
        "这里不作好坏判断，只描述快慢。")],
  counts=["别人说完能立刻接上",
          "身体动作与回应都比较利落"],
  notcount=["说话做事前习惯停顿一下（那属于审慎，不是慢）",
            "只在熟悉的事情上快"],
  edge="这一题在 facet 内偏\"速度\"而非\"活动量\"，与本 facet 其余题目略有不同——见 known_critiques。",
 ),
 167: dict(
  asks="（反向题）你是否偏好慢节奏",
  key_term=("take it easy", "对从容、不赶的偏好", "不是\"懒\""),
  mis=[("把\"慢慢来\"当成\"效率低\"",
        "这一题问的是偏好，不是能力。偏好从容不等于做不好。"),
       ("因为它谈偏好而非行为，不知该怎么答",
        "确实如此——本 facet 混有\"行为\"与\"偏好\"两类题目，这是它的已知问题。照实作答即可。")],
  counts=["有意识地选择不赶的节奏",
          "对\"快\"本身没有向往"],
  notcount=["被迫慢下来（如身体原因、外部限制）",
            "休息时慢，但平时节奏很快"],
  edge=None, rev=True,
 ),
 197: dict(
  asks="（反向题）你是否喜欢不慌不忙地做事",
  key_term=("take my time", "做事情时给自己留出充裕时间", "不是\"拖沓\""),
  mis=[("把\"不慌不忙\"当成\"拖延\"",
        "这里指按自己的节奏稳着做，不是把事往后拖。"),
       ("与第 6 题（喜欢慢慢来）视为同一题",
        "第 6 题是整体的生活节奏偏好，这一题特指**做事时**的节奏。可以不同。")],
  counts=["做事时不喜欢被时间催着",
          "宁可慢一点也不赶"],
  notcount=["因为拖延才显得慢",
            "任务紧急时会主动加速"],
  edge=None, rev=True,
 ),
 227: dict(
  asks="（反向题）你是否向往悠闲的生活方式",
  key_term=("leisurely lifestyle", "对整体生活方式的取向", "不是\"想偷懒\""),
  mis=[("把\"悠闲\"理解成\"不做事\"",
        "悠闲指节奏从容，不等于无所事事。"),
       ("与\"有没有条件悠闲\"混同",
        "这一题问取向，不问现实条件。")],
  counts=["理想的生活状态是从容不迫的",
          "不羡慕高强度高节奏的生活"],
  notcount=["现实中被逼慢下来但内心想快",
            "只是这一个阶段想休息"],
  edge=None, rev=True,
 ),
 257: dict(
  asks="（反向题）你是否倾向让事情按它们自己的节奏发展",
  key_term=("their own pace", "不主动加速、不推动", "不是\"不负责任\""),
  mis=[("把\"不推\"当成\"不管\"",
        "事情仍在推进，只是不额外加力。"),
       ("认为这与\"计划性\"矛盾",
        "它可以与计划性共存——按计划走，但不催。")],
  counts=["不急于推动进度",
          "能接受事情按原有速度展开"],
  notcount=["因为无从下手而被动等待",
            "该推的时候会果断推（那说明并非一贯如此）"],
  edge=None, rev=True,
 ),
 287: dict(
  asks="（反向题）你的反应速度是否偏慢",
  key_term=("react slowly", "回应外界所需的时间", "不是\"想得深\""),
  mis=[("把\"反应慢\"理解成\"思考周密\"",
        "周密是深度，慢是速度。这里只问速度。"),
       ("与第 5 题（反应很快）的方向混淆",
        "这一题说\"慢\"，越符合活跃度越低。系统会反向计分。")],
  counts=["需要一点时间才回应",
          "动作与反应节奏偏缓"],
  notcount=["只是说话前习惯斟酌（不等于反应慢）",
            "在陌生情境下慢，熟悉后很快"],
  edge=None, rev=True,
 ),
},
}

# ============================================================ facet 级定义
FACET_META = {
"selfdiscipline": dict(
  name_zh="自律", name_en="Self-discipline", code="C5", domain="conscientiousness", domain_zh="尽责性",
  definition="自律这一面向描述的是**启动并坚持执行任务**的倾向：能否在想做之前就动手，"
             "能否把自己定下的计划推进下去，以及启动环节的阻力有多大。"
             "它关注的是\"做\"这一环，而不是\"想不想做好\"或\"环境整不整齐\"。",
  does_not_measure=["不测量环境是否整洁有序（属 C2 条理性）",
                    "不测量是否守规矩、尽义务（属 C3 责任心）",
                    "不测量抱负高低与成就动机（属 C4 追求成就）",
                    "不测量对自己能力的信心（属 C1 自我效能）",
                    "不测量能否抵抗诱惑（属 N5 放纵）"],
  boundaries=[
    ("orderliness", "条理性", "条理性管的是**环境与物品**是否有序（房间、桌面、文件）；"
                              "自律管的是**行动**能否启动与推进。桌面很乱但任务照做的人，自律高、条理性低。"),
    ("dutifulness", "责任心", "责任心管的是**外部规范**（该不该做、守不守约）；"
                              "自律管的是**执行**（做不做得到）。一个极守规矩但总要人催才能开工的人，责任心高、自律低。"),
    ("achievementstriving", "追求成就", "追求成就管的是**想要多高**（抱负、标准）；"
                                        "自律管的是**能不能做到**。想拿第一却从不开始的人，追求成就高、自律低。"),
    ("selfefficacy", "自我效能", "自我效能是**相信自己能做成**；自律是**真的去做**。"
                                 "两者常同向，但可以分离——自信却拖沓是常见的组合。"),
    ("cautiousness", "审慎", "审慎管的是**动手前想多久**；自律管的是**想完之后做不做**。"
                            "过度审慎会拖慢启动，但动机不同，不应混为一谈。"),
  ],
  anchor={
    "1": "任务到手往往要搁置很久，常需别人推才启动",
    "2": "多数任务会拖，但最终能完成",
    "3": "有些事立刻做，有些会拖，视任务而定",
    "4": "多数事情能较快启动，偶有拖延",
    "5": "想到就做，启动几乎无阻力，自己定的计划基本都能推进",
  },
  critique=["本 facet 的题目混合了「启动速度」（第 3、4 题）与「持续执行」（第 5 题）两个侧面，"
            "以及「是否浪费时间」这一偏结果导向的表述（第 7 题）。α=.85 尚可接受，但侧面并不单一。",
            "第 10 题（Postpone decisions）针对**决策**而非行动，与本 facet 其余题目的对象不同。"],
  caveats=["本面向的题目混合了「**启动速度**」（第 3、4 题）与「**持续执行**」（第 5 题）"
           "两个侧面，第 10 题问的则是**决策**而非行动。α=.85 尚可接受，"
           "但若你在这几个侧面上差别很大，总分可能掩盖这一差异。"],
  citation="改述自 Costa & McCrae (1992) NEO-PI-R 专业手册中 C5 Self-Discipline 的面向定义",
),
"activitylevel": dict(
  name_zh="活跃度", name_en="Activity Level", code="E4", domain="extraversion", domain_zh="外向性",
  definition="活跃度这一面向描述的是**生活节奏与能量输出**：做事的速度、同时推进多件事的容量、"
             "以及总体上偏好快节奏还是从容节奏。它关注的是\"多快、多少\"，而不是\"想不想要刺激\"。",
  does_not_measure=["不测量对强烈刺激的渴求（属 E5 追求刺激）",
                    "不测量社交中的主导性（属 E3 决断性）",
                    "不测量是否喜欢与人相处（属 E1 友好、E2 合群）",
                    "不测量积极情绪的高低（属 E6 开朗）",
                    "不测量工作是否自律（属 C5 自律）"],
  boundaries=[
    ("excitementseeking", "追求刺激", "活跃度是**基础节奏**（走得快、做得多）；"
                                      "追求刺激是**对强烈体验的渴求**（冒险、喧闹）。"
                                      "节奏快的人未必爱冒险，爱冒险的人也未必日常忙碌。"),
    ("assertiveness", "决断性", "决断性是**在人群中主导**（发言、带队）；"
                              "活跃度是**个人节奏**。安静但一天做很多事的人是活跃度高、决断性低。"),
    ("gregariousness", "合群性", "合群性是**寻求他人陪伴**；活跃度是**活动量**。"
                                "独处但高效的人两者可以分离。"),
    ("cheerfulness", "开朗", "开朗是**积极情绪的强度**；活跃度是**动作的速率**。"),
    ("selfdiscipline", "自律", "自律是**能否启动并坚持该做的事**；"
                              "活跃度是**总体节奏快慢**。被逼着忙碌且拖延的人，活跃度可能不低，自律却低。"),
  ],
  anchor={
    "1": "节奏很慢，喜欢从容，同时处理多件事会觉得吃力",
    "2": "偏慢，做事不太赶，同时做多件事比较勉强",
    "3": "节奏中等，看情况调整快慢",
    "4": "偏快，日常行程较满，能应付多件事并行",
    "5": "节奏很快，总在做事情，能同时推进多项事务",
  },
  critique=["**本 facet 是本量表 α 最低的一个（.71）**，且其题目在内容上并不单一：",
            "· 行为量：第 1、2、3 题（忙碌、奔波、闲暇充实）",
            "· 处理容量：第 4 题（同时处理多件事）",
            "· 反应速度：第 5、10 题（反应快/慢）",
            "· **偏好**而非行为：第 6、7、8、9 题（喜欢慢慢来、不慌不忙、悠闲、顺其自然）",
            "**「行为」与「偏好」混在同一 facet 内，是这一低信度最可能的解释。**"
            "作答者在这些题上可能出现\"我实际很快，但我向往从容\"之类的真实分离。",
            "**官方便携中文译本在该 facet 上的 α 仅为 .422**（见 phase0_ipip_audit §4），"
            "为 30 个 facet 中最低——说明这一内容异质性在翻译后可能被放大。"],
  caveats=["**本面向的题目混合了两类不同的东西**：第 1–5、10 题问的是你的**实际节奏与行为**"
           "（忙碌、奔波、并行、反应快慢），而第 6–9 题问的是你对从容节奏的**偏好**"
           "（喜欢慢慢来、不慌不忙、向往悠闲、顺其自然）。",
           "这是本量表内部一致性最低的面向（α=.71，其余多为 .80 以上）。"
           "**如果你的实际节奏与内心偏好并不一致（例如「实际很快，但向往从容」），"
           "这个总分无法同时描述这两件事**——请分别看上述两类题目。",],
  citation="改述自 Costa & McCrae (1992) NEO-PI-R 专业手册中 E4 Activity 的面向定义",
),
}


def build(facet: str) -> dict:
    canon = load("ipip-neo-300.json")
    base = load("ipip-neo-120-mandarin.json")
    norms = load("uk-norms.json")
    meta = FACET_META[facet]
    items = sorted([i for i in canon["items"] if i["facet"] == facet], key=lambda x: x["order"])
    base_zh = {norm(i["en"]): i["zh"] for i in base["items"] if i["facet"] == facet}

    # 分带
    bands = {}
    for age in norms["levels"]["facets"]:
        tab = norms["levels"]["facets"][age]
        key = [k for k in tab if norm(k) == norm(facet)][0]
        bands[age] = {
            b: (f"{tab[key][b][0]}-{tab[key][b][-1]}" if len(tab[key][b]) > 1
                else str(tab[key][b][0]))
            for b in BANDS if tab[key][b]
        }

    domain_bands = {}
    ov = f"{meta['domain'].upper()} (OVERALL)"
    for age in norms["levels"]["facets"]:
        tab = norms["levels"]["facets"][age]
        if ov in tab:
            domain_bands[age] = {
                b: (f"{tab[ov][b][0]}-{tab[ov][b][-1]}" if len(tab[ov][b]) > 1
                    else str(tab[ov][b][0]))
                for b in BANDS if tab[ov][b]
            }

    # SD 由带反推
    def sd_from(age: str) -> float | None:
        b = bands[age]
        try:
            p05 = (int(b["Average"].split("-")[-1]) + int(b["High"].split("-")[0])) / 2
            p15 = (int(b["High"].split("-")[-1]) + int(b["Very High"].split("-")[0])) / 2
            n05 = (int(b["Average"].split("-")[0]) + int(b["Low"].split("-")[-1])) / 2
            return round(((p05 - n05) + (p15 - p05)) / 2, 2)
        except (KeyError, ValueError):
            return None

    alpha = canon["facet_alphas"][facet]
    out_items = []
    for it in items:
        zh, src = ZH[facet][it["order"]]
        s = SC[facet][it["order"]]
        term, sense, not_this = s["key_term"]
        scaf = {
            "asks": s["asks"],
            "key_term": {"term": term, "sense_here": sense, "not_this": not_this},
            "common_misreadings": [{"misreading": m, "correction": c} for m, c in s["mis"]],
            "counts_as": s["counts"],
            "does_not_count_as": s["notcount"],
            "edge_cases": s["edge"],
            "provenance": "editorial_clarification",
            "evidence_anchor": f"题干承重词为 “{term}”；"
                               + ("本题为反向计分（key = −1），已注明。" if it["key"] < 0 else ""),
        }
        if s.get("rev"):
            scaf["reverse_item_note"] = (
                "反向题。题干表述的是本 facet 的**低**端。照实作答即可，系统会反向计分——"
                "不要为了\"保持一致\"而调整答案。")
        out_items.append({
            "administration_order": it["order"], "id": it["id"], "facet": it["facet"],
            "key": it["key"], "text_en": it["text"],
            "text_master": it.get("text_master"),
            "text_zh": zh, "text_zh_source": src,
            "scaffolding": scaf,
        })

    sems = {age: round((sd_from(age) or 0) * math.sqrt(1 - alpha), 2) for age in bands}
    sds = {age: sd_from(age) for age in bands}

    return {
        "_note": f"Phase 1 切片：{meta['name_zh']}（{meta['name_en']} / {meta['code']}）。"
                 "由 tools/build/build_remaining_slices.py 从规范数据集组装，脚手架为人工撰写。",
        "identity": {
            "id": f"ipip-neo-300.{facet}", "instrument": "IPIP-NEO-300",
            "facet_name_zh": meta["name_zh"], "facet_name_en": meta["name_en"],
            "facet_code": meta["code"], "domain": meta["domain"], "domain_zh": meta["domain_zh"],
        },
        "license": {"status": "public_domain", "show_items": True, "translate": True,
                    "redistribute": True,
                    "evidence": "https://www.ipip.ori.org/newPermission.htm"},
        "construct": {
            "definition": {"text": meta["definition"],
                           "basis": meta["citation"],
                           "provenance": "published_definition"},
            "does_not_measure": meta["does_not_measure"],
            "boundaries": [{"against_facet": f, "against_facet_zh": z, "distinction": d,
                            "basis": "NEO-PI-R 面向定义"}
                           for f, z, d in meta["boundaries"]],
            "applicable_population": "成年一般人群",
            "inapplicable_population": ["无法理解中文题面者",
                                        "处于急性危机状态者（应先处理危机，而非测评）"],
        },
        "administration": {
            "recall_window": {"value": "typical",
                              "instruction_quote": "Describe yourself as you generally are now, "
                                                   "not as you wish to be in the future.",
                              "source": "IPIP-NEO-300 官方问卷指导语",
                              "plain_zh": "请描述你平时一贯的样子，而不是今天的样子，"
                                          "也不是你希望成为的样子。"},
            "item_count": 10,
            "item_order_in_full_instrument": "interleaved_30_facet_cycle",
            "order_style": "interleaved_facet_cycle",
            "estimated_duration_min": 35,
            "response_format": {"points": 5,
                                "labels_zh": ["非常不符合", "比较不符合", "中立",
                                              "比较符合", "非常符合"]},
            "anchor_semantics": dict(meta["anchor"], provenance="editorial_clarification"),
        },
        "scoring": {
            "algorithm": "10 题求和（反向题先做 6 − x 转换）。范围 10–50。",
            "reverse_items": [i["id"] for i in out_items if i["key"] < 0],
            "forward_items": [i["id"] for i in out_items if i["key"] > 0],
            "key_balance": f"{sum(1 for i in out_items if i['key']>0)} 正向 / "
                           f"{sum(1 for i in out_items if i['key']<0)} 反向",
            "reverse_keyed_count": sum(1 for i in out_items if i["key"] < 0),
            "reference_system": "norm_percentile",
        },
        "reliability": {
            "cronbach_alpha": alpha,
            "alpha_source": "OpenScales IPIP-NEO.osd（源自 Goldberg 的 ESCS 数据）",
            "sem": {"formula": "SEM = SD × sqrt(1 − α)", "status": "DERIVED",
                    "value": sems["18-29"], "reference_age_band": "18-29",
                    "sd_used": sds["18-29"], "alpha_used": alpha,
                    "by_age_band": {a: {"sd": sds[a], "sem": sems[a]} for a in bands},
                    "derivation": "源文件未直接给出 SD；分带按 σ 定义，由带边界反推。",
                    "caveat": "⚠️ 由整数化带边界反推，约 ±0.5 分舍入不确定性，"
                              "不是源文件直接给出的 SD。"},
            "noise_floor": {
                "basis": "Kohút et al. (2020)，facet 层 6 个月重测 r ≈ .70",
                "source_file": "archive/literature/interpretation/kohut2020_bfi2-slovak-6month-retest.pdf",
                "user_facing_rule": "facet 分数在约 0.15–0.2 SD 以内的变动属测量噪音。",
                "interpretation_with_sem": f"95% 置信区间约 ±{round(1.96*sems['18-29'],1)} 分；"
                                           f"小于该幅度的变化不应被解读为真实变化。",
                "provenance": "published_definition"},
        },
        "norms": {"status": "AVAILABLE",
                  "parser": "tools/build/parse_uk_norms.py",
                  "bands_values": bands,
                  "domain_bands_values": domain_bands,
                  "applicability_caveat": "**UK 人群，非中国人群。** 源文件未提供样本量、"
                                          "招募方式与采集年份。年龄段划分较粗（14-17 / 18-29 / 30+）。",
                  "cross_file_discrepancy_note": "同一 OSF 目录下的 TRAITS 与 FACETS 文件在 "
                                                 "CONSCIENTIOUSNESS/14-17 边界上不一致；本切片统一采用 FACETS 文件。"},
        "evidence": {
            "validated_in_chinese": False,
            "chinese_note": "IPIP-NEO-300 无中文译本；官方便携译本仅覆盖 120 题版且未经 IPIP 验证。",
            "known_critiques": meta["critique"],
            "interpretation_caveats": meta.get("caveats", []),
        },
        "items": out_items,
    }


def main() -> int:
    for facet in ("selfdiscipline", "activitylevel"):
        rec = build(facet)
        path = os.path.join(ROOT, "content/pilot", f"{facet}.record.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(rec, fh, ensure_ascii=False, indent=2)
        n_off = sum(1 for i in rec["items"] if i["text_zh_source"] == "mandarin_baseline")
        print(f"{facet:16} {len(rec['items'])} 题 / 官方中译 {n_off} / 自译 "
              f"{len(rec['items'])-n_off} / α {rec['reliability']['cronbach_alpha']} "
              f"/ SEM {rec['reliability']['sem']['value']} → {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
