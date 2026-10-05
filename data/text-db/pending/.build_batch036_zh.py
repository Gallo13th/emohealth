# -*- coding: utf-8 -*-
"""Build batch-036-zh.json: keys copied verbatim from batch-036.json by index."""
import json, io, os

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "batch-036.json")
DST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "batch-036-zh.json")

TR = [
 ("身边有糖果或饼干时就忍不住要吃",
  "反向计分：测面对零食诱惑时的克制力，属自我控制低；关键在于“忍不住”，并非不喜欢吃。"),
 ("总在任务临到期限前才动手做",
  "反向计分：测拖延倾向，即临近截止才开始，属自我控制低；并非提前高效完成。"),
 ("没有规律锻炼的习惯",
  "反向计分：测规律运动的习惯有无，属自我控制低；“不”字必须保留，勿读成锻炼习惯良好。"),
 ("即使有些事短期让我感觉良好，只要长期对我有害，我也会舍弃",
  "测为长远利益牺牲即时享乐的自控力，核心是长期有害与短期舒服之间的取舍。"),
 ("屈从于自己的冲动",
  "反向计分：自评是否顺从内心欲望冲动行事，属自我控制低；指内在冲动，非外界压力。"),
 ("吃健康食物对我来说毫无困难",
  "双重否定的正向计分题：吃健康食品毫不费劲，测自我控制好；并非买不到健康食品。"),
 ("任由自己被乱花钱或吃太多的冲动支配",
  "反向计分：测在消费与进食冲动前失去自控，非他人逼迫；“被支配”是理解要点。"),
 ("能够适应任何场合",
  "测融入不同社交情境的适应力，属社交智力；非指委屈自己迎合他人。"),
 ("善于察觉他人的感受",
  "测对他人情绪的敏锐感知，属社交智力；非指自己容易被别人的情绪带动。"),
 ("在新的社交场合不知如何应对",
  "反向计分：测陌生社交情境中的应对自如程度，属社交智力低；非指不懂社交礼仪。"),
 ("能与刚认识的人相处融洽",
  "测与初次相识者建立良好关系的能力，属社交智力；非指与熟人相处得好。"),
 ("有能力让别人感到有趣",
  "原文有此歧义，多指让对方觉得自己有意思；此处照字面直译，属社交智力。"),
 ("懂得别人的心思与动机",
  "tick 为英语习语，指了解他人行事的内在动机，属社交智力；非知道别人在忙什么。"),
 ("知道说什么能让人感觉良好",
  "测言语上让他人感觉舒服的技巧，属社交智力；非指阿谀奉承或操纵他人。"),
 ("我是一个注重灵性的人",
  "指有精神信仰与灵性追求，属灵性/宗教性；非指迷信或神秘主义倾向。"),
 ("我的信仰造就了今天的我",
  "自评信仰对自我认同的塑造作用，属宗教性；faith 指宗教信仰或信念。"),
 ("相信存在某种宇宙力量或上帝",
  "测对超自然宇宙力量或上帝的信仰，属宗教性；universal power 指宇宙性的力量。"),
 ("相信每个人的人生都有其目的",
  "测人生具有目的与意义的信念，属灵性；非指人各有职业或生活目标。"),
 ("不相信存在某种宇宙力量或上帝",
  "反向计分：测无信仰立场，属宗教性低的一端；否定词是全句关键，切勿读反。"),
 ("不践行任何宗教",
  "反向计分：测宗教参与的缺失，属宗教性低；practice 指实际参与宗教活动。"),
 ("过去24小时里至少花30分钟祈祷或冥想",
  "以最近一天的具体时长提问，测祈祷与冥想的实际行为，非笼统的信仰程度。"),
 ("即使艰难时期也坚守我的信仰",
  "测逆境中信仰的坚定性，属宗教性；非指坚持己见、固执不变通。"),
 ("知道我的信念让我的人生变得重要",
  "自评信念赋予人生重要意义，属灵性；非指觉得自己比别人更重要。"),
 ("被认为是个有智慧的人",
  "被动表述：指他人这样评价自己，属智慧/洞察力；非自我评价聪明。"),
 ("不太善于分辨什么才是真正重要的",
  "反向计分：测判断事物轻重本末的能力，属智慧/洞察力低；否定词必须保留。"),
]

with io.open(SRC, encoding="utf-8") as f:
    src = json.load(f)

items = src["items"]
assert len(items) == len(TR), "count mismatch: %d vs %d" % (len(items), len(TR))
assert src.get("count") == len(items), "declared count mismatch"

out = []
for it, (zh, note) in zip(items, TR):
    assert len(note) <= 60, "note too long (%d): %s" % (len(note), note)
    assert zh and note
    out.append({"key": it["key"], "zh": zh, "note": note})

with io.open(DST, "w", encoding="utf-8", newline="\n") as f:
    f.write(json.dumps(out, ensure_ascii=False, indent=1))
    f.write("\n")

# re-verify from disk
with io.open(DST, encoding="utf-8") as f:
    raw = f.read()
assert not raw.startswith("\ufeff"), "BOM present"
back = json.loads(raw)
assert len(back) == len(items)
for a, b in zip(items, back):
    assert a["key"] == b["key"], "key mismatch"
print("OK wrote %d items -> %s" % (len(back), DST))
