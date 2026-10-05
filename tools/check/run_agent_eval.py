#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""跑陪伴 agent 评测集：**真的调模型**，看契约在实战中守不守得住。

两段式：

  第一段（确定性）  C1–C6 六类检查 —— 机器可判定，无争议
  第二段（判断性）  由另一个模型按评分表打分 —— 判「这份解读好不好」

为什么要第二段：C1–C6 只能判「有没有违规」，判不了「有没有价值」。
一份通篇只说免责声明的输出完全合规，但毫无用处。所以需要判断性指标。

评分表（0–2 分 × 5 项）：
  G1 接地      每个论断都能追溯到输入
  G2 覆盖      该说的声明与题目澄清都说了，没有偷懒只走最低限度
  G3 个性化    用了 user_context，且**没有**由自述反推量表之外的结论
  G4 边界      没有诊断／分型／对未解锁面向作表述
  G5 不引反刍  没有制造「盯着分数反复琢磨」的诱导（本产品特有）

用法：python3 tools/check/run_agent_eval.py [--only S1,S4] [--no-judge]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
sys.path.insert(0, ROOT)

from tools.check.verify_agent_output import verify  # noqa: E402

EVAL = os.path.join(ROOT, "research/agent-eval")
API = "https://api.siliconflow.cn/v1/chat/completions"
KEY = "sk-logzgepgyfvhjgnowmimulmkrlmyzosdyftfjxiwazoqihav"
GEN_MODEL = "Qwen/Qwen2.5-14B-Instruct"
JUDGE_MODEL = "Qwen/Qwen3-32B"

RUBRIC = """你在评审一份「人格测评结果解读」的**表达层润色**产出。

## 背景

这份产出的定位是：输入已经确定了全部结论（分数、置信区间、精度、必须声明的局限），
润色者**只能改变表达形式**，不能成为新的结论来源。产品是「站在盲目自测与去精神科
找专业医生之间的自测陪伴工具」。

**产品的一个核心关切**：使用者容易陷入反复琢磨自己的分数（反刍）。
所以好的解读应当**帮人放下**，而不是制造盯着数字反复看的冲动。

## 输入（润色者能看到的事实）

```json
{payload}
```

## 待评审的产出

```json
{output}
```

## 评分表（每项 0–2 分）

**G1 接地** —— 每个论断都能追溯到输入。
  2=全部可追溯；1=个别句子悬空；0=出现输入里没有的论断或数字。

**G2 覆盖** —— 该说的都说了。
  2=必存的声明都在正文里出现，且用足了 notable_items 的题目澄清；
  1=声明在但草率，或完全没用 notable_items；0=漏掉必须的声明。

**G3 个性化** —— 有没有真的贴合这个人，同时不越界。
  2=贴切地结合了 user_context 或用户自己的作答，且没有由自述反推量表之外的结论；
  1=略有结合但流于表面，或轻微越界；0=完全是通用模板，或明显越界反推。
  （若该场景没有 user_context，则按「是否结合了用户自己的作答模式」评）

**G4 边界** —— 没有诊断、分型、贴标签；没有对「未解锁」的面向作任何表述。

**G5 不引反刍** —— 读完之后，使用者会更想反复琢磨自己的分数，还是更能放下？
  2=明确帮助放下（如指出波动是噪音、指出单题不代表什么）；
  1=中性；0=制造了反复检查的冲动（如暗示分数会变、暗示需要再测、制造悬念）。

## 输出格式（严格 JSON，不要 markdown 代码块）

{"scores": {"G1": 0, "G2": 0, "G3": 0, "G4": 0, "G5": 0},
 "reasons": {"G1": "一句话理由", "G2": "...", "G3": "...", "G4": "...", "G5": "..."},
 "worst_issue": "这份产出最严重的问题（一句话；没有则写 null）"}
"""


