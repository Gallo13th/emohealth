#!/usr/bin/env python3
"""知乎内容片段收割器：用多条检索式把**同一篇内容的不同片段**捞出来拼合。

为什么要单独一个脚本
====================
知乎开放平台**不给全文**：
  · `question_answers` 的 `Summary` 约 215 字；
  · `zhihu_search` 的 `ContentText` 是短摘要；
  · `global_search` 的 `ContentText` 明显更长（文档示例里文章摘要达数百字）。
但**同一篇内容**在**不同检索词**下会返回**不同的命中片段**——所以「换词重搜」
是唯一可行的取文路径。手工换几十个词不可复现，故脚本化。

三条容易被忽略的边界（本脚本据此设计）：
  1. 鉴权除 `Authorization` 外**必须**带 `X-Request-Timestamp`（秒级 Unix），否则一律 403。
  2. `user_contents` / `user_content_detail` 的基址是 `/api/v1/user/`，
     `quota` 是 `/api/v1/quota` —— 都**不是** `/api/v1/content/`（通用调用器只覆盖后者）。
  3. `user_content_detail` 只在**内容是调用方本人创作**时返回全文 `Body`；
     作者不是本人时**不返回正文**（且不泄露归属）。对别人的文章无解，但值得一试。

用法
====
  set ZHIHU_KEY=<secret>
  python tools/survey/harvest_zhihu_content.py probe
  python tools/survey/harvest_zhihu_content.py search [额外关键词 ...]
  python tools/survey/harvest_zhihu_content.py digest [ContentID ...]

产物：`.zhihu_harvest.json`（**临时件**，不计入交付；结论写进 research/*.md 后应删除）。
密钥只从环境变量读，不落盘。
"""

from __future__ import annotations

import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

KEY = os.environ.get("ZHIHU_KEY", "")
STORE = ".zhihu_harvest.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0"

# 端点 → 基址（注意三处不同基址）
ENDPOINTS = {
    "zhihu_search": "https://developer.zhihu.com/api/v1/content/zhihu_search",
    "global_search": "https://developer.zhihu.com/api/v1/content/global_search",
    "question_answers": "https://developer.zhihu.com/api/v1/content/question_answers",
    "question_recommendations":
        "https://developer.zhihu.com/api/v1/content/question_recommendations",
    "hot_list": "https://developer.zhihu.com/api/v1/content/hot_list",
    "user_contents": "https://developer.zhihu.com/api/v1/user/contents",
    "user_content_detail": "https://developer.zhihu.com/api/v1/user/content_detail",
    "quota": "https://developer.zhihu.com/api/v1/quota",
}

# 目标内容（Lead 已定位）
TARGET_ANSWER_TOKEN = "1933829036003530674"
TARGET_ANSWER_URL = "https://www.zhihu.com/question/518751517/answer/1933829036003530674"
TARGET_ARTICLE_URL = "https://zhuanlan.zhihu.com/p/2032556162973970712"

