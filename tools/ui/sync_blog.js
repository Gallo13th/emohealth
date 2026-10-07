// 把 EmoHealth 的运行时文件**完整镜像**到博客仓库的 astro/public/emohealth/。
//
// 为什么需要：本机的编辑源在 emohealth/ui/，而部署位置是
// Myblogsource/astro/public/emohealth/（Astro 的 public 会原样复制到 dist）。
// 两边是**同一批文件的两个位置**，手工复制容易漏。
//
// 历史教训（这个脚本被改过两次，每次都是"漏了东西"）：
//   ① 最早只逐个复制根目录 9 个文件——漏过一次 index.html 没同步，量到的还是旧行为。
//   ② 之后补了 instruments/ 与 tree-layouts/ 两个子目录，但**仍是一张手写白名单**：
//      漏掉了 items-structured.js / items-structured/ / inference.js / inference/ / lib/。
//      结果是**部署出去的页面会 404**——因为 ui/index.html 的 614-621 行与 743 行会去加载它们。
//      （2026-10-07 上线时由 Lead 发现：白名单靠"人记得加"，而人一定会忘。）
//   ③ 现在改为**整树镜像**：ui/** 里有什么就同步什么，新增文件不需要谁记得加。
//      并且**删除目标里多出来的文件**——否则被删掉的东西（例如精简前的 342 个量表包）
//      会永远留在部署里，线上一直挂着一批早已废弃的资源。
//
// ⚠️ 目标目录 astro/public/emohealth/ 完全由本构建拥有，所以"多余即删除"是安全的；
//    脚本仍做一道保护：目标路径的末级目录名必须是 emohealth，防止路径写错把别处删空。
//
// 用法：
//   node tools/ui/sync_blog.js            # 同步（含删除多余文件）
//   node tools/ui/sync_blog.js --check    # 只比对，不改动；有差异则退出码 1
//   BLOG_EMOHEALTH=/别的/路径 node tools/ui/sync_blog.js
const fs = require('fs'), path = require('path'), crypto = require('crypto');
const ROOT = require('../_root.js').findRoot(__dirname);

const SRC = path.join(ROOT, 'ui');
const DST = process.env.BLOG_EMOHEALTH ||
  '\\\\wsl.localhost\\Ubuntu-22.04\\home\\glt\\github_official\\Myblogsource\\astro\\public\\emohealth';
const check = process.argv.includes('--check');
const h = b => crypto.createHash('sha256').update(b).digest('hex').slice(0, 16);

if (!fs.existsSync(DST)) {
  console.error(`✗ 目标目录不存在：${DST}\n  （首次部署请先 mkdir，或设 BLOG_EMOHEALTH 指向它）`);
  process.exit(2);
}
if (path.basename(path.resolve(DST)) !== 'emohealth') {
  console.error(`✗ 目标目录末级名不是 emohealth，拒绝操作：${DST}`);
  process.exit(2);
}

/** 递归列出目录下所有文件的相对路径（POSIX 风格）。 */
function walk(base, rel = '') {
  const out = [];
  for (const e of fs.readdirSync(path.join(base, rel), {withFileTypes: true})) {
    const r = rel ? rel + '/' + e.name : e.name;
    if (e.isDirectory()) out.push(...walk(base, r));
    else if (e.isFile()) out.push(r);
  }
  return out;
}

const srcFiles = walk(SRC).sort();
const srcSet = new Set(srcFiles);
const dstFiles = walk(DST).sort();

let added = 0, updated = 0, same = 0, deleted = 0;
const deletes = [];

for (const rel of srcFiles) {
  const s = path.join(SRC, rel), d = path.join(DST, rel);
  const sb = fs.readFileSync(s);
  const has = fs.existsSync(d);
  if (has && h(fs.readFileSync(d)) === h(sb)) { same++; continue; }
  if (!check) {
    fs.mkdirSync(path.dirname(d), {recursive: true});
    fs.writeFileSync(d, sb);
  }
  if (has) { updated++; if (check) console.log(`  ≠ 需更新  ${rel}`); }
  else { added++; if (check) console.log(`  + 需新增  ${rel}`); }
}

// 目标里多出来的（构建已不产出）——删除，否则废弃资源会永远留在线上
for (const rel of dstFiles) {
  if (srcSet.has(rel)) continue;
  deletes.push(rel);
  deleted++;
  if (!check) fs.unlinkSync(path.join(DST, rel));
  if (check && deletes.length <= 15) console.log(`  - 需删除  ${rel}`);
}

if (!check) {
  // 清掉因删除而空掉的目录（自底向上）
  const dirs = [];
  (function collect(base, rel = '') {
    for (const e of fs.readdirSync(path.join(base, rel), {withFileTypes: true})) {
      if (!e.isDirectory()) continue;
      const r = rel ? rel + '/' + e.name : e.name;
      collect(base, r); dirs.push(r);
    }
  })(DST);
  for (const rel of dirs.sort((a, b) => b.length - a.length)) {
    const p = path.join(DST, rel);
    if (fs.existsSync(p) && fs.readdirSync(p).length === 0) fs.rmdirSync(p);
  }
}

console.log(`源 ${srcFiles.length} 个文件 → 目标原有 ${dstFiles.length} 个文件`);
console.log(`${check ? '比对' : '同步'}结果：一致 ${same}，` +
  `${check ? '需更新' : '已更新'} ${updated}，${check ? '需新增' : '已新增'} ${added}，` +
  `${check ? '需删除' : '已删除'} ${deleted}`);
if (check && deletes.length > 15) console.log(`  （删除项仅列前 15 条，共 ${deletes.length} 条）`);

if (check) {
  const bad = added + updated + deleted;
  console.log(bad ? '\n⚠ 需要同步（目标与构建不一致）' : '\n✅ 已同步（目标 == 构建）');
  process.exit(bad ? 1 : 0);
}

console.log('\n接下来（在 WSL 里执行）：');
console.log('  cd ~/github_official/Myblogsource && bash bin/deploy-emohealth.sh');
console.log('  （它负责构建 + 跑门 + 提交 + rebase + 推送；--dry-run 可只构建不推送）');
