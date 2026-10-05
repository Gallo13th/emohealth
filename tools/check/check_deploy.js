// 在 WSL 里核对：/emohealth/ 子路径下页面能真的跑（图形渲染 + 点击作答 + 无脚本报错）
// 用 CDP 直连无头 Chrome，不装 puppeteer。
const { spawn } = require('child_process');
const os = require('os'), fs = require('fs'), path = require('path');

const ROOT_ = require('path').resolve(__dirname, '..', '..');
// ⚠️ 默认必须指向**工作区**，不能是某个部署副本——否则会对着旧构建**假绿**
//    （本仓库已因此踩过三次）。file:// 直开不依赖任何服务，测的就是工作区。
const URL_ = process.env.URL ||
  'file:///' + require('path').join(ROOT_, 'ui', 'index.html').replace(/\\/g, '/');
const PORT = 9334;
const CHROME = process.env.CHROME || 'google-chrome';

const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const prof = fs.mkdtempSync(path.join(os.tmpdir(), 'shot-'));
  const ch = spawn(CHROME, [
    '--headless=new', '--no-sandbox', '--disable-gpu', '--no-first-run',
    '--remote-debugging-port=' + PORT, '--user-data-dir=' + prof,
    '--window-size=1440,1200', 'about:blank',
  ], { stdio: 'ignore' });

  let ver = null;
  for (let i = 0; i < 60 && !ver; i++) {
    try { ver = await (await fetch(`http://127.0.0.1:${PORT}/json/version`)).json(); }
    catch { await sleep(250); }
  }
  if (!ver) { ch.kill(); throw new Error('Chrome 调试端口没起来'); }

  const ws = new WebSocket(ver.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  let id = 0; const pend = new Map(); const errors = [];
  ws.onmessage = ev => {
    const m = JSON.parse(ev.data);
    if (m.id && pend.has(m.id)) { pend.get(m.id)(m); pend.delete(m.id); }
    if (m.method === 'Runtime.exceptionThrown')
      errors.push(m.params.exceptionDetails.exception?.description
        || m.params.exceptionDetails.text);
    if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error')
      errors.push('console.error: ' + m.params.args.map(a => a.value).join(' '));
  };
  const send = (method, params, sessionId) => new Promise(res => {
    const i = ++id; pend.set(i, res);
    ws.send(JSON.stringify({ id: i, method, params, sessionId }));
  });
  const t = await send('Target.createTarget', { url: 'about:blank' });
  const a = await send('Target.attachToTarget', { targetId: t.result.targetId, flatten: true });
  const sid = a.result.sessionId;
  const S = (m, p) => send(m, p, sid);
  await S('Page.enable'); await S('Runtime.enable');
  await S('Page.navigate', { url: URL_ });
  await sleep(2500);

  const ev = async expr => {
    const r = await S('Runtime.evaluate', { expression: expr, returnByValue: true });
    return r.result?.result?.value;
  };

  const report = {};
  report.url = await ev('location.href');
  report['数据包'] = await ev(`(() => ({
    题数: (window.EMOHEALTH||{}).items ? window.EMOHEALTH.items.length : null,
    面向数: (window.EMOHEALTH||{}).facets ? window.EMOHEALTH.facets.length : null,
    分级阶梯: (window.EMOHEALTH_TIER||{}).order ? window.EMOHEALTH_TIER.order.length : null,
    网状坐标: (window.EMOHEALTH_NET||{}).xy ? Object.keys(window.EMOHEALTH_NET.xy).length : null,
    解锁规则: (window.EMOHEALTH_UNLOCK||{}).rel ? Object.keys(window.EMOHEALTH_UNLOCK.rel).length : null,
  }))()`);
  report['图形节点数'] = await ev(`document.querySelectorAll('#graphbox g.nd').length`);
  report['常驻区'] = await ev(`(document.getElementById('nextq')||{}).innerHTML?.length || 0`);
  report['可疑的对齐'] = await ev(`(() => {
      const p = document.querySelector('.panelwrap');
      return p ? getComputedStyle(p).display : 'no .panelwrap';
    })()`);

  // 点第一个「可作答」节点 → 应答区应出现题干与 5 个选项
  const clicked = await ev(`(() => {
      const nd = document.querySelector('#graphbox g.nd.open');
      if (!nd) return 'no open node';
      nd.dispatchEvent(new MouseEvent('click', {bubbles: true}));
      return nd.getAttribute('data-o');
    })()`);
  await sleep(400);
  report['点击节点'] = clicked;
  report['点后选项数'] = await ev(`document.querySelectorAll('#nextq .opt').length`);
  report['点后题干'] = await ev(`(document.querySelector('#nextq .qtext')||{}).textContent?.slice(0,40) || ''`);
  report['_诊断_tierSel'] = await ev(`S.tierSel ? JSON.stringify(S.tierSel) : null`);
  report['_诊断_两个容器的长度'] = await ev(
    `[ (document.getElementById('nextq')||{}).innerHTML?.length || 0,
       (document.getElementById('tierpanel')||{}).innerHTML?.length || 0 ].join(' / ')`);
  report['_诊断_body里 .opt 总数'] = await ev(`document.querySelectorAll('.opt').length`);

  // 真的作答
  const answered = await ev(`(() => {
      const b = document.querySelector('#nextq .opt');
      if (!b) return 'no opt';
      b.dispatchEvent(new MouseEvent('click', {bubbles: true}));
      return 'clicked';
    })()`);
  await sleep(500);
  report['作答'] = answered;
  report['已答数（顶部文案）'] = await ev(`(document.getElementById('topmeta')||{}).textContent || ''`);
  report['localStorage 写入'] = await ev(`Object.keys(localStorage).filter(k=>k.includes('emohealth')||k.includes('EMO')).join(',') || '(none)'`);
  report['脚本报错'] = errors.length ? errors.slice(0, 3) : '无';

  console.log(JSON.stringify(report, null, 1));
  ws.close(); ch.kill();
  process.exit(errors.length ? 1 : 0);
})().catch(e => { console.error('❌', e.message); process.exit(1); });
