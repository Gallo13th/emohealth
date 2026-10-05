import json, io, re

b = 'data/text-db/pending/'
src = json.load(io.open(b + 'batch-000.json', encoding='utf-8'))['items']
out = json.load(io.open(b + '.batch-000.zh-out.json', encoding='utf-8'))

NEG_MARK = ('不', '没', '难以', '未', '并非', '无')
pat = re.compile(r"(?i)\b(not|non-|can't|difficult|declin|less|other than)\b")
lines = []
bad = 0
for s, o in zip(src, out):
    if pat.search(s['en']):
        has_neg = any(c in o['zh'] for c in NEG_MARK)
        if not has_neg:
            bad += 1
        lines.append('%s | EN: %s | ZH: %s' % ('NEG-OK ' if has_neg else 'NEG-MISS', s['en'], o['zh']))
lines.append('negative-polarity items checked: %d, missing Chinese negation: %d' % (
    sum(1 for s in src if pat.search(s['en'])), bad))
io.open(b + '.batch-000.zh-audit.txt', 'w', encoding='utf-8').write('\n'.join(lines))
print('written')
