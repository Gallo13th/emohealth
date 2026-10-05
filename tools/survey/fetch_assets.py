#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""资产下载器 —— 按 JSON 清单抓取并记录溯源信息。

清单格式（JSON 数组）：
  [{"name": "文件名", "url": "下载地址", "dir": "相对此清单的输出子目录"}, ...]

每个成功下载的产物在 --manifest 指定的 jsonl 中追加一行：
  {"name","url","dir","path","status","bytes","sha256","retrieved_at"}

用法：
  python3 tools/survey/fetch_assets.py --spec spec.json --out archive/datasets/osf-johnson \
      --manifest archive/datasets/osf-johnson/manifest.jsonl
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

UA = "emohealth-archive/0.1 (offline preservation)"

# 用 curl 子进程而非 urllib：OSF 的下载会 302 到 Google Cloud Storage，
# urllib 在该链路上挂起（实测 curl 2.7s 完成，urllib 300s 超时）。
# curl 同时避免了本机代理环境下的兼容问题。
CURL = "curl"


def download(url: str, dest: str, timeout: float = 300.0) -> tuple[int, bytes]:
    tmp = dest + ".part"
    proc = subprocess.run(
        [CURL, "-sSL", "--fail", "--retry", "3", "--retry-delay", "2",
         "--connect-timeout", "20", "--max-time", str(int(timeout)),
         "-A", UA, "-o", tmp, "-w", "%{http_code}", url],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise RuntimeError(f"curl exit {proc.returncode}: {proc.stderr.strip()[:200]}")
    code = int((proc.stdout or "0").strip() or 0)
    blob = open(tmp, "rb").read()
    os.replace(tmp, dest)
    return code, blob


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--timeout", type=float, default=300.0)
    ap.add_argument("--skip-existing", action="store_true", default=True)
    args = ap.parse_args()

    with open(args.spec, encoding="utf-8") as fh:
        spec = json.load(fh)

    os.makedirs(args.manifest.rsplit("/", 1)[0] or ".", exist_ok=True)
    mfh = open(args.manifest, "a", encoding="utf-8")
    ok = fail = skip = 0

    for entry in spec:
        name = entry["name"]
        url = entry["url"]
        sub = entry.get("dir", "")
        target_dir = os.path.join(args.out, sub) if sub else args.out
        os.makedirs(target_dir, exist_ok=True)
        dest = os.path.join(target_dir, name)

        if args.skip_existing and os.path.exists(dest) and os.path.getsize(dest) > 0:
            skip += 1
            print(f"[skip] {name}", file=sys.stderr, flush=True)
            continue

        try:
            status, blob = download(url, dest, args.timeout)
        except Exception as e:  # noqa: BLE001 - 归档脚本需吞异常继续
            fail += 1
            mfh.write(json.dumps({"name": name, "url": url, "dir": sub,
                                  "status": None, "error": f"{type(e).__name__}: {e}",
                                  "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")},
                                 ensure_ascii=False) + "\n")
            mfh.flush()
            print(f"[FAIL] {name}: {e}", file=sys.stderr, flush=True)
            continue

        if status != 200:
            fail += 1
            mfh.write(json.dumps({"name": name, "url": url, "dir": sub,
                                  "status": status, "error": "HTTPError",
                                  "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")},
                                 ensure_ascii=False) + "\n")
            mfh.flush()
            print(f"[FAIL {status}] {name}", file=sys.stderr, flush=True)
            continue

        with open(dest, "wb") as fh:
            fh.write(blob)

        mfh.write(json.dumps({
            "name": name, "url": url, "dir": sub,
            "path": os.path.relpath(dest, os.path.dirname(os.path.abspath(args.manifest)) or "."),
            "status": status, "bytes": len(blob),
            "sha256": hashlib.sha256(blob).hexdigest(),
            "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }, ensure_ascii=False) + "\n")
        mfh.flush()
        ok += 1
        print(f"[ok {len(blob)//1024}KB] {name}", file=sys.stderr, flush=True)

    mfh.close()
    print(json.dumps({"ok": ok, "fail": fail, "skip": skip}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
