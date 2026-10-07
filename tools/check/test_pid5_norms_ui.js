// 验证 PID-5 的条件常模在界面上真能算出百分位（不是「—」）
const {spawn} = require('child_process');
const os = require('os'), fs = require('fs'), path = require('path');
const PORT = 9391;
const CHROME = process.env.CHROME ||
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const sleep = ms => new Promise(r => setTimeout(r, ms));
const ROOT = 'C:\\Codes\\emohealth-20260930-full\\emohealth';

let fail = 0;
const ck = (n, c, d = '') => {
  console.log(`  ${c ? '✅' : '❌'} ${n}${d ? '  —— ' + d : ''}`);
  if (!c) fail++;
};

(async () => {
  const toUrl = p => 'file:///' + p.replace(/\\/g, '/');
  const url = toUrl(path.join(ROOT, 'ui', 'index.html'));
  const prof = fs.mkdtempSync(path.join(os.tmpdir(), 'nz-'));
  const ch = spawn(CHROME, ['--headless=new', '--no-sandbox', '--disable-gpu',
    '--remote-debugging-port=' + PORT, '--user-data-dir=' + prof,
    '--window-size=1280,1100', '--allow-file-access-from-files', 'about:blank'],
    {stdio: 'ignore'});
  let ver = null;
  for (let i = 0; i < 60 && !ver; i++) {
    try { ver = await (await fetch(`http://127.0.0.1:${PORT}/json/version`)).json(); }
    catch { await sleep(250); }
  }
  const ws = new WebSocket(ver.webSocketDebuggerUrl);
  await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; });
  let id = 0; const pend = new Map();
  ws.onmessage = e => { const m = JSON.parse(e.data);
    if (m.id && pend.has(m.id)) { pend.get(m.id)(m); pend.delete(m.id); } };
  const send = (m, p, s) => new Promise(r => { const i = ++id; pend.set(i, r);
    ws.send(JSON.stringify({id: i, method: m, params: p, sessionId: s})); });
  const t = await send('Target.createTarget', {url: 'about:blank'});
  const a = await send('Target.attachToTarget', {targetId: t.result.targetId, flatten: true});
  const S = (m, p) => send(m, p, a.result.sessionId);
  await S('Page.enable'); await S('Runtime.enable');
  await S('Page.navigate', {url: url + '#/scale/PID-5/classic'});
  await sleep(3200);
  const ev = async x => {
    const r = await S('Runtime.evaluate',
      {expression: x, returnByValue: true, awaitPromise: true});
    if (r.result?.exceptionDetails) return 'EXC: ' +
      (r.result.exceptionDetails.exception?.message || '').slice(0, 160);
    return r.result?.result?.value;
  };

  const info = await ev(`(async () => {
      const d = INST_NOW;
      if (!d) return {err: '量表未加载'};
      const nrm = d.norms || {};
      // 直接调界面用的换算函数，验证条件常模能被查到
      const rows = [
        ['Anhedonia', 0], ['Anhedonia', 1.5], ['Anhedonia', 3],
        ['Withdrawal', 1.0], ['Negative Affect', 2.0]
      ].map(([n, v]) => {
        const det = instPercentileDetail(d, n, v);
        return {n, v, pctl: det ? det.pctl : null, T: det ? det.T : null};
      });
      return {hasScales: !!nrm.scales, cells: (nrm.cells || []).length,
              n: nrm.n, rows,
              status: (d.norms_status || {}).note?.slice(0, 60)};
    })()`);
  console.log('  常模结构:', JSON.stringify({hasScales: info.hasScales,
    cells: info.cells, n: info.n}));
  ck('PID-5 量表包带条件常模', info.hasScales === true,
     `${info.cells} 个分层，n=${info.n}`);
  const okRows = (info.rows || []).filter(r => r.pctl != null);
  ck('各维度都能算出百分位（不是「—」）', okRows.length === (info.rows || []).length,
     JSON.stringify(info.rows));
  ck('百分位随原始分单调（0 低、3 高）',
     info.rows[0].pctl < info.rows[1].pctl && info.rows[1].pctl < info.rows[2].pctl,
     `${info.rows[0].pctl} < ${info.rows[1].pctl} < ${info.rows[2].pctl}`);
  ck('同时给出 T 分', okRows.every(r => r.T != null),
     okRows.map(r => r.T).join(', '));
  console.log('  常模说明:', info.status);

  /* ══════════ task-39：性别 × 年龄分层参数真的生效 ══════════ */
  console.log('\n=== 分层参数（性别 × 年龄 → 条件常模的 cell）===');
  const scan = await ev(`(() => {
      const nrm = INST_NOW.norms, cells = nrm.cells.slice(), out = [];
      for (const [sid, sc] of Object.entries(nrm.scales)) {
        const name = (nrm.scale_names || {})[sid] || sid;
        const keys = Object.keys(sc.cells[cells[0]] || {}).map(Number).sort((a, b) => a - b);
        for (const raw of keys) {
          const vals = cells.map(c => {
            const d = instPercentileDetail(INST_NOW, name, raw, c);
            return d ? d.pctl : null;
          });
          for (let i = 0; i < cells.length; i++) for (let j = i + 1; j < cells.length; j++) {
            if (vals[i] == null || vals[j] == null) continue;
            const cross50 = (vals[i] < 50) !== (vals[j] < 50);
            const cross70 = (vals[i] < 70) !== (vals[j] < 70);
            if (cross50 || cross70) out.push({sid, name, raw, c1: cells[i], v1: vals[i],
              c2: cells[j], v2: vals[j], span: Math.abs(vals[i] - vals[j]),
              cross: cross50 ? 50 : 70});
          }
        }
      }
      out.sort((x, y) => (y.cross === 70 ? 1 : 0) - (x.cross === 70 ? 1 : 0) || y.span - x.span);
      return {n: out.length, top: out.slice(0, 4)}; })()`);
  console.log('  换分层会跨过 50/70 分档线的组合数:', scan && scan.n);
  (scan && scan.top || []).forEach(x => console.log('    ',
    `${x.name} raw=${x.raw}: ${x.c1}=${x.v1}%ile vs ${x.c2}=${x.v2}%ile（跨 ${x.cross} 档，差 ${x.span}pp）`));
  ck('存在「同一原始分、换分层就跨过 50/70 分档线」的组合（这就是加输入的理由）',
     !!scan && scan.n > 0, String(scan && scan.n));

  const ex = (scan && scan.top || []).find(x => x.cross === 70) || (scan && scan.top || [])[0];
  if (ex) {
    /* 与 data/norms/pid-5.json 的表值**逐位对比**（查表值，不是插值猜） */
    const NORMS = JSON.parse(fs.readFileSync(
      path.join(ROOT, 'data/norms/pid-5.json'), 'utf8'));
    const fileP = c => {
      const tbl = NORMS.scales[ex.sid].cells[c];
      const row = tbl[String(ex.raw)] || tbl[ex.raw];
      return row ? Math.round(row.pctl) : null;
    };
    ck('① 同一 raw 换分层：百分位真的变了，且**等于 data/norms/pid-5.json 的表值**',
       fileP(ex.c1) === ex.v1 && fileP(ex.c2) === ex.v2 && ex.v1 !== ex.v2,
       JSON.stringify({[ex.c1]: ex.v1, [ex.c2]: ex.v2, file: {[ex.c1]: fileP(ex.c1), [ex.c2]: fileP(ex.c2)}}));
    ck('① 该实例确实跨过 70 分档线（换个性别年龄就从「一般」变「偏高」）',
       ex.cross === 70 && Math.abs(ex.v1 - ex.v2) >= 20,
       `${ex.v1} vs ${ex.v2}（差 ${ex.span}pp）`);
    const tBoth = await ev(`(() => {
        const a = instPercentileDetail(INST_NOW, ${JSON.stringify(ex.name)}, ${ex.raw}, ${JSON.stringify(ex.c1)});
        const b = instPercentileDetail(INST_NOW, ${JSON.stringify(ex.name)}, ${ex.raw}, ${JSON.stringify(ex.c2)});
        return {T1: a.T, T2: b.T, cell1: a.cell, cell2: b.cell,
          r1: a.cell_reason, r2: a.cell_reason}; })()`);
    ck('① T 分也随分层变，`cell`/`cell_reason=user` 如实报出',
       tBoth.T1 !== tBoth.T2 && tBoth.cell1 === ex.c1 && tBoth.cell2 === ex.c2
       && tBoth.r1 === 'user' && tBoth.r2 === 'user', JSON.stringify(tBoth));
  }

  const states = await ev(`(() => {
      const name = INST_NOW.norms.scale_names[Object.keys(INST_NOW.norms.scales)[0]];
      S.normStratum = {sex: "", age: ""};
      const a = instPercentileDetail(INST_NOW, name, 1.1, stratumRequestedCell());
      const Ra = instReport(INST_NOW, catalogEntry(S.instCode));
      S.normStratum = {sex: "f", age: "lt18"};
      const b = instPercentileDetail(INST_NOW, name, 1.1, stratumRequestedCell());
      const Rb = instReport(INST_NOW, catalogEntry(S.instCode));
      S.normStratum = {sex: "", age: ""};
      return {unfilled: {req: null, cell: a.cell, reason: a.cell_reason,
          isDefault: a.cell_is_default, note: (Ra.norm_stratum || {}).note},
        under18: {req: stratumUserWhy(), cell: b.cell, reason: b.cell_reason,
          requested: b.cell_requested, fallback: b.cell_fallback,
          note: (Rb.norm_stratum || {}).note}}; })()`);
  console.log('  未填:', JSON.stringify(states.unfilled));
  console.log('  <18 :', JSON.stringify(states.under18));
  ck('② 不填 → 用 overall（cell_reason=default）且导出写明「默认总体层」',
     states.unfilled.cell === 'overall' && states.unfilled.reason === 'default'
     && states.unfilled.isDefault === true && /默认总体层/.test(states.unfilled.note || ''),
     JSON.stringify(states.unfilled));
  ck('③ 年龄 <18 → 回退 overall 且说明「数据源没有任何 18 岁以下分层」',
     states.under18.cell === 'overall' && states.under18.reason === 'fallback'
     && states.under18.requested === 'f [0,18)' && states.under18.fallback === true
     && /18 岁以下/.test(states.under18.note || ''), JSON.stringify(states.under18));

  /* ④ 不影响别的量表：IPIP-NEO 有无填写完全一致；PID-5 才有面板 */
  await S('Page.navigate', {url: url + '#/scale/IPIP-NEO/classic'});
  await sleep(3000);
  const other = await ev(`(async () => {
      for (let i = 0; i < 90; i++) {
        if (INST_NOW && INST_NOW.norms && INST_NOW.norms.facets) break;
        await new Promise(r => setTimeout(r, 150));
      }
      const name = (INST_NOW.norms.facet_names || {})[Object.keys(INST_NOW.norms.facets)[0]];
      S.normStratum = {sex: "", age: ""};
      const a = instPercentileDetail(INST_NOW, name, 3.0, stratumRequestedCell());
      S.normStratum = {sex: "m", age: "35-49"};
      const b = instPercentileDetail(INST_NOW, name, 3.0, stratumRequestedCell());
      const panel = stratumPanelHtml(INST_NOW);
      S.normStratum = {sex: "", age: ""};
      return {a: a && a.pctl, b: b && b.pctl, aT: a && a.T, bT: b && b.T,
        panel: panel, name: name}; })()`);
  ck('④ IPIP-NEO：填与不填的百分位/T **完全一致**（本参数只对 PID-5 有意义）',
     other.a != null && other.a === other.b && other.aT === other.bT,
     JSON.stringify({unfilled: other.a, filled: other.b}));
  ck('④ IPIP-NEO 页面**不出现**分层面板（没有条件常模就不问性别年龄）',
     other.panel === '', JSON.stringify(String(other.panel).slice(0, 40)));

  /* ⑤ 界面：面板出现 + 切分层结果真的变 + 可清除 + 导出只写分层码 */
  await S('Page.navigate', {url: url + '#/scale/PID-5/classic'});
  await sleep(3000);
  const ui = await ev(`(async () => {
      for (let i = 0; i < 90; i++) {
        if (INST_NOW && INST_NOW.norms && INST_NOW.norms.scales) break;
        await new Promise(r => setTimeout(r, 150));
      }
      clearStratum(); renderTop(); renderStage();
      const hasClear = !!document.querySelector('[data-stratum-clear]');
      INST_NOW.items.forEach(it => { S.instResp[it.id] = 1; });
      S.ansVer++;
      S.instResult = {rows: instScores(INST_NOW, S.instResp)};
      renderTop(); renderStage();
      const pageHasPanel = !!document.querySelector('[data-stratum-panel]');
      const tableText = () => {
        const tb = document.querySelector('.insttable tbody');
        return tb ? tb.textContent.replace(/\\s+/g, ' ').trim().slice(0, 400) : '';
      };
      const before = tableText();
      /* ⚠️ 每次改值前必须**重新查询**节点：重渲染会换掉 DOM，旧节点上的事件不会冒泡到 document */
      const selTo = (sel, v) => { const s = document.querySelector(sel);
        s.value = v; s.dispatchEvent(new Event('change', {bubbles: true})); };
      selTo('[data-stratum="sex"]', 'm');
      selTo('[data-stratum="age"]', '35-49');
      const filled = tableText();
      const nowTxt = (document.querySelector('[data-stratum-panel] .stnow') || {}).textContent || '';
      const lsSaved = (() => { try { return localStorage.getItem(STRATUM_STORE); } catch (e) { return null; } })();
      document.querySelector('[data-stratum-clear]')
        .dispatchEvent(new MouseEvent('click', {bubbles: true}));
      const afterClear = {sex: stratumState().sex, age: stratumState().age,
        ls: (() => { try { return localStorage.getItem(STRATUM_STORE); } catch (e) { return 'err'; } })()};
      return {pageHasPanel, hasClear, before, filled, nowTxt, lsSaved, afterClear}; })()`);
  console.log('  界面实测:', JSON.stringify({panel: ui.pageHasPanel, now: ui.nowTxt,
    before: String(ui.before).slice(0, 50), filled: String(ui.filled).slice(0, 50)}));
  ck('⑤ PID-5 作答页/结果页都有分层面板（性别+年龄+清除），默认「不填」',
     ui.pageHasPanel === true && ui.hasClear === true,
     JSON.stringify({panel: ui.pageHasPanel, clear: ui.hasClear}));
  ck('⑤ 面板显示**当前实际用的分层**（填了=你填写的）',
     /你填写的分层 m \[35,50\)/.test(ui.nowTxt || ''), String(ui.nowTxt).slice(0, 80));
  ck('⑤ 切换分层后结果表的分数/百分位**真的变了**',
     typeof ui.before === 'string' && ui.before.length > 20 && ui.before !== ui.filled,
     JSON.stringify({before: String(ui.before).slice(0, 44), filled: String(ui.filled).slice(0, 44)}));
  ck('⑤ 选择被持久化到**独立的** localStorage 键（不是作答存档）',
     !!ui.lsSaved && /"sex":"m"/.test(ui.lsSaved) && /"age":"35-49"/.test(ui.lsSaved),
     String(ui.lsSaved).slice(0, 70));
  ck('⑤ 「清除」真的清空（内存 + localStorage 都不残留）',
     ui.afterClear && ui.afterClear.sex === '' && ui.afterClear.age === ''
     && !ui.afterClear.ls, JSON.stringify(ui.afterClear));

  const priv = await ev(`(() => {
      INST_NOW.items.forEach((it, i) => { S.instResp[it.id] = i % 4; });
      S.ansVer++;
      S.instResult = {rows: instScores(INST_NOW, S.instResp)};
      S.normStratum = {sex: "f", age: "35-49"};
      const cap = [], orig = window.download;
      window.download = (n, t) => { cap.push({n: n, t: t}); };
      try {
        instExportMD(INST_NOW, catalogEntry(S.instCode));
        instExportJSON(INST_NOW, catalogEntry(S.instCode));
      } finally { window.download = orig; }
      const mdx = (cap.find(x => /\\.md$/.test(x.n)) || {}).t || '';
      const jsx = (cap.find(x => /\\.json$/.test(x.n)) || {}).t || '';
      const j = jsx ? JSON.parse(jsx) : {};
      S.normStratum = {sex: "", age: ""};
      return {mdHasCell: /f \\[35,50\\)/.test(mdx), mdSaysYours: /你填写的分层/.test(mdx),
        mdNoPlain: !/(女性|男性|35–49 岁|35-49 岁)/.test(mdx),
        mdUsesOverall: /默认总体层/.test(mdx),
        stratum: j.norm_stratum || null, jsExplains: /只用于选择条件常模的分层/.test(jsx),
        respClean: !Object.values(S.instResp).some(v => typeof v !== 'number')}; })()`);
  console.log('  导出实测:', JSON.stringify(priv).slice(0, 300));
  ck('⑤ 导出只写**分层码** `f [35,50)`、说「你填写的分层」，不写「女性/35–49 岁」',
     priv.mdHasCell === true && priv.mdSaysYours === true && priv.mdNoPlain === true
     && priv.mdUsesOverall === false, JSON.stringify({cell: priv.mdHasCell, noPlain: priv.mdNoPlain}));
  ck('⑤ 存档 JSON 的 `norm_stratum` 是**独立字段**（used_cell/reason + 用途说明）',
     priv.stratum && priv.stratum.used_cell === 'f [35,50)'
     && priv.stratum.reason === 'user' && priv.jsExplains === true,
     JSON.stringify(priv.stratum));
  ck('⑤ 性别年龄**没有**混进作答数据（instResp 里只有数字）', priv.respClean === true);

  ws.close(); ch.kill();
  console.log(fail ? `\n❌ ${fail} 项未通过` : '\n✅ PID-5 常模接入 + 分层参数通过');
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error('❌', e.message); process.exit(1); });
