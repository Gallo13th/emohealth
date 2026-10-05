#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Python↔JS **逐值一致性**实测（不是声称）：`engine/inference.py` vs `ui/lib/inference.js`。

为什么单独一个测试
==================
本项目历史上「两套实现漂移」出过问题（同一口径在 Python 与 JS 各写一遍，改了
一边忘了另一边，而且两边各自的测试都绿）。所以这里不比较「是否都合理」，
只比较**同一批合成部分作答上的输出是否逐值相同**：

  * `predicted_score`、`confidence_r`、`r2`、`r2_total`、`prediction_se`
  * `available`、`n_answered`、`n_answered_own`
  * `top_contributions` 的题号与贡献值（排序也一致）

边界也进对照：0 题（应两边都 `NO_DATA`）、1 题、答满该维度（预测=官方分）、全卷答满。

用法
====
    python tools/check/test_inference_pyjs_consistency.py
退出码：一致 0；有偏差 1。
"""
from __future__ import annotations

import json
import os
import random
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = str(find_root())
sys.path.insert(0, ROOT)

from engine.inference import load as load_model, predict  # noqa: E402

#: 容差：JS 用高斯消元、Python 用 LAPACK，正常条件下偏差应在 1e-9 量级；
#: 留到 1e-6 是为了容忍不同 BLAS/平台的舍入差异，并在报告里打印**实测**最大偏差。
TOL_SCORE = 1e-6
TOL_R = 1e-6

fail = 0


def ck(name: str, cond: bool, detail: str = "") -> None:
    global fail
    print(f"  {'✅' if cond else '❌'} {name}" + (f"  —— {detail}" if detail else ""))
    if not cond:
        fail += 1


def make_cases(models: dict) -> list[dict]:
    """构造合成部分作答：多组随机子集 + 边界。"""
    rng = random.Random(20261004)
    cases: list[dict] = []
    for code, m in models.items():
        lo = m.instrument.response_format.min
        hi = m.instrument.response_format.max
        dims = m.dims
        # ① 边界：0 题
        cases.append({"id": f"{code}-empty", "instrument": code, "responses": {}})
        # ② 每维度：k=1..min(4, n-1) 的随机子集（含只答 1 题）
        for dim in dims[:6]:
            own = m.dim_items[dim]
            for k in (1, 2, 3, 4):
                k = min(k, max(1, len(own) - 1))
                sub = rng.sample(own, k)
                cases.append({"id": f"{code}-{dim}-k{k}", "instrument": code,
                              "responses": {i: rng.randint(lo, hi) for i in sub}})
        # ③ 答满一个维度（预测应 = 官方分）
        dim = dims[0]
        cases.append({"id": f"{code}-{dim}-full",
                      "instrument": code,
                      "responses": {i: rng.randint(lo, hi) for i in m.dim_items[dim]}})
        # ④ 跨维度混合：每维度取 1 题（前 8 个维度）
        mixed = {}
        for dim in dims[:8]:
            mixed[m.dim_items[dim][0]] = rng.randint(lo, hi)
        cases.append({"id": f"{code}-mixed-8", "instrument": code, "responses": mixed})
        # ⑤ 全卷答满（只对 IPIP 做，PID-5 太慢也不必要）
        if code == "IPIP-NEO":
            cases.append({"id": f"{code}-all", "instrument": code,
                          "responses": {i: rng.randint(lo, hi) for i in m.ids}})
        # ⑥ 硬规则压力：把**除最后 3 个维度之外**全部答满 → 那 3 个维度必须
        #    在两侧都返回 NO_OWN_ITEM_ANSWERED 且不返回任何数值
        rest = [i for d in dims[3:] for i in m.dim_items[d]]
        cases.append({"id": f"{code}-hardrule-tail3", "instrument": code,
                      "responses": {i: rng.randint(lo, hi) for i in rest}})
        # ⑦ 跨维度借用：1 道本维度题 + 别的维度各 1 题
        cro = {m.dim_items[dims[0]][0]: rng.randint(lo, hi)}
        for d in dims[1:6]:
            cro[m.dim_items[d][0]] = rng.randint(lo, hi)
        cases.append({"id": f"{code}-cross-borrow", "instrument": code,
                      "responses": cro})
    return cases


def compare(py: dict, js: dict, case_id: str, code: str, worst: dict) -> list[str]:
    """比对单个 (case, instrument) 的所有维度，返回不一致说明。"""
    bad: list[str] = []
    for dim, bp in py["inferred"].items():
        bj = js["inferred"].get(dim)
        if bj is None:
            bad.append(f"{case_id}/{code}/{dim}: JS 缺该维度")
            continue
        for key in ("predicted_score", "confidence_r", "r2", "r2_total",
                    "prediction_se", "predicted_unknown_sum",
                    "predicted_unknown_shift", "known_own_sum",
                    "confidence_r_own_only", "cross_dim_borrow_gain",
                    "cross_dim_share_of_prediction",
                    "ceiling", "ceiling_cross", "ceiling_need",
                    "ceiling_pct", "ceiling_pct_raw"):
            vp, vj = bp.get(key), bj.get(key)
            if vp is None and vj is None:
                continue
            if vp is None or vj is None:
                bad.append(f"{case_id}/{code}/{dim}/{key}: {vp} vs {vj}")
                continue
            d = abs(float(vp) - float(vj))
            worst[key] = max(worst.get(key, 0.0), d)
            if d > (TOL_SCORE if key != "confidence_r" else TOL_R):
                bad.append(f"{case_id}/{code}/{dim}/{key}: {vp} vs {vj}（差 {d:.3g}）")
        for key in ("status", "available", "display_allowed",
                    "n_answered", "n_answered_own"):
            if bp.get(key) != bj.get(key):
                bad.append(f"{case_id}/{code}/{dim}/{key}: {bp.get(key)} vs {bj.get(key)}")
        tp = [(c["item"], round(float(c["contribution"]), 8)) for c in bp["top_contributions"]]
        tj = [(c["item"], round(float(c["contribution"]), 8)) for c in bj["top_contributions"]]
        if [x[0] for x in tp] != [x[0] for x in tj]:
            bad.append(f"{case_id}/{code}/{dim}/top_contributions 题号不同: {tp} vs {tj}")
        else:
            for (i1, c1), (_i2, c2) in zip(tp, tj):
                worst["contribution"] = max(worst.get("contribution", 0.0), abs(c1 - c2))
                if abs(c1 - c2) > TOL_SCORE:
                    bad.append(f"{case_id}/{code}/{dim}/contrib {i1}: {c1} vs {c2}")
        # 官方分也必须一致（分层：official 与 inferred 分开）
        op = py["official"].get(dim, {})
        oj = js["official"].get(dim, {})
        if op.get("complete") != oj.get("complete"):
            bad.append(f"{case_id}/{code}/{dim}/official.complete: "
                       f"{op.get('complete')} vs {oj.get('complete')}")
        if op.get("value") is not None and oj.get("value") is not None:
            d = abs(float(op["value"]) - float(oj["value"]))
            worst["official_value"] = max(worst.get("official_value", 0.0), d)
            # engine/scoring.py 的 official 值按 `to_dict()` 四舍五入到 4 位小数
            # （这是既有的输出契约），所以这一项的容差是 5e-5，不是 1e-6。
            if d > 5e-5:
                bad.append(f"{case_id}/{code}/{dim}/official.value: "
                           f"{op['value']} vs {oj['value']}")
    return bad


def main() -> int:
    print("=== 载入两侧参数（同一份，由 Python 导出）===")
    models = {code: load_model(code) for code in ("IPIP-NEO", "PID-5")}
    cases = make_cases(models)
    print(f"    合成部分作答 {len(cases)} 组（含 0 题 / 1 题 / 答满 / 混合 / 全卷）")

    py_results = {}
    for c in cases:
        py_results[c["id"]] = predict(models[c["instrument"]], c["responses"])

    tmp = tempfile.mkdtemp(prefix="pyjs-infer-")
    try:
        fixture_path = os.path.join(tmp, "fixture.json")
        out_path = os.path.join(tmp, "js_out.json")
        fixture = {
            "cases": cases,
            "params": {},
        }
        for code, m in models.items():
            inf = json.load(open(m.inference_json, encoding="utf-8"))
            fixture["params"][code] = {"params": m.params_for_js(),
                                       "pairB64": inf["pairB64"]}
        with open(fixture_path, "w", encoding="utf-8") as fh:
            json.dump(fixture, fh, ensure_ascii=False)

        print("\n=== 跑 JS 侧（ui/lib/inference.js，node）===")
        # ⚠️ 必须显式给 encoding：Windows 上默认用 GBK 解子进程输出，
        #    node 的中文报错信息会直接让父进程抛 UnicodeDecodeError（实测踩过）。
        r = subprocess.run(["node", os.path.join(ROOT, "tools", "check",
                                                 "inference_pyjs_compare.js"),
                            fixture_path, out_path],
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode != 0:
            print("    ❌ node 执行失败：", ((r.stderr or "") + (r.stdout or ""))[:400])
            return 1
        js = json.load(open(out_path, encoding="utf-8"))
        print(f"    JS 返回 {len(js['cases'])} 组")

        print("\n=== 逐项比对 ===")
        worst: dict[str, float] = {}
        bad_all: list[str] = []
        for row in js["cases"]:
            cid = row["id"]
            code = next(c["instrument"] for c in cases if c["id"] == cid)
            bad_all += compare(py_results[cid], row["results"][code], cid, code, worst)
        ck("Python 与 JS 逐项一致（0 处偏差）", not bad_all,
           ("；".join(bad_all[:4]) + ("…" if len(bad_all) > 4 else "")) if bad_all else "")
        ck("比对覆盖到了两类量表与全部边界/硬规则/跨维借用",
           len({c["instrument"] for c in cases}) == 2
           and any(c["id"].endswith("-empty") for c in cases)
           and any("full" in c["id"] for c in cases)
           and any("hardrule" in c["id"] for c in cases)
           and any("cross-borrow" in c["id"] for c in cases))
        print("    实测最大偏差（容差 %.0e）：" % TOL_SCORE
              + "，".join(f"{k}={v:.3g}" for k, v in sorted(worst.items())))
        ck("最大偏差在容差内",
           all(v <= (5e-5 if k == "official_value" else max(TOL_SCORE, TOL_R))
               for k, v in worst.items()),
           f"worst={max(worst.values()) if worst else 0:.3g}")

        # 边界行为本身（两侧都过一遍，防止「两边一起错」）
        e = py_results["IPIP-NEO-empty"]
        ck("0 题：两侧都是 NO_DATA、不给预测值/置信度（是 None）",
           all(b["status"] == "NO_DATA" and b["predicted_score"] is None
               and b["confidence_r"] is None and b["display_allowed"] is False
               for b in e["inferred"].values()))
        for cid in ("IPIP-NEO-hardrule-tail3", "PID-5-hardrule-tail3"):
            r = py_results[cid]
            code_cid = next(c["instrument"] for c in cases if c["id"] == cid)
            jsrow = next(x for x in js["cases"] if x["id"] == cid)
            jr = jsrow["results"][code_cid]
            tail = [b for b in r["inferred"].values()
                    if b["status"] == "NO_OWN_ITEM_ANSWERED"]
            jtail = [b for b in jr["inferred"].values()
                     if b["status"] == "NO_OWN_ITEM_ANSWERED"]
            ck(f"硬规则[{cid}]：本维度未答的维度在两侧都禁用且无数值",
               len(tail) == 3 and len(jtail) == 3
               and all(b["confidence_r"] is None and b["predicted_score"] is None
                       and b["r2_total"] is None and b["display_allowed"] is False
                       and b["available"] is False for b in tail)
               and all(b["confidence_r"] is None and b["predicted_score"] is None
                       for b in jtail),
               f"python {len(tail)} 个 / js {len(jtail)} 个 NO_OWN_ITEM_ANSWERED")
        full_id = next(c["id"] for c in cases
                       if c["id"].startswith("IPIP-NEO-") and c["id"].endswith("-full"))
        f = py_results[full_id]
        dim = full_id.split("-")[2]
        ck("答满该维度：预测 == 官方分（精确）",
           abs(f["inferred"][dim]["predicted_score"]
               - f["official"][dim]["value"]) < 1e-12,
           f"{f['inferred'][dim]['predicted_score']} vs {f['official'][dim]['value']}")
        # 跨维借用：两侧的 conf_r 增益都必须为正
        cb = py_results["IPIP-NEO-cross-borrow"]
        d0 = models["IPIP-NEO"].dims[0]
        ck("跨维借用：conf_r 增益 > 0（两侧一致）",
           cb["inferred"][d0]["cross_dim_borrow_gain"] > 0.02,
           f"gain={cb['inferred'][d0]['cross_dim_borrow_gain']:+.4f}")
        a = py_results["IPIP-NEO-all"]
        worst_full = max(abs(b["predicted_score"] - a["official"][k]["value"])
                         for k, b in a["inferred"].items())
        ck("全卷答满：全部 30 个维度预测 == 官方分", worst_full < 1e-12,
           f"max|Δ|={worst_full:.3g}")
        ck("分层：inferred 一律带 inferred=true，official 缺失时 value=None",
           all(b["inferred"] for b in a["inferred"].values())
           and all((o["value"] is None) == (not o["complete"])
                   for o in a["official"].values()))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\n{'❌ ' + str(fail) + ' 项未通过' if fail else '✅ Python↔JS 一致性全部通过'}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
