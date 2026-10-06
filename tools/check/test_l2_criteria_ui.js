// L2 逐册口径：按 kind 呈现（分界/分带/逐项/待补T分），且 Substance 不求和
const {spawn} = require('child_process');
const os = require('os'), fs = require('fs'), path = require('path');
const PORT = 9397;
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
  const prof = fs.mkdtempSync(path.join(os.tmpdir(), 'l2-'));
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
  // 进某册、全答某值、出结果，返回结果页特征
  const probe = async (code, fill) => {
    await S('Page.navigate', {url: base + '#/scale/' + code + '/classic'});
    await sleep(2600);
    const r = await ev(`(() => {
        const d = INST_NOW; if (!d) return {err: 'scale not loaded'};
        for (const it of d.items) S.instResp[it.id] = ${fill};
        S.instResult = {rows: instScores(d, S.instResp)};
        renderTop(); renderStage();
        const st = document.getElementById('stage');
        // ⚠️ 只取**结果区**文本：整页文本前面还有子页头部与导出菜单，
        //    取整页会匹配到无关内容（我第一版就误判了「命中 High」）。
        const res = st.querySelector('.insttable') ? st : st;
        return {agg: (Object.values(d.scoring)[0] || {}).aggregation,
                value: S.instResult.rows[0].value,
                heads: [...res.querySelectorAll('.insttable thead th')].map(x=>x.textContent.trim()),
                rows: res.querySelectorAll('.insttable tbody tr').length,
                hit: res.querySelectorAll('tr.domrow').length,
                // 跳过 .insthead 与 .chainbar 后的正文
                body: [...st.children].filter(x =>
                  !x.classList.contains('insthead') && !x.classList.contains('chainbar'))
                  .map(x => x.textContent).join(' ').replace(/\\s+/g,' ').slice(0, 400)};
      })()`);
    return r;
  };

  console.log('=== Mania（ASRM）：分界型 ===');
  const mania = await probe('DSM5TR-L2-Mania', 2);   // 全答 2 → 5×2 = 10 ≥ 6
  ck('聚合是 sum', mania.agg === 'sum', mania.agg);
  ck('原始分 = 10', mania.value === 10, String(mania.value));
  ck('给出 2 个分带区间', mania.rows === 2, mania.rows + ' 行');
  ck('命中 ≥6 那条（高概率躁狂）', mania.hit >= 1 && /高概率|轻躁狂/.test(mania.body),
     JSON.stringify(mania.body.slice(0, 80)));

  console.log('\n=== Somatic（PHQ-15）：严重度分带 ===');
  const som = await probe('DSM5TR-L2-Somatic', 1);   // 15×1 = 15 → High
  ck('原始分 = 15', som.value === 15, String(som.value));
  ck('给出 4 个严重度带', som.rows === 4, som.rows + ' 行');
  ck('命中 High（15–30）', /High/.test(som.body),
     JSON.stringify(som.body.slice(0, 90)));

  console.log('\n=== Repetitive：分界 ≥8 ===');
  const rep = await probe('DSM5TR-L2-Repetitive', 2); // 5×2 = 10 ≥ 8
  ck('原始分 = 10', rep.value === 10, String(rep.value));
  ck('命中「可考虑对强迫症做更详细评估」', /强迫症/.test(rep.body),
     JSON.stringify(rep.body.slice(0, 90)));

  console.log('\n=== Substance：**不求和**，逐项独立 ===');
  const sub = await probe('DSM5TR-L2-Substance', 3);
  ck('聚合是 count_true（不是 sum）', sub.agg === 'count_true', String(sub.agg));
  ck('结果是「>0 的项数」= 10 而非 30（10×3）', sub.value === 10, String(sub.value));
  ck('表头是逐项形态（项/物质/作答/是否 >0）',
     sub.heads.join(',') === '项,物质,作答,是否 >0', sub.heads.join(','));
  ck('明确写出「不是总分」', /不是总分/.test(sub.body));

  console.log('\n=== PROMIS（Depression）：T 分**查表**（Phase 2）===');
  const dep = await probe('DSM5TR-L2-Depression', 5); // 8×5 = 40
  ck('原始分 = 40', dep.value === 40, String(dep.value));
  /* Phase 2：Depression 的官方 raw→T 转换表已入档 → 页面给出**查表** T 与 SE，
     不再说「T 分转换表尚未取得」。断言跟着契约改（仍要求如实说明百分位不可用）。 */
  ck('结果页给出查表 T 分与 SE（不再说 T 分表尚未取得）',
     /T = \d/.test(dep.body) && /SE/.test(dep.body) && !/尚未取得/.test(dep.body),
     dep.body.slice(0, 140));
  ck('结果页说明「T 分＝查表值」，并用标准差衡量（高于/低于常模均值 x.xx 个标准差）',
     /查表值/.test(dep.body) && /个标准差/.test(dep.body), dep.body.slice(0, 140));
  ck('给出 T 分口径说明（M=50, SD=10）', /M=50/.test(dep.body));
  /* 表缺失分支（将来某册尚未入档时走这里）：临时把表藏掉 → 必须明示缺失、不给 T */
  const depNoTable = await ev(`(() => {
      const saved = INST_NOW.criteria.tscore_table;
      INST_NOW.criteria.tscore_table = null;
      renderStage();
      const st = document.getElementById('stage');
      const body = [...st.children].filter(x => !x.classList.contains('insthead')
        && !x.classList.contains('chainbar')).map(x => x.textContent).join(' ')
        .replace(/\\s+/g, ' ').slice(0, 400);
      const J = instJudgment(INST_NOW);
      INST_NOW.criteria.tscore_table = saved;
      renderStage();
      return {body: body, hadTable: !!saved, t: J.tscore}; })()`);
  ck('表缺失时（tscore_table=null）页面明示「尚未取得」且不给 T',
     depNoTable.hadTable === true && depNoTable.t === null
     && /尚未取得/.test(depNoTable.body) && !/T = \d/.test(depNoTable.body),
     depNoTable.body.slice(0, 140));

  ws.close(); ch.kill();
  console.log(fail ? `\n❌ ${fail} 项未通过` : '\n✅ L2 逐册口径全部通过');
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error('❌', e.message); process.exit(1); });
