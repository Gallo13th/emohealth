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

  ws.close(); ch.kill();
  console.log(fail ? `\n❌ ${fail} 项未通过` : '\n✅ PID-5 常模接入通过');
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error('❌', e.message); process.exit(1); });
