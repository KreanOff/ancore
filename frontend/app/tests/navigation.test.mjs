import assert from 'node:assert/strict';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

// Exercise the real navigation controller; rendering and HTTP have separate contracts.
const bundle = await build({
  stdin: {
    contents: `export * from './src/shell/navigation';
      export { acquireInert } from './src/shared/inert';`,
    resolveDir: new URL('..', import.meta.url).pathname,
  },
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
    rendered = [],
    notifications = [],
    timers = new Map();
  let now = 0;
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
  document.activeElement = document.body;
  const content = {
    attributes: new Map(),
    setAttribute(name, value) {
      this.attributes.set(name, value);
    },
    removeAttribute(name) {
      this.attributes.delete(name);
    },
  };
  const page = { inert: false, isConnected: true, contains: (element) => element === focused };
  const focused = {
    isConnected: true,
    focusCount: 0,
    closest: () => (page.inert ? page : null),
    focus() {
      this.focusCount++;
      document.activeElement = this;
    },
  };
  let hidden = true;
  const skeleton = {
    shown: 0,
    get hidden() {
      return hidden;
    },
    set hidden(value) {
      if (!value) this.shown++;
      hidden = value;
    },
  };
  document.querySelector = (selector) =>
    selector === '.main-content' ? content : selector === '.page-container' ? page : null;
  document.getElementById = (id) => (id === 'app-content-loading' ? skeleton : null);
  const window = Object.assign(new EventTarget(), {
    scrollTo() {},
    showNotification: (...args) => notifications.push(args),
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
  const envelope = { shell: data, page: { title: 'Spaces' }, csrf_token: 'token' };
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
    setTimeout(callback, delay) {
      const id = Symbol();
      timers.set(id, { callback, at: now + delay });
      return id;
    },
    clearTimeout: (id) => timers.delete(id),
    performance: { getEntriesByType: () => [] },
    requestAnimationFrame(callback) {
      callback();
    },
    http: async (url, _token, signal) => {
      requests.push(url);
      return reply ? reply(url, signal) : envelope;
    },
  };
  vm.runInNewContext(bundle.outputFiles[0].text, context);
  const dispose = module.exports.startNavigation(data, 'token', () => {});
  return {
    window,
    document,
    assigned,
    requests,
    rendered,
    notifications,
    content,
    page,
    focused,
    skeleton,
    envelope,
    acquireInert: module.exports.acquireInert,
    advance(milliseconds) {
      now += milliseconds;
      for (const [id, timer] of timers) {
        if (timer.at <= now) {
          timers.delete(id);
          timer.callback();
        }
      }
    },
    dispose,
    capturePosition: module.exports.capturePosition,
  };
}

test('returning to document lists and grids restores their own scroll containers', async () => {
  const app = controller();
  const table = {
    scrollTop: 520,
    scrollLeft: 75,
    scrollTo({ top, left }) {
      this.scrollTop = top;
      this.scrollLeft = left;
    },
  };
  const grid = {
    scrollTop: 340,
    scrollLeft: 0,
    scrollTo({ top, left }) {
      this.scrollTop = top;
      this.scrollLeft = left;
    },
  };
  app.document.querySelectorAll = (selector) =>
    selector === '.documents-table-scroll'
      ? [table]
      : selector === '.documents-grid-scroll'
        ? [grid]
        : [];
  const position = app.capturePosition();
  table.scrollTop = table.scrollLeft = grid.scrollTop = 0;
  try {
    await app.window.AncoreApp.navigate('/workplaces/workspace-a/office/', {
      restorePosition: position,
    });
    assert.equal(table.scrollTop, 520);
    assert.equal(table.scrollLeft, 75);
    assert.equal(grid.scrollTop, 340);
  } finally {
    app.dispose();
  }
});

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

function deferred() {
  let resolve, reject;
  const promise = new Promise((accept, fail) => {
    resolve = accept;
    reject = fail;
  });
  return { promise, resolve, reject };
}

test('a fast navigation renders without showing a loader or locking the previous page', async () => {
  const app = controller();
  try {
    const navigation = app.window.AncoreApp.navigate('/workplaces/workspace-a/teams/');
    assert.equal(app.content.attributes.get('aria-busy'), 'true');
    assert.equal(app.skeleton.hidden, true);
    assert.equal(app.page.inert, false);
    assert.equal(await navigation, true);
    app.advance(1000);
    assert.equal(app.rendered.length, 1);
    assert.equal(app.skeleton.shown, 0);
    assert.equal(app.page.inert, false);
    assert.equal(app.content.attributes.has('aria-busy'), false);
  } finally {
    app.dispose();
  }
});

test('a delayed failure restores the existing screen and its focus after hiding the loader', async () => {
  const response = deferred();
  const app = controller(() => response.promise);
  app.document.activeElement = app.focused;
  try {
    const navigation = app.window.AncoreApp.navigate('/workplaces/workspace-a/teams/');
    app.advance(179);
    assert.equal(app.skeleton.hidden, true);
    assert.equal(app.page.inert, false);
    app.advance(1);
    assert.equal(app.skeleton.hidden, false);
    assert.equal(app.page.inert, true);
    app.document.activeElement = app.document.body;
    response.reject(new Error('Nie udało się wczytać ekranu.'));
    assert.equal(await navigation, false);
    assert.equal(app.skeleton.hidden, true);
    assert.equal(app.page.inert, false);
    assert.equal(app.content.attributes.has('aria-busy'), false);
    assert.equal(app.document.activeElement, app.focused);
    assert.equal(app.focused.focusCount, 1);
    assert.equal(app.rendered.length, 0);
    assert.equal(app.notifications.length, 1);
  } finally {
    app.dispose();
  }
});

test('replacing an active request keeps one loader lock until the latest request finishes', async () => {
  const first = deferred(),
    second = deferred(),
    signals = [];
  const app = controller((_url, signal) => {
    signals.push(signal);
    return signals.length === 1 ? first.promise : second.promise;
  });
  app.document.activeElement = app.focused;
  try {
    const previous = app.window.AncoreApp.navigate('/workplaces/workspace-a/teams/');
    app.advance(180);
    app.document.activeElement = app.document.body;
    const current = app.window.AncoreApp.navigate('/workplaces/workspace-a/calendar/');
    assert.equal(signals[0].aborted, true);
    app.advance(180);
    first.resolve(app.envelope);
    assert.equal(await previous, true);
    assert.equal(app.skeleton.hidden, false);
    assert.equal(app.skeleton.shown, 1);
    assert.equal(app.page.inert, true);
    assert.equal(app.content.attributes.get('aria-busy'), 'true');
    assert.equal(app.rendered.length, 0);
    second.reject(new Error('Brak połączenia.'));
    assert.equal(await current, false);
    assert.equal(app.skeleton.hidden, true);
    assert.equal(app.page.inert, false);
    assert.equal(app.content.attributes.has('aria-busy'), false);
    assert.equal(app.document.activeElement, app.focused);
    assert.equal(app.focused.focusCount, 1);
  } finally {
    app.dispose();
  }
});

for (const closeModalFirst of [true, false]) {
  test(`the loader and an existing modal release their shared lock (${closeModalFirst ? 'modal' : 'loader'} first)`, async () => {
    const response = deferred();
    const app = controller(() => response.promise);
    const closeModal = app.acquireInert([app.page]);
    try {
      const navigation = app.window.AncoreApp.navigate('/workplaces/workspace-a/teams/');
      app.advance(180);
      if (closeModalFirst) closeModal();
      assert.equal(app.page.inert, true);
      response.reject(new Error('Brak połączenia.'));
      assert.equal(await navigation, false);
      assert.equal(app.page.inert, !closeModalFirst);
      assert.equal(app.skeleton.hidden, true);
      closeModal();
      assert.equal(app.page.inert, false);
    } finally {
      closeModal();
      app.dispose();
    }
  });
}

test('finishing a loader preserves a page that was already inert', async () => {
  const response = deferred();
  const app = controller(() => response.promise);
  app.page.inert = true;
  try {
    const navigation = app.window.AncoreApp.navigate('/workplaces/workspace-a/teams/');
    app.advance(180);
    response.reject(new Error('Brak połączenia.'));
    assert.equal(await navigation, false);
    assert.equal(app.page.inert, true);
    assert.equal(app.skeleton.hidden, true);
    assert.equal(app.focused.focusCount, 0);
  } finally {
    app.dispose();
  }
});

for (const reason of ['detached', 'another-control', 'modal']) {
  test(`loader cleanup does not restore unavailable or superseded focus (${reason})`, async () => {
    const response = deferred();
    const app = controller(() => response.promise);
    app.document.activeElement = app.focused;
    let closeModal;
    try {
      const navigation = app.window.AncoreApp.navigate('/workplaces/workspace-a/teams/');
      app.advance(180);
      app.document.activeElement = app.document.body;
      if (reason === 'detached') app.focused.isConnected = false;
      if (reason === 'another-control') app.document.activeElement = {};
      if (reason === 'modal') closeModal = app.acquireInert([app.page]);
      response.reject(new Error('Brak połączenia.'));
      assert.equal(await navigation, false);
      assert.equal(app.focused.focusCount, 0);
      assert.equal(app.page.inert, reason === 'modal');
    } finally {
      closeModal?.();
      app.dispose();
    }
  });
}
