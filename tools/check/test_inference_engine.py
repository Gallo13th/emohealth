#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`engine/inference.py` 的单元/集成测试。

四块：
  A. 分层：官方分「缺失不猜」，推断结果**独立**标注（绝不混算）
  B. 边界：0 题 / 1 题 / 答满该维度 / 全卷答满（不许 NaN、不许静默给 0）
  C. 置信度口径与 `dim_ceiling` 一致；`available` 门槛 = ceiling × ratio
  D. 可解释性：贡献之和 == 未答部分的预测；跨维度借用可量化

所有断言都用**手算或独立复算**给期望值，不引用实现自己的说法。
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = str(find_root())
sys.path.insert(0, ROOT)

from engine.inference import load, predict  # noqa: E402

fail = 0


def ck(name: str, cond: bool, detail: str = "") -> None:
    global fail
    print(f"  {'✅' if cond else '❌'} {name}" + (f"  —— {detail}" if detail else ""))
    if not cond:
        fail += 1


IPIP = load("IPIP-NEO")
PID = load("PID-5")
ANX = "anxiety"
ANX_ITEMS = IPIP.dim_items[ANX]


print("=== A. 分层：官方分缺失不猜，推断独立标注 ===")
part = {ANX_ITEMS[0]: 4, ANX_ITEMS[1]: 5, "ipip_neo_011": 2}
r = predict(IPIP, part)
off = r["official"][ANX]
inf = r["inferred"][ANX]
ck("官方分：未答满 → value=None（不是「已答部分的均值」）",
   off["value"] is None and off["complete"] is False,
   f"value={off['value']} n={off['n_answered']}/{off['n_items']}")
ck("官方分：给出 blocker 说明为什么没有分", bool(off.get("blocker")), off.get("blocker"))
ck("推断：带 inferred=true 且给出 predicted_score",
   inf["inferred"] is True and isinstance(inf["predicted_score"], float),
   f"predicted={inf['predicted_score']:.4f}")
ck("推断**不写回**官方分（official.value 仍为 None）",
   r["official"][ANX]["value"] is None)
ck("分层说明写进结果里（调用方读得到）", "不得与官方分混算" in r["layer_note"])
full_anx = {i: 3 for i in ANX_ITEMS}
rf = predict(IPIP, full_anx)
ck("答满该维度 → 官方分 complete=True 且 value 是手算均值",
   rf["official"][ANX]["value"] == 3.0 and rf["official"][ANX]["complete"] is True,
   str(rf["official"][ANX]["value"]))
ck("答满时该维度的其它维度仍 complete=False、value=None",
   all(o["value"] is None for k, o in rf["official"].items() if k != ANX))

print("\n=== B. 边界：0 题 / 1 题 / 答满 ===")
r0 = predict(IPIP, {})
b0 = r0["inferred"][ANX]
ck("0 题：status=NO_DATA、predicted_score/confidence_r 都是 None（不是 0）",
   b0["status"] == "NO_DATA" and b0["predicted_score"] is None
   and b0["confidence_r"] is None and b0["available"] is False
   and b0["display_allowed"] is False)
ck("0 题：全部 30 个维度都 NO_DATA",
   all(b["status"] == "NO_DATA" for b in r0["inferred"].values()))
ck("0 题：官方分也全部 None",
   all(o["value"] is None for o in r0["official"].values()))
r1 = predict(IPIP, {ANX_ITEMS[0]: 4})
b1 = r1["inferred"][ANX]
ck("1 题：能给出预测且不是 NaN",
   b1["status"] == "OK" and b1["predicted_score"] is not None
   and not math.isnan(b1["predicted_score"]),
   f"pred={b1['predicted_score']:.4f} r={b1['confidence_r']:.4f}")
ck("1 题：置信度 = 该题 corrected 相关（手算对照）",
   abs(b1["confidence_r"]
       - abs(IPIP.item_dim_corr[ANX_ITEMS[0]][ANX])) < 1e-12,
   f"{b1['confidence_r']:.6f} vs {abs(IPIP.item_dim_corr[ANX_ITEMS[0]][ANX]):.6f}")
ck("答满该维度：预测 == 官方分（精确）",
   abs(rf["inferred"][ANX]["predicted_score"] - rf["official"][ANX]["value"]) < 1e-12,
   f"{rf['inferred'][ANX]['predicted_score']} vs {rf['official'][ANX]['value']}")
