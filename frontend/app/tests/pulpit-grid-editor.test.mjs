import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

const bundle = await build({
  entryPoints: [new URL('../src/pulpits/DetailPage.tsx', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  external: ['react', 'react/jsx-runtime', 'react-dom'],
  plugins: [
    {
      name: 'page-boundaries',
      setup(build) {
        build.onResolve(
          { filter: /(?:\/shared\/(?:page|useDirtyGuard|usePageActions)|\/autoRefresh)$/ },
          ({ path }) => ({ path: `test:${path.split('/').at(-1)}`, external: true }),
        );
      },
    },
  ],
  write: false,
});
const require = createRequire(import.meta.url);
const plain = (value) => JSON.parse(JSON.stringify(value));
const flush = () => new Promise((resolve) => setImmediate(resolve));
const savedWidgets = [{ id: '41', x: 0, y: 0, w: 6, h: 8 }];
function data(values = {}) {
  return {
    dashboard: {
      name: 'Pulpit',
      url: '/dashboards/pulpit/',
      editable: true,
      description: '',
      emoji: 'layout-dashboard',
      refresh_interval: 60,
    },
    grid: { widgets: savedWidgets, revision: 4, save_url: '/dashboards/pulpit/grid/', columns: 12 },
    editing: false,
    editor_url: '/dashboards/pulpit/gadgets/',
    columns: [
      [
        {
          id: 41,
          label: 'Postęp pracy',
          icon: 'chart-no-axes-combined',
          edit_url: '/gadgets/41/edit/',
        },
      ],
    ],
    gadget_catalog: [{ kind: 'progress', name: 'Postęp pracy', icon: 'chart-no-axes-combined' }],
    max_gadgets: 24,
    modal: null,
    ...values,
  };
}
function nodes(element) {
  if (!element || typeof element !== 'object') return [];
  if (Array.isArray(element)) return element.flatMap(nodes);
  return [element, ...nodes(element.props?.children)];
}
function text(element) {
  if (element == null || typeof element === 'boolean') return '';
  if (Array.isArray(element)) return element.map(text).join('');
  if (typeof element !== 'object') return String(element);
  return text(element.props?.children);
}
function button(tree, label) {
  const match = nodes(tree).find((node) => node.type === 'button' && text(node) === label);
  assert.ok(match, `Missing button: ${label}`);
  return match;
}
const canvas = (tree) => nodes(tree).find((node) => node.props?.ariaLabel === 'Gadżety pulpitu');
const catalog = (tree) => nodes(tree).find((node) => typeof node.props?.add === 'function');

function harness(initialData = data()) {
  const slots = [],
    effects = [],
    requests = [],
    locations = [],
    guards = [],
    timers = [],
    confirms = [];
  let cursor = 0,
    queued = [],
    nextRequest,
    serial = 0;
  const actions = {
    modal: null,
    busy: false,
    error: '',
    close() {
      actions.modal = null;
    },
    open() {},
    act() {},
  };
  const document = {
    title: '',
    modalOpen: false,
    querySelector() {
      return this.modalOpen ? {} : null;
    },
  };
  const navigator = { onLine: true };
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
      if (!previous || deps.some((dep, i) => !Object.is(dep, previous.deps[i])))
        queued.push(() => {
          previous?.cleanup?.();
          effects[index] = { deps, cleanup: callback() };
        });
    },
  };
  const stubs = {
    'test:page': {
      setPageLocation: (url) => locations.push(url),
      pageRequest: (...args) => {
        requests.push(args);
        assert.ok(nextRequest, 'Unexpected request');
        return nextRequest(...args);
      },
    },
    'test:useDirtyGuard': { useDirtyGuard: (...args) => guards.push(args) },
    'test:usePageActions': { usePageActions: () => actions },
    'test:autoRefresh': {
      startAutoRefresh(interval, refresh) {
        const timer = { interval, refresh, disposed: false };
        timers.push(timer);
        return () => {
          timer.disposed = true;
        };
      },
    },
  };
  const module = { exports: {} };
  vm.runInNewContext(bundle.outputFiles[0].text, {
    module,
    exports: module.exports,
    require: (name) => (name === 'react' ? react : stubs[name] || require(name)),
    AbortController,
    Error,
    TypeError,
    document,
    navigator,
    crypto: { randomUUID: () => `uuid-${++serial}` },
    requestAnimationFrame: (callback) => callback(),
    window: { showConfirmModal: (options) => confirms.push(options) },
  });
  return {
    requests,
    locations,
    guards,
    timers,
    actions,
    document,
    navigator,
    confirms,
    respond(callback) {
      nextRequest = callback;
    },
    render() {
      cursor = 0;
      const tree = module.exports.DashboardView({
        initial: { data: initialData, api_url: '/api/v1/page/' },
        csrfToken: 'test-csrf',
      });
      const pending = queued;
      queued = [];
      pending.forEach((callback) => callback());
      return tree;
    },
    dispose() {
      effects.forEach((effect) => effect.cleanup?.());
    },
  };
}

