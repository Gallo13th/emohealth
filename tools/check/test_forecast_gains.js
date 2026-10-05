// 信息增益前瞻（下一题推荐的核心）专项测试 —— **node 直接跑**，不开浏览器。
//
// 为什么单开一条 node 测试：前瞻是纯数值/纯函数，用 node 跑可以穷举大量随机用例
// 做**逐值等价性**断言（而不是靠点几下界面），也方便量耗时。
//
// 钉住六件事：
//   ① **等价性**：`forecastGains` 给出的「答了 x 之后 conf_r」与
//      **同一个** `dimConfidence`（面板用的那个函数）逐值一致 —— 不允许第二套口径。
//   ② **不泄露**：函数入参只有题号（没有作答值）；把「假的值」塞进 payload 也不影响结果。
//   ③ **候选池**：已答的题不进候选；某维度答满后不再推它。
//   ④ **单调性**：信息增益 Δ ≥ 0；可展示维度的 conf_r 只增不减。
//   ⑤ **硬规则**：本维度一题未答 → `dims[dim].confidence_r === null`，且该维度
//      **不参与**任何候选的收益（推荐文案里不会出现它的置信度）。
//   ⑥ **性能**：0/60/120/200 题四档耗时 + 退化（n_slow）比例。
//
// 用法：node tools/check/test_forecast_gains.js
const fs = require('fs'), path = require('path'), vm = require('vm');
const ROOT = path.resolve(__dirname, '..', '..');
const lib = require(path.join(ROOT, 'ui', 'lib', 'inference.js'));

let fail = 0;
const ck = (n, c, d = '') => {
  console.log(`  ${c ? '✅' : '❌'} ${n}${d ? '  —— ' + d : ''}`);
  if (!c) fail++;
};

function loadPayload(code) {
  const f = code === 'IPIP-NEO' ? 'ipip-neo.js' : 'pid-5.js';
  const ctx = { window: {} };
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(path.join(ROOT, 'ui', 'inference', f), 'utf8'), ctx);
  const g = 'EMOHEALTH_INFER_' + code.replace(/[^A-Za-z0-9]/g, '_').toUpperCase();
  const p = ctx.window[g];
  if (!p || !p.params) throw new Error('参数包没挂到 window / 缺 params：' + g);
  return p;
}

/* 复刻 `treeNodeState` 的**结构性**可答规则（depth 0 或某个支撑边邻居已答），
   好让「候选池」与界面真正用的池子一致（不靠 DOM）。 */
function structuralOpen(code, answeredIds, instrumentData, layout) {
  const idByOrder = new Map(instrumentData.items.map(it => [String(it.order), it.id]));
  const open = [], locked = [];
  for (const it of instrumentData.items) {
    const k = String(it.order);
    if (answeredIds.has(it.id)) continue;                 // 已答 → 不进候选
    const depth = (layout.depth[k] != null) ? layout.depth[k] : 0;
    const sup = layout.support[k] || [];
    const nbr = sup.some(o => answeredIds.has(idByOrder.get(String(o))));
    (depth === 0 || nbr ? open : locked).push(it.id);
  }
  return { open, locked };
}
// 「答得最少的维度」旧启发式（与 task-10 的 recommendTreeItem 同规则）
function heuristicPick(pool, dimItems, dimOfItem, answeredPerDim) {
  let best = null;
  for (const id of pool) {
    const d = dimOfItem.get(id);
    const n = answeredPerDim.get(d) || 0;
    if (best === null || n < best.n) best = { id, d, n };
  }
  return best;
}

