const assert = require('node:assert/strict');
const { test } = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const context = {};
for (const name of ['estimateSplitTime', 'formatTime']) {
  const source = html.match(new RegExp(`function ${name}\\([\\s\\S]*?\\n}`));
  assert(source, `${name} is present in standalone page`);
  vm.runInNewContext(source[0], context);
}

test('constant speed covers 500m in 100 seconds', () => {
  assert.equal(context.estimateSplitTime(Array(10).fill(5)), 100);
});

test('variable speed adds equal-distance segment durations', () => {
  const speeds = Array.from({ length: 10 }, (_, index) => index % 2 ? 6 : 4);
  assert(Math.abs(context.estimateSplitTime(speeds) - (250 / 4 + 250 / 6)) < 1e-10);
});

test('incomplete and invalid splits stay unavailable', () => {
  for (const speeds of [[], Array(9).fill(5), Array(11).fill(5), ...[0, -1, NaN, Infinity, null, '5'].map(value => [...Array(9).fill(5), value])]) {
    assert.equal(context.estimateSplitTime(speeds), null);
  }
  assert.equal(context.formatTime(null), '—');
  assert.equal(context.formatTime(NaN), '—');
  assert.equal(context.formatTime(Infinity), '—');
});
