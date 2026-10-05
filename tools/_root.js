// 统一的项目根定位（JS 版，对应 tools/_root.py）。
//
// 为什么需要：迁移把脚本从 `tools/xxx.js` 移进 `tools/<cat>/xxx.js` 后，
// 原来用 `path.join(__dirname, '..')` 推导项目根的写法会落到 `tools/`，
// 全仓路径静默错位——与 Python 侧同一个坑，所以用同一套判据：向上找
// 含 `MANIFEST.sha256` 的目录。找不到抛错，不猜。
//
//     const ROOT = require('../_root.js').findRoot(__dirname);
//
'use strict';
const fs = require('fs');
const path = require('path');

const ROOT_MARKER = 'MANIFEST.sha256';

function findRoot(start) {
  let dir = path.resolve(start || __dirname);
  if (fs.existsSync(dir) && fs.statSync(dir).isFile()) dir = path.dirname(dir);
  for (;;) {
    if (fs.existsSync(path.join(dir, ROOT_MARKER))) return dir;
    const parent = path.dirname(dir);
    if (parent === dir) {
      throw new Error(`从 ${start} 向上找不到含 ${ROOT_MARKER} 的目录`);
    }
    dir = parent;
  }
}

module.exports = {findRoot, ROOT_MARKER};

if (require.main === module) {
  const root = findRoot(__dirname);
  console.log(`项目根  ${root}`);
  for (const rel of ['MANIFEST.sha256', 'ui/index.html', 'data/instruments']) {
    console.log(`  ${fs.existsSync(path.join(root, rel)) ? '✅' : '❌'} ${rel}`);
  }
}
