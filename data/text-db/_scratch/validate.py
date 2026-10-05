import json, sys

src = json.load(open(r"C:\Codes\emohealth-20260930-full\emohealth\data\text-db\pending\batch-000.json", encoding="utf-8"))
out = json.load(open(r"C:\Codes\emohealth-20260930-full\emohealth\data\text-db\_scratch\batch-000.zh.json", encoding="utf-8"))

print("source count:", src["count"], "items:", len(src["items"]))
print("out len:", len(out), "is list:", isinstance(out, list))

ok = True
if len(out) != len(src["items"]):
    ok = False
    print("FAIL count mismatch")

for i, (a, b) in enumerate(zip(src["items"], out)):
    if a["key"] != b["key"]:
        ok = False
        print(f"FAIL key {i}: {a['key']!r} != {b['key']!r}")
    if set(b.keys()) != {"key", "zh", "note"}:
        ok = False
        print(f"FAIL fields {i}: {sorted(b.keys())}")
    if not b["zh"].strip() or not b["note"].strip():
        ok = False
        print(f"FAIL empty {i}")
    if len(b["note"]) > 60:
        ok = False
        print(f"FAIL note len {i}: {len(b['note'])} -> {b['note']}")
    for ch in ("\u0000",):
        if ch in (b["zh"] + b["note"]):
            print(f"WARN control char in {i}")

keys_src = [x["key"] for x in src["items"]]
keys_out = [x["key"] for x in out]
print("multiset equal:", sorted(keys_src) == sorted(keys_out))
print("order equal:", keys_src == keys_out)
print("max note len:", max(len(x["note"]) for x in out))
print("ALL OK" if ok else "PROBLEMS FOUND")
