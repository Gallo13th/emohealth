// 验证子页导出真的产出文件，并核对内容自洽（范围/列名/评分行/常模位置/判读）。
//
// D122（task-34）扩展：导出从「一张原始分表」升级为**完整报告**——
//   得分总表（原始分|估计分|置信度 r|百分位|T 分|z 分|距均值 SD 数|±1SD 区间|口径）
//   + 逐维度细则 + 估计与置信度口径 + 常模与参照说明 + 判读（门槛/分带/逐项/T 分型）
//   + 逐题作答 + 授权与免责声明；结果明细 CSV 加宽到同一批列（**空值必须是空字符串**）。
// 本测试分三段跑，覆盖三种常模形态：
//   A. DSM5TR-L2-Anger（分带/T 分型，**无可用常模**）
//   B. PID-5（条件常模 + 9 个性别×年龄分层；**只答一部分**）
//   C. DSM5TR-L1（门槛型，无可用常模；答满 → 结果页）
// ⚠️ 断言数**只增不减**：task-34 前的 18 条全部保留（只改被替换掉的具体字符串），
//    另加 task-34 要求的 5 组新断言（列头齐备 / 部分作答有估计 / 未答维度不给估计 /
//    L1 门槛导出且无百分位 / CSV 空值为空字符串）。
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

/* 真 CSV 解析（含引号转义与 BOM）——⑤ 要求「用真实解析验证，不要只看文本」 */
function parseCSV(text) {
  let s = text.replace(/^\ufeff/, '');
  const rows = []; let row = []; let cell = ''; let q = false;
  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if (q) {
      if (c === '"') { if (s[i + 1] === '"') { cell += '"'; i++; } else q = false; }
      else cell += c;
    } else if (c === '"') q = true;
    else if (c === ',') { row.push(cell); cell = ''; }
    else if (c === '\r') { /* skip */ }
    else if (c === '\n') { row.push(cell); rows.push(row); row = []; cell = ''; }
    else cell += c;
  }
  if (cell !== '' || row.length) { row.push(cell); rows.push(row); }
  return rows;
}

