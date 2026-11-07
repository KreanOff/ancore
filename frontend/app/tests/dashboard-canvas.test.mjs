import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

const bundle = await build({
  entryPoints: [new URL('../src/shared/DashboardCanvas.tsx', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  external: ['react', 'react/jsx-runtime'],
  write: false,
});
const require = createRequire(import.meta.url);
const plain = (value) => JSON.parse(JSON.stringify(value));
const widget = (id, x = 0, y = 0) => Object.freeze({ id, x, y, w: 6, h: 5 });
const event = (values = {}) => ({
  pointerId: 1,
  button: 0,
  clientX: 10,
  clientY: 20,
  preventDefault() {},
  ...values,
});

function nodes(element) {
  if (!element || typeof element !== 'object') return [];
  if (Array.isArray(element)) return element.flatMap(nodes);
  return [element, ...nodes(element.props?.children)];
}
function byLabel(tree, label) {
  const match = nodes(tree).find((node) => node.props?.['aria-label'] === label);
  assert.ok(match, `Missing ${label}`);
  return match;
}

function ids(tree) {
  return nodes(tree)
    .filter((node) => node.type === 'section')
    .map((node) => node.props['data-summary-widget']);
}

function harness({ width = 1188, scale = 1, ...values } = {}) {
  const slots = [],
    effects = [],
    listeners = new Map(),
    observers = [],
    changes = [],
    notices = [];
  let cursor = 0,
    pendingEffects = [];
  const scroll = { scrollTop: 0 };
  const grid = {
    clientWidth: width,
    getBoundingClientRect: () => ({ width: width * scale }),
    closest: () => scroll,
    setPointerCapture: (pointerId) => {
      grid.captured = pointerId;
    },
  };
  let props = {
    widgets: [widget('41'), widget('new-card', 6)],
    catalog: ['41', 'new-card'].map((id) => ({ id, label: id, min_w: 4, min_h: 5 })),
    editing: true,
    onChange(next) {
      props.widgets = next;
      changes.push(next);
    },
    onNotice: (notice) => notices.push(notice),
    renderWidget: (id) => id,
    ...values,
  };
  const react = {
    ...require('react'),
    useState(initial) {
      const index = cursor++;
      if (!(index in slots)) slots[index] = initial;
      return [
        slots[index],
        (value) => {
          slots[index] = typeof value === 'function' ? value(slots[index]) : value;
        },
      ];
    },
    useRef(initial) {
      const index = cursor++;
      if (!(index in slots)) slots[index] = { current: initial };
      return slots[index];
    },
    useEffect(callback, deps) {
      const index = cursor++;
      const previous = effects[index];
      if (!previous || deps.some((dep, i) => !Object.is(dep, previous.deps[i]))) {
        pendingEffects.push(() => {
          previous?.cleanup?.();
          effects[index] = { deps, cleanup: callback() };
        });
      }
    },
  };
  const module = { exports: {} };
  vm.runInNewContext(bundle.outputFiles[0].text, {
    module,
    exports: module.exports,
    require: (name) => (name === 'react' ? react : require(name)),
    document: {
      addEventListener: (type, callback) => listeners.set(type, callback),
      removeEventListener: (type, callback) => {
        if (listeners.get(type) === callback) listeners.delete(type);
      },
    },
    ResizeObserver: class {
      constructor(callback) {
        this.callback = callback;
        observers.push(this);
      }
      observe(element) {
        this.element = element;
      }
      disconnect() {
        this.disconnected = true;
      }
    },
    requestAnimationFrame: (callback) => callback(),
    CSS: { escape: (id) => id },
  });
  return {
    changes,
    notices,
    grid,
    scroll,
    listeners,
    observers,
    get widgets() {
      return props.widgets;
    },
    render(next = {}) {
      cursor = 0;
      props = { ...props, ...next };
      const tree = module.exports.DashboardCanvas(props);
      tree.ref.current = grid;
      const queued = pendingEffects;
      pendingEffects = [];
      queued.forEach((callback) => callback());
      return tree;
    },
    dispose() {
      effects.forEach((effect) => effect.cleanup?.());
    },
  };
}

test('shared canvas moves arbitrary gadget IDs and resolves collisions while keeping edit DOM order', () => {
  const app = harness();
  const tree = app.render({ ariaLabel: 'Pulpit zespołu' });
  assert.equal(tree.props['aria-label'], 'Pulpit zespołu');
  byLabel(tree, 'Przesuń: 41').props.onKeyDown(event({ key: 'ArrowRight' }));
  assert.deepEqual(plain(app.widgets), [
    { ...widget('41'), x: 1 },
    { ...widget('new-card', 6), y: 5 },
  ]);
  const reordered = [widget('new-card', 0, 8), widget('41')];
  assert.deepEqual(ids(app.render({ widgets: reordered })), ['new-card', '41']);
  assert.deepEqual(ids(app.render({ editing: false })), ['41', 'new-card']);
});

test('pointer movement accounts for display scale and scrolling and Escape restores its initial draft', () => {
  const app = harness({ scale: 2 });
  const original = app.widgets;
  let tree = app.render();
  byLabel(tree, 'Przesuń: 41').props.onPointerDown(event());
  assert.equal(app.grid.captured, 1);
  tree = app.render();
  assert.match(byLabel(tree, '41').props.className, /is-moving/);
  app.scroll.scrollTop = 60;
  tree.props.onPointerMove(event({ clientX: 210, clientY: 140 }));
  assert.equal(app.widgets[0].x, 1);
  assert.equal(app.widgets[0].y, 2);
  app.listeners.get('keydown')(event({ key: 'Escape' }));
  assert.equal(app.widgets, original);
  tree.props.onPointerMove(event({ clientX: 410, clientY: 260 }));
  assert.equal(app.widgets, original);
  assert.equal(app.notices.at(-1), 'Anulowano przeciąganie.');
  assert.doesNotMatch(byLabel(app.render(), '41').props.className, /is-moving/);
  app.dispose();
  assert.equal(app.listeners.size, 0);
  assert.equal(app.observers[0].disconnected, true);
});

test('pointer resizing stays anchored at the right edge and cancellation restores all widgets', () => {
  const app = harness({ widgets: [widget('41', 6)] });
  const original = app.widgets;
  const tree = app.render();
  byLabel(tree, 'Zmień rozmiar: 41').props.onPointerDown(event());
  tree.props.onPointerMove(event({ clientX: 310, clientY: 140 }));
  assert.deepEqual(plain(app.widgets), [{ ...widget('41', 6), h: 7 }]);
  tree.props.onPointerCancel(event());
  assert.equal(app.widgets, original);
});

test('keyboard resizing stays anchored at right and bottom edges without changing the other dimension', () => {
  const app = harness({ widgets: [widget('41', 6, 195)] });
  const original = app.widgets;
  let handle = byLabel(app.render(), 'Zmień rozmiar: 41');
  handle.props.onKeyDown(event({ key: 'ArrowRight' }));
  assert.equal(app.widgets, original);
  handle.props.onKeyDown(event({ key: 'ArrowDown' }));
  assert.equal(app.widgets, original);
  handle.props.onKeyDown(event({ key: 'ArrowLeft' }));
  assert.deepEqual(plain(app.widgets), [{ ...widget('41', 6, 195), w: 5 }]);
  handle = byLabel(app.render(), 'Zmień rozmiar: 41');
  handle.props.onKeyDown(event({ key: 'ArrowRight' }));
  assert.deepEqual(plain(app.widgets), [widget('41', 6, 195)]);
});

test('stacked layout reorders cards through keyboard without starting pointer drag', () => {
  const app = harness({ width: 390 });
  app.render();
  let tree = app.render();
  byLabel(tree, 'Przesuń: 41').props.onPointerDown(event());
  assert.equal(app.grid.captured, undefined);
  byLabel(tree, 'Przesuń: 41').props.onKeyDown(event({ key: 'ArrowRight' }));
  assert.equal(app.changes.length, 0);
  byLabel(tree, 'Przesuń: 41').props.onKeyDown(event({ key: 'ArrowDown' }));
  tree = app.render();
  assert.equal(byLabel(tree, '41').props.style.order, 1);
  byLabel(tree, 'Przesuń: 41').props.onKeyDown(event({ key: 'ArrowUp' }));
  assert.equal(byLabel(app.render(), '41').props.style.order, 0);
});

test('busy and read-only canvases cannot start layout changes', () => {
  const app = harness({ busy: true });
  let tree = app.render();
  const handle = byLabel(tree, 'Przesuń: 41');
  assert.equal(handle.props.disabled, true);
  handle.props.onPointerDown(event());
  handle.props.onKeyDown(event({ key: 'ArrowRight' }));
  byLabel(tree, 'Zmień rozmiar: 41').props.onKeyDown(event({ key: 'ArrowRight' }));
  assert.equal(app.changes.length, 0);
  assert.equal(app.grid.captured, undefined);
  tree = app.render({ editing: false, busy: false });
  assert.equal(nodes(tree).filter((node) => node.type === 'button').length, 0);
  tree.props.onPointerMove(event({ clientX: 210 }));
  assert.equal(app.changes.length, 0);
});
