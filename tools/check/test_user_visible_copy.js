// 用户端产品化（D118 / task-20）：**默认视野**里不该有开发者/审阅者向的内容。
// （文件名按 Lead 2026-10-05 裁决⑥由 `test_user_facing_ux.js` 改成这个：它测的是
//   「可见文案」，UX 是更宽的东西。）
//
// 为什么用「可见文字」而不是 `textContent`：这是本任务的核心判据。
// 溯源/依据/口径**没有删**（R1：每个数字都要能追到出处），只是**收进默认折叠**；
// 而折叠内容仍计入 `textContent`——所以既有的 `test_tree_mode.js`（要求有「布局依据」）
// 与 `test_multiscale_fetch.js`（要求有「授权」）才仍然为真。
// 本测试因此自己实现「用户实际看到什么」：
//   · 关闭的 `<details>` 只算 `<summary>`（入口文字），不算内容
//   · `display:none` / `visibility:hidden` 不算
//   · SVG `<title>`（悬停提示）不算
//
// 断言六组：
//   ① 默认视野**不含**开发者关键词（逐条列出扫描结果，命中必须为 0）
//   ② 默认视野**仍含**用户要的东西：题文四字段、情景说明、作答注记、
//      「这是估计、不是已经测出来的得分」这句诚实性文案
//   ③ 打开「依据与出处」后**仍能查到**：conf_r / 门槛 / 样本量 / meaning_source /
//      布局性质 / 常模来源与 n（可溯源没丢）
//   ④ 硬规则仍成立：本维度未答 → 默认视野里没有该维度的估计与可信程度
//   ⑤ 面板默认只列「已有估计/已可估计」的维度 + 一行汇总（裁决⑤）：
//      未答维度收进折叠，**展开后每行仍有完整契约、仍没有 data-r/data-pred**
//   ⑥ 页脚**可见**一行授权署名（裁决①），且页脚不含开发者关键词
//
// 同时把**默认视野清单**打印出来（验收①要看的「还剩哪些文字」）。
const {spawn} = require('child_process');
const os = require('os'), fs = require('fs'), path = require('path');
const PORT = 9356;
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

/* 开发者/审阅者向关键词：默认视野命中任何一个都算失败。
   ⚠️ `ceiling`/`ms` 用词边界，避免误伤普通英文题文里的字母组合。 */
const KEYWORDS = [
  ["conf_r", /\bconf_r\b/], ["dim_ceiling", /dim_ceiling/], ["ceiling_ratio", /ceiling_ratio/],
  ["ceiling_cross", /ceiling_cross/], ["ceiling", /\bceiling\b/], ["门槛", /门槛/],
  ["耗时", /耗时/], ["ms", /\bms\b/], ["n_slow", /n_slow/], ["utility", /\butility\b/],
  ["信息增益", /信息增益/], ["manual_verbatim", /manual_verbatim/],
  ["manual_labels", /manual_labels/], ["project_editorial", /project_editorial/],
  ["手册原文", /手册原文/], ["手册", /手册/], ["项目自撰", /项目自撰/],
  ["推论", /推论/], ["判据", /判据/], ["算式", /算式/], ["口径", /口径/], ["出处", /出处/],
  ["已核查", /已核查/], ["推算", /推算/], ["手册未给|没有规定", /没有规定|手册未给/],
  ["n=", /n=/], ["inferred", /inferred/], ["官方分", /官方分/], ["缺失不猜", /缺失不猜/],
  ["已达上限", /已达上限/], ["项目自撰", /项目自撰/], ["手册原文逐字", /手册原文逐字/],
  ["手册锚点标签", /手册锚点标签/], ["r=", /\br=/], ["效用", /效用/],
  ["置信度 r", /置信度 r/], ["item_dim_corr", /item_dim_corr/], ["pairB64", /pairB64/],
  ["ansVer", /ansVer/], ["dim_items", /dim_items/], ["前瞻", /前瞻/],
];

/* 「用户实际看到的文字」——见文件头的判据说明 */
const VIS = `(() => {
  const root = document.getElementById('stage');
  const skip = new Set(['SCRIPT', 'STYLE', 'TITLE', 'NOSCRIPT']);
  const out = [];
  const walk = el => {
    if (el.tagName === 'DETAILS' && !el.open) {
      const s = el.querySelector(':scope > summary');
      if (s) out.push(s.textContent);
      return;
    }
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') return;
    for (const c of el.childNodes) {
      if (c.nodeType === 3) { const t = c.nodeValue.trim(); if (t) out.push(t); }
      else if (c.nodeType === 1 && !skip.has(c.tagName)) walk(c);
    }
  };
  walk(root);
  return out.join(' ').replace(/\\s+/g, ' ').trim();
})()`;

