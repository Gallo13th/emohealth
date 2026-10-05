# -*- coding: utf-8 -*-
"""Generate batch-070-zh.json from batch-070.json, verifying 1:1 key correspondence."""
import json, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "batch-070.json")
DST = os.path.join(BASE, "batch-070-zh.json")

TR = {
 # --- IPIP-Depression (past tense stem: "During the past two weeks...") ---
 "had a poor appetite": ("食欲差。", "过去两周的食欲下降，属躯体性抑郁表现。"),
 "had crying spells": ("哭过好几场。", "指一阵阵控制不住的哭泣（crying spells），非偶尔落泪。"),
 "had restless sleep": ("睡眠不安稳。", "指入睡后辗转、易醒的睡眠质量差，不是睡得少。"),
 "had thoughts about death": ("想到过死亡。", "被动地想到死亡，不等于有自杀计划，注意与自杀意念区分。"),
 "had trouble keeping my mind on what i was doing": ("做事时难以集中注意力。", "指注意力不能保持在手头事情上，非记性差。"),
 "talked less than usual": ("比平时说话少。", "言语活动减少，他人可观察到的抑郁表现。"),
 "thought about killing myself": ("想到过自杀。", "主动的自杀意念，比「想到死亡」程度更重。"),
 "thought that my life had been a failure": ("觉得自己的生活很失败。", "对整个人生的失败感与自我否定，非对某件事的懊悔。"),
 "was bothered by things that usually don't bother me": ("平时不会烦我的事也让我心烦。", "指烦恼阈值下降，琐事也变得扰人。"),
 "was down in the dumps": ("情绪低落沮丧。", "口语化说法，指闷闷不乐、提不起劲的心境。"),
 # --- IPIP-Foa2002: Physical Attractiveness ---
 "am considered attractive by others": ("被他人认为有吸引力。", "从他人眼光看自己的外表吸引力，非自我评价。"),
 "attract attention from the opposite sex": ("能吸引异性的注意。", "以异性关注衡量自身吸引力，属自评的吸引力感知。"),
 "dislike looking at my body": ("不喜欢看自己的身体。", "对自身身体外观的回避与不满。"),
 "dislike looking at myself in the mirror": ("不喜欢照镜子看自己。", "照镜时的回避，指向对自身外表的不满。"),
 "don't consider myself attractive": ("我不认为自己有吸引力。", "反向计分题：否认自己有吸引力，译时不可改成肯定。"),
 "have a pleasing physique": ("身材令人满意。", "physique 指体形体格，非面容好看。"),
 "like to look at my body": ("喜欢看自己的身体。", "对自身身体的欣赏与接纳。"),
 "like to look at myself in the mirror": ("喜欢照镜子看自己。", "乐于看镜中的自己，反映对身体外观的满意。"),
 # --- IPIP-Foa2002: Obsessive-Compulsive Symptoms ---
 "check on things more often than necessary": ("检查东西的次数超出必要。", "反复核对（如门窗煤气），强迫性检查行为。"),
 "feel that i have to repeat certain numbers": ("觉得某些数字非重复不可。", "重复特定数字的强迫冲动，非单纯喜欢数字。"),
 "feel that there are good and bad numbers": ("觉得数字有吉凶之分。", "把数字分为吉利与不吉利，带神奇思维色彩的强迫观念。"),
 "find it difficult to touch an object that has been touched by others": ("难以触碰别人碰过的东西。", "对他人接触过的物件感到抗拒，涉及污染顾虑。"),
 "get upset if objects are not arranged properly": ("物品没摆放整齐就心烦。", "对物品摆放秩序的苛求与不适。"),
 "have difficulty getting rid of nasty thoughts": ("难以摆脱令人不快的念头。", "侵入性想法挥之不去，即强迫观念。"),
 "need things to be arranged in a particular order": ("需要物品按特定顺序排列。", "对排列次序的强迫性需要，与整齐并列但侧重顺序。"),
}

with open(SRC, "r", encoding="utf-8") as f:
    src = json.load(f)

items = src["items"]
src_keys = [it["key"] for it in items]
assert len(src_keys) == len(set(src_keys)), "duplicate keys in source"
missing = [k for k in src_keys if k not in TR]
extra = [k for k in TR if k not in set(src_keys)]
assert not missing, "missing translations: %r" % missing
assert not extra, "extra translations: %r" % extra

out = []
for it in items:
    zh, note = TR[it["key"]]
    assert len(note) <= 60, "note too long for %s (%d)" % (it["key"], len(note))
    out.append({"key": it["key"], "zh": zh, "note": note})

with open(DST, "w", encoding="utf-8", newline="\n") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
    f.write("\n")

# --- verify ---
with open(DST, "rb") as f:
    raw = f.read()
assert not raw.startswith(b"\xef\xbb\xbf"), "BOM found"
back = json.loads(raw.decode("utf-8"))
assert len(back) == len(items) == src["count"], (len(back), len(items), src["count"])
assert [r["key"] for r in back] == src_keys, "key mismatch"
assert all(set(r) == {"key", "zh", "note"} and r["zh"] and r["note"] for r in back)
print("OK lines=%d count_field=%d keys_identical=True json_valid=True bom=False" % (len(back), src["count"]))
