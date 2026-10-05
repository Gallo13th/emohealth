# -*- coding: utf-8 -*-
"""Build batch-001-zh.json from batch-001.json (keys copied verbatim)."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "batch-001.json")
DST = os.path.join(HERE, "batch-001-zh.json")

# Translations in input order, keyed by the exact English source text.
TRANSLATIONS = [
    ("I am capable of completing tasks without AI, but I still cannot resist using it.",
     "我有能力不借助AI完成任务，但我仍然忍不住要用它。",
     "明知自己能做仍无法不用，测的是失控而非能力不足。"),
    ("I can no longer manage complex academic tasks without the assistance of AI.",
     "没有AI的协助，我再也无法应对复杂的学业任务。",
     "测能力感的丧失：自认离开AI就做不了复杂学业任务。"),
    ("I delegate almost all my academic tasks to AI because it performs them faster and better than I do.",
     "我几乎把所有学业任务都交给AI，因为它比我做得更快、更好。",
     "测任务让渡程度，其动机是比较后形成的自我能力不足感。"),
    ("I feel inadequate in my studies without the support of AI.",
     "没有AI的支持，我在学业上感到自己不够好。",
     "测失去AI支持时的自我能力怀疑，而非客观成绩差。"),
    ("I feel uneasy or insecure without the help of AI.",
     "没有AI的帮助，我感到不安或没有把握。",
     "测停用AI时的情绪不适，属依赖的戒断样反应。"),
    ("I have almost no control over the frequency and duration of my AI use.",
     "我几乎无法控制自己使用AI的频率和时长。",
     "测使用行为的失控程度，而非使用量本身大小。"),
    ("I have tried to reduce my use of AI, but I have never succeeded for long.",
     "我曾试图减少使用AI，但从没能坚持多久。",
     "测既往减量尝试反复失败，是依赖的核心指标。"),
    ("I know I shouldn't rely too much on AI, but I can't control myself.",
     "我知道自己不该过度依赖AI，但就是控制不住自己。",
     "测认知与行为的冲突：明知过度却仍难以自控。"),
    ("I often ask AI for answers directly without thinking for myself first.",
     "我常常不先自己思考，就直接向AI要答案。",
     "测思考外包：先问AI而非先自主思考，非问得多。"),
    ("I prefer to delegate information gathering and content organization to AI rather than doing it entirely myself.",
     "比起完全自己动手，我更愿意把信息搜集和内容整理交给AI。",
     "测对信息搜集与整理的偏好性外包，不是使用频率。"),
    ("I rely on AI's functions, including providing answers and writing suggestions, to improve my learning efficiency.",
     "我依赖AI的功能，包括提供答案和写作建议，来提升我的学习效率。",
     "测以提升效率为由的功能性依赖，落点在效率动机。"),
    ("I would feel anxious and frustrated if I couldn't use AI for my studies.",
     "如果学习时无法使用AI，我会感到焦虑和烦躁。",
     "测假想停用AI时的焦虑烦躁，属戒断样情绪反应。"),
    ("If I don't use AI for a period of time, I feel a strong urge to use it, sometimes even feeling irritable.",
     "如果一段时间不用AI，我就有强烈的使用冲动，有时甚至变得易激惹。",
     "测停用后的渴求与易激惹，属戒断样体验。"),
    ("In my studies, I excessively rely on the ready-made answers or solutions provided by AI.",
     "在学业中，我过度依赖AI提供的现成答案或解法。",
     "测对现成答案的过度依赖，关键词是现成、不经思考。"),
    ("Interacting with AI via chat prompts is a pleasant experience that makes me feel supported.",
     "通过聊天提示与AI互动是愉快的体验，让我感到被支持。",
     "测与AI互动的正性体验与支持感，不是使用时长。"),
    ("Once I start using AI, I often find it difficult to stop, even after spending a lot of time on it.",
     "我一旦开始使用AI，就常常难以停下来，即使已经花了很长时间。",
     "测停止困难：即使耗时已久也无法自主中断使用。"),
    ("Using AI to assist my studies makes me feel calm and relaxed.",
     "用AI辅助我的学习让我感到平静和放松。",
     "测AI带来的情绪安抚，属依赖的正强化来源。"),
    ("When faced with an academic challenge, I rely on AI instead of attempting to think it through on my own.",
     "面对学业挑战时，我依赖AI，而不是尝试自己把它想清楚。",
     "测遇挑战即转向AI，以求助取代自主思考过程。"),
    ("Whenever I encounter a difficult problem, my first instinct is to hope AI can help me; otherwise, I feel tense.",
     "每当我遇到难题，第一反应就是希望AI能帮我；否则我就感到紧张。",
     "测求助的首要性：不依赖AI时的紧张不适。"),
    ("I could not get \u201cgoing.\u201d",
     "我提不起劲来（原文：I could not get \u201cgoing.\u201d）。",
     "原文going加引号意为启动不起来；测抑郁性启动困难，非懒惰。"),
    ("I did not feel like eating; my appetite was poor.",
     "我不想吃东西；我的胃口很差。",
     "测食欲下降这一抑郁躯体症状，不是挑食或节食减肥。"),
    ("I enjoyed life.",
     "我享受生活。",
     "CES-D反向计分题：测快感缺失之有无，须保持正面表述。"),
    ("I felt depressed.",
     "我感到抑郁。",
     "测抑郁心境本身，而非一时难过或短暂情绪低落。"),
    ("I felt fearful.",
     "我感到害怕。",
     "测近期主观恐惧体验，不是对特定对象的恐惧。"),
    ("I felt hopeful about the future.",
     "我对未来感到有希望。",
     "CES-D反向计分题：测希望感之有无，须保持正面表述。"),
]

with open(SRC, "r", encoding="utf-8") as f:
    data = json.load(f)

items = data["items"] if isinstance(data, dict) and "items" in data else data
assert isinstance(items, list) and len(items) == 25, len(items)
assert len(TRANSLATIONS) == len(items), (len(TRANSLATIONS), len(items))

out = []
for item, (en, zh, note) in zip(items, TRANSLATIONS):
    assert item["en"] == en, "EN mismatch:\n%r\n%r" % (item["en"], en)
    assert len(note) <= 60, (len(note), note)
    out.append({"key": item["key"], "zh": zh, "note": note})

with open(DST, "w", encoding="utf-8", newline="\n") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
    f.write("\n")

print("written", DST, len(out))
