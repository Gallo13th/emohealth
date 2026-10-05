// 给 Mania（每题独立选项：5 组 × 5 句陈述）出图
const {spawn} = require('child_process');
const os = require('os'), fs = require('fs'), path = require('path');
const ROOT = require('../_root.js').findRoot(__dirname);
const PORT = 9351;
const CHROME = process.env.CHROME ||
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const prof = fs.mkdtempSync(path.join(os.tmpdir(), 'sh2-'));
  const ch = spawn(CHROME, ['--headless=new', '--no-sandbox', '--disable-gpu',
    '--remote-debugging-port=' + PORT, '--user-data-dir=' + prof,
    '--window-size=1280,1100', 'about:blank'], {stdio: 'ignore'});
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
  await sleep(2500);
  const ev = async x => (await S('Runtime.evaluate',
    {expression: x, returnByValue: true, awaitPromise: true})).result?.result?.value;

  await ev(`document.querySelector('#modes button[data-m="inst"]').click()`);
  await sleep(500);
  await ev(`[...document.querySelectorAll('.instcard')]
    .find(x => x.dataset.inst === 'DSM5TR-L2-Mania').click()`);
  await sleep(1300);
  // 选两组看看选中态
  await ev(`(() => { const its = document.querySelectorAll('.institem');
      [0,2].forEach(i => { const b = its[i] && its[i].querySelectorAll('.opt')[2];
        if (b) b.click(); }); return 1; })()`);
  await sleep(400);
  const r = await S('Page.captureScreenshot', {format: 'png', captureBeyondViewport: true});
  fs.mkdirSync(path.join(ROOT, '.shots'), {recursive: true});
  fs.writeFileSync(path.join(ROOT, '.shots', 'inst-mania.png'),
    Buffer.from(r.result.data, 'base64'));
  console.log('  → .shots/inst-mania.png');
  ws.close(); ch.kill(); process.exit(0);
})().catch(e => { console.error('❌', e.message); process.exit(1); });
