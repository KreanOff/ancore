import assert from 'node:assert/strict';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

const bundle = await build({
  entryPoints: [new URL('../src/spaces/workflow-minimap.ts', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  write: false,
});
const module = { exports: {} };
vm.runInNewContext(bundle.outputFiles[0].text, { module, exports: module.exports });
const { workflowMinimap, minimapToWorld } = module.exports;
const close = (actual, expected) =>
  assert.ok(Math.abs(actual - expected) <= Math.max(1, Math.abs(expected)) * 1e-9);
const toMini = (point, projection) => ({
  x: point.x * projection.scale + projection.x,
  y: point.y * projection.scale + projection.y,
});
const inside = (rectangle, projection, padding = 10) => {
  assert.ok(rectangle.x >= padding - 1e-8);
  assert.ok(rectangle.y >= padding - 1e-8);
  assert.ok(rectangle.x + rectangle.width <= projection.width - padding + 1e-8);
  assert.ok(rectangle.y + rectangle.height <= projection.height - padding + 1e-8);
};

test('minimap contains full signed cards and a viewport panned away from the graph', () => {
  const nodes = [
    { x: -900, y: -640 },
    { x: 500, y: 350 },
    { x: -80, y: 720 },
  ];
  const camera = { x: -3000, y: 2000, zoom: 0.5 };
  const viewport = { width: 840, height: 620 };
  const projection = workflowMinimap(nodes, camera, viewport);
  inside(projection.viewport, projection);
  projection.nodes.forEach((rectangle, index) => {
    inside(rectangle, projection);
    const start = minimapToWorld(rectangle, projection);
    const end = minimapToWorld(
      { x: rectangle.x + rectangle.width, y: rectangle.y + rectangle.height },
      projection,
    );
    close(start.x, nodes[index].x);
    close(start.y, nodes[index].y);
    close(end.x, nodes[index].x + 220);
    close(end.y, nodes[index].y + 88);
  });
  const start = minimapToWorld(projection.viewport, projection);
  const end = minimapToWorld(
    {
      x: projection.viewport.x + projection.viewport.width,
      y: projection.viewport.y + projection.viewport.height,
    },
    projection,
  );
  close(start.x * camera.zoom + camera.x, 0);
  close(start.y * camera.zoom + camera.y, 0);
  close(end.x * camera.zoom + camera.x, viewport.width);
  close(end.y * camera.zoom + camera.y, viewport.height);
});

test('click coordinates round trip at both position limits and below the manual zoom limit', () => {
  const nodes = [
    { x: -1000000, y: 1000000 },
    { x: 1000000, y: -1000000 },
  ];
  for (const zoom of [0.000001, 0.01, 0.5, 2]) {
    const projection = workflowMinimap(
      nodes,
      { x: -400, y: 200, zoom },
      { width: 900, height: 600 },
    );
    assert.ok(Number.isFinite(projection.scale) && projection.scale > 0);
    inside(projection.viewport, projection);
    projection.nodes.forEach((rectangle) => inside(rectangle, projection));
    for (const point of [...nodes, { x: 0, y: 0 }, { x: -123.75, y: 643.25 }]) {
      const restored = minimapToWorld(toMini(point, projection), projection);
      close(restored.x, point.x);
      close(restored.y, point.y);
    }
  }
});

test('empty minimap centers the visible world and remains usable before viewport measurement', () => {
  const camera = { x: 300, y: -180, zoom: 0.5 };
  for (const viewport of [
    { width: 800, height: 600 },
    { width: 0, height: 0 },
  ]) {
    const projection = workflowMinimap([], camera, viewport);
    assert.equal(projection.nodes.length, 0);
    inside(projection.viewport, projection);
    close(projection.viewport.x + projection.viewport.width / 2, projection.width / 2);
    close(projection.viewport.y + projection.viewport.height / 2, projection.height / 2);
    const center = minimapToWorld(
      { x: projection.width / 2, y: projection.height / 2 },
      projection,
    );
    close(center.x, (viewport.width / 2 - camera.x) / camera.zoom);
    close(center.y, (viewport.height / 2 - camera.y) / camera.zoom);
  }
});

test('custom minimap size preserves aspect ratio, padding and the full graph', () => {
  const projection = workflowMinimap(
    [
      { x: -600, y: -1000 },
      { x: 300, y: 2000 },
    ],
    { x: 50, y: -20, zoom: 1.5 },
    { width: 400, height: 300 },
    { width: 160, height: 90 },
    8,
  );
  assert.equal(projection.width, 160);
  assert.equal(projection.height, 90);
  inside(projection.viewport, projection, 8);
  projection.nodes.forEach((rectangle) => {
    inside(rectangle, projection, 8);
    close(rectangle.width / rectangle.height, 220 / 88);
  });
});

test('projection and navigation leave positions, camera, viewport and size unchanged', () => {
  const nodes = Object.freeze([Object.freeze({ x: -400, y: 230 })]);
  const camera = Object.freeze({ x: 50, y: -20, zoom: 0.75 });
  const viewport = Object.freeze({ width: 800, height: 600 });
  const size = Object.freeze({ width: 200, height: 112 });
  const before = JSON.stringify({ nodes, camera, viewport, size });
  const projection = workflowMinimap(nodes, camera, viewport, size);
  const projected = JSON.stringify(projection);
  minimapToWorld(Object.freeze({ x: 30, y: 40 }), projection);
  assert.equal(JSON.stringify(projection), projected);
  assert.equal(JSON.stringify({ nodes, camera, viewport, size }), before);
});
