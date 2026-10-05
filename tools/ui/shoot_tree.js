// 给天赋树出图（PID-5，答若干题后）
const {spawn} = require('child_process');
const os = require('os'), fs = require('fs'), path = require('path');
const ROOT = require('../_root.js').findRoot(__dirname);
const PORT = 9359;
const CHROME = process.env.CHROME ||
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const prof = fs.mkdtempSync(path.join(os.tmpdir(), 'sh4-'));
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
  await sleep(2600);
  const ev = async x => (await S('Runtime.evaluate',
    {expression: x, returnByValue: true, awaitPromise: true})).result?.result?.value;

  await ev(`document.querySelector('#modes button[data-m="inst"]').click()`);
  await sleep(400);
  await ev(`[...document.querySelectorAll('.instcard')]
    .find(x => x.dataset.inst === 'PID-5').click()`);
  await sleep(2200);
  // 答 14 题（走推荐，答案错开）
  for (let i = 0; i < 14; i++) {
    await ev(`(() => {
        const b = document.querySelector('[data-treepick]') ||
                  document.querySelector('[data-treenext]');
        if (b) b.dispatchEvent(new MouseEvent('click', {bubbles: true}));
        const opts = document.querySelectorAll('#treeq .opt');
        if (!opts.length) return 0;
        opts[${i} % 4].dispatchEvent(new MouseEvent('click', {bubbles: true}));
        return 1;
      })()`);
    await sleep(60);
  }
  const st = await ev(`({done: document.querySelectorAll('.treenode.done').length,
      open: document.querySelectorAll('.treenode.open').length,
      locked: document.querySelectorAll('.treenode.locked').length})`);
  console.log('  已答/可答/锁定:', JSON.stringify(st));
  await sleep(400);
  const cap = await S('Page.captureScreenshot', {format: 'png', captureBeyondViewport: true});
  fs.writeFileSync(path.join(ROOT, '.shots', 'inst-tree.png'),
    Buffer.from(cap.result.data, 'base64'));
  console.log('  → .shots/inst-tree.png');
  ws.close(); ch.kill(); process.exit(0);
})().catch(e => { console.error('❌', e.message); process.exit(1); });
