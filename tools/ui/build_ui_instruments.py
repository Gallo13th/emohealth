#!/usr/bin/env python3
"""生成界面用的**按需加载**数据包：``ui/instruments/<code>.js`` + 清单。

为什么用 ``<script>`` 注入而不是 ``fetch()``
============================================
项目的一个硬性约束是**纯静态、离线可用**（`ui/index.html` 现在可 ``file://`` 打开）。
``fetch('data.json')`` 在 ``file://`` 下会被同源策略拒绝，所以按需加载沿用现有做法：
注入 ``<script src>``，由数据包自己把内容挂到 ``window`` 上。

每个包挂 ``window.EMOHEALTH_INST_<CODE>``（code 已正则化为标识符），
清单 ``ui/instruments.js`` 给出 ``{code: 相对路径}``。

只输出界面真正要用的字段（题项 id/order/text/key、维度、计分、授权、作答格式）：
实测全部 40 套精简后合计 0.4 MB，单套最大 35 KB——按需加载时首屏只需一套。
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
OUT_DIR = os.path.join(ROOT, "ui", "instruments")
MANIFEST = os.path.join(ROOT, "ui", "instruments.js")
TEXT_DB = os.path.join(ROOT, "data", "text-db", "text-db.json")
NORMS_DIR = os.path.join(ROOT, "data", "norms")

#: 从 `data/norms/<code>.json` 随前端包下发的**解释性字段**（导出报告要逐字引用；
#: 界面默认视野一个字都不读它们）。
#:
#: ⚠️ 改这里之前先读三条铁律：
#:   ① **只做加法**：绝不覆盖量表包里已有的 `norms` 键（`setdefault`），也绝不动 `norms_status`；
#:   ② **绝不下发 `facets` / `domains` / `scales`**——界面用 `norms.{facets|domains|scales}`
#:      判「有没有常模」（`ui/index.html` 的 `hasNorms`）。下发它们会把门槛型量表（L1/L2）
#:      误判成「有常模」，默认结果页凭空多出百分位列——违反 D120「界面默认视野只留用户
#:      要判断的东西」；
#:   ③ `source.citation` **展平成 `source_citation` 字符串**：`norms.source` 在
#:      IPIP-NEO / PID-5 的包里本来就是**字符串**，塞个对象进去会让同名字段有两种类型。
NORMS_EXPLAIN_KEYS = ("status", "interpretation_basis", "unavailable_reason",
                      "applicability_warning", "reference_sample", "detail_source")


def norms_explanation(code: str) -> dict:
    """读 `data/norms/<code>.json` 的解释性字段（只取有值的）→ 合并进前端包 `norms`。

    为什么需要：`data/norms/dsm5tr-l1.json` 里有一条**权威**的 `unavailable_reason`
    （「APA 把本册设计为门槛型筛查而非常模参照量表……」），但它原先没随包下发——运行时
    只剩 `norms_status.reason` 那句弱化版（「归档中未找到可溯源的常模」）。
    **两句含义不同**：原文是「手册按设计就不提供」，弱化版读起来像「我们没找到」。
    导出因此做不到逐字引用。这里只补解释性字段，不整包塞（体积与「界面不显示」是两件事）。
    """
    p = os.path.join(NORMS_DIR, code.lower() + ".json")
    if not os.path.exists(p):
        return {}
    with open(p, encoding="utf-8") as fh:
        rec = json.load(fh)
    out = {k: rec[k] for k in NORMS_EXPLAIN_KEYS if rec.get(k) not in (None, "", [], {})}
    src = rec.get("source")
    citation = src.get("citation") if isinstance(src, dict) else None
    if citation:
        out["source_citation"] = citation
    return out


def norm(t: str) -> str:
    """与文本库一致的归一化（含连字符转空格）。"""
    s = (t or "").replace("\u2019", "'").replace("\u2018", "'")
    s = s.replace("\u201c", '"').replace("\u201d", '"')
    s = s.replace("-", " ").replace("\u2013", " ").replace("\u2014", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return re.sub(r"[.\s]+$", "", s).lower()


def load_text_db() -> dict:
    """读统一文本库：归一化题文 → {zh, note, scaffold}。

    界面数据包的中译**只从文本库来**（D113：前端不自己去猜或去翻）；
    `note`/`scaffold` 是译者/审阅者备忘，**不下发**（见 lean() 里的说明）。
    """
    if not os.path.exists(TEXT_DB):
        return {}
    with open(TEXT_DB, encoding="utf-8") as fh:
        return (json.load(fh).get("entries") or {})


def ident(code: str) -> str:
    return "EMOHEALTH_INST_" + re.sub(r"[^A-Za-z0-9]", "_", code).upper()


def lean(d: dict, tdb: dict) -> dict:
    """只保留界面需要的字段，并保留溯源信息（授权、引用、结构）。

    题项**带上中译**（取自统一文本库 D113）与英文原文：界面既能默认显示中文，
    也能随时回看原题。**不带**文本库里的 `note` / `scaffold`——那是译者/审阅者备忘，
    界面不许出现开发者文案（D120），见下面那一行的说明。
    """
    items = []
    for x in d["items"]:
        e = tdb.get(norm(x["text"])) or {}
        row = {"order": x["order"], "id": x["id"], "text": x["text"],
               "key": x.get("key", 1)}
        if e.get("zh"):
            row["zh"] = e["zh"]
        # ⚠️ **不下发**文本库里的 `note` / `scaffold`——它们是**译者/审阅者备忘**：
        #    · `note`  例：「测快感缺失：…」「原文 enjoylife 为排版噪声…」
        #    · `scaffold` 是结构化的逐题审阅注释 {asks, counts, mis, loc, edge}（300 条）
        #    它们**留在 `data/text-db/text-db.json`** 作为溯源资产（D113 的中间产物，
        #    也供 build_item_structured / check_text_db / audit_capabilities 使用），
        #    但**不该随前端包发出去**：界面不许出现开发者/审阅者文案（D120）。
        #    只靠界面不渲染是「一层」；**不发才是纵深防御的第二层**——下一个人手滑加
        #    一行 `it.note` 渲染就又漏了。下发 ≠ 渲染，反过来也一样：不该下发的别下发。
        #    （历史：这两行曾把 PID-5 的 220 条备忘、IPIP-NEO 的 300 条 scaffold 发到前端。）
        if x.get("kind"):
            row["kind"] = x["kind"]
        # ⚠️ 每题自己的选项组必须带出去（Mania 每题是一组整句陈述、Repetitive 各题
        #    锚点不同）。**规范位置是 `items[].options`**。此前这里没拷这个字段，
        #    界面只能绕道读 `provenance.item_options` 镜像——镜像删掉后若不补这一行，
        #    Mania 的 5 行选项会**静默变空**（2026-10-04 收口时发现）。
        if x.get("options"):
            row["options"] = x["options"]
        if x.get("options_evidence"):
            row["options_evidence"] = x["options_evidence"]
        items.append(row)
    prov = {k: v for k, v in (d.get("provenance") or {}).items()
            if k not in ("item_options", "item_options_mirror_note")}
    # 常模的解释性字段（导出用）：从 `data/norms/<code>.json` 补进 `norms`。
    # ⚠️ 只做加法（setdefault），且绝不下发 facets/domains/scales——见 NORMS_EXPLAIN_KEYS 的说明。
    norms = dict(d.get("norms") or {})
    for k, v in norms_explanation(d["instrument"]).items():
        norms.setdefault(k, v)
    return {
        "instrument": d["instrument"],
        "display_name": d["display_name"],
        "citation": d.get("citation", ""),
        "license": d["license"],
        "structure": d["structure"],
        "response_format": d["structure"]["response_format"],
        "items": items,
        "dimensions": [{"id": x["id"], "name": x["name"], "level": x.get("level", 1),
                        **({"parent": x["parent"]} if x.get("parent") else {}),
                        **({"children": x["children"]} if x.get("children") else {}),
                        **({"items": x["items"]} if x.get("items") else {}),
                        **({"reverse_keyed": x["reverse_keyed"]}
                           if x.get("reverse_keyed") else {})}
                       for x in d["dimensions"]],
        "scoring": d["scoring"],
        "norms": norms,
        "norms_status": d.get("norms_status", {}),
        # 判读口径（如 DSM-5-TR L1 的「门槛」）：界面据此呈现判定，
        # 而不是硬套百分位——L1 不是常模量表。
        "interpretation": d.get("interpretation", {}),
        # 链路关系（DSM-5-TR L1 → L2 → PID-5）：界面据此做可点跳转
        "linkage": d.get("linkage", {}),
        # 判读口径（分带/分界/逐项/T 分）：八册互不相同
        "criteria": d.get("criteria", {}),
        "criteria_source": d.get("criteria_source", ""),
        "provenance": prov,
    }


def main() -> int:
    # ── 前端闸门（D113）：文本库没定稿就不生成前端数据包。
    #    理由：文本库错了能在校验里拦住，前端错了用户直接看到错题。
    if "--allow-incomplete-text" not in sys.argv:
        import subprocess
        chk = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "check",
                                                           "check_text_db.py"),
                              "--require-full"],
                             capture_output=True, text=True, encoding="utf-8",
                             errors="replace", cwd=ROOT)
        tail = [ln for ln in (chk.stdout or "").splitlines() if ln.strip()][-3:]
        if chk.returncode != 0:
            print("✗ 文本库未通过校验，按 D113 不生成前端数据包：")
            for ln in tail:
                print("   ", ln)
            print("\n（确需跳过请显式加 --allow-incomplete-text）")
            return 1
        print("✓ 文本库校验通过")

    os.makedirs(OUT_DIR, exist_ok=True)
    paths = [p for p in sorted(glob.glob(
        os.path.join(ROOT, "data", "instruments", "*.json")))
        if os.path.basename(p) != "catalog.json"]

    manifest: dict[str, str] = {}
    TDB = load_text_db()
    print(f"文本库 {len(TDB)} 条（用于填中译；`note`/`scaffold` 是译者备忘，不下发）")
    total = 0
    biggest = ("", 0)
    for p in paths:
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
        code = d["instrument"]
        payload = lean(d, TDB)
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        fn = os.path.basename(p).replace(".json", ".js")
        header = (f"/* {code}｜{len(d['items'])} 题｜"
                  f"授权 {d['license']['kind']}｜由 tools/ui/build_ui_instruments.py 生成，勿手改 */\n")
        with open(os.path.join(OUT_DIR, fn), "w", encoding="utf-8") as fh:
            fh.write(header)
            fh.write(f"window.{ident(code)} = ")
            fh.write(body)
            fh.write(";\n")
        size = os.path.getsize(os.path.join(OUT_DIR, fn))
        total += size
        if size > biggest[1]:
            biggest = (code, size)
        manifest[code] = f"instruments/{fn}"

    with open(MANIFEST, "w", encoding="utf-8") as fh:
        fh.write("/* 界面按需加载清单（由 tools/ui/build_ui_instruments.py 生成）\n"
                 "   用法：loadInstrument(code) 注入 <script>，再从 window 上取数据。\n"
                 "   tree：> 60 题的量表另有天赋树布局，字段同 net-layout.js。 */\n")
        fh.write("window.EMOHEALTH_INSTMAP = ")
        json.dump(manifest, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write(";\n")
        # 天赋树布局清单：只有 > 60 题的量表有（D114）
        tl_index = os.path.join(ROOT, "ui", "tree-layouts", "index.json")
        tree = {}
        if os.path.exists(tl_index):
            for s in json.load(open(tl_index, encoding="utf-8"))["scales"]:
                tree[s["code"]] = "tree-layouts/" + os.path.basename(s["file"])
        fh.write("window.EMOHEALTH_TREEMAP = ")
        json.dump(tree, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write(";\n")

    print(f"生成 {len(manifest)} 个界面数据包 → ui/instruments/")
    if tree:
        print(f"其中 {len(tree)} 套带天赋树布局（> 60 题）")
    print(f"合计 {total / 1024:.0f} KB；最大单套 {biggest[0]} {biggest[1] / 1024:.0f} KB")
    print(f"清单 → {os.path.relpath(MANIFEST, ROOT)}"
          f"（{os.path.getsize(MANIFEST) / 1024:.1f} KB）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
