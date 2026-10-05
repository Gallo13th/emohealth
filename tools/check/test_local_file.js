// 本地 file:// 直开验证：不依赖任何服务器，双击 ui/index.html 就能用。
// 这是项目的硬约束（离线静态、相对路径）——同步到博客只是分发方式之一。
// 期望的量表套数**从 catalog 动态读**，不写死——范围裁剪后套数会变，
// 写死会让每次裁剪都要手改，还会把「套数意外变化」伪装成「数字过时」。
const EXPECT_N = JSON.parse(
  require('fs').readFileSync(
    require('path').join(__dirname, '..', '..', 'data', 'instruments', 'catalog.json'),
    'utf8')).instruments.length;

const {spawn} = require('child_process');
const os = require('os'), fs = require('fs'), path = require('path');
const PORT = 9371;
const CHROME = process.env.CHROME ||
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const sleep = ms => new Promise(r => setTimeout(r, ms));

let fail = 0;
const ck = (n, c, d = '') => {
  console.log(`  ${c ? '✅' : '❌'} ${n}${d ? '  —— ' + d : ''}`);
  if (!c) fail++;
};

(async () => {
  const root = require('../_root.js').findRoot(__dirname);
  const index = path.join(root, 'ui', 'index.html');
  const fileUrl = 'file:///' + index.replace(/\\/g, '/');
  console.log('file:// 地址：', fileUrl, '\n');

  const prof = fs.mkdtempSync(path.join(os.tmpdir(), 'file-'));
  const ch = spawn(CHROME, ['--headless=new', '--no-sandbox', '--disable-gpu',
    '--remote-debugging-port=' + PORT, '--user-data-dir=' + prof,
    '--window-size=1280,1000',
    // file:// 下要允许读同目录的 js（默认是允许的，显式声明更稳）
    '--allow-file-access-from-files', 'about:blank'], {stdio: 'ignore'});
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
  await S('Page.navigate', {url: fileUrl});
  await sleep(2600);
  const ev = async x => {
    const r = await S('Runtime.evaluate',
      {expression: x, returnByValue: true, awaitPromise: true});
    if (r.result?.exceptionDetails) return 'EXC: ' +
      (r.result.exceptionDetails.exception?.description || '').slice(0, 160);
    return r.result?.result?.value;
  };

  console.log('=== file:// 首页 ===');
  const home = await ev(`({
      catalog: !!window.EMOHEALTH_CATALOG,
      treeMap: Object.keys(window.EMOHEALTH_TREEMAP || {}).length,
      instMap: Object.keys(window.EMOHEALTH_INSTMAP || {}).length,
      cards: document.querySelectorAll('.instcard').length,
      topMeta: document.getElementById('topmeta').textContent.slice(0, 50)
    })`);
  ck('目录已加载', home.catalog === true);
  ck(`${EXPECT_N} 套量表都在`, home.cards === EXPECT_N, home.cards + ' 张卡片');
  ck('天赋树清单 2 套', home.treeMap === 2, home.treeMap + ' 套');
  ck(`按需加载清单 ${EXPECT_N} 条`, home.instMap === EXPECT_N, home.instMap + ' 条');

  console.log('\n=== file:// 下按需加载（注入 <script>，不是 fetch）===');
  const load = await ev(`(async () => {
      const d = await loadInstrument('PID-5');
      return {items: d.items.length, zh: d.items.filter(x => x.zh).length,
              firstZh: d.items[0].zh};
    })()`);
  ck('能加载量表包（file:// 不受同源限制）', load.items === 220, load.items + ' 题');
  ck('包内带中译', load.zh === 220, load.zh + ' 条');

  console.log('\n=== file:// 下的量表子页与天赋树 ===');
  await S('Page.navigate', {url: fileUrl + '#/scale/PID-5'});
  await sleep(2800);
  const sub = await ev(`({
      code: (document.querySelector('.instheadcode')||{}).textContent || '',
      nodes: document.querySelectorAll('.treenode').length,
      open: document.querySelectorAll('.treenode.open').length,
      hasExport: !!document.querySelector('[data-instexport]'),
      hasBack: !!document.querySelector('[data-gohome]'),
      href: location.href.slice(-30),
      cards: document.querySelectorAll('.instcard').length,
      stageLen: (document.getElementById('stage')||{}).innerHTML?.length || -1,
      stageHead: ((document.getElementById('stage')||{}).textContent||'').slice(0, 60)
    })`);
  if (!sub.code) console.log('     （诊断：' + JSON.stringify(sub) + '）');
  ck('子页路由可用', sub.code === 'PID-5', sub.code);
  ck('天赋树渲染', sub.nodes === 220, sub.nodes + ' 节点');
  // ⚠️ 这一条是用户报的问题：**可答节点必须有高亮**。
  //    根因是 CSS 用了不存在的 `--brand`，`stroke:var(--brand)` 整条声明失效，
  //    可答节点退化成白色空心圈，与锁定节点几乎分不出。
  ck('可答节点有高亮（>0）', sub.open > 0, sub.open + ' 个可答');
  ck('导出入口存在', sub.hasExport === true);

  console.log('\n=== file:// 下每套 >60 题量表都能高亮 ===');
  const treeScales = await ev(`Object.keys(window.EMOHEALTH_TREEMAP || {})`);
  const noHighlight = [];
  for (const code of treeScales) {
    // ⚠️ 必须显式进 `/tree`：IPIP-NEO 的**默认**作答方式是「分级模式」
    //    （它是本项目的基准，有自己的阶梯与支撑网络），所以默认视图里
    //    不会有天赋树的节点——按默认 URL 断言会误报。
    await S('Page.navigate', {url: fileUrl + '#/scale/' + code + '/tree'});
    await sleep(1800);
    const r = await ev(`({nodes: document.querySelectorAll('.treenode').length,
        open: document.querySelectorAll('.treenode.open').length})`);
    if (!(r.nodes > 0 && r.open > 0)) noHighlight.push(code + '(' + JSON.stringify(r) + ')');
  }
  ck(`${treeScales.length} 套天赋树量表都有节点且有高亮`,
     noHighlight.length === 0, noHighlight.slice(0, 3).join(' '));

  console.log('\n=== file:// 下导出（Blob 下载）===');
  const dl = fs.mkdtempSync(path.join(os.tmpdir(), 'fdl-'));
  await S('Browser.setDownloadBehavior',
    {behavior: 'allow', downloadPath: dl, eventsEnabled: true});
  await ev(`(() => { const b = document.querySelector('[data-instexport="csv"]');
      if (b) b.dispatchEvent(new MouseEvent('click', {bubbles: true}));
      return 1; })()`);
  await sleep(1200);
  const files = fs.readdirSync(dl).filter(f => !f.endsWith('.crdownload'));
  ck('file:// 下能下载导出文件', files.length === 1, files.join(', ') || '(空)');

  console.log('\n脚本报错:', errs.length ? errs.slice(0, 2) : '无');
  ck('无脚本异常', errs.length === 0);
  ws.close(); ch.kill();
  console.log(fail ? `\n❌ ${fail} 项未通过` : '\n✅ file:// 本地直开全部通过');
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error('❌', e.message); process.exit(1); });
