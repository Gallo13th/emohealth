// 答题界面（D117）两条：**题面四字段** 与 **各指标预测 + 置信度**。
//
// 这条测试钉住四件事（对应用户与 Lead 的验收）：
//   ① 一道题的 DOM 里能**同时**取到结构化文本的四部分：
//      `text_en` / `text_zh` / `response.options[].meaning_zh` / `notes_zh`
//      —— 并且内容与 `ui/items-structured/<code>.js` 逐字段一致（不是占位/混排）。
//   ② **硬规则**：本维度一道题都没答时，页面上**不出现**该维度的预测与置信度
//      （连 `data-r` 都没有），只给原因；而且**别的维度答了多少都不放行**。
//   ③ 已答时出现的数值与**直接调用 `ui/lib/inference.js`** 的结果逐值一致。
//   ④ **按需加载没被破坏**：首页不加载 `ui/inference/*.js` 数据包、
//      不加载 `ui/items-structured/*.js`、也不加载 `lib/inference.js`；
//      更没有 `EMOHEALTH_INFER_*` 数据全局。
//
// file:// 直开工作区（不指向任何已部署副本）。
const {spawn} = require('child_process');
const os = require('os'), fs = require('fs'), path = require('path');
const PORT = 9418;
const CHROME = process.env.CHROME ||
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const sleep = ms => new Promise(r => setTimeout(r, ms));
const ROOT = path.resolve(__dirname, '..', '..');
const URL_ = process.env.URL ||
  'file:///' + path.join(ROOT, 'ui', 'index.html').replace(/\\/g, '/');

let fail = 0;
const ck = (n, c, d = '') => {
  console.log(`  ${c ? '✅' : '❌'} ${n}${d ? '  —— ' + d : ''}`);
  if (!c) fail++;
};
// 界面用 `md()` 把 **强调** 渲染成 <b>，textContent 里星号消失——比较前先归一
const norm = s => String(s == null ? '' : s).replace(/\*\*/g, '').replace(/\s+/g, ' ').trim();