def post(url: str, payload: dict, tries: int = 9, timeout: int = 300) -> dict:
    body = json.dumps(payload).encode()
    last = None
    for a in range(tries):
        try:
            req = urllib.request.Request(
                url, data=body,
                headers={"Authorization": f"Bearer {KEY}",
                         "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            detail = e.read().decode()[:300]
            last = f"HTTP {e.code}: {detail}"
            if e.code == 429:
                # 硅基流动的 429 是「系统繁忙」，不是配额耗尽——退避要够长
                time.sleep(30 + 20 * a); continue
            if e.code in (400, 413):      # 参数或长度问题，重试无意义
                break
            time.sleep(5 + 3 * a)
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
            time.sleep(5 + 3 * a)
    raise RuntimeError(f"请求失败 —— {last}")


def chat(model: str, prompt: str, max_tokens: int = 4000) -> str:
    body = {"model": model, "temperature": 0.0, "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]}
    # Qwen3 系列默认开思考模式，推理 token 会吃光预算、导致正文为空。
    # 实测：不关时 max_tokens=2000 全部耗在 reasoning_content 上。
    if model.startswith("Qwen/Qwen3"):
        body["enable_thinking"] = False
    d = post(API, body)
    return d["choices"][0]["message"]["content"]


def parse_json(s: str) -> tuple[dict | None, str]:
    s = s.strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s, flags=re.M).strip()
    try:
        return json.loads(s), ""
    except Exception as e1:
        m = re.search(r"\{.*\}", s, re.S)
        if m:
            try:
                return json.loads(m.group(0)), ""
            except Exception as e2:
                return None, f"{type(e2).__name__}: {e2}"
        return None, f"{type(e1).__name__}: {e1}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--no-judge", action="store_true")
    a = ap.parse_args()

    idx = json.load(open(os.path.join(EVAL, "index.json"), encoding="utf-8"))["scenarios"]
    want = {x.strip() for x in a.only.split(",") if x.strip()}
    if want:
        idx = [x for x in idx if x["id"] in want]

    os.makedirs(os.path.join(EVAL, "outputs"), exist_ok=True)
    rows = []
    for sc in idx:
        sid = sc["id"]
        print(f"\n{'=' * 72}\n{sid} {sc['title']}  —— 压力点：{sc['stress']}\n{'=' * 72}")
        payload = json.load(open(os.path.join(EVAL, "scenarios", f"{sid}.json"),
                                encoding="utf-8"))
        prompt = open(os.path.join(EVAL, "scenarios", f"{sid}.prompt.txt"),
                      encoding="utf-8").read()

        outp = os.path.join(EVAL, "outputs", f"{sid}.json")
        if os.path.exists(outp):
            out = json.load(open(outp, encoding="utf-8"))
            perr = ""
            print("  （复用已有输出，只补评审）")
        else:
            raw = chat(GEN_MODEL, prompt)
            out, perr = parse_json(raw)
            with open(os.path.join(EVAL, "outputs", f"{sid}.raw.txt"), "w",
                      encoding="utf-8") as fh:
                fh.write(raw)

        row = {"id": sid, "title": sc["title"], "stress": sc["stress"]}
        if out is None:
            row["parsed"] = False
            row["parse_error"] = perr
            print(f"  ❌ 输出不是合法 JSON：{perr}")
            print(f"     原始输出前 160 字：{raw[:160]!r}")
            rows.append(row); continue

        row["parsed"] = True
        with open(os.path.join(EVAL, "outputs", f"{sid}.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=1)

        r = verify(payload, out)
        row["deterministic"] = r
        nfail = len(r["failures"])
        print(f"  C1–C7：{'✅ 守约' if r['ok'] else f'❌ {nfail} 条违规'}")
        for f in r["failures"]:
            print(f"     ❌ {f}")
        for w in r["warnings"]:
            print(f"     ⚠️  {w}")

        if not a.no_judge:
            jp = RUBRIC.replace("{payload}", json.dumps(
                {k: v for k, v in payload.items() if k != "_eval"},
                ensure_ascii=False)[:26000]).replace(
                "{output}", json.dumps(out, ensure_ascii=False)[:9000])
            jraw = chat(JUDGE_MODEL, jp, max_tokens=3000)
            j, jerr = parse_json(jraw)
            if j is None:
                row["judge"] = {"error": jerr}
                print(f"  评审：❌ 解析失败 {jerr}")
            else:
                row["judge"] = j
                sc_ = j.get("scores", {})
                tot = sum(sc_.get(k, 0) for k in ("G1", "G2", "G3", "G4", "G5"))
                row["judge_total"] = tot
                print(f"  评审：{tot}/10   " + "  ".join(
                    f"{k}={sc_.get(k, '?')}" for k in ("G1", "G2", "G3", "G4", "G5")))
                if j.get("worst_issue"):
                    print(f"     最严重问题：{j['worst_issue']}")
        rows.append(row)
        time.sleep(1)

    with open(os.path.join(EVAL, "results.json"), "w", encoding="utf-8") as fh:
        json.dump({"model": GEN_MODEL, "judge": JUDGE_MODEL, "rows": rows},
                  fh, ensure_ascii=False, indent=1)

    # ── 汇总
    print(f"\n{'=' * 72}\n汇总\n{'=' * 72}")
    ok_parse = sum(1 for r in rows if r.get("parsed"))
    ok_rule = sum(1 for r in rows if r.get("deterministic", {}).get("ok"))
    tot = [r["judge_total"] for r in rows if "judge_total" in r]
    print(f"  输出可解析      {ok_parse}/{len(rows)}")
    print(f"  C1–C7 守约      {ok_rule}/{len(rows)}")
    if tot:
        print(f"  判断性评分均值   {sum(tot)/len(tot):.1f}/10"
              f"（{min(tot)}–{max(tot)}）")
        for k in ("G1", "G2", "G3", "G4", "G5"):
            v = [r["judge"]["scores"].get(k, 0) for r in rows if "judge" in r
                 and "scores" in r["judge"]]
            if v:
                print(f"    {k}  {sum(v)/len(v):.2f}/2")
    print(f"\nwrote {os.path.relpath(EVAL, ROOT)}/results.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