# 检索式：从已拿到的片段里挖出来的词 + 量表名 + 文献名 + 方法词
QUERIES = [
    # —— 标题与主题 ——
    "关于如何进行最深度全面且专业的人格自测",
    "最深度全面且专业的人格自测",
    "如何进行最深度全面且专业的人格自测",
    "最深度 全面 专业 人格自测",
    "人格自测 教程 心理测量学",
    "心理测量学 自我人格测量 AI",
    # —— 已知片段里的原词 ——
    "联合交叉分析",
    "本方法的重中之重",
    "联合分析 人格测试",
    "PID-5 原始分数 百分比",
    "PID-5 原始分数 不代表 百分比",
    "MMPI-2 Pd 反社会",
    "MMPI-2 Pd 中文翻译 反社会",
    "ADHD 快感缺失 开放性",
    "大五 240 原版 300",
    "大五 240题 300题",
    "大五、PID-5 和 MMPI",
    # —— 量表名 ——
    "ipip-neo 300题 大五",
    "IPIP-NEO-300",
    "IPIP Neo 300",
    "MMPI-2 明尼苏达多项人格",
    "MMPI-2 临床量表 效度量表",
    "MMPI-2 RF",
    "MMPI-3",
    "PID-5 人格障碍",
    "PID-5 facet 25",
    "PID-5-BF",
    "DSM-5-TR 人格障碍 维度",
    "DSM-5 人格问卷 中文版 张道龙",
    "张道龙 DSM-5",
    "SCID-5 结构访谈",
    "SCID-5-PD",
    "CAT-PD",
    "NEO-PI-R",
    "NEO-PI-3",
    "HEXACO",
    "16PF",
    "TCI 气质性格",
    "Zuckerman 替代五因素",
    "PAI 人格评估问卷",
    "MCMI",
    "大五人格 30个面向 facet",
    "IPIP-NEO-120 中文",
    # —— 方法与判读 ——
    "人格测验 常模 百分位 T分",
    "临床量表 剖面图 解读",
    "效度量表 L F K",
    "人格障碍 维度模型 AMPD",
    "人格测评 联合分析 交叉",
    "多量表 交叉验证 人格",
    "人格测试 信度 效度 自我测评",
    # —— 文献线索 ——
    "Krueger PID-5 2012",
    "Zimmermann PID-5 常模",
    "Johnson 2005 IPIP 效度",
    "Widiger 人格障碍 五因素",
    "Hopwood 人格 测评",
]

# 第二轮：全部从第一轮已取到的片段里挖出来——「已取到的句子」是找下一段的最好线索
QUERIES += [
    "三联人格测量", "利用心理测量学信效度最高的三联人格测量", "傻瓜教程 人格自测",
    "霍格伍兹网络", "赛博牛马 计算 百分位", "鞭打它 截图",
    "4-6-8 编码 暴力攻击性", "超75分 严重暴力攻击性",
    "131项 VRIN TRT2", "VRIN 到 TRT2",
    "PID-5-SF Percentile Rankings and Thresholds for Clinically Relevant Scores",
    "A Review of the Clinical Utility and Psychometric Properties of the Personality "
    "Inventory for DSM-5",
    "64页的文献 PID-5", "精神病态偏离 39项", "交叉映射脑图", "PIPI-NEO",
    "20万人常模 大五", "MMPI-2 Assessing Personality and Psychopathology",
    "John R. Graham MMPI", "Psychological Testing 心理测量学 700页",
    "PDQ-4 人格障碍 筛查", "SCL-90 负性情绪", "韦克斯勒成人智力量表 WAIS",
    "韩国 常模 人格障碍 边缘型", "被动攻击人格障碍 行为障碍", "张道龙 结构访谈",
    "IPIP-NEO 300 测试网站", "PID-5 测试 网站 220", "MMPI-2 github 中文开源 计分",
    "注意力涣散 常模 0.86", "2.97 out of 2.97",
    "人群中的百分比位置 精确到小数点后四位", "深度研究 检索50个以上学术网站",
    "Gemini pro 2.5 GPT o3 心理量表", "MMPI-2 附加量表 PTSD PK PS",
    "K校正 中国常模 装好", "中国常模 极端值扣分 65分", "开放性 99分 神经质 74",
    "宜人性 低 尖锐 刻薄", "大五 30个子项目 常模", "MMPI 一代 白人常模 800人",
    "杰弗里达莫 Pd 110分 6个标准差", "MMPI-2 展示上限 90-95分 十万分之三",
    "O Reg 人格 自测", "人格自测 大五 PID-5 MMPI 联合",
]

# 第三轮：补文章尾部与网页/文献线索
QUERIES += [
    "我节选一部分吧", "ADHD-注意力涣散-快感缺失-童年高强度刺激-极高开放性",
    "rick和阿纳金", "找国内写MMPI2 PID5等文献的作者付费测试", "我的宜人性为0",
    "高功能bpd 偏执 远离亲密关系", "成因配合MMPI的高低分",
    "这套方案能挖出来非常多潜在的东西", "所以这个思路只很简单分析了",
    "我看到什么mbti比大五精度高", "MBTI不被学界接受的四个问题",
    "问题四 无伤大雅的描述", "最后一个问题",
    "ipip.ori.org 大五 300题", "PID-5 测试网站 免费 220题",
    "MMPI-2 中文开源 github 计分键", "常模和计算方式的图片", "下面俩图 常模",
    "那个网站也会整理在后面", "T、F的形式 答题结果",
    "三联人格测量 网站 推荐", "人格自测 网站 顺序 IPIP PID MMPI",
    "黑暗三联征 量表", "MMPI-2 中国常模 65分 前6.68%",
]



