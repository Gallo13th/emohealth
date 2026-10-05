// 移动端布局门：用真实浏览器量**渲染后的几何**，断言当前界面（最小 UI + 题面四字段
// + 预测面板 + 天赋树解锁）在窄屏上的几条体验约束。
//
// 为什么必须用浏览器：这些是 CSS 布局的结果，stub DOM 与静态断言都看不见。
// 本仓库因此踩过两次坑：「图被卡在 300×300」、以及「常驻条把作答区推到折叠线以下」——
// 都只有量出来的数字才说明问题。
//
// ⚠️ 历史（2026-10-04，D116/D117）：本脚本原先量的是**分级模式**的几何
//    （`#graphbox svg` / `#nextq` 常驻条 / `S.tierSel` / `refreshAdapt` / `renderTree`）。
//    那套界面已按用户要求撤下，脚本随之报 `ReferenceError: refreshAdapt is not defined`
//    ——「总是红的检查」和「假绿」是同一种病。现在**改指到现有的渲染入口**：
//      · 天赋树：`renderInstTree()` → `.treewrap svg.treesvg`（环/簇/支撑边/节点）
//      · 经典逐题：`renderInstStage()` → `.institems > li .opt`
//      · 预测面板：`renderInferencePanel()` → `.infpanel`（`max-height` 上限是硬约束）
//    被测的仍是同一类不变量：**不横向裁切**、**图不被卡死**、**面板不许把作答区推走**、
//    **窄屏上真的能作答**。
//
// 用法：
//   node tools/check/check_mobile_layout.js             # 三档屏宽实测
//   node tools/check/check_mobile_layout.js --selftest  # 故意破坏（图卡 300 / 面板不限高）
//                                                      # 必须**失败**才说明本检查不是假绿
const {spawn} = require('child_process');
const os = require('os'), fs = require('fs'), path = require('path');

const PORT = 9345;
const CHROME = process.env.CHROME ||
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const ROOT_ = path.resolve(__dirname, '..', '..');
// ⚠️ 默认必须指向**工作区**，不能是某个部署副本——否则会对着旧构建**假绿**。
//    file:// 直开不依赖任何服务，测的就是工作区。
const URL_ = process.env.URL ||
  'file:///' + path.join(ROOT_, 'ui', 'index.html').replace(/\\/g, '/');
/* D121（task-32）：把最窄档压到 320 —— 情景块（.scene）与选项在极窄屏也不能横向溢出。
   保留原有 360/390/414 档，做到「320/375/414 都有实测」。 */
const SIZES = [[320, 568], [375, 667], [360, 640], [390, 844], [414, 896]];
const SELFTEST = process.argv.includes('--selftest');
const sleep = ms => new Promise(r => setTimeout(r, ms));

let fail = 0;
const ck = (n, c, d = '') => {
  console.log(`  ${c ? '✅' : '❌'} ${n}${d ? '  —— ' + d : ''}`);
  if (!c) fail++;
};

const GEO = `(() => {
  const de = document.documentElement;
  const stage = document.getElementById('stage');
  const svg = document.querySelector('.treesvg');
  const wrap = document.querySelector('.treewrap');
  const ip = document.querySelector('.infpanel');
  const firstItem = document.querySelector('.institem');
  const opts = firstItem ? [...firstItem.querySelectorAll('.opt')] : [];
  const rect = el => { const r = el.getBoundingClientRect();
    return {w: +r.width.toFixed(1), h: +r.height.toFixed(1),
            top: +r.top.toFixed(1), right: +r.right.toFixed(1)}; };
  return {
    vw: innerWidth, vh: innerHeight,
    docScrollW: de.scrollWidth,
    stage: stage ? {...rect(stage), scrollW: stage.scrollWidth, clientW: stage.clientWidth} : null,
    svg: svg ? {...rect(svg), nodes: svg.querySelectorAll('.treenode').length,
                ready: svg.querySelectorAll('.treenode.ready').length,
                done: svg.querySelectorAll('.treenode.done').length,
                locked: svg.querySelectorAll('.treenode.locked').length} : null,
    wrap: wrap ? rect(wrap) : null,
    infpanel: ip ? {...rect(ip), scrollH: ip.scrollHeight,
                    overflowY: getComputedStyle(ip).overflowY} : null,
    first: firstItem ? {...rect(firstItem), opts: opts.length,
      optsRight: opts.length ? +Math.max(...opts.map(o => o.getBoundingClientRect().right)).toFixed(1) : null,
      optsLeft: opts.length ? +Math.min(...opts.map(o => o.getBoundingClientRect().left)).toFixed(1) : null,
      optsVisible: opts.filter(o => { const b = o.getBoundingClientRect();
        return b.top >= 0 && b.bottom <= innerHeight + 1; }).length} : null,
    /* D121（task-32）：情景块（.scene，schema 2.1 每题必填）的几何——
       窄屏上不能横向溢出、不能与选项挤在一起。 */
    scene: (() => {
      const s = firstItem ? firstItem.querySelector('[data-f="scenario_zh"]') : null;
      if (!s) return {found: false};
      const r = s.getBoundingClientRect();
      const o = firstItem.querySelector('.opts');
      const or = o ? o.getBoundingClientRect() : null;
      const cs = getComputedStyle(s);
      return {found: true, left: +r.left.toFixed(1), right: +r.right.toFixed(1),
        gapToOpts: or ? +(or.top - r.bottom).toFixed(1) : null,
        visible: s.getClientRects().length > 0 && cs.display !== 'none',
        borderLeft: parseFloat(cs.borderLeftWidth) || 0,
        inFold: !!s.closest('details'),
        cjk: (s.textContent.match(/[\u4e00-\u9fff]/g) || []).length};
    })(),
  };
})()`;

