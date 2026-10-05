import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
base = os.path.dirname(os.path.abspath(__file__))
src = json.load(open(base + r'\batch-032.json', encoding='utf-8'))
out = json.load(open(base + r'\batch-032.out.json', encoding='utf-8'))

errs = []
in_keys = [i['key'] for i in src['items']]
out_keys = [o.get('key') for o in out]

print('input count      :', len(in_keys), '(declared', src['count'], ')')
print('output count     :', len(out))

if len(out) != len(in_keys):
    errs.append('count mismatch')

if in_keys != out_keys:
    errs.append('key order/content mismatch')
    for a, b in zip(in_keys, out_keys):
        if a != b:
            print('  MISMATCH in=', repr(a), 'out=', repr(b))
    if len(set(out_keys)) != len(out_keys):
        errs.append('duplicate keys in output')
    extra = set(out_keys) - set(in_keys)
    missing = set(in_keys) - set(out_keys)
    if extra:   print('  EXTRA  :', extra)
    if missing: print('  MISSING:', missing)
else:
    print('key exact match  : OK (character-for-character, same order)')

# field / length checks
for idx, o in enumerate(out):
    if set(o.keys()) != {'key', 'zh', 'note'}:
        errs.append(f'row {idx}: unexpected fields {sorted(o.keys())}')
    zh, note = o.get('zh', ''), o.get('note', '')
    if not zh.strip():  errs.append(f'row {idx} ({o.get("key")}): empty zh')
    if not note.strip(): errs.append(f'row {idx} ({o.get("key")}): empty note')
    if len(note) > 60:
        errs.append(f'row {idx} ({o.get("key")}): note {len(note)} chars > 60')
    # Chinese must not be identical to English source (sanity: actually translated)
    en = src['items'][idx]['en'].rstrip('.')
    if zh.strip().rstrip('。') == en:
        errs.append(f'row {idx}: untranslated')

# terminology consistency spot-check (forbidden/required terms)
banned = {'焦虑性': 'anxiousness must be 焦虑', '域面': 'domain must be 域'}
body = json.dumps(out, ensure_ascii=False)
for term, why in banned.items():
    if term in body:
        errs.append(f'banned term {term}: {why}')

maxnote = max(len(o['note']) for o in out)
print('quotes/escapes   : OK (json parsed)')
print('max note length  :', maxnote)
print('empty zh/note    :', sum(1 for o in out if not o['zh'].strip() or not o['note'].strip()))

# quick dump for eyeballing pairing
print('\n--- zh / en pairing ---')
for s, o in zip(src['items'], out):
    print(f"{o['key']}\n  EN: {s['en']}\n  ZH: {o['zh']}\n  NT: {o['note']}")

if errs:
    print('\nRESULT: FAIL')
    for e in errs:
        print(' -', e)
    sys.exit(1)
print('\nRESULT: PASS')
