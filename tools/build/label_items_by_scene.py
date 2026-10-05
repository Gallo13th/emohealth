#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用硅基流动的 embedding + 小模型，为 300 道题做「生活情景」标注。

借用了 `~/Documents/social_research/zhihu_research/scripts/` 里的现成方案：
  · embedding: `BAAI/bge-large-zh-v1.5`（1024 维）
  · 小模型打标签: `Qwen/Qwen2.5-14B-Instruct`
  · 接口: https://api.siliconflow.cn/v1/{embeddings,chat/completions}

三趟流程：
  Pass 1  逐题**自由提议**情景名（不给候选清单，避免被我的预设框住）
  Pass 2  把 Pass 1 的原始标签汇总，让模型**归并成一套分类法**（允许「一般性/杂项」）
  Pass 3  按归并后的分类法**重新标注**全部 300 题

同时算 embedding 并聚类，用于与情景标签**交叉验证**：
若情景标签与语义聚类高度一致，说明情境划分捕捉到了真实的内容结构；
若不一致，则说明情景是一个独立于语义的维度（这本身也是有用的结论）。

输出：
  data/scene-labeling.json      三趟标注的完整结果
  data/item-embeddings.npy      300 × 1024
  data/scene-clusters.json      聚类与交叉验证结果
"""
from __future__ import annotations

import glob
import json
import os
import sys
import re
import time
import urllib.error
import urllib.request

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
CANON = os.path.join(ROOT, "data/ipip-neo-300.json")
OUT_LAB = os.path.join(ROOT, "data/scene-labeling.json")
OUT_EMB = os.path.join(ROOT, "data/item-embeddings.npy")
OUT_CLU = os.path.join(ROOT, "data/scene-clusters.json")

API_EMB = "https://api.siliconflow.cn/v1/embeddings"
API_CHAT = "https://api.siliconflow.cn/v1/chat/completions"
KEY = "sk-logzgepgyfvhjgnowmimulmkrlmyzosdyftfjxiwazoqihav"
EMB_MODEL = "BAAI/bge-large-zh-v1.5"
CHAT_MODEL = "Qwen/Qwen2.5-14B-Instruct"


def post(url: str, payload: dict, timeout: int = 90, tries: int = 5) -> dict:
    body = json.dumps(payload).encode("utf-8")
    for a in range(tries):
        try:
            req = urllib.request.Request(
                url, data=body,
                headers={"Authorization": f"Bearer {KEY}",
                         "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(15 + 8 * a)
                continue
            time.sleep(3 + 2 * a)
        except Exception:
            time.sleep(3 + 2 * a)
    raise RuntimeError(f"请求失败：{url}")


def chat(prompt: str, max_tokens: int = 400, temperature: float = 0.0) -> str:
    d = post(API_CHAT, {"model": CHAT_MODEL, "temperature": temperature,
                        "max_tokens": max_tokens,
                        "messages": [{"role": "user", "content": prompt}]})
    return d["choices"][0]["message"]["content"].strip()


# ───────────────────────────────────────────── Pass 1：自由提议
P1 = """下面是一句中文人格量表题面，描述某种行为或感受。

请判断：这句话描述的行为或感受，**最可能在什么日常生活情境下被观察到**？

要求：
- 用 3-10 个字概括情境，例如「和朋友聚会」「工作接到任务」「独处时」「和人起冲突」
- 如果这句话是**一般性**的、不指向特定情境（例如「喜欢音乐」「信任他人」），就输出：一般性
- 只输出情境名，不要标点、不要解释

题面："""


def pass1(items: list[dict]) -> dict[int, str]:
    out: dict[int, str] = {}
    for i, it in enumerate(items):
        try:
            s = chat(P1 + it["text_zh"], max_tokens=16)
            s = re.sub(r"[\s。，,、：:；;\"'「」]", "", s)
            out[it["administration_order"]] = s[:14] or "一般性"
        except Exception as e:
            out[it["administration_order"]] = "ERROR"
            print(f"  ⚠️ #{it['administration_order']} {e}")
        if (i + 1) % 50 == 0:
            print(f"  Pass1 {i+1}/{len(items)}", flush=True)
        time.sleep(0.15)
    return out


# ───────────────────────────────────────────── Pass 2：归并分类法
P2 = """下面是给 300 句人格量表题面自由标注的「生活情境」标签，及各自出现次数。

