import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import { build, transform } from 'esbuild';
import ts from 'typescript';

// Execute TaskPage's real action callback with only autosave and HTTP controlled.
const bundle = await build({
  stdin: {
    contents: `import React from 'react';
      import { renderToStaticMarkup } from 'react-dom/server';
      import TaskPage from './src/tasks/TaskPage';
      import CommentComposer from './src/tasks/CommentComposer';
      export function capture(props) {
        renderToStaticMarkup(React.createElement(TaskPage, props));
        return { composer: globalThis.taskComposer, retryRefresh: globalThis.taskRetryRefresh };
      }
      export const renderComposer = props => renderToStaticMarkup(React.createElement(CommentComposer, props));`,
    resolveDir: new URL('..', import.meta.url).pathname,
  },
  plugins: [
    {
      name: 'task-action-boundaries',
      setup(builder) {
        builder.onLoad({ filter: /\/tasks\/TaskPage\.tsx$/ }, async (args) => ({
          contents: (await readFile(args.path, 'utf8')).replace(
            'const title = schema.fields',
            'globalThis.taskRetryRefresh = retryRefresh; const title = schema.fields',
          ),
          loader: 'tsx',
        }));
        builder.onResolve({ filter: /^\.\/(useTaskSave|CommentComposer)$/ }, (args) => {
          if (!args.importer.endsWith('/tasks/TaskPage.tsx')) return;
          return { path: args.path, namespace: 'task-action-boundary' };
        });
        builder.onLoad({ filter: /.*/, namespace: 'task-action-boundary' }, (args) => ({
          contents: args.path.endsWith('useTaskSave')
            ? `export const useTaskSave = () => ({
                save: globalThis.taskControls.save, dirty: false, pending: false,
                errors: {}, error: '', notice: '', synchronize() {}
              });`
            : `export default function Composer(props) { globalThis.taskComposer = props; return null; }`,
        }));
      },
    },
  ],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  write: false,
  define: { 'process.env.NODE_ENV': '"production"' },
});

// Exercise the actual submit function and its state setters without a browser DOM.
const composerSource = ts.createSourceFile(
  'CommentComposer.tsx',
  await readFile(new URL('../src/tasks/CommentComposer.tsx', import.meta.url), 'utf8'),
  ts.ScriptTarget.Latest,
  true,
  ts.ScriptKind.TSX,
);
let submit;
function findSubmit(node) {
  if (ts.isFunctionDeclaration(node) && node.name?.text === 'submit') submit = node.getText();
  ts.forEachChild(node, findSubmit);
}
findSubmit(composerSource);
assert.ok(submit, 'CommentComposer must expose its submit handler');
const submitBundle = await transform(`${submit}\nexport { submit };`, {
  loader: 'tsx',
  format: 'cjs',
});

function field(name) {
  return { name, id: name, label: name, type: 'text', value: '', errors: [], attrs: {} };
}
function page() {
  return {
    type: 'space-task',
    url: '/space/test/tasks/TS-1/',
    api_url: '/api/v1/page/',
    data: {
      item: { id: 1, key: 'TS-1', title: 'Zadanie' },
      form: { fields: [field('title'), field('description')], errors: [] },
      can_edit: true,
      error: '',
      tab: 'main',
      tabs: [{ key: 'main', label: 'Zadanie', icon: 'list' }],
      back_url: '/space/test/',
      statuses: [{ key: 'new', label: 'Nowe', category: 'new' }],
      status: 'new',
      comments: [],
      children: [],
      files: [],
      history: [],
      mentions: [],
      comment_draft: 'Szkic komentarza',
      attachment_limit: 10,
      attachment_max_size: 1024,
      attachment_accept: '.txt',
      created_by: null,
      work_log: { total_minutes: 0, total_label: '0 min', count: 0, pages: 1, results: [] },
      team: { can_manage: false, is_owner: true, members: [] },
    },
  };
}
function deferred() {
  let resolve, reject;
  const promise = new Promise((done, fail) => {
    resolve = done;
    reject = fail;
  });
  return { promise, resolve, reject };
}
function harness(save) {
  const initial = page(),
    posts = [],
    requests = [],
    controls = { save, failPost: false, failRefresh: false };
  const module = { exports: {} };
  const context = {
    module,
    exports: module.exports,
    require: createRequire(import.meta.url),
    taskControls: controls,
    AbortController,
    AbortSignal,
    FormData,
    URL,
    TextEncoder,
    TextDecoder,
    Buffer,
    console,
    process,
    setTimeout,
    clearTimeout,
    setImmediate,
    location: { origin: 'http://ancore.test' },
    fetch: async (_url, options) => {
      const post = options.method === 'POST';
      requests.push(options.method);
      if (post) posts.push(options.body);
      return {
        ok: post ? !controls.failPost : !controls.failRefresh,
        status: post ? (controls.failPost ? 500 : 200) : controls.failRefresh ? 503 : 200,
        headers: { get: () => 'application/json' },
        json: async () => (post ? {} : initial),
      };
    },
  };
  vm.runInNewContext(bundle.outputFiles[0].text, context);
  const { composer, retryRefresh } = module.exports.capture({ initial, csrfToken: 'token' });
  return {
    composer,
    retryRefresh,
    controls,
    posts,
    requests,
    renderComposer: module.exports.renderComposer,
    initial,
  };
}
function draft(send) {
  const module = { exports: {} };
  const context = {
    module,
    exports: module.exports,
    FormData,
    pending: false,
    text: 'Szkic komentarza',
    files: [new File(['Treść pliku'], 'notatka.txt', { type: 'text/plain' })],
    mentions: [{ user_id: 2, start: 0, end: 5 }],
    query: { value: 'osoba' },
    life: { current: true },
    send,
  };
  for (const name of ['Text', 'Files', 'Mentions', 'Query'])
    context['set' + name] = (value) => {
      context[name.toLowerCase()] = value;
    };
  vm.runInNewContext(submitBundle.code, context);
  return { state: context, submit: module.exports.submit };
}

