// 勘查：把 archive/OpenScales 里每个量表的**可判定要素**提取成机器可读清单。
//
// 为什么先做这个而不是直接读题：这个项目的规则是「界面上的每个数字都必须能追到
// 出处」，所以选量表的第一步不是题量，而是**授权 + 常模 + 计分 + 施测说明**四件事
// 齐不齐。这份清单把每个 .osd 的这四项摊开，缺什么一眼看到。
//
// 输出：research/scales/inventory.json（逐量表）+ 控制台摘要
const fs = require('fs'), path = require('path');

const ROOT = 'archive/ipip/data/OpenScales';
const OUT = 'research/scales/inventory.json';

const status = fs.readFileSync(path.join(ROOT, 'scales/scale_status.csv'), 'utf8')
  .split('\n').slice(1).filter(Boolean).map(l => l.split(','));

const osdFiles = [];
(function walk(d) {
  for (const e of fs.readdirSync(d, {withFileTypes: true})) {
    const p = path.join(d, e.name);
    if (e.isDirectory()) walk(p);
    else if (e.name.endsWith('.osd')) osdFiles.push(p);
  }
})(ROOT);

const strings = (o, acc = []) => {
  if (typeof o === 'string') acc.push(o);
  else if (Array.isArray(o)) o.forEach(x => strings(x, acc));
  else if (o && typeof o === 'object') Object.values(o).forEach(x => strings(x, acc));
  return acc;
};
const findKey = (o, re, out = []) => {
  if (o && typeof o === 'object') {
    for (const [k, v] of Object.entries(o)) {
      if (re.test(k)) out.push([k, v]);
      findKey(v, re, out);
    }
  }
  return out;
};

const rows = [];
for (const f of osdFiles) {
  const code = path.basename(f, '.osd');
  const st = status.find(r => r[0] === code) || [];
  const rel = f.replace(/\\/g, '/');
  let j = null, err = null;
  try { j = JSON.parse(fs.readFileSync(f, 'utf8')); } catch (e) { err = e.message; }
  if (!j) { rows.push({code, file: rel, parse_error: err}); continue; }

  const ss = strings(j);
  const lic = ss.find(s => /copyright|permission|licen|public domain|CC BY/i.test(s)) || '';
  const licUrl = ss.find(s => /^https?:\/\/creativecommons|^https?:\/\/.*licen/i.test(s)) || '';
  const cite = ss.find(s => /\b(19|20)\d{2}\b/.test(s) && s.length > 30 &&
                            !/^https?:/.test(s) && !/copyright|permission/i.test(s)) || '';

  // 题项：第一人称/第二人称陈述，且不是选项标签或说明
  const looksLikeItem = s => s.length > 14 && s.length < 220 &&
    /\b(I|my|me|you|your)\b/.test(s) &&
    !/^(I|my|me|you|your)$/i.test(s) &&
    !/^https?:|copyright|permission|licen|^Mean of|^Sum of|range \d/i.test(s);
  const items = ss.filter(looksLikeItem);

  const likert = findKey(j, /^likert|response_?option|scale_?point/i)
    .map(([k, v]) => ({k, v: typeof v === 'object' ? v : String(v).slice(0, 80)}));
  const domains = findKey(j, /^domain|^subscale|^facet|^dimension|^factor/i)
    .map(([k, v]) => ({k, n: Array.isArray(v) ? v.length : (v && typeof v === 'object' ? Object.keys(v).length : 1)}));

  rows.push({
    code,
    name: st[1] || (findKey(j, /^name$/)[0] || [])[1] || code,
    abbr: st[2] || '',
    domain_class: st[3] || '',
    declared_items: st[4] || '',
    license_field: st[5] || '',
    license_text: String(lic).replace(/\s+/g, ' ').slice(0, 300),
    license_url: licUrl,
    citation_hint: String(cite).replace(/\s+/g, ' ').slice(0, 200),
    item_like_strings: items.length,
    likert: likert.slice(0, 3),
    structures: domains.slice(0, 6),
    bytes: fs.statSync(f).size,
    file: rel,
  });
}

rows.sort((a, b) => (b.item_like_strings || 0) - (a.item_like_strings || 0));
fs.writeFileSync(OUT, JSON.stringify({generated_from: ROOT, count: rows.length, scales: rows}, null, 1));

console.log(`量表总数：${rows.length}（已写入 ${OUT}）\n`);
console.log('代码'.padEnd(16), '题项'.padEnd(5), '声明'.padEnd(5), '授权字段'.padEnd(30), '名称');
console.log('-'.repeat(104));
for (const r of rows) {
  if (r.parse_error) { console.log(r.code.padEnd(16), '解析失败', r.parse_error); continue; }
  console.log(
    String(r.code).padEnd(16),
    String(r.item_like_strings).padEnd(5),
    String(r.declared_items).padEnd(5),
    String(r.license_field).slice(0, 28).padEnd(30),
    String(r.name).slice(0, 42));
}
