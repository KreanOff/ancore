import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

const bundle = await build({
  entryPoints: [new URL('../src/documents/useActions.ts', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  external: ['react', 'react-dom'],
  plugins: [
    {
      name: 'document-boundaries',
      setup(build) {
        build.onResolve({ filter: /\/shared\/page$/ }, () => ({
          path: 'test:page',
          external: true,
        }));
        build.onResolve({ filter: /\/shared\/useDirtyGuard$/ }, () => ({
          path: 'test:guard',
          external: true,
        }));
      },
    },
  ],
  write: false,
});
const require = createRequire(import.meta.url);

function harness() {
  class Element {}
  const body = new Element();
  const document = { activeElement: body };
  const requests = [],
    slots = [],
    effects = [];
  let cursor = 0;
  const react = {
    useState(initial) {
      const index = cursor++;
      if (!(index in slots)) slots[index] = initial;
      return [
        slots[index],
        (next) => {
          slots[index] = next;
        },
      ];
    },
    useRef(initial) {
      return (slots[cursor++] ||= { current: initial });
    },
    useEffect(callback) {
      const index = cursor++;
      if (!(index in slots)) {
        slots[index] = true;
        effects.push(callback());
      }
    },
  };
  const module = { exports: {} };
  vm.runInNewContext(bundle.outputFiles[0].text, {
    module,
    exports: module.exports,
    AbortController,
    HTMLElement: Element,
    document,
    require(name) {
      if (name === 'react') return react;
      if (name === 'react-dom') return { flushSync: (callback) => callback() };
      if (name === 'test:guard') return { useDirtyGuard() {} };
      if (name === 'test:page')
        return {
          pageRequest: () => new Promise((resolve, reject) => requests.push({ resolve, reject })),
          setPageLocation() {},
        };
      return require(name);
    },
  });
  return {
    body,
    document,
    requests,
    Element,
    render() {
      cursor = 0;
      return module.exports.useActions(
        { initial: { api_url: '/api/v1/pages/' }, csrfToken: 'csrf' },
        null,
      );
    },
    unmount() {
      effects.forEach((cleanup) => cleanup?.());
    },
  };
}

test('document dialogs remember the trigger before loading blurs it and across preview/edit switches', async () => {
  const app = harness();
  const trigger = new app.Element();
  app.document.activeElement = trigger;
  const opening = app.render().open('/documents/new/');
  assert.equal(app.render().busy, true);
  app.document.activeElement = app.body;
  app.requests[0].resolve({ type: 'document-form', data: { action: '/documents/new/' } });
  await opening;
  assert.equal(app.render().returnFocus, trigger);

  app.document.activeElement = new app.Element();
  const switching = app.render().open('/documents/1/edit/');
  app.requests[1].resolve({ type: 'document-form', data: { action: '/documents/1/edit/' } });
  await switching;
  assert.equal(app.render().returnFocus, trigger);

  app.render().close();
  const nextTrigger = new app.Element();
  app.document.activeElement = nextTrigger;
  const reopening = app.render().open('/documents/upload/');
  app.requests[2].resolve({ type: 'document-form', data: { action: '/documents/upload/' } });
  await reopening;
  assert.equal(app.render().returnFocus, nextTrigger);
  app.unmount();
});
