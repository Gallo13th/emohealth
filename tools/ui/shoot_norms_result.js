// 给「有常模」的结果页出图（IPIP-NEO 300 题，显示百分位）
const {spawn} = require('child_process');
const os = require('os'), fs = require('fs'), path = require('path');
const ROOT = require('../_root.js').findRoot(__dirname);
const PORT = 9353;
const CHROME = process.env.CHROME ||
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const prof = fs.mkdtempSync(path.join(os.tmpdir(), 'sh3-'));
  const ch = spawn(CHROME, ['--headless=new', '--no-sandbox', '--disable-gpu',
    '--remote-debugging-port=' + PORT, '--user-data-dir=' + prof,
    '--window-size=1280,1200', 'about:blank'], {stdio: 'ignore'});
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
  await S('Page.navigate', {url: 'http://127.0.0.1:8891/emohealth/'});
  await sleep(2800);
  const ev = async x => (await S('Runtime.evaluate',
    {expression: x, returnByValue: true, awaitPromise: true})).result?.result?.value;

  await ev(`document.querySelector('#modes button[data-m="inst"]').click()`);
  await sleep(500);
  await ev(`[...document.querySelectorAll('.instcard')]
    .find(x => x.dataset.inst === 'IPIP-NEO').click()`);
  await sleep(1800);
  // 全答「3」以外的变化值，让百分位有差异；再直接触发计分（不必逐页点 300 题）
  const r = await ev(`(() => {
      const d = INST_NOW;
      if (!d) return {err: '未加载'};
      // 直接写入作答（模拟已完成），再看结果
      d.items.forEach((it, i) => { S.instResp[it.id] = 2 + (i % 4); });
      S.instResult = {rows: instScores(d, S.instResp)};
      renderTop(); renderStage();
      const heads = [...document.querySelectorAll('.insttable thead th')]
        .map(x => x.textContent.trim());
      const first = [...document.querySelectorAll('.insttable tbody tr')]
        .slice(0, 3).map(tr => tr.textContent.replace(/\\s+/g, ' ').trim().slice(0, 56));
      return {heads, first, note: document.querySelector('#stage .note').textContent
        .replace(/\\s+/g, ' ').trim().slice(0, 110)};
    })()`);
  console.log('  表头:', JSON.stringify(r.heads));
  console.log('  首几行:', JSON.stringify(r.first, null, 0));
  console.log('  说明:', r.note);
  await sleep(400);
  const cap = await S('Page.captureScreenshot', {format: 'png', captureBeyondViewport: true});
  fs.writeFileSync(path.join(ROOT, '.shots', 'inst-norms.png'),
    Buffer.from(cap.result.data, 'base64'));
  console.log('  → .shots/inst-norms.png');
  ws.close(); ch.kill(); process.exit(0);
})().catch(e => { console.error('❌', e.message); process.exit(1); });
