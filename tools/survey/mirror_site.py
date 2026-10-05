#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""同域站点镜像器 —— 用于离线归档公共领域量表资产。

设计目标：
  1. 只抓同一 host（避免外链爆炸）
  2. 原始字节落盘（不改写内容，保留可校验性）
  3. 每个产物写入 manifest.jsonl：url / 状态 / 类型 / 字节数 / sha256 / 落盘路径 / 抓取时间
  4. 礼貌抓取：串行 + 延迟，避免给捐赠维持的小站造成压力

用法：
  python3 tools/survey/mirror_site.py --start https://www.ipip.ori.org/ \
      --out archive/ipip/site --manifest archive/ipip/site_manifest.jsonl \
      --max-pages 3000 --delay 0.4
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from html.parser import HTMLParser

UA = "emohealth-archive/0.1 (offline preservation; contact: local research project)"

# 只跟这些扩展名/协议，其余（邮件、ftp 等）跳过
SKIP_SCHEMES = ("mailto:", "javascript:", "ftp:", "tel:", "data:")


class LinkExtractor(HTMLParser):
    """抽取 href/src，覆盖 <a> <link> <img> <frame> <iframe> <script>。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []

    def _maybe(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if key in ("href", "src") and value:
                self.links.append(value)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("a", "link", "img", "frame", "iframe", "script", "area"):
            self._maybe(tag, attrs)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)


def norm_url(base: str, raw: str) -> str | None:
    raw = raw.strip()
    if not raw or raw.startswith("#"):
        return None
    low = raw.lower()
    if any(low.startswith(s) for s in SKIP_SCHEMES):
        return None
    absolute = urllib.parse.urljoin(base, raw)
    parts = urllib.parse.urlsplit(absolute)
    if parts.scheme not in ("http", "https"):
        return None
    # 去掉 fragment；保留 query（部分页面靠 query 区分内容）
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))


def local_path(root: str, url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    path = urllib.parse.unquote(parts.path)
    if path.endswith("/"):
        path += "index.html"
    if not os.path.splitext(path)[1]:
        path += ".html"
    # 防目录穿越
    path = path.lstrip("/")
    path = os.path.normpath(path)
    if path.startswith(".."):
        path = path.replace("..", "_")
    if parts.query:
        digest = hashlib.sha1(parts.query.encode("utf-8")).hexdigest()[:8]
        stem, ext = os.path.splitext(path)
        path = f"{stem}__q{digest}{ext}"
    return os.path.join(root, path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", action="append", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--max-pages", type=int, default=3000)
    ap.add_argument("--max-bytes", type=int, default=80 * 1024 * 1024, help="单文件上限")
    ap.add_argument("--delay", type=float, default=0.4)
    ap.add_argument("--timeout", type=float, default=30.0)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(args.manifest)) or ".", exist_ok=True)

    seen: set[str] = set()
    queue: deque[str] = deque()
    host: str | None = None

    for s in args.start:
        u = norm_url(s, s)
        if u:
            if host is None:
                host = urllib.parse.urlsplit(u).netloc
            queue.append(u)

    manifest_fh = open(args.manifest, "a", encoding="utf-8")
    ok = fail = skipped = 0

    while queue and len(seen) < args.max_pages:
        url = queue.popleft()
        if url in seen:
            continue
        seen.add(url)

        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=args.timeout) as resp:
                ctype = resp.headers.get("Content-Type", "")
                blob = resp.read(args.max_bytes + 1)
                status = resp.status
        except urllib.error.HTTPError as e:
            fail += 1
            manifest_fh.write(json.dumps({
                "url": url, "status": e.code, "error": "HTTPError",
                "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            }, ensure_ascii=False) + "\n")
            manifest_fh.flush()
            continue
        except Exception as e:  # noqa: BLE001 - 归档脚本要吞掉网络异常继续跑
            fail += 1
            manifest_fh.write(json.dumps({
                "url": url, "status": None, "error": f"{type(e).__name__}: {e}",
                "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            }, ensure_ascii=False) + "\n")
            manifest_fh.flush()
            continue

        if len(blob) > args.max_bytes:
            skipped += 1
            manifest_fh.write(json.dumps({
                "url": url, "status": status, "error": "TOO_LARGE",
                "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            }, ensure_ascii=False) + "\n")
            manifest_fh.flush()
            continue

        dest = local_path(args.out, url)
        os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
        with open(dest, "wb") as fh:
            fh.write(blob)

        manifest_fh.write(json.dumps({
            "url": url,
            "status": status,
            "content_type": ctype,
            "bytes": len(blob),
            "sha256": hashlib.sha256(blob).hexdigest(),
            "path": os.path.relpath(dest, os.path.dirname(os.path.abspath(args.manifest)) or "."),
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }, ensure_ascii=False) + "\n")
        manifest_fh.flush()
        ok += 1

        # 只解析文本型页面
        if "html" in ctype.lower():
            text = blob.decode("utf-8", errors="replace")
            parser = LinkExtractor()
            try:
                parser.feed(text)
            except Exception:  # noqa: BLE001 - 畸形 HTML 不应中断归档
                pass
            for raw in parser.links:
                nxt = norm_url(url, raw)
                if not nxt or nxt in seen:
                    continue
                if urllib.parse.urlsplit(nxt).netloc != host:
                    continue
                queue.append(nxt)

        if args.delay:
            time.sleep(args.delay)

        if ok % 100 == 0:
            print(f"[progress] ok={ok} fail={fail} queued={len(queue)} seen={len(seen)}",
                  file=sys.stderr, flush=True)

    manifest_fh.close()
    print(json.dumps({"ok": ok, "fail": fail, "skipped": skipped, "seen": len(seen),
                      "out": args.out, "manifest": args.manifest}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
