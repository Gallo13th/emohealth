// 子页与路由专项：每套量表一个子页、URL 可直达/可后退、作答方式在子页内切、
// 导出按本量表范围（且真的产出文件内容）。
// 期望的量表套数**从 catalog 动态读**，不写死——范围裁剪后套数会变，
// 写死会让每次裁剪都要手改，还会把「套数意外变化」伪装成「数字过时」。
const EXPECT_N = JSON.parse(
  require('fs').readFileSync(
    require('path').join(__dirname, '..', '..', 'data', 'instruments', 'catalog.json'),
    'utf8')).instruments.length;

const {spawn} = require('child_process');
const os = require('os'), fs = require('fs'), path = require('path');
const PORT = 9361;
const CHROME = process.env.CHROME ||
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
// ⚠️ 默认目标必须是**工作区代码**。原先默认 `http://127.0.0.1:8891/emohealth/`
//    （WSL 里的旧部署），本测试因此长期对着**旧构建假绿**：那台 index.html 还是
//    `data-instview="paged"`，而工作区早就改成了 `data-instmode="classic"`。
//    改为 file:// 直开工作区（与 test_local_file.js 同一做法），不依赖服务。
const ROOT = path.resolve(__dirname, '..', '..');
const URL_ = process.env.URL ||
  'file:///' + path.join(ROOT, 'ui', 'index.html').replace(/\\/g, '/');
const sleep = ms => new Promise(r => setTimeout(r, ms));

let fail = 0;
const ck = (n, c, d = '') => {
  console.log(`  ${c ? '✅' : '❌'} ${n}${d ? '  —— ' + d : ''}`);
  if (!c) fail++;
};

(async () => {
  const prof = fs.mkdtempSync(path.join(os.tmpdir(), 'rt-'));
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
  let id = 0; const pend = new Map(); const errs = [];
  ws.onmessage = e => { const m = JSON.parse(e.data);
    if (m.id && pend.has(m.id)) { pend.get(m.id)(m); pend.delete(m.id); }
    if (m.method === 'Runtime.exceptionThrown')
      errs.push(m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text); };
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
      (r.result.exceptionDetails.exception?.description || '').slice(0, 180);
    return r.result?.result?.value;
  };
  const nav = async url => { await S('Page.navigate', {url}); await sleep(2600); };

  console.log('=== 首页 ===');
  await nav(URL_);
  const home = await ev(`({hash: location.hash,
      cards: document.querySelectorAll('.instcard').length,
      mode: (document.querySelector('#modes button.on')||{}).dataset?.m || ''})`);
  ck(`首页显示量表选择器（${EXPECT_N} 套）`, home.cards === EXPECT_N, home.cards + ' 张卡片');
  ck('首页没有子页头部（返回按钮）',
     !(await ev(`!!document.querySelector('[data-gohome]')`)));

  console.log('\n=== 直接访问子页 URL（可分享/可刷新）===');
  await nav(URL_ + '#/scale/PID-5');
  const sub = await ev(`({
      hash: location.hash,
      hasBack: !!document.querySelector('[data-gohome]'),
      code: (document.querySelector('.instheadcode')||{}).textContent || '',
      treeNodes: document.querySelectorAll('.treenode').length,
      items: document.querySelectorAll('.institem').length,
      hasExport: !!document.querySelector('[data-instexport]'),
      hasTierTree: !!document.querySelector('#treecard .treecard'),
      cards: document.querySelectorAll('.instcard').length
    })`);
  ck('URL 直达子页', /PID-5/.test(sub.hash), sub.hash);
  ck('子页有返回按钮', sub.hasBack === true);
  ck('子页显示量表代码', sub.code === 'PID-5', sub.code);
  ck('子页不再是选择器', sub.cards === 0, sub.cards + ' 张卡片');
  ck('220 题量表默认天赋树', sub.treeNodes === 220, sub.treeNodes + ' 节点');
  ck('子页有导出入口', sub.hasExport === true);

  console.log('\n=== 作答方式在子页内切换 ===');
  const sw = await ev(`(() => {
      const b = document.querySelector('[data-instmode="classic"]');
      if (!b) return {err: '没有切换按钮'};
      b.dispatchEvent(new MouseEvent('click', {bubbles: true}));
      return 1;
    })()`);
  await sleep(700);
  const paged = await ev(`({items: document.querySelectorAll('.institem').length,
      url: location.hash})`);
  ck('切到经典逐题后仍在该子页', paged.items === 10 && /PID-5/.test(paged.url),
     `${paged.items} 题 / ${paged.url}`);

  console.log('\n=== 子页导出：范围只含本量表 ===');
  const csv = await ev(`(() => {
      const ce = catalogEntry('PID-5');
      // 直接调生成函数取内容（download 会走 a.click，headless 下不好断言）
      const rows = instRows(INST_NOW);
      return {rows: rows.length, ids: rows.slice(0,2).map(r=>r.id),
              instruments: [...new Set(rows.map(r => r.id.split('_')[0]))]};
    })()`);
  ck('导出数据行数 = 该量表题数', csv.rows === 220, csv.rows + ' 行');
  ck('导出数据只来自本量表（ID 前缀一致）',
     csv.instruments.length === 1, JSON.stringify(csv.instruments));

  console.log('\n=== 浏览器后退回到首页 ===');
  await nav(URL_ + '#/scale/PID-5');
  await ev(`go('#/')`);
  await sleep(900);
  const back = await ev(`({hash: location.hash,
      cards: document.querySelectorAll('.instcard').length,
      hasBack: !!document.querySelector('[data-gohome]')})`);
  ck('回到首页', back.cards === EXPECT_N && !back.hasBack,
     `${back.cards} 张卡片 / hash=${back.hash}`);

  console.log('\n=== 已撤下的顶层模式不再可达（最小 UI / D116）===');
  // 原先这里断言「分级模式路由可用」（#/tier → #modes 亮 tier）。
  // 用户要求把分级/情景与实时置信度推断**从 UI 撤下**，所以这条改成**回退断言**：
  // #/tier 不再是一种模式，而是回落量表库；顶层只剩「题库」一个入口。
  // （完整回退断言见 test_ui_rolled_back.js）
  await nav(URL_ + '#/tier');
  const tier = await ev(`({mode: (document.querySelector('#modes button.on')||{}).dataset?.m,
      modeCount: document.querySelectorAll('#modes button').length,
      cards: document.querySelectorAll('.instcard').length,
      hasTreecard: !!document.querySelector('#treecard .treecard')})`);
  ck('分级模式路由已撤下（回落量表库）',
     tier.cards === EXPECT_N && tier.hasTreecard === false,
     `${tier.cards} 张卡片 / 技能条=${tier.hasTreecard}`);
  ck('顶层只剩「题库」一个入口', tier.modeCount === 1, tier.modeCount + ' 个按钮');

  console.log('\n脚本报错:', errs.length ? errs.slice(0, 2) : '无');
  ck('无脚本异常', errs.length === 0);
  ws.close(); ch.kill();
  console.log(fail ? `\n❌ ${fail} 项未通过` : '\n✅ 子页与路由全部通过');
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error('❌', e.message); process.exit(1); });