请你把它们**归并成一套简洁的分类法**，用于组织一份人格测评的作答流程。

规则：
- 目标 8–14 个情境（不必强求固定数量）
- 语义重合、只是措辞不同的标签必须合并（如「工作」「工作任务」「工作场合」→ 一个）
- 出现次数很少（≤2）且无法归入任何情境的，一律并入「其他情境」
- 「一般性」作为**独立的一类保留**（它不指向特定情境）
- 每个情境名 3–8 个字，用用户能一眼看懂的说法

标签清单（标签: 次数）：
{labels}

输出格式：每行一个情境，格式为
情境名 | 原始标签1,原始标签2,原始标签3
不要编号、不要解释、不要 markdown、不要多余空行。"""


def pass2(raw: dict[int, str]) -> list[dict]:
    from collections import Counter
    c = Counter(v for v in raw.values() if v and v != "ERROR")
    labels = "\n".join(f"{k}: {v}" for k, v in c.most_common())
    s = chat(P2.replace("{labels}", labels), max_tokens=3000)
    out = []
    for line in s.split("\n"):
        line = line.strip().strip("`").lstrip("-*0123456789. ").strip()
        if "|" not in line:
            continue
        name, _, tags = line.partition("|")
        name = re.sub(r"^[\"「]|[\"」]$", "", name.strip())
        if not name or name in ("情境名",):
            continue
        out.append({"情境名": name,
                    "包含的原始标签": [t.strip() for t in tags.split(",") if t.strip()]})
    if not out:
        raise RuntimeError(f"Pass2 未解析出任何情境：{s[:300]}")
    return out


# ───────────────────────────────────────────── Pass 3：按分类法重标
P3 = """下面是一句中文人格量表题面。请从给定情境中选**最贴切的一个**。

情境列表：
{tax}

规则：
- 只输出情境名本身，不要解释、不要标点
- 若这句话不指向特定情境，选「一般性」
- 若都不合适，选「其他情境」

