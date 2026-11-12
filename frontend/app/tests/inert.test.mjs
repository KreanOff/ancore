import assert from 'node:assert/strict';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

const bundle = await build({
  entryPoints: [new URL('../src/shared/inert.ts', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  write: false,
});
const module = { exports: {} };
vm.runInNewContext(bundle.outputFiles[0].text, { module, exports: module.exports });
const { acquireInert } = module.exports;

test('page content stays inert until both its drawer and dialog release it, in either order', () => {
  for (const closeDrawerFirst of [true, false]) {
    const page = { inert: false };
    const drawer = { inert: false };
    const closeDrawer = acquireInert([page]);
    const closeDialog = acquireInert([page, drawer]);
    assert.equal(page.inert, true);
    assert.equal(drawer.inert, true);

    if (closeDrawerFirst) closeDrawer();
    else closeDialog();
    assert.equal(page.inert, true);
    assert.equal(drawer.inert, closeDrawerFirst);

    if (closeDrawerFirst) closeDialog();
    else closeDrawer();
    assert.equal(page.inert, false);
    assert.equal(drawer.inert, false);
  }
});

test('cleanup preserves preexisting inert state and restores detached elements', () => {
  const disabled = { inert: true };
  const page = { inert: false, isConnected: true };
  const closeDrawer = acquireInert([disabled, page]);
  const closeDialog = acquireInert([disabled, page]);
  page.isConnected = false;
  closeDrawer();
  assert.equal(page.inert, true);
  closeDialog();
  assert.equal(disabled.inert, true);
  assert.equal(page.inert, false);
});

test('repeated cleanup and duplicate elements cannot release another active dialog', () => {
  const page = { inert: false };
  const closeDrawer = acquireInert([page, page]);
  const closeDialog = acquireInert([page]);
  closeDrawer();
  closeDrawer();
  assert.equal(page.inert, true);
  closeDialog();
  assert.equal(page.inert, false);

  page.inert = true;
  const closeNextDialog = acquireInert([page]);
  closeDialog();
  closeNextDialog();
  assert.equal(page.inert, true);
});
