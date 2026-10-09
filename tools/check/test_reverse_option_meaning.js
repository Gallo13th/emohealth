// task-45：反向题的**选项语义**必须按 key 镜像（IPIP-NEO 148/300 道反向题曾整体读反）
//
// 背景（用户原话「校对注释，怎么出现了颠倒的问题」）：
//   面向级阶梯 `scale_guides[scale_id].options[].meaning_zh` 是**按面向水平从低到高**写的
//   （来自 content/facets/<facet>.record.json 的 administration.anchor_semantics）。
//   选项 v 是「对**题面陈述**的符合程度」。反向计分题上两者镜像：
//     ipip_neo_227「Have a high opinion of myself.」key=-1；
//     v=1（非常不符合题面）⇒ 面向水平**最高**（最谦逊）→ 应取阶梯第 min+max−1 级。
//   修复前直接取第 v 级 → 整个题的语义读反。
//
// 本守卫四条（都要能红）：
//   ① **镜面对称**：同面向的正向题(221)与反向题(227)逐题渲染后，选项语义必须互为倒序，
//      且反向题每档标出 mapped_v = min+max−v、来源是 scale_guide；
//   ② **逐题锚点不许翻**：FOCI（DSM5TR-L2-Repetitive）的语义来自题自己的
//      `response.options[].meaning_zh` → 必须逐字等于原文、来源标 item；
//   ③ **锚点级不许翻**：`anchorGuideHtml()` 渲染的是数据原文（把 markdown 星号去掉后逐字包含）；
//   ④ **全部反向题**：IPIP-NEO 的 148 道反向题 × 全部档位逐题核对 = 取镜像级、
//      0 miss（不是抽查）。
const {spawn} = require('child_process');
const os = require('os'), fs = require('fs'), path = require('path');
const PORT = 9397;
const CHROME = process.env.CHROME ||
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const ROOT = path.resolve(__dirname, '..', '..');
const URL_ = process.env.URL ||
  'file:///' + path.join(ROOT, 'ui', 'index.html').replace(/\\/g, '/');
const sleep = ms => new Promise(r => setTimeout(r, ms));

let fail = 0;
const ck = (n, c, d = '') => {
  console.log(`  ${c ? '✅' : '❌'} ${n}${d ? '  —— ' + d : ''}`);
  if (!c) fail++;
};
const stripBold = s => String(s || '').split('**').join('');

