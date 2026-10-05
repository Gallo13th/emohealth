// Mania 每题选项组（ASRM）：必须从 **items[].options** 渲染出 5 组 × 5 句陈述。
//
// 为什么要这条测试
// ================
// 2026-10-04 把「每题自己的选项」从 `provenance.item_options`（旧兼容镜像）
// 切到规范位置 `items[].options`，并删除了镜像。这是**切数据源**：
// 一旦哪一环没接上（打包器漏拷 `options`、界面仍读旧字段），
// Mania 的选项会**静默变空**——页面不报错、只是 5 组题都没有可选的句子，
// 用户根本没法作答。所以这条测试同时钉住**两条读取路径**：
//   ① 经典逐题页（`.institems`）—— Mania 走这条；
//   ② 天赋树就地作答（`.treeq`）—— PID-5 走这条（无自带选项 → 回退统一标签）。
const {spawn} = require('child_process');
const os = require('os'), fs = require('fs'), path = require('path');
const PORT = 9395;
const CHROME = process.env.CHROME ||
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const sleep = ms => new Promise(r => setTimeout(r, ms));
const ROOT = 'C:\\Codes\\emohealth-20260930-full\\emohealth';

let fail = 0;
const ck = (n, c, d = '') => {
  console.log(`  ${c ? '✅' : '❌'} ${n}${d ? '  —— ' + d : ''}`);
  if (!c) fail++;
};

(async () => {
  const toUrl = p => 'file:///' + p.replace(/\\/g, '/');
  const base = toUrl(path.join(ROOT, 'ui', 'index.html'));
  const prof = fs.mkdtempSync(path.join(os.tmpdir(), 'mania-'));
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
    if (r.result?.exceptionDetails) return 'EXC: ' +
      (r.result.exceptionDetails.exception?.message || '').slice(0, 200);
    return r.result?.result?.value;
  };

  // ── ① 经典逐题页：Mania 的 5 组选项 ──
  console.log('=== Mania（ASRM）经典逐题页：items[].options ===');
  await S('Page.navigate', {url: base + '#/scale/DSM5TR-L2-Mania/classic'});
  await sleep(2600);
  const mania = await ev(`(() => {
      const d = INST_NOW; if (!d) return {err: 'scale not loaded'};
      const lis = [...document.querySelectorAll('.institems > li')];
      return {
        nItems: d.items.length,
        // 每题在数据包里是否真的有 options（这是本次切换的核心）
        pkgOwn: d.items.map(it => (it.options || []).length),
        groups: lis.map(li => ({
          text: (li.querySelector('.insttext') || {}).textContent || '',
          opts: [...li.querySelectorAll('.opts button.opt')]
                  .map(b => (b.querySelector('.ot') || {}).textContent || ''),
        })),
        // 底部统一标签图例：每题自带选项时**不应**出现
        legend: !!document.querySelector('.note .ot, .institems ~ .note'),
        errs: (window.__errs || []).slice(0, 3),
      };
    })()`);
  if (mania.err) { ck('量体裁入 Mania', false, mania.err); }
  else {
    ck('数据包里每题都有 options（5 组 × 5）',
       JSON.stringify(mania.pkgOwn) === JSON.stringify([5, 5, 5, 5, 5]),
       JSON.stringify(mania.pkgOwn));
    ck('页面渲染出 5 组', mania.groups.length === 5, mania.groups.length + ' 组');
    ck('每组都渲染出 5 个选项',
       mania.groups.every(g => g.opts.length === 5),
       JSON.stringify(mania.groups.map(g => g.opts.length)));
    ck('选项是**整句陈述**（不是空壳/数字）',
       mania.groups.every(g => g.opts.every(x => x.length > 18)));
    ck('第 1 组第 1 句与手册一致',
       mania.groups[0].opts[0] === 'I do not feel happier or more cheerful than usual',
       JSON.stringify(mania.groups[0].opts[0]));
    const empty = mania.groups.filter(g => g.opts.length === 0).length;
    ck('没有任何一组的选项为空', empty === 0, empty + ' 组为空');
    console.log('  ── 渲染实测（页面 DOM 取出的选项文本）──');
    mania.groups.forEach((g, i) => {
      console.log(`  第 ${i + 1} 组（${g.opts.length} 项）：`);
      g.opts.forEach((o, v) => console.log(`     ${v}. ${o}`));
    });
  }

  // ── ② 天赋树就地作答：另一条读取路径（PID-5，无自带选项 → 回退统一标签）──
  console.log('\n=== PID-5 天赋树就地作答：另一条读取路径 ===');
  await S('Page.navigate', {url: base + '#/scale/PID-5/tree'});
  await sleep(3000);
  const tree = await ev(`(() => {
      const nodes = [...document.querySelectorAll('.treenode')];
      if (!nodes.length) return {err: 'no tree nodes'};
      // 点一个有内容的节点（跳过前几个纯结构点）
      const n = nodes[Math.min(5, nodes.length - 1)];
      n.dispatchEvent(new MouseEvent('click', {bubbles: true}));
      return new Promise(res => setTimeout(() => {
        const q = document.querySelector('.treeq');
        res({nodes: nodes.length,
             q: !!q,
             opts: q ? [...q.querySelectorAll('.opts button.opt')].length : 0,
             dataV: q ? [...q.querySelectorAll('.opts button.opt')].map(b => b.dataset.v) : []});
      }, 600));
    })()`);
  if (tree.err) { ck('天赋树可选节点', false, tree.err); }
  else {
    ck('树节点渲染', tree.nodes > 50, tree.nodes + ' 节点');
    ck('点节点后就地展开作答区', tree.q === true);
    ck('选项按钮渲染出来（回退统一标签 0–3）',
       tree.opts === 4, tree.opts + ' 个：' + JSON.stringify(tree.dataV));
    console.log('  ── 实测：', JSON.stringify(tree));
  }

  ws.close(); ch.kill();
  console.log(fail ? `\n❌ ${fail} 项未通过` : '\n✅ Mania 选项组与天赋树两条读取路径全部通过');
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error('❌', e.message); process.exit(1); });
