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


def norm(t: str) -> str:
    """与文本库一致的归一化（含连字符转空格）。"""
    s = (t or "").replace("\u2019", "'").replace("\u2018", "'")
    s = s.replace("\u201c", '"').replace("\u201d", '"')
    s = s.replace("-", " ").replace("\u2013", " ").replace("\u2014", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return re.sub(r"[.\s]+$", "", s).lower()


def load_text_db() -> dict:
    """读统一文本库：归一化题文 → {zh, note}。

    界面数据包的中译与注释**只从文本库来**（D113：前端不自己去猜或去翻）。
    """
    if not os.path.exists(TEXT_DB):
        return {}
    with open(TEXT_DB, encoding="utf-8") as fh:
        return (json.load(fh).get("entries") or {})


def ident(code: str) -> str:
    return "EMOHEALTH_INST_" + re.sub(r"[^A-Za-z0-9]", "_", code).upper()


def lean(d: dict, tdb: dict) -> dict:
    """只保留界面需要的字段，并保留溯源信息（授权、引用、结构）。

    题项**带上中译与注释**：中译取自统一文本库（D113），英文原文一并保留，
    这样界面既能默认显示中文，也能随时回看原题。
    """
    items = []
    for x in d["items"]:
        e = tdb.get(norm(x["text"])) or {}
        row = {"order": x["order"], "id": x["id"], "text": x["text"],
               "key": x.get("key", 1)}
        if e.get("zh"):
            row["zh"] = e["zh"]
        if e.get("note"):
            row["note"] = e["note"]
        if e.get("scaffold"):
            row["scaffold"] = e["scaffold"]
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
        "norms": d.get("norms", {}),
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
    print(f"文本库 {len(TDB)} 条（用于填中译与注释）")
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
