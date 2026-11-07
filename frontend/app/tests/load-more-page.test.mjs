import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

const bundle = await build({
  entryPoints: [new URL('../src/shared/useLoadMorePage.ts', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  external: ['react'],
  plugins: [
    {
      name: 'http-boundary',
      setup(build) {
        build.onResolve({ filter: /^\.\/page$/ }, () => ({ path: 'test:page', external: true }));
      },
    },
  ],
  write: false,
});
const require = createRequire(import.meta.url);
const plain = (value) => JSON.parse(JSON.stringify(value));
const url = '/workplaces/w_test/spaces/';
function page(count = 20, query = '') {
  return {
    type: 'space-directory',
    api_url: '/api/v1/pages/',
    url: url + '?q=' + query + '&limit=' + count,
    data: {
      results: Array.from({ length: count }, (_, id) => ({ id, name: query + id })),
      pagination: {
        count: 45,
        end: count,
        next: count < 45 ? url + '?q=' + query + '&limit=' + Math.min(45, count + 20) : '',
      },
    },
  };
}
function harness() {
  let index = 0,
    props = { initial: page(), csrfToken: 'csrf' };
  const values = [],
    effects = [],
    requests = [],
    locations = [];
  const react = {
    useState(initial) {
      const slot = index++;
      if (!(slot in values)) values[slot] = typeof initial === 'function' ? initial() : initial;
      return [
        values[slot],
        (next) => {
          values[slot] = typeof next === 'function' ? next(values[slot]) : next;
        },
      ];
    },
    useRef(initial) {
      const slot = index++;
      return (values[slot] ||= { current: initial });
    },
    useLayoutEffect(callback, deps) {
      const slot = index++,
        previous = effects[slot];
      if (!previous || deps.some((value, n) => value !== previous.deps[n])) {
        previous?.cleanup?.();
        effects[slot] = { deps, cleanup: callback() };
      }
    },
  };
  const module = { exports: {} };
  vm.runInNewContext(bundle.outputFiles[0].text, {
    module,
    exports: module.exports,
    AbortController,
    Error,
    require(name) {
      if (name === 'react') return react;
      if (name === 'test:page')
        return {
          pageRequest(...args) {
            return new Promise((resolve, reject) => requests.push({ args, resolve, reject }));
          },
          setPageLocation: (value) => locations.push(value),
        };
      return require(name);
    },
  });
  return {
    requests,
    locations,
    render(initial) {
      if (initial) props = { ...props, initial };
      index = 0;
      module.exports.useLoadMorePage(props, (data) => data.pagination.next);
      index = 0;
      return module.exports.useLoadMorePage(props, (data) => data.pagination.next);
    },
    unmount() {
      effects.forEach((effect) => effect?.cleanup?.());
    },
  };
}

test('more keeps the current prefix, takes one request per click sequence, and stops at the end', async () => {
  const app = harness();
  let view = app.render();
  const pending = view.loadMore();
  await view.loadMore();
  assert.equal(app.requests.length, 1);
  assert.equal(app.requests[0].args[1], url + '?q=&limit=40');
  assert.equal(app.render().data.results.length, 20);
  assert.equal(app.render().loading, true);
  app.requests[0].resolve(page(40));
  await pending;
  view = app.render();
  assert.deepEqual(plain(view.data.results.slice(0, 20)), page().data.results);
  assert.equal(new Set(view.data.results.map((item) => item.id)).size, 40);
  assert.equal(app.locations.at(-1), page(40).url);
  const final = view.loadMore();
  app.requests[1].resolve(page(45));
  await final;
  await app.render().loadMore();
  assert.equal(app.requests.length, 2);
  assert.equal(app.render().data.results.length, 45);
  app.unmount();
});

test('failure leaves existing rows and next URL intact; retry succeeds without duplication', async () => {
  const app = harness();
  const pending = app.render().loadMore();
  app.requests[0].reject(new Error('Brak połączenia'));
  await pending;
  const failed = app.render();
  assert.equal(failed.error, 'Brak połączenia');
  assert.equal(failed.loading, false);
  assert.equal(failed.data.results.length, 20);
  assert.equal(app.locations.length, 0);
  const retry = failed.loadMore();
  app.requests[1].resolve(page(40));
  await retry;
  assert.equal(app.render().data.results.length, 40);
  assert.equal(app.render().error, '');
  app.unmount();
});

test('changing filters cancels the old window and ignores a response that arrives afterwards', async () => {
  const app = harness();
  const pending = app.render().loadMore();
  app.render(page(20, 'nowe'));
  assert.equal(app.requests[0].args[3].aborted, true);
  app.requests[0].resolve(page(40));
  await pending;
  const current = app.render();
  assert.equal(current.data.results.length, 20);
  assert.equal(current.data.results[0].name, 'nowe0');
  assert.equal(current.loading, false);
  assert.equal(app.locations.length, 0);
  app.unmount();
});

test('unmount cancels loading and unexpected page types cannot replace the list', async () => {
  const app = harness();
  const pending = app.render().loadMore();
  app.requests[0].resolve({ ...page(40), type: 'form' });
  await pending;
  assert.equal(app.render().data.results.length, 20);
  assert.match(app.render().error, /kolejnych wyników/);
  const second = app.render().loadMore();
  app.unmount();
  assert.equal(app.requests[1].args[3].aborted, true);
  app.requests[1].resolve(page(40));
  await second;
  assert.equal(app.locations.length, 0);
});