test('staged gadget additions, moves and removals do not write before save and cancel restores saved layout', () => {
  const app = harness();
  button(app.render(), 'Edytuj pulpit').props.onClick();
  let tree = app.render();
  button(tree, 'Dodaj gadżet').props.onClick();
  tree = app.render();
  catalog(tree).props.add('progress');
  catalog(app.render()).props.add('progress');
  tree = app.render();
  assert.equal(canvas(tree).props.widgets.length, 3);
  assert.equal(new Set(canvas(tree).props.widgets.map((item) => item.id)).size, 3);
  canvas(tree).props.onChange(
    canvas(tree).props.widgets.map((item) => ({ ...item, y: item.y + 2 })),
  );
  canvas(app.render()).props.onRemove('41');
  tree = app.render();
  assert.equal(canvas(tree).props.widgets.length, 2);
  assert.deepEqual(app.guards.at(-1), [true, false]);
  assert.equal(app.requests.length, 0);
  button(tree, 'Anuluj').props.onClick();
  tree = app.render();
  assert.deepEqual(plain(canvas(tree).props.widgets), savedWidgets);
  assert.equal(canvas(tree).props.editing, false);
  assert.deepEqual(app.guards.at(-1), [false, false]);
  assert.equal(app.locations.at(-1), '/dashboards/pulpit/');
  assert.equal(app.requests.length, 0);
});

test('save posts one revisioned draft including new gadget kinds and accepts server IDs', async () => {
  const app = harness(data({ editing: true }));
  button(app.render(), 'Dodaj gadżet').props.onClick();
  catalog(app.render()).props.add('progress');
  let tree = app.render();
  let resolve;
  app.respond(
    () =>
      new Promise((done) => {
        resolve = done;
      }),
  );
  const save = button(tree, 'Zapisz układ');
  save.props.onClick();
  save.props.onClick();
  assert.equal(app.requests.length, 1);
  const request = app.requests[0];
  assert.equal(request[0], '/api/v1/page/');
  assert.equal(request[1], '/dashboards/pulpit/grid/');
  assert.equal(request[2], 'test-csrf');
  assert.equal(request[4].revision, 4);
  assert.equal(request[4].widgets[0].kind, undefined);
  assert.equal(request[4].widgets[1].kind, 'progress');
  assert.match(request[4].widgets[1].id, /^new-/);
  tree = app.render();
  assert.equal(button(tree, 'Anuluj').props.disabled, true);
  assert.equal(canvas(tree).props.busy, true);
  assert.deepEqual(app.guards.at(-1), [true, true]);
  const widgets = plain(request[4].widgets).map(({ kind, ...item }) => ({
    ...item,
    id: item.id.startsWith('new-') ? '42' : item.id,
  }));
  resolve({
    page: { type: 'pulpit-detail', data: data({ grid: { ...data().grid, revision: 5, widgets } }) },
  });
  await flush();
  tree = app.render();
  assert.equal(canvas(tree).props.editing, false);
  assert.deepEqual(plain(canvas(tree).props.widgets), widgets);
  assert.match(text(tree), /Układ pulpitu zapisany/);
  assert.deepEqual(app.guards.at(-1), [false, false]);
});

