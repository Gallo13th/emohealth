#!/usr/bin/env python3
"""把浏览器测试里写死的「量表套数」改为**从 catalog 动态读**。

为什么
======
范围裁剪后套数会变（342 → 16 → 11 → …），而测试把数字写死，每裁一次都要手改
四个地方（`test_local_file.js` ×2、`test_scale_pages.js` ×2）。写死还会**掩盖真问题**：
如果套数意外变化（数据损坏、打包漏了），断言失败的原因看起来像「数字过时」，
人会顺手改数字而不是去查为什么变。

改成从 `data/instruments/catalog.json` 读期望值 —— 单一真相源，
且「页面卡片数 == catalog 条数」这个断言本身更有意义（它测的是**一致性**）。
"""

from __future__ import annotations

import io
import os
import re
import sys

ROOT = r"C:\Codes\emohealth-20260930-full\emohealth"

HEADER = """
// 期望的量表套数**从 catalog 动态读**，不写死——范围裁剪后套数会变，
// 写死会让每次裁剪都要手改，还会把「套数意外变化」伪装成「数字过时」。
const EXPECT_N = JSON.parse(
  require('fs').readFileSync(
    require('path').join(__dirname, '..', '..', 'data', 'instruments', 'catalog.json'),
    'utf8')).instruments.length;
"""

targets = {
    "tools/check/test_local_file.js": [
        ("ck('16 套量表都在', home.cards === 16, home.cards + ' 张卡片');",
         "ck(`${EXPECT_N} 套量表都在`, home.cards === EXPECT_N, home.cards + ' 张卡片');"),
        ("ck('按需加载清单 16 条', home.instMap === 16, home.instMap + ' 条');",
         "ck(`按需加载清单 ${EXPECT_N} 条`, home.instMap === EXPECT_N, home.instMap + ' 条');"),
    ],
    "tools/check/test_scale_pages.js": [
        ("ck('首页显示量表选择器', home.cards === 16, home.cards + ' 张卡片');",
         "ck(`首页显示量表选择器（${EXPECT_N} 套）`, home.cards === EXPECT_N, home.cards + ' 张卡片');"),
        ("ck('回到首页', back.cards === 16 && !back.hasBack,",
         "ck('回到首页', back.cards === EXPECT_N && !back.hasBack,"),
    ],
}

for rel, subs in targets.items():
    p = os.path.join(ROOT, rel.replace("/", os.sep))
    s = io.open(p, encoding="utf-8").read()
    n = 0
    for old, new in subs:
        if old in s:
            s = s.replace(old, new, 1)
            n += 1
        else:
            print(f"  · {rel}: 未找到锚点 {old[:44]!r}")
    if n and "EXPECT_N" in s and "const EXPECT_N" not in s:
        # 插到第一个 const 声明之前
        m = re.search(r"^const ", s, re.M)
        s = s[:m.start()] + HEADER.lstrip("\n") + "\n" + s[m.start():]
    io.open(p, "w", encoding="utf-8").write(s)
    print(f"  ✓ {rel}：替换 {n} 处" + ("（并注入 EXPECT_N）" if "const EXPECT_N" in s else ""))

# 检查残留
print()
for rel in targets:
    p = os.path.join(ROOT, rel.replace("/", os.sep))
    left = re.findall(r"=== 16\b|'16 ", io.open(p, encoding="utf-8").read())
    print(f"  {rel} 残留写死的 16：{len(left)} 处")
