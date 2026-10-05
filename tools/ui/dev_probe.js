// 开发期探针（不进 v1 交付）：直接 eval ui/index.html 的脚本，暴露内部函数供核查。
// 用法：node tools/ui/dev_probe.js
const fs = require('fs'), path = require('path');
const ROOT = require('../_root.js').findRoot(__dirname);
const html = fs.readFileSync(ROOT + '/ui/index.html', 'utf8');
const b = html.match(/<script>[\s\S]*?<\/script>/g);
let code = b[b.length - 1].replace(/<\/?script>/g, '').replace(/^\s*"use strict";/m, '');
code += `\n;globalThis.__T={D,TR,UN,AD,NET,NR,isNarrow,NR_OF,S,itemByOrder,facetOrders,tierNodeState,tierRingOfOrder,tierRingProgress,netR2,netUnlocked,ownCount,ceilingOf,ceilingRatio,readyR,rOf,facetReady,readyFacets,recommend,totalGain,unlockNote,ring1Done,refreshAdapt,renderTierGraph,renderTierPanel,renderTierTree,nextQuestionHtml,facetWindowEnd,maxWindowEnd,adaptCtx,gainCeiling,buildReport,renderTop,confOf,pairR};`;
const els = {};
const mk = id => els[id] || (els[id] = {
  id, textContent: '', innerHTML: '', value: '', files: null,
  classList: {add(){}, remove(){}, toggle(){}, contains(){return false}},
  addEventListener(){}, appendChild(){}, remove(){}, click(){},
  dataset: {}, style: {}, select(){}, querySelector(){return null},
});
global.document = {getElementById: mk, querySelectorAll: () => [], querySelector: () => null,
  addEventListener(){}, createElement: () => mk('t'), body: {appendChild(){}}};
global.window = {EMOHEALTH:null, EMOHEALTH_TIER:null, EMOHEALTH_UNLOCK:null,
                 EMOHEALTH_ADAPT:null};
global.localStorage = {_d:{}, getItem(k){return this._d[k] ?? null},
  setItem(k, v){this._d[k] = v}, removeItem(k){delete this._d[k]}};
global.atob = x => Buffer.from(x, 'base64').toString('binary');
global.setInterval = () => 0; global.clearInterval = () => {};
global.navigator = {}; global.location = {protocol: 'file:'}; global.confirm = () => false;
global.URL = {createObjectURL: () => 'x', revokeObjectURL(){}};
global.Blob = function(){}; global.FileReader = function(){};
for (const f of ['emohealth-data.js', 'tier-data.js', 'unlock-data.js',
                 'adaptive-data.js', 'net-layout.js'])
  eval(fs.readFileSync(ROOT + '/ui/' + f, 'utf8'));
eval(code);

const T = globalThis.__T, {S, TR} = T;
module.exports = T;

if (require.main === module) {
  console.log('=== 检查 ①：unlockNote 的「已经可以给结果」是否与 facetReady 一致 ===');
  S.resp = {}; TR.order.slice(0, 30).forEach(o => S.resp[o] = 3);
  const bad = [];
  for (let fi = 0; fi < 30; fi++) {
    const note = T.unlockNote(TR.tierRingNodes[0][fi]);
    const claims = note.includes('这个面向已经可以给结果了');
    const real = T.facetReady(fi);
    if (claims !== real) bad.push({facet: TR.facets[fi], own: T.ownCount(fi),
      r: +Math.sqrt(T.netR2(fi)).toFixed(3), note_says_ready: claims, really_ready: real});
  }
  console.log(`  第 1 环答完：${bad.length}/30 个面向「界面说可以给结果」但 facetReady=false`);
  console.log('  readyFacets() 实际 =', T.readyFacets().length);
  if (bad.length) console.log('  例：', JSON.stringify(bad.slice(0, 3)));

  console.log('\n=== 检查 ②：自适应推荐会不会跨环（破坏「每面向恰好 R 题」的平衡） ===');
  const rows = [];
  for (const n of [30, 40, 50, 60, 75, 90, 120, 300]) {
    S.resp = {}; TR.order.slice(0, n).forEach(o => S.resp[o] = 3);
    T.refreshAdapt();
    const list = T.recommend(5);
    const rings = list.map(x => T.tierRingOfOrder(x.o));
    const unlocked = T.deepestUnlockedRing();
    const fc = {}; list.forEach(x => { const f = T.itemByOrder[x.o][1]; fc[f] = (fc[f] || 0) + 1; });
    // 推荐出来的节点必须是可点的（不能是 locked）
    const clickable = list.every(x => T.tierNodeState(T.itemByOrder[x.o][1],
      T.tierRingOfOrder(x.o)) !== "locked");
    rows.push({已答: n, 已答深度: T.deepestAnsweredRing(), 已解锁到环: unlocked,
      推荐环: rings.join(','), 跨环: Math.max(...rings) > unlocked,
      推荐可点: clickable});
  }
  console.table(rows);

  console.log('\n=== 检查 ③：环约束会不会损失信息增益（对比「放开全 300 题」） ===');
  for (const n of [30, 60, 90]) {
    S.resp = {}; TR.order.slice(0, n).forEach(o => S.resp[o] = 3);
    const ctx = T.adaptCtx();
    const lim = T.recRingLimit();
    const free = [], bound = [];
    for (const o of T.D.items.map(i => i[0])) {
      if (o in S.resp) continue;
      const g = T.totalGain(o, ctx);
      free.push(g);
      if (T.tierRingOfOrder(o) <= lim) bound.push(g);
    }
    free.sort((a, b) => b - a); bound.sort((a, b) => b - a);
    const top5 = a => a.slice(0, 5).reduce((s, x) => s + x, 0);
    console.log(`  ${String(n).padStart(3)} 题：候选 ${free.length} → ${bound.length}；`
      + `前 5 增益 ${top5(free).toFixed(3)} → ${top5(bound).toFixed(3)}`
      + `（保留 ${(top5(bound) / top5(free) * 100).toFixed(1)}%）`);
  }
}

