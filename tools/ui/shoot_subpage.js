// 给子页出图：子页头部（返回 + 本量表导出）+ 内容
const {spawn} = require('child_process');
const os = require('os'), fs = require('fs'), path = require('path');
const ROOT = require('../_root.js').findRoot(__dirname);
const PORT = 9363;
const CHROME = process.env.CHROME ||
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const prof = fs.mkdtempSync(path.join(os.tmpdir(), 'sh5-'));
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

  // ① 子页（PID-5，天赋树）——展开导出菜单
  await S('Page.navigate', {url: 'http://127.0.0.1:8891/emohealth/#/scale/PID-5'});
  await sleep(2800);
  await S('Runtime.evaluate', {expression: `(() => {
      const w = document.querySelector('.expwrap'); if (w) w.focus();
      return 1; })()`});
  await sleep(400);
  let cap = await S('Page.captureScreenshot', {format: 'png', captureBeyondViewport: false});
  fs.writeFileSync(path.join(ROOT, '.shots', 'subpage-header.png'),
    Buffer.from(cap.result.data, 'base64'));
  console.log('  → .shots/subpage-header.png');

  // ② 短量表子页（Anger，经典逐题）
  await S('Page.navigate', {url: 'http://127.0.0.1:8891/emohealth/#/scale/DSM5TR-L2-Anger'});
  await sleep(2400);
  cap = await S('Page.captureScreenshot', {format: 'png', captureBeyondViewport: true});
  fs.writeFileSync(path.join(ROOT, '.shots', 'subpage-short.png'),
    Buffer.from(cap.result.data, 'base64'));
  console.log('  → .shots/subpage-short.png');
  ws.close(); ch.kill(); process.exit(0);
})().catch(e => { console.error('❌', e.message); process.exit(1); });
