// 起一个极简静态服务，用于在浏览器里核对构建产物。
// 为什么不用 WSL 里的 python http.server：wsl.exe 每次调用是独立的，
// 后台进程活不过命令结束（实测监听没了、curl 000），跨 VM 端口转发也就不稳。
// 直接在本机起服务、用本机 Chrome 访问，路径与线上 1:1。
//
// 用法：node tools/ui/serve_dist.js <dist目录> [端口]
const http = require('http'), fs = require('fs'), path = require('path');

const ROOT = path.resolve(process.argv[2] || '.');
const PORT = +(process.argv[3] || 8891);
const TYPES = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8', '.json': 'application/json; charset=utf-8',
  '.md': 'text/plain; charset=utf-8', '.png': 'image/png', '.jpg': 'image/jpeg',
  '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.xml': 'application/xml',
  '.txt': 'text/plain; charset=utf-8', '.ico': 'image/x-icon'};

http.createServer((req, res) => {
  let p = decodeURIComponent(req.url.split('?')[0]);
  let full = path.join(ROOT, p);
  try {
    if (fs.existsSync(full) && fs.statSync(full).isDirectory()) {
      full = path.join(full, 'index.html');
    } else if (!fs.existsSync(full) && !path.extname(full)) {
      const alt = path.join(ROOT, p, 'index.html');
      if (fs.existsSync(alt)) full = alt;
    }
    if (!fs.existsSync(full)) { res.writeHead(404); res.end('404'); return; }
    const body = fs.readFileSync(full);
    res.writeHead(200, {'Content-Type': TYPES[path.extname(full).toLowerCase()] || 'application/octet-stream',
                        'Content-Length': body.length});
    res.end(body);
  } catch (e) { res.writeHead(500); res.end(String(e)); }
}).listen(PORT, '127.0.0.1', () => {
  console.log(`serving ${ROOT} → http://127.0.0.1:${PORT}/`);
});
