#!/bin/sh
# 用系统 Python + 项目内 vendor 目录跑分析脚本。
#
# 为什么不用捆绑的 Python：它是**加固运行时**，加载不了 pip 装的 .so
# （Team ID 不匹配），ad-hoc 重签与去签名都无效。
#
# 新机器上先跑 ./bootstrap.sh 建好 vendor/。
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
if [ ! -d "$HERE/vendor" ]; then
  echo "缺少 vendor/ —— 先跑 ./bootstrap.sh" >&2
  exit 1
fi
PYTHONPATH="$HERE/vendor" exec "${EMOHEALTH_PY:-python3}" "$@"