题面："""


def pass3(items: list[dict], tax: list[str]) -> dict[int, str]:
    tax_s = "\n".join(f"- {t}" for t in tax)
    out: dict[int, str] = {}
    for i, it in enumerate(items):
        try:
            s = chat(P3.replace("{tax}", tax_s) + it["text_zh"], max_tokens=16)
            s = re.sub(r"[\s。，,、：:；;\"'「」\-]", "", s)
            # 容错：取最长的匹配项
            cand = [t for t in tax if t in s] or [t for t in tax if s in t]
            out[it["administration_order"]] = cand[0] if cand else "其他情境"
        except Exception as e:
            out[it["administration_order"]] = "ERROR"
        if (i + 1) % 50 == 0:
            print(f"  Pass3 {i+1}/{len(items)}", flush=True)
        time.sleep(0.15)
    return out


def embed(texts: list[str], batch: int = 32) -> np.ndarray:
    vecs = []
    for i in range(0, len(texts), batch):
        chunk = texts[i:i + batch]
        d = post(API_EMB, {"model": EMB_MODEL, "input": chunk})
        vecs.extend([x["embedding"] for x in d["data"]])
        print(f"  embed {min(i+batch, len(texts))}/{len(texts)}", flush=True)
        time.sleep(0.2)
    return np.array(vecs, dtype=np.float32)


def cached(path: str, fn):
    if os.path.exists(path):
        print(f"  （命中缓存 {os.path.basename(path)}）")
        return json.load(open(path, encoding="utf-8"))
    v = fn()
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(v, fh, ensure_ascii=False, indent=1)
    return v


def main() -> int:
    canon = json.load(open(CANON, encoding="utf-8"))
    # 中文题面在 content/facets/ 的档案里（规范数据集只有英文与结构）
    zh: dict[int, str] = {}
    for f in glob.glob(os.path.join(ROOT, "content/facets/*.record.json")):
        rec = json.load(open(f, encoding="utf-8"))
        for it in rec["items"]:
            zh[it["administration_order"]] = it["text_zh"]
    items = []
    for x in sorted(canon["items"], key=lambda x: x["order"]):
        o = x["order"]
        items.append({"administration_order": o, "facet": x["facet"],
                      "text_en": x["text"], "text_zh": zh.get(o, x["text"])})

    CACHE = os.path.join(ROOT, "data/_scene_cache")
    os.makedirs(CACHE, exist_ok=True)

    print("=== Pass 1：自由提议情境 ===")
    l1 = {int(k): v for k, v in cached(
        os.path.join(CACHE, "pass1.json"), lambda: pass1(items)).items()}
    from collections import Counter
    print("  原始标签数:", len(set(l1.values())))
    for k, v in Counter(l1.values()).most_common(12):
        print(f"    {k}: {v}")

    print("\n=== Pass 2：归并分类法 ===")
    tax_groups = cached(os.path.join(CACHE, "pass2.json"), lambda: pass2(l1))
    tax = []
    for g in tax_groups:
        n = g.get("情境名") or next((v for k, v in g.items() if k != "包含的原始标签"), None)
        if n:
            tax.append(n)
    print(f"  归并后 {len(tax)} 类:", "、".join(tax))

    print("\n=== Pass 3：按分类法重标 ===")
    l3 = {int(k): v for k, v in cached(
        os.path.join(CACHE, "pass3.json"), lambda: pass3(items, tax)).items()}

    print("\n=== Embedding ===")
    if os.path.exists(OUT_EMB):
        emb = np.load(OUT_EMB)
        print(f"  （命中缓存）{emb.shape}")
    else:
        emb = embed([it["text_zh"] for it in items])
        np.save(OUT_EMB, emb)
    print(f"  {emb.shape} → {os.path.relpath(OUT_EMB, ROOT)}")

    # ── 交叉验证：情景标签 vs 语义聚类
    print("\n=== 交叉验证：语义聚类 vs 情景标签 ===")
    from sklearn.cluster import KMeans
    from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
    from sklearn.preprocessing import normalize
    Xn = normalize(emb)
    best = None
    for k in range(2, 16):
        km = KMeans(n_clusters=k, n_init=10, random_state=0).fit(Xn)
        # 用轮廓系数选 k
        from sklearn.metrics import silhouette_score
        s = silhouette_score(Xn, km.labels_, sample_size=min(300, len(Xn))) if k > 1 else -1
        if best is None or s > best[1]:
            best = (k, s, km.labels_)
    k_best, sil, clu = best
    orders = [it["administration_order"] for it in items]
    scene_ids = [tax.index(l3[o]) if l3[o] in tax else -1 for o in orders]
    ari = adjusted_rand_score(scene_ids, clu)
    nmi = normalized_mutual_info_score(scene_ids, clu)
    print(f"  语义聚类最佳 k={k_best}（轮廓 {sil:.3f}）")
    print(f"  与情景标签的一致度：ARI={ari:+.3f}  NMI={nmi:.3f}")

    payload = {
        "method": "硅基流动 BAAI/bge-large-zh-v1.5 + Qwen2.5-14B-Instruct",
        "pass1_free_labels": {str(k): v for k, v in l1.items()},
        "pass2_taxonomy": tax_groups,
        "taxonomy": tax,
        "pass3_final": {str(k): v for k, v in l3.items()},
        "counts": {k: v for k, v in Counter(l3.values()).most_common()},
        "cross_validation": {
            "embedding_k": k_best, "silhouette": round(float(sil), 4),
            "ARI_vs_scene": round(float(ari), 4), "NMI_vs_scene": round(float(nmi), 4),
            "interpretation": "ARI 高 = 情景划分与语义结构一致；ARI 低 = 情景是独立于语义的维度",
        },
    }
    with open(OUT_LAB, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
    with open(OUT_CLU, "w", encoding="utf-8") as fh:
        json.dump({"k": k_best, "silhouette": float(sil),
                   "labels": {str(o): int(c) for o, c in zip(orders, clu)}},
                  fh, ensure_ascii=False, indent=1)

    print(f"\n=== 最终情景分布 ===")
    for k, v in Counter(l3.values()).most_common():
        print(f"  {k:<16} {v:>3} 题")
    print(f"\nwrote {os.path.relpath(OUT_LAB, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
