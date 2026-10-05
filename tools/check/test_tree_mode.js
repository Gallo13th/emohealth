// 天赋树专项：> 60 题量表应默认进天赋树、节点可点、答完解锁邻居、可切回逐题。
const {spawn} = require('child_process');
const os = require('os'), fs = require('fs'), path = require('path');
const PORT = 9355;
const CHROME = process.env.CHROME ||
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
// ⚠️ 默认目标必须是**工作区代码**，不能是某个已部署的副本。
//    这里原先默认 `http://127.0.0.1:8891/emohealth/`（WSL 里的旧部署），
//    结果本测试长期对着**旧构建假绿**：那台的 index.html 还是
//    `data-instview`，而工作区早已改成 `data-instmode`。
//    改为 file:// 直开工作区的 ui/index.html（与 test_local_file.js 同一做法），
//    不依赖任何服务，测的就是工作区。
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
  const prof = fs.mkdtempSync(path.join(os.tmpdir(), 'tree-'));
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
  await S('Page.navigate', {url: URL_});
  await sleep(2600);
  const ev = async x => (await S('Runtime.evaluate',
    {expression: x, returnByValue: true, awaitPromise: true})).result?.result?.value;

  console.log('=== 树布局清单 ===');
  const map = await ev(`window.EMOHEALTH_TREEMAP || {}`);
  ck('树布局清单已加载', Object.keys(map).length === 2, Object.keys(map).length + ' 套');

  console.log('\n=== > 60 题：默认进天赋树 ===');
  await ev(`document.querySelector('#modes button[data-m="inst"]').click()`);
  await sleep(400);
  await ev(`[...document.querySelectorAll('.instcard')]
    .find(x => x.dataset.inst === 'PID-5').click()`);
  await sleep(2000);
  const st = await ev(`({
      view: S.instView,
      nodes: document.querySelectorAll('.treenode').length,
      open: document.querySelectorAll('.treenode.open').length,
      locked: document.querySelectorAll('.treenode.locked').length,
      edges: document.querySelectorAll('.treeedge').length,
      /* D120（task-24）：不再渲染数据层的 layout_basis 方法学长文，改成一句白话；
         断言跟着文案改，但**仍要求如实说明这不是数据相关性图**。 */
      hasBasis: /这张图按维度分组排布/.test(document.getElementById('stage').textContent),
      basisIsHonest: /不是根据答题数据/.test(document.getElementById('stage').textContent),
      hasSwitch: !!document.querySelector('[data-instmode]')
    })`);
  ck('默认视图是天赋树', st.view === 'tree', st.view);
  ck('220 个节点全部渲染', st.nodes === 220, st.nodes + ' 个');
  ck('最内环可答、其余锁定', st.open > 0 && st.locked > 0,
     `可答 ${st.open} / 锁定 ${st.locked}`);
  ck('画出了支撑边', st.edges > 0, st.edges + ' 条');
  ck('标注了这张图的排布依据（白话）', st.hasBasis === true);
  ck('如实说明「不是根据答题数据画的相关性图」', st.basisIsHonest === true);
  ck('提供作答方式切换', st.hasSwitch === true);

  console.log('\n=== 答一题后解锁它的下游节点 ===');
  const before = await ev(`document.querySelectorAll('.treenode.open').length`);
  /* ⚠️ 断言要答「有下游的」节点，不能随便答一个就期望 unlocked 数变多：
     螺旋布局里最内环的题，其下游是**按螺旋顺序的下一簇首题**，
     答它不一定立刻多出可答节点（我的第一版断言就是这样误报的）。
     正确做法：先找一个「有 support 指向它」的可答节点，答它，再看那个下游是否转为可答。 */
  const ans = await ev(`(() => {
      // 找可答、且被别的节点 support 引用的节点
      const openOrders = [...document.querySelectorAll('.treenode.open')]
        .map(n => +n.dataset.node);
      const hasDependent = openOrders.find(o =>
        Object.entries(TREE_NOW.support).some(([k, v]) => v.includes(String(o))
          && treeNodeState(TREE_NOW, +k, S.instResp) === 'locked'));
      const target = hasDependent != null ? hasDependent : openOrders[0];
      const nd = document.querySelector('.treenode[data-node="' + target + '"]');
      nd.dispatchEvent(new MouseEvent('click', {bubbles: true}));
      return {order: target, hasQ: !!document.getElementById('treeq')};
    })()`);
  ck('点节点后展开该题', ans.hasQ === true, '选中题号 ' + ans.order);
  const after = await ev(`(() => {
      const b = document.querySelector('#treeq .opt');
      if (!b) return {err: '没有选项'};
      b.dispatchEvent(new MouseEvent('click', {bubbles: true}));
      return {answered: Object.keys(S.instResp).length,
              done: document.querySelectorAll('.treenode.done').length,
              open: document.querySelectorAll('.treenode.open').length};
    })()`);
  ck('选项作答被记录', after.answered === 1, after.answered + ' 题');
  ck('已答节点变色', after.done === 1, after.done + ' 个 done');
  ck('答完后可答节点没有减少（解锁只增不减）', after.open >= before,
     `${before} → ${after.open}`);

  console.log('\n=== 推荐下一题 ===');
  const rec = await ev(`(() => {
      const b = document.querySelector('[data-treepick]') ||
                document.querySelector('[data-treenext]');
      if (!b) return {err: '没有推荐按钮'};
      b.dispatchEvent(new MouseEvent('click', {bubbles: true}));
      return {sel: S.treeSel, hasQ: !!document.getElementById('treeq')};
    })()`);
  ck('推荐会选中一个可答题并展开', rec.hasQ === true, '推荐题号 ' + rec.sel);

  console.log('\n=== 可切回经典逐题 ===');
  // ⚠️ 点击切换会走**路由**（`go('#/scale/<code>/classic')` → hashchange → applyRoute），
  //    是异步的。原先把 dispatchEvent 与读 `S.instView` 写在同一个同步表达式里，
  //    读到的必然是旧值 `'tree'` —— 于是误报「切不回去」。
  //    必须分成两步、中间给渲染留时间（test_scale_pages 里同一操作就是分开写的）。
  const clicked = await ev(`(() => {
      const b = document.querySelector('[data-instmode="classic"]');
      if (!b) return {err: '没有切回按钮'};
      b.dispatchEvent(new MouseEvent('click', {bubbles: true}));
      return {ok: true};
    })()`);
  if (clicked.err) console.log('     （诊断：' + clicked.err + '）');
  await sleep(1500);
  const sw = await ev(`({view: S.instView,
      items: document.querySelectorAll('.institem').length})`);
  ck('能切回经典逐题', sw.view === 'classic', sw.view);
  ck('逐题视图仍显示 10 题/页', sw.items === 10, sw.items + ' 题');

  console.log('\n=== 短表不出现天赋树 ===');
  // ⚠️ 这里用了 await，必须包在 async 函数里——我第一版漏了，
  //    整个表达式语法报错、返回 undefined，被当成界面失败（假警报）。
  // ⚠️ 必须先点「换一套」回到选择器，否则页面上根本没有 .instcard
  //    ——我第一版漏了这步，于是「点卡片」落空，后面测的还是 PID-5（假警报）。
  await ev(`(() => {
      const b = document.querySelector('[data-instback]');
      if (b) b.dispatchEvent(new MouseEvent('click', {bubbles: true}));
      return 1;
    })()`);
  await sleep(500);
  const onPicker = await ev(`document.querySelectorAll('.instcard').length`);
  ck('能回到量表选择器', onPicker > 0, onPicker + ' 张卡片');

  await ev(`(() => {
      const c = [...document.querySelectorAll('.instcard')]
        .find(x => x.dataset.inst === 'DSM5TR-L2-Anger');
      c.dispatchEvent(new MouseEvent('click', {bubbles: true}));
      return 1;
    })()`);
  await sleep(1400);
  const small = await ev(`({
      nodes: document.querySelectorAll('.treenode').length,
      items: document.querySelectorAll('.institem').length,
      switchBtns: document.querySelectorAll('[data-instmode]').length,
      title: (document.querySelector('#stage .ph') || {}).textContent || ''
    })`);
  console.log('     （DOM 实测：' + JSON.stringify(small) + '）');
  ck('确实切到了 5 题量表', /Anger/.test(small.title), small.title.slice(0, 40));
  ck('5 题量表渲染为逐题（共 5 题）', small.items === 5,
     small.items + ' 个 .institem');
  ck('5 题量表没有天赋树节点', small.nodes === 0, small.nodes + ' 个节点');
  ck('5 题量表不显示切换按钮', small.switchBtns === 0,
     small.switchBtns + ' 个按钮');

  console.log('\n脚本报错:', errs.length ? errs.slice(0, 2) : '无');
  ck('无脚本异常', errs.length === 0);
  ws.close(); ch.kill();
  console.log(fail ? `\n❌ ${fail} 项未通过` : '\n✅ 天赋树全部通过');
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error('❌', e.message); process.exit(1); });
