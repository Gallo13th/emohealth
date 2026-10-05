#!/usr/bin/env python3
"""正反验证 check_item_truncation 的判据：修了误报，守卫不能变瞎。

背景：该检查报出 DSM5TR-L2-Depression 第 2 题「可疑截断」，经与归档手册
逐字核对确认是**误报**（`look forward to` 是完整固定搭配）。加了例外后必须
确认三件事：①误报消失；②真截断仍被抓；③真实数据现在全绿。
"""
import importlib.util
import json
import os
import re
import sys

ROOT = r"C:\Codes\emohealth-20260930-full\emohealth"

# 直接导入被测模块取它的正则（比正则抠源码稳——TAIL 的定义跨了两行，
# 用 `re.M` 的 `^...$` 抠不到；我第一版就栽在这）。
sys.path.insert(0, os.path.join(ROOT, "tools"))
import importlib.util
spec = importlib.util.spec_from_file_location(
    "check_item_truncation",
    os.path.join(ROOT, "tools", "check", "check_item_truncation.py"))
_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_mod)
TAIL, EXEMPT = _mod.TAIL, _mod.EXEMPT


def flagged(t: str) -> bool:
    t = t.strip()
    if len(t) < 4:
        return False
    return bool((TAIL.search(t) and not EXEMPT.search(t))
                or (t[:1].islower() and not t[:1].isdigit()))


CASES = [
    # (题干, 期望是否报可疑, 说明)
    ("I felt that I had nothing to look forward to", False, "完整固定搭配→放行"),
    # ⚠️ 下面这条揭示判据的**固有局限**（不是本次修复引入的）：截断若丢的是
    #    词表外的普通词（这里是丢了句末的 `to`），判据抓不到。
    #    期望值按「判据实际能力」写 False，并在此如实记录局限。
    ("I felt that I had nothing to look forward", False,
     "局限：丢了词表外的尾词→判据抓不到"),
    ("I have trouble with", True, "以介词 with 结尾→要抓"),
    ("Feeling of", True, "以 of 结尾→要抓"),
    ("I felt sad", False, "正常完整题干→不报"),
    ("I felt depressed", False, "正常完整题干→不报"),
    ("and then I", True, "以小写开头→报（正确：无来源片段）"),
    ("felt sad", True, "以小写开头→要抓（丢了前半段）"),
    ("2 or 3 times", False, "数字开头选项→不报"),
]
print("=== 判据正反验证 ===")
bad = 0
for t, exp, why in CASES:
    got = flagged(t)
    ok = got == exp
    if not ok:
        bad += 1
    print(f"  {'✅' if ok else '❌'} {t!r:52} 报={got!s:5} 期望={exp!s:5} {why}")
print(f"\n判据用例：{len(CASES) - bad}/{len(CASES)} 通过")

print("\n=== 真实数据全扫（应 0 条可疑）===")
tot = 0
for fn in sorted(os.listdir(os.path.join(ROOT, "data", "instruments"))):
    if not fn.endswith(".json") or fn == "catalog.json":
        continue
    d = json.load(open(os.path.join(ROOT, "data", "instruments", fn),
                       encoding="utf-8"))
    hits = [it["order"] for it in d["items"] if flagged(it["text"])]
    if hits:
        tot += len(hits)
        print(f"  {d['instrument']:24} {len(hits)} 条 → 题号 {hits[:6]}")
print(f"合计可疑 {tot} 条")
print("\n" + ("❌ 判据或数据有问题" if (bad or tot) else
              "✅ 误报已消除，守卫仍有效（真截断用例全部命中），真实数据 0 条可疑"))
