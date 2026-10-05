#!/usr/bin/env node
/**
 * 本地开发预览（Windows）：起一个静态服务器指向 ``ui/``，然后打开浏览器。
 *
 * 为什么除了 `file://` 还要有这个
 * ==============================
 * `ui/index.html` 本来就支持 `file://` 直接打开（项目硬约束，已验证：
 * `tools/check/test_local_file.js` 全绿）。但本地开发时多一条 HTTP 路径有实际好处：
 *   · 行为与部署后一致（`fetch`/CORS/相对路径按真实规则走，能提早暴露问题）
 *   · 改文件刷新即生效，不必复制到部署目录
 *   · 端口固定，方便对着 URL 反复调试
 *
 * 用法
 * ====
 *   node tools/ui/serve_local.js            # 默认 http://127.0.0.1:8892/ui/
 *   node tools/ui/serve_local.js --port 9000 --no-open
 *
 * 只读静态文件，不做任何构建。**不碰部署目录**（那是 sync_blog.js 的事）。
 */
const http = require('http');
const fs = require('fs');
const path = require('path');
const {execFile} = require('child_process');

const ROOT = require('../_root.js').findRoot(__dirname);
const UI = path.join(ROOT, 'ui');

const argv = process.argv.slice(2);
const arg = (name, dflt) => {
  const i = argv.indexOf('--' + name);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : dflt;
};
const PORT = +arg('port', 8892);
const OPEN = !argv.includes('--no-open');

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.md': 'text/markdown; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
};

if (!fs.existsSync(path.join(UI, 'index.html'))) {
  console.error('✗ 找不到 ui/index.html，请确认在项目根目录运行');
  process.exit(2);
}

const server = http.createServer((req, res) => {
  let p = decodeURIComponent(req.url.split('?')[0]);
  if (p === '/' || p === '') p = '/ui/';
  // 允许 /ui/xxx 与 /xxx 两种写法，省得记路径
  const rel = p.startsWith('/ui/') ? p.slice(4) : p;
  let file = path.join(UI, rel);
  // 防目录穿越：解析后必须仍在 ui/ 内
  if (!path.resolve(file).startsWith(path.resolve(UI))) {
    res.writeHead(403).end('forbidden');
    return;
  }
  if (fs.existsSync(file) && fs.statSync(file).isDirectory()) {
    file = path.join(file, 'index.html');
  }
  fs.readFile(file, (err, buf) => {
    if (err) {
      res.writeHead(404, {'Content-Type': 'text/plain; charset=utf-8'});
      res.end('404 ' + rel);
      return;
    }
    res.writeHead(200, {
      'Content-Type': MIME[path.extname(file).toLowerCase()] || 'application/octet-stream',
      // 开发期不缓存，改完刷新即见
      'Cache-Control': 'no-store',
    });
    res.end(buf);
  });
});

server.listen(PORT, '127.0.0.1', () => {
  const url = `http://127.0.0.1:${PORT}/ui/`;
  console.log(`EmoHealth 本地预览：${url}`);
  console.log(`（也可以直接双击 ui/index.html 用 file:// 打开，同样可用）`);
  console.log('Ctrl+C 停止');
  if (OPEN) {
    // Windows 下用 start 打开默认浏览器；其它平台各自回退
    if (process.platform === 'win32') {
      execFile('cmd', ['/c', 'start', '', url], () => {});
    } else if (process.platform === 'darwin') {
      execFile('open', [url], () => {});
    } else {
      execFile('xdg-open', [url], () => {});
    }
  }
});