(async () => {
  const prof = fs.mkdtempSync(path.join(os.tmpdir(), 'ux-'));
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
  /* ⚠️ ⑩ 段会调 `instExportCSV/instExportJSON`（内部走 `download()`）——先把下载行为设成
     「允许但不弹窗」，否则 headless 下的下载会挂住这一页（实测卡了 15 分钟）。 */
  const dlDir = fs.mkdtempSync(path.join(os.tmpdir(), 'uxdl-'));
  await S('Browser.setDownloadBehavior',
    {behavior: 'allow', downloadPath: dlDir, eventsEnabled: true});
  const ev = async x => {
    const r = await S('Runtime.evaluate',
      {expression: x, returnByValue: true, awaitPromise: true});
    if (r.result?.exceptionDetails) return 'EXC: ' +
      (r.result.exceptionDetails.exception?.description || '').slice(0, 300);
    return r.result?.result?.value;
  };
  const nav = async (u, wait = 3200) => { await S('Page.navigate', {url: u}); await sleep(wait); };
  const waitReady = async code => ev(`(async () => {
      for (let i = 0; i < 80; i++) {
        if (window['EMOHEALTH_STRUCT_' + ${JSON.stringify(code)}.replace(/[^A-Za-z0-9]/g, '_').toUpperCase()]
            && document.querySelector('.infpanel[data-display="ok"]')) return true;
        await new Promise(r => setTimeout(r, 150));
      }
      return false; })()`);
  const scan = async () => {
    const vis = await ev(VIS);
    const hits = KEYWORDS.filter(([, re]) => re.test(vis)).map(([n]) => n);
    return {vis, hits};
  };
  const report = (label, vis) => {
    console.log(`\n  ── 默认视野清单（${label}，${vis.length} 字）──`);
    console.log('  ' + vis.slice(0, 900) + (vis.length > 900 ? ' …' : ''));
  };

  /* ══ ① 经典逐题页：默认视野 ══ */
  console.log('=== ① 经典逐题页（PID-5，已答该量表第一维度的 3 题）===');
  await nav(URL_ + '#/scale/PID-5/classic');
  ck('按需数据就位', await waitReady('PID-5') === true);
  await ev(`(() => {
      const d = INST_NOW, dim0 = d.dimensions[0];
      S.instResp = {}; S.ansVer++;
      dim0.items.slice(0, 3).forEach((id, i) => { S.instResp[id] = i % 4; });
      S.ansVer++; renderTop(); renderStage(); return 1; })()`);
  await sleep(400);
  const c1 = await scan();
  report('经典逐题', c1.vis);
  ck('默认视野**没有**开发者/审阅者关键词', c1.hits.length === 0, JSON.stringify(c1.hits));
  const ess = await ev(`(() => {
      const vis = ${VIS};
      const li = document.querySelector('.institems > li[data-item]');
      const zh = (li.querySelector('[data-f="text_zh"]') || {}).textContent || '';
      const en = (li.querySelector('[data-f="text_en"]') || {}).textContent || '';
      const mean = (li.querySelector('[data-f="meaning_zh"]') || {}).textContent || '';
      const note = (li.querySelector('[data-f="notes_zh"]') || {}).textContent || '';
      return {zh: vis.includes(zh.trim().slice(0, 12)), en: vis.includes(en.replace('EN', '').trim().slice(0, 12)),
        mean: vis.includes(mean.trim().slice(0, 10)), note: vis.includes(note.trim().slice(0, 10)),
        estimate: /估计/.test(vis), honesty: /不是已经测出来的得分/.test(vis),
        openFolds: document.querySelectorAll('#stage details[open]').length,
        foldCount: document.querySelectorAll('#stage details').length};
    })()`);
  ck('用户要的内容仍在默认视野：中译/原文/情景说明/作答注记',
     ess.zh && ess.en && ess.mean && ess.note, JSON.stringify(ess));
  ck('「这是估计、不是已经测出来的得分」仍在默认视野（诚实性不藏）',
     ess.estimate === true && ess.honesty === true);
  ck('所有溯源/口径折叠默认都是关闭的', ess.openFolds === 0,
     `${ess.openFolds} 个打开 / 共 ${ess.foldCount} 个`);

  /* ══ ④ 硬规则（默认视野）══ */
  const hard = await ev(`(() => {
      const rows = [...document.querySelectorAll('.infpanel tr[data-dim]')];
      const blocked = rows.filter(r => r.dataset.display === 'blocked');
      const vis = ${VIS};
      return {n: rows.length, blocked: blocked.length,
        blockedNoR: blocked.every(r => (r.dataset.r == null || r.dataset.r === '') && r.dataset.pred == null),
        blockedText: blocked.slice(0, 1).map(r => r.textContent.replace(/\\s+/g, ' ').slice(0, 70)),
        allowedText: rows.filter(r => r.dataset.display === 'allowed')
          .map(r => r.textContent.replace(/\\s+/g, ' ').slice(0, 70)),
        visHasR: /\\br=/.test(vis), visHasPct: /%/.test(vis)};
    })()`);
  console.log('    实测（硬规则）：', JSON.stringify(hard));
  ck('本维度未答的行没有 data-r / data-pred（硬规则）',
     hard.blocked > 0 && hard.blockedNoR === true, `${hard.blocked}/${hard.n} 行被挡`);
  ck('被挡的行只说原因，不出现置信度数值',
     !/\d\.\d\d/.test(hard.blockedText.join(' ')), JSON.stringify(hard.blockedText));

  /* ══ ⑤ 面板默认视野变短：只列有状态的维度 + 一行汇总（裁决⑤）══ */
  console.log('\n=== ⑤ 面板：默认只列「已有估计/已可估计」的维度，未答的收进折叠 ===');
  const dens = await ev(`(() => {
      const panel = document.querySelector('.infpanel');
      const rows = [...panel.querySelectorAll('tr[data-dim]')];
      const fold = panel.querySelector('[data-dimfold]');
      const foldRows = fold ? [...fold.querySelectorAll('tr[data-dim]')] : [];
      const defRows = rows.filter(r => !fold || !fold.contains(r));
      const vis = ${VIS};
      return {shown: panel.dataset.shown, others: panel.dataset.others,
        totalRows: rows.length, defRows: defRows.length, foldRows: foldRows.length,
        defAllAllowed: defRows.every(r => r.dataset.display === 'allowed'),
        foldAllBlocked: foldRows.every(r => r.dataset.display === 'blocked'),
        foldClosed: fold ? fold.open === false : null,
        foldSummary: fold ? (fold.querySelector('summary') || {}).textContent : null,
        // 默认视野里那句重复长句出现几次（应只由 summary 提供「还没答过题」这个概念）
        visLongRepeat: (vis.match(/先不给估计与可信程度/g) || []).length,
        visHasOthersLine: /另有 \\d+ 个维度你还没答过题/.test(vis),
        visLen: vis.length};
    })()`);
  console.log('    实测（默认/折叠）：', JSON.stringify(dens));
  ck('默认表只列有状态的维度（allowed），未答的全部进折叠',
     +dens.shown === dens.defRows && +dens.others === dens.foldRows
     && dens.defAllAllowed === true && dens.foldAllBlocked === true,
     `默认 ${dens.defRows} 行（allowed=${dens.defAllAllowed}）／折叠 ${dens.foldRows} 行（blocked=${dens.foldAllBlocked}）`);
  ck('默认视野里不再逐行重复那句长文案（折叠默认关闭）',
     dens.visLongRepeat === 0 && dens.foldClosed === true, `重复 ${dens.visLongRepeat} 次`);
  ck('默认视野只留一行汇总说明（「另有 N 个维度你还没答过题」）',
     dens.visHasOthersLine === true, dens.foldSummary);

  /* 展开折叠后：契约与硬规则**都不能破** */
  const opened = await ev(`(() => {
      const panel = document.querySelector('.infpanel');
      const fold = panel.querySelector('[data-dimfold]');
      if (fold) fold.open = true;
      const rows = [...panel.querySelectorAll('tr[data-dim]')];
      const blocked = rows.filter(r => r.dataset.display === 'blocked');
      const vis = ${VIS};
      return {totalRows: rows.length, blocked: blocked.length,
        blockedNoR: blocked.every(r => (r.dataset.r == null || r.dataset.r === '')
          && r.dataset.pred == null),
        blockedHasStatus: blocked.every(r => r.dataset.status != null && r.dataset.status !== ''),
        blockedHasReason: blocked.every(r => (r.dataset.reason || '') !== ''),
        blockedLongText: (vis.match(/先不给估计与可信程度/g) || []).length,
        visHasR: /\\br=/.test(vis), visHasPred: /约 \\d/.test(vis),
        rowsVisible: blocked.filter(r => r.getClientRects().length > 0).length};
    })()`);
  console.log('    实测（展开后）：', JSON.stringify(opened));
  ck('展开后逐维度行仍在（硬规则的断言对象没被折叠掉）',
     opened.totalRows === 25 && opened.blocked === 24, `${opened.blocked}/${opened.totalRows}`);
  ck('展开后被挡维度**仍然没有** data-r / data-pred，且带着原因',
     opened.blockedNoR === true && opened.blockedHasStatus === true
     && opened.blockedHasReason === true);
  ck('展开后被挡行只写原因（可见文字里仍不出现 r= / 估计值）',
     opened.visHasR === false && opened.blockedLongText === 24,
     `原因句 ${opened.blockedLongText} 次，visHasR=${opened.visHasR}`);
  await ev(`(() => { const f = document.querySelector('[data-dimfold]');
      if (f) f.open = false; return 1; })()`);

  /* ══ ⑥ 页脚：授权署名**可见**，且不含开发者关键词 ══ */
  console.log('\n=== ⑥ 页脚授权一行（裁决①：署名要可见）===');
  const foot = await ev(`(() => {
      const el = document.getElementById('foot');
      const cs = getComputedStyle(el);
      return {exists: !!el, text: el ? el.textContent.replace(/\\s+/g, ' ').trim() : null,
        visible: !!(el && cs.display !== 'none' && el.getClientRects().length > 0),
        html: el ? el.innerHTML.slice(0, 200) : null};
    })()`);
  console.log('    实测（页脚）：', JSON.stringify(foot));
  const footHits = KEYWORDS.filter(([, re]) => re.test(foot.text || '')).map(([n]) => n);
  ck('页脚存在且可见', foot.exists === true && foot.visible === true, foot.text);
  ck('页脚写明授权署名', /授权：/.test(foot.text || ''), foot.text);
  ck('页脚不含开发者关键词', footHits.length === 0, JSON.stringify(footHits));

  /* ══ ③ 内部技术说明**整份 DOM 都不该有**（D120 / task-24）══
     判据变了：以前是「折叠里可以查到」，现在是「界面不承担溯源职责」——
     折叠也是 DOM，会被点开/搜索/截图，所以**展开所有折叠后**再扫一遍。 */
  console.log('\n=== ③ 整份 DOM（展开所有折叠）：内部技术词汇 0 命中 ===');
  const INTERNAL = [
    "conditional_expectation_linear", "Σ_AA", "ceiling_ratio", "ceiling_cross",
    "item-norms", "zenodo", "10.5281", "N=2148", "N=2,471", "N=2471", "临床 683",
    "calibrate_", "engine/inference.py", "pairB64", "BLUP", "inferred=true",
    "dim_ceiling", "conf_r", "item_dim_corr", "pair_source", "stats_source",
    "item_mean", "item_sd", "key_of_item", "dim_items", "dim_agg", "forecastGains",
    "utility", "research/", "tools/check", "data/inference", "archive/",
    "data/items-structured", "data/text-db", "ui/lib/", "ui/items-structured",
    "manual.pdf", "Scoring 段", "sample_note", "quality.", "ceiling_note",
    "layer_note", "min_own_removed", "DOI", "N=", "n=",
    /* D121（task-32）：数据层排版/本地化过程与内部修复留痕，也一律不许上界面 */
    "排版噪声", "缺空格", "漏空格", "直译", "逐条复核", "仲裁", "scaffold",
    "zh_source", "常见误读", "中文语境读法风险", "text_en_verbatim", "text_en_repairs",
  ];
  const deepScan = async (label) => {
    const hits = await ev(`(() => {
        document.querySelectorAll('details').forEach(d => { d.open = true; });
        const skip = new Set(['SCRIPT', 'STYLE']);
        const parts = [];
        const walk = el => {
          for (const c of el.childNodes) {
            if (c.nodeType === 3) parts.push(c.nodeValue);
            else if (c.nodeType === 1 && !skip.has(c.tagName)) {
              const t = c.getAttribute && c.getAttribute('title');
              if (t) parts.push(t);
              const a = c.getAttribute && c.getAttribute('aria-label');
              if (a) parts.push(a);
              walk(c);
            }
          }
        };
        walk(document.body);
        const text = parts.join(' \\n ');
        const words = ${JSON.stringify(INTERNAL)};
        const found = [];
        for (const w of words) if (text.indexOf(w) >= 0) found.push(w);
        if (/\\bofficial\\b/i.test(text)) found.push('official');
        if (/\\bBLUP\\b/.test(text) && found.indexOf('BLUP') < 0) found.push('BLUP');
        return found;
      })()`);
    ck(`${label}：整份 DOM（含折叠）内部词汇 0 命中`,
       Array.isArray(hits) && hits.length === 0, JSON.stringify(hits));
    return hits;
  };
  await deepScan('PID-5 经典逐题');

  /* 折叠只剩用户能懂的东西：授权（署名）与「这张图/这组选项」这类说明 */
  const folds = await ev(`(() => {
      const ds = [...document.querySelectorAll('#stage details')].filter(d => d.open);
      return {open: ds.length,
        dev: [...document.querySelectorAll('#stage [data-dev]')].map(x => x.dataset.dev),
        hasLicense: !!document.querySelector('#stage [data-dev="license"]')};
    })()`);
  console.log('    实测（展开后剩下的折叠）：', JSON.stringify(folds));
  ck('内部说明折叠已全部移除（panel-basis / item-basis / reco-basis 都不在）',
     !folds.dev.includes('panel-basis') && !folds.dev.includes('item-basis')
     && !folds.dev.includes('reco-basis'), JSON.stringify(folds.dev));
  ck('授权折叠仍在（署名信息保留）', folds.hasLicense === true);

  /* ══ 天赋树页 ══ */
  console.log('\n=== 天赋树页（PID-5）===');
  await nav(URL_ + '#/scale/PID-5/tree');
  ck('天赋树按需数据就位', await waitReady('PID-5') === true);
  await ev(`(() => { S.instResp = {}; S.ansVer++;
      INST_NOW.dimensions[0].items.slice(0, 4).forEach((id, i) => { S.instResp[id] = i % 4; });
      S.ansVer++; S.treeSel = null; renderTop(); renderStage(); return 1; })()`);
  await sleep(500);
  const c2 = await scan();
  report('天赋树', c2.vis);
  ck('天赋树默认视野**没有**开发者关键词', c2.hits.length === 0, JSON.stringify(c2.hits));
  const tree = await ev(`(() => {
      const open = sel => { const el = document.querySelector(sel);
        if (el) { el.open = true; return el.textContent.replace(/\\s+/g, ' '); } return null; };
      const basis = open('[data-dev="tree-basis"]');
      const vis = ${VIS};
      return {hasBasisFold: !!document.querySelector('[data-dev="tree-basis"]'),
        /* task-43 契约变更：task-42 之后环序**确实**来自「题↔面向相关」，
           旧文案「不是根据答题数据」现在是**假的** → 断言改成新文案，
           但仍要求说清「不是按你个人的作答」、且不含内部字段名。 */
        basisHasPlainLayout: !!(basis && /按维度分组/.test(basis)
          && /题↔面向相关/.test(basis) && /不是按你个人的作答/.test(basis)
          && !/不是根据答题数据/.test(basis)),
        basisHasAuth: !!(basis && /授权/.test(basis)),
        basisHasInternal: !!(basis && /conf_r|ceiling|门槛|判据|calibrate|research\\//.test(basis)),
        hasRecoBasisFold: !!document.querySelector('[data-dev="reco-basis"]'),
        recoAttrsKept: (() => {
          const b = document.querySelector('.treereco[data-reco="1"]');
          return !!(b && b.dataset.recoItem && b.dataset.recoOwnDisplay != null);
        })(),
        legend: document.querySelectorAll('.treelegend i').length,
        visBefore: vis.slice(0, 150)};
    })()`);
  console.log('    实测（天赋树折叠）：', JSON.stringify(tree).slice(0, 320));
  ck('天赋树折叠只剩「这张图是什么 + 授权」，且用白话',
     tree.hasBasisFold && tree.basisHasPlainLayout && tree.basisHasAuth
     && tree.basisHasInternal === false, JSON.stringify(tree.basisHasInternal));
  ck('推荐的技术依据折叠已删除（信息增益/效用/耗时不再上界面）',
     tree.hasRecoBasisFold === false);
  ck('推荐的机器可读契约仍在（data-reco-item / data-reco-own-display）',
     tree.recoAttrsKept === true);
  ck('图例是五类状态（含 task-43 的「新解锁（相关/互补）」）',
     tree.legend === 5, tree.legend + ' 项');

  /* ══ 结果页：常模型（PID-5）与门槛/分带型（L2）分别看 ══ */
  console.log('\n=== 结果页 A：常模型（PID-5，220 题答满）===');
  await nav(URL_ + '#/scale/PID-5/classic');
  ck('PID-5 就绪', await waitReady('PID-5') === true);
  await ev(`(() => { const d = INST_NOW;
      S.instResp = {}; S.ansVer++;
      d.items.forEach((it, i) => { S.instResp[it.id] = i % 4; });
      S.ansVer++; renderTop(); renderStage();
      const btn = document.querySelector('[data-instdone="1"]');
      if (btn && !btn.disabled) btn.dispatchEvent(new MouseEvent('click', {bubbles: true}));
      return 1; })()`);
  await sleep(900);
  const c3 = await scan();
  report('结果页（PID-5）', c3.vis);
  const res = await ev(`(() => {
      const open = sel => { const el = document.querySelector(sel);
        if (el) { el.open = true; return el.textContent.replace(/\\s+/g, ' '); } return null; };
      const lic = open('[data-dev="license"]');
      const body = document.getElementById('stage').textContent.replace(/\\s+/g, ' ');
      return {isResultPage: !!document.querySelector('.insttable'),
        hasResultBasisFold: !!document.querySelector('[data-dev="result-basis"]'),
        plainNormLine: /约 [\\d,]+ 人规模的样本/.test(body),
        visibleHasAggWords: /计分口径|sum=|mean=|max=/.test(body),
        visibleHasN: /n=\\d|N=\\d/.test(body),
        license: (lic || '').slice(0, 140)};
    })()`);
  console.log('    实测（结果页折叠，截断）：', JSON.stringify(res).slice(0, 320));
  ck('常模型结果页默认视野没有开发者关键词（含 n= / 口径）',
     c3.hits.length === 0, JSON.stringify(c3.hits));
  ck('结果页的「计分口径 / 常模来源 / n=」折叠已删除（内部字段不渲染）',
     res.hasResultBasisFold === false && res.visibleHasAggWords === false
     && res.visibleHasN === false, JSON.stringify(res));
  ck('「分数跟谁比」改成一句白话（约 N 人规模的样本，不给字段名）',
     res.plainNormLine === true);
  ck('授权与引用折叠保留（报告元数据）', /授权/.test(res.license) && /引用/.test(res.license));
  ck('结果页仍显示分数与百分位（用户要的东西没被藏）',
     /%ile|百分位/.test(c3.vis) && res.isResultPage === true, c3.vis.slice(0, 100));

  /* L2 的门槛/分带型结果页：「门槛」是**该册的用户语义**（手册判读规则），
     不是开发者术语 —— 所以这里只用**收窄的**关键词集（去掉门槛/达到门槛）。 */
  console.log('\n=== 结果页 B：门槛/分带型（DSM5TR-L2-Anger）===');
  await nav(URL_ + '#/scale/DSM5TR-L2-Anger/classic');
  await sleep(1200);
  await ev(`(() => { const d = INST_NOW;
      S.instResp = {}; S.ansVer++;
      d.items.forEach((it, i) => { S.instResp[it.id] = 1 + (i % 4); });
      S.ansVer++; renderTop(); renderStage();
      const btn = document.querySelector('[data-instdone="1"]');
      if (btn && !btn.disabled) btn.dispatchEvent(new MouseEvent('click', {bubbles: true}));
      return 1; })()`);
  await sleep(700);
  const visB = await ev(VIS);
  const hitsB = KEYWORDS.filter(([n, re]) => re.test(visB) && n !== '门槛').map(([n]) => n);
  report('结果页（L2 Anger）', visB);
  ck('门槛型结果页默认视野没有开发者关键词（「门槛」除外——那是该册的用户语义）',
     hitsB.length === 0, JSON.stringify(hitsB));
  const resB = await ev(`(() => {
      const lic = document.querySelector('[data-dev="license"]');
      if (lic) lic.open = true;
      return {hasLicenseFold: !!lic, licenseText: lic ? lic.textContent.slice(0, 120) : null};
    })()`);
  ck('门槛型结果页也有「授权与来源」折叠可查', resB.hasLicenseFold === true && /授权/.test(resB.licenseText || ''),
     JSON.stringify(resB.licenseText));

  /* ══ ⑦ 三档提醒的分级显示（D119 / schema 2.0）══ */
  console.log('\n=== ⑦ 分级显示：量表级 1 次 / 锚点级每组尺子 1 次 / 选项级不重复 ═══');
  /* IPIP-NEO 每页 10 题、正好一把尺子（一个 facet）→ 锚点说明只该出现 1 次 */
  await nav(URL_ + '#/scale/IPIP-NEO/classic');
  ck('IPIP-NEO 就绪（10 题/页、每 facet 10 题）', await waitReady('IPIP-NEO') === true);
  const lv = await ev(`(() => {
      const d = INST_NOW, st = window.EMOHEALTH_STRUCT_IPIP_NEO;
      const items = [...document.querySelectorAll('.institems > li[data-item]')];
      const sids = items.map(li => {
        const s = st.items.find(x => x.id === li.dataset.item);
        return s ? s.response.scale_id : null;
      });
      const vis = ${VIS};
      const instGuides = document.querySelectorAll('[data-guide="instrument"]');
      const anchorGuides = document.querySelectorAll('[data-guide="anchor"]');
      const anchor = anchorGuides[0];
      return {perPage: items.length, distinctSids: [...new Set(sids)].length,
        instrumentGuides: instGuides.length,
        anchorGuides: anchorGuides.length,
        anchorScaleIds: [...anchorGuides].map(g => g.dataset.scaleId),
        anchorNote: anchor ? (anchor.querySelector('[data-guide-part="anchor_note"]') || {}).textContent : null,
        quantNote: anchor ? (anchor.querySelector('[data-guide-part="quantification_note"]') || {}).textContent : null,
        instruction: (document.querySelector('[data-guide="instrument"] [data-guide-part="instruction"]') || {}).textContent,
        timeFrame: (document.querySelector('[data-guide="instrument"] [data-guide-part="time_frame"]') || {}).textContent,
        /* 面向用户的可见文字里，锚点句与量化句各出现几次（必须各 1 次） */
        visAnchorCount: anchor ? vis.split(anchor.textContent.replace(/\\s+/g, ' ').trim()).length - 1 : -1,
        options: document.querySelectorAll('.institems .opt').length,
        meanings: document.querySelectorAll('.institems .opt [data-f="meaning_zh"]').length,
        /* 选项里不得出现上级句子（不重复） */
        optTexts: [...document.querySelectorAll('.institems .opt')].map(b => b.textContent),
        anchorsText: anchor ? anchor.textContent : '',
        /* 内部字段（source / label_source / options_source / 手册…）一个字都不显示 */
        internalLeak: /manual\\.pdf|手册原文|项目自撰|label_source|options_source|不是手册原文/
          .test(document.getElementById('stage').textContent)};
    })()`);
  console.log('    实测（IPIP-NEO 第 1 页）：', JSON.stringify(lv).slice(0, 700));
  ck('量表级提醒每册 1 次（作答指示 + 时间窗都在它里面）',
     lv.instrumentGuides === 1 && !!lv.instruction && /时间窗/.test(lv.timeFrame || ''),
     `instrument=${lv.instrumentGuides}`);
  ck('锚点级：本页 10 题同属一把尺子 → 只出现 1 次',
     lv.perPage === 10 && lv.distinctSids === 1 && lv.anchorGuides === 1,
     `10 题 / ${lv.distinctSids} 把尺子 / ${lv.anchorGuides} 次锚点说明`);
  ck('锚点说明与「没有统一标准」那句都在锚点级（不逐题重复）',
     !!lv.anchorNote && /没有统一标准/.test(lv.quantNote || ''), String(lv.quantNote).slice(0, 60));
  ck('选项级：每个选项都有就地语义，且不含上级句子',
     lv.options > 0 && lv.meanings === lv.options
     && !lv.optTexts.some(t => /没有统一标准/.test(t)),
     `选项 ${lv.options} / 语义 ${lv.meanings}`);
  ck('页面任何地方都不出现内部出处字段（source/label_source/options_source/手册原文）',
     lv.internalLeak === false);

  /* PID-5：单一尺子跨 22 页——每页仍只出现 1 次；换页不重复上级句子 */
  await nav(URL_ + '#/scale/PID-5/classic');
  ck('PID-5 就绪', await waitReady('PID-5') === true);
  const lv5 = await ev(`(() => {
      const pages = document.querySelectorAll('.instpage, .institems');
      return {instrumentGuides: document.querySelectorAll('[data-guide="instrument"]').length,
        anchorGuides: document.querySelectorAll('[data-guide="anchor"]').length,
        anchorScaleId: (document.querySelector('[data-guide="anchor"]') || {}).dataset
          ? document.querySelector('[data-guide="anchor"]').dataset.scaleId : null,
        reverse: !!document.querySelector('[data-guide-part="reverse"]'),
        nonDiag: (document.querySelector('[data-guide-part="non_diagnostic"]') || {}).textContent,
        options: document.querySelectorAll('.institems .opt').length,
        meanings: document.querySelectorAll('.institems .opt [data-f="meaning_zh"]').length,
        firstMeaning: ((document.querySelector('.institems .opt [data-f="meaning_zh"]') || {}).textContent || '').slice(0, 60)};
    })()`);
  console.log('    实测（PID-5 第 1 页）：', JSON.stringify(lv5));
  ck('PID-5：量表级 1 次 + 锚点级 1 次（单把尺子）',
     lv5.instrumentGuides === 1 && lv5.anchorGuides === 1, JSON.stringify(lv5.anchorScaleId));
  /* ⚠️ 不是每个量表都有「非诊断声明」（PID-5 只有反向计分说明；L1/L2 才有非诊断声明）。
     断言要对着**数据实际给了什么**写，不能假设每个量表都齐。 */
  ck('PID-5：反向计分说明在量表级', lv5.reverse === true);
  ck('PID-5：选项级语义（不再带「PID-5 没有规定…」那句研究说明）',
     lv5.meanings === lv5.options && !/没有规定|具体指什么/.test(lv5.firstMeaning),
     lv5.firstMeaning);

  /* L1：按维度的敏感提示（量表级）+ 计数型锚点说明。
     ⚠️ 「内部字段不显示」的判据分两层：
       · **可见**文字里不得出现那类词（用户实际看到的）
       · `scale_guides[*].source`/`label_source`/`options_source` 这些**具体字符串**
         在整份 DOM（含折叠）里都不许出现——这是 task-22 交接的硬要求
         （题目自己的 `text_zh_source`/注记来源是 R1 证据，允许留在「依据」折叠里）。 */
  await nav(URL_ + '#/scale/DSM5TR-L1/classic');
  const lv1 = await ev(`(() => {
      const st = window.EMOHEALTH_STRUCT_DSM5TR_L1;
      const sid = st.items[0].response.scale_id;
      const guide = st.scale_guides[sid] || {};
      const topics = [...document.querySelectorAll('[data-guide-part="topic"]')]
        .map(x => x.textContent.replace(/\\s+/g, ' ').slice(0, 40));
      const all = document.body.textContent;
      const leaked = [guide.source, guide.label_source, guide.options_source]
        .filter(s => s && s.length > 12 && all.includes(s));
      const vis = ${VIS};
      return {instrumentGuides: document.querySelectorAll('[data-guide="instrument"]').length,
        anchorGuides: document.querySelectorAll('[data-guide="anchor"]').length,
        topics: topics, nTopics: topics.length,
        anchorNote: ((document.querySelector('[data-guide="anchor"] [data-guide-part="anchor_note"]') || {}).textContent || '').slice(0, 60),
        firstMeaning: ((document.querySelector('.institems .opt [data-f="meaning_zh"]') || {}).textContent || '').slice(0, 70),
        guideSourceLeakCount: leaked.length,
        visibleInternal: /manual\\.pdf|手册原文|项目自撰|本项目安全策略|label_source|options_source/.test(vis)};
    })()`);
  console.log('    实测（L1）：', JSON.stringify(lv1).slice(0, 500));
  ck('L1：量表级 1 次，含按维度的敏感提示；提示的 source 不显示',
     lv1.instrumentGuides === 1 && lv1.nTopics >= 1 && lv1.visibleInternal === false,
     `${lv1.nTopics} 条敏感提示`);
  ck('L1：scale_guides 的 source/label_source/options_source 在整份 DOM 里都不出现',
     lv1.guideSourceLeakCount === 0, `泄漏 ${lv1.guideSourceLeakCount} 处`);
  ck('L1：锚点级 1 次 + 选项级语义是用户语言（含确切天数、无研究说明）',
     lv1.anchorGuides === 1 && /\d/.test(lv1.firstMeaning)
     && !/手册|推算|印出/.test(lv1.firstMeaning), lv1.firstMeaning);

  /* ══ ⑨ 情景块（schema 2.1 / D121）：3 个量表各抽一题，必须渲染出非空且 ≥20 汉字的
     `[data-f="scenario_zh"]`，且位置在题干之后、作答注记之前 ══
     判据来自用户原话：每题下面那句「一句情景展示（例如什么场景下我更怎么样）」
     是答题必需信息 → 默认可见、不做折叠。此处是**正向断言**：
     数据没到位时它会红——那是预期的（等 T-C/T-D/E/F 生成完再跑终验）。 */
  console.log('\n=== ⑨ 情景块（scenario_zh）：3 个量表各抽一题 ===');
  const SCENE_SCALES = ['PID-5', 'IPIP-NEO', 'DSM5TR-L2-Anger'];
  const cjkLen = s => (String(s || '').match(/[\u4e00-\u9fff]/g) || []).length;
  let sceneAllOk = true, sceneOrderOk = true;
  for (const code of SCENE_SCALES) {
    await nav(URL_ + '#/scale/' + code + '/classic');
    await waitReady(code);
    const sc = await ev(`(() => {
        const li = document.querySelector('.institems > li[data-item]');
        if (!li) return {err: 'no item'};
        const zh = li.querySelector('[data-f="text_zh"]');
        const box = li.querySelector('[data-f="scenario_zh"]');
        const notes = li.querySelector('[data-f="notes_zh"]');
        const kids = [...li.children];
        return {text: box ? box.textContent.replace(/\\s+/g, ' ').trim() : null,
          hasBox: !!box,
          cls: box ? box.className : null,
          /* DOM 顺序：scenario 在 text_zh 之后；有 notes 时在 notes 之前 */
          afterStem: !!(zh && box && kids.indexOf(box) > kids.indexOf(zh)),
          beforeNotes: !notes || !box || kids.indexOf(box) < kids.indexOf(notes),
          folded: !!(box && box.closest('details')),
          /* ⚠️ 比的是**文本节点**（跳过 script/style）：body.textContent 会把
             index.html 自己的源码算进来，那样连注释里出现字段名都会「命中」。 */
          innerFields: (() => {
            const parts = [];
            const walkT = el => {
              for (const c of el.childNodes) {
                if (c.nodeType === 3) parts.push(c.nodeValue);
                else if (c.nodeType === 1 && !/^(SCRIPT|STYLE)$/.test(c.tagName)) {
                  const t = c.getAttribute && c.getAttribute('title');
                  if (t) parts.push(t);
                  walkT(c);
                }
              }
            };
            walkT(document.body);
            return /text_en_verbatim|text_en_repairs/.test(parts.join(' '));
          })()};
      })()`);
    const n = cjkLen(sc.text);
    console.log(`    ${code}：${sc.hasBox ? '情景=' + JSON.stringify(sc.text).slice(0, 70) + `（${n} 汉字）` : '没有情景块'}`);
    ck(`${code}：渲染出非空的情景块且 ≥20 汉字`,
       sc.hasBox === true && n >= 20, `汉字数=${n} text=${JSON.stringify(sc.text).slice(0, 60)}`);
    if (!(sc.hasBox === true && n >= 20)) sceneAllOk = false;
    ck(`${code}：情景块在题干之后、作答注记之前，且不在折叠里`,
       sc.afterStem === true && sc.beforeNotes === true && sc.folded === false,
       JSON.stringify({afterStem: sc.afterStem, beforeNotes: sc.beforeNotes, folded: sc.folded}));
    if (!(sc.afterStem === true && sc.beforeNotes === true && sc.folded === false)) sceneOrderOk = false;
    ck(`${code}：内部字段 text_en_verbatim / text_en_repairs 不出现`,
       sc.innerFields === false);
  }
  ck('3 个量表的情景块全部合格（汇总）', sceneAllOk === true && sceneOrderOk === true);

  /* ══ ⑩ 逐题覆盖（task-40）：译者备忘**永不上界面、永不进导出文件** ══════════
     背景：itemStemHtml 里原来有一条 else if (it.note) 回退，把**译者备忘**
     （「测快感缺失：…」「原文 enjoylife 为排版噪声…」）当注记渲染。PID-5 只有 15/220
     题有情景提醒 → 其余约 205 题回落到备忘，违反 D120。旧守卫只扫「打开的那几页」，
     散落在中间的备忘从没被扫到 —— 这段就是补这个覆盖漏洞。
     覆盖：4 个量表**逐题**（PID-5 全 220 题，不抽样），数据 / DOM / 导出文件三层各断言一次。
     ⚠️ 备忘的前提**没有消失，只是搬到了 data 层**：converge-pack 已把 note/scaffold
     从发前端的量表包里去掉（D120 的纵深防御第一层），界面这层由本段守（第二层）。 */
  console.log('\n=== ⑩ 逐题覆盖：译者备忘绝不上界面、绝不进导出文件（task-40）===');
  const tdbPath = path.join(ROOT, 'data', 'text-db', 'text-db.json');
  const TDB = JSON.parse(fs.readFileSync(tdbPath, 'utf8'));
  const tdbEntries = Array.isArray(TDB.entries) ? TDB.entries : Object.values(TDB.entries || {});
  const memoTexts = [];
  for (const en of tdbEntries) {
    if (!en || typeof en !== 'object') continue;
    if (typeof en.note === 'string' && en.note.trim()) memoTexts.push(en.note.trim());
    const sc = en.scaffold;
    if (sc && typeof sc === 'object') {
      for (const v of Object.values(sc)) if (typeof v === 'string' && v.trim()) memoTexts.push(v.trim());
    }
  }
  const nNote = tdbEntries.filter(x => x && x.note).length;
  const nScaf = tdbEntries.filter(x => x && x.scaffold).length;
  console.log('    data 层对照：text-db ' + tdbEntries.length + ' 条，其中 '
    + nNote + ' 条带 note、' + nScaf + ' 条带 scaffold；抽出 ' + memoTexts.length + ' 段备忘文本');
  ck('对照（前提搬到 data 层、没消失）：text-db 里**仍有大量**译者备忘 → 守卫非空转',
     nNote + nScaf > 100 && memoTexts.length > 100, nNote + ' note + ' + nScaf + ' scaffold');
  /* 按题面英文归一化 → 该题的备忘片段（用于逐题精确对查，避免 O(题×全部备忘)） */
  const normEn = s => String(s || '').toLowerCase().replace(/\s+/g, ' ').trim();
  /* ⚠️ 探针必须是**只可能来自备忘**的片段：
     · 只取**中文**片段（题面本身含英文，ASCII 片段会假阳性）；
     · 且不能是该题自己的 en/zh 文本的一部分（`scaffold` 里有些字段会复述题面）。
     这样才能把「题面正常显示」与「备忘被渲染出来」区分开。 */
  const memoProbesOf = en => {
    const out = [];
    const push = s => {
      const t = String(s == null ? '' : s).trim();
      if (t.length >= 8 && /[\u4e00-\u9fff]/.test(t)) out.push(t.slice(0, 12));
    };
    push(en.note);
    const sc = en.scaffold;
    if (sc && typeof sc === 'object') {
      push(sc.asks); push(sc.loc); push(sc.edge);
      if (Array.isArray(sc.counts)) sc.counts.forEach(push);
    }
    const own = (normEn(en.en) + ' ' + String(en.zh || '').toLowerCase());
    return out.filter(p => own.indexOf(p.toLowerCase()) < 0);
  };
  const probeByEn = {};
  for (const en of tdbEntries) {
    if (!en || typeof en !== 'object') continue;
    const key = normEn(en.en);
    if (!key) continue;
    const use = [...new Set(memoProbesOf(en))];
    if (use.length) probeByEn[key] = use;
  }
  console.log('    可逐题对查的备忘题面：' + Object.keys(probeByEn).length + ' 条');
  ck('逐题对查表非空（每道带备忘的题都能对上自己的备忘片段）',
     Object.keys(probeByEn).length > 100, Object.keys(probeByEn).length + ' 条');

  const PER_ITEM_SCALES = ['PID-5', 'IPIP-NEO', 'DSM5TR-L1', 'DSM5TR-L2-Anger'];
  let perItemTotal = 0, shippedMemoTotal = 0;
  const counts = {};
  for (const code of PER_ITEM_SCALES) {
    await nav(URL_ + '#/scale/' + code + '/classic');
    await waitReady(code);
    const r = await ev(`(async () => {
        for (let i = 0; i < 80; i++) {
          if (INST_NOW && INST_NOW.instrument === ${JSON.stringify(code)}) break;
          await new Promise(r2 => setTimeout(r2, 150));
        }
        const d = INST_NOW;
        const probes = ${JSON.stringify(probeByEn)};
        const norm = s => String(s || '').toLowerCase().replace(/\s+/g, ' ').trim();
        const items = d.items || [];
        const stOf = it => { try { const m = structIndex(d.instrument);
          return m ? m.get(it.id) : null; } catch (e) { return null; } };
        /* ① 发前端的包里不该再有备忘字段（纵深防御第一层） */
        const shipped = items.filter(it => (it.note && String(it.note).trim())
          || (it.scaffold && String(it.scaffold).trim()));
        /* ② 逐题渲染（真实 DOM 容器，离屏）：查 .instnote 元素 + 该题自己的备忘片段 */
        const box = document.createElement('div');
        box.style.cssText = 'position:fixed;left:-9999px;top:0;width:400px';
        document.body.appendChild(box);
        const instnoteIds = [], memoIds = [];
        let withProbe = 0;
        for (const it of items) {
          box.innerHTML = itemStemHtml(it, stOf(it));
          if (box.querySelector('.instnote')) instnoteIds.push(it.id);
          const ps = probes[norm(it.text)];
          if (ps) {
            withProbe++;
            const txt = box.textContent;
            if (ps.some(p => txt.indexOf(p) >= 0)) memoIds.push(it.id);
          }
        }
        /* ③ 整批渲染（所有题同时在场）：.instnote 必须为 0，且备忘样式文案 0 命中 */
        box.innerHTML = items.map(it => itemStemHtml(it, stOf(it))).join('');
        const batchInstnote = box.querySelectorAll('.instnote').length;
        const batchText = box.textContent;
        const MEMO_RES = [[/测[\u4e00-\u9fff]{2,8}：/, '测XX：'], [/排版噪声/, '排版噪声'],
          [/缺空格|漏空格/, '缺空格'], [/直译/, '直译'], [/逐字/, '逐字']];
        const batchPats = MEMO_RES.filter(x => x[0].test(batchText)).map(x => x[1]);
        /* 整批文本里也不许出现任何一条 data 层备忘片段 */
        const allProbes = [];
        for (const k of Object.keys(probes)) for (const p of probes[k]) allProbes.push(p);
        const batchMemoHits = allProbes.filter(p => batchText.indexOf(p) >= 0).slice(0, 3);
        box.innerHTML = '';
        box.remove();
        /* ④ 导出文件：逐题 CSV 与存档 JSON 里一个备忘片段都不许有 */
        const cap = [], orig = window.download;
        window.download = (n, t) => { cap.push({n: n, t: t}); };
        try { instExportCSV(d, catalogEntry(d.instrument));
              instExportJSON(d, catalogEntry(d.instrument)); }
        finally { window.download = orig; }
        const csv = (cap.find(x => /\\.csv$/.test(x.n)) || {}).t || '';
        const js = (cap.find(x => /\\.json$/.test(x.n)) || {}).t || '';
        const exportMemoHits = allProbes.filter(p => csv.indexOf(p) >= 0 || js.indexOf(p) >= 0)
          .slice(0, 3);
        const rows = instRows(d);
        const memoKeys = ['note', 'notes', 'scaffold'].filter(k => rows.some(x => k in x));
        const csvHead = (csv.split(/\\r?\\n/)[0] || '');
        return {code: d.instrument, items: items.length, shippedMemo: shipped.length,
          withProbe: withProbe, instnoteIds: instnoteIds.slice(0, 3), instnoteLeak: instnoteIds.length,
          memoIds: memoIds.slice(0, 3), memoTextLeak: memoIds.length,
          batchInstnote: batchInstnote, batchPats: batchPats, batchMemoHits: batchMemoHits,
          exportMemoHits: exportMemoHits, memoKeys: memoKeys,
          csvHasNoteCol: csvHead.indexOf('注释') >= 0,
          csvCols: csvHead.split(',').length}; })()`);
    if (typeof r === 'string' && r.startsWith('EXC:')) {
      ck(code + '：逐题渲染未抛异常', false, r.slice(0, 160));
      continue;
    }
    perItemTotal += r.items;
    shippedMemoTotal += r.shippedMemo;
    counts[code] = r.items;
    console.log('    ' + code + '：' + r.items + ' 题（其中 ' + r.withProbe + ' 题能对上 data 层备忘）'
      + '｜发前端包带备忘 ' + r.shippedMemo + '｜逐题 .instnote ' + r.instnoteLeak
      + '｜逐题备忘文本 ' + r.memoTextLeak + '｜整批 .instnote ' + r.batchInstnote
      + '｜整批备忘片段 ' + JSON.stringify(r.batchMemoHits)
      + '｜导出含备忘 ' + JSON.stringify(r.exportMemoHits)
      + '｜备注字段 ' + JSON.stringify(r.memoKeys) + '｜逐题CSV ' + r.csvCols + ' 列');
    ck(code + '：发前端的量表包里 **0 条**备忘（note/scaffold 不发货）',
       r.shippedMemo === 0, r.shippedMemo + ' 条');
    ck(code + '：逐题渲染**全部 ' + r.items + ' 题**都不出现 .instnote 元素',
       r.instnoteLeak === 0, JSON.stringify(r.instnoteIds));
    ck(code + '：逐题渲染**全部题**都不把译者备忘正文显示出来',
       r.memoTextLeak === 0, JSON.stringify(r.memoIds));
    ck(code + '：整批渲染后 .instnote = 0，且不出现备忘样式文案（测XX：/排版噪声/缺空格/直译/逐字）',
       r.batchInstnote === 0 && r.batchPats.length === 0,
       JSON.stringify({instnote: r.batchInstnote, pats: r.batchPats}));
    ck(code + '：整批题面文本里**没有**任何 data 层备忘片段',
       r.batchMemoHits.length === 0, JSON.stringify(r.batchMemoHits));
    ck(code + '：逐题 CSV / 存档 JSON 里**没有**任何 data 层备忘片段',
       r.exportMemoHits.length === 0, JSON.stringify(r.exportMemoHits));
    ck(code + '：导出对象里不再有 note / notes / scaffold 字段，逐题 CSV 也不再有「注释」列',
       r.memoKeys.length === 0 && r.csvHasNoteCol === false,
       JSON.stringify({memoKeys: r.memoKeys, csvHasNoteCol: r.csvHasNoteCol}));
  }
  ck('逐题覆盖合计 ≥ 540 题（PID-5 全 220 + IPIP-NEO 全 300 + L1 23 + L2 5）',
     perItemTotal >= 540 && counts['PID-5'] === 220, JSON.stringify(counts));
  ck('4 个量表发前端的备忘合计 = 0（一条都不发）', shippedMemoTotal === 0,
     shippedMemoTotal + ' 条');

  console.log('\n脚本报错:', errs.length ? errs.slice(0, 2) : '无');
  ck('无脚本异常', errs.length === 0);
  ws.close(); ch.kill();
  console.log(fail ? `\n❌ ${fail} 项未通过` : '\n✅ 用户端默认视野（无开发者内容）与可溯源（折叠可查）全部通过');
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error('❌', e.message); process.exit(2); });
