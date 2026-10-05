#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""前端层打包器：把 ``data/**`` 的 JSON 包成前端可加载的 ``ui/**`` 脚本。

为什么需要它
============
``ui/index.html`` 是**纯静态、可 ``file://`` 打开**的页面，数据包只能靠
``<script src>`` 注入，而 ``fetch('x.json')`` 在 ``file://`` 下会被同源策略拒绝。
所以每个数据包都必须是一段会自己挂到 ``window`` 上的 JS：

    window.EMOHEALTH_XXX = {…};

历史上这段包装是**数据层的 build 脚本自己写的**（``build_tier_ui_data``、
``build_unlock_network``、``build_adaptive_data``、``build_catalog``、
``build_tree_layouts``），于是数据层直接产出 ``ui/*.js``——那是跨层依赖：
改界面数据格式要动数据层脚本，数据层产物又散落在前端目录里。

现在把这一步单独抽出来放在**前端层**（``tools/ui/``）：

    数据层：archive/ → data/**.json        （不碰 ui/）
    前端层：data/**.json → ui/**.js          ← 就是本脚本

用法
====
    python tools/ui/pack_ui_data.py                 # 全部打包
    python tools/ui/pack_ui_data.py --only tier     # 只打一个包
    python tools/ui/pack_ui_data.py --check         # 只比对，不写文件（退出码 1 = 有差异）
    python tools/ui/pack_ui_data.py --list          # 列出作业表

设计
====
* **声明式作业表**（``JOBS``）：新增一个包 = 加一条记录，**不写新的打包代码**。
  单文件作业给 ``src``/``dst``/``var``；目录作业给 ``src_dir``/``dst_dir``/
  ``var_from``/``var_prefix``，逐个 json 变成同名 ``.js``。
* **通用包装**：读 json → ``window.<VAR> = <紧凑 JSON>;``。包装格式就这一种，
  没有针对某个包的解析分支。
* **紧凑重排**：用 ``json.dumps(..., ensure_ascii=False, separators=(",", ":"))``
  重新序列化，而不是原样搬运文件文本。这一条是必需的——``data/instruments/catalog.json``
  是 ``indent=1`` 的**人读**格式，而 ``ui/catalog.js`` 要的是紧凑单行。
  对本来就是紧凑格式的源文件（``tier-prefix`` 等），重排结果与源文件**逐字节相同**。
* **二进制 + LF 写出**：文本模式在 Windows 上会把 ``\\n`` 翻译成 ``\\r\\n``，
  于是同一份数据在不同机器上产出不同字节。这里统一按二进制写、行尾只用 LF。
* **注释头**：``ui/catalog.js`` 与 ``ui/tree-layouts/*.js`` 保留「自动生成」注释头
  （架构守卫的生成产物豁免要求有这个标记）。头里的生成者写**本脚本**，
  不写已经不再生成它的数据层脚本。
* ``ui/tree-layouts/index.json`` 是清单（``build_ui_instruments.py`` 直接 ``json.load``
  它），不是 JS，按原字节复制过去。
* **作业 → 输入显式化**（``inputs``）：新鲜度守卫
  ``tools/check/check_pack_freshness.py`` 要**逐 job** 比「最新输入 mtime」与
  「最旧产物 mtime」。写了 ``inputs`` 的作业以它为准，没写的按 ``src`` /
  ``src_dir/*.json`` 推（见 ``job_input_patterns``）。**引擎组装类作业必须显式写**：
  ``inference`` 的 payload 由 ``engine/inference.py`` 现场算，除 ``data/inference/*.json``
  外还读 ``data/instruments/**``、``data/item-norms*.json``、``data/norms/pid-5.json``，
  不写出来守卫就会漏判。

契约位置
========
本脚本属**前端层**：只读 ``data/**``，只写 ``ui/**``，不碰 ``archive/``（C1）。
数据层不再需要写 ``ui/``（C3 的「写入 ui/」计数因此归零）。
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root, force_utf8_io  # noqa: E402

ROOT = find_root()


#: 打包作业表。单文件作业：src/dst/var；目录作业：src_dir/dst_dir/var_from/var_prefix。
JOBS: tuple[dict, ...] = (
    {
        "name": "tier",
        "src": "data/tier-prefix.json",
        "dst": "ui/tier-data.js",
        "var": "EMOHEALTH_TIER",
        "inputs": ("data/tier-prefix.json",),
    },
    {
        "name": "unlock",
        "src": "data/unlock-network.json",
        "dst": "ui/unlock-data.js",
        "var": "EMOHEALTH_UNLOCK",
        "inputs": ("data/unlock-network.json",),
    },
    {
        "name": "adaptive",
        "src": "data/adaptive-network.json",
        "dst": "ui/adaptive-data.js",
        "var": "EMOHEALTH_ADAPT",
        "inputs": ("data/adaptive-network.json",),
    },
    {
        "name": "catalog",
        "src": "data/instruments/catalog.json",
        "dst": "ui/catalog.js",
        "var": "EMOHEALTH_CATALOG",
        "inputs": ("data/instruments/catalog.json",),
        "header": "多量表目录（由 tools/ui/pack_ui_data.py 从 "
                  "data/instruments/catalog.json 打包，勿手改）\n"
                  "   只有元信息：题项在各 data/instruments/<code>.json 里，按需加载。",
    },
    {
        "name": "tree-layouts",
        "src_dir": "data/tree-layouts",
        "dst_dir": "ui/tree-layouts",
        "inputs": ("data/tree-layouts/*.json",),
        # 变量名取自布局自己的 meta.instrument（`EMOHEALTH_TREE_<CODE>`），
        # 与界面按需注入的约定一致；文件名用 instrument 的小写形式。
        "var_from": ("meta", "instrument"),
        "var_prefix": "EMOHEALTH_TREE_",
        # ⚠️ 必须是赋值语句，不能是裸 JSON：界面用 <script> 注入，
        #    裸 JSON 会被当语句解析并抛 "Unexpected token ':'"。
        "header": "{instrument} 天赋树布局｜由 tools/ui/pack_ui_data.py 生成，勿手改",
        # 清单不是 JS，原样复制（内容是 {"threshold","count","note","scales"}）
        "copy": ("index.json",),
    },
    # ⚠️ 第 6 个作业 `inference` 曾在「只留最小 UI」那一轮被删除（task-10）。
    #    现在按用户要求（答题界面要展示「各指标预测 + 置信度」）**加回来**。
    {
        # 题面五字段（原文 / 中译 / 情景展示 scenario_zh / 选项情景说明 / 作答注记）→ 按需加载。
        # 数据由 tools/build/build_item_structured.py 产出（606 题，五字段齐全率 100%，
        # 守卫 tools/check/check_item_structured.py）。
        "name": "items-structured",
        "src_dir": "data/items-structured",
        "dst_dir": "ui/items-structured",
        "inputs": ("data/items-structured/*.json",),
        "var_from": ("instrument",),
        "var_prefix": "EMOHEALTH_STRUCT_",
        "header": "{instrument} 题面结构化五字段（原文 / 中译 / 情景展示 scenario_zh / "
                  "选项情景说明 / 作答注记）｜由 tools/ui/pack_ui_data.py 生成，勿手改",
        "manifest": ("ui/items-structured.js", "EMOHEALTH_STRUCTMAP", "items-structured/"),
        "manifest_header": ("题面结构化清单（code → ui/items-structured/<code>.js）"
                            "｜由 tools/ui/pack_ui_data.py 生成，勿手改"),
        # index.json 是给校验器看的总表，不是某一套量表的字段包
        "copy": ("index.json",),
    },
    {
        # 推断参数：**由 engine/inference.py 的 `params_for_js()` 生成**，
        # 不是简单把 `data/inference/*.json` 重排一遍。原因：
        # `ui/lib/inference.js` 需要 `ids` / `item_mean` / `item_sd` / `dim_items` /
        # `dim_agg` / `key_of_item` / `response_min·max` 等参数，其中题级均值与 SD
        # 由 engine 侧解析（IPIP-NEO 取 data/item-norms.json；PID-5 由 facet T 分表
        # 反推）。照抄 data/inference/*.json 会让 JS 侧**缺参数**；在 UI 里再写一遍
        # 组装逻辑就是「两套实现漂移」——本项目明确禁止（见
        # tools/check/test_inference_pyjs_consistency.py 的说明）。
        # 数值全部来自 data/inference/*.json（pairB64 / item_dim_corr / dim_ceiling /
        # dim_ceiling_cross / ceiling_ratio / ceiling_ratio_cross），engine 只做组装。
        # ⚠️ 因此本作业**需要 numpy**（engine/inference.py 的依赖）。缺依赖时**明确报错**，
        #    不会静默留下旧产物。
        "name": "inference",
        "src_dir": "data/inference",
        "dst_dir": "ui/inference",
        # ⚠️ 显式输入：payload 由 engine/inference.py 现场组装，它除了
        #    `data/inference/<code>.json` 还读 `data/instruments/**`（按 instrument 字段找量表包）、
        #    `data/item-norms*.json` / `data/norms/pid-5.json`（题级 mean·SD），
        #    以及 engine 侧代码本身。漏一个，新鲜度守卫就会漏判。
        "inputs": ("data/inference/*.json", "data/instruments/*.json",
                   "data/item-norms.json", "data/item-norms-*.json",
                   "data/norms/pid-5.json", "engine/inference.py",
                   "engine/instrument_schema.py", "engine/scoring.py"),
        "var_from": ("instrument",),
        "var_prefix": "EMOHEALTH_INFER_",
        "header": ("{instrument} 题级推断参数（ids/题→维度相关/题级 mean·SD/"
                   "上限·比例/pairB64）｜由 tools/ui/pack_ui_data.py 调 "
                   "engine/inference.py 生成，勿手改"),
        "manifest": ("ui/inference.js", "EMOHEALTH_INFERMAP", "inference/"),
        "manifest_header": ("推断参数清单（code → ui/inference/<code>.js）"
                            "｜由 tools/ui/pack_ui_data.py 生成，勿手改"),
        "engine_payload": True,
    },
)


def engine_payload(code: str) -> dict:
    """用 `engine/inference.py` 组装某量表的 JS 参数包（与 Python 侧**同一份**）。

    ⚠️ 需要 numpy。缺依赖时抛 RuntimeError 并说明——**不要**退回「只搬 JSON」，
    那样 JS 侧会缺 `item_mean`/`item_sd`/`dim_items` 等参数。
    """
    sys.path.insert(0, ROOT)
    try:
        from engine.inference import load as load_model  # noqa: PLC0415
    except Exception as exc:                              # noqa: BLE001
        raise RuntimeError(
            "inference 作业需要 engine/inference.py（依赖 numpy），"
            f"当前解释器导入失败：{type(exc).__name__}: {exc}"
            "——请用带 numpy 的解释器跑本脚本") from exc
    m = load_model(code)
    inf = load_json(m.inference_json)
    return {
        "instrument": code,
        # 与 engine/inference.py --dump-params 的输出同形：{params, pairB64}
        "params": m.params_for_js(),
        "pairB64": inf["pairB64"],
        # 出处与口径（界面上「为什么能给这个数」要能查到）
        "item_dim_corr_kind": inf.get("item_dim_corr_kind"),
        "ceiling_note": inf.get("ceiling_note", ""),
        "ceiling_cross_note": inf.get("ceiling_cross_note", ""),
        "min_own_removed": inf.get("min_own_removed", ""),
        "level": inf.get("level"),
        "n_respondents": inf.get("n_respondents"),
        "quality": inf.get("quality", {}),
    }


def compact(obj, sort_keys: bool = False) -> str:
    """紧凑序列化：与历史 build 脚本的 ``separators=(',", ':' )`` 口径一致。

    ``sort_keys`` 用于**引擎生成**的作业：`engine/inference.py` 的
    `_resolve_item_stats` 用 `ids = {…}`（集合）建题级均值/SD 字典，集合迭代序
    受 Python 字符串哈希随机化影响 → 同一份数据两次产出**字节不同**（大小相同）。
    排序键即可消除，保证 `--check` 逐字节一致。
    """
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"),
                      sort_keys=sort_keys)


def ident(code: str) -> str:
    """把量表 code 变成合法的 JS 标识符片段（与 build_ui_instruments.py 同规则）。"""
    return re.sub(r"[^A-Za-z0-9]", "_", code).upper()


def render(header: str | None, var: str, obj, sort_keys: bool = False) -> str:
    """通用包装：可选注释头 + ``window.<var> = <紧凑 JSON>;``。"""
    out = f"/* {header} */\n" if header else ""
    return out + f"window.{var} = {compact(obj, sort_keys=sort_keys)};\n"