ck("答满该维度：prediction_se == 0（没有未答部分）",
   rf["inferred"][ANX]["prediction_se"] == 0.0)
all_resp = {i: ((k % 5) + 1) for k, i in enumerate(IPIP.ids)}
ra = predict(IPIP, all_resp)
worst = max(abs(b["predicted_score"] - ra["official"][k]["value"])
            for k, b in ra["inferred"].items())
ck("全卷答满：30 个维度预测都精确等于官方分", worst < 1e-12, f"max|Δ|={worst:.3g}")
ck("全卷答满：全部维度 available=True",
   all(b["available"] for b in ra["inferred"].values()))

print("\n=== C. 置信度口径与 dim_ceiling / available 门槛 ===")
ck("答满该维度时 confidence_r ≈ dim_ceiling（同口径）",
   abs(rf["inferred"][ANX]["confidence_r"] - IPIP.dim_ceiling[ANX]) < 1e-3,
   f"{rf['inferred'][ANX]['confidence_r']:.6f} vs {IPIP.dim_ceiling[ANX]:.6f}")
ck("答满该维度时 confidence_r_total == 1（最终分已知）",
   abs(rf["inferred"][ANX]["confidence_r_total"] - 1.0) < 1e-12)
ck("available 门槛 = ceiling × ratio",
   all(abs(b["ceiling_need"] - b["ceiling"] * IPIP.ceiling_ratio) < 1e-12
       for b in ra["inferred"].values()),
   f"ratio={IPIP.ceiling_ratio}")
ck("available 与 confidence_r ≥ 门槛 逐维度一致",
   all(b["available"] == (b["confidence_r"] >= b["ceiling_need"])
       for b in ra["inferred"].values()))
# 至少有一组部分作答落在「不可给」区间，证明门槛真的在起作用
mid = {i: 3 for i in ANX_ITEMS[:2]}
rm = predict(IPIP, mid)
ck("只答 2 题时该维度 available=False（门槛在起作用）",
   rm["inferred"][ANX]["available"] is False,
   f"r={rm['inferred'][ANX]['confidence_r']:.3f} "
   f"need={rm['inferred'][ANX]['ceiling_need']:.3f}")
ck("PID-5 的判据口径同样是 dim_ceiling × ratio",
   all(abs(b["ceiling_need"] - b["ceiling"] * PID.ceiling_ratio) < 1e-12
       for b in predict(PID, {"pid5_001": 2})["inferred"].values()))

print("\n=== C2. 跨维度上限 `dim_ceiling_cross`（界面显示分母）===")
ck("两个量表的每个维度都有 dim_ceiling_cross（数据层已落盘）",
   set(IPIP.dim_ceiling_cross) == set(IPIP.dims)
   and set(PID.dim_ceiling_cross) == set(PID.dims),
   f"IPIP {len(IPIP.dim_ceiling_cross)} / PID-5 {len(PID.dim_ceiling_cross)}")
ck("跨维度上限 ≥ 本维度上限（1.03–1.10 倍，实测）",
   all(IPIP.dim_ceiling_cross[d] >= IPIP.dim_ceiling[d] - 1e-9 for d in IPIP.dims)
   and all(PID.dim_ceiling_cross[d] >= PID.dim_ceiling[d] - 1e-9 for d in PID.dims),
   f"IPIP 比值 {min(IPIP.dim_ceiling_cross[d]/IPIP.dim_ceiling[d] for d in IPIP.dims):.3f}"
   f"–{max(IPIP.dim_ceiling_cross[d]/IPIP.dim_ceiling[d] for d in IPIP.dims):.3f}")
ck("ceiling_pct 落在 [0,1]（不会显示 >100%）",
   all(b["ceiling_pct"] is None or 0.0 <= b["ceiling_pct"] <= 1.0
       for b in ra["inferred"].values())
   and all(b["ceiling_pct"] is None or 0.0 <= b["ceiling_pct"] <= 1.0
           for b in predict(PID, {"pid5_001": 2})["inferred"].values()))
