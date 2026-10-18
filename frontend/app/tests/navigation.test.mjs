import assert from 'node:assert/strict';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

// Exercise the real navigation controller; rendering and HTTP have separate contracts.
const bundle = await build({
  entryPoints: [new URL('../src/shell/navigation.ts', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  write: false,
  plugins: [
    {
      name: 'navigation-boundaries',
      setup(build) {
        build.onResolve({ filter: /^(react-dom|\.\.\/shared\/api)$/ }, ({ path }) => ({
          path,
          namespace: 'boundary',
        }));
        build.onLoad({ filter: /.*/, namespace: 'boundary' }, ({ path }) => ({
          contents:
            path === 'react-dom'
              ? 'export const flushSync = callback => callback();'
              : `export const request = (...args) => globalThis.http(...args);
             export class ApiError extends Error {}
             export const errorMessage = error => error.message;`,
        }));
      },
    },
  ],
});

function controller(reply) {
  const assigned = [],
    requests = [],
    rendered = [];
  const location = new URL('https://ancore.test/workplaces/workspace-a/spaces/');
  location.assign = (url) => assigned.push(url);
  const classes = { remove() {}, toggle() {} };
  const document = Object.assign(new EventTarget(), {
    querySelector: () => null,
    querySelectorAll: () => [],
    getElementById: () => null,
    documentElement: { classList: classes },
    body: { classList: classes },
    referrer: '',
  });
  const window = Object.assign(new EventTarget(), {
    scrollTo() {},
    AncoreReactRuntime: {
      preparePage: async () => {},
      renderPage: (envelope) => rendered.push(envelope),
    },
  });
  const history = {
    state: {},
    replaceState(state, _, url) {
      this.state = state;
      location.href = url;
    },
    pushState(state, _, url) {
      this.replaceState(state, _, url);
    },
  };
  const data = {
    account_id: '1',
    workplace_id: '1',
    build_id: 'build',
    mode: 'workspace',
    navigation_url: '/workplaces/workspace-a/api/v1/navigation/',
  };
  const module = { exports: {} };
  const context = {
    module,
    exports: module.exports,
    window,
    document,
    history,
    location,
    URL,
    AbortController,
    CustomEvent,
    HTMLFormElement: class {},
    scrollX: 0,
    scrollY: 0,
    setTimeout,
    clearTimeout,
    performance: { getEntriesByType: () => [] },
    requestAnimationFrame() {},
    http: async (url) => {
      requests.push(url);
      return reply ? reply(url) : { shell: data, page: { title: 'Spaces' }, csrf_token: 'token' };
    },
  };
  vm.runInNewContext(bundle.outputFiles[0].text, context);
  const dispose = module.exports.startNavigation(data, 'token', () => {});
  return { window, document, assigned, requests, rendered, dispose };
}

test('same Workspace stays in the current document', async () => {
  const app = controller();
  try {
    assert.equal(
      await app.window.AncoreApp.navigate('/workplaces/workspace-a/spaces/?q=task'),
      true,
    );
    assert.equal(app.requests.length, 1);
    assert.equal(app.rendered.length, 1);
    assert.equal(app.assigned.length, 0);
  } finally {
    app.dispose();
  }
});

test('another Workspace opens directly after pending edits finish saving', async () => {
  const app = controller();
  let finish;
  const saved = new Promise((resolve) => {
    finish = resolve;
  });
  app.document.addEventListener('ancore:before-navigate', (event) => event.detail.waitUntil(saved));
  try {
    const destination = '/workplaces/workspace-b/space/product/tasks/PRO-1/?tab=history#comment';
    const navigation = app.window.AncoreApp.navigate(destination);
    assert.equal(app.assigned.length, 0);
    finish(true);
    assert.equal(await navigation, true);
    assert.deepEqual(app.assigned, ['https://ancore.test' + destination]);
    assert.equal(app.requests.length, 0);
  } finally {
    app.dispose();
  }
});

test('failed autosave blocks leaving for another Workspace', async () => {
  const app = controller();
  app.document.addEventListener('ancore:before-navigate', (event) =>
    event.detail.waitUntil(Promise.resolve(false)),
  );
  try {
    assert.equal(await app.window.AncoreApp.navigate('/workplaces/workspace-b/spaces/'), false);
    assert.equal(app.assigned.length, 0);
    assert.equal(app.requests.length, 0);
  } finally {
    app.dispose();
  }
});

test('cancelled navigation does not switch Workspace', async () => {
  const app = controller();
  app.document.addEventListener('ancore:before-navigate', (event) => event.preventDefault());
  try {
    assert.equal(await app.window.AncoreApp.navigate('/workplaces/workspace-b/spaces/'), false);
    assert.equal(app.assigned.length, 0);
  } finally {
    app.dispose();
  }
});

test('redirects to another Workspace never reuse the original Workspace API', async () => {
  const app = controller(() => ({ redirect: '/workplaces/workspace-b/spaces/?q=task' }));
  try {
    assert.equal(await app.window.AncoreApp.navigate('/workplaces/workspace-a/spaces/'), true);
    assert.equal(app.requests.length, 1);
    assert.deepEqual(app.assigned, ['https://ancore.test/workplaces/workspace-b/spaces/?q=task']);
  } finally {
    app.dispose();
  }
});
