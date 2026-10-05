import json, io, sys, os

base = r"C:\Codes\emohealth-20260930-full\emohealth\data\text-db\pending"
src = json.load(open(os.path.join(base, "batch-021.json"), encoding="utf-8"))
path = os.path.join(base, "batch-021-zh.json")

raw = open(path, "rb").read()
print("BOM:", raw[:3] == b"\xef\xbb\xbf", "| size:", len(raw))
txt = raw.decode("utf-8")
print("decoded as utf-8 strictly: OK")

out = json.loads(txt)
print("is list:", isinstance(out, list), "| len:", len(out), "| declared:", src["count"], "| items:", len(src["items"]))

errs = []
in_keys = [i["key"] for i in src["items"]]
out_keys = [o.get("key") for o in out]
if len(out) != len(in_keys):
    errs.append("count mismatch")
if in_keys != out_keys:
    errs.append("key order/content mismatch")
    for a, b in zip(in_keys, out_keys):
        if a != b:
            print("  MISMATCH:", repr(a), "!=", repr(b))
    print("  EXTRA:", set(out_keys) - set(in_keys), "MISSING:", set(in_keys) - set(out_keys))

for idx, o in enumerate(out):
    if set(o.keys()) != {"key", "zh", "note"}:
        errs.append(f"row {idx}: fields {sorted(o.keys())}")
    zh, note = o.get("zh", ""), o.get("note", "")
    if not zh.strip(): errs.append(f"row {idx}: empty zh")
    if not note.strip(): errs.append(f"row {idx}: empty note")
    if len(note) > 60: errs.append(f"row {idx}: note {len(note)} chars")
    if "\ufffd" in zh + note: errs.append(f"row {idx}: replacement char")
    if zh.strip().rstrip("\u3002") == src["items"][idx]["en"].rstrip("."):
        errs.append(f"row {idx}: untranslated")

print("max note len:", max(len(o["note"]) for o in out))
print("min note len:", min(len(o["note"]) for o in out))
print("max zh len:", max(len(o["zh"]) for o in out))
print("dup keys:", len(out_keys) != len(set(out_keys)))

print("\n--- pairing ---")
for s, o in zip(src["items"], out):
    print(f"[{s['context']}] {s['en']}\n   -> {o['zh']}\n   # {o['note']}")

print("\nRESULT:", "PASS" if not errs else "FAIL")
for e in errs:
    print(" -", e)
sys.exit(1 if errs else 0)
