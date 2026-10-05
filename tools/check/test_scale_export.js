// 验证子页导出真的产出文件，并核对内容自洽（范围/列名/评分行）
const {spawn} = require('child_process');
const os = require('os'), fs = require('fs'), path = require('path');
const PORT = 9362;
const CHROME = process.env.CHROME ||
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const ROOT_ = require('path').resolve(__dirname, '..', '..');
// ⚠️ 默认必须指向**工作区**，不能是某个部署副本——否则会对着旧构建**假绿**
//    （本仓库已因此踩过三次）。file:// 直开不依赖任何服务，测的就是工作区。
const URL_ = process.env.URL ||
  'file:///' + require('path').join(ROOT_, 'ui', 'index.html').replace(/\\/g, '/');
const sleep = ms => new Promise(r => setTimeout(r, ms));

let fail = 0;
const ck = (n, c, d = '') => {
  console.log(`  ${c ? '✅' : '❌'} ${n}${d ? '  —— ' + d : ''}`);
  if (!c) fail++;
};

(async () => {
  const dl = fs.mkdtempSync(path.join(os.tmpdir(), 'dl-'));
  const prof = fs.mkdtempSync(path.join(os.tmpdir(), 'pf-'));
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
  await S('Browser.setDownloadBehavior',
    {behavior: 'allow', downloadPath: dl, eventsEnabled: true});
  const ev = async x => {
    const r = await S('Runtime.evaluate',
      {expression: x, returnByValue: true, awaitPromise: true});
    if (r.result?.exceptionDetails) return 'EXC: ' +
      (r.result.exceptionDetails.exception?.description || '').slice(0, 160);
    return r.result?.result?.value;
  };

  await S('Page.navigate', {url: URL_ + '#/scale/DSM5TR-L2-Anger'});
  await sleep(2600);
  // 答满 5 题再出结果，这样四种导出都能测
  await ev(`(() => { for (const li of document.querySelectorAll('.institem')) {
      const b = li.querySelector('.opt'); if (b) b.dispatchEvent(new MouseEvent('click',{bubbles:true}));
    } return 1; })()`);
  await sleep(500);
  await ev(`(() => { const b = document.querySelector('[data-instdone]');
      if (b && !b.disabled) b.dispatchEvent(new MouseEvent('click',{bubbles:true}));
      return 1; })()`);
  await sleep(600);
  const state = await ev(`({answered: Object.keys(S.instResp).length,
      hasResult: !!S.instResult})`);
  ck('已答满并算出结果', state.answered === 5 && state.hasResult === true,
     JSON.stringify(state));

  // 依次触发四种导出
  const kinds = ['csv', 'json', 'md', 'result'];
  for (const k of kinds) {
    await ev(`(() => { const b = [...document.querySelectorAll('[data-instexport]')]
        .find(x => x.dataset.instexport === '${k}');
        if (b) b.dispatchEvent(new MouseEvent('click', {bubbles: true}));
        return 1; })()`);
    await sleep(700);
  }
  await sleep(1200);

  const files = fs.readdirSync(dl).filter(f => !f.endsWith('.crdownload'));
  console.log('  下载目录：', files.join(', ') || '(空)');
  ck('导出了 4 个文件', files.length === 4, files.length + ' 个');
  ck('文件名带量表代码',
     files.every(f => f.startsWith('DSM5TR-L2-Anger')), files.join(' '));

  const rd = f => { const p = path.join(dl, f);
    return fs.existsSync(p) ? fs.readFileSync(p, 'utf8') : ''; };
  const find = ext => files.find(f => f.endsWith(ext)) || '';
  // ⚠️ 有两个 .csv（逐题作答 / 结果），**必须按文件名区分**。
  //    我第一版用 `find(f => f.endsWith('.csv'))`，抓到的是「结果」CSV
  //    （目录里「结果」排在「逐题作答」之前），于是误报「没有中文表头」。
  const itemCsv = files.find(f => /逐题作答.*\.csv$/.test(f)) || '';
  const resultCsv = files.find(f => /结果.*\.csv$/.test(f)) || '';

  const csv = rd(itemCsv);
  ck('逐题作答 CSV 有中文表头', /题号,题项ID,维度,计分键/.test(csv),
     csv.split('\n')[0].slice(0, 60));
  const csvLines = csv.split(/\r?\n/).filter(Boolean);
  ck('CSV 行数 = 表头 + 5 题', csvLines.length === 6, csvLines.length + ' 行');

  const js = rd(find('.json'));
  let jd = null;
  try { jd = JSON.parse(js); } catch (e) { jd = null; }
  ck('JSON 可解析', !!jd);
  if (jd) {
    ck('JSON 只含本量表', jd.instrument === 'DSM5TR-L2-Anger', jd.instrument);
    ck('JSON 记了已答数', jd.answered === 5, String(jd.answered));
    ck('JSON 含作答（按 itemId）', Object.keys(jd.responses || {}).length === 5,
       Object.keys(jd.responses || {}).length + ' 条');
    ck('JSON 含分数', Array.isArray(jd.scores) && jd.scores.length > 0,
       (jd.scores || []).length + ' 行');
    ck('JSON 带授权', !!(jd.license && jd.license.kind), jd.license?.kind);
  }

  const md = rd(find('.md'));
  ck('Markdown 有标题', /^# /.test(md), md.split('\n')[0].slice(0, 50));
  ck('Markdown 声明只含本量表', /仅含「DSM5TR-L2-Anger」/.test(md));
  ck('Markdown 有结果表', /\| 维度 \| 分数 \|/.test(md));
  ck('Markdown 有逐题表', /## 逐题作答/.test(md));
  ck('Markdown 说明常模缺失', /暂无可用常模/.test(md));

  const rc = rd(resultCsv);
  ck('结果 CSV 有列头', /维度,分数,百分位,已答,题数/.test(rc), rc.split('\n')[0].slice(0, 50));
  ck('结果 CSV 有 1 行维度', rc.split(/\r?\n/).filter(Boolean).length === 2,
     rc.split(/\r?\n/).filter(Boolean).length + ' 行');

  ws.close(); ch.kill();
  console.log(fail ? `\n❌ ${fail} 项未通过` : '\n✅ 子页导出全部通过');
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error('❌', e.message); process.exit(1); });