def call(endpoint: str, params: dict | None = None, *, retries: int = 2) -> dict:
    """调一个端点，返回解析后的 JSON。失败抛 RuntimeError。"""
    if not KEY:
        raise RuntimeError("缺环境变量 ZHIHU_KEY")
    url = ENDPOINTS[endpoint]
    if params:
        url += "?" + urllib.parse.urlencode(params, encoding="utf-8")
    last = ""
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {KEY}",
            "X-Request-Timestamp": str(int(time.time())),   # ⚠️ 缺这条一律 403
            "Content-Type": "application/json",
            "User-Agent": UA,
        })
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:200]
            last = f"HTTP {e.code}: {body}"
            if e.code in (429, 500, 502, 503) and attempt < retries:
                time.sleep(2 * (attempt + 1))
                continue
            break
        except Exception as exc:                              # noqa: BLE001
            last = str(exc)
            if attempt < retries:
                time.sleep(1)
                continue
    raise RuntimeError(f"{endpoint} 调用失败：{last}")


def norm(text: str) -> str:
    """片段规范化：去掉高亮标签与多余空白，便于判重。"""
    t = re.sub(r"</?em>", "", text or "")
    t = t.replace("\u200b", "").replace("\xa0", " ")
    return re.sub(r"\s+", " ", t).strip()


def load() -> dict:
    if os.path.exists(STORE):
        return json.load(io.open(STORE, encoding="utf-8"))
    return {"probe": {}, "items": {}, "snippets": [], "queries": {}}


def save(d: dict) -> None:
    io.open(STORE, "w", encoding="utf-8").write(
        json.dumps(d, ensure_ascii=False, indent=1))


def record_items(store: dict, items: list[dict], query: str, channel: str) -> int:
    """把一批搜索结果并入 store（按 ContentID 归并内容，按规范化文本去重片段）。"""
    new = 0
    for it in items or []:
        cid = str(it.get("ContentID") or it.get("ContentToken") or "")
        if not cid:
            continue
        ent = store["items"].setdefault(cid, {
            "ContentID": cid,
            "Title": it.get("Title") or "",
            "Url": it.get("Url") or "",
            "ContentType": it.get("ContentType") or "",
            "AuthorName": it.get("AuthorName") or "",
            "VoteUpCount": it.get("VoteUpCount"),
            "CommentCount": it.get("CommentCount"),
            "EditTime": it.get("EditTime"),
            "snippets": [],
        })
        # 用较完整的元数据补空字段
        for f in ("Title", "Url", "ContentType", "AuthorName",
                  "VoteUpCount", "CommentCount", "EditTime"):
            if not ent.get(f) and it.get(f) not in (None, ""):
                ent[f] = it[f]
        sn = norm(it.get("ContentText") or "")
        if sn:
            seen = {s["text"] for s in ent["snippets"]}
            if sn not in seen:
                ent["snippets"].append({"text": sn, "query": query,
                                        "channel": channel})
                new += 1
    store["queries"].setdefault(query, {"channels": []})
    if channel not in store["queries"][query]["channels"]:
        store["queries"][query]["channels"].append(channel)
    return new


