import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

// Exercise the real component and HTTP helper with controlled hooks, DOM and time.
const bundle = await build({
  entryPoints: [new URL('../src/shell/Search.tsx', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  jsx: 'automatic',
  external: ['react', 'react/jsx-runtime', 'react-dom'],
  write: false,
});
const require = createRequire(import.meta.url);
const base = '/workplaces/w_test/';
const settle = () => new Promise(setImmediate);

function nodes(element) {
  if (!element || typeof element !== 'object') return [];
  if (Array.isArray(element)) return element.flatMap(nodes);
  return [element, ...nodes(element.props?.children)];
}
function byClass(tree, name) {
  return nodes(tree).find((node) => node.props?.className?.split(' ').includes(name));
}
function result(title) {
  return {
    title,
    type: 'Zadanie',
    url: base + 'space/produkt/tasks/' + title + '/',
    icon: 'list-checks',
    meta: 'Produkt',
    eyebrow: '',
  };
}
function payload(titles = ['PRO-1', 'PRO-2'], overrides = {}) {
  return {
    query: 'produkt',
    total: titles.length,
    groups: [
      {
        key: 'space_tasks',
        label: 'Zadania przestrzeni',
        icon: 'list-checks',
        has_more: false,
        results: titles.map(result),
      },
    ],
    ...overrides,
  };
}

function harness() {
  const slots = [],
    timers = new Map(),
    requests = [],
    navigation = [],
    documentListeners = new Map(),
    windowListeners = new Map(),
    anchors = new Map();
  let cursor = 0,
    dirty = false,
    pending = [],
    tree,
    now = 0,
    nextTimer = 0;
  const same = (a, b) =>
    a && b && a.length === b.length && a.every((value, index) => Object.is(value, b[index]));
  function slot(create) {
    const index = cursor++;
    if (!(index in slots)) slots[index] = create();
    return slots[index];
  }
  const hooks = {
    useState(initial) {
      const state = slot(() => ({ value: typeof initial === 'function' ? initial() : initial }));
      return [
        state.value,
        (next) => {
          const value = typeof next === 'function' ? next(state.value) : next;
          if (!Object.is(value, state.value)) dirty = true;
          state.value = value;
        },
      ];
    },
    useRef(initial) {
      return slot(() => ({ current: initial }));
    },
    useEffect(callback, dependencies) {
      const effect = slot(() => ({}));
      if (!same(effect.dependencies, dependencies)) {
        effect.dependencies = dependencies;
        pending.push(() => {
          effect.cleanup?.();
          effect.cleanup = callback();
        });
      }
    },
  };
  const document = {
    activeElement: null,
    body: { classList: { toggle() {}, remove() {} } },
    querySelector: () => null,
    getElementById: () => null,
    addEventListener: (name, callback) => documentListeners.set(name, callback),
    removeEventListener: (name, callback) => {
      if (documentListeners.get(name) === callback) documentListeners.delete(name);
    },
  };
  const input = {
    focus() {
      document.activeElement = input;
      input.element.props.onFocus?.();
    },
    select() {},
    matches: () => true,
  };
  const form = { contains: () => true, closest: () => null };
  const links = () =>
    nodes(tree)
      .filter((node) => node.type === 'a')
      .map((node) => anchors.get(node.props.href));
  const results = {
    querySelectorAll: links,
    querySelector: (selector) =>
      links().find(
        (link) =>
          !selector.includes('.is-active') ||
          link.element.props.className.split(' ').includes('is-active'),
      ),
    scrollTo() {},
  };
  const module = { exports: {} };
  vm.runInNewContext(bundle.outputFiles[0].text, {
    module,
    exports: module.exports,
    require: (name) =>
      name === 'react'
        ? { ...require('react'), ...hooks }
        : name === 'react-dom'
          ? { flushSync: (callback) => callback() }
          : require(name),
    AbortController,
    AbortSignal,
    URL,
    URLSearchParams,
    FormData,
    CustomEvent: class {
      constructor(type) {
        this.type = type;
      }
    },
    location: { origin: 'http://localhost' },
    document,
    window: {
      dispatchEvent: (event) => windowListeners.get(event.type)?.(event),
      addEventListener: (name, callback) => windowListeners.set(name, callback),
      removeEventListener: (name, callback) => {
        if (windowListeners.get(name) === callback) windowListeners.delete(name);
      },
    },
    setTimeout(callback, delay = 0) {
      const id = ++nextTimer;
      timers.set(id, { callback, at: now + delay });
      return id;
    },
    clearTimeout: (id) => timers.delete(id),
    fetch: (url, options) =>
      new Promise((resolve) => requests.push({ url: String(url), ...options, resolve })),
  });

  function render(effects = true) {
    let commits = 0;
    do {
      assert.ok(++commits < 20, 'search rendering should settle');
      cursor = 0;
      dirty = false;
      tree = module.exports.default({
        config: { api_url: base + 'api/v1/page/', search_url: base + 'global-search/' },
        token: 'search-csrf',
      });
      tree.ref.current = form;
      input.element = nodes(tree).find((node) => node.type === 'input');
      input.element.ref.current = input;
      byClass(tree, 'global-search-results').ref.current = results;
      for (const element of nodes(tree).filter((node) => node.type === 'a')) {
        const href = element.props.href;
        if (!anchors.has(href)) {
          const anchor = {
            closest: () => anchor,
            focus() {
              document.activeElement = anchor;
              anchor.element.props.onFocus?.();
            },
            scrollIntoView() {},
            click() {
              navigation.push(href);
              anchor.element.props.onClick?.();
            },
          };
          anchors.set(href, anchor);
        }
        anchors.get(href).element = element;
      }
      if (effects) {
        const callbacks = pending;
        pending = [];
        for (const callback of callbacks) callback();
      }
    } while (effects && dirty);
    return tree;
  }
  const app = {
    input,
    document,
    requests,
    navigation,
    links,
    render,
    panel: () => nodes(tree).find((node) => node.props?.id === 'global-search-panel'),
    filter: (key) => nodes(tree).find((node) => node.type === 'button' && node.key === key),
    change(value, effects = true) {
      input.element.props.onChange({ target: { value } });
      return render(effects);
    },
    key(key, target = input) {
      let prevented = false;
      tree.props.onKeyDown({
        key,
        target,
        nativeEvent: { isComposing: false },
        preventDefault() {
          prevented = true;
        },
      });
      render();
      if (key === 'Enter' && target === input && !prevented) app.submit();
      return tree;
    },
    submit() {
      tree.props.onSubmit({ preventDefault() {} });
      return render();
    },
    close() {
      documentListeners.get('keydown')({
        key: 'Escape',
        target: input,
        preventDefault() {},
        stopPropagation() {},
      });
      return render();
    },
    async advance(ms) {
      now += ms;
      for (const [id, timer] of [...timers]) {
        if (timer.at > now) continue;
        timers.delete(id);
        void timer.callback();
      }
      await settle();
      return render();
    },
    async respond(index, data, status = 200) {
      requests[index].resolve({
        ok: status < 400,
        status,
        headers: { get: () => 'application/json' },
        json: async () => data,
      });
      await settle();
      return render();
    },
    async load(data = payload()) {
      app.change('produkt');
      await app.advance(180);
      await app.respond(requests.length - 1, data);
    },
    destroy() {
      for (const current of slots) current.cleanup?.();
    },
  };
  render();
  return app;
}

test('Enter and either arrow reopen a closed search without activating hidden results', async () => {
  for (const key of ['Enter', 'ArrowUp', 'ArrowDown']) {
    const app = harness();
    try {
      await app.load();
      app.close();
      assert.equal(app.panel().props.hidden, true);
      app.key(key);
      assert.equal(app.panel().props.hidden, false, key + ' should reopen the panel');
      assert.deepEqual(app.navigation, []);
      assert.equal(app.document.activeElement, app.input);
    } finally {
      app.destroy();
    }
  }
});

test('moving the pointer over a result preserves the target activated by Enter', async () => {
  const app = harness();
  try {
    await app.load();
    app.links()[1].element.props.onMouseMove?.();
    app.render();
    app.submit();
    assert.deepEqual(app.navigation, [result('PRO-1').url]);
  } finally {
    app.destroy();
  }
});

test('the selected result type survives another query and a response without that group', async () => {
  const app = harness();
  try {
    await app.load();
    app.filter('space_tasks').props.onClick();
    app.render();
    assert.equal(app.filter('space_tasks').props['aria-pressed'], true);
    app.change('dokument');
    assert.equal(app.filter('space_tasks').props['aria-pressed'], true);
    await app.advance(180);
    await app.respond(
      1,
      payload(['DOC-1'], {
        query: 'dokument',
        groups: [
          {
            key: 'office-documents',
            label: 'Dokumenty',
            icon: 'file-text',
            has_more: false,
            results: [result('DOC-1')],
          },
        ],
      }),
    );
    assert.equal(app.filter('space_tasks').props['aria-pressed'], true);
    assert.equal(app.links().length, 0);
    assert.equal(app.filter('office-documents').props['aria-pressed'], false);
    app.filter('office-documents').props.onClick();
    app.render();
    assert.equal(app.links()[0].element.props.href, result('DOC-1').url);
  } finally {
    app.destroy();
  }
});

test('editing the query clears old results and selection before effects and the debounce', async () => {
  const app = harness();
  try {
    await app.load();
    app.key('ArrowDown');
    app.key('ArrowDown', app.links()[0]);
    app.change('nowe', false);
    assert.equal(app.links().length, 0, 'no previous result may remain actionable before effects');
    app.submit();
    assert.deepEqual(app.navigation, []);
    await app.advance(179);
    assert.equal(app.requests.length, 1);
    await app.advance(1);
    assert.equal(app.requests.length, 2);
    await app.respond(1, payload(['NEW-1', 'NEW-2'], { query: 'nowe' }));
    app.submit();
    assert.deepEqual(app.navigation, [result('NEW-1').url]);
  } finally {
    app.destroy();
  }
});

test('a changed query aborts its request and an older response cannot replace new results', async () => {
  const app = harness();
  try {
    app.change('stare');
    await app.advance(180);
    const original = app.requests[0];
    assert.equal(
      new URL(original.url, 'http://localhost').searchParams.get('url'),
      base + 'global-search/?q=stare',
    );
    assert.equal(original.credentials, 'same-origin');
    assert.equal(original.headers['X-CSRFToken'], 'search-csrf');
    app.change('nowe');
    assert.equal(original.signal.aborted, true);
    await app.advance(180);
    await app.respond(1, payload(['NEW-1'], { query: 'nowe' }));
    await app.respond(0, payload(['OLD-1'], { query: 'stare' }));
    assert.deepEqual(
      app.links().map((link) => link.element.props.href),
      [result('NEW-1').url],
    );
  } finally {
    app.destroy();
  }
});

test('closing search cancels both scheduled and in-flight requests and ignores late results', async () => {
  const app = harness();
  try {
    app.change('produkt');
    app.close();
    await app.advance(180);
    assert.equal(app.requests.length, 0);
    app.key('ArrowDown');
    await app.advance(180);
    assert.equal(app.requests.length, 1);
    app.close();
    assert.equal(app.requests[0].signal.aborted, true);
    await app.respond(0, payload());
    assert.equal(app.panel().props.hidden, true);
    assert.equal(app.links().length, 0);
    app.key('ArrowDown');
    await app.advance(180);
    await app.respond(1, payload(['NEW-1']));
    assert.equal(app.links()[0].element.props.href, result('NEW-1').url);
  } finally {
    app.destroy();
  }
});

test('ArrowUp from the first real result link returns focus to the input and clears selection', async () => {
  const app = harness();
  try {
    await app.load();
    assert.equal(app.input.element.props.role, 'combobox');
    assert.equal(app.input.element.props['aria-haspopup'], 'dialog');
    assert.equal(app.panel().props.role, 'dialog');
    app.key('ArrowDown');
    const first = app.links()[0];
    assert.equal(app.document.activeElement, first);
    assert.ok(first.element.props.className.split(' ').includes('is-active'));
    app.key('ArrowUp', first);
    assert.equal(app.document.activeElement, app.input);
    assert.ok(
      app.links().every((link) => !link.element.props.className.split(' ').includes('is-active')),
    );
  } finally {
    app.destroy();
  }
});

test('a failed search offers a retry that retrieves results for the same query', async () => {
  const app = harness();
  try {
    app.change('produkt');
    await app.advance(180);
    const tree = await app.respond(0, { error: 'offline' }, 503);
    const error = nodes(tree).find((node) => typeof node.props?.retry === 'function');
    assert.ok(error, 'failed search should offer a retry');
    assert.equal(app.links().length, 0);
    error.props.retry();
    app.render();
    await app.advance(180);
    assert.equal(app.requests[1].url, app.requests[0].url);
    await app.respond(1, payload(['PRO-3']));
    assert.equal(app.links()[0].element.props.href, result('PRO-3').url);
  } finally {
    app.destroy();
  }
});

test('Enter on the clear button keeps its native action after Escape closes search', async () => {
  const app = harness();
  try {
    await app.load();
    app.close();
    assert.equal(app.panel().props.hidden, true);
    assert.equal(app.input.element.props.value, 'produkt');
    app.key('Tab');
    const tree = app.render();
    const clear = nodes(tree).find(
      (node) => node.type === 'button' && node.props['aria-label'] === 'Wyczyść wyszukiwanie',
    );
    assert.equal(clear.props.hidden, false);
    const target = { closest: () => null };
    app.document.activeElement = target;
    let prevented = false;
    tree.props.onKeyDown({
      key: 'Enter',
      target,
      nativeEvent: { isComposing: false },
      preventDefault() {
        prevented = true;
      },
    });
    app.render();
    assert.equal(prevented, false, 'Enter must retain the clear button’s native click');
    assert.equal(app.panel().props.hidden, true);
    clear.props.onClick();
    app.render();
    assert.equal(app.input.element.props.value, '');
    assert.equal(app.panel().props.hidden, false);
    assert.equal(app.document.activeElement, app.input);
    await app.advance(0);
    assert.equal(
      new URL(app.requests[1].url, 'http://localhost').searchParams.get('url'),
      base + 'global-search/?recent=1',
    );
    const recent = payload(['REC-1'], { query: '', recent: true });
    recent.groups[0].key = 'recent';
    await app.respond(1, recent);
    assert.equal(app.links()[0].element.props.href, result('REC-1').url);
    assert.deepEqual(app.navigation, []);
  } finally {
    app.destroy();
  }
});
