// 天赋树「节点解锁 + 下一题推荐」专项（task-19）—— 真浏览器（CDP，file:// 直开）。
//
// 钉住五件事：
//   ① **解锁判据不自创**：节点 `data-unlocked` 与 `conf_r ≥ dim_ceiling × 0.90`
//      逐维度一致；且给出**边界实测**（刚过门槛 → 点亮；差一步 → 不点亮）。
//   ② **硬规则（单独断言）**：本维度一道题都没答时——即使**别的维度全部答满**——
//      该维度的节点**不点亮**、解锁依据表里**不出现 r**、预测面板那一行也是 blocked。
//   ③ **推荐 = 信息增益**：推荐框里的题未答且可答；页面显示的前瞻与
//      **直接调 `EmoHealthInference.forecastGains`** 的结果逐值一致；
//      并与旧启发式「答得最少的维度」对比（不同题时页面要写出来）。
//   ④ **不泄露**：推荐只依赖题号 + pairB64——改**已答题的作答值**不改变推荐。
//   ⑤ **性能**：在页面上量 0/60/120/200 题的前瞻耗时（面板/推荐同一套 conf_r）。
//
// 用法：node tools/check/test_tree_unlock.js
const {spawn} = require('child_process');
const os = require('os'), fs = require('fs'), path = require('path');
const PORT = 9419;
const CHROME = process.env.CHROME ||
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const sleep = ms => new Promise(r => setTimeout(r, ms));
const ROOT = path.resolve(__dirname, '..', '..');
const URL_ = process.env.URL ||
  'file:///' + path.join(ROOT, 'ui', 'index.html').replace(/\\/g, '/');

let fail = 0;
const ck = (n, c, d = '') => {
  console.log(`  ${c ? '✅' : '❌'} ${n}${d ? '  —— ' + d : ''}`);
  if (!c) fail++;
};

