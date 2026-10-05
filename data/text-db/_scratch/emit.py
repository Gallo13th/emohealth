import json

out = json.load(open(r"C:\Codes\emohealth-20260930-full\emohealth\data\text-db\_scratch\batch-000.zh.json", encoding="utf-8"))
compact = [{"key": o["key"], "zh": o["zh"], "note": o["note"]} for o in out]
s = json.dumps(compact, ensure_ascii=False, separators=(",", ":"))
assert json.loads(s) == compact
print(s)
