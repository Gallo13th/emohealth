#!/usr/bin/env python3
"""检查 tools/README.md 是否有重复的索引条目，并报告各节表格行数。

背景：`patch_readme_index.py`（一次性补录工具）**没有幂等检查**，我连跑两次
就插了两遍。这类「工具自身不防重复」的坑要留个检查，否则下次还会中。
"""
import os
import re
import sys
from collections import Counter

# 本脚本是**扁平入口**（没有 main()），所以兜底只能就地调用——但必须在第一次
# print 之前。Windows 默认控制台是 GBK，下面的 ✅/⚠️ 会让 print 抛
# UnicodeEncodeError：崩溃点在**输出结果那一行**，退出码 1 与「真的发现重复」
# 完全不可区分，于是完好的守卫在默认控制台上永远假装变红。
# 实现只有一份，在 tools/_root.py（别在这里另写一份）。
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import force_utf8_io  # noqa: E402

force_utf8_io()

ROOT = r"C:\Codes\emohealth-20260930-full\emohealth"
MD = os.path.join(ROOT, "tools", "README.md")
md = open(MD, encoding="utf-8").read()
lines = md.split("\n")

rows = re.findall(r"^\|\s*`(?:tools/)?([^`/\\]+\.(?:py|js|sh|json|md))`\s*\|",
                  md, re.M)
cnt = Counter(rows)
dup_global = {k: v for k, v in cnt.items() if v > 1}

# ⚠️ 「重复」必须**按小节**判：同一文件名出现在不同小节是正常的（叙述性引用），
#    全局判重会把这类误报成重复（我第一版就是全局判重，虚报 12 个）。
H3 = re.compile(r"^### ([0-9.]+)\s")
ITEM = re.compile(r"^\|\s*`(?:tools/)?([^`/\\]+\.(?:py|js|sh|json|md))`\s*\|")
sec_bounds = [(H3.match(l).group(1), i) for i, l in enumerate(lines) if H3.match(l)]
dup_in_sec = {}
for k, (sec, start) in enumerate(sec_bounds):
    end = sec_bounds[k + 1][1] if k + 1 < len(sec_bounds) else len(lines)
    c = Counter(ITEM.match(lines[i]).group(1)
                for i in range(start, end) if ITEM.match(lines[i]))
    bad = {n: v for n, v in c.items() if v > 1}
    if bad:
        dup_in_sec[sec] = bad

print(f"索引表项总数：{len(rows)}；去重后 {len(cnt)}")
print(f"全局出现 ≥2 次的文件名：{len(dup_global)} 个（多为跨小节正常引用）")
if dup_in_sec:
    print(f"\n❌ **同一小节内**重复 {sum(len(v) for v in dup_in_sec.values())} 个：")
    for sec, bad in sorted(dup_in_sec.items()):
        for n, v in sorted(bad.items()):
            print(f"  §{sec}  {n}  × {v}")
else:
    print("✅ 无同小节内重复条目")

# 各节行数 vs 磁盘
print()
SEC = [("3.1", "survey"), ("3.2", "build"), ("3.3", "analyze"),
       ("3.4", "check"), ("3.5", "ui"), ("3.6", "legacy")]
for sec, sub in SEC:
    start = next((i for i, l in enumerate(lines)
                  if re.match(rf"^### {re.escape(sec)}\b", l)), None)
    if start is None:
        continue
    end = next((i for i in range(start + 1, len(lines))
                if re.match(r"^### ", lines[i])), len(lines))
    body = [l for l in lines[start:end]
            if re.match(r"^\|\s*`", l)]
    d = os.path.join(ROOT, "tools", sub)
    actual = len([f for f in os.listdir(d) if os.path.isfile(os.path.join(d, f))])
    flag = "✅" if len(body) == actual else "⚠️"
    print(f"  {flag} §{sec} {sub:8} 表 {len(body):3} 行 / 磁盘 {actual:3} 个")

sys.exit(1 if dup_in_sec else 0)