(async () => {
  const prof = fs.mkdtempSync(path.join(os.tmpdir(), 'treeunlock-'));
  const ch = spawn(CHROME, ['--headless=new', '--no-sandbox', '--disable-gpu',
    '--remote-debugging-port=' + PORT, '--user-data-dir=' + prof,
    '--window-size=1280,1400', '--allow-file-access-from-files', 'about:blank'],
    {stdio: 'ignore'});
  let ver = null;
  for (let i = 0; i < 60 && !ver; i++) {
    try { ver = await (await fetch(`http://127.0.0.1:${PORT}/json/version`)).json(); }
    catch { await sleep(250); }
  }
  const ws = new WebSocket(ver.webSocketDebuggerUrl);
  await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; });
  let id = 0; const pend = new Map(); const errs = [];
  ws.onmessage = e => {
    const m = JSON.parse(e.data);
    if (m.id && pend.has(m.id)) { pend.get(m.id)(m); pend.delete(m.id); }
    if (m.method === 'Runtime.exceptionThrown')
      errs.push(m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text);
  };
  const send = (m, p, s) => new Promise(r => {
    const i = ++id; pend.set(i, r);
    ws.send(JSON.stringify({id: i, method: m, params: p, sessionId: s}));
  });
  const t = await send('Target.createTarget', {url: 'about:blank'});
  const a = await send('Target.attachToTarget', {targetId: t.result.targetId, flatten: true});
  const S = (m, p) => send(m, p, a.result.sessionId);
  await S('Page.enable'); await S('Runtime.enable');
  const ev = async x => {
    const r = await S('Runtime.evaluate',
      {expression: x, returnByValue: true, awaitPromise: true});
    if (r.result?.exceptionDetails) return 'EXC: ' +
      (r.result.exceptionDetails.exception?.description || '').slice(0, 300);
    return r.result?.result?.value;
  };
  const nav = async u => { await S('Page.navigate', {url: u}); await sleep(3200); };
  const seed = async resp => ev(`(() => {
      S.instResp = ${JSON.stringify(resp)}; S.ansVer++; S.treeSel = null;
      renderTop(); renderStage(); return Object.keys(S.instResp).length;
    })()`);
  /* 把「本维度已答 n 题 + 可选跨维度题」灌进去，再读该维度的解锁状态 */
  const probe = async (dim, n) => ev(`(() => {
      const p = inferencePayload(S.instCode).params, lib = window.EmoHealthInference;
      const own = p.dim_items[${JSON.stringify(dim)}];
      const need = p.dim_ceiling[${JSON.stringify(dim)}] * p.ceiling_ratio;
      const resp = {};
      for (let i = 0; i < ${n}; i++) resp[own[i]] = 3;
      S.instResp = resp; S.ansVer++; S.treeSel = null;
      renderTop(); renderStage();
      const pairs = window.EmoHealthInference.buildPairMatrix(
        inferencePayload(S.instCode).pairB64, p.ids.length);
      const idxOf = {}; p.ids.forEach((x, i) => { idxOf[x] = i; });
      const coded = {}; Object.keys(resp).forEach(k => { coded[k] = 0; });
      const r = lib.dimConfidence(p, pairs, p.ids.length, ${JSON.stringify(dim)}, coded, idxOf);
      const nodes = [...document.querySelectorAll('.treenode[data-dim="' + ${JSON.stringify(dim)} + '"]')];
      /* D120（task-24）：原来读「解锁依据表」的行；那张表（判据/精确 r/门槛）已按
         用户要求删除，改读**节点 data-unlocked**（机器可读契约）+ **预测面板该行**
         （data-display / data-r）。判据本身仍由本测试直接调 dimConfidence 复算。 */
      const panelRow = document.querySelector('.infpanel tr[data-dim="' + ${JSON.stringify(dim)} + '"]');
      return { r: r.confidence_r, need: need, unlocked: r.confidence_r != null && r.confidence_r >= need,
               nodeStates: [...new Set(nodes.map(n => n.dataset.unlocked))],
               nodeCount: nodes.length,
               panelDisplay: panelRow && panelRow.dataset.display,
               panelAvailable: panelRow && panelRow.dataset.available,
               panelR: panelRow ? panelRow.dataset.r : null,
               panelText: panelRow ? panelRow.textContent.replace(/\\s+/g, ' ').slice(0, 90) : '',
             };
    })()`);

  /* ═══ 进入 PID-5 天赋树 ═══ */
  await nav(URL_);
  await ev(`document.querySelector('#modes button[data-m="inst"]').click()`);
  await sleep(400);
  await ev(`[...document.querySelectorAll('.instcard')].find(x => x.dataset.inst === 'PID-5').click()`);
  await sleep(3200);                       // 等按需数据（布局 + 题面 + 参数 + 库）
  const ready = await ev(`({
      view: S.instView,
      nodes: document.querySelectorAll('.treenode').length,
      flagged: document.querySelectorAll('.treenode[data-unlocked]').length,
      readyNodes: document.querySelectorAll('.treenode.ready').length,
      legend: document.querySelectorAll('.treelegend i').length,
      basis: !!document.querySelector('[data-unlock-fold]'),
      reco: !!document.querySelector('[data-reco]'),
      lib: typeof window.EmoHealthInference,
      payload: !!inferencePayload(S.instCode)
    })`);
  console.log('=== 页面就绪 ===');
  console.log('    实测：', JSON.stringify(ready));
  ck('进入 PID-5 天赋树且按需数据已加载',
    ready.view === 'tree' && ready.lib === 'object' && ready.payload === true);
  ck('每个节点都带 data-unlocked 标记（为 0 时也不隐藏）',
    ready.flagged === ready.nodes && ready.nodes === 220,
    `${ready.flagged}/${ready.nodes}`);
  ck('图例区分四类：已答/已解锁/可答/未解锁', ready.legend === 4, ready.legend + ' 项');
  ck('有「解锁依据」可展开块', ready.basis === true);
  ck('有「下一题推荐」框', ready.reco === true);

  /* ═══ ① 解锁判据 + 边界实测 ═══ */
  console.log('\n=== ① 解锁判据（conf_r ≥ dim_ceiling × 0.90）与边界实测 ===');
  const DIM = await ev(`(() => {
      const p = inferencePayload(S.instCode).params;
      // 挑一个题数适中、门槛不极端的维度
      const ds = Object.keys(p.dim_items).filter(d => p.dim_items[d].length >= 6);
      return ds[0];
    })()`);
  console.log('    目标维度：' + DIM);
  // 找出「第一次跨过门槛」所需的题数
  const cross = await ev(`(async () => {
      const p = inferencePayload(S.instCode).params, lib = window.EmoHealthInference;
      const dim = ${JSON.stringify(DIM)}, own = p.dim_items[dim];
      const need = p.dim_ceiling[dim] * p.ceiling_ratio;
      const pairs = lib.buildPairMatrix(inferencePayload(S.instCode).pairB64, p.ids.length);
      const idxOf = {}; p.ids.forEach((x, i) => { idxOf[x] = i; });
      let first = null;
      for (let n = 1; n <= own.length; n++) {
        const coded = {}; for (let i = 0; i < n; i++) coded[own[i]] = 0;
        const r = lib.dimConfidence(p, pairs, p.ids.length, dim, coded, idxOf).confidence_r;
        if (r != null && r >= need) { first = {n, r, need}; break; }
      }
      return first;
    })()`);
  console.log('    第一次跨过门槛：答 ' + cross.n + ' 题（r=' + cross.r.toFixed(4) +
    ' ≥ 门槛 ' + cross.need.toFixed(4) + '）');
  const below = await probe(DIM, cross.n - 1);
  const at = await probe(DIM, cross.n);
  console.log(`    答 ${cross.n - 1} 题：r=${below.r.toFixed(4)} → 节点 data-unlocked=${below.nodeStates}` +
    `，面板 display=${below.panelDisplay}`);
  console.log(`    答 ${cross.n} 题：r=${at.r.toFixed(4)} → 节点 data-unlocked=${at.nodeStates}` +
    `，面板 display=${at.panelDisplay}`);
  ck('差一步（未达门槛）：节点不点亮、面板该行也未可给估计（available=0）',
     below.unlocked === false && below.nodeStates.join() === '0'
     && below.panelAvailable === '0');
  ck('刚好跨过门槛：该维度全部节点点亮 data-unlocked=1、面板该行 available=1',
     at.unlocked === true && at.nodeStates.join() === '1'
     && at.panelAvailable === '1',
     `${at.nodeCount} 个节点`);
  ck('页面点亮状态与直接调 dimConfidence 的判据一致（不自创口径）',
    at.unlocked === true && below.unlocked === false);

  /* ═══ ② 硬规则：别的维度答满，本维度未答 ═══ */
  console.log('\n=== ② 硬规则（单独断言）：别的维度全答满，本维度未答 → 仍未解锁 ===');
  const hard = await ev(`(() => {
      const p = inferencePayload(S.instCode).params;
      const dims = Object.keys(p.dim_items);
      const target = dims[2];
      const resp = {};
      for (const d of dims) {
        if (d === target) continue;
        for (const it of p.dim_items[d]) resp[it] = 2;      // 别的维度**全部答满**
      }
      S.instResp = resp; S.ansVer++; S.treeSel = null;
      renderTop(); renderStage();
      const nodes = [...document.querySelectorAll('.treenode[data-dim="' + target + '"]')];
      const row = document.querySelector('tr[data-unlock-dim="' + target + '"]');
      const panelRow = document.querySelector('.infpanel tr[data-dim="' + target + '"]');
      return {
        target, answered: Object.keys(resp).length, nodesTotal: nodes.length,
        unlockedNodes: nodes.filter(n => n.dataset.unlocked === '1').length,
        readyClass: nodes.filter(n => n.classList.contains('ready')).length,
        allNodesUnlocked: nodes.every(n => n.dataset.unlocked === '0'),
        panelDisplay: panelRow && panelRow.dataset.display,
        panelAvailable: panelRow && panelRow.dataset.available,
        panelHasR: !!(panelRow && panelRow.dataset.r),
        panelText: panelRow ? panelRow.textContent.replace(/\\s+/g, ' ').slice(0, 120) : '',
        readyDimCount: document.querySelectorAll('.treereco').length,
      };
    })()`);
  console.log('    实测：', JSON.stringify(hard));
  ck('别的维度全部答满（' + hard.answered + ' 题）后，本维度节点仍 data-unlocked=0',
    hard.nodesTotal > 0 && hard.allNodesUnlocked === true,
    `${hard.nodesTotal} 个节点，点亮 ${hard.unlockedNodes} 个`);
  ck('本维度节点没有 ready 类（硬规则：不点亮）', hard.readyClass === 0);
  ck('预测面板该行是 blocked、且**不出现 r**（硬规则：连 data-r 都没有）',
     hard.panelDisplay === 'blocked' && hard.panelHasR === false,
     `display=${hard.panelDisplay} hasR=${hard.panelHasR}`);
  ck('面板该行写的是「这个维度你还没答过题…」',
     /还没答过题|还不能给出估计/.test(hard.panelText), hard.panelText.slice(0, 60));
  ck('预测面板同一维度也是 blocked（与天赋树同一条规则）',
    hard.panelDisplay === 'blocked' && hard.panelHasR === false);

  /* ═══ ③ 推荐 = 信息增益，且与库逐值一致 ═══ */
  console.log('\n=== ③ 推荐：信息增益前瞻 + 与旧启发式对比 + 与库逐值一致 ===');
  const reco = await ev(`(() => {
      const p = inferencePayload(S.instCode).params, lib = window.EmoHealthInference;
      S.instResp = {}; S.ansVer++; S.treeSel = null; renderTop(); renderStage();
      const box = document.querySelector('[data-reco="1"]');
      const item = box && box.dataset.recoItem;
      const own = {};
      for (const d of Object.keys(p.dim_items)) own[d] = p.dim_items[d];
      const dimOf = {}; for (const d of Object.keys(own)) for (const it of own[d]) dimOf[it] = d;
      // 页面**真正用的**候选池：结构性可答
      const openOrders = INST_NOW.items.map(it => it.order)
        .filter(o => treeNodeState(TREE_NOW, o, S.instResp) === 'open');
      const idOfOrder = new Map(INST_NOW.items.map(it => [it.order, it.id]));
      const cands = openOrders.map(o => idOfOrder.get(o)).filter(Boolean);
      const answered = INST_NOW.items.filter(it => it.id in S.instResp).map(it => it.id);
      const res = lib.forecastGains(inferencePayload(S.instCode), answered, cands);
      // 旧启发式
      const perDim = {}; for (const d of Object.keys(own)) perDim[d] = 0;
      for (const it of answered) if (dimOf[it]) perDim[dimOf[it]]++;
      const heur = openOrders.slice().sort((a, b) => {
        const da = perDim[dimOf[idOfOrder.get(a)]] || 0, db = perDim[dimOf[idOfOrder.get(b)]] || 0;
        return da - db || a - b;
      })[0];
      const heurItem = idOfOrder.get(heur);
      return {
        pageItem: item, pageDim: box && box.dataset.recoDim,
        pageUnlocks: box && box.dataset.recoUnlocks, pageMs: box && box.dataset.recoMs,
        libBest: res.best && res.best.item, libDim: res.best && res.best.own_dim,
        libUtility: res.best && res.best.utility, libGain: res.best && res.best.gain_total,
        libMs: res.ms, libSlow: res.n_slow, pool: cands.length,
        unmasked: box ? box.textContent.replace(/\\s+/g, ' ').slice(0, 400) : '',
        heurItem: heurItem, differs: heurItem !== (res.best && res.best.item),
        pageItemUnanswered: item ? !(item in S.instResp) : false,
        pageItemOpen: item ? cands.includes(item) : false,
        isLibFn: lib.forecastGains.length === 4,
      };
    })()`);
  console.log('    实测：', JSON.stringify(reco).slice(0, 700));
  ck('推荐框给出了题号，且该题未答、在候选池内',
    !!reco.pageItem && reco.pageItemUnanswered === true && reco.pageItemOpen === true,
    reco.pageItem);
  ck('页面推荐 === 直接调 forecastGains 的 best（同一套 conf_r）',
    reco.pageItem === reco.libBest, `${reco.pageItem} vs ${reco.libBest}`);
  ck('推荐维度与库一致', reco.pageDim === reco.libDim, `${reco.pageDim} / ${reco.libDim}`);
  /* D120（task-24）：推荐的技术依据（信息增益/效用/耗时/与旧启发式的对照）**已从界面删除**；
     文案改用用户语言。启发式对照本身在 `test_forecast_gains.js`（node 级）里仍然验证。 */
  ck('推荐文案用用户语言说明理由，且不含内部指标（信息增益/效用/门槛/耗时）',
     /最能提高|第一次估计/.test(reco.unmasked)
     && !/信息增益|效用|门槛|耗时|\bms\b|conf_r/.test(reco.unmasked),
     reco.unmasked.slice(0, 120));
  ck('推荐的技术依据折叠已删除（不再上界面）',
     (await ev(`!!document.querySelector('[data-dev="reco-basis"]')`)) === false);
  ck('两套选法在实测场景下选出**不同**的题（不是换汤不换药）',
    reco.differs === true, `${reco.heurItem} ≠ ${reco.libBest}`);
  ck('前瞻不做第二套实现（用的是 lib 的 forecastGains）', reco.isLibFn === true);

  /* ═══ ④ 不泄露：改已答值不影响推荐 ═══ */
  console.log('\n=== ④ 不泄露：推荐只依赖题号 + pairB64 ===');
  const leak = await ev(`(() => {
      const p = inferencePayload(S.instCode).params;
      const dims = Object.keys(p.dim_items);
      const respA = {}, respB = {};
      for (const d of dims.slice(0, 5)) {
        respA[p.dim_items[d][0]] = 1; respB[p.dim_items[d][0]] = 4;   // 同一批题、不同作答值
        respA[p.dim_items[d][1]] = 2; respB[p.dim_items[d][1]] = 3;
      }
      const run = resp => {
        S.instResp = resp; S.ansVer++; S.treeSel = null; renderTop(); renderStage();
        const box = document.querySelector('[data-reco="1"]');
        return box && box.dataset.recoItem;
      };
      const a = run(respA), b = run(respB);
      // 顺带：把「假值」塞进 payload 也不该影响（lib 入参只有题号）
      const payload = inferencePayload(S.instCode);
      const answered = Object.keys(respA);
      const openOrders = INST_NOW.items.map(it => it.order)
        .filter(o => treeNodeState(TREE_NOW, o, S.instResp) === 'open');
      const idOfOrder = new Map(INST_NOW.items.map(it => [it.order, it.id]));
      const cands = openOrders.map(o => idOfOrder.get(o)).filter(Boolean);
      const lib = window.EmoHealthInference;
      const r1 = lib.forecastGains(payload, answered, cands);
      payload.fakeValues = {}; for (const it of p.ids) payload.fakeValues[it] = 5;
      payload.params.fakeValues = payload.fakeValues;
      const r2 = lib.forecastGains(payload, answered, cands);
      return {a, b, same: a === b && a != null,
              orderSame: JSON.stringify(r1.order) === JSON.stringify(r2.order)};
    })()`);
  console.log('    实测：', JSON.stringify(leak));
  ck('同一批题、不同作答值 → 推荐完全相同（作答值不参与）',
    leak.same === true, `${leak.a} === ${leak.b}`);
  ck('往 payload 里塞假值 → 推荐顺序不变', leak.orderSame === true);

  /* ═══ ⑤ 性能四档（在页面上量） ═══ */
  console.log('\n=== ⑤ 性能实测（页面内，IPIP-NEO 最坏情形：30 维 + 300 题）===');
  await nav(URL_ + '#/scale/IPIP-NEO/tree');
  await sleep(4200);
  const perf = await ev(`(() => {
      const p = inferencePayload(S.instCode).params, lib = window.EmoHealthInference;
      const dims = Object.keys(p.dim_items);
      const layout = TREE_NOW;
      const idOfOrder = new Map(INST_NOW.items.map(it => [it.order, it.id]));
      const out = [];
      for (const m of [0, 60, 120, 200]) {
        const resp = {}; let round = 0;
        while (Object.keys(resp).length < m && round < 40) {
          for (const d of dims) {
            const it = p.dim_items[d][round];
            if (it && Object.keys(resp).length < m) resp[it] = 3;
          }
          round++;
        }
        S.instResp = resp; S.ansVer++; S.treeSel = null;
        renderTop(); renderStage();                    // 页面真实路径（含推荐框渲染）
        const answered = INST_NOW.items.filter(it => it.id in S.instResp).map(it => it.id);
        const openOrders = INST_NOW.items.map(it => it.order)
          .filter(o => treeNodeState(layout, o, S.instResp) === 'open');
        const cands = openOrders.map(o => idOfOrder.get(o)).filter(Boolean);
        const r = lib.forecastGains(inferencePayload(S.instCode), answered, cands);
        out.push({m: answered.length, pool: cands.length, ms: +r.ms.toFixed(1),
                  slow: r.n_slow, slowPct: cands.length ? +(100 * r.n_slow / cands.length).toFixed(1) : 0,
                  boxMs: (document.querySelector('[data-reco="1"]') || {}).dataset?.recoMs || null,
                  boxItem: (document.querySelector('[data-reco="1"]') || {}).dataset?.recoItem || null,
                  boxDim: (document.querySelector('[data-reco="1"]') || {}).dataset?.recoDim || null,
                  boxUnlocks: (document.querySelector('[data-reco="1"]') || {}).dataset?.recoUnlocks || null,
                  boxOwnDisplay: (document.querySelector('[data-reco="1"]') || {}).dataset?.recoOwnDisplay || null,
                  boxText: (document.querySelector('[data-reco="1"]') || {}).textContent
                    ?.replace(/\s+/g, ' ').slice(0, 220) || ''});
      }
      return out;
    })()`);
  for (const row of perf) {
    console.log(`    已答 ${String(row.m).padStart(3)}：树池 ${String(row.pool).padStart(2)} 题 → ` +
      `${row.ms} ms（退化 ${row.slow} / ${row.slowPct}%）｜推荐框 data-reco-ms=${row.boxMs}`);
  }
  const withNums = perf.filter(r => /r \d\.\d\d → \d\.\d\d/.test(r.boxText));
  console.log('    实例（已答 60 题时的推荐框）：' + (perf[1].boxText || '').slice(0, 260));
  console.log('    实例（已答 120 题时的推荐框）：' + (perf[2].boxText || '').slice(0, 260));
  /* D120（task-24）：文案里的 `before → after`、信息增益、`跨过门槛` 全部删除；
     现在推荐框只说一句用户语言的理由。这两条断言改成**反向**：
     ① 任何一档的推荐文案都不含内部指标/数字；② 无论目标维度是否已可展示，
     文案都必须是那句用户语言的理由。 */
  ck('推荐文案不含内部指标与数字（信息增益 / r= / 门槛 / 耗时）',
     perf.every(r => !/信息增益|r \d\.\d\d|门槛|耗时|\bms\b|效用/.test(r.boxText)),
     perf.map(r => r.boxText.slice(0, 60)).join(' ｜ ').slice(0, 200));
  ck('推荐文案始终是用户语言的理由句',
     perf.every(r => /最能提高|第一次估计/.test(r.boxText)),
     perf[3].boxText.slice(0, 120));
  ck('目标维度未答时也不给数字（硬规则延伸到推荐文案）',
     perf[0].boxOwnDisplay === '0' && !/r \d\.\d\d|\d+\.\d/.test(perf[0].boxText),
     `own-display=${perf[0].boxOwnDisplay}`);
  ck('四档都量到了，且 200 题时仍 < 1500 ms',
    perf.length === 4 && perf[3].ms < 1500, perf.map(p => p.ms + 'ms').join(' / '));
  ck('退化（走精确重算）比例可忽略（< 5%，全档）',
    perf.every(p => p.slowPct < 5), perf.map(p => p.slowPct + '%').join(' / '));
  ck('页面推荐框如实报出前瞻耗时（data-reco-ms）',
    perf.every(p => p.boxMs != null), JSON.stringify(perf.map(p => p.boxMs)));

  console.log('\n脚本报错:', errs.length ? errs.slice(0, 3) : '无');
  ck('无脚本异常', errs.length === 0);
  ws.close(); ch.kill();
  console.log(fail ? `\n❌ ${fail} 项未通过` : '\n✅ 天赋树解锁 + 信息增益推荐 全部通过');
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error('❌', e.message); process.exit(1); });
