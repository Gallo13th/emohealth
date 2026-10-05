// 给多量表界面出图：题库选择器、单量表分页作答、结果页
const {spawn} = require('child_process');
const os = require('os'), fs = require('fs'), path = require('path');
const ROOT = require('../_root.js').findRoot(__dirname);
const PORT = 9349;
const CHROME = process.env.CHROME ||
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const OUT = path.join(ROOT, '.shots');
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  fs.mkdirSync(OUT, {recursive: true});
  const prof = fs.mkdtempSync(path.join(os.tmpdir(), 'shot-'));
  const ch = spawn(CHROME, ['--headless=new', '--no-sandbox', '--disable-gpu',
    '--remote-debugging-port=' + PORT, '--user-data-dir=' + prof,
    '--window-size=1280,1000', 'about:blank'], {stdio: 'ignore'});
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
    {expression: x, returnByValue: true, awaitPromise: true}))
    .result?.result?.value;

  const shot = async name => {
    const r = await S('Page.captureScreenshot', {format: 'png', captureBeyondViewport: true});
    const p = path.join(OUT, name + '.png');
    fs.writeFileSync(p, Buffer.from(r.result.data, 'base64'));
    console.log('  →', path.relative(ROOT, p));
  };

  // 1) 题库选择器
  await ev(`document.querySelector('#modes button[data-m="inst"]').click()`);
  await sleep(600);
  await shot('inst-picker');

  // 2) 单量表分页作答：选一个多题量表（PID-5 220 题，分 22 页）
  await ev(`(() => { const c=[...document.querySelectorAll('.instcard')]
      .find(x=>x.dataset.inst==='PID-5'); c.click(); return 1; })()`);
  await sleep(1500);
  // 答几题再截图，显示进度
  await ev(`(() => { document.querySelectorAll('.institem').forEach((li,i) => {
      const b = li.querySelectorAll('.opt')[i % 5]; if (b) b.click(); }); return 1; })()`);
  await sleep(400);
  await shot('inst-answer');

  // 3) 结果页：换一套小量表，全答后看结果
  await ev(`document.querySelector('[data-instback]').click()`);
  await sleep(400);
  await ev(`(() => { const c=[...document.querySelectorAll('.instcard')]
      .find(x=>x.dataset.inst==='IPIP-16PF'); c.click(); return 1; })()`);
  await sleep(1800);
  await ev(`(() => { for (let p=0;p<17;p++){
      document.querySelectorAll('.institem').forEach((li,i) => {
        const b = li.querySelectorAll('.opt')[(i+p) % 5]; if (b) b.click(); });
      const nx = document.querySelector('[data-page]:not([disabled])');
      if (nx && !nx.textContent.includes('上一')) nx.click();
    } return 1; })()`);
  await sleep(600);
  const state = await ev(`({answered: Object.keys(S.instResp).length,
      done: !!(document.querySelector('[data-instdone]')||{}).disabled})`);
  console.log('  16PF 已答', state.answered, '题');
  const doneBtn = await ev(`(() => { const b=document.querySelector('[data-instdone]');
      if (b && !b.disabled) { b.click(); return 'clicked'; } return 'disabled'; })()`);
  await sleep(700);
  await shot('inst-result-' + doneBtn);

  ws.close(); ch.kill(); process.exit(0);
})().catch(e => { console.error('❌', e.message); process.exit(1); });
