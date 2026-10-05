import json, io

base = r"C:\Codes\emohealth-20260930-full\emohealth\data\text-db\pending"
src = json.load(io.open(base + r"\batch-006.json", encoding="utf-8"))
out = json.load(io.open(base + r"\.batch-006.zh-draft.json", encoding="utf-8"))

sk = [i["key"] for i in src["items"]]
ok = [i["key"] for i in out]
print("src count:", len(sk), "out count:", len(ok))
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
    if len(i["note"]) > 60:
        bad.append(("note-len", i["key"], len(i["note"])))
    if not i["zh"].strip():
        bad.append(("empty-zh", i["key"], ""))
    if not i["note"].strip():
        bad.append(("empty-note", i["key"], ""))
print("violations:", bad)
print("zh==en (untranslated):", [i["key"] for i, s in zip(out, src["items"]) if i["zh"] == s["en"]])
print("zh identical to key:", [i["key"] for i in out if i["zh"] == i["key"]])
print("NUL-padded keys preserved:", [repr(i["key"]) for i in out if "\x00" in i["key"]])
print("max note len:", max(len(i["note"]) for i in out))
for i in out:
    print(len(i["note"]), "|", i["zh"])
