#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 300 题排成一张**由支撑关系长出来的**图（D99/D100），并定下 30 个面向的角序。

为什么要有这个脚本：
    旧的「径向天赋树」把节点的半径＝层数（阶梯里的第几题）。但解锁口径已改成
    「逐面向滑动窗口」——一个节点可答是因为**别的已答内容把它顶到了门槛**，
    不是因为它在第几环。位置若仍由层数决定，图形就在宣称一个已经被推翻的机制。

两个阶段（都在这里做完，界面只做确定性绘制，不做物理模拟）：

  ① **角序**（原 `optimize_layout.py`，已并入）：把 30 个面向按关联强度排成一个圆，
     使 Σ相邻 |r| 最大（环形序列化：种子链 + 贪心插入 + 2-opt）。它决定第 1 层
     那 30 道题的角位置——在没有任何作答时，「谁挨着谁」唯一可依据的就是这个。
     并进来的理由：原先它单独产出一份 `ui/layout-data.js`，而那份文件只被这个脚本
     与几个测试读，界面早已不用（D100 后位置由支撑决定）——留着一份「看起来还在
     生效」的中间产物，正是 D94 记过的那种坑。

  ② **位置**：一层 = 一个面向上刚好一道题（`tierRingNodes` 的列），深度按梯度排。
     每题用**题-题相关**（`adaptive-network.json` 的 300×300 矩阵）挑一个
     **层数更浅、且已放置的邻居**里最相关的那道当支撑点，挂在它旁边。
     于是「强相关的题聚在一起」是算出来的，不是画的；深度仍是梯度，可读。
     最后用「排斥 + 贴住本层半径」把重叠推开——**贴半径那一项必须强**，
     否则中心节点会被挤到圈外、「离中心越远＝越深」当场失效（实测过）。

输出：ui/net-layout.js（题目坐标 + 支撑边 + 角序 + 自检指标）

