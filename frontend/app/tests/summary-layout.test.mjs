import assert from 'node:assert/strict';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

const bundle = await build({
  entryPoints: [new URL('../src/spaces/summaryLayout.ts', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  write: false,
});
const module = { exports: {} };
vm.runInNewContext(bundle.outputFiles[0].text, { module, exports: module.exports });
const {
  GRID_COLUMNS,
  MAX_GRID_ROWS,
  MAX_WIDGET_HEIGHT,
  addWidget,
  clampWidget,
  layoutsEqual,
  moveWidget,
  moveWidgetInOrder,
  resizeWidget,
  updateWidget,
  widgetMinimum,
  widgetsOverlap,
} = module.exports;

const widget = (id, x, y, w = 6, h = 5) => ({ id, x, y, w, h });
const freeze = (layout) => Object.freeze(layout.map(Object.freeze));
const plain = (value) => JSON.parse(JSON.stringify(value));

// These are the bounds the save endpoint accepts, independent of the engine's
// collision helper so a shared mistake cannot conceal overlapping rectangles.
function valid(layout) {
  assert.equal(new Set(layout.map((item) => item.id)).size, layout.length);
  for (const item of layout) {
    const metric = ['completed', 'updated', 'created', 'due'].includes(item.id);
    for (const key of ['x', 'y', 'w', 'h'])
      assert.ok(Number.isInteger(item[key]), `${item.id}.${key}`);
    assert.ok(item.x >= 0 && item.y >= 0);
    assert.ok(item.w >= (metric ? 3 : 4) && item.h >= (metric ? 2 : 5));
    assert.ok(item.h <= MAX_WIDGET_HEIGHT);
    assert.ok(item.x + item.w <= GRID_COLUMNS);
    assert.ok(item.y + item.h <= MAX_GRID_ROWS);
  }
  for (let index = 0; index < layout.length; index++) {
    for (const other of layout.slice(index + 1)) {
      const item = layout[index];
      assert.ok(
        item.x + item.w <= other.x ||
          other.x + other.w <= item.x ||
          item.y + item.h <= other.y ||
          other.y + other.h <= item.y,
        `${item.id} overlaps ${other.id}`,
      );
    }
  }
}

test('widget dimensions and positions stay within metric, panel and save limits', () => {
  for (const id of ['completed', 'updated', 'created', 'due', 'statuses', 'activity']) {
    const minimum = ['completed', 'updated', 'created', 'due'].includes(id)
      ? { w: 3, h: 2 }
      : { w: 4, h: 5 };
    assert.deepEqual(plain(widgetMinimum(id)), minimum);
    const smallest = clampWidget(widget(id, -8, -9, -10, -11));
    assert.deepEqual(plain(smallest), { id, x: 0, y: 0, ...minimum });
    const largest = clampWidget(widget(id, 30, 1000, 30, 100));
    assert.deepEqual(plain(largest), { id, x: 0, y: 184, w: 12, h: 16 });
    valid([smallest]);
    valid([largest]);
  }
  assert.deepEqual(plain(clampWidget(widget('due', 11.8, 2.4, 3.2, 2.7))), {
    id: 'due',
    x: 9,
    y: 2,
    w: 3,
    h: 3,
  });
  valid([clampWidget(widget('activity', NaN, Infinity, NaN, -Infinity))]);
});

test('touching edges are available grid space while genuine intersections collide', () => {
  const left = widget('statuses', 0, 0);
  assert.equal(widgetsOverlap(left, widget('activity', 6, 0)), false);
  assert.equal(widgetsOverlap(left, widget('activity', 0, 5)), false);
  assert.equal(widgetsOverlap(left, widget('activity', 5, 4)), true);
  assert.equal(widgetsOverlap(left, { ...left, id: 'activity' }), true);
});

test('moving a widget pushes a whole collision chain down without changing the source', () => {
  const source = freeze([
    widget('completed', 0, 0, 3, 2),
    widget('statuses', 0, 2),
    widget('activity', 0, 7),
    widget('priorities', 0, 12),
    widget('workload', 6, 2, 6, 15),
  ]);
  const moved = updateWidget(source, 'completed', { y: 3 });
  assert.deepEqual(
    moved.map((item) => item.id),
    source.map((item) => item.id),
  );
  assert.deepEqual(plain(moved.map(({ id, y }) => ({ id, y }))), [
    { id: 'completed', y: 3 },
    { id: 'statuses', y: 5 },
    { id: 'activity', y: 10 },
    { id: 'priorities', y: 15 },
    { id: 'workload', y: 2 },
  ]);
  assert.deepEqual(
    source.map((item) => item.y),
    [0, 2, 7, 12, 2],
  );
  assert.equal(moved[4], source[4]);
  valid(moved);
});

test('resizing pins the target and settles both columns in stable original spatial order', () => {
  const source = freeze([
    widget('completed', 0, 0, 3, 2),
    widget('statuses', 0, 2),
    widget('activity', 6, 2),
    widget('types', 0, 7, 12, 5),
  ]);
  const resized = updateWidget(source, 'completed', { w: 12, h: 8 });
  assert.deepEqual(plain(resized), [
    widget('completed', 0, 0, 12, 8),
    widget('statuses', 0, 8),
    widget('activity', 6, 8),
    widget('types', 0, 13, 12, 5),
  ]);
  assert.deepEqual(plain(updateWidget(source, 'completed', { h: 8, w: 12 })), plain(resized));
  valid(resized);
});

test('moving into free space preserves intentional gaps and clamps horizontal and vertical edges', () => {
  const source = freeze([widget('completed', 0, 0, 3, 2), widget('statuses', 0, 20)]);
  const moved = updateWidget(source, 'completed', { x: 100, y: 1000 });
  assert.deepEqual(plain(moved[0]), widget('completed', 9, 198, 3, 2));
  assert.equal(moved[1], source[1]);
  valid(moved);
  const upperLeft = updateWidget(moved, 'completed', { x: -100, y: -100 });
  assert.deepEqual(plain(upperLeft[0]), source[0]);
  assert.equal(upperLeft[1], source[1]);
  valid(upperLeft);
});

test('impossible cascades are rejected atomically and no-op updates retain array identity', () => {
  const source = freeze([widget('completed', 0, 0, 12, 2), widget('statuses', 0, 195, 12, 5)]);
  assert.equal(updateWidget(source, 'completed', { y: 194, h: 6 }), source);
  assert.equal(updateWidget(source, 'completed', { x: -1, y: -1 }), source);
  assert.equal(updateWidget(source, 'completed', {}), source);
  assert.equal(updateWidget(source, 'missing', { y: 5 }), source);
  valid(source);
});

test('directional controls move exactly one cell on the chosen axis and preserve size', () => {
  const source = freeze([widget('statuses', 3, 10, 6, 7)]);
  for (const [direction, x, y] of [
    ['left', 2, 10],
    ['right', 4, 10],
    ['up', 3, 9],
    ['down', 3, 11],
  ]) {
    const moved = moveWidget(source, 'statuses', direction);
    assert.deepEqual(plain(moved), [widget('statuses', x, y, 6, 7)]);
    assert.deepEqual(plain(source), [widget('statuses', 3, 10, 6, 7)]);
    valid(moved);
  }
});

test('directional controls stop at every canvas boundary without changing the array', () => {
  for (const [direction, x, y] of [
    ['left', 0, 10],
    ['right', 6, 10],
    ['up', 3, 0],
    ['down', 3, 193],
  ]) {
    const source = freeze([widget('statuses', x, y, 6, 7)]);
    assert.equal(moveWidget(source, 'statuses', direction), source);
  }
  const source = freeze([widget('statuses', 0, 0)]);
  assert.equal(moveWidget(source, 'missing', 'right'), source);
});

test('a directional move resolves intersected neighbours with the same deterministic cascade', () => {
  const source = freeze([
    widget('completed', 0, 0, 3, 2),
    widget('updated', 3, 0, 3, 2),
    widget('statuses', 0, 2, 6, 5),
  ]);
  const moved = moveWidget(source, 'completed', 'right');
  assert.deepEqual(plain(moved), [
    widget('completed', 1, 0, 3, 2),
    widget('updated', 3, 2, 3, 2),
    widget('statuses', 0, 4, 6, 5),
  ]);
  valid(moved);
  const blocked = freeze([widget('completed', 0, 195, 3, 2), widget('statuses', 3, 195, 6, 5)]);
  assert.equal(moveWidget(blocked, 'completed', 'right'), blocked);
});

const visibleOrder = (layout) =>
  [...layout].sort((a, b) => a.y - b.y || a.x - b.x).map((item) => item.id);

test('stacked-screen movement swaps exactly one same-row neighbour and retains source array order', () => {
  const source = freeze([
    widget('completed', 0, 0, 3, 2),
    widget('updated', 3, 0, 3, 2),
    widget('created', 6, 0, 3, 2),
    widget('due', 9, 0, 3, 2),
    widget('statuses', 0, 2, 6, 6),
    widget('activity', 6, 2, 6, 6),
  ]);
  const original = plain(source);
  const moved = moveWidgetInOrder(source, 'updated', 'down');
  assert.deepEqual(visibleOrder(moved), [
    'completed',
    'created',
    'updated',
    'due',
    'statuses',
    'activity',
  ]);
  assert.deepEqual(plain(moved[1]), widget('updated', 6, 0, 3, 2));
  assert.deepEqual(plain(moved[2]), widget('created', 3, 0, 3, 2));
  assert.deepEqual(
    moved.map((item) => item.id),
    source.map((item) => item.id),
  );
  assert.deepEqual(plain(source), original);
  valid(moved);
  const restored = moveWidgetInOrder(moved, 'updated', 'up');
  assert.deepEqual(plain(restored), original);
});

test('stacked-screen movement preserves the intended one-card swap for unequal widths and heights', () => {
  const source = freeze([
    widget('statuses', 0, 0, 4, 8),
    widget('activity', 4, 0, 8, 5),
    widget('types', 4, 5, 8, 5),
    widget('workload', 0, 10, 12, 6),
  ]);
  const moved = moveWidgetInOrder(source, 'activity', 'down');
  assert.deepEqual(visibleOrder(moved), ['statuses', 'types', 'activity', 'workload']);
  assert.deepEqual(plain(moved), [
    widget('statuses', 0, 0, 4, 8),
    widget('activity', 0, 8, 8, 5),
    widget('types', 4, 0, 8, 5),
    widget('workload', 0, 13, 12, 6),
  ]);
  assert.deepEqual(plain(moveWidgetInOrder(source, 'types', 'up')), plain(moved));
  for (const direction of ['up', 'down']) {
    for (let index = 0; index < source.length; index++) {
      const next = moveWidgetInOrder(source, source[index].id, direction);
      const expected = visibleOrder(source);
      const adjacent = index + (direction === 'up' ? -1 : 1);
      if (adjacent >= 0 && adjacent < expected.length) {
        [expected[index], expected[adjacent]] = [expected[adjacent], expected[index]];
      }
      assert.deepEqual(visibleOrder(next), expected);
      assert.deepEqual(
        plain(next.map(({ id, w, h }) => ({ id, w, h }))),
        plain(source.map(({ id, w, h }) => ({ id, w, h }))),
      );
      valid(next);
    }
  }
});

test('stacked-screen movement uses spatial order for unsorted arrays and stops at either end', () => {
  const source = freeze([
    widget('activity', 6, 30, 6, 5),
    widget('statuses', 0, 10, 6, 8),
    widget('types', 0, 30, 6, 5),
  ]);
  assert.deepEqual(visibleOrder(source), ['statuses', 'types', 'activity']);
  const moved = moveWidgetInOrder(source, 'types', 'down');
  assert.deepEqual(visibleOrder(moved), ['statuses', 'activity', 'types']);
  assert.deepEqual(
    moved.map((item) => item.id),
    source.map((item) => item.id),
  );
  assert.equal(moveWidgetInOrder(source, 'statuses', 'up'), source);
  assert.equal(moveWidgetInOrder(source, 'activity', 'down'), source);
  assert.equal(moveWidgetInOrder(source, 'missing', 'down'), source);
  const single = freeze([widget('statuses', 4, 190, 6, 5)]);
  assert.equal(moveWidgetInOrder(single, 'statuses', 'up'), single);
  assert.equal(moveWidgetInOrder(single, 'statuses', 'down'), single);
  valid(moved);
});

test('size controls preserve the anchor and the unchanged dimension at right and bottom edges', () => {
  const source = freeze([widget('statuses', 7, 194, 4, 5)]);
  const wider = resizeWidget(source, 'statuses', { w: 12 });
  assert.deepEqual(plain(wider), [widget('statuses', 7, 194, 5, 5)]);
  const taller = resizeWidget(source, 'statuses', { h: 16 });
  assert.deepEqual(plain(taller), [widget('statuses', 7, 194, 4, 6)]);
  const largest = resizeWidget(source, 'statuses', { w: 12, h: 16 });
  assert.deepEqual(plain(largest), [widget('statuses', 7, 194, 5, 6)]);
  assert.equal(resizeWidget(largest, 'statuses', { w: 12, h: 16 }), largest);
  assert.deepEqual(plain(source), [widget('statuses', 7, 194, 4, 5)]);
  for (const resized of [wider, taller, largest]) valid(resized);
});

test('size controls enforce the metric and panel minimums without moving either anchor', () => {
  for (const [id, w, h] of [
    ['completed', 3, 2],
    ['statuses', 4, 5],
  ]) {
    const source = freeze([widget(id, 4, 20, 6, 10)]);
    const smallest = resizeWidget(source, id, { w: -100, h: -100 });
    assert.deepEqual(plain(smallest), [widget(id, 4, 20, w, h)]);
    assert.equal(resizeWidget(smallest, id, { w: -1, h: -1 }), smallest);
    assert.equal(resizeWidget(source, id, {}), source);
    assert.equal(resizeWidget(source, 'missing', { w: 8 }), source);
    valid(smallest);
  }
});

test('anchored resizing pushes intersected neighbours and atomically rejects overflowing cascades', () => {
  const source = freeze([
    widget('statuses', 4, 3, 4, 5),
    widget('activity', 8, 3, 4, 5),
    widget('types', 0, 8, 12, 5),
  ]);
  const larger = resizeWidget(source, 'statuses', { w: 8, h: 12 });
  assert.deepEqual(plain(larger), [
    widget('statuses', 4, 3, 8, 12),
    widget('activity', 8, 15, 4, 5),
    widget('types', 0, 20, 12, 5),
  ]);
  valid(larger);
  const blocked = freeze([
    widget('statuses', 0, 190, 6, 5),
    widget('activity', 6, 190, 6, 10),
    widget('types', 0, 195, 6, 5),
  ]);
  assert.equal(resizeWidget(blocked, 'statuses', { w: 12 }), blocked);
  assert.equal(resizeWidget(blocked, 'statuses', { h: 9 }), blocked);
  valid(blocked);
});

test('adding a widget fills the first fitting hole before extending the grid', () => {
  const source = freeze([
    widget('completed', 0, 0, 3, 2),
    widget('created', 6, 0, 3, 2),
    widget('due', 9, 0, 3, 2),
    widget('statuses', 0, 2, 12, 5),
  ]);
  const filled = addWidget(source, { id: 'updated' });
  assert.deepEqual(plain(filled.at(-1)), widget('updated', 3, 0, 3, 2));
  const extended = addWidget(filled, { id: 'activity', w: 6, h: 8 });
  assert.deepEqual(plain(extended.at(-1)), widget('activity', 0, 7, 6, 8));
  assert.equal(addWidget(extended, { id: 'activity', w: 12, h: 16 }), extended);
  assert.equal(source.length, 4);
  valid(filled);
  valid(extended);
});

test('adding returns the untouched layout when the grid has no fitting free rectangle', () => {
  const source = freeze(
    Array.from({ length: 13 }, (_, i) => widget(`panel-${i}`, 0, i * 16, 12, i === 12 ? 8 : 16)),
  );
  valid(source);
  assert.equal(addWidget(source, { id: 'completed' }), source);
  assert.equal(addWidget(source, { id: 'activity' }), source);
});

test('layout equality ignores array order but detects removed, resized and moved widgets', () => {
  const source = freeze([widget('completed', 0, 0, 3, 2), widget('statuses', 0, 2)]);
  assert.equal(layoutsEqual(source, [...source].reverse()), true);
  assert.equal(
    layoutsEqual(
      source,
      source.map((item) => ({ ...item })),
    ),
    true,
  );
  assert.equal(layoutsEqual(source, source.slice(1)), false);
  for (const key of ['x', 'y', 'w', 'h']) {
    assert.equal(
      layoutsEqual(source, [{ ...source[0], [key]: source[0][key] + 1 }, source[1]]),
      false,
    );
  }
  assert.equal(layoutsEqual(source, [source[0], source[0]]), false);
  assert.equal(layoutsEqual([], []), true);
});

test('many deterministic move and resize sequences always produce a layout accepted by save bounds', () => {
  const catalog = [
    'completed',
    'updated',
    'created',
    'due',
    'statuses',
    'activity',
    'priorities',
    'types',
    'workload',
    'epics',
  ];
  let layout = [];
  for (const id of catalog) {
    layout = addWidget(layout, {
      id,
      ...(['completed', 'updated', 'created', 'due'].includes(id)
        ? { w: 3, h: 2 }
        : { w: 6, h: 7 }),
    });
  }
  let seed = 805016;
  const random = (maximum) => {
    seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
    return seed % maximum;
  };
  valid(layout);
  for (let i = 0; i < 400; i++) {
    const before = plain(layout);
    const changes = { x: random(18) - 3, y: random(225) - 10, w: random(18), h: random(22) };
    const id = catalog[random(catalog.length)];
    const next = updateWidget(layout, id, changes);
    assert.deepEqual(plain(layout), before, 'the saved layout is never mutated');
    assert.deepEqual(
      plain(updateWidget(layout, id, changes)),
      plain(next),
      'repeated input is deterministic',
    );
    valid(next);
    assert.deepEqual(plain(next.map((item) => item.id)), catalog);
    layout = next;
  }
});