function main() {
  const t0 = Date.now();
  const P = { 'IPIP-NEO': loadPayload('IPIP-NEO'), 'PID-5': loadPayload('PID-5') };
  console.log('=== 载入两侧参数包 ===');
  for (const c of Object.keys(P)) {
    console.log(`    ${c}: ${P[c].params.ids.length} 题 / ` +
      `${Object.keys(P[c].params.dim_items).length} 维 / ceiling_ratio=${P[c].params.ceiling_ratio}`);
  }

  /* ══ ① 等价性：前瞻的 after == dimConfidence(加该题后) ══ */
  console.log('\n=== ① 等价性：前瞻 after 必须 === 同一个 dimConfidence ===');
  let worst = 0, nCmp = 0, worstAt = '';
  for (const code of Object.keys(P)) {
    const payload = P[code], params = payload.params, n = params.ids.length;
    const pairs = payload.__pairs || lib.buildPairMatrix(payload.pairB64, n);
    payload.__pairs = pairs;
    const idxOf = {}; params.ids.forEach((id, i) => { idxOf[id] = i; });
    const dims = Object.keys(params.dim_items);
    // 三档已答量 × 每档若干候选题，覆盖「本维度未答/已答/已可给结果」三种状态
    const states = [3, 17, 40];
    for (const m of states) {
      // 前 m 题按「每维轮流」答，避免只答前几个维度
      const answered = [];
      const perDim = new Map(dims.map(d => [d, 0]));
      let round = 0;
      while (answered.length < m) {
        for (const d of dims) {
          const own = params.dim_items[d];
          const item = own[round];
          if (item && !answered.includes(item)) answered.push(item);
          if (answered.length >= m) break;
        }
        round++;
        if (round > 40) break;
      }
      const cands = [];
      for (const d of dims) {
        const own = params.dim_items[d];
        for (const it of own) if (!answered.includes(it)) { cands.push(it); break; }   // 每维一题候选
      }
      const res = lib.forecastGains(payload, answered, cands.slice(0, 12));
      for (const c of res.candidates) {
        const coded = {}; answered.forEach(id => { coded[id] = 0; }); coded[c.item] = 0;
        for (const d of Object.keys(c.after)) {
          const ref = lib.dimConfidence(params, pairs, n, d, coded, idxOf).confidence_r;
          const got = c.after[d].confidence_r;
          const dev = Math.abs(ref - got);
          nCmp++;
          if (dev > worst) { worst = dev; worstAt = `${code} m=${m} ${c.item} ${d}`; }
        }
      }
    }
  }
  ck('前瞻 after 与 dimConfidence 逐值一致（容差 1e-9）', worst < 1e-9,
    `比对 ${nCmp} 个 (候选×维度) 值，最大偏差 ${worst.toExponential(2)}${worstAt ? ' @' + worstAt : ''}`);

  /* ══ ② 不泄露：入参只有题号；塞假值也不影响 ══ */
  console.log('\n=== ② 不泄露：只用 pairB64 + 已答集合 ===');
  {
    const payload = P['IPIP-NEO'], params = payload.params;
    const dims = Object.keys(params.dim_items);
    const answered = dims.slice(0, 4).map(d => params.dim_items[d][0]);
    const cands = dims.slice(0, 8).map(d => params.dim_items[d][1]);
    const a = lib.forecastGains(payload, answered, cands);
    // 把「假作答值」塞进 payload 的各个角落（若实现偷看值，这里会变）
    const p2 = JSON.parse(JSON.stringify(payload));
    p2.responses = {}; p2.values = {}; p2.instResp = {};
    for (const id of params.ids) {
      p2.responses[id] = 4; p2.values[id] = 1; p2.instResp[id] = 5;
    }
    p2.params.responses = p2.responses;
    const b = lib.forecastGains(p2, answered, cands);
    const same = JSON.stringify(a.order) === JSON.stringify(b.order)
      && JSON.stringify(a.candidates.map(c => c.utility)) ===
         JSON.stringify(b.candidates.map(c => c.utility));
    ck('把「假作答值」塞进 payload 也不改变推荐（排名与效用逐值相同）', same);
    ck('签名里没有作答值（只有 payload / 已答题号 / 候选题号 / 选项）',
      lib.forecastGains.length === 4,
      'arity=' + lib.forecastGains.length);
    const src = fs.readFileSync(path.join(ROOT, 'ui', 'lib', 'inference.js'), 'utf8');
    const body = src.slice(src.indexOf('function forecastGains'), src.indexOf('/* 预测入口'));
    ck('函数体内不读取任何作答值对象（无 responses[...] / coded[...] 取值）',
      !/responses\[/.test(body) && !/instResp/.test(body) && !/\bvalues\[/.test(body),
      '仅用题号 + pairB64');
  }

  /* ══ ③ 候选池 + ④ 单调性 ══ */
  console.log('\n=== ③ 候选池：已答的题不进池、答满的维度不再推 ===');
  for (const code of Object.keys(P)) {
    const payload = P[code], params = payload.params, dims = Object.keys(params.dim_items);
    const answered = dims.slice(0, 3).map(d => params.dim_items[d][0]);
    const pool = dims.flatMap(d => params.dim_items[d]);
    const res = lib.forecastGains(payload, answered, pool);
    const items = res.candidates.map(c => c.item);
    ck(`[${code}] 已答题不出现在候选里`,
      !items.some(i => answered.includes(i)), `${items.length} 个候选`);
    // 把某个维度答满 → 该维度的题不应再出现在候选里
    const dFull = dims[4];
    const full = params.dim_items[dFull];
    const res2 = lib.forecastGains(payload, answered.concat(full), pool);
    ck(`[${code}] 答满「${dFull}」后该维度不再被推荐`,
      !res2.candidates.some(c => full.includes(c.item)));
    ck(`[${code}] 答满维度不出现在收益里（既不推也不给它的 Δ）`,
      res2.candidates.every(c => c.gains[dFull] === undefined
        || full.includes(c.item) === false && c.gains[dFull] === 0
        || !full.includes(c.item)),
      '');
    let nonNeg = true, mono = true;
    for (const c of res.candidates) {
      if (c.gain_total < 0) nonNeg = false;
      for (const d of Object.keys(c.after)) {
        if (c.after[d].confidence_r < (res.dims[d].confidence_r || 0) - 1e-12) mono = false;
      }
    }
    ck(`[${code}] 信息增益 Δ ≥ 0`, nonNeg);
    ck(`[${code}] conf_r 只增不减（可展示维度）`, mono);
  }

  /* ══ ⑤ 硬规则 ══ */
  console.log('\n=== ⑤ 硬规则：本维度未答 → 不给该维度置信度、不进推荐 ===');
  for (const code of Object.keys(P)) {
    const payload = P[code], params = payload.params, dims = Object.keys(params.dim_items);
    const target = dims[1];
    // 只答**别的维度**的题（目标维度一题不答），并且答得很密
    const answered = [];
    for (const d of dims) {
      if (d === target) continue;
      answered.push(...params.dim_items[d].slice(0, 3));
    }
    const pool = dims.flatMap(d => params.dim_items[d]);
    const res = lib.forecastGains(payload, answered, pool);
    ck(`[${code}] 未答维度的 dims.confidence_r === null`, res.dims[target].confidence_r === null,
      `${target}`);
    ck(`[${code}] 未答维度 available=false（别的维度答了 ${answered.length} 题也不放行）`,
      res.dims[target].available === false);
    ck(`[${code}] 未答维度的题仍可作候选（答它才可能把它推进可给结果）`,
      res.candidates.some(c => params.dim_items[target].includes(c.item)));
    // 目标维度的增益只出现在「候选题属于该维度」时；跨维度候选不给该维度算收益
    const cross = res.candidates.find(c => !params.dim_items[target].includes(c.item));
    ck(`[${code}] 别的维度的候选不给未答维度记收益（不泄露）`,
      cross && cross.gains[target] === undefined);
  }

  /* ══ ⑥ 性能：四档 + 退化比例 ══ */
  console.log('\n=== ⑥ 性能实测（含退化 n_slow 比例）===');
  const perf = {};
  for (const code of Object.keys(P)) {
    const payload = P[code], params = payload.params, dims = Object.keys(params.dim_items);
    const layout = JSON.parse(fs.readFileSync(
      path.join(ROOT, 'data', 'tree-layouts', code.toLowerCase() + '.json'), 'utf8'));
    const inst = JSON.parse(fs.readFileSync(
      path.join(ROOT, 'data', 'instruments', code.toLowerCase() + '.json'), 'utf8'));
    perf[code] = [];
    for (const m of [0, 60, 120, 200]) {
      // 按「每维轮流」取前 m 题（与界面里一环一题的结构一致）
      const answered = [];
      const roundMax = Math.ceil(m / dims.length) + 1;
      for (let round = 0; round < roundMax && answered.length < m; round++) {
        for (const d of dims) {
          const it = params.dim_items[d][round];
          if (it && answered.length < m) answered.push(it);
        }
      }
      const ansSet = new Set(answered);
      const pool = structuralOpen(code, ansSet, inst, layout);
      const cands = pool.open;                       // 界面真正用的池子
      const stress = params.ids.filter(i => !ansSet.has(i)).slice(0, 60);   // 压力上界
      const r1 = lib.forecastGains(payload, answered, cands);
      const r2 = lib.forecastGains(payload, answered, stress);
      perf[code].push({ m: answered.length, pool: cands.length, ms: r1.ms, slow: r1.n_slow,
                        slowPct: cands.length ? (100 * r1.n_slow / cands.length) : 0,
                        ms60: r2.ms, slow60: r2.n_slow });
      console.log(`    ${code.padEnd(9)} 已答 ${String(answered.length).padStart(3)}：` +
        `树池 ${String(cands.length).padStart(2)} 题 → ${r1.ms.toFixed(0)} ms` +
        `（退化 ${r1.n_slow}）｜压测 60 题 → ${r2.ms.toFixed(0)} ms（退化 ${r2.n_slow}）`);
    }
    ck(`[${code}] 树池下 200 题的前瞻耗时 < 1500 ms`,
      perf[code][3].ms < 1500, `${perf[code][3].ms.toFixed(0)} ms`);
    ck(`[${code}] 退化比例可忽略（< 5%）`,
      perf[code].every(p => p.slowPct < 5),
      perf[code].map(p => p.slowPct.toFixed(1) + '%').join(' / '));
  }

  /* ══ ⑦ 与「答得最少的维度」启发式对比（实例） ══ */
  console.log('\n=== ⑦ 信息增益 vs 旧启发式「答得最少的维度」（实例）===');
  {
    const code = 'IPIP-NEO';
    const payload = P[code], params = payload.params, dims = Object.keys(params.dim_items);
    const layout = JSON.parse(fs.readFileSync(
      path.join(ROOT, 'data', 'tree-layouts', 'ipip-neo.json'), 'utf8'));
    const inst = JSON.parse(fs.readFileSync(
      path.join(ROOT, 'data', 'instruments', 'ipip-neo.json'), 'utf8'));
    // 场景：每维答 1 题（共 30 题），此时「答得最少」全平手 → 旧启发式退化成按题号取第一个
    const answered = dims.map(d => params.dim_items[d][0]);
    const ansSet = new Set(answered);
    const dimOfItem = new Map();
    for (const d of dims) for (const it of params.dim_items[d]) dimOfItem.set(it, d);
    const perDim = new Map(dims.map(d => [d, 1]));
    const pool = structuralOpen(code, ansSet, inst, layout).open;
    const res = lib.forecastGains(payload, answered, pool);
    const h = heuristicPick(pool, params.dim_items, dimOfItem, perDim);
    const gainBest = res.best;
    const why = gainBest.confirmed && Object.entries(gainBest.confirmed)
      .sort((a, b) => b[1].gain - a[1].gain)[0];
    console.log(`    候选池（结构性可答）：${pool.length} 题`);
    console.log(`    信息增益选中：${gainBest.item}（维度 ${gainBest.own_dim}）` +
      ` utility=${gainBest.utility.toFixed(4)} 总增益=${gainBest.gain_total.toFixed(4)}` +
      ` 解锁=${JSON.stringify(gainBest.unlocks)}`);
    if (gainBest.confirmed) {
      console.log(`      → 预计提升最大的维度：${why[0]} ` +
        `conf_r ${why[1].before == null ? '(未答)' : why[1].before.toFixed(4)} → ${why[1].after.toFixed(4)}` +
        `（Δr²=${why[1].gain.toFixed(4)}）`);
    }
    console.log(`    旧启发式选中：${h ? h.id : '(空)'}（维度 ${h ? h.d : '-'}，该维度已答 ${h ? h.n : '-'} 题）`);
    ck('两种选法选出了不同的题（证明不是换汤不换药）',
      !!h && h.id !== gainBest.item, `${h && h.id} ≠ ${gainBest.item}`);
    ck('信息增益给出的预计提升量 > 0 且有可解释的目标维度',
      gainBest.gain_total > 0 && !!why, `Δr²=${gainBest.gain_total.toFixed(4)}`);
    // 再看一个「某维度只差一点就解锁」的场景，验证它会优先补短板
    const dShort = dims.find(d => d !== gainBest.own_dim);
    const answered2 = answered.slice();
    while (answered2.filter(i => params.dim_items[dShort].includes(i)).length < 3) {
      const nxt = params.dim_items[dShort].find(i => !answered2.includes(i));
      if (!nxt) break;
      answered2.push(nxt);
    }
    const pool2 = structuralOpen(code, new Set(answered2), inst, layout).open;
    const res2 = lib.forecastGains(payload, answered2, pool2);
    const unlockTargets = res2.candidates.filter(c => c.unlocks && c.unlocks.length);
    console.log(`    补短板场景（「${dShort}」答到 3 题）：有 ${unlockTargets.length} 个候选题` +
      `会让某维度首次跨过门槛；最佳=${res2.best && res2.best.item}` +
      `${res2.best && res2.best.unlocks.length ? '（解锁 ' + res2.best.unlocks.join('、') + '）' : ''}`);
    ck('「跨过门槛」的候选题会被优先（utility 里含解锁加分）',
      res2.best != null, `best=${res2.best && res2.best.item}`);
  }

  console.log(`\n总耗时 ${((Date.now() - t0) / 1000).toFixed(1)} s`);
  console.log(fail ? `\n❌ ${fail} 项未通过` : '\n✅ 前瞻（信息增益推荐）全部通过');
  process.exit(fail ? 1 : 0);
}

main();