test('a second task action cannot submit while the first awaits autosave', async () => {
  const saving = deferred(),
    app = harness(() => saving.promise);
  const first = app.composer.send({ action: 'comment', message: 'Pierwszy' });
  assert.equal(await app.composer.send({ action: 'comment', message: 'Drugi' }), false);
  assert.equal(app.posts.length, 0);
  saving.resolve(true);
  assert.equal(await first, true);
  assert.equal(app.posts.length, 1);
  assert.equal(app.posts[0].get('message'), 'Pierwszy');
});

test('failed autosave and HTTP failure preserve the comment draft and allow a retry', async () => {
  let saves = 0;
  const app = harness(async () => ++saves > 1),
    composer = draft(app.composer.send),
    attachment = composer.state.files[0],
    mentions = composer.state.mentions;
  await composer.submit();
  assert.equal(app.posts.length, 0);
  assert.equal(composer.state.text, 'Szkic komentarza');
  assert.equal(composer.state.files[0], attachment);
  assert.equal(composer.state.mentions, mentions);
  app.controls.failPost = true;
  await composer.submit();
  assert.equal(app.posts.length, 1);
  assert.equal(composer.state.text, 'Szkic komentarza');
  assert.equal(composer.state.files[0], attachment);
  assert.equal(composer.state.mentions, mentions);
  app.controls.failPost = false;
  await composer.submit();
  assert.equal(app.posts.length, 2);
  assert.equal(app.posts[1].get('message'), 'Szkic komentarza');
  assert.equal(app.posts[1].get('comment_attachments').name, 'notatka.txt');
  assert.equal(composer.state.text, '');
  assert.equal(composer.state.files.length, 0);
  assert.equal(composer.state.mentions.length, 0);
  assert.equal(composer.state.query, null);
});

test('an unexpected autosave error releases the action lock for the next attempt', async () => {
  let saves = 0;
  const app = harness(async () => {
    if (++saves === 1) throw new Error('Zapis niedostępny');
    return true;
  });
  assert.equal(await app.composer.send({ action: 'comment', message: 'Szkic' }), false);
  assert.equal(app.posts.length, 0);
  assert.equal(await app.composer.send({ action: 'comment', message: 'Szkic' }), true);
  assert.equal(app.posts.length, 1);
});

test('a committed comment clears its draft when refresh fails and retries only the read', async () => {
  const app = harness(async () => true),
    composer = draft(app.composer.send);
  app.controls.failRefresh = true;
  await composer.submit();
  assert.deepEqual(app.requests, ['POST', 'GET']);
  assert.equal(composer.state.text, '');
  assert.equal(composer.state.files.length, 0);
  assert.equal(composer.state.mentions.length, 0);
  await app.retryRefresh();
  assert.deepEqual(app.requests, ['POST', 'GET', 'GET']);
  app.controls.failRefresh = false;
  await app.retryRefresh();
  assert.deepEqual(app.requests, ['POST', 'GET', 'GET', 'GET']);
  assert.equal(app.posts.length, 1);
});

test('a pending task action disables editing and submitting the comment draft', () => {
  const app = harness(async () => true);
  const html = app.renderComposer({ data: app.initial.data, pending: true, send: () => {} });
  assert.match(html, /<textarea[^>]*disabled=""[^>]*>Szkic komentarza<\/textarea>/);
  assert.match(html, /<input[^>]*type="file"[^>]*disabled=""/);
  assert.match(html, /<button[^>]*aria-label="Wyślij komentarz"[^>]*disabled=""/);
});
