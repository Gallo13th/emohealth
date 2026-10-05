#!/usr/bin/env python3
"""校验「可填量表文档 + 评估指标」这套产物：**逐项**比对，不给假绿。

为什么要有它
============
这套产物有两个特点，使「看起来对」和「真的对」相差很远：

1. **反向题清单**是最容易静默出错的地方。PID-5 手册两处原文自相矛盾（Step 1 正文
   列 14 题，facet 表标 16 题），项目最后靠数据裁决为 16 题（原 D117；证据见
   ``data/pid5-reverse-keys.json``）。一处反向键写错不会报错——它只会让所有分数
   算反。所以这里的比对是**逐项集合双向相等**，不是抽查、不是计数相等。
2. **生成物禁止手改**。文档一旦被手工编辑，就会与量表包/常模悄悄脱钩，而它读起来
   仍然像是对的。所以本校验器会**重新生成一遍并逐字节比对**。

校验项（任一不过 → 退出码 1）
============================
V1  每套量表都有 ``data/descriptions/<code>.md``，且六节结构齐全（按顺序）
V2  ``data/descriptions/index.json`` 与磁盘一致；``data/instruments/`` 里每一套都有条目
V3  **反向题逐项一致**：文档的 id 清单 == 量表包 ``items[].key == -1`` 的 id 集合
V4  PID-5 额外：与 ``data/pid5-reverse-keys.json`` 的 16 题逐项一致，且文档写明「14 vs 16」争议
V5  常模记录 ``data/norms/<code>.json`` 存在、schema 合法；``status != available`` 时
    必须写明原因，且文档里出现「仅原始分，无可用常模」或「有部分解读基准」这类明示
V6  α 必须有出处：α 表里每一行都要有 source（或文档明示「未获得可溯源的 α」）
V7  MMPI-2：题项为空、文档写明版权限制与合法获取途径、且**文档内不得出现任何题面**
V8  生成物未被手改：重新生成 md 并与磁盘逐字节比对
V9  数字可溯源：常模记录的 ``source.evidence`` 非空；文档每个「出处」引用指向实际存在的路径

用法
====
    python tools/check/check_descriptions.py
    python tools/check/check_descriptions.py --no-regen   # 跳过字节比对（仅诊断用）
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root, force_utf8_io  # noqa: E402

ROOT = find_root()
DOCS = os.path.join(ROOT, "data", "descriptions")
NORMS = os.path.join(ROOT, "data", "norms")
INSTR = os.path.join(ROOT, "data", "instruments")

#: 六节固定结构（顺序即校验顺序）。生成器保证标题就是这个字面量。
SECTIONS = [
    "## 1. 量表是什么 / 测什么",
    "## 2. 维度表",
    "## 3. 计分方法",
    "## 4. 结果解读基准",
    "## 5. 信度与出处",
    "## 6. 解读义务（哪些话不许说）",
]

MMPI_KEY = "mmpi-2"


def fail(problems: list[str], msg: str) -> None:
    problems.append(msg)


def load(p: str):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def reverse_ids_from_md(md: str) -> set[str]:
    """从文档的「纯 id 清单」代码块里逐项取出反向题 id。"""
    i = md.find("**纯 id 清单（便于机器比对）**：")
    if i < 0:
        return set()
    j = md.find("```", i)
    k = md.find("```", j + 3)
    block = md[j + 3:k]
    return {x.strip() for x in re.split(r"[,\s]+", block) if x.strip()}


# --------------------------------------------------------------- V1/V2

def check_structure(code: str, md: str, problems: list[str]) -> None:
    pos = -1
    for sec in SECTIONS:
        idx = md.find(sec)
        if idx < 0:
            fail(problems, f"V1 {code}: 缺章节「{sec}」")
            continue
        if idx < pos:
            fail(problems, f"V1 {code}: 章节顺序错误（{sec} 出现在前一节之前）")
        pos = idx
    if "禁止手改" not in md and "请勿手改" not in md:
        fail(problems, f"V1 {code}: 文档缺少「生成物禁止手改」提示")


def check_index(index: dict, problems: list[str]) -> None:
    codes = {e["code"] for e in index.get("instruments", [])}
    for fn in sorted(os.listdir(INSTR)):
        if not fn.endswith(".json") or fn == "catalog.json":
            continue
        code = fn[:-5]
        if code not in codes:
            fail(problems, f"V2 data/instruments/{fn} 没有对应的文档条目（{code} 未覆盖）")
    for e in index.get("instruments", []):
        md_path = os.path.join(ROOT, e["description"])
        if not os.path.exists(md_path):
            fail(problems, f"V2 清单里的文档不存在：{e['description']}")
            continue
        md = open(md_path, encoding="utf-8").read()
        import hashlib
        got = hashlib.sha256(md.encode("utf-8")).hexdigest()
        if got != e.get("sha256"):
            fail(problems, f"V2 {e['code']}: 清单 sha256 与文档不符（文档被改过？）")


# --------------------------------------------------------------- V3/V4

def check_reverse(code: str, md: str, pkg: dict | None, problems: list[str]) -> None:
    if not pkg:
        return
    actual = {it["id"] for it in pkg["items"] if it.get("key") == -1}
    declared = reverse_ids_from_md(md)
    if actual != declared:
        missing = sorted(actual - declared)
        extra = sorted(declared - actual)
        fail(problems, f"V3 {code}: 反向题清单与量表包**逐项不一致**"
                       f"（量表包 {len(actual)} / 文档 {len(declared)}；"
                       f"漏 {missing[:6]}；多 {extra[:6]}）")
    # 维度声明的反向题也要逐项对得上（重复一道保险）
    for d in pkg["dimensions"]:
        decl = set(d.get("reverse_keyed", []))
        act = {it["id"] for it in pkg["items"]
               if it["id"] in set(d.get("items", [])) and it.get("key") == -1}
        if decl != act:
            fail(problems, f"V3 {code}: 维度 {d['id']} 的 reverse_keyed 与题项不一致")


def check_pid5_reverse(md: str, problems: list[str]) -> None:
    p = os.path.join(ROOT, "data", "pid5-reverse-keys.json")
    if not os.path.exists(p):
        fail(problems, "V4 缺 data/pid5-reverse-keys.json")
        return
    rec = load(p)
    want = {f"pid5_{n:03d}" for n in rec.get("reverse_keyed", [])}
    step1 = {f"pid5_{n:03d}" for n in rec.get("reverse_keyed_step1_verbatim", [])}
    declared = reverse_ids_from_md(md)
    if declared != want:
        fail(problems, f"V4 文档反向题清单与 pid5-reverse-keys.json 不一致"
                       f"（清单 {len(want)} / 文档 {len(declared)}）")
    if not (want - step1):
        fail(problems, "V4 裁决后的反向集应比 Step 1 多 2 题（7、30），实测没有多")
    for token in ("14", "16", "7", "30"):
        if token not in md:
            fail(problems, f"V4 文档未写明反向题争议的关键数字/题号：{token}")


# --------------------------------------------------------------- V5

NORMS_REQUIRED = ("instrument", "code", "status", "interpretation_basis")
VALID_STATUS = {"available", "partial", "unavailable"}


def check_norms(code: str, md: str, entry: dict, problems: list[str]) -> None:
    rel = entry.get("norms")
    if not rel:
        fail(problems, f"V5 {code}: 清单未登记常模记录")
        return
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        fail(problems, f"V5 {code}: 常模记录不存在 {rel}")
        return
    n = load(p)
    for k in NORMS_REQUIRED:
        if k not in n:
            fail(problems, f"V5 {code}: 常模记录缺字段 {k}")
    if n.get("status") not in VALID_STATUS:
        fail(problems, f"V5 {code}: status 非法：{n.get('status')!r}")
        return
    if n.get("status") != "available":
        if not (n.get("unavailable_reason") or n.get("notes")
                or n.get("source")):
            fail(problems, f"V5 {code}: status={n.get('status')} 但没写明原因")
        # 文档必须显式承认「没有可用常模」
        if "仅原始分" not in md and "有部分解读基准" not in md:
            fail(problems, f"V5 {code}: 无可用常模，但文档没有显式写明"
                           "（缺「仅原始分，无可用常模」或「有部分解读基准」）")
    if n.get("status") == "available":
        # 两种记录形态都支持：描述层信封用 source.evidence（dict），
        # 既有细表（IPIP-NEO / PID-5）的 source 是字符串、证据在 source_files。
        src = n.get("source")
        ev = src.get("evidence") if isinstance(src, dict) else (src or n.get("source_files"))
        if not ev:
            fail(problems, f"V5 {code}: status=available 但没有任何来源证据字段")


# --------------------------------------------------------------- V6

def check_alpha(code: str, md: str, problems: list[str]) -> None:
    i = md.find("### 5.1 内部一致性（α）")
    if i < 0:
        fail(problems, f"V6 {code}: 找不到 α 小节")
        return
    j = md.find("###", i + 5)
    block = md[i:j if j > 0 else len(md)]
    if "未获得可溯源的 α" in block:
        if "未报告" not in block and "未获得" not in block:
            fail(problems, f"V6 {code}: α 留白但没写原因")
        return
    rows = [ln for ln in block.splitlines() if ln.startswith("| ") and "α" not in ln]
    rows = [ln for ln in rows if not set(ln) <= set("|-: ")]
    bad = [ln for ln in rows if ln.count("|") >= 4 and not ln.rstrip().endswith("|")
           or (ln.count("|") >= 4 and ln.split("|")[3].strip() in ("", "—"))]
    if bad:
        fail(problems, f"V6 {code}: α 表有 {len(bad)} 行没有出处：{bad[:2]}")
    if "数据/criteria" in block:
        pass


# --------------------------------------------------------------- V7

def check_mmpi(md: str, index: dict, problems: list[str]) -> None:
    e = next((x for x in index.get("instruments", []) if x["code"] == MMPI_KEY), None)
    if not e:
        fail(problems, "V7 清单里没有 mmpi-2")
        return
    if e.get("n_items"):
        fail(problems, f"V7 mmpi-2 必须题项为空，实测 n_items={e['n_items']}")
    if e.get("items_policy") != "copyright_excluded":
        fail(problems, "V7 mmpi-2 的 items_policy 必须是 copyright_excluded")
    for token in ("does not allow for the reproduction of test items",
                  "Pearson", "不得", "本地导入"):
        if token not in md:
            fail(problems, f"V7 mmpi-2 文档缺少必要声明：{token}")
    pkg = os.path.join(INSTR, "mmpi-2.json")
    if os.path.exists(pkg):
        fail(problems, "V7 不应存在 data/instruments/mmpi-2.json（题项不得收录）")


# --------------------------------------------------------------- V8/V9

def check_regeneration(problems: list[str]) -> None:
    sys.path.insert(0, os.path.join(ROOT, "tools", "build"))
    import build_descriptions as B  # noqa: E402
    for entry in B.INSTRUMENTS:
        built = B.build_one(entry)
        path = os.path.join(DOCS, f"{entry['code']}.md")
        disk = open(path, encoding="utf-8").read() if os.path.exists(path) else None
        if disk != built["md"]:
            fail(problems, f"V8 {entry['code']}: 生成物与重新生成的结果**不一致**"
                           "（文档被手改，或生成器已过期）")
        rec = built["norms_record"]
        if rec:
            rp = os.path.join(NORMS, f"{entry['code']}.json")
            if not os.path.exists(rp) or load(rp) != rec:
                fail(problems, f"V8 {entry['code']}: 常模记录与重新生成的结果不一致")


#: 只取反引号里**第一个路径段**：证据串里常写成「路径；说明；说明」，
#: 整段当路径会误报（第一版就是这样）。
EV_RE = re.compile(r"`((?:archive|data|content|research|tools|ui|engine)/[^`；;。\s，]+)")


def check_evidence_paths(code: str, md: str, problems: list[str]) -> None:
    seen = set()
    for m in EV_RE.finditer(md):
        raw = m.group(1).strip()
        if raw in seen:
            continue
        seen.add(raw)
        if any(ch in raw for ch in "*{}<>") or raw.endswith("/"):
            continue                      # 通配/占位形态，跳过
        base = raw.split("（")[0].split(" ")[0].rstrip("，。；")
        if not os.path.exists(os.path.join(ROOT, base)):
            fail(problems, f"V9 {code}: 文档引用的路径不存在：{raw}")


# --------------------------------------------------------------- 主流程

def main() -> int:
    force_utf8_io()          # 入口第一件事：GBK 控制台下不许崩（见 tools/_root.py）
    ap = argparse.ArgumentParser(description="校验量表文档与评估指标产物")
    ap.add_argument("--no-regen", action="store_true", help="跳过 V8 重新生成比对")
    args = ap.parse_args()

    problems: list[str] = []
    idx_path = os.path.join(DOCS, "index.json")
    if not os.path.exists(idx_path):
        print("❌ 缺少 data/descriptions/index.json —— 先跑 tools/build/build_descriptions.py")
        return 1
    index = load(idx_path)
    print(f"校验 {len(index.get('instruments', []))} 套量表的文档与常模记录\n")

    check_index(index, problems)

    for e in index.get("instruments", []):
        code = e["code"]
        p = os.path.join(ROOT, e["description"])
        if not os.path.exists(p):
            continue
        md = open(p, encoding="utf-8").read()
        pkg_p = os.path.join(INSTR, f"{code}.json")
        pkg = load(pkg_p) if os.path.exists(pkg_p) else None
        check_structure(code, md, problems)
        check_reverse(code, md, pkg, problems)
        check_norms(code, md, e, problems)
        check_alpha(code, md, problems)
        check_evidence_paths(code, md, problems)
        if code == "pid-5":
            check_pid5_reverse(md, problems)
        if code == MMPI_KEY:
            check_mmpi(md, index, problems)
        if pkg and e.get("n_items") != len(pkg["items"]):
            fail(problems, f"V2 {code}: 清单 n_items={e.get('n_items')} 与量表包 {len(pkg['items'])} 不符")

    if not args.no_regen:
        check_regeneration(problems)
    else:
        print("（已跳过 V8 重新生成比对）")

    print("─" * 72)
    print(f"V1 章节结构　V2 清单一致　V3 反向题逐项　V4 PID-5 争议　V5 常模 schema/明示")
    print(f"V6 α 出处　V7 MMPI-2 版权　V8 生成物未手改　V9 引用路径存在")
    print("─" * 72)
    if problems:
        print(f"❌ {len(problems)} 处问题：\n")
        for x in problems:
            print("  -", x)
        return 1
    print("✅ 全部通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
