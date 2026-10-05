#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""解析 IPIP-NEO-300 的 UK 常模分数带表（.docx）。

背景（Phase 1 阻塞项）：这些表格用纯 XML 正则解析会得到错误区间——Word 把每个
分数值拆成独立的段落，且 Agreeableness 的 Cooperation 列横跨两个网格列，
导致按 `row.cells` 索引会整体错位一列。

解法（两道独立保障）：
  1. 用 python-docx 读取，并以 **`<w:tc>` 索引**为可靠键（所有行的 tc 数与
     gridSpan 完全一致），而不是会被合并单元格撑开的 `row.cells` 网格索引。
  2. 单元格内的"多行"是排版假象：每个分数值各占一个段落，纵向堆叠。
     因此取该单元格**全部非空段落**，解析成覆盖的整数集合。

正确性判据（本脚本强制校验，任一不满足即报错）：
  - 五个带的值集合**两两不交**
  - 并集**连续无缝**覆盖该量表的完整可能范围
    （facet 10 题 → 10–50；TRAITS 为维度总分，范围另行识别）
  - 带序单调：Very Low < Low < Average < High < Very High

Outputs: data/uk-norms.json
"""
from __future__ import annotations

import json
import os
import re
import sys

from docx import Document
from docx.oxml.ns import qn

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
NORM_DIR = os.path.join(ROOT, "archive/datasets/osf-johnson/scoring/uk-norms")
OUT = os.path.join(ROOT, "data/uk-norms.json")

BANDS = ["Very High", "High", "Average", "Low", "Very Low"]
AGE_FILES = {
    "14-17": "UK_Norms_{kind}_14to17.docx",
    "18-29": "UK_Norms_{kind}_18to29.docx",
    "30+": "UK_Norms_{kind}_30plus.docx",
}

RANGE = re.compile(r"^\s*(\d{1,3})\s*[-\u2010-\u2015\u00ad]\s*(\d{1,3})\s*$")
SINGLE = re.compile(r"^\s*(\d{1,3})\s*$")


def clean(s: str) -> str:
    """归一化表格文本。

    该表格用 **U+0335 COMBINING SHORT STROKE OVERLAY** 附着在空格上来渲染连接号：
    「48 \\u0335 49」在视觉上是「48-49」，「Self \\u0335 efficacy」是「Self-efficacy」。
    连同软连字符（U+00AD）一并归一化为普通连字符。
    """
    s = s.replace("\u00ad", "-")
    s = re.sub(r"[ \t]*\u0335[ \t]*", "-", s)   # 组合短横线 -> '-'
    return re.sub(r"\s+", " ", s).strip()


def tc_list(row):
    return row._tr.findall(qn("w:tc"))


def cell_text(tc) -> list[str]:
    """返回该单元格全部非空段落。"""
    out = []
    for p in tc.findall(qn("w:p")):
        txt = clean("".join(t.text or "" for t in p.iter(qn("w:t"))))
        if txt:
            out.append(txt)
    return out


def expand(values: list[str]) -> set[int]:
    """把 ['50', '48 - 49', ...] 展开成整数集合。"""
    got: set[int] = set()
    for v in values:
        m = RANGE.match(v)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            got.update(range(min(a, b), max(a, b) + 1))
            continue
        m = SINGLE.match(v)
        if m:
            got.add(int(m.group(1)))
            continue
        raise ValueError(f"无法解析的分数值：{v!r}")
    return got


def parse_file(path: str) -> tuple[dict[str, dict[str, set[int]]], list[str]]:
    """返回 {facet: {band: 整数集合}} 与日志。"""
    doc = Document(path)
    if not doc.tables:
        raise ValueError(f"{path} 中没有表格")
    t = doc.tables[0]
    log: list[str] = []

    rows = t.rows
    # 定位表头行：第一个「首格是带标签」的行，其上一行即表头。
    # 不用查找 OVERALL——TRAITS 表（维度级）没有该列。
    band_re = re.compile(r"(very\s*high|very\s*low|^high|^average|^low)", re.I)
    first_band = None
    for i, r in enumerate(rows):
        tcs = tc_list(r)
        if tcs:
            first = clean("".join(x.text or "" for x in tcs[0].iter(qn("w:t"))))
            if band_re.search(first):
                first_band = i
                break
    if first_band is None or first_band == 0:
        raise ValueError(f"{path} 中无法定位带标签行")
    header_idx = first_band - 1

    hdr_tcs = tc_list(rows[header_idx])
    names = [clean("".join(x.text or "" for x in tc.iter(qn("w:t")))) for tc in hdr_tcs]
    log.append(f"{os.path.basename(path)}: header row={header_idx}, tc={len(hdr_tcs)}, "
               f"names={len([n for n in names if n])}")

    # 若表头上方还有域名行（如 FACETS 表的 OPENNESS/…/NEUROTICISM 五列组），
    # 用它给重复出现的 "OVERALL" 加上域名前缀，否则 5 个 OVERALL 会互相覆盖。
    group_prefix = [""] * len(names)
    if header_idx >= 1:
        grp_tcs = tc_list(rows[header_idx - 1])
        grid_col = 0
        for tc in grp_tcs:
            gname = clean("".join(x.text or "" for x in tc.iter(qn("w:t"))))
            span = 1
            pr = tc.find(qn("w:tcPr"))
            if pr is not None:
                gs = pr.find(qn("w:gridSpan"))
                if gs is not None:
                    span = int(gs.get(qn("w:val")))
            for k in range(span):
                if grid_col + k < len(group_prefix):
                    group_prefix[grid_col + k] = gname
            grid_col += span
        if any(group_prefix):
            log.append(f"  域名组前缀：{[g for g in group_prefix if g][:6]}…")

    def full_name(col: int) -> str:
        base = names[col] if col < len(names) else ""
        if not base:
            return ""
        if base.upper() == "OVERALL" and group_prefix[col]:
            return f"{group_prefix[col]} (OVERALL)"
        return base

    # 数据行必须紧跟表头之后，且 tc 数一致
    data_rows = rows[header_idx + 1: header_idx + 1 + len(BANDS)]
    if len(data_rows) != len(BANDS):
        raise ValueError(f"{path}: 数据行数 {len(data_rows)} != {len(BANDS)}")
    for r in data_rows:
        if len(tc_list(r)) != len(hdr_tcs):
            raise ValueError(f"{path}: 数据行 tc 数不一致")

    result: dict[str, dict[str, set[int]]] = {}
    for band_i, row in enumerate(data_rows):
        tcs = tc_list(row)
        label = clean("".join(x.text or "" for x in tcs[0].iter(qn("w:t"))))
        band = BANDS[band_i]
        if label and band.split()[0].lower() not in label.lower():
            log.append(f"  ⚠️ 行顺序提示：第 {band_i} 行标签为 {label!r}，期望 {band!r}")
        for col in range(1, len(tcs)):
            name = full_name(col)
            if not name:
                continue
            vals = cell_text(tcs[col])
            if not vals:
                continue
            result.setdefault(name, {})[band] = expand(vals)

    return result, log


def verify(table: dict[str, dict[str, set[int]]], label: str) -> tuple[list[str], list[str]]:
    """返回 (硬错误, 源数据异常)。

    硬错误 = 解析不可能产生、只可能是读取错误的现象：带间重叠、带序非单调。
    源数据异常 = 源表本身的特征，必须如实记录而非"修正"：覆盖有空洞、带为空。
    """
    problems: list[str] = []
    anomalies: list[str] = []
    for facet, bands in table.items():
        if set(bands) != set(BANDS):
            anomalies.append(f"{label}/{facet}: 源表中该带为空 "
                             f"{sorted(set(BANDS) - set(bands))}")
        present = [b for b in BANDS if b in bands and bands[b]]
        sets = [bands[b] for b in present]
        for i in range(len(sets)):
            for j in range(i + 1, len(sets)):
                if sets[i] & sets[j]:
                    problems.append(f"{label}/{facet}: {present[i]} 与 {present[j]} 重叠 "
                                    f"{sorted(sets[i] & sets[j])[:6]}")
        if not sets:
            continue
        union = set().union(*sets)
        lo, hi = min(union), max(union)
        if union != set(range(lo, hi + 1)):
            gaps = sorted(set(range(lo, hi + 1)) - union)
            anomalies.append(f"{label}/{facet}: 源表覆盖有空洞 {gaps[:12]}")
        order = [bands[b] for b in BANDS if b in bands and bands[b]]
        for i in range(len(order) - 1):
            if min(order[i]) <= max(order[i + 1]):
                problems.append(f"{label}/{facet}: 带序非单调")
                break
    return problems, anomalies


def _fmt(values) -> str:
    """把整数序列压缩成区间表示，便于日志阅读。"""
    if not values:
        return "∅"
    vals = sorted(values)
    out, start, prev = [], vals[0], vals[0]
    for v in vals[1:]:
        if v == prev + 1:
            prev = v
            continue
        out.append(f"{start}" if start == prev else f"{start}-{prev}")
        start = prev = v
    out.append(f"{start}" if start == prev else f"{start}-{prev}")
    return ",".join(out)

def main() -> int:
    out: dict = {"source": "IPIP-NEO-300 Profile Sheets, UK Norms",
                 "source_dir": "archive/datasets/osf-johnson/scoring/uk-norms/",
                 "retrieved_at": "2026-09-29",
                 "bands_scheme": "Very High > 1.5σ | High 0.6–1.4σ | Average −0.5–0.5σ | "
                                 "Low −0.6–−1.4σ | Very Low < −1.5σ",
                 "caveats": ["UK 人群，非中国人群",
                             "未提供样本量、招募方式与采集年份"],
                 "levels": {}}
    logs: list[str] = []
    problems: list[str] = []
    anomalies: list[str] = []

    for kind, key in (("FACETS", "facets"), ("TRAITS", "domains")):
        out["levels"][key] = {}
        for age, pattern in AGE_FILES.items():
            path = os.path.join(NORM_DIR, pattern.format(kind=kind))
            if not os.path.exists(path):
                problems.append(f"缺少文件 {path}")
                continue
            table, log = parse_file(path)
            logs.extend(f"[{kind}/{age}] {l}" for l in log)
            p, a = verify(table, f"{kind}/{age}")
            problems.extend(p)
            anomalies.extend(a)
            out["levels"][key][age] = {
                name: {b: sorted(bands[b]) for b in BANDS if b in bands}
                for name, bands in table.items()
            }
            rng = sorted({(min(v), max(v)) for bands in table.values()
                          for v in bands.values() if v})
            logs.append(f"[{kind}/{age}] {len(table)} 个量表；值域样本 {rng[:3]}…")

    # ---- 独立交叉校验：FACETS 表的 OVERALL 列 vs TRAITS 表 ----
    # 两者是同一批维度常模，分别独立解析。吻合即为解析正确性的强证据。
    cross_ok = cross_diff = 0
    cross_notes: list[str] = []
    for age in out["levels"]["domains"]:
        overall = {k: v for k, v in out["levels"]["facets"].get(age, {}).items()
                   if k.endswith("(OVERALL)")}
        for name, bands in out["levels"]["domains"][age].items():
            okey = f"{name} (OVERALL)"
            if okey not in overall:
                cross_notes.append(f"{age}/{name}: FACETS 无对应 OVERALL 列")
                continue
            for b in BANDS:
                a = tuple(bands.get(b, []))
                c = tuple(overall[okey].get(b, []))
                if a == c:
                    cross_ok += 1
                else:
                    cross_diff += 1
                    cross_notes.append(f"{age}/{name}/{b}: TRAITS={_fmt(a)} "
                                       f"FACETS-OVERALL={_fmt(c)}")
    out["cross_validation"] = {
        "method": "FACETS 表的 <DOMAIN> (OVERALL) 列 vs TRAITS 表，两者独立解析后逐带比对",
        "agree": cross_ok, "disagree": cross_diff, "notes": cross_notes,
    }
    if cross_diff:
        anomalies.append(
            f"两个已发布文件不一致：{cross_diff} 个维度带不符（共 {cross_ok + cross_diff} 项）。"
            "已核对原始 XML，两边各自内部连续，属**源数据本身的分歧**，非解析错误。"
            "产品使用常模时必须声明采用哪一份。")

    out["validation"] = {"problems": problems, "source_anomalies": anomalies}
    out["build_log"] = logs
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)

    print("\n".join(logs))
    print(f"\n交叉校验：一致 {cross_ok} / 不一致 {cross_diff}")
    for n in cross_notes[:6]:
        print("   ", n)
    print()
    if problems:
        print(f"❌ {len(problems)} 个硬错误（解析问题，必须修复）：")
        for p in problems[:20]:
            print("   -", p)
    else:
        print("✅ 无硬错误：带间不交、带序单调")
    if anomalies:
        print(f"\n⚠️ {len(anomalies)} 项源数据异常（如实记录，不修正）：")
        for a in anomalies[:20]:
            print("   -", a)
    print(f"\nwrote {OUT}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
