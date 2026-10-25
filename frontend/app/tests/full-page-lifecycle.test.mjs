import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import vm from 'node:vm';

// Full-screen editors omit the navigation shell and use the existing layout lifecycle.
const layout = await readFile(new URL('../../../static/js/layout.js', import.meta.url), 'utf8');

function classes(...initial) {
  const values = new Set(initial);
  return {
    add: (...names) => names.forEach((name) => values.add(name)),
    remove: (...names) => names.forEach((name) => values.delete(name)),
    contains: (name) => values.has(name),
    toggle(name, force) {
      const active = force ?? !values.has(name);
      if (active) values.add(name);
      else values.delete(name);
      return active;
    },
  };
}

function editor() {
  const timers = new Map(),
    root = { classList: classes('office-editor-window', 'app-shell-booting', 'app-page-loading') },
    body = { classList: classes('app-page-loading'), dataset: {} },
    overlay = {
      attributes: { 'aria-hidden': 'true' },
      setAttribute(name, value) {
        this.attributes[name] = value;
      },
    };
  const document = Object.assign(new EventTarget(), {
    documentElement: root,
    body,
    visibilityState: 'visible',
    querySelector: (selector) => (selector === '[data-app-full-navigation]' ? {} : null),
    querySelectorAll: () => [],
    getElementById: (id) => (id === 'app-loading-overlay' ? overlay : null),
  });
  const window = Object.assign(new EventTarget(), {
    location: new URL('http://ancore.test/office/1/editor/'),
    history: { state: {} },
    matchMedia: () => ({ matches: false }),
    setTimeout(callback) {
      const id = Symbol();
      timers.set(id, callback);
      return id;
    },
    clearTimeout: (id) => timers.delete(id),
  });
  vm.runInNewContext(layout, { document, window, URL });
  return {
    document,
    window,
    root,
    body,
    overlay,
    flushTimers() {
      const callbacks = [...timers.values()];
      timers.clear();
      callbacks.forEach((callback) => callback());
    },
  };
}

function assertReady(app) {
  assert.equal(app.root.classList.contains('office-editor-window'), true);
  assert.equal(app.root.classList.contains('app-shell-booting'), false);
  assert.equal(app.root.classList.contains('app-page-loading'), false);
  assert.equal(app.body.classList.contains('app-page-loading'), false);
  assert.equal(app.overlay.attributes['aria-hidden'], 'true');
  assert.equal(app.window.AncoreApp.canNavigatePartially('/office/'), false);
}

test('a reloaded full-screen editor clears the blocking loader on pageshow', () => {
  const app = editor();
  assert.equal(app.root.classList.contains('app-shell-booting'), false);
  assert.equal(app.overlay.attributes['aria-hidden'], 'false');
  app.window.dispatchEvent(new Event('pageshow'));
  assertReady(app);
});

test('the load fallback also clears the loader without a navigation shell', () => {
  const app = editor();
  app.window.dispatchEvent(new Event('load'));
  app.flushTimers();
  assertReady(app);
});

test('canceling navigation from a full-screen editor restores its controls', () => {
  const app = editor();
  app.window.dispatchEvent(new Event('pageshow'));
  app.window.addEventListener('beforeunload', (event) => event.preventDefault());
  app.window.dispatchEvent(new Event('beforeunload', { cancelable: true }));
  assert.equal(app.overlay.attributes['aria-hidden'], 'false');
  app.flushTimers();
  assertReady(app);
});