ck("答满本维度、**不答跨维度**：ceiling_pct < 1（分母是跨维度上限）",
   rf["inferred"][ANX]["ceiling_pct"] < 1.0
   and abs(rf["inferred"][ANX]["confidence_r"] - IPIP.dim_ceiling[ANX]) < 1e-3,
   f"pct={rf['inferred'][ANX]['ceiling_pct']:.4f} "
   f"（conf_r={rf['inferred'][ANX]['confidence_r']:.4f} / "
   f"cross={rf['inferred'][ANX]['ceiling_cross']:.4f}）")
ck("整卷答满：ceiling_pct ≈ 1（分母即整卷答满时的 conf_r；落盘值 4 位小数，容差 1e-3）",
   abs(ra["inferred"][ANX]["ceiling_pct"] - 1.0) < 1e-3,
   f"pct={ra['inferred'][ANX]['ceiling_pct']:.6f}")
ck("**判据**仍锚在 dim_ceiling × ceiling_ratio（没被新分母改动）",
   all(abs(b["ceiling_need"] - b["ceiling"] * b["ceiling_ratio"]) < 1e-12
       for b in ra["inferred"].values())
   and all(b["available"] == (b["confidence_r"] >= b["ceiling_need"])
           for b in ra["inferred"].values() if b["confidence_r"] is not None))
ck("硬规则维度：ceiling_pct 也是 None（不给数），但 ceiling/ceiling_cross 仍在",
   (lambda b: b["ceiling_pct"] is None and b["ceiling_pct_raw"] is None
    and b["ceiling"] is not None and b["ceiling_cross"] is not None)(
       predict(IPIP, {i: 5 for i in IPIP.dim_items["anger"][:5]})["inferred"][ANX]))

print("\n=== D. 可解释性：贡献与跨维度借用 ===")
# 只用本维度的题：borrow 应为 0，贡献之和 == 未答部分的**位移**（不含总体均值）
own_only = {ANX_ITEMS[0]: 4, ANX_ITEMS[1]: 5}
r_own = predict(IPIP, own_only)
b = r_own["inferred"][ANX]
ck("只用本维度题：cross_dim_share_of_prediction == 0",
   abs(b["cross_dim_share_of_prediction"]) < 1e-12)
s = sum(c["contribution"] for c in b["contributions"])
ck("贡献之和 == predicted_unknown_shift（可由作答解释的位移）",
   abs(s - b["predicted_unknown_shift"]) < 1e-9,
   f"Σcontrib={s:.6f} vs shift={b['predicted_unknown_shift']:.6f}")
ck("predicted_unknown_sum == 未答题的总体均值 + 位移（手算对照）",
   abs(b["predicted_unknown_sum"]
       - (sum(IPIP.item_mean[i] for i in ANX_ITEMS[2:]) + b["predicted_unknown_shift"])) < 1e-9,
   f"pred_U={b['predicted_unknown_sum']:.4f} = Σμ_U "
   f"{sum(IPIP.item_mean[i] for i in ANX_ITEMS[2:]):.4f} + shift "
   f"{b['predicted_unknown_shift']:.4f}")
ck("贡献排序：top_contributions 按 |contribution| 降序",
   all(abs(b["top_contributions"][i]["contribution"])
       >= abs(b["top_contributions"][i + 1]["contribution"])
       for i in range(len(b["top_contributions"]) - 1)))

print("\n=== D2. 硬规则：本维度一道题都没答 → 禁止展示（引擎层）===")
other = {i: 5 for i in IPIP.dim_items["anger"][:5]}
ro = predict(IPIP, other)
bo = ro["inferred"][ANX]
ck("只答别的维度的题：status=NO_OWN_ITEM_ANSWERED",
   bo["status"] == "NO_OWN_ITEM_ANSWERED", bo["status"])
ck("只答别的维度的题：display_allowed=False、available=False",
   bo["display_allowed"] is False and bo["available"] is False)
ck("只答别的维度的题：**不返回**置信度与预测数值（是 None，不是 0）",
   bo["confidence_r"] is None and bo["confidence_r_own_only"] is None
   and bo["predicted_score"] is None and bo["r2"] is None
   and bo["r2_total"] is None and bo["confidence_r_total"] is None
   and bo["prediction_se"] is None,
   f"conf={bo['confidence_r']} pred={bo['predicted_score']} r2_total={bo['r2_total']}")
