// 链路跳转：L1 → L2 → PID-5 上下游都能点通，且推论关系有标注
const {spawn} = require('child_process');
const os = require('os'), fs = require('fs'), path = require('path');
const PORT = 9395;
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
  const base = toUrl(path.join(ROOT, 'ui', 'index.html'));
  const prof = fs.mkdtempSync(path.join(os.tmpdir(), 'ch-'));
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
  const ev = async x => {
    const r = await S('Runtime.evaluate',
      {expression: x, returnByValue: true, awaitPromise: true});
    if (r.result?.exceptionDetails) return 'EXC: ' +
      (r.result.exceptionDetails.exception?.message || '').slice(0, 160);
    return r.result?.result?.value;
  };
  const nav = async h => { await S('Page.navigate', {url: base + h}); await sleep(2800); };

  console.log('=== L1 结果页：建议列可点 ===');
  await nav('#/scale/DSM5TR-L1/classic');
  // 让抑郁与人格功能都达到门槛
  await ev(`(() => {
      const d = INST_NOW; const by = {};
      for (const dim of d.dimensions) by[dim.name] = dim.items;
      for (const it of d.items) S.instResp[it.id] = 0;
      S.instResp[by['Depression'][0]] = 3;
      S.instResp[by['Personality Functioning'][0]] = 2;
      S.instResp[by['Suicidal Ideation'][0]] = 1;
      S.instResult = {rows: instScores(d, S.instResp)};
      renderTop(); renderStage(); return 1; })()`);
  await sleep(400);
  const l1 = await ev(`(() => {
      const st = document.getElementById('stage');
      const btns = [...st.querySelectorAll('[data-goscale]')].map(b => b.dataset.goscale);
      const bar = st.querySelector('.chainbar');
      /* D119（用户点名）：界面**不再显示**「推论/非手册原文」这类来源性质说明，
         改为机器可读的 data-link-status（断言跟着改，不是删断言）。 */
      const route = st.querySelector('[data-goscale][data-link-status]');
      return {btns, hasBar: !!bar,
              barText: bar ? bar.textContent.replace(/\\s+/g,' ').slice(0, 110) : '',
              inferredStatus: route ? route.dataset.linkStatus : null,
              visibleInferred: /推论|非手册原文/.test(st.textContent)};
    })()`);
  ck('建议列给出可点的下游量表', l1.btns.includes('DSM5TR-L2-Depression'),
     JSON.stringify(l1.btns));
  ck('人格功能域给出 PID-5 入口（来源性质在 data-link-status，不写「推论」字样）',
     l1.btns.includes('PID-5') && l1.inferredStatus === 'inferred'
     && l1.visibleInferred === false,
     `status=${l1.inferredStatus} visibleInferred=${l1.visibleInferred}`);
  ck('L1 有链路条并标明是起点', l1.hasBar === true, l1.barText);

  console.log('\n=== 点进 Level 2 抑郁册 ===');
  await ev(`(() => { const b = document.querySelector('[data-goscale="DSM5TR-L2-Depression"]');
      b.dispatchEvent(new MouseEvent('click', {bubbles: true})); return 1; })()`);
  await sleep(2200);
  const l2 = await ev(`(() => {
      const bar = document.querySelector('.chainbar');
      return {hash: location.hash,
              code: (document.querySelector('.instheadcode')||{}).textContent || '',
              barText: bar ? bar.textContent.replace(/\\s+/g,' ').slice(0, 140) : '',
              hasBack: !!document.querySelector('[data-goscale="DSM5TR-L1"]')};
    })()`);
  ck('跳到了 L2 抑郁册', l2.code === 'DSM5TR-L2-Depression', l2.code);
  ck('L2 标明自己是哪个域触发后的细评',
     /Level 1/.test(l2.barText) && /Depression/.test(l2.barText), l2.barText);
  ck('L2 能回到 Level 1', l2.hasBack === true);

  console.log('\n=== 回 Level 1 ===');
  await ev(`(() => { const b = document.querySelector('[data-goscale="DSM5TR-L1"]');
      b.dispatchEvent(new MouseEvent('click', {bubbles: true})); return 1; })()`);
  await sleep(2200);
  ck('回到 L1', (await ev(`location.hash`)).includes('DSM5TR-L1'),
     await ev(`document.querySelector('.instheadcode').textContent`));

  console.log('\n=== PID-5 侧：与链路的关系（来源性质改为机器可读）===');
  await nav('#/scale/PID-5');
  const p5 = await ev(`(() => {
      const bar = document.querySelector('.chainbar');
      const note = bar ? bar.querySelector('[data-link-status]') : null;
      return {hasBar: !!bar,
              text: bar ? bar.textContent.replace(/\\s+/g,' ').slice(0, 160) : '',
              status: note ? note.dataset.linkStatus : null,
              visibleInferred: /推论|非手册原文/.test(bar ? bar.textContent : ''),
              hasBack: !!document.querySelector('[data-goscale="DSM5TR-L1"]')};
    })()`);
  ck('PID-5 有链路条', p5.hasBar === true, p5.text);
  ck('注明与 L1 人格功能域相接；来源性质在 data-link-status（可见文案不提「推论」）',
     p5.status === 'inferred' && p5.visibleInferred === false,
     `status=${p5.status} visibleInferred=${p5.visibleInferred}`);
  ck('PID-5 能回到 Level 1', p5.hasBack === true);

  ws.close(); ch.kill();
  console.log(fail ? `\n❌ ${fail} 项未通过` : '\n✅ 链路跳转全部通过');
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error('❌', e.message); process.exit(1); });
