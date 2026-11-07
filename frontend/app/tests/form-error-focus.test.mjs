import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

const bundle = await build({
  entryPoints: [new URL('../src/forms/FormDialog.tsx', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  jsx: 'automatic',
  external: ['react', 'react/jsx-runtime', 'react-dom'],
  write: false,
});
const require = createRequire(import.meta.url);

function find(node, predicate) {
  if (Array.isArray(node)) return node.map((child) => find(child, predicate)).find(Boolean);
  if (!node?.props) return undefined;
  return predicate(node) ? node : find(node.props.children, predicate);
}

// Execute the real request/error callback and then its scheduled focus after React commits.
function harness(invalid = []) {
  const hooks = [];
  const frames = [];
  const document = { activeElement: null };
  let cursor = 0;
  let saved = 0;
  const summary = { focus: () => (document.activeElement = summary) };
  const form = { querySelectorAll: () => invalid };
  const useState = (initial) => {
    const index = cursor++;
    if (!(index in hooks)) hooks[index] = typeof initial === 'function' ? initial() : initial;
    return [hooks[index], (value) => (hooks[index] = value)];
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
            useEffect() {},
            useLayoutEffect() {},
          }
        : require(name),
    document,
    requestAnimationFrame: (callback) => frames.push(callback),
    AbortController,
    AbortSignal,
    URL,
    FormData: class {},
    location: { origin: 'https://ancore.test' },
    fetch: async () => ({
      ok: false,
      status: 503,
      headers: { get: () => 'application/json' },
      json: async () => ({ error: 'Zapis jest chwilowo niedostępny. Spróbuj ponownie.' }),
    }),
  });
  function render() {
    cursor = 0;
    const tree = module.exports.EmbeddedForm({
      data: {
        action: '/spaces/create/',
        return_url: '/spaces/',
        form: { fields: [], errors: [], bound: false, submit_label: 'Zapisz' },
      },
      api: '/api/v1/page/',
      csrfToken: 'test-csrf',
      onSaved: () => saved++,
      onStateChange() {},
    });
    tree.ref.current = form;
    const error = find(tree, (node) => node.props.role === 'alert');
    if (error) error.ref.current = summary;
    return { tree, error };
  }
  const focusable = (options = {}) => {
    const element = {
      closest: (selector) =>
        selector === '[hidden], [inert]'
          ? options.hidden
          : options.button
            ? { querySelector: () => options.button }
            : null,
      matches: () => !!options.disabled,
      getClientRects: () => (options.invisible ? [] : [{}]),
      focus: () => (document.activeElement = element),
    };
    return element;
  };
  return {
    document,
    summary,
    focusable,
    async failSave() {
      const { tree } = render();
      await tree.props.onSubmit({ preventDefault() {} });
      const result = render();
      frames.forEach((callback) => callback());
      assert.equal(saved, 0);
      assert.equal(result.tree.props['aria-busy'], false);
      return result;
    },
  };
}

test('a failed save without a field error moves focus to the visible error message', async () => {
  const app = harness();
  const { error } = await app.failSave();
  assert.equal(error.props.tabIndex, -1);
  assert.equal(error.props.children, 'Zapis jest chwilowo niedostępny. Spróbuj ponownie.');
  assert.equal(app.document.activeElement, app.summary);
});

test('focus skips hidden and disabled errors and reaches the custom select button', async () => {
  const invalid = [];
  const app = harness(invalid);
  const button = app.focusable();
  invalid.push(
    app.focusable({ hidden: {} }),
    app.focusable({ disabled: true }),
    app.focusable({ invisible: true }),
    app.focusable({ button }),
  );
  await app.failSave();
  assert.equal(app.document.activeElement, button);
});

test('an invalid checkbox is directly focusable and errors in a hidden section fall back to the summary', async () => {
  const invalid = [];
  const app = harness(invalid);
  const checkbox = app.focusable();
  invalid.push(checkbox);
  await app.failSave();
  assert.equal(app.document.activeElement, checkbox);
  invalid.splice(0, 1, app.focusable({ hidden: {} }));
  await app.failSave();
  assert.equal(app.document.activeElement, app.summary);
});
