# -*- coding: utf-8 -*-
"""Verify batch-001-zh.json: valid JSON, UTF-8 no BOM, 25 items, keys byte-identical."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "batch-001.json")
DST = os.path.join(HERE, "batch-001-zh.json")

raw = open(DST, "rb").read()
print("BOM:", raw[:3] == b"\xef\xbb\xbf")
print("bytes:", len(raw), "valid utf-8:", bool(raw.decode("utf-8")))

zh = json.loads(raw.decode("utf-8"))
src = json.load(open(SRC, encoding="utf-8"))
items = src["items"] if isinstance(src, dict) else src

print("count src/zh:", len(items), len(zh))
assert isinstance(zh, list) and len(zh) == len(items) == 25
ok = True
for i, (a, b) in enumerate(zip(items, zh)):
    assert set(b.keys()) == {"key", "zh", "note"}, b.keys()
    if a["key"] != b["key"]:
        ok = False
        print("KEY MISMATCH", i, repr(a["key"]), repr(b["key"]))
    assert b["zh"].strip() and b["note"].strip()
    assert len(b["note"]) <= 60, (i, len(b["note"]))
print("keys identical:", ok)
print("no html-tag source items:", all(("<" not in i["en"]) for i in items))
print("max note len:", max(len(b["note"]) for b in zh))
print("RESULT:", "PASS" if ok else "FAIL")
