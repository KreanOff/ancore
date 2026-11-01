import assert from 'node:assert/strict';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

const bundle = await build({
  entryPoints: [new URL('../src/spaces/workflow-viewport.ts', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  write: false,
});
const module = { exports: {} };
vm.runInNewContext(bundle.outputFiles[0].text, { module, exports: module.exports });
const { screenToWorld, zoomWorkflowAt, fitWorkflow, MIN_ZOOM, MAX_ZOOM } = module.exports;
const toScreen = (point, camera) => ({
  x: point.x * camera.zoom + camera.x,
  y: point.y * camera.zoom + camera.y,
});
const close = (actual, expected) => assert.ok(Math.abs(actual - expected) < 1e-8);
const plain = (value) => JSON.parse(JSON.stringify(value));

test('screen coordinates map to signed world coordinates after pan and zoom', () => {
  const camera = { x: 100, y: -40, zoom: 0.5 };
  assert.deepEqual(plain(screenToWorld({ x: 30, y: 50 }, camera)), { x: -140, y: 180 });
  const world = { x: -720, y: -330 };
  assert.deepEqual(plain(screenToWorld(toScreen(world, camera), camera)), world);
});

test('moving the camera changes the world point under a stationary cursor by the scaled pan', () => {
  const before = { x: -180, y: 140, zoom: 0.25 };
  const after = { ...before, x: before.x + 40, y: before.y - 15 };
  const cursor = { x: 400, y: 300 };
  const first = screenToWorld(cursor, before);
  const second = screenToWorld(cursor, after);
  close(second.x - first.x, -40 / before.zoom);
  close(second.y - first.y, 15 / before.zoom);
});

test('zoom preserves the world point beneath an arbitrary cursor anchor', () => {
  const camera = { x: -280, y: 170, zoom: 0.7 };
  const anchor = { x: 133, y: 491 };
  const world = screenToWorld(anchor, camera);
  for (const zoom of [0.05, 0.2, 1, 1.7, 2]) {
    const changed = zoomWorkflowAt(camera, zoom, anchor);
    const screen = toScreen(world, changed);
    close(screen.x, anchor.x);
    close(screen.y, anchor.y);
    assert.equal(changed.zoom, zoom);
  }
  const back = zoomWorkflowAt(zoomWorkflowAt(camera, 1.5, anchor), camera.zoom, anchor);
  close(back.x, camera.x);
  close(back.y, camera.y);
});

test('zoom limits retain anchor invariance, including invalid requested magnification', () => {
  const camera = { x: 120, y: -80, zoom: 0.5 };
  const anchor = { x: 300, y: 190 };
  const world = screenToWorld(anchor, camera);
  for (const [requested, expected] of [
    [-1, MIN_ZOOM],
    [0.001, MIN_ZOOM],
    [100, MAX_ZOOM],
    [Number.NaN, camera.zoom],
  ]) {
    const changed = zoomWorkflowAt(camera, requested, anchor);
    assert.equal(changed.zoom, expected);
    const screen = toScreen(world, changed);
    close(screen.x, anchor.x);
    close(screen.y, anchor.y);
  }
});

test('fit includes full cards at negative and positive coordinates with padding', () => {
  const nodes = [
    { x: -900, y: -640 },
    { x: 500, y: 350 },
    { x: -80, y: 720 },
  ];
  const viewport = { width: 840, height: 620 };
  const camera = fitWorkflow(nodes, viewport, 48);
  assert.ok(camera.zoom < 1 && camera.zoom > MIN_ZOOM);
  nodes.forEach((node) => {
    const start = toScreen(node, camera);
    const end = toScreen({ x: node.x + 220, y: node.y + 88 }, camera);
    assert.ok(start.x >= 48 - 1e-8 && start.y >= 48 - 1e-8);
    assert.ok(end.x <= viewport.width - 48 + 1e-8);
    assert.ok(end.y <= viewport.height - 48 + 1e-8);
  });
  const center = toScreen({ x: (-900 + 500 + 220) / 2, y: (-640 + 720 + 88) / 2 }, camera);
  close(center.x, viewport.width / 2);
  close(center.y, viewport.height / 2);
});

test('fit centers a small map at natural size and an empty map at the origin', () => {
  const viewport = { width: 900, height: 600 };
  const camera = fitWorkflow([{ x: -400, y: -200 }], viewport);
  assert.equal(camera.zoom, 1);
  const center = toScreen({ x: -400 + 110, y: -200 + 44 }, camera);
  assert.deepEqual(center, { x: 450, y: 300 });
  const empty = fitWorkflow([], viewport);
  assert.deepEqual(plain(empty), { x: 450, y: 300, zoom: 1 });
  assert.deepEqual(toScreen({ x: 0, y: 0 }, empty), { x: 450, y: 300 });
});

test('fit keeps a valid bounded camera for a temporarily collapsed viewport', () => {
  const camera = fitWorkflow([{ x: -800, y: -300 }], { width: 0, height: 0 });
  assert.equal(camera.zoom, 1e-6);
  assert.ok(Number.isFinite(camera.x) && Number.isFinite(camera.y));
});

test('fit can go below the manual zoom limit to show widely separated cards', () => {
  const nodes = [
    { x: -100000, y: -90000 },
    { x: 100000, y: 90000 },
  ];
  const viewport = { width: 900, height: 600 };
  const camera = fitWorkflow(nodes, viewport);
  assert.ok(camera.zoom < MIN_ZOOM && camera.zoom > 1e-6);
  nodes.forEach((node) => {
    const start = toScreen(node, camera);
    const end = toScreen({ x: node.x + 220, y: node.y + 88 }, camera);
    assert.ok(start.x >= 48 - 1e-8 && start.y >= 48 - 1e-8);
    assert.ok(end.x <= viewport.width - 48 + 1e-8);
    assert.ok(end.y <= viewport.height - 48 + 1e-8);
  });
});

test('zooming out after fitting a very large map stays put and zooming in is gradual and anchored', () => {
  const camera = fitWorkflow(
    [
      { x: -100000, y: -90000 },
      { x: 100000, y: 90000 },
    ],
    { width: 900, height: 600 },
  );
  const anchor = { x: 217, y: 381 };
  const world = screenToWorld(anchor, camera);
  assert.ok(camera.zoom < MIN_ZOOM);
  assert.strictEqual(zoomWorkflowAt(camera, camera.zoom * 0.8, anchor), camera);
  const closer = zoomWorkflowAt(camera, camera.zoom * 1.25, anchor);
  close(closer.zoom, camera.zoom * 1.25);
  assert.ok(closer.zoom < MIN_ZOOM);
  const screen = toScreen(world, closer);
  close(screen.x, anchor.x);
  close(screen.y, anchor.y);
});

test('camera helpers do not modify source positions or the existing camera', () => {
  const camera = Object.freeze({ x: 100, y: -40, zoom: 0.5 });
  const nodes = Object.freeze([Object.freeze({ x: -600, y: -300 })]);
  screenToWorld({ x: 10, y: 20 }, camera);
  zoomWorkflowAt(camera, 1, { x: 100, y: 80 });
  fitWorkflow(nodes, { width: 900, height: 600 });
  assert.deepEqual(camera, { x: 100, y: -40, zoom: 0.5 });
  assert.deepEqual(nodes, [{ x: -600, y: -300 }]);
});
