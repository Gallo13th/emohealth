#!/bin/sh
# 打包，供换机器使用。
#
# ⚠️ **顺序有讲究**，踩过一次：
#     MANIFEST.sha256 必须在**所有内容文件定稿之后**生成，
#     否则改了文件却没重算校验和，解包校验就会 FAILED。
#     另：MANIFEST.sha256 必须**排除自己**——否则它一边被写一边被哈希。
#
# 用法：  ./tools/package.sh [输出目录]
set -e
HERE="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$(dirname "$HERE")}"
NAME="$(basename "$HERE")"
STAMP="$(date +%Y%m%d)"
cd "$HERE"

export COPYFILE_DISABLE=1          # 别把 macOS 的 ._ 资源叉打进包

echo "① 清理临时产物"
find . -name "__pycache__" -type d -not -path "./vendor/*" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name ".DS_Store" -delete 2>/dev/null || true
rm -rf .shot 2>/dev/null || true

echo "② 生成 MANIFEST.txt"
python3 - "$HERE" <<'PY'
import os, sys, datetime
from collections import Counter
ROOT = sys.argv[1]
SKIP = {'.git', 'vendor', '__pycache__', '.shot', 'node_modules', '.DS_Store'}
rows = []
for dp, dns, fns in os.walk(ROOT):
    dns[:] = [d for d in dns if d not in SKIP]
    for fn in fns:
        if fn in SKIP or fn.endswith('.pyc'):
            continue
        p = os.path.join(dp, fn)
        rows.append((os.path.relpath(p, ROOT), os.path.getsize(p)))
rows.sort()
core = [r for r in rows if not r[0].startswith('archive' + os.sep)]
arch = [r for r in rows if r[0].startswith('archive' + os.sep)]
bucket = lambda rel: os.sep.join(rel.split(os.sep)[:2]) if os.sep in rel else rel
L = ["# EmoHealth 打包清单",
     f"# 生成时间 {datetime.datetime.now().isoformat(timespec='seconds')}",
     f"# 文件总数 {len(rows)}（核心 {len(core)}，档案 {len(arch)}）",
     f"# 总大小 {sum(s for _, s in rows)/1024/1024:.1f} MB",
     "#",
     "# 核心文件校验：  shasum -a 256 -c MANIFEST.sha256",
     "# 档案校验：      python3 tools/check/verify_archive.py --root archive",
     "",
     f"## 核心文件（{len(core)} 个，逐字节校验）"]
L += [f"{s:>10}  {r}" for r, s in core]
L += ["", f"## 档案（{len(arch)} 个，按目录汇总）"]
for k, v in sorted(Counter(bucket(r) for r, _ in arch).items()):
    sz = sum(s for r, s in arch if bucket(r) == k)
    L.append(f"{v:>6} 个  {sz/1024/1024:>8.1f} MB  {k}")
open(os.path.join(ROOT, 'MANIFEST.txt'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
print(f"   核心 {len(core)}，档案 {len(arch)}，总 {sum(s for _, s in rows)/1024/1024:.1f} MB")
PY

echo "③ 生成 MANIFEST.sha256（排除自己）"
find . -type f \
  -not -path "./vendor/*" -not -path "./archive/*" \
  -not -name "*.pyc" -not -name ".DS_Store" -not -path "./.git/*" \
  -not -name "MANIFEST.sha256" \
  | LC_ALL=C sort | xargs shasum -a 256 > MANIFEST.sha256
n=$(wc -l < MANIFEST.sha256 | tr -d ' ')
ok=$(shasum -a 256 -c MANIFEST.sha256 2>/dev/null | grep -c ": OK" || true)
echo "   $n 条，自校验 $ok OK"
[ "$n" = "$ok" ] || { echo "❌ 自校验不通过，中止"; exit 1; }

echo "④ 打包（full = 含 archive；slim = 不含）"
cd "$(dirname "$HERE")"
tar --exclude="./$NAME/vendor" --exclude="*/__pycache__" --exclude="*.pyc" \
    --exclude=".DS_Store" --exclude="./$NAME/.shot" \
    -czf "$OUT/$NAME-$STAMP-full.tar.gz" "$NAME"
tar --exclude="./$NAME/vendor" --exclude="./$NAME/archive" \
    --exclude="*/__pycache__" --exclude="*.pyc" --exclude=".DS_Store" \
    --exclude="./$NAME/.shot" \
    -czf "$OUT/$NAME-$STAMP-slim.tar.gz" "$NAME"

echo "⑤ 解包复验"
T="$(mktemp -d)"
tar -xzf "$OUT/$NAME-$STAMP-slim.tar.gz" -C "$T"
bad=$(cd "$T/$NAME" && shasum -a 256 -c MANIFEST.sha256 2>/dev/null | grep -c "FAILED" || true)
rm -rf "$T"
[ "$bad" = "0" ] || { echo "❌ 解包后校验有 $bad 项失败"; exit 1; }

echo
ls -lh "$OUT/$NAME-$STAMP-"*.tar.gz | awk '{print "   " $5 "\t" $9}'
echo "✅ 完成（解包校验 0 失败）"
