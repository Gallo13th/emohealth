// Python↔JS 一致性对照的 **JS 侧执行器**（由 test_inference_pyjs_consistency.py 调用）。
//
// 输入 fixture（JSON）：
//   { "cases": [ {"id": "...", "instrument": "IPIP-NEO", "responses": {...}}, ... ],
//     "params": { "IPIP-NEO": {"params": {...}, "pairB64": "..."}, ... },
//     "pairB64": {...} }
// 输出：{ "cases": [ {"id": "...", "ipip-or-null": {...}, ...} ] } —— 直接写文件，
// 不走 stdout（避免管道/编码问题），由 Python 读回逐项比对。
//
// 用法（一般不用手跑）：
//   node tools/check/inference_pyjs_compare.js <fixture.json> <out.json>
const fs = require('fs');
const path = require('path');
const ROOT = path.resolve(__dirname, '..', '..');
const lib = require(path.join(ROOT, 'ui', 'lib', 'inference.js'));

function main() {
  const [, , fixturePath, outPath] = process.argv;
  if (!fixturePath || !outPath) {
    console.error('用法：node inference_pyjs_compare.js <fixture.json> <out.json>');
    process.exit(2);
  }
  const fx = JSON.parse(fs.readFileSync(fixturePath, 'utf8'));
  const payloads = {};
  for (const code of Object.keys(fx.params)) {
    payloads[code] = {
      params: fx.params[code].params,
      pairB64: fx.params[code].pairB64,
      __pairs: lib.buildPairMatrix(fx.params[code].pairB64,
                                   fx.params[code].params.ids.length),
    };
  }
  const out = { cases: [] };
  for (const c of fx.cases) {
    const row = { id: c.id, results: {} };
    // 只喂给该 case 自己的量表——别的量表的题号对不上（会正确地抛错，
    // 但那是用例构造问题，不是一致性对照的内容）
    row.results[c.instrument] = lib.predict(payloads[c.instrument], c.responses);
    out.cases.push(row);
  }
  fs.writeFileSync(outPath, JSON.stringify(out), 'utf8');
  return 0;
}

if (require.main === module) process.exit(main());
module.exports = { main };