def load_json(path: str):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def job_files(job: dict) -> list[tuple[str, str, str]]:
    """展开一个作业 → [(源相对路径, 目标相对路径, 要写出的文本)]。"""
    if "src" in job:
        obj = load_json(os.path.join(ROOT, *job["src"].split("/")))
        return [(job["src"], job["dst"],
                 render(job.get("header"), job["var"], obj))]

    src_dir = os.path.join(ROOT, *job["src_dir"].split("/"))
    if not os.path.isdir(src_dir):
        raise FileNotFoundError(f"{job['src_dir']}/ 不存在（先跑数据层脚本产出它）")
    copies = set(job.get("copy", ()))
    out: list[tuple[str, str, str]] = []
    manifest: dict[str, str] = {}
    for fn in sorted(os.listdir(src_dir)):
        if not fn.endswith(".json") or fn in copies:
            continue
        obj = load_json(os.path.join(src_dir, fn))
        code = obj
        for key in job["var_from"]:
            code = code[key]
        payload = engine_payload(code) if job.get("engine_payload") else obj
        header = job["header"].format(instrument=code) if job.get("header") else None
        rel_js = f"{fn[:-len('.json')]}.js"
        out.append((f"{job['src_dir']}/{fn}",
                    f"{job['dst_dir']}/{rel_js}",
                    render(header, job["var_prefix"] + ident(code), payload,
                           sort_keys=bool(job.get("engine_payload")))))
        manifest[code] = (job["manifest"][2] + rel_js) if job.get("manifest") else rel_js
    if job.get("manifest"):
        dst_rel, var, _prefix = job["manifest"]
        # 键排序：同一份数据每次产出同样的字节（--check 要求逐字节一致）
        out.append((f"{job['src_dir']}/*.json（清单）", dst_rel,
                    render(job.get("manifest_header"), var,
                           {k: manifest[k] for k in sorted(manifest)})))
    for fn in job.get("copy", ()):
        with open(os.path.join(src_dir, fn), "rb") as fh:
            raw = fh.read()
        out.append((f"{job['src_dir']}/{fn}", f"{job['dst_dir']}/{fn}",
                    raw.decode("utf-8")))
    return out


