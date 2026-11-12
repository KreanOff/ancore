import assert from 'node:assert/strict';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

const bundle = await build({
  entryPoints: [new URL('../src/shell/sidebarSizing.ts', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  write: false,
});
const module = { exports: {} };
vm.runInNewContext(bundle.outputFiles[0].text, { module, exports: module.exports });
const { savedRightSidebarWidth, sidebarWidths, rightSidebarDragWidth } = module.exports;
const base = {
  viewport: 1440,
  scale: 0.98,
  gap: 4,
  leftPreference: 272,
  leftCollapsed: false,
  collapsedWidth: 64,
  rightPreference: null,
  rightDefault: 272,
  rightVisible: true,
};

test('stored widths reject malformed values and keep valid preferences', () => {
  for (const value of [null, undefined, true, '', '370', {}, [], NaN, Infinity, -1, 239, 521])
    assert.equal(savedRightSidebarWidth(value), null);
  for (const value of [240, 272, 370, 519.5, 520])
    assert.equal(savedRightSidebarWidth(value), value);
});

test('right edge drag follows physical pointer movement at UI zoom and respects limits', () => {
  assert.equal(rightSidebarDragWidth(272, 1000, 902, 0.98, 520), 372);
  assert.equal(rightSidebarDragWidth(372, 902, 1000, 0.98, 520), 272);
  assert.equal(rightSidebarDragWidth(272, 1000, 2000, 0.98, 520), 240);
  assert.equal(rightSidebarDragWidth(272, 1000, 0, 0.98, 410), 410);
});

test('viewport constraints preserve the content and recover the unchanged saved preference', () => {
  const preferences = { ...base, rightPreference: 520, leftPreference: 420 };
  const wide = sidebarWidths(preferences);
  assert.equal(wide.right, 520);
  const narrow = sidebarWidths({ ...preferences, viewport: 1101 });
  assert.ok(narrow.right < 520);
  assert.ok(1101 / base.scale - narrow.left - narrow.right - 4 * base.gap >= 360);
  assert.equal(sidebarWidths(preferences).right, 520);
  assert.equal(sidebarWidths({ ...preferences, viewport: 1101 }).right, narrow.right);
});

test('default task width, reset and collapsed panels use independent layout budgets', () => {
  assert.equal(sidebarWidths(base).right, 272);
  assert.equal(sidebarWidths({ ...base, rightDefault: 370 }).right, 370);
  assert.equal(sidebarWidths({ ...base, rightDefault: 370, rightPreference: 450 }).right, 450);
  const narrow = { ...base, viewport: 1101, leftPreference: 420, rightPreference: 520 };
  assert.equal(sidebarWidths({ ...narrow, leftCollapsed: true }).right, 520);
  assert.equal(sidebarWidths({ ...narrow, rightVisible: false }).left, 420);
});