(async () => {
  const prof = fs.mkdtempSync(path.join(os.tmpdir(), 'uifields-'));
  const ch = spawn(CHROME, ['--headless=new', '--no-sandbox', '--disable-gpu',
    '--remote-debugging-port=' + PORT, '--user-data-dir=' + prof,
    '--window-size=1280,1400', '--allow-file-access-from-files', 'about:blank'],
    {stdio: 'ignore'});
  let ver = null;
  for (let i = 0; i < 60 && !ver; i++) {
    try { ver = await (await fetch(`http://127.0.0.1:${PORT}/json/version`)).json(); }
    catch { await sleep(250); }
  }
  const ws = new WebSocket(ver.webSocketDebuggerUrl);
  await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; });
  let id = 0; const pend = new Map(); const errs = [];
  ws.onmessage = e => {
    const m = JSON.parse(e.data);
    if (m.id && pend.has(m.id)) { pend.get(m.id)(m); pend.delete(m.id); }
    if (m.method === 'Runtime.exceptionThrown')
      errs.push(m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text);
  };
  const send = (m, p, s) => new Promise(r => {
    const i = ++id; pend.set(i, r);
    ws.send(JSON.stringify({id: i, method: m, params: p, sessionId: s}));
  });
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
  const nav = async u => { await S('Page.navigate', {url: u}); await sleep(3000); };
  // 等到某套量表的按需数据与面板都就位
  const waitReady = async code => ev(`(async () => {
      for (let i = 0; i < 80; i++) {
        if (window.EMOHEALTH_STRUCT_${code.replace(/[^A-Za-z0-9]/g, '_').toUpperCase()}
            && document.querySelector('.infpanel[data-display="ok"]')) return true;
        await new Promise(r => setTimeout(r, 150));
      }
      return false;
    })()`);

  /* ══ ④ 首页：按需加载没被破坏 ══ */
  console.log('=== ④ 首页：不加载任何按需数据包 ===');
  await nav(URL_);
  const home = await ev(`({
      inferGlobals: Object.keys(window).filter(k => /^EMOHEALTH_INFER_(IPIP|PID)/.test(k)),
      inferMap: typeof window.EMOHEALTH_INFERMAP,
      structMap: typeof window.EMOHEALTH_STRUCTMAP,
      lib: typeof window.EmoHealthInference,
      dataScripts: [...document.scripts].map(s => s.src)
        .filter(u => /(inference|items-structured)\\//.test(u)).length,
      dataRes: (performance.getEntriesByType('resource') || []).map(e => e.name)
        .filter(u => /(inference|items-structured)\\//.test(u)).length,
      cards: document.querySelectorAll('.instcard').length,
    })`);
  console.log('    实测：', JSON.stringify(home));
  ck('首页没有推断数据全局（EMOHEALTH_INFER_*）', home.inferGlobals.length === 0,
     JSON.stringify(home.inferGlobals));
  ck('首页没有加载 lib/inference.js（EmoHealthInference 未定义）', home.lib === 'undefined');
  ck('首页没有注入 ui/inference/*.js 或 ui/items-structured/*.js',
     home.dataScripts === 0, home.dataScripts + ' 个脚本');
  ck('首页的资源请求里没有这两个数据目录', home.dataRes === 0, home.dataRes + ' 条');
  ck('两份清单仍随首页加载（按需加载的入口）',
     home.inferMap === 'object' && home.structMap === 'object',
     `inferMap=${home.inferMap} structMap=${home.structMap}`);
  ck('首页量表库仍可用', home.cards > 0, home.cards + ' 张卡片');

  /* ══ ① 题面四件套（PID-5 经典页，选项说明来自锚点级数据；schema 2.1 起含情景块）══ */
  console.log('\n=== ① 题面四件套：text_en / text_zh / meaning_zh / scenario_zh（notes_zh 可为空）===');
  await nav(URL_ + '#/scale/PID-5/classic');
  ck('PID-5 子页的按需数据已就位', await waitReady('PID-5') === true);
  const f4 = await ev(`(() => {
      const d = INST_NOW, st = window.EMOHEALTH_STRUCT_PID_5;
      const byId = new Map(st.items.map(x => [x.id, x]));
      const li = document.querySelector('.institems > li[data-item]');
      const it = d.items.find(x => x.id === li.dataset.item);
      const s = byId.get(it.id);
      const opts = [...li.querySelectorAll('.opt')];
      /* schema 2.0：选项**语义**在锚点级 scale_guides[scale_id].options[]，
         选项**标签**在题上 response.options[]（逐题锚点如 ASRM 的陈述也在题上）。 */
      const guide = st.scale_guides[s.response.scale_id] || {};
      const gOpts = new Map((guide.options || []).map(o => [+o.v, o]));
      const visOf = el => { const c = el.cloneNode(true);
        c.querySelectorAll('details').forEach(d => d.remove()); return c.textContent; };
      return {
        item: it.id,
        hasTextZh: !!li.querySelector('[data-f="text_zh"]'),
        hasTextEn: !!li.querySelector('[data-f="text_en"]'),
        hasNotes: !!li.querySelector('[data-f="notes_zh"]'),
        hasMeaning: opts.some(b => b.querySelector('[data-f="meaning_zh"]')),
        textZh: (li.querySelector('[data-f="text_zh"]')||{}).textContent,
        textEn: (li.querySelector('[data-f="text_en"]')||{}).textContent,
        wantZh: s.text_zh, wantEn: s.text_en,
        meanings: opts.map(b => (b.querySelector('[data-f="meaning_zh"]')||{}).textContent),
        wantMeanings: opts.map(b => (gOpts.get(+b.dataset.v) || {}).meaning_zh || ''),
        labelsZh: opts.map(b => (b.querySelector('[data-f="opt_label_zh"]')||{}).textContent),
        wantLabels: (s.response.options||[]).map(o => o.label_zh),
        notes: [...li.querySelectorAll('[data-f="notes_zh"] li')].map(x => x.textContent),
        wantNotes: (s.notes_zh||[]).map(n => n.text),
        basisFold: !!li.querySelector('[data-f="option_basis"]'),
        /* schema 2.1（task-32）：情景块 scenario_zh —— 存在、非空、位置在题干之后 */
        hasScene: !!li.querySelector('[data-f="scenario_zh"]'),
        sceneText: (li.querySelector('[data-f="scenario_zh"]')||{}).textContent || '',
        wantScene: s.scenario_zh || '',
        sceneAfterStem: (() => {
          const kids = [...li.children];
          const zh = li.querySelector('[data-f="text_zh"]');
          const box = li.querySelector('[data-f="scenario_zh"]');
          const notes = li.querySelector('[data-f="notes_zh"]');
          if (!zh || !box) return false;
          return kids.indexOf(box) > kids.indexOf(zh)
            && (!notes || kids.indexOf(box) < kids.indexOf(notes));
        })(),
        /* 内部字段**可见层**一个字都不该有（用户点名）；
           题目自己的 text_zh_source / 注记来源属 R1 证据，允许留在**折叠**里，
           所以这里比的是「去掉折叠后的可见文字」。 */
        internalShown: /manual\.pdf|项目自撰|手册原文|label_source|options_source/
          .test(visOf(li)),
      };
    })()`);
  console.log('    实测（截断）：', JSON.stringify({...f4, meanings: f4.meanings.slice(0, 2),
    wantMeanings: f4.wantMeanings.slice(0, 2), notes: f4.notes.slice(0, 1)}).slice(0, 900));
  /* schema 2.1：题面四件套改为 text_zh / text_en / meaning_zh / scenario_zh；
     `notes_zh` 大幅缩减、**可以为空甚至不出现**（不再要求每题都有）。 */
  ck('题面同时有 text_zh / text_en / meaning_zh / scenario_zh（notes_zh 可为空）',
     f4.hasTextZh && f4.hasTextEn && f4.hasMeaning && f4.hasScene,
     JSON.stringify({zh: f4.hasTextZh, en: f4.hasTextEn, mean: f4.hasMeaning,
       scene: f4.hasScene, notes: f4.hasNotes}));
  ck('notes_zh 若出现则 ≤1 条（schema 2.1 约定）且与数据逐条一致',
     (f4.wantNotes || []).length <= 1 && f4.notes.length === f4.wantNotes.length
     && f4.notes.every((t, i) => t.includes(f4.wantNotes[i])),
     `DOM ${f4.notes.length} 条 / 数据 ${(f4.wantNotes || []).length} 条`);
  ck('中译与结构化数据逐字一致', f4.textZh === f4.wantZh, JSON.stringify(f4.textZh));
  ck('英文原文与结构化数据逐字一致（并列可读）',
     (f4.textEn || '').includes(f4.wantEn), JSON.stringify(f4.textEn));
  ck('每个选项的情景说明都在 DOM 里且与数据一致',
     JSON.stringify(f4.meanings.map(norm)) === JSON.stringify(f4.wantMeanings.map(norm)),
     `${f4.meanings.length} 个选项说明`);
  ck('每个选项还有中英标签', JSON.stringify(f4.labelsZh) === JSON.stringify(f4.wantLabels));
  ck('作答注记（notes_zh）默认可见且与数据一致',
     f4.notes.length === f4.wantNotes.length
     && f4.notes.every((t, i) => t.includes(f4.wantNotes[i])),
     JSON.stringify(f4.notes).slice(0, 120));
  ck('每题不再有内部「依据/出处」折叠（D120：界面不承担溯源职责）',
     f4.basisFold === false, String(f4.basisFold));
  ck('数据层内部字段（出处字符串）一个字都不显示', f4.internalShown === false,
     JSON.stringify((f4.meanings[0] || '').slice(0, 60)));
  /* schema 2.1（task-32）：情景块必须渲染、非空、且在题干之后（题库位） */
  ck('情景块 scenario_zh 存在且非空', f4.hasScene === true && f4.sceneText.trim().length > 0,
     JSON.stringify(f4.sceneText).slice(0, 80));
  ck('情景块文本与数据一致', norm(f4.sceneText) === norm(f4.wantScene),
     JSON.stringify({dom: norm(f4.sceneText).slice(0, 40), data: norm(f4.wantScene).slice(0, 40)}));
  ck('情景块 ≥20 汉字（冻结契约：20–60 汉字）',
     (f4.sceneText.match(/[\u4e00-\u9fff]/g) || []).length >= 20,
     '汉字数=' + (f4.sceneText.match(/[\u4e00-\u9fff]/g) || []).length);
  ck('情景块位置：题干之后、作答注记之前', f4.sceneAfterStem === true);

  /* ①-b IPIP-NEO：schema 2.0 起**内部出处字段不上界面**（task-22 交接说明 +
     用户点名「不要提」）。所以这一节断言：默认视野干净 + 内部字段（手册/来源路径/
     label_source/options_source）在任何地方都不显示；用户需要的情景说明仍然可见。 */
  console.log('\n=== ①-b IPIP-NEO：内部出处字段不显示，用户要的情景说明仍在 ===');
  await nav(URL_ + '#/scale/IPIP-NEO/classic');
  ck('IPIP-NEO 子页的按需数据已就位', await waitReady('IPIP-NEO') === true);
  const prov = await ev(`(() => {
      const li = document.querySelector('.institems > li[data-item]');
      const st = window.EMOHEALTH_STRUCT_IPIP_NEO;
      const s = st.items.find(x => x.id === li.dataset.item);
      const guide = st.scale_guides[s.response.scale_id] || {};
      const all = li.textContent;
      return {hasAnyDevFold: !!li.querySelector('details[data-dev], [data-f="option_basis"]'),
        hasAnchorGuide: !!li.parentElement.querySelector('[data-guide="anchor"]'),
        anchorNote: (guide.anchor_note_zh || '').slice(0, 40),
        optionsHaveMeaning: [...li.querySelectorAll('.opt')]
          .every(b => !!(b.querySelector('[data-f="meaning_zh"]') || {}).textContent),
        anyInternalInItem: /项目自撰|手册原文|manual\\.pdf|label_source|options_source|不是手册原文/
          .test(all)};
    })()`);
  console.log('    实测：', JSON.stringify(prov).slice(0, 420));
  ck('锚点级说明（IPIP 30 个 facet 尺子）出现在该组第一题上',
     prov.hasAnchorGuide === true && prov.anchorNote.length > 0, prov.anchorNote);
  ck('每个选项都有情景说明（用户要的，没被一起删掉）', prov.optionsHaveMeaning === true);
  ck('内部出处字段（项目自撰/手册原文/label_source/options_source）一个字都不显示',
     prov.anyInternalInItem === false);
  ck('每题没有任何内部「依据」折叠', prov.hasAnyDevFold === false);

  /* ══ ②③ 预测 + 置信度：硬规则、分层、与库逐值一致 ══ */
  console.log('\n=== ②③ 预测与置信度：硬规则 + 与 ui/lib/inference.js 逐值一致 ===');
  await nav(URL_ + '#/scale/PID-5/classic');
  ck('PID-5 推断面板已就位', await waitReady('PID-5') === true);
  const empty = await ev(`(() => {
      const rows = [...document.querySelectorAll('.infpanel tr[data-dim]')];
      return {n: rows.length,
        blocked: rows.filter(r => r.dataset.display === 'blocked').length,
        allowed: rows.filter(r => r.dataset.display === 'allowed').length,
        withPred: rows.filter(r => r.dataset.pred != null).length,
        withR: rows.filter(r => r.dataset.r != null).length,
        sample: rows.slice(0, 2).map(r => r.textContent.replace(/\\s+/g, ' ').slice(0, 90)),
        statuses: [...new Set(rows.map(r => r.dataset.status))]};
    })()`);
  console.log('    实测（一题未答）：', JSON.stringify(empty));
  ck('面板列出了全部维度', empty.n === 25, empty.n + ' 个维度');
  ck('一题未答时所有维度都不展示预测/置信度',
     empty.allowed === 0 && empty.withPred === 0 && empty.withR === 0,
     `blocked=${empty.blocked} allowed=${empty.allowed} pred=${empty.withPred} r=${empty.withR}`);

  const hard = await ev(`(() => {
      const d = INST_NOW;
      // 只答第一个维度的一题，别的维度一题不答
      const dim0 = d.dimensions[0];
      const id0 = dim0.items[0];
      S.instResp = {}; S.instResp[id0] = 1; S.ansVer++;
      renderStage();
      const rows = [...document.querySelectorAll('.infpanel tr[data-dim]')];
      const own = rows.find(r => r.dataset.display !== 'blocked');
      const others = rows.filter(r => r.dataset.display === 'blocked');
      return {
        dim0: dim0.id, nBlocked: others.length,
        ownRow: own ? {dim: own.dataset.dim, status: own.dataset.status,
          pred: own.dataset.pred, r: own.dataset.r, avail: own.dataset.available,
          hasPredEl: !!own.querySelector('.infpred'),
          text: own.textContent.replace(/\\s+/g, ' ').slice(0, 110)} : null,
        otherSample: others.length ? {
          pred: others[0].dataset.pred, r: others[0].dataset.r,
          text: others[0].textContent.replace(/\\s+/g, ' ').slice(0, 130),
          hasPredEl: !!others[0].querySelector('.infpred'),
          colspan: others[0].querySelectorAll('td[colspan]').length,
          digits: (others[0].textContent.match(/r=|约 |%/g) || [])} : null,
      };
    })()`);
  console.log('    实测（只答 dim0 一题）：', JSON.stringify(hard).slice(0, 600));
  ck('答了自己一题的维度才进入「可显示」', !!hard.ownRow && hard.ownRow.dim === hard.dim0,
     hard.ownRow ? hard.ownRow.dim : '(无)');
  ck('其余 24 个维度**仍然**不展示预测与置信度（硬规则）',
     hard.nBlocked === 24 && hard.otherSample.pred === undefined
     && hard.otherSample.r === undefined && hard.otherSample.hasPredEl === false
     && hard.otherSample.colspan === 1,
     `blocked=${hard.nBlocked} pred=${hard.otherSample.pred} r=${hard.otherSample.r}`);
  ck('被挡住的行只给原因（没有 r=/约 /%）',
     hard.otherSample.digits.length === 0, JSON.stringify(hard.otherSample.digits));
  ck('可显示的维度给出 r（置信度）', hard.ownRow && hard.ownRow.r != null,
     'r=' + (hard.ownRow && hard.ownRow.r));
  ck('置信度不足门槛时不给预测数（available=0 且无预测元素）',
     hard.ownRow && hard.ownRow.avail === '0' ? hard.ownRow.hasPredEl === false : true,
     `available=${hard.ownRow && hard.ownRow.avail}`);

  const match = await ev(`(() => {
      const p = inferencePayload('PID-5');
      const ref = window.EmoHealthInference.predictFrom(p, S.instResp);
      const rows = [...document.querySelectorAll('.infpanel tr[data-dim]')];
      let checked = 0, bad = [];
      for (const r of rows) {
        const b = ref.inferred[r.dataset.dim];
        if (!b) continue;
        if (!b.display_allowed) {
          if (r.dataset.r != null || r.dataset.pred != null) bad.push(r.dataset.dim + ':blocked-but-number');
          continue;
        }
        if (String(b.confidence_r) !== String(r.dataset.r)) bad.push(r.dataset.dim + ':r ' + r.dataset.r + '≠' + b.confidence_r);
        if (b.available) {
          if (String(b.predicted_score) !== String(r.dataset.pred)) bad.push(r.dataset.dim + ':pred');
          /* 「这是估计」的标记必须是**可见**的（D118 换语言后是 .infbadge「估计」），
             不能因为把工程术语换掉就把「非实测」的信息一起藏掉。 */
          const badge = r.querySelector('.infbadge');
          if (!badge || !/估计/.test(badge.textContent)) {
            bad.push(r.dataset.dim + ':no-visible-estimate-badge');
          }
        } else if (r.dataset.pred != null) bad.push(r.dataset.dim + ':not-available-but-pred');
        checked++;
      }
      // 官方分层：official 未答满 → 不给值；且面板里有分层说明
      const o = ref.official[rows[0].dataset.dim];
      return {checked, bad, officialValue: o.value, complete: o.complete,
        layerNote: !!ref.layer_note, panelText: document.querySelector('.infpanel').textContent.slice(0, 260)};
    })()`);
  console.log('    实测（与库对照）：', JSON.stringify(match).slice(0, 500));
  ck('界面上的 r/预测值与 ui/lib/inference.js 直接调用逐值一致',
     match.bad.length === 0, JSON.stringify(match.bad));
  ck('官方分未答满时不给值（缺失不猜）', match.complete === false && match.officialValue === null,
     `complete=${match.complete} value=${match.officialValue}`);
  /* D118：面板默认视野改用**用户语言**，但「这是估计、不是已测出来的得分」必须仍在。 */
  ck('面板默认文案仍说清「这是估计，不是已经测出来的得分」',
     /估计/.test(match.panelText) && /不是已经测出来的得分/.test(match.panelText),
     match.panelText.replace(/\s+/g, ' ').slice(0, 120));

  /* 答满一个维度 → 预测 = 官方分（库的硬性质，顺带验证面板给出可用值） */
  const full = await ev(`(() => {
      const d = INST_NOW, dim0 = d.dimensions[0];
      const lo = d.response_format.min, hi = d.response_format.max;
      S.instResp = {}; S.ansVer++;
      dim0.items.forEach((id, i) => { S.instResp[id] = lo + (i % (hi - lo + 1)); });
      S.ansVer++; renderStage();
      const row = document.querySelector('.infpanel tr[data-dim="' + dim0.id + '"]');
      const p = inferencePayload('PID-5');
      const ref = window.EmoHealthInference.predictFrom(p, S.instResp);
      return {dim: dim0.id, rowPred: row.dataset.pred, rowR: row.dataset.r,
        avail: row.dataset.available, refPred: ref.inferred[dim0.id].predicted_score,
        availRef: ref.inferred[dim0.id].available, official: ref.official[dim0.id].value,
        badge: !!row.querySelector('.infbadge'),
        ready: document.querySelector('.infpanel').dataset.ready};
    })()`);
  console.log('    实测（答满 dim0）：', JSON.stringify(full));
  ck('答满该维度 → 给出预测值且与库一致',
     full.avail === '1' && String(full.rowPred) === String(full.refPred), JSON.stringify(full.rowPred));
  ck('预测值带「推断」徽章（不与官方分混算）', full.badge === true);
  ck('答满时预测 ≈ 官方分（库的硬性质，差 < 1e-9）',
     Math.abs(full.refPred - full.official) < 1e-9,
     `pred=${full.refPred} official=${full.official}`);

  /* 硬规则延伸（天赋树推荐）：目标维度不可展示时，**连机器可读的
     `data-reco-utility` 属性也不输出**——否则将来加导出/API/截图分析时它就是
     「未答维度置信度信息」的泄漏口。可见文案与属性必须**同时** gate。
     正例也要覆盖到：目标维度可展示时属性必须在，且等于我独立复算的 utility。 */
  console.log('\n=== 硬规则延伸：data-reco-utility 的 gate ===');
  await nav(URL_ + '#/scale/PID-5/tree');
  ck('天赋树页就绪（推荐框可查）', await waitReady('PID-5') === true);
  const gate = await ev(`(() => {
      const d = INST_NOW, p = inferencePayload('PID-5'), lib = window.EmoHealthInference;
      const plan = [
        [d.dimensions[0].items[0]],
        d.dimensions[0].items.slice(0, 4),
        d.dimensions[0].items.slice(0, 8).concat([d.dimensions[1].items[0]]),
        d.dimensions[0].items.slice(0, 8).concat(d.dimensions[1].items.slice(0, 9)),
        /* 每个有题的维度都答一题 → 全部维度可展示 ⇒ 推荐的目标维度必然可展示
           （信息增益通常偏好「还没碰过的维度」，所以只答少数维度时正例覆盖不到）。
           ⚠️ 量表包的 dimensions 里还有**域级**条目（items 为空数组，由 facet 汇总而来），
           取题时必须跳过空 items。 */
        d.dimensions.filter(x => (x.items || []).length).map(x => x.items[0]),
      ];
      const states = [];
      plan.forEach(ids => {
        S.instResp = {}; S.ansVer++;
        ids.forEach((id, i) => { S.instResp[id] = i % 4; });
        S.ansVer++; S.treeSel = null; renderTop(); renderStage();
        const box = document.querySelector('.treereco[data-reco="1"]');
        const attr = box ? box.getAttribute('data-reco-utility') : null;
        const ownShown = box ? box.dataset.recoOwnDisplay === '1' : null;
        // 与界面同源同池地独立复算 utility（候选＝结构性可答且未答）
        const answered = d.items.filter(it => it.id in S.instResp).map(it => it.id);
        const openOrders = d.items.map(it => it.order)
          .filter(o => treeNodeState(TREE_NOW, o, S.instResp) === 'open');
        const idOf = new Map(d.items.map(it => [it.order, it.id]));
        const mine = lib.forecastGains(p, answered, openOrders.map(o => idOf.get(o)));
        /* 默认视野（D118）：推荐框里**不该出现任何开发者指标**——
           把折叠整棵去掉后再读，若还剩「效用/信息增益/耗时/ms/门槛」就是漏了。 */
        const vis = el => { const c = el.cloneNode(true);
          c.querySelectorAll('details').forEach(d => d.remove()); return c.textContent; };
        const visText = box ? vis(box).replace(/\s+/g, ' ') : '';
        states.push({answered: ids.length, hasAttr: attr != null, attr: attr,
          ownShown: ownShown, visible: visText,
          visibleHasDevMetric: /效用|信息增益|耗时|门槛|\bms\b|utility|conf_r/.test(visText),
          hasRecoFold: box ? !!box.querySelector('[data-dev="reco-basis"]') : null,
          utility: mine.best ? +mine.best.utility.toFixed(4) : null});
      });
      return states;
    })()`);
  console.log('    实测：', JSON.stringify(gate.map(s => ({a: s.answered, own: s.ownShown,
    attr: s.attr, dev: s.visibleHasDevMetric, vis: s.visible.slice(0, 60)}))));
  ck('属性存在与否 == 目标维度是否可展示（一一对应）',
     gate.every(s => s.ownShown === true ? s.hasAttr : s.hasAttr === false),
     JSON.stringify(gate.map(s => [s.answered, s.ownShown, s.hasAttr])));
  ck('推荐框里没有开发者指标，也没有技术依据折叠（D120 已删除）',
     gate.every(s => s.visibleHasDevMetric === false && s.hasRecoFold === false),
     JSON.stringify(gate.filter(s => s.visibleHasDevMetric || s.hasRecoFold)
       .map(s => s.visible.slice(0, 90))));
  ck('可展示时属性在，且与独立复算的 utility 一致（正例被覆盖到）',
     gate.some(s => s.ownShown === true && s.hasAttr && Math.abs(+s.attr - s.utility) < 1e-3),
     JSON.stringify(gate.map(s => [s.answered, s.ownShown, s.attr, s.utility])));
  /* 复位作答：同码导航不会清空 `S.instResp`，不复位会让下面的
     「未答维度仍被挡住」没有可断言的状态（实测踩过：留下 25 题→0 个维度被挡）。 */
  await ev(`(() => { S.instResp = {}; S.ansVer++; S.treeSel = null;
      renderTop(); renderStage(); return 1; })()`);

  /* 天赋树页也要有同一套题面与面板（同一套渲染路径） */
  console.log('\n=== 天赋树就地作答：题面 + 情景块 + 面板同样生效 ===');
  await nav(URL_ + '#/scale/PID-5/tree');
  ck('天赋树页的按需数据已就位', await waitReady('PID-5') === true);
  const tree = await ev(`(() => {
      const nodes = [...document.querySelectorAll('.treenode')];
      /* task-43：不要按下标盲点——task-42 之后环序/
         环内选谁由数据决定，第 6 个节点可能落在未解锁环上（点了不会有反应，
         旧写法会假红）。这里改点**真的可答**的节点。 */
      const open = [...document.querySelectorAll('.treenode.open')];
      const n = open[Math.min(3, open.length - 1)] || nodes[Math.min(5, nodes.length - 1)];
      n.dispatchEvent(new MouseEvent('click', {bubbles: true}));
      return new Promise(res => setTimeout(() => {
        const q = document.querySelector('.treeq');
        res({nodes: nodes.length, hasQ: !!q,
          fields: q ? ['text_zh','text_en','meaning_zh','scenario_zh']
            .filter(f => q.querySelector('[data-f="' + f + '"]')).length : 0,
          hasScene: !!(q && q.querySelector('[data-f="scenario_zh"]')),
          sceneText: q ? ((q.querySelector('[data-f="scenario_zh"]') || {}).textContent || '')
            .replace(/\\s+/g, ' ').trim() : '',
          notesCount: q ? q.querySelectorAll('[data-f="notes_zh"] li').length : 0,
          opts: q ? q.querySelectorAll('.opts button.opt').length : 0,
          panel: !!document.querySelector('.infpanel'),
          panelBlocked: document.querySelectorAll('.infpanel tr[data-display="blocked"]').length});
      }, 700));
    })()`);
  console.log('    实测：', JSON.stringify(tree).slice(0, 300));
  ck('天赋树仍渲染（布局保留）', tree.nodes === 220, tree.nodes + ' 节点');
  /* schema 2.1：题面四件套是 text_zh / text_en / meaning_zh / scenario_zh；
     `notes_zh` 现在**可为空**（很多题没有），所以不再要求它必须出现。 */
  ck('就地作答区有题面四件套（notes_zh 按 schema 2.1 可为空）',
     tree.hasQ && tree.fields === 4, tree.fields + '/4 部分');
  ck('天赋树就地作答也渲染情景块且 ≥20 汉字',
     tree.hasScene === true && (tree.sceneText.match(/[\u4e00-\u9fff]/g) || []).length >= 20,
     '汉字数=' + (tree.sceneText.match(/[\u4e00-\u9fff]/g) || []).length);
  ck('天赋树就地作答的 notes_zh 若出现则 ≤1 条（schema 2.1 约定）',
     tree.notesCount <= 1, tree.notesCount + ' 条');
  ck('天赋树页也有推断面板，且未答维度仍被挡住',
     tree.panel === true && tree.panelBlocked > 0, tree.panelBlocked + ' 个维度被挡');

  console.log('\n脚本报错:', errs.length ? errs.slice(0, 2) : '无');
  ck('无脚本异常', errs.length === 0);
  ws.close(); ch.kill();
  console.log(fail ? `\n❌ ${fail} 项未通过` : '\n✅ 题面四字段与预测/置信度全部通过');
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error('❌', e.message); process.exit(1); });