(async () => {
  const prof = fs.mkdtempSync(path.join(os.tmpdir(), 'rev-'));
  const ch = spawn(CHROME, ['--headless=new', '--no-sandbox', '--disable-gpu',
    '--remote-debugging-port=' + PORT, '--user-data-dir=' + prof,
    '--window-size=1280,1000', '--allow-file-access-from-files', 'about:blank'],
    {stdio: 'ignore'});
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
      (r.result.exceptionDetails.exception?.description || '').slice(0, 300);
    return r.result?.result?.value;
  };

  /* ══ ① 镜面对称（IPIP-NEO：221 正向 / 227 反向，同面向 modesty_humility）══ */
  console.log('=== ① 镜面对称：ipip_neo_221(正向) vs ipip_neo_227(反向) ===');
  await S('Page.navigate', {url: URL_ + '#/scale/IPIP-NEO/classic'});
  await sleep(3200);
  await ev(`(async () => { for (let i = 0; i < 90; i++) {
      if (INST_NOW && INST_NOW.instrument === 'IPIP-NEO' && structIndex('IPIP-NEO')) return 1;
      await new Promise(r => setTimeout(r, 150)); } return 0; })()`);
  const pair = await ev(`(() => {
      const st = structIndex('IPIP-NEO'), rf = INST_NOW.response_format;
      const pick = id => INST_NOW.items.find(x => x.id === id);
      /* 走**渲染同一个函数**（不是另写一套取值） */
      const render = it => {
        const el = document.createElement('div');
        el.innerHTML = itemOptionsHtml(it, st.get(it.id), rf, undefined, '');
        return [...el.querySelectorAll('.opt')].map(b => {
          const om = b.querySelector('.om');
          return {v: +b.dataset.v, om: om ? om.textContent : '',
            src: om ? om.dataset.meaningSource : null,
            mv: om ? om.dataset.meaningMappedV : null};
        });
      };
      const posIt = pick('ipip_neo_221'), revIt = pick('ipip_neo_227');
      const sid = st.get('ipip_neo_227').response.scale_id;
      const g = scaleGuideOf('IPIP-NEO', sid);
      return {pos: render(posIt), rev: render(revIt),
        posKey: posIt.key, revKey: revIt.key,
        sameSid: st.get('ipip_neo_221').response.scale_id === sid,
        ladder: (g.options || []).map(o => o.meaning_zh),
        min: g.min, max: g.max}; })()`);
  if (typeof pair === 'string' && pair.startsWith('EXC:')) {
    ck('① 渲染两题选项未抛异常', false, pair.slice(0, 160));
  } else {
    console.log('    221(正向) 语义: ' + JSON.stringify(pair.pos.map(o => o.om)));
    console.log('    227(反向) 语义: ' + JSON.stringify(pair.rev.map(o => o.om)));
    ck('① 两题同属一个面向，且 221 是正向、227 是反向',
       pair.sameSid === true && pair.posKey > 0 && pair.revKey < 0,
       JSON.stringify({posKey: pair.posKey, revKey: pair.revKey, sameSid: pair.sameSid}));
    ck('① 反向题的选项语义 === 正向题的**倒序**（镜面对称）',
       JSON.stringify(pair.rev.map(o => o.om))
         === JSON.stringify(pair.pos.map(o => o.om).slice().reverse()),
       JSON.stringify({pos: pair.pos.map(o => o.om), rev: pair.rev.map(o => o.om)}));
    ck('① 反向题每档 mapped_v = min+max−v 且来源是 scale_guide',
       pair.rev.every(o => +o.mv === (pair.min + pair.max - o.v) && o.src === 'scale_guide'),
       JSON.stringify(pair.rev.map(o => o.mv)));
    ck('① 正向题不镜像（mapped_v === v，来源 scale_guide）',
       pair.pos.every(o => +o.mv === o.v && o.src === 'scale_guide'));
    ck('① 227 的 v=1 取到阶梯**最后一级**（最谦逊），不是第一级（旧行为=颠倒）',
       pair.rev[0].om === pair.ladder[pair.ladder.length - 1]
       && pair.rev[0].om !== pair.ladder[0],
       JSON.stringify({got: pair.rev[0].om, last: pair.ladder[pair.ladder.length - 1]}));
    ck('① 227 的 v=5 取到阶梯**第一级**（最不谦逊）',
       pair.rev[pair.rev.length - 1].om === pair.ladder[0]);
  }

  /* ══ ④ 全部反向题（148 道 × 全档位）逐题核对 ══ */
  console.log('\n=== ④ IPIP-NEO 全部反向题逐题逐档核对 ===');
  const all = await ev(`(() => {
      const st = structIndex('IPIP-NEO'), rf = INST_NOW.response_format;
      const rev = INST_NOW.items.filter(it => (it.key === -1) || it.reverse_keyed);
      const bad = [], miss = [];
      let checked = 0, withGuide = 0;
      for (const it of rev) {
        const s = st.get(it.id);
        const g = scaleGuideOf('IPIP-NEO', s.response.scale_id);
        const byV = new Map((g.options || []).map(o => [+o.v, o.meaning_zh]));
        if (byV.size) withGuide++;
        const lo = g.min != null ? +g.min : +rf.min;
        const hi = g.max != null ? +g.max : +rf.max;
        for (let v = lo; v <= hi; v++) {
          const r = optMeaningFor(it, s, rf, v);
          checked++;
          if (r.miss) { miss.push({id: it.id, v: v}); continue; }
          const want = byV.get(lo + hi - v);
          if (r.text !== want || r.source !== 'scale_guide' || r.mapped_v !== lo + hi - v) {
            bad.push({id: it.id, v: v, got: r.text, want: want, src: r.source});
          }
        }
      }
      return {nRev: rev.length, nAll: INST_NOW.items.length, checked: checked,
        withGuide: withGuide, badN: bad.length, bad: bad.slice(0, 3),
        missN: miss.length, miss: miss.slice(0, 3),
        globalMiss: optMeaningMisses().length}; })()`);
  console.log('    实测：', JSON.stringify(all).slice(0, 260));
  ck('④ 反向题数 = 148（占 300 的近一半）', all.nRev === 148 && all.nAll === 300,
     `${all.nRev}/${all.nAll}`);
  ck('④ 148 道反向题**全部**有面向级阶梯，且逐档都取镜像级（0 处错误）',
     all.withGuide === 148 && all.checked === 148 * 5 && all.badN === 0,
     JSON.stringify({checked: all.checked, bad: all.badN, badSample: all.bad}));
  ck('④ 没有任何一档映射失败（不静默降级）', all.missN === 0 && all.globalMiss === 0,
     JSON.stringify({miss: all.missN, renderMiss: all.globalMiss}));

  /* ══ ② 逐题锚点不许翻（FOCI：语义来自题自己的 response.options）══ */
  console.log('\n=== ② 逐题锚点（FOCI / DSM5TR-L2-Repetitive）不许翻 ===');
  await S('Page.navigate', {url: URL_ + '#/scale/DSM5TR-L2-Repetitive/classic'});
  await sleep(2800);
  const foci = await ev(`(() => {
      const st = structIndex('DSM5TR-L2-Repetitive');
      const it = INST_NOW.items[0], s = st.get(it.id), rf = INST_NOW.response_format;
      const el = document.createElement('div');
      el.innerHTML = itemOptionsHtml(it, s, rf, undefined, '');
      const g = scaleGuideOf('DSM5TR-L2-Repetitive', s.response.scale_id) || {};
      return {rendered: [...el.querySelectorAll('.opt')].map(b => {
          const om = b.querySelector('.om');
          return {v: +b.dataset.v, om: om ? om.textContent : '',
            src: om ? om.dataset.meaningSource : null,
            mv: om ? om.dataset.meaningMappedV : null};
        }),
        own: (s.response.options || []).map(o => o.meaning_zh),
        guideOpts: ((g.options) || []).length}; })()`);
  console.log('    实测：', JSON.stringify(foci).slice(0, 240));
  ck('② 本题的语义来自题自己（source=item），且逐字等于 response.options 原文',
     foci.guideOpts === 0 && foci.rendered.length === foci.own.length
     && foci.rendered.every(o => o.src === 'item' && o.om === foci.own[o.v]),
     JSON.stringify({src: foci.rendered.map(o => o.src)}));
  ck('② 来源是题自己时**不做镜像**（mapped_v === v）',
     foci.rendered.every(o => +o.mv === o.v));

  /* ══ ③ 锚点级不许翻 ══ */
  console.log('\n=== ③ 锚点级（anchorGuideHtml）不许翻 ===');
  await S('Page.navigate', {url: URL_ + '#/scale/IPIP-NEO/classic'});
  await sleep(2800);
  const anchor = await ev(`(() => {
      const st = structIndex('IPIP-NEO');
      const sid = st.get('ipip_neo_227').response.scale_id;
      const g = scaleGuideOf('IPIP-NEO', sid);
      const el = document.createElement('div');
      el.innerHTML = anchorGuideHtml('IPIP-NEO', sid);
      return {txt: el.textContent.replace(/\\s+/g, ' ').trim(),
        note: g.anchor_note_zh || '', quant: g.quantification_note_zh || '',
        ladder: (g.options || []).map(o => o.meaning_zh)}; })()`);
  const ladderIdx = anchor.ladder.map(x => String(anchor.txt).indexOf(x));
  const ladderShown = ladderIdx.every(i => i >= 0);
  const ladderAscending = ladderIdx.every((v, i) => i === 0 || v > ladderIdx[i - 1]);
  console.log('    锚点级里的阶梯顺序：', JSON.stringify(ladderIdx));
  ck('③ 锚点级渲染的是数据原文（低→高），两项都在且顺序未变',
     String(anchor.txt).indexOf(stripBold(anchor.note)) >= 0
     && String(anchor.txt).indexOf(stripBold(anchor.quant)) >= 0
     && anchor.ladder.length === 5
     && anchor.ladder[0] === '常强调自己的成绩与能力，喜欢居于显眼位置'
     && anchor.ladder[4] === '几乎总在弱化自己的作用，觉得没什么值得夸耀的',
     JSON.stringify({hasNote: String(anchor.txt).indexOf(stripBold(anchor.note)) >= 0,
       hasQuant: String(anchor.txt).indexOf(stripBold(anchor.quant)) >= 0}));
  /* 锚点级**若**展示这条阶梯，顺序必须是数据里的原顺序（低→高）；
     一旦有人把 mirror 也套到锚点级，这里立刻红。 */
  ck('③ 锚点级里的阶梯（若展示）顺序必须是原顺序、不许被镜像倒序',
     !ladderShown || ladderAscending, JSON.stringify({shown: ladderShown, idx: ladderIdx}));
  ck('③ 锚点级是**面向本身**的说明（不是按题镜像的），页面 DOM 里也只有一份',
     await ev(`document.querySelectorAll('[data-guide="anchor"]').length <= 1`));

  console.log('\n脚本报错:', errs.length ? errs.slice(0, 3) : '无');
  ck('无脚本异常', errs.length === 0);
  ws.close(); ch.kill();
  console.log(fail ? `\n❌ ${fail} 项未通过` : '\n✅ 反向题选项语义（镜像映射 + 两类不翻 + 148 题全覆盖）全部通过');
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error('❌', e.message); process.exit(1); });
