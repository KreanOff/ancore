import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

// Execute both save implementations, controlling only React, the DOM, HTTP and time.
const hook = await build({
  entryPoints: [new URL('../src/documents/useOffice.ts', import.meta.url).pathname],
  plugins: [
    {
      name: 'office-react-boundary',
      setup(builder) {
        builder.onResolve({ filter: /^react$/ }, () => ({
          path: 'react',
          namespace: 'office-test',
        }));
        builder.onLoad({ filter: /.*/, namespace: 'office-test' }, () => ({
          contents: `export const useEffect = action => globalThis.effects.push(action);
            export const useRef = current => ({ current });
            export const useState = initial => {
              const index = globalThis.states.push(initial) - 1;
              return [initial, value => { globalThis.states[index] = value; }];
            };`,
        }));
      },
    },
  ],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  write: false,
});
const adapter = await readFile(
  new URL('../../../static/js/office-suite.js', import.meta.url),
  'utf8',
);

function target(values = {}) {
  const listeners = new Map();
  return Object.assign(values, {
    addEventListener(name, action) {
      if (!listeners.has(name)) listeners.set(name, new Set());
      listeners.get(name).add(action);
    },
    removeEventListener(name, action) {
      listeners.get(name)?.delete(action);
    },
    dispatch(name) {
      for (const action of listeners.get(name) || []) action();
    },
  });
}
function deferred() {
  let resolve, reject;
  const promise = new Promise((done, fail) => {
    resolve = done;
    reject = fail;
  });
  return { promise, resolve, reject };
}
async function flush() {
  for (let index = 0; index < 60; index++) await Promise.resolve();
}
function harness(implementation, initialReceipt = 0) {
  const timers = new Map(),
    posts = [],
    effects = [],
    states = [],
    status = { textContent: '' },
    error = { hidden: true },
    message = { textContent: '' },
    retry = target({ hidden: true }),
    config = { document: { key: 'doc-key' } },
    control = {
      state: {
        key: 'doc-key',
        revision: 1,
        save_receipt: initialReceipt,
        save_error: false,
        saved_at: '12:00',
      },
      post: () => ({ pending: true }),
      get: () => control.state,
    };
  let nextId = 0,
    now = 0,
    events,
    destroyed = 0;
  const holder = { dataset: { apiUrl: '/onlyoffice/api.js' } },
    root = {
      dataset: {
        revision: '1',
        saveReceipt: String(initialReceipt),
        stateUrl: '/state/',
        saveUrl: '/save/',
        backUrl: '/documents/',
      },
      querySelector(selector) {
        return {
          '[data-suite-status]': status,
          '[data-suite-error]': error,
          '[data-suite-error-message]': message,
          '[data-suite-retry]': retry,
          '[name=csrfmiddlewaretoken]': { value: 'token' },
          '[data-api-url]': holder,
        }[selector];
      },
    },
    window = target({
      DocsAPI: {
        DocEditor: class {
          constructor(_id, value) {
            events = value.events;
          }
          destroyEditor() {
            destroyed++;
          }
        },
      },
    }),
    document = target({
      readyState: 'complete',
      querySelector: (selector) => (selector === '[data-office-suite]' ? root : null),
      getElementById: () => ({ textContent: JSON.stringify(config) }),
      createElement: () => ({ remove() {} }),
      head: { append: (script) => script.onload() },
    }),
    module = { exports: {} },
    context = {
      module,
      exports: module.exports,
      effects,
      states,
      window,
      document,
      location: { origin: 'http://ancore.test' },
      AbortController,
      AbortSignal: {
        any: (signals) => AbortSignal.any(signals),
        timeout: () => new AbortController().signal,
      },
      FormData,
      Error,
      URL,
      setTimeout(callback, delay) {
        const id = ++nextId;
        timers.set(id, { callback, at: now + delay });
        return id;
      },
      clearTimeout: (id) => timers.delete(id),
      setInterval(callback, delay) {
        const id = ++nextId;
        timers.set(id, { callback, at: now + delay, repeat: delay });
        return id;
      },
      clearInterval: (id) => timers.delete(id),
      fetch: async (_url, options) => {
        const post = options.method === 'POST';
        if (post) posts.push(options);
        const value = await (post ? control.post() : control.get());
        return {
          ok: true,
          redirected: false,
          headers: { get: () => 'application/json' },
          json: async () => value,
        };
      },
    };
  let cleanup, save;
  if (implementation === 'hook') {
    vm.runInNewContext(hook.outputFiles[0].text, context);
    const office = module.exports.useOffice(
      {
        editor_config: config,
        revision: 1,
        save_receipt: initialReceipt,
        state_url: '/state/',
        save_url: '/save/',
      },
      'token',
    );
    cleanup = effects[0]();
    save = office.save;
  } else {
    vm.runInNewContext(adapter, context);
    cleanup = () => window.dispatch('pagehide');
    save = () => retry.dispatch('click');
  }
  events.onDocumentReady();
  return {
    control,
    posts,
    timers,
    events,
    cleanup,
    save,
    window,
    get status() {
      return implementation === 'hook' ? states[0] : status.textContent;
    },
    get error() {
      return implementation === 'hook' ? states[1] : error.hidden ? '' : message.textContent;
    },
    get retry() {
      return implementation === 'hook' ? states[2] : !retry.hidden;
    },
    get destroyed() {
      return destroyed;
    },
    edit() {
      events.onDocumentStateChange({ data: true });
      events.onDocumentStateChange({ data: false });
    },
    async advance(ms) {
      const until = now + ms;
      for (;;) {
        const next = [...timers].sort((a, b) => a[1].at - b[1].at)[0];
        if (!next || next[1].at > until) break;
        const [id, timer] = next;
        now = timer.at;
        if (timer.repeat) timer.at += timer.repeat;
        else timers.delete(id);
        timer.callback();
        await flush();
      }
      now = until;
      await flush();
    },
  };
}