def cmd_probe() -> int:
    store = load()
    print("=" * 68)
    try:
        q = call("quota")
        store["probe"]["quota"] = q
        for row in (q.get("Data") or []):
            print(f"  {row.get('APIID'):18} {row.get('APIName'):8} "
                  f"{row.get('TotalUsed')}/{row.get('TotalQuota')} 用，"
                  f"余 {row.get('RemainingQuota')}")
    except RuntimeError as exc:
        print("  quota 失败：", exc)

    print("\n--- 本人创作列表（判断调用方是否就是作者）---")
    try:
        r = call("user_contents", {"ContentType": "all", "Limit": 50})
        items = ((r.get("Data") or {}).get("Items")) or []
        store["probe"]["own_contents"] = r
        print(f"  Code={r.get('Code')} 本人内容 {len(items)} 条")
        for it in items[:50]:
            print(f"    [{it.get('ContentType')}] {str(it.get('Title'))[:60]} "
                  f"{it.get('Url')}")
    except RuntimeError as exc:
        print("  user_contents 失败：", exc)

    print("\n--- 目标链接是否属本人创作（是则能拿全文 Body）---")
    for label, url in (("answer", TARGET_ANSWER_URL), ("article", TARGET_ARTICLE_URL)):
        try:
            r = call("user_content_detail", {"ContentUrl": url})
            store["probe"]["detail_" + label] = r
            body = (r.get("Data") or {}).get("Body") or ""
            print(f"  {label}: Code={r.get('Code')} Message={r.get('Message')} "
                  f"Body={len(body)} 字")
            if body:
                io.open(f".zhihu_fulltext_{label}.txt", "w", encoding="utf-8").write(body)
                print(f"    ★ 已存 .zhihu_fulltext_{label}.txt")
        except RuntimeError as exc:
            print(f"  {label} 失败：{exc}")
    save(store)
    return 0


def cmd_search(extra: list[str]) -> int:
    store = load()
    queries = list(QUERIES)
    for a in extra:
        if a.startswith("@"):
            # 从文件读追加检索式（一行一条），避免在 shell 里传中文参数被转码
            with io.open(a[1:], encoding="utf-8") as fh:
                queries += [ln.strip() for ln in fh if ln.strip()
                            and not ln.strip().startswith("#")]
        else:
            queries.append(a)
    total_new = 0
    for i, q in enumerate(queries, 1):
        for channel, params in (
            ("zhihu_search", {"Query": q, "Count": 10}),
            ("global_search", {"Query": q, "Count": 20}),
        ):
            try:
                r = call(channel, params)
            except RuntimeError as exc:
                print(f"[{i}/{len(queries)}] {channel} 《{q}》 失败：{exc}")
                continue
            items = ((r.get("Data") or {}).get("Items")) or []
            n = record_items(store, items, q, channel)
            total_new += n
            if n:
                print(f"[{i}/{len(queries)}] {channel:14} 《{q}》 "
                      f"命中 {len(items)} 条，新增片段 {n}")
        if i % 10 == 0:
            save(store)
    save(store)
    print(f"\n新增片段合计 {total_new}；内容条目 {len(store['items'])}")
    return 0


def cmd_digest(ids: list[str]) -> int:
    store = load()
    print(f"内容条目 {len(store['items'])} 条")
    rows = sorted(store["items"].values(),
                  key=lambda e: -(e.get("VoteUpCount") or 0))
    print("\n--- 命中条目（按赞同排序，前 40）---")
    for e in rows[:40]:
        print(f"  {str(e['ContentID']):22} 赞{e.get('VoteUpCount')} "
              f"片{len(e['snippets'])} {str(e['ContentType']):8} "
              f"{str(e['Title'])[:52]}")
    for cid in ids:
        e = store["items"].get(str(cid))
        if not e:
            print(f"\n### {cid} 不在库里")
            continue
        print(f"\n{'=' * 68}\n### {e['Title']}\n{e['Url']}\n"
              f"作者={e['AuthorName']} 赞={e.get('VoteUpCount')} 片段={len(e['snippets'])}")
        for s in e["snippets"]:
            print(f"\n  〔{s['channel']} / {s['query']}〕\n  {s['text']}")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    cmd = sys.argv[1]
    if cmd == "probe":
        return cmd_probe()
    if cmd == "search":
        return cmd_search(sys.argv[2:])
    if cmd == "digest":
        return cmd_digest(sys.argv[2:])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