复现：python3 tools/ui/build_tier_layout.py
"""
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
DATA = os.path.join(ROOT, 'data')
UI = os.path.join(ROOT, 'ui')

VB = 900                      # viewBox 边长（与界面一致）
CX = CY = VB / 2
R0, R1 = 158.0, 424.0         # 第 1 层 / 第 10 层的半径
N = 300
LEVELS = 10
MIN_SEP = 22.0                # 节点最小间距（节点半径约 8.4，太小会糊在一起）


def load_json(name):
    with open(os.path.join(DATA, name), encoding='utf-8') as f:
        return json.load(f)


def load_ui_js(name, var):
    """读一个 window.XXX = {...}; 形式的界面数据包。"""
    with open(os.path.join(UI, name), encoding='utf-8') as f:
        t = f.read()
    i = t.index('{')
    j = t.rindex('}')
    return json.loads(t[i:j + 1])


def pair_reader(b64, n=300):
    """adaptive-network.json 的 pairB64 是 float32 下三角（行偏移 (a-1)(a-2)/2）。"""
    import base64
    import struct
    raw = base64.b64decode(b64)
    arr = struct.unpack('<%df' % (len(raw) // 4), raw)

    def r(i, j):
        if i == j:
            return 1.0
        a, b = (i, j) if i > j else (j, i)          # 1-based
        off = (a - 1) * (a - 2) // 2
        return arr[off + (b - 1)]
    return r


def circ_objective(order, W):
    """环形目标：相邻（含首尾）的 |r| 之和。"""
    n = len(order)
    return sum(W[order[i], order[(i + 1) % n]] for i in range(n))


def seriate_facets(C):
    """环形序列化：让 Σ相邻 |r| 最大。

    三步（与原来那份 optimize_layout.py 一致，只是搬进来）：
      1. 种子链：从最强的一对开始，每次把与链两端最相似的面接上去
      2. 贪心插入：把每个面向拔出来，插到增益最大的位置
      3. 2-opt：反转区间
    30 个元素，秒级完成。
    """
    n = C.shape[0]
    W = np.abs(C.copy())
    np.fill_diagonal(W, -1e9)

    i, j = np.unravel_index(np.argmax(W), W.shape)
    order = [int(i), int(j)]
    rest = set(range(n)) - set(order)
    while rest:
        best, best_gain, best_end = None, -1e9, None
        for k in rest:
            for end in (0, -1):
                g = W[k, order[end]]
                if g > best_gain:
                    best, best_gain, best_end = k, g, end
        if best_end == 0:
            order.insert(0, best)
        else:
            order.append(best)
        rest.discard(best)

    improved, rounds = True, 0
    while improved and rounds < 40:
        improved, rounds = False, rounds + 1
        for k in list(order):
            cur = circ_objective(order, W)
            trial = [x for x in order if x != k]
            best_pos, best_val = None, cur
            for pos in range(len(trial) + 1):
                cand = trial[:pos] + [k] + trial[pos:]
                v = circ_objective(cand, W)
                if v > best_val + 1e-12:
                    best_val, best_pos = v, pos
            if best_pos is not None:
                order = trial[:best_pos] + [k] + trial[best_pos:]
                improved = True

    improved, swaps = True, 0
    while improved:
        improved = False
        cur = circ_objective(order, W)
        for a in range(n - 1):
            for b in range(a + 1, n):
                if b - a < 2:
                    continue
                cand = order[:a] + order[a:b + 1][::-1] + order[b + 1:]
                v = circ_objective(cand, W)
                if v > cur + 1e-12:
                    order, cur, improved = cand, v, True
                    swaps += 1
    return order, round(circ_objective(order, W), 4)


def main():
    tier = load_ui_js('tier-data.js', 'EMOHEALTH_TIER')
    ad = load_ui_js('adaptive-data.js', 'EMOHEALTH_ADAPT')
    un = load_ui_js('unlock-data.js', 'EMOHEALTH_UNLOCK')
    net = load_json('correlation-network.json')

    facets = tier['facets']                         # 30 个面向名（按界面索引排序）
    rings = tier['tierRingNodes']                   # 10 × 30：ring[t][f] = 题号
    order = tier['order']
    R = pair_reader(ad['pairB64'])

    # 题号 → (面向索引, 层索引)
    pos_of = {}
    for t in range(LEVELS):
        for f in range(len(facets)):
            pos_of[rings[t][f]] = (f, t)

    # ── ① 角序：环形序列化，用 correlation-network 的**面向级相关矩阵**。
    #
    # 两套矩阵**不是同一个口径**，别指望它们逐格相符：
    #   · `correlation-network.facet_corr` = 在**反向题已还原**（6−x，使所有分同向）
    #     的作答上，对**面向总分**算 Pearson（见 analyze_correlation_network.py L65–97）
    #   · `adaptive.pairR` = **题级**相关（不是总分），且已在计分对齐后的空间里
    #     （同面向内部一律为正，再按 key 翻符号会打散它——D59 的双重翻转陷阱）
    # 实测两者最强对都不同（面向级：excitementseeking—cautiousness；题级：
    # friendliness—gregariousness）——总分抵消了题目独特方差，题级平均则被稀释。
    # 所以：角序用面向级矩阵（它才是当初优化布局的依据），
    # 题-题矩阵只用于下游的**支撑关系**（它自己的口径自洽）。
    #
    # 但**矩阵与标签的绑定必须验**（D88 那种「矩阵没错、标签错了」踩过两次）。
    # 这里用一个**同一口径内**的判据：对每个面向，拿它的 10 道题去和它自己的
    # 总分算相关，必须高于拿它去和任何**别的**面向总分算相关——列错位时这条必崩。
    net_facets = net['facets']
    assert set(net_facets) == set(facets), '两份数据的面向集合不一致'
    C_net = np.array(net['facet_corr'], dtype=float)
    C = C_net[np.ix_([net_facets.index(f) for f in facets],
                     [net_facets.index(f) for f in facets])]
    assert np.allclose(C, C.T, atol=1e-6), '面向相关矩阵不对称'

    own_best, weak = 0, []
    for a in range(len(facets)):
        keys = [rings[k][a] for k in range(LEVELS)]
        scores = []
        for b in range(len(facets)):
            tot_b = [rings[k][b] for k in range(LEVELS)]
            scores.append(sum(R(x, y) for x in keys for y in tot_b)
                          / (len(keys) * len(tot_b)))
        top = max(range(len(facets)), key=lambda b: scores[b])
        if top == a:
            own_best += 1
        else:
            weak.append(f'{facets[a]}→最强的是 {facets[top]}')
    assert own_best >= len(facets) - 3, (
        f'矩阵与标签疑似错位：只有 {own_best}/30 个面向「与自己总分最相关」；'
        f'例：{weak[:3]}')
    print('标签绑定复核：%d/30 个面向「与自己总分最相关」（阈值 ≥27）' % own_best)

    def strongest_facet_pair():
        best = (-2.0, None, None)
        for a in range(len(facets)):
            for b in range(a + 1, len(facets)):
                v = abs(C[a, b])
                if v > best[0]:
                    best = (v, facets[a], facets[b])
        return best

    v_net, fa_net, fb_net = strongest_facet_pair()
    print('面向级最强对：%s—%s（%.3f）' % (fa_net, fb_net, v_net))

    angle_order, obj = seriate_facets(C)
    # 对照：按维度分扇区
    DOM_KEY = tier['domains']
    dom_of = {}
    for d, dn in enumerate(DOM_KEY):
        for f in tier['domainFacetIdx'][dn]:
            dom_of[f] = d
    fixed = sorted(range(len(facets)), key=lambda k: (dom_of[k], k))
    W = np.abs(C.copy())
    np.fill_diagonal(W, -1e9)
    obj_fixed = round(circ_objective(fixed, W), 4)

    slot = {f: k for k, f in enumerate(angle_order)}

    # ── 放置顺序：先第 1 层（30 道，无支撑），再按层
    XY = {}
    depth = {}
    parent = {}
    for t in range(LEVELS):
        for f in range(len(facets)):
            o = rings[t][f]
            depth[o] = t

    # 第 1 层：均匀铺在圆上，角序来自上面的环形序列化——
    # 「谁挨着谁」在没有任何作答时唯一可依据的，就是面向级相关结构。
    ang = {}
    for f in range(len(facets)):
        a = (-90 + slot[f] * 12) * math.pi / 180
        ang[f] = a
        o = rings[0][f]
        XY[o] = (CX + R0 * math.cos(a), CY + R0 * math.sin(a))
        parent[o] = None

    placed = [rings[0][f] for f in range(len(facets))]

    # ── 逐层放置：每题挂到「已放置的邻居」里最相关的那道旁边
    def radius(t):
        return R0 + (R1 - R0) * (t / (LEVELS - 1))

    for t in range(1, LEVELS):
        # 同一层内先按「与已放置集合的最大相关」降序——相关强的先占好位置
        cand = []
        for f in range(len(facets)):
            o = rings[t][f]
            best_o, best_r = None, -2.0
            for q in placed:
                v = R(o, q)
                if v > best_r:
                    best_o, best_r = q, v
            cand.append((best_r, o, best_o))
        cand.sort(key=lambda x: -x[0])

        for _v, o, sup in cand:
            sx, sy = XY[sup]
            sa = math.atan2(sy - CY, sx - CX)
            rr = radius(t)
            # 角度先试支撑点的方向；被占就左右交替偏开
            best = None
            for k in range(0, 60):
                for sign in ((0,) if k == 0 else (1, -1)):
                    a = sa + sign * math.radians(6.0 * ((k + 1) // 2))
                    x = CX + rr * math.cos(a)
                    y = CY + rr * math.sin(a)
                    if x < 26 or x > VB - 26 or y < 26 or y > VB - 26:
                        continue
                    d = min((x - XY[q][0]) ** 2 + (y - XY[q][1]) ** 2
                            for q in placed if abs(depth[q] - t) <= 1)
                    if best is None or d > best[0]:
                        best = (d, a, x, y)
                    if d ** 0.5 >= MIN_SEP:
                        best = (d, a, x, y)
                        break
                if best is not None and best[0] ** 0.5 >= MIN_SEP:
                    break
            _d, a, x, y = best
            XY[o] = (x, y)
            parent[o] = sup
            placed.append(o)

    # ── 排斥：题目是「挂在支撑点旁」，但同层挤在一起时还是要推开
    keys = list(XY.keys())
    for _ in range(260):
        moved = 0.0
        for i in range(len(keys)):
            oi = keys[i]
            xi, yi = XY[oi]
            fx = fy = 0.0
            for j in range(len(keys)):
                if i == j:
                    continue
                oj = keys[j]
                xj, yj = XY[oj]
                dx, dy = xi - xj, yi - yj
                d2 = dx * dx + dy * dy
                if d2 < 1e-9:
                    dx, dy, d2 = 0.7, 0.7, 0.98
                d = math.sqrt(d2)
                if d < MIN_SEP * 1.6:
                    push = (MIN_SEP * 1.6 - d) / d * 0.55
                    fx += dx * push
                    fy += dy * push
            # 拉向支撑点（保持「聚在支撑旁」的语义）
            sup = parent[oi]
            if sup:
                xs, ys = XY[sup]
                fx += (xs - xi) * 0.035
                fy += (ys - yi) * 0.035
            # 贴住本层半径。这一项必须**强**：纯排斥会把中心节点挤到圈外、
            # 把第 2 层挤进中心，于是「离中心越远＝阶梯越深」在图上就看不出来了
            # （实测过：第 1–3 层的平均半径只差 15，肉眼分不开）。
            want = radius(depth[oi])
            d = math.hypot(xi - CX, yi - CY) or 1e-6
            ux, uy = (xi - CX) / d, (yi - CY) / d
            fx += (CX + ux * want - xi) * 0.22
            fy += (CY + uy * want - yi) * 0.22
            nx, ny = xi + fx * 0.32, yi + fy * 0.32
            nx = min(VB - 26, max(26, nx))
            ny = min(VB - 26, max(26, ny))
            moved += abs(nx - xi) + abs(ny - yi)
            XY[oi] = (nx, ny)
        if moved < 0.5:
            break

    # ── 自检
    mind = 1e9
    worst = None
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = XY[keys[i]], XY[keys[j]]
            d = math.hypot(a[0] - b[0], a[1] - b[1])
            if d < mind:
                mind, worst = d, (keys[i], keys[j])
    out_of_canvas = [o for o in keys
                     if XY[o][0] < 22 or XY[o][0] > VB - 22
                     or XY[o][1] < 22 or XY[o][1] > VB - 22]

    # 支撑边（题→支撑题）与面向级骨边（取相关最强的若干条，供淡显骨架）
    support = {str(o): parent[o] for o in keys if parent[o]}
    # 深度半径的单调性：每层的平均半径必须递增，否则「离中心越远＝越深」不成立
    layer_r = []
    for t in range(LEVELS):
        rs = [math.hypot(XY[rings[t][f]][0] - CX, XY[rings[t][f]][1] - CY)
              for f in range(len(facets))]
        layer_r.append(sum(rs) / len(rs))

    ok = (mind >= 15.0 and not out_of_canvas
          and all(layer_r[i] < layer_r[i + 1] for i in range(LEVELS - 2)))

    # 角序的自检：必须是一个排列，且目标值不能比「按维度分扇区」更差
    assert sorted(angle_order) == list(range(len(facets))), '角序不是排列'
    assert obj > obj_fixed, f'序列化没带来增益（{obj} vs {obj_fixed}）'

    payload = {
        'meta': {
            'method': '支撑驱动布局：每题挂到「层数更浅的已放置邻居」里最相关的那道旁边，'
                      '再做排斥；深度仍是梯度（离中心越远越深），'
                      '第 1 层的角序由面向级相关的环形序列化定。',
            'viewBox': VB, 'cx': CX, 'cy': CY,
            'r0': R0, 'r1': R1, 'minSep': round(mind, 2), 'minSepWorst': worst,
            'outOfCanvas': len(out_of_canvas),
            'layerMeanR': [round(v, 1) for v in layer_r],
            'selfCheck': 'ok' if ok else 'FAILED',
        },
        # 角序（原 layout-data.js 的内容并到这里）——
        # 测试要拿它验「最强的一对在优化后相邻」，界面不再用（位置由支撑决定）
        'angleOrder': angle_order,
        'angleNames': [facets[k] for k in angle_order],
        'objective': obj,
        'objectiveFixed': obj_fixed,
        'gainPct': round((obj / obj_fixed - 1) * 100, 2),
        'xy': {str(o): [round(XY[o][0], 2), round(XY[o][1], 2)] for o in keys},
        'depth': {str(o): depth[o] for o in keys},
        'support': support,
    }

    js = ('window.EMOHEALTH_NET = ' + json.dumps(payload, ensure_ascii=False,
                                                 separators=(',', ':')) + ';\n')
    with open(os.path.join(UI, 'net-layout.js'), 'w', encoding='utf-8') as f:
        f.write(js)

    print('角序：相邻 |r| 之和 %.3f → %.3f（固定扇区 %.3f，%+.1f%%）'
          % (obj_fixed, obj, obj_fixed, (obj / obj_fixed - 1) * 100))
    print('最小节点间距 %.2f（%s—%s）' % (mind, worst[0], worst[1]))
    print('出界节点 %d' % len(out_of_canvas))
    print('每层平均半径 ' + ' '.join('%.0f' % v for v in layer_r))
    print('自检 %s' % ('通过' if ok else '❌ 未通过'))
    print('→ ui/net-layout.js (%.1f KB)' %
          (os.path.getsize(os.path.join(UI, 'net-layout.js')) / 1024))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
