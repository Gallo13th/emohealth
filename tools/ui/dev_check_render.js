// 渲染产出的**静态检查**（开发用）：语法、死代码、以及标注是否真的不重叠。
//
// 为什么需要「标注重叠」这一条：这是看图才能发现的问题，但它其实是**几何**问题，
// 可以离线断言。截图里出现过「支线名压在维度名上」「名字压在节点上」，
// 每次都靠肉眼看图发现太慢，所以把它变成可判定的检查。
// 检查器自己也踩过坑：一开始把 300 个**淡骨架**节点都当成障碍物，
// 于是报了一堆假重叠——只有**看得见**的节点才算障碍。
//
// 用法：node tools/ui/dev_check_render.js
const fs = require('fs'), path = require('path');
const ROOT = require('../_root.js').findRoot(__dirname);
const html = fs.readFileSync(ROOT + '/ui/index.html', 'utf8');
const b = html.match(/<script>[\s\S]*?<\/script>/g);
const code = b[b.length - 1].replace(/<\/?script>/g, '').replace(/^\s*"use strict";/m, '');
try { new Function(code); console.log('✅ 语法通过'); }
catch (e) { console.log('❌ 语法错误:', e.message); process.exit(1); }

// 这些名字若只剩一处（声明本身）就是死代码。已删的：TREE/angOf（旧径向几何）、
// LY（layout-data 已并入 net-layout）、reachedRings/fullRingCount/deepestAnsweredRing
// （「层」已从界面退场，D99）。
const names = ['facetWindowEnd', 'maxWindowEnd', 'NET', 'NR_OF', 'isNarrow', 'placeLabels'];
const dead = [];
for (const n of names) {
  const c = code.split(new RegExp('\\b' + n + '\\b')).length - 1;
  if (c <= 1) dead.push(n);
}
console.log(dead.length ? `  ⚠ 疑似死代码：${dead.join(' ')}` : '  ✅ 无死代码');
// 「层」不该再出现在用户可见的文案里（除了「第 1 环强制」这条产品规则）
const ringWords = (code.match(/完成 \d+ 层|第 \$\{[^}]*\}\/10 层|最深支线/g) || []);
console.log(ringWords.length ? `  ⚠ 界面仍在报层数：${ringWords.join(' / ')}`
                             : '  ✅ 界面已不报「完成几层」');

/* ── 标注重叠检查：直接渲染几个状态，取 SVG 里的 text 元素算盒 ── */
const T = require('./dev_probe.js');
const els = {};
const mk = id => els[id] || (els[id] = {id, innerHTML: ''});
let NARROW = false;
global.window = global.window || {};
global.window.matchMedia = () => ({matches: NARROW});   // 让 isNarrow() 可控
global.document = {getElementById: mk, querySelectorAll: () => [], querySelector: () => null,
  addEventListener(){}, createElement: () => mk('t'), body: {appendChild(){}}};
const {D, TR, S} = T;
const CHW = 11.5, LH = 13;

function boxes(svg) {
  const out = [];
  const re = /<text class="(facetlbl[^"]*|domlbl)"[^>]*x="([-\d.]+)"[^>]*y="([-\d.]+)"[^>]*text-anchor="(start|end)"[^>]*>([^<]*)</g;
  let m;
  while ((m = re.exec(svg))) {
    const [, cls, xs, ys, anchor, txt] = m;
    const x = +xs, y = +ys, w = txt.length * CHW;
    out.push({cls, txt,
      x0: anchor === 'start' ? x : x - w, x1: anchor === 'start' ? x + w : x,
      y0: y - LH / 2, y1: y + LH / 2});
  }
  // 节点盒子：**只算看得见的**（ans/open/rec）。把 300 个淡骨架节点也算进去
  // 会得到一堆假重叠（检查器自己踩过这个坑）。
  const gs = svg.match(/<g class="nd (?:ans|open|rec)"[\s\S]*?<\/g>/g) || [];
  const nodes = [];
  for (const gg of gs) {
    const c = gg.match(/<circle cx="([-\d.]+)" cy="([-\d.]+)" r="([\d.]+)"/);
    if (!c) continue;
    const x = +c[1], y = +c[2], r = +c[3];
    nodes.push({x0: x - r, x1: x + r, y0: y - r, y1: y + r, node: true});
  }
  return {labels: out, nodes};
}
const hit = (a, b) => a.x0 < b.x1 && b.x0 < a.x1 && a.y0 < b.y1 && b.y0 < a.y1;