# ------------------------------------------------- 作业 → 输入/产物（路径级，不读内容）
#
# 供 tools/check/check_pack_freshness.py 用：它要**逐 job** 比
# 「最新输入 mtime」与「最旧产物 mtime」，所以这里只算路径、不读文件内容、
# 也不调 engine（否则守卫会变成一次昂贵的打包）。

def job_input_patterns(job: dict) -> tuple[str, ...]:
    """该作业声明的输入（相对路径或 glob）。手工 ``inputs`` 优先。"""
    explicit = job.get("inputs")
    if explicit:
        return tuple(explicit)
    if "src" in job:
        return (job["src"],)
    return (f"{job['src_dir']}/*.json",)


def glob_rel(pattern: str) -> list[str]:
    """展开 glob 为实际存在的文件（相对路径，``/`` 分隔，按名排序）。

    公开给 ``tools/check/check_pack_freshness.py``：它要分辨「声明了但一个都没匹配到」
    （源目录缺失）与「匹配到了」两种情形。
    """
    pat = os.path.join(ROOT, *pattern.split("/"))
    return [os.path.relpath(p, ROOT).replace(os.sep, "/")
            for p in sorted(glob.glob(pat))]


def job_input_paths(job: dict) -> list[str]:
    """该作业**实际存在的输入文件**（只算路径，不读内容）。"""
    out: list[str] = []
    for pattern in job_input_patterns(job):
        out.extend(glob_rel(pattern))
    return out


