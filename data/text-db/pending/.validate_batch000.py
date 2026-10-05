import json, io, sys

base = r"C:\Codes\emohealth-20260930-full\emohealth\data\text-db\pending"
src = json.load(io.open(base + r"\batch-000.json", encoding="utf-8"))
out = json.load(io.open(base + r"\.batch-000.zh-draft.json", encoding="utf-8"))

src_items = src["items"]
print("src count:", len(src_items), "out count:", len(out))

sk = [i["key"] for i in src_items]
ok = [i["key"] for i in out]
print("keys identical & same order:", sk == ok)
if sk != ok:
    for a, b in zip(sk, ok):
        if a != b:
            print("DIFF\n  src:", repr(a), "\n  out:", repr(b))
print("dup keys in out:", len(ok) != len(set(ok)))
print("extra/missing:", set(sk) ^ set(ok))

bad = []
for i in out:
    if set(i.keys()) != {"key", "zh", "note"}:
        bad.append(("fields", i["key"], list(i.keys())))
    n = len(i["note"])
    if n > 60:
        bad.append(("note-len", i["key"], n))
    if not i["zh"].strip():
        bad.append(("empty-zh", i["key"], ""))
    for ch in ('"', "\\"):
        pass
print("violations:", bad)
print("max note len:", max(len(i["note"]) for i in out))
for i in out:
    print(len(i["note"]), "|", i["zh"], "|", i["note"])