let bad = 0;
for (const n of [0, 30, 45, 60, 90, 150, 300]) {
  S.resp = {};
  TR.order.slice(0, n).forEach(o => S.resp[o] = 3);
  T.refreshAdapt();
  T.renderTierGraph();
  const svg = els['graphbox'].innerHTML;
  const {labels, nodes} = boxes(svg);
  const overl = [];
  for (let i = 0; i < labels.length; i++)
    for (let j = i + 1; j < labels.length; j++)
      if (hit(labels[i], labels[j]))
        overl.push(`${labels[i].txt}×${labels[j].txt}`);
  const onNode = labels.filter(l => nodes.some(nd => hit(l, nd))).map(l => l.txt);
  const ok = overl.length === 0 && onNode.length === 0;
  if (!ok) bad++;
  console.log(`  ${ok ? '✅' : '❌'} 已答 ${String(n).padStart(3)}：`
    + `${labels.length} 个标注，互相重叠 ${overl.length}`
    + (overl.length ? `（${overl.slice(0, 3).join(' ')}）` : '')
    + `，压节点 ${onNode.length}`
    + (onNode.length ? `（${onNode.slice(0, 3).join(' ')}）` : ''));
}

/* ── 窄屏检查：节点要放大（手指点得准）、支线名要让位给「推荐那几道」 ── */
NARROW = true;
console.log('\n=== 窄屏（≤700px）：几何放大 + 标注减负 ===');
{
  S.resp = {};
  TR.order.slice(0, 60).forEach(o => S.resp[o] = 3);
  T.refreshAdapt();
  T.renderTierGraph();
  const svg = els['graphbox'].innerHTML;
  const {labels, nodes} = boxes(svg);
  const radii = [...svg.matchAll(/<g class="nd ans[\s\S]*?r="([\d.]+)"/g)].map(m => +m[1]);
  const nr = T.NR_OF();
  const overl = [];
  for (let i = 0; i < labels.length; i++)
    for (let j = i + 1; j < labels.length; j++)
      if (hit(labels[i], labels[j])) overl.push(`${labels[i].txt}×${labels[j].txt}`);
  const bare = labels.filter(l => !/^(神经质|外向性|开放性|宜人性|尽责性)$/.test(l.txt));
  const cks = [
    ['窄屏节点半径放大（宽屏 8.4 → 窄屏 ' + nr + '）', nr >= 13],
    ['窄屏标注数量收敛（只留维度名 + 推荐那几道）',
     labels.length <= 12, `${labels.length} 个：${labels.map(l => l.txt).join(' ')}`],
    ['窄屏标注不互相重叠', overl.length === 0, overl.slice(0, 3).join(' ')],
    ['窄屏有「亮着的是可答 / 橙色脉冲是推荐的几道」提示',
     /橙色脉冲是推荐的几道/.test(svg)],
  ];
  for (const [n2, ok2, d2] of cks) {
    if (!ok2) bad++;
    console.log(`  ${ok2 ? '✅' : '❌'} ${n2}${d2 ? `  —— ${d2}` : ''}`);
  }
  console.log(`  （可见节点 ${nodes.length} 个，标注 ${labels.length} 个`
    + `${bare.length ? '：' + bare.map(l => l.txt).join(' ') : ''}）`);
}
console.log(bad ? `\n❌ ${bad} 项未通过` : '\n✅ 宽屏与窄屏的标注都不重叠、不压节点');
process.exit(bad ? 1 : 0);