def job_output_paths(job: dict) -> list[str]:
    """该作业预期的**产物文件**（只算路径，不读内容）。

    目录作业按「源目录里每个 json → 同名 .js」推产物，所以**新增了一个源文件
    却没重打包**时，会得到一个「预期存在但磁盘上没有」的产物——守卫据此报 ❌；
    再加上清单文件与 ``copy`` 目标。
    """
    if "src" in job:
        return [job["dst"]]
    src_dir = os.path.join(ROOT, *job["src_dir"].split("/"))
    copies = set(job.get("copy", ()))
    outs: list[str] = []
    if os.path.isdir(src_dir):
        for fn in sorted(os.listdir(src_dir)):
            if fn.endswith(".json") and fn not in copies:
                outs.append(f"{job['dst_dir']}/{fn[:-len('.json')]}.js")
    if job.get("manifest"):
        outs.append(job["manifest"][0])
    outs.extend(f"{job['dst_dir']}/{fn}" for fn in job.get("copy", ()))
    return outs


def write_text(rel: str, text: str) -> int:
    """二进制写、只用 LF —— 避免 Windows 文本模式把 \\n 变成 \\r\\n。"""
    dst = os.path.join(ROOT, *rel.split("/"))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    data = text.encode("utf-8")
    with open(dst, "wb") as fh:
        fh.write(data)
    return len(data)


