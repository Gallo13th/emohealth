#!/bin/sh
# 在新机器上建好分析环境。
#
# 用到两个 Python，分工不同：
#   · **引擎与测试**（engine/、tools/test_*.py、tools/validate_*.py）
#     只需要 numpy + pandas，用什么 Python 都行。
#   · **分析脚本**（tools/analyze_*.py、tools/build_*.py、tools/optimize_*.py、
#     tools/compare_*.py）需要 sklearn，装在项目内 vendor/，用系统 Python 跑。
#
# 用法：  ./bootstrap.sh            # 用 python3
#         EMOHEALTH_PY=python3.11 ./bootstrap.sh
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="${EMOHEALTH_PY:-python3}"
cd "$HERE"

echo "解释器：$($PY -V 2>&1)  ($(command -v "$PY"))"
$PY - <<'PYCHK'
import sys
if sys.version_info < (3, 9):
    sys.exit(f"需要 Python ≥3.9，当前 {sys.version.split()[0]}")
PYCHK

echo "装依赖到 vendor/ …"
$PY -m pip install --quiet --upgrade --target ./vendor -r requirements.txt

echo "自检："
PYTHONPATH="$HERE/vendor" $PY - <<'PYCHK'
import numpy, pandas, scipy, sklearn
print(f"  numpy {numpy.__version__}  pandas {pandas.__version__}  "
      f"scipy {scipy.__version__}  sklearn {sklearn.__version__}")
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import KFold
print("  sklearn 树模型与交叉验证可用")
PYCHK
echo "完成。跑 ./run.sh tools/analyze/compare_linear_vs_tree.py 试试。"
