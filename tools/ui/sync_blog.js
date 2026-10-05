// 把 EmoHealth 的运行时文件同步到博客仓库的 astro/public/emohealth/。
//
// 为什么需要：本机的编辑源在 emohealth/ui/，而部署位置是
// Myblogsource/astro/public/emohealth/（Astro 的 public 会原样复制到 dist）。
// 两边是**同一批文件的两个位置**，手工复制容易漏（我已经漏过一次：
// 改了 ui/index.html 却没同步，于是量到的还是旧行为）。
//
// 用法：node tools/ui/sync_blog.js [--check]
const fs = require('fs'), path = require('path'), crypto = require('crypto');
const ROOT = require('../_root.js').findRoot(__dirname);

const SRC = path.join(ROOT, 'ui');
const DST = process.env.BLOG_EMOHEALTH ||
  '\\\\wsl.localhost\\Ubuntu-22.04\\home\\glt\\github_official\\Myblogsource\\astro\\public\\emohealth';
const FILES = ['index.html', 'emohealth-data.js', 'tier-data.js', 'unlock-data.js',
               'adaptive-data.js', 'net-layout.js',
               // 多量表：目录 + 按需加载清单
               'catalog.js', 'instruments.js', 'README.md'];
const check = process.argv.includes('--check');
const h = b => crypto.createHash('sha256').update(b).digest('hex').slice(0, 16);

if (!fs.existsSync(DST)) {
  console.error(`✗ 目标目录不存在：${DST}\n  （首次部署请先 mkdir，或设 BLOG_EMOHEALTH 指向它）`);
  process.exit(2);
}

let same = 0, diff = 0, missing = 0;
for (const f of FILES) {
  const s = path.join(SRC, f), d = path.join(DST, f);
  if (!fs.existsSync(s)) { console.log(`  ⚠ 源缺失 ${f}`); continue; }
  const sb = fs.readFileSync(s);
  const db = fs.existsSync(d) ? fs.readFileSync(d) : null;
  if (db && h(sb) === h(db)) { same++; if (!check) ; continue; }
  if (!db) missing++; else diff++;
  if (check) {
    console.log(`  ${db ? '≠ 内容不同' : '+ 目标缺失'}  ${f}  源 ${h(sb)}${db ? ' / 目标 ' + h(db) : ''}`);
  } else {
    fs.writeFileSync(d, sb);
    console.log(`  ${db ? '↻ 已更新' : '+ 已新增'}  ${f}  (${sb.length} 字节, ${h(sb)})`);
  }
}
if (check) {
  console.log(`\n${same} 个一致，${diff} 个不同，${missing} 个缺失` +
    (diff + missing ? '  ← 需要同步' : '  ✅ 已同步'));
  process.exit(diff + missing ? 1 : 0);
}
console.log(`\n同步完成：${same} 个本来就一致，${diff} 个更新，${missing} 个新增`);

// 多量表的按需加载包在子目录里单独同步（40 个文件，逐个比对哈希）
const INST_SRC = path.join(SRC, 'instruments');
const INST_DST = path.join(DST, 'instruments');
if (fs.existsSync(INST_SRC)) {
  if (!check) fs.mkdirSync(INST_DST, {recursive: true});
  let iSame = 0, iDiff = 0, iNew = 0;
  for (const f of fs.readdirSync(INST_SRC)) {
    const s = path.join(INST_SRC, f), d = path.join(INST_DST, f);
    const sb = fs.readFileSync(s);
    const db = fs.existsSync(d) ? fs.readFileSync(d) : null;
    if (db && h(sb) === h(db)) { iSame++; continue; }
    if (!db) iNew++; else iDiff++;
    if (!check) fs.writeFileSync(d, sb);
  }
  console.log(`量表包：${iSame} 个一致，${iDiff} 个更新，${iNew} 个新增`
    + (check && (iDiff + iNew) ? '  ← 需要同步' : ''));
  if (check && (iDiff + iNew)) process.exit(1);
}

// 天赋树布局（> 60 题的量表，D114）
const TREE_SRC = path.join(SRC, 'tree-layouts');
const TREE_DST = path.join(DST, 'tree-layouts');
if (fs.existsSync(TREE_SRC)) {
  if (!check) fs.mkdirSync(TREE_DST, {recursive: true});
  let tSame = 0, tDiff = 0, tNew = 0;
  for (const f of fs.readdirSync(TREE_SRC)) {
    const s = path.join(TREE_SRC, f), d = path.join(TREE_DST, f);
    const sb = fs.readFileSync(s);
    const db = fs.existsSync(d) ? fs.readFileSync(d) : null;
    if (db && h(sb) === h(db)) { tSame++; continue; }
    if (!db) tNew++; else tDiff++;
    if (!check) fs.writeFileSync(d, sb);
  }
  console.log(`天赋树布局：${tSame} 个一致，${tDiff} 个更新，${tNew} 个新增`
    + (check && (tDiff + tNew) ? '  ← 需要同步' : ''));
  if (check && (tDiff + tNew)) process.exit(1);
}
if (check) {
  console.log((diff + missing) ? '\n⚠ 需要同步' : '\n✅ 已同步');
  process.exit(diff + missing ? 1 : 0);
}
console.log('\n接下来（在 WSL 里执行）：');
console.log('  cd ~/github_official/Myblogsource/astro && npm run build');
console.log('  cd .. && git add astro/public/emohealth && git commit -m "..."');
console.log('  git fetch origin main && git rebase origin/main && git push origin main');
console.log('提示：origin 必须用 SSH（git@github.com:...）——GitHub 已不接受密码认证。');