def check_text(rel: str, text: str) -> tuple[bool, str, int]:
    dst = os.path.join(ROOT, *rel.split("/"))
    if not os.path.exists(dst):
        return False, "缺失", len(text.encode("utf-8"))
    with open(dst, "rb") as fh:
        cur = fh.read()
    want = text.encode("utf-8")
    if cur == want:
        return True, "一致", len(want)
    return False, f"不一致（磁盘 {len(cur)} B / 应为 {len(want)} B）", len(want)


def main(argv: list[str] | None = None) -> int:
    force_utf8_io()          # 入口第一件事：GBK 控制台下不许崩（见函数 docstring）
    ap = argparse.ArgumentParser(
        description="把 data/** 的 JSON 打包成 ui/** 的 window.* 赋值脚本（前端层）")
    ap.add_argument("--only", action="append", metavar="NAME",
                    help="只处理指定作业（可多次；作业名见 --list）")
    ap.add_argument("--check", action="store_true",
                    help="只比对生成结果与磁盘现状，不写文件")
    ap.add_argument("--list", action="store_true", help="列出作业表后退出")
    args = ap.parse_args(argv)

    if args.list:
        for job in JOBS:
            ins = job_input_paths(job)
            outs = job_output_paths(job)
            dst_desc = job.get("dst") or f"{job['dst_dir']}/*.js"
            if job.get("manifest"):
                dst_desc += "、" + job["manifest"][0]
            if job.get("copy"):
                dst_desc += "、" + "、".join(f"{job['dst_dir']}/{c}"
                                            for c in job["copy"])
            print(f"  {job['name']}")
            print(f"    输入 {len(ins):3} 个  ←  " + "、".join(job_input_patterns(job)))
            print(f"    产物 {len(outs):3} 个  →  {dst_desc}")
        return 0

    print(f"前端打包（项目根：{ROOT}）")
    print(f"模式：{'只比对（--check）' if args.check else '写入'}")
    print()

    bad = 0
    total = 0
    for job in JOBS:
        if args.only and job["name"] not in args.only:
            continue
        try:
            files = job_files(job)
        except FileNotFoundError as exc:
            print(f"✗ {job['name']}：{exc}")
            bad += 1
            continue
        print(f"── {job['name']}（{len(files)} 个）")
        for src_rel, dst_rel, text in files:
            total += 1
            if args.check:
                ok, note, nbytes = check_text(dst_rel, text)
                mark = "✓" if ok else "✗"
                if not ok:
                    bad += 1
                print(f"   {mark} {src_rel} → {dst_rel}：{note}")
            else:
                nbytes = write_text(dst_rel, text)
                print(f"   ✓ {src_rel} → {dst_rel}（{nbytes / 1024:.1f} KB）")
        print()

    if args.check:
        if bad:
            print(f"❌ {bad}/{total} 个文件与磁盘现状不一致。")
            return 1
        print(f"✅ {total} 个文件与磁盘现状逐字节一致。")
        return 0
    print(f"✅ 打包 {total} 个文件。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
