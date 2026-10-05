// 界面截图工具（开发用，不进 v1 交付链路）
//
// 为什么需要：天赋树是**图形**界面，改布局只能看图判断。而 6 个 node 测试
// 只验证结构与门控，验证不了「看不看得懂」。这个脚本用 CDP 直接驱动无头
// Chrome：注入作答 → 渲染 → 截图，不需要装 puppeteer/playwright。
//
// 用法：
//   node tools/ui/shoot_ui.js                     # 默认几个场景
//   node tools/ui/shoot_ui.js --n 30 --sel 5      # 答 30 题并选中第 5 个节点
//
// 输出：.shots/*.png
const fs = require('fs'), path = require('path');
const {spawn} = require('child_process');

const ROOT = require('../_root.js').findRoot(__dirname);
const OUT = path.join(ROOT, '.shots');
const CHROME = process.env.CHROME_PATH ||
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const PORT = 9333;
const FILE_URL = 'file:///' + path.join(ROOT, 'ui', 'index.html').replace(/\\/g, '/');

const argv = process.argv.slice(2);
const arg = (k, d) => {
  const i = argv.indexOf('--' + k);
  return i < 0 ? d : argv[i + 1];
};
const W = +arg('w', 1440), H = +arg('h', 1200);

const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  fs.mkdirSync(OUT, {recursive: true});
  const prof = path.join(require('os').tmpdir(), 'emohealth-shot-prof');
  const chrome = spawn(CHROME, [
    '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
    '--hide-scrollbars', '--mute-audio', `--remote-debugging-port=${PORT}`,
    `--user-data-dir=${prof}`, `--window-size=${W},${H}`, 'about:blank',
  ], {stdio: 'ignore'});

  // 等 devtools 端口起来
  let ver = null;
  for (let i = 0; i < 60 && !ver; i++) {
    try { ver = await (await fetch(`http://127.0.0.1:${PORT}/json/version`)).json(); }
    catch (e) { await sleep(250); }
  }
  if (!ver) { chrome.kill(); throw new Error('Chrome devtools 端口没起来'); }

  const ws = new WebSocket(ver.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  let id = 0;
  const pend = new Map();
  ws.onmessage = ev => {
    const m = JSON.parse(ev.data);
    if (m.id && pend.has(m.id)) { pend.get(m.id)(m); pend.delete(m.id); }
  };
  const send = (method, params, sessionId) => new Promise(res => {
    const i = ++id;
    pend.set(i, res);
    ws.send(JSON.stringify({id: i, method, params, sessionId}));
  });

  // 自己建一个 target，这样能拿到 sessionId 直接对它发 Page/Runtime
  const t = await send('Target.createTarget', {url: 'about:blank'});
  const targetId = t.result.targetId;
  const a = await send('Target.attachToTarget', {targetId, flatten: true});
  const sid = a.result.sessionId;
  const S = (m, p) => send(m, p, sid);

  await S('Page.enable', {});
  await S('Runtime.enable', {});
  await S('Emulation.setDeviceMetricsOverride',
          {width: W, height: H, deviceScaleFactor: 1, mobile: false});
  await S('Page.navigate', {url: FILE_URL});
  await sleep(1500);

  const evaluate = async expr => {
    const r = await S('Runtime.evaluate',
      {expression: expr, returnByValue: true, awaitPromise: true});
    if (r.result && r.result.exceptionDetails)
      throw new Error(JSON.stringify(r.result.exceptionDetails));
    return r.result && r.result.result ? r.result.result.value : null;
  };

  const shot = async (name, fullPage) => {
    const p = path.join(OUT, name + '.png');
    const opts = {format: 'png', captureBeyondViewport: !!fullPage};
    if (fullPage) {
      const m = await S('Page.getLayoutMetrics', {});
      const cs = m.result.cssContentSize || m.result.contentSize;
      opts.clip = {x: 0, y: 0, width: W, height: Math.min(cs.height, 6000), scale: 1};
    }
    const r = await S('Page.captureScreenshot', opts);
    fs.writeFileSync(p, Buffer.from(r.result.data, 'base64'));
    console.log('  →', path.relative(ROOT, p));
  };
  // 直接驱动页面内部的函数（index.html 的脚本是全局作用域的，"use strict" 不隔离）
  // 驱动页面内部的函数。注意必须走 renderStage()/renderTierTree() 这条**应用自己的**
  // 路径——只调 renderTierGraph + renderTierPanel 会漏掉「下一题」常驻区的更新，
  // 于是截图显示的是上一次的旧内容（这个坑我踩过：图对了、面板是旧的）。
  const reset = async () => evaluate(`(() => {
      S.resp = {}; S.tierSel = null; S.result = null; S.peekOpen = false;
      S.coolUntil = 0; S.scene = null; S.panelOpen = null;
      refreshAdapt(); renderTop(); renderTree(); renderStage(); renderResult();
      return 0;
    })()`);
  const answer = async n => evaluate(`(() => {
      S.resp = {}; S.tierSel = null; S.result = null; S.panelOpen = null;
      for (const o of TR.order.slice(0, ${n})) S.resp[o] = 3;
      refreshAdapt(); renderTop(); renderTree(); renderStage(); renderResult();
      return {已答: Object.keys(S.resp).length, 第一环答完: ring1Done()};
    })()`);
  const select = async fi => evaluate(`(() => {
      const o = TR.tierRingNodes[0][${fi}];
      S.tierSel = {f: ${fi}, t: 1, o};
      refreshAdapt(); renderTierGraph(); renderTierPanel();
      return S.tierSel;
    })()`);
  /* 模拟「点了推荐卡片」：这是常驻区的核心路径——不点图上的圆圈也能作答 */
  const pick = async i => evaluate(`(() => {
      const list = (S.adaptList && S.adaptList.length) ? S.adaptList : recommend(6);
      const x = list[${i}];
      S.tierSel = {f: itemByOrder[x.o][1], t: tierRingOfOrder(x.o), o: x.o};
      refreshAdapt(); renderStage(); renderResult();
      return S.tierSel;
    })()`);

  // 场景名不用「第几环」——那套口径已退场（D99/D100），图里也没有环了
  const mobile = argv.includes('--mobile');
  // 文件名带上尺寸：不同手机尺寸各出一份，否则后一次会覆盖前一次（踩过）
  const tag = mobile ? `-${W}x${H}` : '';
  const scenarios = mobile ? [
    {name: `m30${tag}`, setup: 'void 0', n: 30},
    {name: `m60${tag}`, setup: 'void 0', n: 60},
    {name: `m60-picked${tag}`, setup: 'void 0', n: 60, pick: 0},
  ] : JSON.parse(arg('scenes', 'null')) || [
    {name: 's0-empty', setup: 'S.resp={};refreshAdapt();renderTop();renderTree();renderStage();'},
    {name: 's1-answered30', setup: 'void 0', n: 30},
    {name: 's2-selected', setup: 'void 0', n: 30, sel: 0},
    {name: 's3-answered60', setup: 'void 0', n: 60},
    {name: 's4-answered300', setup: 'void 0', n: 300},
    // 动态解锁的两张：45 题（窗口刚分叉）、90 题（相关性把 29 条支线推前）
    {name: 's5-answered45', setup: 'void 0', n: 45},
    {name: 's6-answered90', setup: 'void 0', n: 90},
  ];

  for (const sc of scenarios) {
    console.log(sc.name);
    // 每个场景都从干净状态开始——否则作答会累加，后一张图等于把前面的题又答一遍
    await reset();
    if (sc.setup) await evaluate(sc.setup);
    if (sc.n != null) {
      const r = await answer(sc.n);
      console.log('   ', JSON.stringify(r));
    }
    if (sc.sel != null) await select(sc.sel);
    if (sc.pick != null) console.log('    已选中推荐', JSON.stringify(await pick(sc.pick)));
    await sleep(sc.wait || 400);
    await shot(sc.name, sc.full !== false);
  }

  ws.close();
  chrome.kill();
  process.exit(0);
})().catch(e => { console.error('❌', e.message); process.exit(1); });
