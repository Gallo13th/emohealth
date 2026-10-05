import json, io, sys

base = r'data/text-db/pending'
src = json.load(io.open(base + '/batch-000.json', encoding='utf-8'))
out = json.load(io.open(base + '/.batch-000.zh-out.json', encoding='utf-8'))

ik = [it['key'] for it in src['items']]
ok = [it['key'] for it in out]
errs = []
if len(out) != len(ik):
    errs.append('count mismatch: in=%d out=%d' % (len(ik), len(out)))
if ok != ik:
    for i, (a, b) in enumerate(zip(ik, ok)):
        if a != b:
            errs.append('key mismatch at %d: %r != %r' % (i, a, b))
    if len(ok) != len(ik):
        errs.append('key list differs in length')
if len(set(ok)) != len(ok):
    errs.append('duplicate keys present')
for i, it in enumerate(out):
    if set(it.keys()) != {'key', 'zh', 'note'}:
        errs.append('bad fields at %d: %s' % (i, sorted(it.keys())))
    if not it.get('zh', '').strip():
        errs.append('empty zh at %d' % i)
    n = it.get('note', '')
    if len(n) > 60:
        errs.append('note too long at %d (%d chars): %s' % (i, len(n), n))
    if not n.strip():
        errs.append('empty note at %d' % i)

print('items in :', len(ik))
print('items out:', len(out))
print('notes max chars:', max(len(it['note']) for it in out))
print('ERRORS:', len(errs))
for e in errs:
    print(' -', e)
sys.exit(1 if errs else 0)