(async () => {
  const prof = fs.mkdtempSync(path.join(os.tmpdir(), 'mlay-'));
  const ch = spawn(CHROME, ['--headless=new', '--no-sandbox', '--disable-gpu',
    '--no-first-run', '--remote-debugging-port=' + PORT, '--user-data-dir=' + prof,
    '--window-size=390,844', 'about:blank'], {stdio: 'ignore'});
  let ver = null;
  for (let i = 0; i < 60 && !ver; i++) {
    try { ver = await (await fetch(`http://127.0.0.1:${PORT}/json/version`)).json(); }
    catch { await sleep(250); }
  }
  if (!ver) { ch.kill(); throw new Error('Chrome 调试端口没起来'); }
  const ws = new WebSocket(ver.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
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
    if (r.result?.exceptionDetails)
      throw new Error(r.result.exceptionDetails.exception?.description || 'eval failed');
    return r.result?.result?.value;
  };

  /* 按尺寸整页重载：`setDeviceMetricsOverride` 之后必须**换文档**再量，
     否则会量到上一档宽度的旧布局（实测踩过：360 档量出 372px 的卡片）。 */
  const load = async (hash, wait = 3000) => {
    await S('Page.navigate', {url: 'about:blank'});
    await sleep(150);
    await S('Page.navigate', {url: URL_ + hash});
    await sleep(wait);
  };
  const readyPid5 = async () => ev(`(async () => {
      for (let i = 0; i < 80; i++) {
        if (window.EMOHEALTH_STRUCT_PID_5 && document.querySelector('.infpanel[data-display="ok"]'))
          return true;
        await new Promise(r => setTimeout(r, 150));
      }
      return false;
    })()`);
  // 答该量表第一个维度的 4 题（让面板/解锁/推荐都有内容）
  const seed = () => ev(`(() => {
      const d = INST_NOW; const dim0 = d.dimensions[0];
      S.instResp = {}; S.ansVer++;
      dim0.items.slice(0, 4).forEach((id, i) => { S.instResp[id] = i % 4; });
      S.treeSel = null; S.ansVer++;
      if (${SELFTEST}) {
        const st = document.createElement('style');
        st.textContent = '.treesvg{width:300px!important;height:300px!important}'
          + '.infpanel{max-height:none!important;overflow:visible!important}';
        document.head.appendChild(st);
      }
      renderTop(); renderStage();
      return 1;
    })()`);

  const svgWidths = [];
  for (const [W, H] of SIZES) {
    await S('Emulation.setDeviceMetricsOverride',
      {width: W, height: H, deviceScaleFactor: 1, mobile: true});
    console.log(`\n=== ${W}×${H} ===`);

    // ── ① 天赋树 ──
    await load('#/scale/PID-5/tree');
    const okTree = await readyPid5();
    ck('天赋树页的按需数据就位（面板可用）', okTree === true);
    await seed();
    await sleep(600);
    const g = await ev(GEO);
    if (typeof g === 'string') throw new Error(g);
    const cardW = g.stage.w;
    console.log(`    图 ${g.svg.w}×${g.svg.h} 节点 ${g.svg.nodes}（已解锁 ${g.svg.ready}）`
      + ` 面板高 ${g.infpanel.h} 首题 ${g.first ? g.first.top : '—'}`);
    ck('① 无横向裁切（文档/卡片/SVG 都在视口内）',
       g.docScrollW <= g.vw + 1 && g.stage.scrollW <= g.stage.clientW + 1
       && g.svg.right <= g.vw + 1,
       `doc ${g.docScrollW}/${g.vw} · stage ${g.stage.scrollW}/${g.stage.clientW} · svg right ${g.svg.right}`);
    ck('② 天赋树图按卡片宽展开（没有被卡死在固定尺寸）',
       g.svg.w > 0.85 * cardW, `图 ${g.svg.w} vs 卡片 ${cardW}`);
    ck('③ 图保持布局比例（viewBox 720×620，容差 3%）',
       Math.abs(g.svg.h / g.svg.w - 620 / 720) < 0.03,
       `${(g.svg.h / g.svg.w).toFixed(3)} vs ${(620 / 720).toFixed(3)}`);
    ck('④ 节点全部渲染且解锁状态可见（ready 类 > 0）',
       g.svg.nodes === 220 && g.svg.ready > 0,
       `${g.svg.nodes} 节点 / ${g.svg.ready} 已解锁`);
    ck('⑤ 预测面板有高度上限（≤ 屏高一半），不把图推走',
       g.infpanel.h <= Math.max(0.5 * g.vh, 320) + 8,
       `面板 ${g.infpanel.h}px / 上限 ${Math.round(Math.max(0.5 * g.vh, 320))}px`);
    ck('⑥ 图在「面板 + 推荐」之后仍能在 2.5 屏内到达',
       g.wrap.top <= 2.5 * g.vh, `图顶端 ${g.wrap.top} vs ${Math.round(2.5 * g.vh)}`);
    svgWidths.push(g.svg.w);

    // ── ② 经典逐题：窄屏上真的能作答 ──
    await load('#/scale/PID-5/classic');
    await readyPid5();
    await seed();
    await sleep(500);
    const c = await ev(GEO);
    const tap = await ev(`(() => {
        const li = document.querySelector('.institem[data-item]');
        const opt = li && li.querySelector('.opt');
        if (!opt) return {err: 'no option'};
        opt.dispatchEvent(new MouseEvent('click', {bubbles: true}));
        return {id: li.dataset.item, v: +opt.dataset.v,
                recorded: S.instResp[li.dataset.item]};
      })()`);
    console.log(`    首题 top ${c.first.top} 选项 ${c.first.opts} 个`
      + `（右边界 ${c.first.optsRight} / 视口 ${c.vw}）`)
    ck('⑦ 无横向裁切（文档/卡片/首题选项都在视口内）',
       c.docScrollW <= c.vw + 1 && c.stage.scrollW <= c.stage.clientW + 1
       && c.first.optsRight <= c.vw + 1 && c.first.optsLeft >= -1,
       `doc ${c.docScrollW}/${c.vw} · 选项 ${c.first.optsLeft}–${c.first.optsRight}`);
    ck('⑧ 面板有高度上限，首题在 2.5 屏内到达',
       c.infpanel.h <= Math.max(0.5 * c.vh, 320) + 8 && c.first.top <= 2.5 * c.vh,
       `面板 ${c.infpanel.h} · 首题 ${c.first.top} vs ${Math.round(2.5 * c.vh)}`);
    ck('⑨ 窄屏上点选项能记录作答',
       tap.recorded === tap.v, JSON.stringify(tap));
    /* D121（task-32）：情景块必须**默认可见**、不溢出、有左侧色条、不与选项挤在一起 */
    ck('⑩ 情景块渲染且默认可见（无折叠），文本 ≥20 汉字',
       c.scene.found === true && c.scene.visible === true && c.scene.inFold === false
       && c.scene.cjk >= 20,
       JSON.stringify({found: c.scene.found, visible: c.scene.visible,
         inFold: c.scene.inFold, 汉字: c.scene.cjk}));
    ck('⑪ 情景块不横向溢出、与选项之间留有空隙，且有左侧色条',
       c.scene.found === true && c.scene.right <= c.vw + 1 && c.scene.left >= -1
       && c.docScrollW <= c.vw + 1
       && (c.scene.gapToOpts == null ? false : c.scene.gapToOpts >= 0)
       && c.scene.borderLeft >= 2,
       JSON.stringify({right: c.scene.right, vw: c.vw, gap: c.scene.gapToOpts,
         borderLeft: c.scene.borderLeft}));
  }

  console.log('\n=== 图随屏幕变大（不是写死的尺寸）===');
  const uniq = new Set(svgWidths.map(v => Math.round(v / 5)));
  ck('各档屏宽下图宽不同（不是写死的尺寸）', uniq.size > 1, svgWidths.join(' / '));

  ws.close(); ch.kill();
  if (SELFTEST) {
    // 自检模式：注入了「图卡 300 + 面板不限高」，**必须**出现失败才算检查有效
    console.log(fail ? `\n✅ 自检通过：故意破坏后检查确实报错（${fail} 项未通过）`
                     : '\n❌ 自检失败：故意破坏后检查仍全绿 —— 这是个假绿检查！');
    process.exit(fail ? 0 : 1);
  }
  console.log(fail ? `\n❌ ${fail} 项未通过` : '\n✅ 移动端布局全部通过');
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error('❌', e.message); process.exit(2); });
