// 选量表：先看「一套完整的量表」，而不是几百个 10 题子量表
const fs = require('fs');
const inv = JSON.parse(fs.readFileSync('research/scales/inventory.json', 'utf8'));

// ① 主量表：题量 >= 20，且不是 IPIP 语言主池 / PhenX 体检类
const isSubscale = r => /-(?:[A-Z][a-z]{2}|[A-Z]{2,4}\d?)$/.test(r.code) &&
  (+r.declared_items || 0) <= 20;                 // 如 IPIP-AB5C-Trq
const isLangPool = r => /^ipip_master/.test(r.code);
const isPhenX = r => /^PX\d/.test(r.code);
const offTopic = /Sickle|Asthma|Epilepsy|Hemophilia|Scoliosis|Respiratory|Hearing Loss|Care - |Family History|Physical Activity|Sitting/i;

const main = inv.scales.filter(r => !r.parse_error)
  .filter(r => !isLangPool(r) && !isPhenX(r) && !offTopic.test(r.name))
  .filter(r => !isSubscale(r))
  .filter(r => (+r.declared_items || 0) >= 15 || /PID|SIBord|CAT-?PD/.test(r.code));

const licCat = r => {
  const l = `${r.license_field} ${r.license_text}`;
  if (/public domain/i.test(l)) return '1 公有领域';
  if (/creativecommons|CC BY/i.test(l)) return '2 CC 署名';
  if (/free to use|freely availab|free for research/i.test(l)) return '3 免费（待核）';
  if (/copyright/i.test(l)) return '4 有版权（逐条看）';
  return '5 未知';
};
main.forEach(r => r.licCat = licCat(r));
main.sort((a, b) => a.licCat.localeCompare(b.licCat) ||
                    (+b.declared_items || 0) - (+a.declared_items || 0));

console.log(`完整量表候选：${main.length} 个（题量 ≥15）\n`);
let cur = '';
for (const r of main) {
  if (r.licCat !== cur) { cur = r.licCat; console.log(`\n══════ ${cur} ══════`); }
  console.log(`  ${String(r.code).padEnd(20)} ${String(r.declared_items || '?').padStart(4)} 题  ` +
    `${String(r.name).slice(0, 50)}`);
  if (r.license_text) console.log(`      └ ${r.license_text.slice(0, 96)}`);
}
fs.writeFileSync('research/scales/candidates.json',
  JSON.stringify({note: '完整量表候选（题量≥15）', count: main.length, scales: main}, null, 1));

// ② 专项：PID-5 完整版？中文？大规模常模？
console.log('\n\n═══ 专项核查 ═══');
const hit = (re) => inv.scales.filter(r => !r.parse_error &&
  re.test(`${r.code} ${r.name} ${r.license_text} ${r.citation_hint}`)).slice(0, 12);
for (const [label, re] of [
  ['PID-5 完整版 / 220 题', /PID-?5(?!BF)|220\s*item|PID5\b/i],
  ['CAT-PD / 人格病理', /CAT-?PD|personality disorder/i],
  ['中文 / 中国常模', /chinese|mandarin|中文|CN\b|China/i],
  ['大规模常模线索', /norm|normative|20,?993|20993|110,?000|1,?000,?000/i],
]) {
  const rows = hit(re);
  console.log(`\n· ${label}：${rows.length} 条`);
  for (const r of rows.slice(0, 8))
    console.log(`    ${String(r.code).padEnd(20)} ${String(r.declared_items || '?').padStart(4)} 题  ${String(r.name).slice(0, 44)}`);
}