test('failed save preserves staged layout and retry revision while reload requires a discard decision', async () => {
  const app = harness(data({ editing: true }));
  canvas(app.render()).props.onChange([{ ...savedWidgets[0], w: 12 }]);
  app.respond(async () => {
    throw new Error('Pulpit został zmieniony.');
  });
  button(app.render(), 'Zapisz układ').props.onClick();
  await flush();
  let tree = app.render();
  assert.equal(canvas(tree).props.editing, true);
  assert.equal(canvas(tree).props.widgets[0].w, 12);
  assert.match(text(tree), /Pulpit został zmieniony/);
  assert.equal(button(tree, 'Zapisz układ').props.disabled, false);
  button(tree, 'Wczytaj aktualny układ').props.onClick();
  assert.equal(app.confirms.length, 1);
  assert.equal(app.requests.length, 1);
  button(tree, 'Zapisz układ').props.onClick();
  await flush();
  assert.equal(app.requests[1][4].revision, 4);
  app.respond(async () => ({
    type: 'pulpit-detail',
    data: data({ grid: { ...data().grid, revision: 6 } }),
  }));
  app.confirms[0].onConfirm();
  await flush();
  tree = app.render();
  assert.deepEqual(plain(canvas(tree).props.widgets), savedWidgets);
  assert.equal(canvas(tree).props.editing, true);
  assert.deepEqual(app.guards.at(-1), [false, false]);
  assert.equal(
    nodes(tree).some((node) => node.props?.role === 'alert'),
    false,
  );
});

test('auto refresh pauses during editing, modal work and offline state and restarts after cancel', async () => {
  const app = harness();
  let tree = app.render();
  assert.equal(app.timers.length, 1);
  const first = app.timers[0];
  app.respond(async () => ({ type: 'pulpit-detail', data: data() }));
  app.document.modalOpen = true;
  await first.refresh();
  app.document.modalOpen = false;
  app.navigator.onLine = false;
  await first.refresh();
  app.navigator.onLine = true;
  app.actions.modal = {};
  app.render();
  await first.refresh();
  app.actions.modal = null;
  app.actions.busy = true;
  app.render();
  await first.refresh();
  assert.equal(app.requests.length, 0);
  app.actions.busy = false;
  tree = app.render();
  button(tree, 'Edytuj pulpit').props.onClick();
  tree = app.render();
  assert.equal(first.disposed, true);
  await first.refresh();
  assert.equal(app.requests.length, 0);
  button(tree, 'Anuluj').props.onClick();
  app.render();
  assert.equal(app.timers.length, 2);
  await app.timers[1].refresh();
  assert.equal(app.requests.length, 1);
  app.dispose();
  assert.equal(app.timers[1].disposed, true);
});

test('saved gadget configuration is blocked for dirty layouts and refresh failure is propagated to its form', async () => {
  const app = harness(data({ editing: true }));
  let tree = app.render();
  assert.equal(canvas(tree).props.renderActions('41', () => {}).props.disabled, false);
  canvas(tree).props.onChange([{ ...savedWidgets[0], y: 1 }]);
  tree = app.render();
  assert.equal(canvas(tree).props.renderActions('41', () => {}).props.disabled, true);
  button(tree, 'Anuluj').props.onClick();
  app.actions.modal = {};
  tree = app.render();
  app.respond(async () => {
    throw new Error('Nie można odświeżyć konfiguracji.');
  });
  const form = nodes(tree).find((node) => typeof node.props?.onSaved === 'function');
  await assert.rejects(form.props.onSaved(), /Nie można odświeżyć konfiguracji/);
  assert.ok(app.actions.modal);
});
