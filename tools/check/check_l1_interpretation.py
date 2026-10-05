#!/usr/bin/env python3
"""检查 L1 量表包里的判读口径是否完整（13 域门槛 + PID-5 接口）。"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _root import find_root  # noqa: E402
ROOT = find_root()
d = json.load(open(os.path.join(ROOT, "data", "instruments", "dsm5tr-l1.json"),
                   encoding="utf-8"))
i = d.get("interpretation") or {}
print("kind:", i.get("kind"))
print("scoring:", str(i.get("scoring"))[:90])
print("域数:", len(i.get("domains") or []))
for x in (i.get("domains") or []):
    flag = "**" if x["threshold"] == 1 else "  "
    print(f"  {flag}{x['domain']:36} ≥{x['threshold']}  → L2: {x['level2']}")
p = i.get("pid5_interface") or {}
print("\nPID-5 接口:")
print("  status:", p.get("status"))
print("  from:", p.get("from_domain"), "→", p.get("to_instrument"))
print("  evidence:", str(p.get("evidence"))[:110])
print("\n免责声明:", str(i.get("disclaimer"))[:120])
