// 多量表按需加载的浏览器实测：目录是否就位、注入 <script> 后能否取到数据、
// 二次调用是否命中缓存、错误路径是否可辨识。
//
// 为什么必须用浏览器：这是「注入 script + 等 onload + 读 window」的行为，
// 静态断言看不见。file:// 与 http:// 下的差异也只有真加载才知道。
const {spawn} = require('child_process');
const os = require('os'), fs = require('fs'), path = require('path');

const PORT = 9347;
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
  const prof = fs.mkdtempSync(path.join(os.tmpdir(), 'inst-'));
  const ch = spawn(CHROME, ['--headless=new', '--no-sandbox', '--disable-gpu',
    '--remote-debugging-port=' + PORT, '--user-data-dir=' + prof,
    '--window-size=1200,900', 'about:blank'], {stdio: 'ignore'});
  let ver = null;
  for (let i = 0; i < 60 && !ver; i++) {
    try { ver = await (await fetch(`http://127.0.0.1:${PORT}/json/version`)).json(); }
    catch { await sleep(250); }
  }
  if (!ver) throw new Error('Chrome 调试端口没起来');
  const ws = new WebSocket(ver.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  let id = 0; const pend = new Map(); const errs = [];
  ws.onmessage = e => {
    const m = JSON.parse(e.data);
    if (m.id && pend.has(m.id)) { pend.get(m.id)(m); pend.delete(m.id); }
    if (m.method === 'Runtime.exceptionThrown')
      errs.push(m.params.exceptionDetails.exception?.description ||
                m.params.exceptionDetails.text);
  };
  const send = (m, p, s) => new Promise(r => { const i = ++id; pend.set(i, r);
    ws.send(JSON.stringify({id: i, method: m, params: p, sessionId: s})); });
  const t = await send('Target.createTarget', {url: 'about:blank'});
  const a = await send('Target.attachToTarget', {targetId: t.result.targetId, flatten: true});
  const S = (m, p) => send(m, p, a.result.sessionId);
  await S('Page.enable'); await S('Runtime.enable');
  await S('Page.navigate', {url: URL_});
  await sleep(2500);
  const ev = async x => {
    const r = await S('Runtime.evaluate',
      {expression: x, returnByValue: true, awaitPromise: true});
    if (r.result?.exceptionDetails)
      throw new Error(r.result.exceptionDetails.exception?.description || 'eval failed');
    return r.result?.result?.value;
  };

  console.log('=== 目录 ===');
  const cat = await ev(`({
      hasCatalog: !!window.EMOHEALTH_CATALOG,
      count: (window.EMOHEALTH_CATALOG||{}).count,
      groups: ((window.EMOHEALTH_CATALOG||{}).groups||[]).map(g=>g.label),
      instmap: Object.keys(window.EMOHEALTH_INSTMAP||{}).length,
    })`);
  ck('目录已加载', cat.hasCatalog);
  // 数量从目录本身读，避免每加一套量表就要改测试（我第一版硬编码 40，
  // 加了三册 Level 2 之后立刻失效）。
  ck('目录条目数 > 0 且与清单一致', cat.count > 0 && cat.count === cat.instmap,
     `${cat.count} 套`);

  console.log('\n=== 首次按需加载某套量表 ===');
  const first = await ev(`(async () => {
      const t0 = performance.now();
      const d = await loadInstrument('PID-5');
      return {ms: Math.round(performance.now()-t0), items: d.items.length,
              dims: d.dimensions.length, name: d.display_name,
              license: d.license.kind,
              cached: INST_CACHE.has('PID-5')};
    })()`);
  ck('PID-5 加载成功', first.items === 220, `${first.items} 题 / ${first.dims} 维度`);
  ck('数据包带授权字段（界面要能显示来源）', first.license === 'copyright_permitted',
     first.license);
  ck('加载后进入缓存', first.cached === true, `${first.ms} ms`);

  console.log('\n=== 二次加载（应命中缓存、不再发请求）===');
  const second = await ev(`(async () => {
      const t0 = performance.now();
      await loadInstrument('PID-5');
      return Math.round(performance.now()-t0);
    })()`);
  ck('二次加载明显更快（缓存生效）', second <= first.ms,
     `首次 ${first.ms} ms，二次 ${second} ms`);

  console.log('\n=== 加载另一套（互不干扰）===');
  const other = await ev(`(async () => {
      const d = await loadInstrument('DSM5TR-L2-Anger');
      return {items: d.items.length, dims: d.dimensions.length,
              total: INST_CACHE.size};
    })()`);
  ck('DSM5TR-L2-Anger 加载成功', other.items === 5, `${other.items} 题`);
  ck('两套都在缓存里', other.total === 2, String(other.total));

  console.log('\n=== 授权与来源（界面直接显示；目录只留标签，完整版在数据包里）===');
  const ent = await ev(`(async () => {
      const e = catalogEntry('PID-5');
      const d = await loadInstrument('PID-5');
      const lic = d.license;
      return {label: e.license.label, kind: e.license.kind,
              holder: lic.holder, evidence: (lic.evidence || '').slice(0, 60),
              text: (lic.text || '').slice(0, 50),
              items: e.items, sample: e.preview_dimensions || null};
    })()`);
  ck('目录条目含授权标签', !!ent.label, ent.label);
  ck('数据包含权利人与证据（溯源链完整）',
     !!ent.holder && !!ent.evidence, `${ent.holder}｜${ent.evidence}`);
  ck('数据包含授权原文', (ent.text || '').length > 10, ent.text);
  ck('目录条目含题数与授权类别', ent.items === 220 && !!ent.kind,
     `${ent.items} 题 / ${ent.kind}`);

  console.log('\n=== 错误路径可辨识 ===');
  const missing = await ev(`(async () => {
      try { await loadInstrument('NOT-A-SCALE'); return 'no-error'; }
      catch (e) { return e.message; }
    })()`);
  ck('请求不存在的量表会给出明确错误', /没有量表/.test(missing), missing.slice(0, 50));

  /* ── 界面流程：切换到题库模式 → 选量表 → 分页作答 → 看结果 ──────────
     这一段验证的是**用户真正会走的路径**，而不是加载函数本身。 */
  console.log('\n=== 界面流程：进题库模式 ===');
  const enter = await ev(`(() => {
      const b = document.querySelector('#modes button[data-m="inst"]');
      if (!b) return {err: '找不到题库模式按钮'};
      b.click();
      return {mode: S.mode, top: document.getElementById('topmeta').textContent.slice(0,60),
              cards: document.querySelectorAll('.instcard').length,
              groups: document.querySelectorAll('.instgroup').length};
    })()`);
  ck('能切到题库模式', enter.mode === 'inst', String(enter.mode));
  ck('选择器列出全部量表', enter.cards === cat.count,
     `${enter.cards} 张卡片 / 目录 ${cat.count} 套`);
  ck('按分组呈现', enter.groups >= 1, String(enter.groups));

  console.log('\n=== 界面流程：选一套量表 ===');
  const pick = await ev(`(() => {
      const c = [...document.querySelectorAll('.instcard')]
        .find(x => x.dataset.inst === 'DSM5TR-L2-Anger');
      if (!c) return {err: '找不到 Angre 卡片'};
      c.click();
      return {code: S.instCode};
    })()`);
  // 选卡后会异步加载数据包，等一会儿
  await sleep(1200);
  const staged = await ev(`({
      code: S.instCode,
      items: document.querySelectorAll('.institem').length,
      hasScoreShown: /\d+\\.\\d\\d/.test(document.getElementById('stage').textContent),
      pageLabel: (document.querySelector('.nqhead b')||{}).textContent || '',
      top: document.getElementById('topmeta').textContent.slice(0,80),
    })`);
  ck('进入该量表并分页显示', staged.items === 5,
     `第 1 页 ${staged.items} 题（该量表共 5 题）`);
  ck('答题中不显示分值（硬规则 ④）', staged.hasScoreShown === false);
  // 改成子页布局后，授权显示在**子页底部**（不再重复在顶部）。
  // 断言的对象也要跟着走，否则测的是已经不存在的旧布局。
  const licenceShown = await ev(`/授权/.test(document.getElementById('stage').textContent)`);
  ck('子页显示该量表的授权', licenceShown === true);

  console.log('\n=== 界面流程：作答与翻页 ===');
  /* 逐步重新查询 DOM：每次点击后重新取节点，避免用到已脱离文档的旧引用
     （我第一版遍历的是固定节点列表，只记录到 1 题——那是测试写法的问题，
     但它顺带暴露了一个真实缺陷：整块重绘会让后续点击落到失效节点上）。 */
  const answer = await ev(`(() => {
      const items = document.querySelectorAll('.institem');
      const before = items[0];
      for (let i = 0; i < items.length; i++) {
        const li = document.querySelectorAll('.institem')[i];
        const first = li && li.querySelector('.opt');
        if (first) first.click();
      }
      const after = document.querySelectorAll('.institem')[0];
      return {answered: Object.keys(S.instResp).length,
              sel: document.querySelectorAll('.institem .opt.sel').length,
              // 同一个节点对象仍在文档里 → 说明没有整块重绘
              sameNode: before === after && document.contains(after)};
    })()`);
  ck('作答被记录', answer.answered === 5, `${answer.answered} 题`);
  ck('选中态正确回显', answer.sel === 5, `${answer.sel} 个选中`);
  ck('作答时不做整块重绘（节点保持、滚动位置不丢）',
     answer.sameNode === true, answer.sameNode ? '同一节点仍在文档中' : '节点被替换了');

  console.log('\n=== 界面流程：看结果 ===');
  const res = await ev(`(() => {
      const b = document.querySelector('[data-instdone]');
      if (!b) return {err: '找不到「看结果」按钮'};
      if (b.disabled) return {err: '按钮仍禁用（作答没被算进进度）'};
      b.click();
      const rows = [...document.querySelectorAll('.insttable tbody tr')];
      return {rows: rows.length,
              first: rows[0] ? rows[0].textContent.replace(/\s+/g,' ').trim().slice(0,60) : '',
              hasLicense: /授权/.test(document.getElementById('stage').textContent),
              hasCitation: /引用/.test(document.getElementById('stage').textContent),
              body: document.getElementById('stage').textContent.replace(/\s+/g,' ')};
    })()`);
  /* L2-Anger 属「待补 T 分」册：手册要求原始分经 T 分转换表解读，
     项目无转换表 → 结果页明示缺口，不渲染分数表（不编造数字）。
     分数表行为由 test_l2_criteria_ui.js 的分界/分带册覆盖。 */
  ck('L2 结果明示 T 分转换缺口（不渲染未经依据的分数表）',
     /T 分/.test(res.body) && res.rows === 0, `${res.rows} 行`);
  ck('结果区显示授权', res.hasLicense === true);
  ck('结果区显示引用（每个数字可追到出处）', res.hasCitation === true);

  console.log('\n=== 计分口径与 Python 引擎一致（抽样核对）===');
  const cross = await ev(`(async () => {
      // 用与 Python 相同的输入算一次：全答该量表最小值
      const d = INST_CACHE.get('DSM5TR-L2-Anger');
      const resp = {};
      for (const it of d.items) resp[it.id] = d.response_format.min;
      const rows = instScores(d, resp);
      const bs = rows.find(r => r.id === 'l2_anger');
      return {value: bs ? bs.value : null, n: bs ? bs.n_items : null,
              agg: (d.scoring['l2_anger']||{}).aggregation};
    })()`);
  // 5 题、0 反向、求和、全答 1 → 5
  ck('全答最小值时：5 题求和 = 5', cross.value === 5,
     `得到 ${cross.value}（${cross.agg}，${cross.n} 题）`);

  console.log('\n=== 每题独立选项的量表（Mania：5 组 × 5 句陈述）===');
  const mania = await ev(`(async () => {
      document.querySelector('[data-instback]').click();
      const c = [...document.querySelectorAll('.instcard')]
        .find(x => x.dataset.inst === 'DSM5TR-L2-Mania');
      if (!c) return {err: '选择器里没有 Mania'};
      c.click();
      await new Promise(r => setTimeout(r, 1200));
      const items = document.querySelectorAll('.institem');
      const opts0 = items[0] ? [...items[0].querySelectorAll('.opt')] : [];
      return {groups: items.length, opts: opts0.length,
              longLayout: !!document.querySelector('.longopts'),
              firstText: opts0[0] ? opts0[0].textContent.trim().slice(0, 40) : '',
              // 选项里应带着整句陈述，而不是只有数字
              hasSentenceText: opts0.length > 0 &&
                opts0[0].textContent.replace(/^\d+/, '').trim().length > 16,
              noScoresShown: !/\d+\\.\\d\\d/.test(
                document.getElementById('stage').textContent)};
    })()`);
  ck('Mania 5 组都渲染出来', mania.groups === 5, `${mania.groups} 组`);
  ck('每组 5 个选项', mania.opts === 5, `${mania.opts} 个`);
  ck('长选项用竖排布局（不是数字按钮）', mania.longLayout === true);
  ck('选项带整句陈述文本', mania.hasSentenceText === true, mania.firstText);
  ck('Mania 答题中也不显示分值', mania.noScoresShown === true);

  console.log('\n脚本报错:', errs.length ? errs.slice(0, 2) : '无');
  ck('无脚本异常', errs.length === 0);

  ws.close(); ch.kill();
  console.log(fail ? `\n❌ ${fail} 项未通过` : '\n✅ 多量表按需加载全部通过');
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error('❌', e.message); process.exit(1); });