(async () => {
  const dl = fs.mkdtempSync(path.join(os.tmpdir(), 'dl-'));
  const prof = fs.mkdtempSync(path.join(os.tmpdir(), 'pf-'));
  /* ⚠️ 起 Chrome：本机沙箱偶发 `spawn EPERM`（同一命令重试即可成功），
     所以显式挂 error 处理器 + 最多重试 3 次，避免把环境抖动误报成测试失败。 */
  let ch = null, spawnErr = null;
  for (let attempt = 0; attempt < 3 && !ch; attempt++) {
    const c = spawn(CHROME, ['--headless=new', '--no-sandbox', '--disable-gpu',
      '--remote-debugging-port=' + PORT,
      '--user-data-dir=' + prof + (attempt ? '-' + attempt : ''),
      '--window-size=1280,1000', 'about:blank'], {stdio: 'ignore'});
    spawnErr = null;
    c.on('error', e => { spawnErr = e; });
    await sleep(800);
    if (!spawnErr) ch = c;
    else console.log(`  （Chrome spawn 失败 ${spawnErr.code}，重试 ${attempt + 1}/3）`);
  }
  if (!ch) throw new Error('Chrome 起不来（spawn EPERM），非测试问题：'
    + (spawnErr && spawnErr.code));
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
  const list = () => fs.readdirSync(dl).filter(f => !f.endsWith('.crdownload'));
  /* 点某个导出按钮（或直接调导出函数），返回**本次新产出**的那个文件内容 */
  const exportOf = async (kind, ext, directExpr) => {
    const before = new Set(list());
    if (directExpr) {
      await ev(`(() => { ${directExpr}; return 1; })()`);
    } else {
      await ev(`(() => { const b = [...document.querySelectorAll('[data-instexport]')]
          .find(x => x.dataset.instexport === '${kind}');
          if (b) b.dispatchEvent(new MouseEvent('click', {bubbles: true}));
          return !!b; })()`);
    }
    for (let i = 0; i < 24; i++) {
      await sleep(250);
      const fresh = list().filter(f => !before.has(f) && f.endsWith(ext));
      if (fresh.length) return fs.readFileSync(path.join(dl, fresh[0]), 'utf8');
    }
    /* ⚠️ 文件名带 `stamp()`（秒级）——同一秒内导出两次会同名**覆盖**，从而看不到「新文件」。
       此时按 mtime 取最新的那个同扩展名文件（内容就是刚写出的那份）。 */
    const cands = list().filter(f => f.endsWith(ext))
      .map(f => ({f, t: fs.statSync(path.join(dl, f)).mtimeMs}))
      .sort((x, y) => y.t - x.t);
    return cands.length ? fs.readFileSync(path.join(dl, cands[0].f), 'utf8') : '';
  };
  const answerFirst = n => ev(`(() => { let k = 0;
      for (const li of document.querySelectorAll('.institem')) {
        const b = li.querySelector('.opt');
        if (b && k < ${n}) { b.dispatchEvent(new MouseEvent('click', {bubbles: true})); k++; }
      } return k; })()`);
  /* 点**最后一个**选项（= 满分档）：L1 的域分是域内最高分，取满分才能验证
     「达到门槛 → 建议做 Level 2」这条链路（取第一档的话全册都判「未达到」）。 */
  const answerAll = () => ev(`(() => { for (const li of document.querySelectorAll('.institem')) {
      const os = li.querySelectorAll('.opt');
      const b = os[os.length - 1];
      if (b) b.dispatchEvent(new MouseEvent('click', {bubbles: true}));
    } return 1; })()`);

  /* ══════════ A. DSM5TR-L2-Anger（分带/T 分型，无可用常模）══════════ */
  console.log('=== A. DSM5TR-L2-Anger（无可用常模）===');
  await S('Page.navigate', {url: URL_ + '#/scale/DSM5TR-L2-Anger'});
  await sleep(2600);
  await answerAll();
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
  const A = {csv: await exportOf('csv', '.csv'), json: await exportOf('json', '.json'),
    md: await exportOf('md', '.md'), result: await exportOf('result', '.csv')};
  const files = list();
  console.log('  下载目录：', files.join(', ') || '(空)');
  ck('导出了 4 个文件', files.length === 4, files.length + ' 个');
  ck('文件名带量表代码',
     files.every(f => f.startsWith('DSM5TR-L2-Anger')), files.join(' '));

  const csv = A.csv;
  ck('逐题作答 CSV 有中文表头', /题号,题项ID,维度,计分键/.test(csv),
     csv.split('\n')[0].slice(0, 60));
  /* task-40：译者备忘（`it.note`）已从数据与代码里删掉，所以「注释」列**连列带字段一起去掉**——
     留一个恒为空的列会被读者当成「这题没有注释」（Lead 裁决：删列比留空列好）。 */
  const csvHead = csv.split(/\r?\n/)[0].replace(/^\ufeff/, "");
  ck('逐题作答 CSV 表头 = 8 列（不再有「注释」列）',
     csvHead === "题号,题项ID,维度,计分键,英文原题,中文题面,你的作答,作答范围", csvHead);
  ck('逐题作答 CSV **不得**再出现「注释」列 / note 字段', !/注释/.test(csvHead));
  const csvLines = csv.split(/\r?\n/).filter(Boolean);
  ck('CSV 行数 = 表头 + 5 题', csvLines.length === 6, csvLines.length + ' 行');

  let jd = null;
  try { jd = JSON.parse(A.json); } catch (e) { jd = null; }
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

  const md = A.md;
  ck('Markdown 有标题', /^# /.test(md), md.split('\n')[0].slice(0, 50));
  // ← 旧断言「仅含「<code>」」按新文案改写（不是删除：仍要求声明只含本量表）
  ck('Markdown 声明只含本量表', /只含「DSM5TR-L2-Anger」这一套量表/.test(md));
  // ← 旧断言「| 维度 | 分数 |」按新表头改写
  ck('Markdown 有得分总表（新表头）', /\| 维度 \| 原始分 \| 已答\/题数 \| 估计分 \|/.test(md),
     (md.split('\n').find(l => l.startsWith('| 维度 |')) || '').slice(0, 90));
  ck('Markdown 有逐题表', /## 逐题作答/.test(md));
  // ← 旧断言「暂无可用常模」按新文案改写（仍要求说明常模缺失）；
  //    Phase 2：T 分型册子**有 T 分**，所以精确说法是「没有常模**百分位**」
  ck('Markdown 说明常模缺失（T 分型册：没有常模百分位；其余册：没有可用常模）',
     /没有可用常模|没有常模百分位/.test(md),
     (md.match(/(本册没有常模百分位|本量表没有可用常模)[^\n]{0,40}/) || [''])[0]);
  /* D122 / Phase 2：L2 的「为什么没有常模」**按册分支**，且**权威原文优先**——
     Anger 表现为「有 T 分可用（raw→T 转换表），但没有百分位常模」，
     不能再说「T 分表尚未取得」（那是 Sleep 的说法），也不能用通用错句。 */
  const angerReason = await ev(`String((INST_NOW.norms || {}).unavailable_reason || '')`);
  ck('L2 t_score 册（Anger）：导出写「有 T 分 / raw→T 转换表 + 没有百分位常模」',
     /有 T 分/.test(md) && /raw→T 转换表/.test(md) && /没有百分位常模/.test(md),
     (md.match(/原因：[^\n]{0,120}/) || [''])[0]);
  ck('L2 t_score 册（Anger）：照引数据层权威原文（norms.unavailable_reason）',
     angerReason.length > 20 && md.includes(angerReason.slice(0, 30)),
     JSON.stringify({field: angerReason.slice(0, 60), quoted: md.includes(angerReason.slice(0, 30))}));
  ck('L2 t_score 册（Anger）：不得声称「T 分表（确）未取得」（表已在）',
     !/T 分表(确未|尚未)取得/.test(md.slice(md.indexOf('没有可用常模'),
       md.indexOf('没有可用常模') + 500)),
     (md.match(/没有可用常模\*\*：[^\n]{0,90}/) || [''])[0]);
  ck('L2 t_score 册：不得再出现「判读依据是分界/分带/逐项判据」这种通用错句',
     !/判读依据是分界\/分带\/逐项判据/.test(md));

  /* task-34 ①：MD 得分总表同时出现这些列头 */
  const mdHead = md.split('\n').find(l => l.startsWith('| 维度 |')) || '';
  for (const col of ['原始分', '估计分', '置信度 r', 'T 分', 'z 分', '±1SD 区间']) {
    ck(`MD 得分总表有「${col}」列头`, mdHead.includes(col), mdHead.slice(0, 100));
  }
  /* 结果 CSV 表头（新契约）+ 真实解析 */
  const rc = A.result;
  const rcParsed = parseCSV(rc);
  ck('结果 CSV 有列头（新契约：状态/原始分/估计分/置信度 r…)',
     /维度,状态,原始分,估计分,置信度r/.test(rc), rc.split('\n')[0].slice(0, 60));
  ck('结果 CSV 有 1 行维度', rc.split(/\r?\n/).filter(Boolean).length === 2,
     rc.split(/\r?\n/).filter(Boolean).length + ' 行');
  ck('结果 CSV 列头含 实测T分 / 实测z分 / 1SD 上下限 列',
     rcParsed[0].includes('实测T分') && rcParsed[0].includes('实测z分')
     && rcParsed[0].includes('1SD下限') && rcParsed[0].includes('1SD上限')
     && rcParsed[0].includes('实测百分位'),
     rcParsed[0].slice(0, 12).join(','));
  ck('结果 CSV 每行列数与表头一致（真实解析）',
     rcParsed.slice(1).every(r => r.length === rcParsed[0].length),
     rcParsed.map(r => r.length).join('/'));

  /* ══════════ B. PID-5：只答一部分（条件常模 + 分层）══════════ */
  console.log('\n=== B. PID-5（条件常模；只答前 3 题）===');
  /* ⚠️ PID-5 有 220 题，子页**默认进天赋树**（>60 题），没有 `.institem`；
     这里显式走经典逐题路径，并等推断库与参数包就位（面板按需注入）。 */
  await S('Page.navigate', {url: URL_ + '#/scale/PID-5/classic'});
  await sleep(3200);
  const ready = await ev(`(async () => { for (let i = 0; i < 90; i++) {
      if (inferencePayload(S.instCode) && window.EmoHealthInference
          && document.querySelector('.institem')) return true;
      await new Promise(r => setTimeout(r, 150));
    } return false; })()`);
  ck('PID-5 经典逐题 + 推断库/参数包就位', ready === true);
  /* ⚠️ PID-5 经典页的题目顺序是**每个维度先出一道**（不是按维度成块），所以「点前 7 题」
     会得到 7 个维度各 1 题。这里要的是「同一个 facet 答 7/8 题」——
     直接按参数包里的 `dim_items` 注入作答（等价于用户逐题点完那个 facet），
     状态仍由应用自己的 `instScores`/`predictFrom` 计算。 */
  const injected = await ev(`(() => {
      const p = inferencePayload(S.instCode).params;
      const dims = Object.keys(p.dim_items);
      const dim = dims[0], dim2 = dims[1];
      const own = p.dim_items[dim];
      const vals = [3, 2, 3, 2, 3, 2, 3];
      S.instResp = {};
      own.slice(0, 7).forEach((id, i) => { S.instResp[id] = vals[i]; });
      /* 再给**第二个** facet 答 1 题：制造「答了但置信度未达门槛」的那一类，
         用来验证「已作答但信息量不足」与「一题未答」在报告里被分开写 */
      S.instResp[p.dim_items[dim2][0]] = 2;
      S.ansVer++; renderTop(); renderStage();
      const b = (currentPrediction(S.instCode).inferred || {})[dim] || {};
      const b2 = (currentPrediction(S.instCode).inferred || {})[dim2] || {};
      return {dim, n_own: b.n_answered_own, total: own.length,
        allowed: !!b.display_allowed, available: !!b.available,
        r: b.confidence_r, estimate: b.predicted_score,
        dim2, n2: b2.n_answered_own, allowed2: !!b2.display_allowed,
        available2: !!b2.available}; })()`);
  console.log('  注入实测：', JSON.stringify(injected));
  ck('PID-5 造出「同一 facet 答 7/8 题、估计可用」+「另一 facet 答 1 题、置信度未达门槛」两种状态',
     injected && injected.n_own === 7 && injected.total > 7
     && injected.allowed === true && injected.available === true
     && injected.n2 === 1 && injected.allowed2 === true && injected.available2 === false,
     JSON.stringify(injected));
  const bs = await ev(`({answered: Object.keys(S.instResp).length,
      result: !!S.instResult,
      hasInfer: !!(inferencePayload(S.instCode) && window.EmoHealthInference)})`);
  console.log('  实测：', JSON.stringify({injected: injected && injected.dim, ...bs}));
  ck('PID-5 只答了 8 题（7 + 1）、尚未出结果（= 答题进行中）',
     bs.answered === 8 && bs.result === false, JSON.stringify(bs));
  const pmd = await exportOf('md', '.md', `instExportMD(INST_NOW, catalogEntry(S.instCode))`);
  ck('部分作答也能导出 Markdown', pmd.length > 500, pmd.length + ' 字符');

  /* 按**表头列名**取值（列一多就不该再硬编码下标） */
  const pHeadCols = (pmd.split('\n').find(l => l.startsWith('| 维度 |')) || '')
    .split('|').map(x => x.trim());
  const rowOf = name => (pmd.split('\n').find(l => l.startsWith('| ' + name + ' |')) || '')
    .split('|').map(x => x.trim());
  const pRow = rowOf('Anhedonia');
  const cell = k => pRow[pHeadCols.indexOf(k)];
  console.log('  Anhedonia 行：', pRow.slice(0, 12).join(' | '));

  /* ②：部分作答时估计分列有值且带置信度 */
  ck('② 部分作答：估计分列有值（不是「—」）',
     cell('估计分') !== '' && cell('估计分') !== '—', JSON.stringify(cell('估计分')));
  ck('② 部分作答：置信度 r 列有值', cell('置信度 r') !== '' && cell('置信度 r') !== '—',
     JSON.stringify(cell('置信度 r')));
  ck('② 逐维度细则里写明估计是怎么来的（按已答 k 题 / 不等于真实得分）',
     /估计分：/.test(pmd) && /不等于答满时的真实得分/.test(pmd));
  /* 三条口径（Lead 定）：部分作答不给实测位置、但给「按估计分算的位置」并明确标注 */
  ck('② 部分作答：实测百分位/T/z 三列都为空（不得用部分原始分查常模）',
     cell('实测百分位') === '—' && cell('实测 T 分') === '—'
     && cell('实测 z 分') === '—',
     JSON.stringify([cell('实测百分位'), cell('实测 T 分'), cell('实测 z 分')]));
  ck('② 部分作答：给出「估计位置（按估计分）」且带 T/z',
     /%ile/.test(cell('估计位置（按估计分）')) && /T /.test(cell('估计位置（按估计分）')),
     cell('估计位置（按估计分）'));
  ck('② 估计位置明确标注「不是实测位置」',
     /不是实测位置/.test(pmd) && /按\*\*估计分\*\*/.test(pmd),
     (pmd.match(/- \*\*估计位置\*\*[^\n]{0,120}/) || [''])[0]);

  /* ③：本维度一题未答 → 不出现估计与置信度数值 */
  const blockedName = await ev(`(() => { const p = inferencePayload(S.instCode);
      if (!p || !p.params) return null;
      const d = Object.keys(p.params.dim_items).find(x => (p.params.dim_items[x] || [])
        .every(id => !(id in S.instResp)));
      return d ? ((currentPrediction(S.instCode).inferred[d] || {}).name || d) : null; })()`);
  console.log('  未答维度：', blockedName);
  const blockedSec = pmd.slice(pmd.indexOf('## 未答维度'));
  const blockedLine = blockedSec.split('\n').find(l => l.startsWith('| ' + blockedName + ' |')) || '';
  console.log('  未答维度行：', blockedLine.slice(0, 120));
  ck('③ 未答维度出现在「未答维度」表里，且写明按硬规则不给估计',
     blockedLine.includes('本维度一道题都没答') && blockedLine.includes('硬规则'),
     blockedLine.slice(0, 100));
  ck('③ 未答维度的那一行不含估计分/置信度数值',
     !/\|\s*\d+(\.\d+)?\s*\|/.test(blockedLine.replace(/\| \d+\/\d+ \|/, '|')),
     blockedLine.slice(0, 100));
  ck('③ 未答维度不出现在得分总表里',
     !pmd.split('\n').some(l => l.startsWith('| ' + blockedName + ' |') && l.includes('%ile')),
     blockedName);

  /* ── D122 缺陷回归断言（这些断言在修复前**必须是红的**）────────────────────
     ① 已答的维度绝不能被写成「本维度一道题都没答」
     ② 「未答维度」表里绝不允许出现 n>0 的行
     ③ 部分作答的维度绝不能用部分原始分给出实测百分位/T/z
     ④ 授权绝不允许打印内部枚举（copyright_permitted / public_domain …）
     ⑤ 报告时间必须是本地时间（不是裸 UTC） */
  const answeredNames = await ev(`(() => { const p = inferencePayload(S.instCode).params;
      return Object.keys(p.dim_items).filter(d => p.dim_items[d]
        .some(id => id in S.instResp)).map(d => (currentPrediction(S.instCode).inferred[d] || {}).name || d); })()`);
  /* 「已作答但信息量不足」表里应有的维度 = 答过题但**置信度未达门槛**的那些
     （答过且已达门槛的走「有估计」，不该出现在这张表里） */
  const insufficientNames = await ev(`(() => { const pred = currentPrediction(S.instCode);
      return Object.keys(pred.inferred).filter(d => { const b = pred.inferred[d];
        return b && b.display_allowed && !b.available; })
        .map(d => pred.inferred[d].name || d); })()`);
  const mdLines = pmd.split('\n');
  const wrongHardRule = mdLines.filter(l => /本维度一道题都没答/.test(l)
    && /^\| (.+?) \| (\d+)\/\d+ \|/.test(l)
    && +l.replace(/^\| (.+?) \| (\d+)\/\d+ \|.*$/, '$2') > 0);
  ck('回归① 没有任何「n>0 却写一道题都没答」的行', wrongHardRule.length === 0,
     JSON.stringify(wrongHardRule.slice(0, 2)).slice(0, 120));
  const answeredInUnanswered = answeredNames.filter(n =>
    new RegExp('\\| ' + n.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ' \\| 0/').test(
      pmd.slice(pmd.indexOf('## 未答维度'))));
  ck('回归② 已答维度不得出现在「未答维度」表里', answeredInUnanswered.length === 0,
     JSON.stringify(answeredInUnanswered));
  ck('回归② 答了题但置信度未达门槛的维度出现在「已作答但信息量不足」表里（真实原因）',
     insufficientNames.length > 0 && insufficientNames.every(n =>
       new RegExp('\\| ' + n.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ' \\|').test(
         pmd.slice(pmd.indexOf('## 已作答但信息量不足')))),
     JSON.stringify({insufficientNames, answeredNames}));
  ck('回归② 已达门槛、有估计的维度**不**出现在「信息量不足」表里',
     answeredNames.filter(n => !insufficientNames.includes(n)).every(n =>
       !new RegExp('\\| ' + n.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ' \\|').test(
         pmd.slice(pmd.indexOf('## 已作答但信息量不足')))), JSON.stringify(answeredNames));
  /* ③ 部分作答：得分总表里这些维度的「实测百分位/实测 T 分/实测 z 分」必须全为 — */
  const partialRows = mdLines.filter(l => /^\| .+? \| [\d.]+ \| \d+\/\d+ \|/.test(l)
    && !/ \| \d+\/\d+ \| .+ \| .+ \| [\d.]+%ile/.test(l));
  const partialNums = mdLines.filter(l => /^\| (.+?) \| ([\d.]+) \| (\d+)\/(\d+) \|/.test(l)
    && (() => { const m = l.match(/^\| (.+?) \| ([\d.]+) \| (\d+)\/(\d+) \|/);
      return +m[3] < +m[4]; })()
    && /%ile/.test(l.split('|').slice(6).join('|')));
  ck('回归③ 部分作答的维度不给实测百分位/T/z（不得用部分原始分查常模）',
     partialNums.length === 0, JSON.stringify(partialNums.slice(0, 2)).slice(0, 140));
  ck('回归③ 报告里明确写了「不用部分作答的原始分查常模」',
     /不用部分作答的原始分查常模|不用部分分查表/.test(pmd));
  ck('回归④ 授权是给人读的标签，不是内部枚举',
     !/copyright_permitted|public_domain|cc_by|all_rights_reserved/.test(pmd)
     && /授权：/.test(pmd),
     (pmd.match(/- 授权：[^\n]*/) || [''])[0]);
  ck('回归⑤ 报告时间给的是本地时间（含时区名），不是裸 UTC',
     /报告生成时间：\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}（.+?，本地时间）/.test(pmd),
     (pmd.match(/- 报告生成时间：[^\n]*/) || [''])[0]);
  ck('回归⑥ 任何报告都不得出现「归档中未找到」这类弱化措辞',
     !/归档中未找到/.test(pmd));

  /* ④-前哨：分层披露 */
  ck('PID-5 导出写明实际用的分层 = 总体层 overall',
     /常模分层：\*\*overall\*\*/.test(pmd), (pmd.match(/常模分层[^\n]{0,50}/) || [''])[0]);
  /* ⚠️ task-39 契约变更：现在**可以**填性别年龄（可选、只本机），于是导出不再说
     「不采集 / 不对任何个人做分层校正」，而是**写明本次实际用了哪一层**。
     旧断言按新契约改写，并**增加**两条（未填=默认总体层 + 参数的来源与可选性）。 */
  ck('PID-5 导出写明「本次实际使用的分层：`overall`」（未填时=默认总体层）',
     /本次实际使用的分层：`overall`/.test(pmd) && /默认总体层/.test(pmd),
     (pmd.match(/本次实际使用的分层[^\n]{0,60}/) || [''])[0]);
  ck('PID-5 导出说明该参数可选/只本机（不填就用总体层）',
     /只存在本机/.test(pmd) && /不填则用总体层|填了就会用对应分层/.test(pmd),
     (pmd.match(/分层说明[^\n]{0,80}/) || [''])[0]);
  ck('PID-5 导出**不再**出现「不采集用户的性别与年龄」这类已过期表述',
     !/不采集用户的性别与年龄/.test(pmd));
  ck('PID-5 导出报出复核过的分层敏感度（46 / 32.98 个百分点）',
     /45\.93 个百分点/.test(pmd) && /32\.98 个百分点/.test(pmd),
     (pmd.match(/分层敏感度[^\n]{0,80}/) || [''])[0]);
  ck('PID-5 导出照抄投影说明（GESIS / 贝叶斯桥接）',
     /GESIS/.test(pmd) && /贝叶斯桥接/.test(pmd));

  /* B2：答满 → 结果页 → 结果明细 CSV（确认「常模分层 / 分层是否默认」两列如实） */
  await ev(`(() => { S.instResp = {}; S.ansVer++;
      INST_NOW.items.forEach((it, i) => { S.instResp[it.id] = i % 4; });
      S.ansVer++; renderTop(); renderStage();
      const b = document.querySelector('[data-instdone="1"]');
      if (b && !b.disabled) b.dispatchEvent(new MouseEvent('click', {bubbles: true}));
      return 1; })()`);
  await sleep(1200);
  const pResultOk = await ev(`!!S.instResult && !!document.querySelector('[data-instexport="result"]')`);
  ck('PID-5 答满后能出结果页与结果明细导出', pResultOk === true);
  const pcsv = await exportOf('result', '.csv');
  const pParsed = parseCSV(pcsv);
  const pHead = pParsed[0] || [];
  const pRows = pParsed.slice(1).filter(r => r[0]);
  const cCell = pHead.indexOf('常模分层');
  const cDef = pHead.indexOf('分层是否默认');
  const cFb = pHead.indexOf('分层是否回退');
  const cSrc = pHead.indexOf('分层来源');
  const cPctl = pHead.indexOf('百分位');
  console.log('  PID-5 结果 CSV 首行：', JSON.stringify(pRows[0] && pRows[0].slice(0, 8)));
  ck('CSV 有「常模分层 / 分层来源 / 分层是否默认 / 分层是否回退」四列',
     cCell >= 0 && cSrc >= 0 && cDef >= 0 && cFb >= 0, pHead.slice(19, 24).join(','));
  ck('CSV 的常模分层列全部是 overall（不再恒定落到 f [18,35)）',
     pRows.length > 0 && pRows.every(r => r[cCell] === 'overall'),
     JSON.stringify([...new Set(pRows.map(r => r[cCell]))]));
  ck('CSV 的分层是否默认列 = 是、分层是否回退列 = 否（如实）',
     pRows.every(r => r[cDef] === '是' && r[cFb] === '否'),
     JSON.stringify({def: [...new Set(pRows.map(r => r[cDef]))],
       fb: [...new Set(pRows.map(r => r[cFb]))]}));
  ck('CSV 的分层来源列写明「默认总体层 overall」',
     pRows.every(r => /默认总体层 overall/.test(r[cSrc])),
     JSON.stringify([...new Set(pRows.map(r => r[cSrc]))]));
  ck('CSV 里条件常模的百分位与 T 分确实有值（不是空列）',
     pRows.some(r => r[cPctl] !== '' && r[pHead.indexOf('T分')] !== ''),
     JSON.stringify({pctl: pRows[0] && pRows[0][cPctl], T: pRows[0] && pRows[0][pHead.indexOf('T分')]}));

  /* ══════════ C. DSM5TR-L1（门槛型；答满 → 结果页）══════════ */
  console.log('\n=== C. DSM5TR-L1（门槛型，无可用常模）===');
  await S('Page.navigate', {url: URL_ + '#/scale/DSM5TR-L1'});
  await sleep(2800);
  // L1 有 23 题，分 3 页：每页答完翻页
  for (let page = 0; page < 5; page++) {
    await answerAll();
    await sleep(300);
    const more = await ev(`(() => { const b = [...document.querySelectorAll('[data-page]')]
        .find(x => +x.dataset.page > 0 && !x.disabled);
        return b ? b.dataset.page : null; })()`);
    const done = await ev(`(() => { const b = document.querySelector('[data-instdone]');
        return b && !b.disabled; })()`);
    if (done) break;
    if (!more) break;
    await ev(`(() => { const b = [...document.querySelectorAll('[data-page]')]
        .find(x => +x.dataset.page > 0 && !x.disabled);
        if (b) b.dispatchEvent(new MouseEvent('click', {bubbles: true})); return 1; })()`);
    await sleep(600);
  }
  await ev(`(() => { const b = document.querySelector('[data-instdone]');
      if (b && !b.disabled) b.dispatchEvent(new MouseEvent('click',{bubbles:true}));
      return 1; })()`);
  await sleep(700);
  const ls = await ev(`({answered: Object.keys(S.instResp).length, result: !!S.instResult,
      hasJudgment: !!(instJudgment(INST_NOW) && instJudgment(INST_NOW).kind === 'threshold')})`);
  console.log('  实测：', JSON.stringify(ls));
  ck('L1 答满并算出结果（门槛判读可用）',
     ls.result === true && ls.hasJudgment === true, JSON.stringify(ls));
  const lmd = await exportOf('md', '.md');
  const lcsv = await exportOf('result', '.csv');

  /* ④：L1 导出含门槛判读、且不含任何百分位数字 */
  ck('④ L1 导出含「门槛判读」章节', /## 门槛判读/.test(lmd),
     (lmd.match(/##[^\n]*判读[^\n]*/) || [''])[0]);
  ck('④ L1 导出给出门槛判读表（域｜域分｜门槛｜判定｜建议）与「达到门槛」判定',
     /\| 域 \| 域分 \| 门槛 \| 判定 \| 建议 \|/.test(lmd) && /达到门槛/.test(lmd));
  ck('④ L1 导出含门槛阈值列（≥N + 门槛标签，如 Mild or greater）',
     /≥\d+ /.test(lmd) && /Mild or greater|Slight or greater/.test(lmd),
     JSON.stringify({hasGe: /≥\d+ /.test(lmd),
       sample: (lmd.match(/^\| Depression \|[^\n]*/m) || [''])[0].slice(0, 80)}));
  ck('④ L1 导出说明没有可用常模的原因',
     /没有可用常模/.test(lmd), (lmd.match(/没有可用常模[^\n]{0,60}/) || [''])[0]);
  /* 缺陷 6（Lead 定）：**照引数据层权威原文**（打包层已下发 norms.unavailable_reason），
     不能再出现运行时那句被弱化的「归档中未找到可溯源的常模」 */
  ck('回归⑥a L1 导出照引权威 unavailable_reason（含「门槛型筛查…手册不提供常模表」）',
     /APA 把本册设计为\*\*门槛型筛查\*\*/.test(lmd) && /手册不提供常模表/.test(lmd),
     (lmd.match(/原因：[^\n]{0,80}/) || [''])[0]);
  ck('回归⑥a2 L1 导出写明原因来源是 data/norms/…json（原文照引），且无弱化措辞',
     /原因来源：data\/norms\/dsm5tr-l1\.json/.test(lmd) && !/归档中未找到/.test(lmd),
     (lmd.match(/- 原因来源：[^\n]*/) || [''])[0]);
  ck('④ L1 导出不含任何百分位数字（无 N%ile）',
     !/\d+\s*%ile/.test(lmd) && !/T 分 \d/.test(lmd) && !/z 分 -?\d/.test(lmd),
     (lmd.match(/\d+\s*%ile/) || ['（无）'])[0]);
  ck('④ L1 结果 CSV 不含百分位数值（该册无常模）',
     !/\d+\s*%ile/.test(lcsv));

  /* ④ 加强：L1 现在用**满分档**作答（answerAll 点最后一个选项），
     所以「达到门槛 → 建议做 Level 2」这条链路必须在同一份报告里成立 */
  console.log('  Depression 行：',
    ((lmd.match(/^\| Depression \|[^\n]*/m) || [''])[0]).slice(0, 90));
  ck('④b 达到门槛时给出「建议做 Level 2—X」的下游指引',
     /建议做 Level 2—/.test(lmd), ((lmd.match(/建议做 Level 2—[^\s|）]*/) || [''])[0]));
  ck('④b 满分作答时域判定为「达到门槛」且给出建议',
     /^\| Depression \| 4 \|.*达到门槛.*建议做 Level 2—/m.test(lmd),
     ((lmd.match(/^\| Depression \|[^\n]*/m) || [''])[0]).slice(0, 90));
  await S('Page.navigate', {url: URL_ + '#/scale/DSM5TR-L1/classic'});
  await sleep(2400);
  const craft = await ev(`(() => {
      /* 只答 Depression 域的第 1 题（l1_01）、值 0：域分 = max = 0 < 门槛 2，且未答满 */
      S.instResp = { l1_01: 0 }; S.ansVer++;
      S.instResult = { rows: instScores(INST_NOW, S.instResp) };
      const ce = catalogEntry(S.instCode); instExportMD(INST_NOW, ce);
      const J = instJudgment(INST_NOW);
      const d = (J.domains || []).find(x => x.domain === 'Depression');
      return {value: d && d.value, complete: d && d.complete, reached: d && d.reached,
        decidable: d && d.decidable}; })()`);
  await sleep(900);
  const crafted = await ev(`window.__lastMd || ''`);
  const cMd = crafted || (await (async () => {
    /* 上面直接调导出会触发下载，取最新 md 文件 */
    const files = fs.readdirSync(dl).filter(f => f.endsWith('.md'));
    files.sort((a, b) => fs.statSync(path.join(dl, b)).mtimeMs
      - fs.statSync(path.join(dl, a)).mtimeMs);
    return files.length ? fs.readFileSync(path.join(dl, files[0]), 'utf8') : '';
  })());
  console.log('  构造实测：', JSON.stringify(craft));
  ck('回归（附2）1/2 已答且低于门槛 → 判读标为「未答完，不能判定」',
     craft && craft.value === 0 && craft.complete === false && craft.decided !== true
     && craft.decidable === false && /未答完，不能判定/.test(cMd),
     JSON.stringify(craft));
  ck('回归（附2）未答满时**不得**输出「未达到」结论（Depression 行）',
     !/^\| Depression \| 0 \|.*未达到/m.test(cMd),
     (cMd.match(/^\| Depression \|[^\n]*/m) || [''])[0].slice(0, 90));
  ck('回归（附2）报告里点明「未答完不能判未达到」的理由',
     /未答的题可能是高分/.test(cMd));
  ck('④ L1 导出对未答域写「未答」（判读三态齐全：达到门槛/未达到/未答）',
     /达到门槛/.test(cMd) && /未答/.test(cMd), '');

  /* ⑤：CSV 空值为空字符串（真实解析，不看文本） */
  const lParsed = parseCSV(lcsv);
  const head = lParsed[0];
  const iEst = head.indexOf('估计分'), iPct = head.indexOf('实测百分位');
  const iT = head.indexOf('实测T分'), iZ = head.indexOf('实测z分');
  const iSdLo = head.indexOf('1SD下限');
  const row0 = lParsed[1] || [];
  console.log('  L1 结果 CSV 首行：', JSON.stringify(row0.slice(0, 14)).slice(0, 200));
  ck('⑤ CSV 表头含 估计分/实测百分位/实测T分/实测z分/1SD下限 列',
     iEst >= 0 && iPct >= 0 && iT >= 0 && iZ >= 0 && iSdLo >= 0,
     JSON.stringify({iEst, iPct, iT, iZ, iSdLo}));
  ck('⑤ 无常模时百分位/T/z/±1SD 单元格是**空字符串**（不是「—」）',
     row0[iPct] === '' && row0[iT] === '' && row0[iZ] === '' && row0[iSdLo] === '',
     JSON.stringify({pctl: row0[iPct], T: row0[iT], z: row0[iZ], sd_lo: row0[iSdLo]}));
  ck('⑤ CSV 里没有任何单元格是「—」或 null/undefined（可被程序直接读）',
     lParsed.every(r => r.every(c => c !== '—' && c !== 'null' && c !== 'undefined')),
     '');
  ck('⑤ 无常模原因写进了 CSV 的专门一列（不留一堆空格）',
     row0[head.indexOf('无可用常模原因')] && row0[head.indexOf('无可用常模原因')].length > 5,
     String(row0[head.indexOf('无可用常模原因')]).slice(0, 60));

  /* ══════════ E. Phase 2：L2 的 T 分（官方 raw→T 查表）══════════
     三册表已入档（Anxiety 7a / Depression 8b / Anger 5a），Sleep 仍为 null。
     断言用的是**册内印出的算例值**（Anxiety raw 23 → 63.8；Depression raw 27 → 64.4；
     Anger raw 19 → 67.2），所以「查表 vs 自算」能立刻分辨。 */
  console.log('\n=== E. L2 T 分（查表）===');
  const seedSum = (target) => ev(`(() => {
      const dims = Object.keys(INST_NOW.scoring || {});
      const of = INST_NOW.scoring[dims[0]].of || [];
      const rf = INST_NOW.response_format, lo = rf.min, hi = rf.max;
      let rest = ${target} - lo * of.length;
      const vals = of.map(() => lo);
      for (let i = 0; i < of.length && rest > 0; i++) {
        const add = Math.min(hi - lo, rest); vals[i] += add; rest -= add;
      }
      S.instResp = {}; S.ansVer++;
      of.forEach((x, i) => { S.instResp[x] = vals[i]; });
      S.ansVer++; renderTop(); renderStage();
      S.instResult = { rows: instScores(INST_NOW, S.instResp) };
      renderStage();
      const row = S.instResult.rows[0];
      const J = instJudgment(INST_NOW);
      const body = document.getElementById('stage').textContent.replace(/\\s+/g, ' ');
      return {raw: row && row.value, complete: row && row.complete,
        n_items: of.length, lo, hi,
        t: J.tscore && J.tscore.T, se: J.tscore && J.tscore.SE,
        found: !!(J.tscore && J.tscore.found),
        pageT: body.match(/T = ([\\d.]+)/) ? body.match(/T = ([\\d.]+)/)[1] : null,
        pageSD: /个标准差/.test(body)}; })()`);
  const T_CASES = [
    ['DSM5TR-L2-Anxiety', 23, 63.8, 2.2, 7],
    ['DSM5TR-L2-Depression', 27, 64.4, null, 8],
    ['DSM5TR-L2-Anger', 19, 67.2, null, 5],
    /* ⚠️ Sleep 的**锚点必须用官方 2023 表的值**：APA 册子（©2008-2012）的算例
       raw 27 → 57.3 与官方表 raw 27 → 59.1 不一致（官方明文「2014-05-22 修订，
       此前数据应重算」）。本项目采用官方现行表 → 用 raw 40 → 77.5 做锚点。 */
    ['DSM5TR-L2-Sleep', 40, 77.5, 4.2, 8],
  ];
  for (const [code, raw, wantT, wantSE, wantN] of T_CASES) {
    await S('Page.navigate', {url: URL_ + '#/scale/' + code + '/classic'});
    await sleep(2400);
    const r = await seedSum(raw);
    console.log(`  ${code}：raw=${r && r.raw} T=${r && r.t} SE=${r && r.se}（期望 ${wantT}/${wantSE}）`);
    ck(`E. ${code} raw=${raw} → 查表 T=${wantT}`,
       r && r.complete === true && r.raw === raw && r.t === wantT,
       JSON.stringify({raw: r && r.raw, t: r && r.t, complete: r && r.complete}));
    if (wantSE != null) {
      ck(`E. ${code} 的 SE=${wantSE}（来自同一张表，不是自算）`, r && r.se === wantSE,
         String(r && r.se));
    }
    ck(`E. ${code} 结果页显示 T = ${wantT} 且给出「… 个标准差」衡量`,
       r && r.pageT === String(wantT) && r.pageSD === true,
       JSON.stringify({pageT: r && r.pageT, pageSD: r && r.pageSD}));
    /* 导出（MD + CSV）必须带 T / SE / 来源 / 溯源 */
    const emd = await exportOf('md', '.md', `instExportMD(INST_NOW, catalogEntry(S.instCode))`);
    const ecsv = await exportOf('result', '.csv',
      `instExportResultCSV(INST_NOW, catalogEntry(S.instCode))`);
    ck(`E. ${code} 导出 MD 的 T 分型判读段给出 T=${wantT} 与「查表值」`,
       new RegExp('T = ' + String(wantT).replace('.', '\\.')).test(emd)
       && /查表值/.test(emd) && !/T 分表\*\*尚未取得/.test(emd),
       (emd.match(/T = [\d.]+[^\n]{0,50}/) || [''])[0]);
    ck(`E. ${code} 导出 MD 带转换表溯源（表名 + file/page）`,
       /转换表来源/.test(emd) && /archive\//.test(emd),
       (emd.match(/- 转换表来源：[^\n]{0,80}/) || [''])[0]);
    const eHead = parseCSV(ecsv)[0] || [];
    const eRow = parseCSV(ecsv)[1] || [];
    ck(`E. ${code} 结果 CSV 的 实测T分 / SE / T分来源 列有值（SE 与查表值一致）`,
       eRow[eHead.indexOf('实测T分')] === String(wantT)
       && (wantSE == null
         ? Number(eRow[eHead.indexOf('SE')]) >= 0 && eRow[eHead.indexOf('SE')] !== ''
         : eRow[eHead.indexOf('SE')] === String(wantSE))
       && /查表/.test(eRow[eHead.indexOf('T分来源')] || ''),
       JSON.stringify({T: eRow[eHead.indexOf('实测T分')], SE: eRow[eHead.indexOf('SE')],
         src: eRow[eHead.indexOf('T分来源')], inPageSE: r && r.se}));
    ck(`E. ${code} 导出 MD 说明「没有常模百分位」（T 来自转换表，不是百分位）`,
       /不给百分位|没有常模百分位|百分位：\*\*不可用\*\*/.test(emd));
  }

  /* E-边界：未答满 / 越界 / 无表 */
  await S('Page.navigate', {url: URL_ + '#/scale/DSM5TR-L2-Anxiety/classic'});
  await sleep(2400);
  const ePartial = await ev(`(() => {
      const of = INST_NOW.scoring[Object.keys(INST_NOW.scoring)[0]].of;
      S.instResp = {}; S.ansVer++;
      of.slice(0, 3).forEach(x => { S.instResp[x] = 5; });
      S.ansVer++; renderTop(); renderStage();
      S.instResult = { rows: instScores(INST_NOW, S.instResp) }; renderStage();
      const row = S.instResult.rows[0], J = instJudgment(INST_NOW);
      return {complete: row.complete, n_answered: row.n_answered,
        found: J.tscore.found, reason: J.tscore.reason}; })()`);
  console.log('  E-边界（未答满）：', JSON.stringify(ePartial));
  ck('E③ 未答满的域不给 T，且写明「域分只是下界、T 会偏低」',
     ePartial.complete === false && ePartial.found === false
     && /下界/.test(ePartial.reason) && /偏低/.test(ePartial.reason), ePartial.reason);
  const eRange = await ev(`(() => {
      const hi = instTScoreDetail(INST_NOW, 99), lo = instTScoreDetail(INST_NOW, 3);
      const ok = instTScoreDetail(INST_NOW, 23);
      return {rr: INST_NOW.criteria.tscore_table.raw_range,
        hi: {found: hi.found, reason: hi.reason}, lo: {found: lo.found, reason: lo.reason},
        ok: ok.found, okT: ok.T}; })()`);
  console.log('  E-边界（越界）：', JSON.stringify(eRange));
  ck('E④ 原始分超出转换表范围（99 / 3）→ 不给 T，且写明「不做外推」',
     eRange.hi.found === false && eRange.lo.found === false
     && /超出转换表范围/.test(eRange.hi.reason) && /外推/.test(eRange.hi.reason)
     && /外推/.test(eRange.lo.reason), JSON.stringify(eRange.hi));
  ck('E④ 值域内（23）→ 正常查表（T=63.8）', eRange.ok === true && eRange.okT === 63.8,
     JSON.stringify(eRange.okT));
  /* Sleep：survey-pid5 在 Phase 2 中也把表补上了 → **数据驱动**：
     有表就断言 T 显示；无论数据如何，都另外验证「表缺失 → 不给 T」这条分支（临时藏表）。 */
  const sleepInfo = await ev(`(() => {
      const of = INST_NOW.scoring[Object.keys(INST_NOW.scoring)[0]].of;
      S.instResp = {}; S.ansVer++;
      of.forEach(x => { S.instResp[x] = 2; });
      S.ansVer++; renderTop(); renderStage();
      S.instResult = { rows: instScores(INST_NOW, S.instResp) }; renderStage();
      const J = instJudgment(INST_NOW);
      const body = document.getElementById('stage').textContent.replace(/\\s+/g, ' ');
      return {hasTable: !!INST_NOW.criteria.tscore_table,
        ts: J.tscore ? {found: J.tscore.found, T: J.tscore.T, reason: J.tscore.reason} : null,
        pageNoT: !/T = \\d/.test(body), saysMissing: /尚未取得/.test(body),
        reason: String((INST_NOW.norms || {}).unavailable_reason
          || (INST_NOW.criteria || {}).pending_reason || '')}; })()`);
  console.log('  E-边界（Sleep）：', JSON.stringify(sleepInfo).slice(0, 260));
  if (sleepInfo.hasTable) {
    ck('E② Sleep 的 T 分表已入档（数据比 Lead 交办时更新）→ 结果页给出查表 T、不说「尚未取得」',
       sleepInfo.ts && sleepInfo.ts.found === true && sleepInfo.pageNoT === false
       && sleepInfo.saysMissing === false, JSON.stringify(sleepInfo.ts));
    const eSleepMd = await exportOf('md', '.md',
      `instExportMD(INST_NOW, catalogEntry(S.instCode))`);
    ck('E② Sleep 导出写「有 T 分可用」并照引数据层原文',
       /有 T 分/.test(eSleepMd) && sleepInfo.reason.length > 10
       && eSleepMd.includes(sleepInfo.reason.slice(0, 24)),
       JSON.stringify({mdLen: eSleepMd.length, field: sleepInfo.reason.slice(0, 40)}));
  } else {
    ck('E② Sleep（tscore_table=null）不给 T，页面保持「尚未取得」',
       sleepInfo.ts === null && sleepInfo.pageNoT === true && sleepInfo.saysMissing === true,
       JSON.stringify(sleepInfo));
  }
  /* ⚠️ 表缺失分支必须始终可测（这是将来任何「表还没入档」的册子的路径）：
     把 `criteria.tscore_table` 与 `norms.unavailable_reason` **一起**藏掉
     （后者是权威原文，若只说「没有表」它会说「有 T 分可用」）→ 页面/导出都要明示缺失、不给 T。 */
  const noTable = await ev(`(() => {
      const savedT = INST_NOW.criteria.tscore_table;
      const savedR = (INST_NOW.norms || {}).unavailable_reason;
      INST_NOW.criteria.tscore_table = null;
      if (INST_NOW.norms) INST_NOW.norms.unavailable_reason = undefined;
      renderStage();
      const body = document.getElementById('stage').textContent.replace(/\\s+/g, ' ');
      const J = instJudgment(INST_NOW);
      const R = instReport(INST_NOW, catalogEntry(S.instCode));
      INST_NOW.criteria.tscore_table = savedT;
      if (INST_NOW.norms) INST_NOW.norms.unavailable_reason = savedR;
      renderStage();
      return {t: J.tscore, pageNoT: !/T = \\d/.test(body),
        saysMissing: /尚未取得/.test(body),
        reason: R.norm_notes.unavailable_reason}; })()`);
  ck('E② 表缺失分支：tscore_table=null → 判读不给 T、页面明示「尚未取得」',
     noTable.t === null && noTable.pageNoT === true && noTable.saysMissing === true,
     JSON.stringify({t: noTable.t, pageNoT: noTable.pageNoT, saysMissing: noTable.saysMissing}));
  ck('E② 表缺失分支：导出原因写「T 分表尚未取得」并引数据层 pending_reason/原文',
     /尚未取得/.test(noTable.reason || '')
     && /(表不在册子里|没有表|scoring manual|未取得)/.test(noTable.reason || ''),
     (noTable.reason || '').slice(0, 90));
  await S('Page.navigate', {url: URL_ + '#/scale/DSM5TR-L2-Mania/classic'});
  await sleep(2200);
  const eCut = await ev(`(() => {
      const of = INST_NOW.scoring[Object.keys(INST_NOW.scoring)[0]].of;
      S.instResp = {}; S.ansVer++;
      of.forEach(x => { S.instResp[x] = 5; });
      S.ansVer++; renderTop(); renderStage();
      S.instResult = { rows: instScores(INST_NOW, S.instResp) }; renderStage();
      const J = instJudgment(INST_NOW);
      return {hasTable: !!INST_NOW.criteria.tscore_table, ts: J.tscore,
        kind: (INST_NOW.criteria || {}).kind}; })()`);
  ck('E. cutoff 型册子（Mania）不算 T（没有转换表 → 不硬算）',
     eCut.kind === 'cutoff' && eCut.hasTable === false && eCut.ts === null,
     JSON.stringify(eCut));

  /* E-分带（Phase 2）：`lo`/`hi` 为 null = 无界 → 必须 ±∞ 特判（JS 里 null<x 会静默为真）。
     ⚠️ 断言**按运行时实际分带**驱动（数据侧仍在补档，档数会变），不硬编 4 档。 */
  await S('Page.navigate', {url: URL_ + '#/scale/DSM5TR-L2-Anxiety/classic'});
  await sleep(2400);
  const bandCheck = await ev(`(() => {
      const bands = INST_NOW.criteria.bands || [];
      const pick = t => { const b = bands.find(x => bandHit(x, t)); return b ? b.label : null; };
      const loUnb = bands.findIndex(x => x.lo == null);
      const hiUnb = bands.findIndex(x => x.hi == null);
      const out = {n: bands.length, labels: bands.map(b => b.label),
        loUnb: loUnb, hiUnb: hiUnb,
        bandHitNull: bandHit(bands[0], null) === false,
        hasSource: !!(INST_NOW.criteria.bands_source || {}).file};
      /* 无下界档：取它 hi 以下的某个值必须命中它 */
      if (loUnb >= 0) {
        const b = bands[loUnb];
        out.loProbe = pick((b.hi == null ? 50 : b.hi) - 0.1);
        out.loExpect = b.label;
      }
      /* 无上界档：取它 lo 以上的大值必须命中它 */
      if (hiUnb >= 0) {
        const b = bands[hiUnb];
        out.hiProbe = pick((b.lo == null ? 70 : b.lo) + 100);
        out.hiExpect = b.label;
      }
      /* 内部边界（若有）：把某个 lo>低界 的档的 lo 值喂进去，必须命中该档 */
      const mid = bands.findIndex(x => x.lo != null && x.lo > 0);
      if (mid >= 0) { out.midProbe = pick(bands[mid].lo); out.midExpect = bands[mid].label; }
      return out; })()`);
  console.log('  E-分带实测：', JSON.stringify(bandCheck).slice(0, 260));
  ck('E-分带：无界档（lo/hi=null）按 ±∞ 处理，落点正确',
     bandCheck.n >= 2
     && (bandCheck.loUnb < 0 || bandCheck.loProbe === bandCheck.loExpect)
     && (bandCheck.hiUnb < 0 || bandCheck.hiProbe === bandCheck.hiExpect),
     JSON.stringify(bandCheck));
  ck('E-分带：档的内部下界值命中该档（边界不看漏）',
     bandCheck.midProbe === undefined || bandCheck.midProbe === bandCheck.midExpect,
     JSON.stringify({probe: bandCheck.midProbe, expect: bandCheck.midExpect}));
  ck('E-分带：null 分数不命中任何档（不会把 null 当 0 算）',
     bandCheck.bandHitNull === true);
  ck('E-分带：数据层给了分带出处（bands_source.file）', bandCheck.hasSource === true);
  /* 达到最高档的作答 → 判读带出分带 label + 分带出处（与 T 表出处分开） */
  const bandRow = await seedSum(40);   // Anxiety raw 40 → T 81.6 ⇒ 最高档
  const bandMd = await exportOf('md', '.md', `instExportMD(INST_NOW, catalogEntry(S.instCode))`);
  const expectBand = bandCheck.labels[bandCheck.labels.length - 1];
  ck('E-分带：导出给出分带 label（T 落在哪一档）',
     new RegExp('分带：\\*\\*' + expectBand + '\\*\\*').test(bandMd),
     JSON.stringify({expect: expectBand, got: (bandMd.match(/分带：[^\n]{0,30}/) || [''])[0]}));
  ck('E-分带：**分带来源**与**转换表来源**分开标注（不合并成一句）',
     /分带来源：`archive\/scales\//.test(bandMd) && /转换表来源：`archive\//.test(bandMd)
     && /不是同一处/.test(bandMd),
     JSON.stringify({band: (bandMd.match(/分带来源：[^\n]{0,50}/) || [''])[0],
       table: (bandMd.match(/转换表来源：[^\n]{0,50}/) || [''])[0]}));
  const bandCsv = await exportOf('result', '.csv',
    `instExportResultCSV(INST_NOW, catalogEntry(S.instCode))`);
  const bHead = parseCSV(bandCsv)[0] || [];
  const bRow = parseCSV(bandCsv)[1] || [];
  ck('E-分带：结果 CSV 有「T分带 / 分带来源」列且有值',
     bRow[bHead.indexOf('T分带')] === expectBand
     && /archive\/scales\//.test(bRow[bHead.indexOf('分带来源')] || ''),
     JSON.stringify({band: bRow[bHead.indexOf('T分带')],
       src: bRow[bHead.indexOf('分带来源')]}));

  ws.close(); ch.kill();
  console.log(fail ? `\n❌ ${fail} 项未通过` : '\n✅ 子页导出（报告/明细/存档/逐题）全部通过');
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error('❌', e.message); process.exit(1); });