for (const implementation of ['hook', 'adapter']) {
  test(`${implementation}: an existing receipt cannot confirm edits made after opening`, async () => {
    const app = harness(implementation, 7);
    app.edit();
    await app.advance(4000);
    assert.doesNotMatch(app.status, /Zapisano w Ancore/);
    app.control.state.save_receipt = 8;
    await app.advance(4000);
    assert.match(app.status, /Zapisano w Ancore/);
    app.cleanup();
  });

  test(`${implementation}: moving a file cannot acknowledge a pending content save`, async () => {
    const app = harness(implementation);
    app.edit();
    await app.advance(1500);
    app.control.state.revision = 2;
    app.control.state.saved_at = '12:01';
    await app.advance(2500);
    assert.doesNotMatch(app.status, /Zapisano w Ancore/);
    await app.advance(30000);
    assert.match(app.error, /Zapis nie został jeszcze potwierdzony/);
    assert.equal(app.retry, true);
    assert.equal(app.posts.length, 1);
    app.cleanup();
  });

  test(`${implementation}: only a new content receipt releases queued edits after a move`, async () => {
    const app = harness(implementation);
    app.edit();
    await app.advance(1500);
    app.edit();
    await app.advance(1500);
    app.control.state.revision = 20;
    await app.advance(1000);
    assert.equal(app.posts.length, 1);
    app.control.state.save_receipt = 1;
    await app.advance(4000);
    assert.equal(app.posts.length, 2);
    app.control.state.save_receipt = 2;
    await app.advance(4000);
    assert.match(app.status, /Zapisano w Ancore/);
    assert.equal(app.error, '');
    app.cleanup();
  });

  test(`${implementation}: a newer edit saves after the pending revision is confirmed`, async () => {
    const app = harness(implementation);
    app.edit();
    await app.advance(1500);
    assert.equal(app.posts.length, 1);
    assert.equal(app.posts[0].headers['X-Office-Key'], 'doc-key');
    app.edit();
    app.edit();
    await app.advance(1500);
    assert.equal(app.posts.length, 1);
    app.control.state.save_receipt = 1;
    await app.advance(1000);
    assert.equal(app.posts.length, 2);
    app.control.state.save_receipt = 2;
    await app.advance(4000);
    assert.match(app.status, /Zapisano w Ancore/);
    assert.equal(app.error, '');
    await app.advance(60000);
    assert.equal(app.posts.length, 2);
    assert.equal(app.error, '');
    app.cleanup();
  });

  test(`${implementation}: an unchanged generation does not enqueue duplicate saves`, async () => {
    const app = harness(implementation);
    app.edit();
    await app.advance(1500);
    app.save();
    app.events.onDocumentStateChange({ data: false });
    await app.advance(1500);
    app.control.state.save_receipt = 1;
    await app.advance(1000);
    await app.advance(60000);
    assert.equal(app.posts.length, 1);
    assert.equal(app.error, '');
    app.cleanup();
  });

  test(`${implementation}: confirmation during an HTTP request cannot start a parallel save`, async () => {
    const response = deferred(),
      app = harness(implementation);
    app.control.post = () => response.promise;
    app.edit();
    await app.advance(1500);
    app.edit();
    await app.advance(1500);
    app.control.state.save_receipt = 1;
    await app.advance(1000);
    assert.equal(app.posts.length, 1);
    app.control.post = () => ({ pending: true });
    response.resolve({ pending: true });
    await flush();
    assert.equal(app.posts.length, 2);
    app.cleanup();
  });

  test(`${implementation}: no-new-changes still drains a newer generation without a retry loop`, async () => {
    const response = deferred(),
      app = harness(implementation);
    app.control.post = () => response.promise;
    app.edit();
    await app.advance(1500);
    app.edit();
    await app.advance(1500);
    app.control.post = () => ({ pending: false });
    response.resolve({ pending: false });
    await flush();
    assert.equal(app.posts.length, 2);
    assert.equal(app.status, 'Brak nowych zmian do zapisania');
    await app.advance(60000);
    assert.equal(app.posts.length, 2);
    assert.equal(app.error, '');
    app.cleanup();
  });

  test(`${implementation}: failed saves stop the queue and manual retry saves the latest edit`, async () => {
    const response = deferred(),
      app = harness(implementation);
    app.control.post = () => response.promise;
    app.edit();
    await app.advance(1500);
    app.edit();
    await app.advance(1500);
    response.reject(new Error('Połączenie przerwane'));
    await flush();
    assert.equal(app.error, 'Połączenie przerwane');
    assert.equal(app.retry, true);
    await app.advance(60000);
    assert.equal(app.posts.length, 1);
    app.control.post = () => ({ pending: true });
    app.save();
    await flush();
    assert.equal(app.posts.length, 2);
    app.control.state.save_receipt = 1;
    await app.advance(4000);
    assert.match(app.status, /Zapisano w Ancore/);
    app.cleanup();
  });

  test(`${implementation}: a missing confirmation leaves an explicit retry without an automatic loop`, async () => {
    const app = harness(implementation);
    app.edit();
    await app.advance(1500);
    app.edit();
    await app.advance(1500);
    app.control.state.save_error = true;
    await app.advance(60000);
    assert.equal(app.posts.length, 1);
    assert.equal(app.retry, true);
    assert.match(app.error, /Nie udało się zapisać pliku/);
    app.save();
    await flush();
    assert.equal(app.posts.length, 2);
    app.control.state.save_error = false;
    app.control.state.save_receipt = 1;
    await app.advance(4000);
    assert.match(app.status, /Zapisano w Ancore/);
    assert.equal(app.error, '');
    app.cleanup();
  });

  test(`${implementation}: a callback error is not cleared by a simultaneous revision change`, async () => {
    const app = harness(implementation);
    app.edit();
    await app.advance(1500);
    app.edit();
    await app.advance(1500);
    app.control.state.save_receipt = 1;
    app.control.state.save_error = true;
    await app.advance(1000);
    assert.match(app.error, /Nie udało się zapisać pliku/);
    assert.equal(app.posts.length, 1);
    app.control.state.save_error = false;
    await app.advance(4000);
    assert.equal(app.posts.length, 1);
    app.save();
    await flush();
    assert.equal(app.posts.length, 2);
    app.cleanup();
  });

  test(`${implementation}: a temporary state read failure preserves the queued generation`, async () => {
    const app = harness(implementation);
    app.edit();
    await app.advance(1500);
    app.edit();
    await app.advance(1500);
    app.control.get = () => {
      throw new Error('Brak połączenia');
    };
    await app.advance(1000);
    assert.match(app.error, /Brak potwierdzenia zapisu/);
    assert.equal(app.posts.length, 1);
    app.control.get = () => app.control.state;
    app.control.state.save_receipt = 1;
    await app.advance(4000);
    assert.equal(app.posts.length, 2);
    assert.equal(app.error, '');
    app.cleanup();
  });

  test(`${implementation}: an invalid session cancels queued and future saves`, async () => {
    const response = deferred(),
      app = harness(implementation);
    app.control.post = () => response.promise;
    app.edit();
    await app.advance(1500);
    app.edit();
    await app.advance(1500);
    app.control.state.key = 'replacement-key';
    await app.advance(1000);
    response.resolve({ pending: true });
    await flush();
    assert.equal(app.status, 'Sesja dokumentu zmieniła się');
    assert.equal(app.retry, false);
    app.edit();
    app.save();
    await app.advance(60000);
    assert.equal(app.posts.length, 1);
    app.cleanup();
  });

  test(`${implementation}: disposal aborts requests and removes all save timers`, async () => {
    const response = deferred(),
      app = harness(implementation);
    app.control.post = () => response.promise;
    app.edit();
    await app.advance(1500);
    app.edit();
    await app.advance(1500);
    app.cleanup();
    assert.equal(app.posts[0].signal.aborted, true);
    assert.equal(app.timers.size, 0);
    assert.equal(app.destroyed, 1);
    response.resolve({ pending: true });
    await flush();
    app.edit();
    app.save();
    await app.advance(60000);
    assert.equal(app.posts.length, 1);
    assert.equal(app.timers.size, 0);
  });

  test(`${implementation}: a delayed state response cannot revive an invalid session`, async () => {
    const response = deferred(),
      app = harness(implementation);
    app.edit();
    await app.advance(1500);
    app.edit();
    await app.advance(1500);
    app.control.get = () => response.promise;
    await app.advance(1000);
    app.control.get = () => ({ ...app.control.state, key: 'replacement-key' });
    await app.advance(4000);
    assert.equal(app.status, 'Sesja dokumentu zmieniła się');
    response.resolve({ ...app.control.state, save_receipt: 1 });
    await flush();
    assert.equal(app.status, 'Sesja dokumentu zmieniła się');
    assert.equal(app.posts.length, 1);
    app.cleanup();
  });

  test(`${implementation}: disposal also clears the confirmation timeout`, async () => {
    const app = harness(implementation);
    app.edit();
    await app.advance(1500);
    assert.equal(app.timers.size, 2);
    app.cleanup();
    await app.advance(60000);
    assert.equal(app.timers.size, 0);
    assert.equal(app.error, '');
    assert.equal(app.posts.length, 1);
  });
}