ck("只答别的维度的题：给出原因", bool(bo.get("reason")), bo.get("reason", "")[:40])
# 极端情形：把**别的 29 个维度全部答满**，该维度仍然不得放行
others_full = {i: 4 for d in IPIP.dims if d != ANX for i in IPIP.dim_items[d]}
ro2 = predict(IPIP, others_full)
bo2 = ro2["inferred"][ANX]
ck("别的 29 个维度**全部答满**，本维度仍被硬规则拦住",
   bo2["status"] == "NO_OWN_ITEM_ANSWERED" and bo2["display_allowed"] is False
   and bo2["predicted_score"] is None and bo2["confidence_r"] is None,
   f"n_answered={bo2['n_answered']} status={bo2['status']}")
ck("该维度自己的官方分与其它维度不受影响（分层没被破坏）",
   bo2["inferred"] is True and ro2["official"][ANX]["value"] is None
   and all(o["complete"] for k, o in ro2["official"].items() if k != ANX))

print("\n=== D3. conf_r 纳入跨维度信息（改前/改后对照）===")
one_own = {ANX_ITEMS[0]: 4}
r1 = predict(IPIP, one_own)["inferred"][ANX]
mixed = dict(one_own, **{i: 4 for i in IPIP.dim_items["anger"][:5]})
rm2 = predict(IPIP, mixed)["inferred"][ANX]
ck("只答 1 题本维度：conf_r == 旧口径（没有跨维度项时逐值相同）",
   abs(r1["confidence_r"] - r1["confidence_r_own_only"]) < 1e-12,
   f"new={r1['confidence_r']:.6f} own_only={r1['confidence_r_own_only']:.6f}")
ck("加上 5 道别的维度的题：conf_r 变高（真的借了跨维度）",
   rm2["confidence_r"] > r1["confidence_r"] + 0.05,
   f"{r1['confidence_r']:.4f} → {rm2['confidence_r']:.4f}"
   f"（gain={rm2['cross_dim_borrow_gain']:+.4f}）")
ck("conf_r 与 r_total 是两个量（答满该维度时 conf_r=dim_ceiling<1，而 r_total=1）",
   abs(rf["inferred"][ANX]["confidence_r_total"] - 1.0) < 1e-12
   and rf["inferred"][ANX]["confidence_r"] < IPIP.dim_ceiling[ANX] + 1e-3,
   f"conf_r={rf['inferred'][ANX]['confidence_r']:.4f} vs "
   f"r_total={rf['inferred'][ANX]['confidence_r_total']:.4f}")
ck("答满本维度且无跨维度时 conf_r 仍 == dim_ceiling（锚点未被改动）",
   abs(rf["inferred"][ANX]["confidence_r"] - IPIP.dim_ceiling[ANX]) < 1e-4)

print("\n=== E. 参数来源与错误处理 ===")
ck("IPIP 用的是显式题级统计（item-norms.json）",
   "item-norms.json" in IPIP.stats_source, IPIP.stats_source[:60])
ck("PID-5 用的是**新补的题级常模**（item-norms-pid5.json，不再是 T 分表假设）",
   "item-norms-pid5.json" in PID.stats_source
   and PID.stats_source.count("item-norms-pid5.json") == 1,
   PID.stats_source[:80])
ck("PID-5 题级 mean/sd 是逐题不同的实测值（不是常数）",
   len({round(v, 3) for v in PID.item_sd.values()}) > 50
   and len({round(v, 3) for v in PID.item_mean.values()}) > 50,
   f"sd 取值 {len({round(v, 3) for v in PID.item_sd.values()})} 种")
try:
    predict(IPIP, {ANX_ITEMS[0]: 9})
    ck("越界作答会被拒绝（不静默截断）", False)
except ValueError as e:
    ck("越界作答会被拒绝（不静默截断）", True, str(e)[:60])
try:
    predict(IPIP, {"not_an_item": 3})
    ck("量表外题号会被拒绝", False)
except KeyError as e:
    ck("量表外题号会被拒绝", True, str(e)[:60])
ck("预测不会修改参数（重复调用结果一致）",
   predict(IPIP, part)["inferred"][ANX]["predicted_score"]
   == r["inferred"][ANX]["predicted_score"])

print(f"\n{'❌ ' + str(fail) + ' 项未通过' if fail else '✅ engine/inference.py 全部通过'}")
sys.exit(1 if fail else 0)
