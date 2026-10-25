import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

// Run the board entry point; replace only Excalidraw's surface and the DOM mount.
const bundle = await build({
  entryPoints: [new URL('../../board/board.jsx', import.meta.url).pathname],
  plugins: [
    {
      name: 'board-surface',
      setup(builder) {
        builder.onResolve({ filter: /^(@excalidraw\/excalidraw|react-dom\/client)$/ }, (args) => ({
          path: args.path,
          namespace: 'board-test',
        }));
        builder.onLoad({ filter: /.*/, namespace: 'board-test' }, (args) => ({
          contents:
            args.path === 'react-dom/client'
              ? `export const createRoot = () => ({ render: element => {
                globalThis.boardProps = element.type(element.props).props;
              } });`
              : `export const Excalidraw = () => null;
              export const MainMenu = Object.assign(() => null, {
                Item: () => null, Separator: () => null,
                DefaultItems: Object.fromEntries(['LoadScene', 'SaveAsImage', 'SearchMenu',
                  'CommandPalette', 'ClearCanvas', 'ChangeCanvasBackground', 'ToggleTheme',
                  'Help'].map(name => [name, () => null]))
              });`,
        }));
        builder.onLoad({ filter: /\.css$/ }, () => ({ contents: '', loader: 'js' }));
      },
    },
  ],
  bundle: true,
  conditions: ['production'],
  platform: 'node',
  format: 'cjs',
  write: false,
  define: { 'process.env.NODE_ENV': '"production"' },
});

function harness(readOnly) {
  const notifications = [],
    posts = [],
    timers = new Map(),
    listeners = {};
  const scene = { elements: [], appState: { viewBackgroundColor: '#fff' }, files: {} },
    config = { scene, readOnly, revision: 3, saveUrl: '/board/save/', name: 'Tablica' },
    parent = { postMessage: (value) => notifications.push(value) };
  const context = {
    require: createRequire(import.meta.url),
    module: { exports: {} },
    console,
    process,
    window: {
      addEventListener: (name, callback) => {
        listeners[name] = callback;
      },
    },
    parent,
    location: { origin: 'http://ancore.test' },
    document: {
      getElementById: (id) =>
        id === 'board-root'
          ? { dataset: { assets: '/static/vendor/board/' } }
          : { textContent: JSON.stringify(config) },
      querySelector: () => ({ value: 'token' }),
    },
    setTimeout: (callback) => {
      const id = Symbol();
      timers.set(id, callback);
      return id;
    },
    clearTimeout: (id) => timers.delete(id),
    AbortController,
    fetch: async (_url, options) => {
      posts.push(JSON.parse(options.body));
      return { ok: true, status: 200, json: async () => ({ revision: 4, saved_at: '12:00' }) };
    },
  };
  vm.runInNewContext(bundle.outputFiles[0].text, context);
  const board = context.boardProps;
  const save = board.children.props.children[0].props.onSelect;
  return { board, save, notifications, posts, timers, listeners, parent };
}

test('a read-only board announces readiness without scheduling or posting saves', async () => {
  const app = harness(true),
    state = { viewBackgroundColor: '#fff' };
  assert.equal(app.board.viewModeEnabled, true);
  app.board.onChange([], state, {});
  assert.equal(app.notifications.length, 1);
  assert.equal(app.notifications[0].type, 'status');
  assert.equal(app.notifications[0].message, 'Tablica otwarta');
  assert.equal(app.notifications[0].dirty, false);
  app.board.onChange([], state, {});
  app.board.onChange([{ id: 'new', version: 1, versionNonce: 2 }], state, {});
  await app.save();
  app.listeners.message({
    origin: 'http://ancore.test',
    source: app.parent,
    data: { source: 'ancore', type: 'save' },
  });
  let prevented = false;
  app.listeners.beforeunload({
    preventDefault: () => {
      prevented = true;
    },
  });
  assert.equal(app.notifications.length, 1);
  assert.equal(app.timers.size, 0);
  assert.equal(app.posts.length, 0);
  assert.equal(prevented, false);
});

test('an editable board still saves changes and clears its dirty status', async () => {
  const app = harness(false),
    state = { viewBackgroundColor: '#fff' };
  app.board.onChange([], state, {});
  app.board.onChange([{ id: 'new', version: 1, versionNonce: 2 }], state, {});
  assert.equal(app.notifications.at(-1).dirty, true);
  await app.save();
  assert.equal(app.posts.length, 1);
  assert.equal(app.posts[0].revision, 3);
  assert.equal(app.posts[0].scene.elements[0].id, 'new');
  assert.equal(app.notifications.at(-1).dirty, false);
  assert.match(app.notifications.at(-1).message, /Zapisano w Ancore/);
});
