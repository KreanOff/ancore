import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

const bundle = await build({
  entryPoints: [new URL('../src/shared/Dropdown.tsx', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  jsx: 'automatic',
  external: ['react', 'react/jsx-runtime'],
  write: false,
});
const require = createRequire(import.meta.url);

function mount({ role = 'dialog', items = [] } = {}) {
  const hooks = [],
    effects = [],
    frames = [],
    listeners = new Map();
  let cursor = 0;
  const useState = (initial) => {
    const index = cursor++;
    if (!(index in hooks)) hooks[index] = typeof initial === 'function' ? initial() : initial;
    return [hooks[index], (value) => (hooks[index] = value)];
  };
  const anchor = { focus() {}, closest: () => null };
  const field = {};
  const menu = {
    parentElement: { contains: (node) => node === field || node === anchor },
    querySelector: () => null,
    querySelectorAll: () => items,
  };
  const document = {
    addEventListener: (name, fn) => listeners.set(name, fn),
    removeEventListener: (name) => listeners.delete(name),
  };
  const module = { exports: {} };
  vm.runInNewContext(bundle.outputFiles[0].text, {
    module,
    exports: module.exports,
    require: (name) =>
      name === 'react'
        ? {
            ...require(name),
            useState,
            useRef: (initial) => useState(() => ({ current: initial }))[0],
            useId: () => 'dropdown',
            useLayoutEffect: (fn) => effects.push(fn),
          }
        : require(name),
    document,
    requestAnimationFrame: (fn) => frames.push(fn),
  });
  function render() {
    cursor = 0;
    const tree = module.exports.Dropdown({
      label: 'Filtry',
      trigger: 'Filtruj',
      layer: false,
      role,
    });
    const [button, panel] = tree.props.children;
    button.ref.current = anchor;
    panel.ref.current = menu;
    return { button, panel };
  }
  return {
    render,
    anchor,
    field,
    listeners,
    effects: () =>
      effects
        .splice(0)
        .map((effect) => effect())
        .filter(Boolean),
    frames: () => frames.splice(0).forEach((fn) => fn()),
  };
}

test('an inline filter closes when Tab leaves its controls, while preserving focus within it', () => {
  const app = mount();
  app.render().button.props.onClick();
  app.effects();
  assert.equal(app.render().panel.props.hidden, false);
  const cleanups = app.effects();
  app.listeners.get('focusin')({ target: app.field });
  assert.equal(app.render().panel.props.hidden, false);
  app.listeners.get('focusin')({ target: {} });
  assert.equal(app.render().panel.props.hidden, true);
  cleanups.forEach((fn) => fn());
  assert.equal(app.listeners.size, 0);
});

test('ArrowDown opens a form panel at its first visible control rather than skipping to an action', () => {
  const focused = [];
  const item = (id, visible) => ({
    getClientRects: () => (visible ? [{}] : []),
    closest: () => null,
    focus: () => focused.push(id),
  });
  const app = mount({ items: [item('hidden', false), item('search', true), item('apply', true)] });
  let prevented = false;
  app
    .render()
    .button.props.onKeyDown({
      key: 'ArrowDown',
      target: app.anchor,
      preventDefault: () => (prevented = true),
    });
  app.render();
  app.frames();
  assert.equal(prevented, true);
  assert.deepEqual(focused, ['search']);
});

test('arrow and text navigation keys in native editors are not taken over by the menu', () => {
  const app = mount();
  for (const tag of ['input', 'textarea', 'select', 'contenteditable']) {
    for (const key of ['ArrowDown', 'ArrowUp', 'Home', 'End']) {
      let prevented = false;
      app.render().panel.props.onKeyDown({
        key,
        target: {
          closest: (selector) =>
            selector.includes(tag === 'contenteditable' ? '[contenteditable]' : tag) ? {} : null,
        },
        preventDefault: () => (prevented = true),
      });
      assert.equal(prevented, false, `${tag} ${key}`);
    }
  }
});
