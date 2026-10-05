// 验证 Level 1 的门槛型结果页：按门槛判定，**不显示百分位**
const {spawn} = require('child_process');
const os = require('os'), fs = require('fs'), path = require('path');
const PORT = 9393;
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
  const url = toUrl(path.join(ROOT, 'ui', 'index.html')) + '#/scale/DSM5TR-L1/classic';
  const prof = fs.mkdtempSync(path.join(os.tmpdir(), 'l1r-'));
  const ch = spawn(CHROME, ['--headless=new', '--no-sandbox', '--disable-gpu',
    '--remote-debugging-port=' + PORT, '--user-data-dir=' + prof,
    '--window-size=1280,1200', '--allow-file-access-from-files', 'about:blank'],
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
  await S('Page.navigate', {url});
  await sleep(3000);
  const ev = async x => {
    const r = await S('Runtime.evaluate',
      {expression: x, returnByValue: true, awaitPromise: true});
    if (r.result?.exceptionDetails) return 'EXC: ' +
      (r.result.exceptionDetails.exception?.message || '').slice(0, 160);
    return r.result?.result?.value;
  };

  // 制造「自杀意念达到门槛（≥1）、抑郁也达到（≥2）」的作答
  const setup = await ev(`(() => {
      const d = INST_NOW;
      if (!d) return 'THE SCALE NOT LOADED';
      for (const it of d.items) S.instResp[it.id] = 0;
      const byName = {};
      for (const dim of d.dimensions) byName[dim.name] = dim.items;
      // 抑郁域第 1 题 = 2（正好到门槛），自杀意念域 = 1（门槛更低也到）
      S.instResp[byName['Depression'][0]] = 2;
      S.instResp[byName['Suicidal Ideation'][0]] = 1;
      S.instResult = {rows: instScores(d, S.instResp)};
      renderTop(); renderStage();
      const st = document.getElementById('stage');
      return {text: st.textContent.replace(/\\s+/g, ' ').slice(0, 200),
              hasTable: !!st.querySelector('.insttable'),
              rows: st.querySelectorAll('.insttable tbody tr').length,
              reached: [...st.querySelectorAll('tr.domrow')].map(tr =>
                tr.children[0].textContent),
              // ⚠️ 不能全文搜「百分位」——我的说明文字里就写着「不给百分位」。
              //    真正的意图是：**表头里没有百分位列**。断言要对着意图写。
              heads: [...st.querySelectorAll('.insttable thead th')]
                .map(x => x.textContent.trim()),
              hasPctlCol: [...st.querySelectorAll('.insttable thead th')]
                .some(x => x.textContent.includes('百分位')),
              hasInferred: /没有对应的 Level 2 细评册/.test(st.textContent),
              /* D120（task-24）：来源性质说明（推论/不是这册手册的原文/已核查）已删除 */
              hasSourceNature: /推论|非手册原文|已核查/.test(st.textContent),
              hasClipNote: /漏报的代价高于误报/.test(st.textContent)};
    })()`);
  if (typeof setup === 'string') { console.log('  ✗', setup); process.exit(1); }
  console.log('  表头:', JSON.stringify(setup.heads));
  ck('结果页按门槛呈现（13 行）', setup.rows === 13, setup.rows + ' 行');
  ck('达到门槛的域被标出', setup.reached.length === 2,
     JSON.stringify(setup.reached));
  ck('表头没有百分位列（L1 不是常模量表）', setup.hasPctlCol === false);
  ck('如实说明「该域没有 Level 2 细评册，人格功能用 PID-5」（用户语言）',
     setup.hasInferred === true);
  ck('界面上不再出现来源性质说明（推论/非手册原文/已核查）',
     setup.hasSourceNature === false);
  ck('说明自杀意念等门槛更低的原因', setup.hasClipNote === true);

  const cap = await S('Page.captureScreenshot',
    {format: 'png', captureBeyondViewport: true});
  fs.writeFileSync(path.join(ROOT, '.shots', 'l1-threshold.png'),
    Buffer.from(cap.result.data, 'base64'));
  console.log('  → .shots/l1-threshold.png');
  ws.close(); ch.kill();
  console.log(fail ? `\n❌ ${fail} 项未通过` : '\n✅ L1 门槛型结果页通过');
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error('❌', e.message); process.exit(1); });
