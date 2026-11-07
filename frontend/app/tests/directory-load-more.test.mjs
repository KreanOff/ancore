import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import vm from 'node:vm';
import { transform } from 'esbuild';
import ts from 'typescript';

// Exercise the production loaders with state and transport controlled at their boundaries.
async function callbacks(file, names) {
  const source = ts.createSourceFile(
    file,
    await readFile(new URL('../src/' + file, import.meta.url), 'utf8'),
    ts.ScriptTarget.Latest,
    true,
    ts.ScriptKind.TSX,
  );
  const found = new Map();
  function visit(node) {
    if (ts.isFunctionDeclaration(node) && names.includes(node.name?.text))
      found.set(node.name.text, node.getText());
    ts.forEachChild(node, visit);
  }
  visit(source);
  assert.equal(found.size, names.length);
  return (
    await transform([...found.values()].join('\n') + `\nexport { ${names.join(', ')} };`, {
      loader: 'tsx',
      format: 'cjs',
    })
  ).code;
}
const documents = await callbacks('documents/DirectoryPage.tsx', ['load', 'query', 'url']);
const resources = await callbacks('resources/App.tsx', [
  'load',
  'change',
  'loadHistory',
  'operate',
]);
const workLog = await callbacks('tasks/TaskPage.tsx', ['loadWorkLog']);
function deferred() {
  let resolve, reject;
  const promise = new Promise((done, fail) => {
    resolve = done;
    reject = fail;
  });
  return { promise, resolve, reject };
}
function execute(code, context) {
  const module = { exports: {} };
  Object.assign(context, {
    module,
    exports: module.exports,
    AbortController,
    URL,
    URLSearchParams,
    Set,
    encodeURIComponent,
    errorMessage: (error) => error.message,
  });
  vm.runInNewContext(code, context);
  return module.exports;
}
function states(context, names) {
  for (const name of names) {
    const key = name[0].toLowerCase() + name.slice(1);
    context['set' + name] = (value) =>
      (context[key] = typeof value === 'function' ? value(context[key]) : value);
  }
}
function documentHarness() {
  const requests = [],
    locations = [];
  const context = {
    props: { initial: { api_url: '/api/page/' }, csrfToken: 'csrf' },
    data: {
      query: '',
      base_url: '/documents/',
      rows: [{ id: 'a' }],
      filter_params: { owner: 'me' },
      sort: 'name',
      display: 'list',
      libraries: true,
    },
    actions: { busy: false },
    selected: new Set(['a']),
    search: '',
    desired: { current: '' },
    read: { current: undefined },
    serial: { current: 0 },
    retry: { current: '' },
    reading: false,
    pageRequest: async (...args) => {
      requests.push(args);
      return context.response;
    },
    setPageLocation: (...args) => locations.push(args),
  };
  states(context, ['Data', 'Selected', 'Reading', 'Error', 'MoreError', 'Search']);
  return { context, requests, locations, ...execute(documents, context) };
}
function resourceHarness() {
  const requests = [],
    locations = [];
  const context = {
    data: {
      api_url: '/api/resources/',
      query: 'druk',
      results: [{ id: 1 }],
      list_url: '/resources/?q=druk&status=available&limit=40',
    },
    selected: new Set([1]),
    queryRef: { current: 'druk' },
    operation: { current: false },
    listing: { current: undefined },
    life: { current: new AbortController() },
    retry: { current: undefined },
    editor: undefined,
    actionDialog: undefined,
    busy: false,
    csrfToken: 'csrf',
    window: {
      location: {
        origin: 'https://app.test',
        href: 'https://app.test/resources/1/?status=available',
      },
    },
    request: async (...args) => {
      requests.push(args);
      return context.response;
    },
    setPageLocation: (...args) => locations.push(args),
  };
  states(context, [
    'Data',
    'Selected',
    'Busy',
    'Error',
    'MoreError',
    'Query',
    'Detail',
    'HistoryError',
  ]);
  return { context, requests, locations, ...execute(resources, context) };
}
function logHarness() {
  const requests = [],
    locations = [];
  const data = {
    item: { title: 'Unsaved local title' },
    work_log: {
      next: '/tasks/T-1/?tab=work-log&work_log_limit=40',
      count: 50,
      results: [{ id: 1 }],
    },
  };
  const context = {
    data,
    latest: { current: data },
    initial: { type: 'space-task', api_url: '/api/page/' },
    csrfToken: 'csrf',
    logRequest: { current: undefined },
    actionPending: { current: false },
    auto: { pending: false },
    life: { current: new AbortController() },
    workLogURL: { current: '/tasks/T-1/' },
    logSelected: new Set([1]),
    location: { href: 'https://app.test/tasks/T-1/?tab=comments' },
    pageRequest: async (...args) => {
      requests.push(args);
      return context.response;
    },
    setPageLocation: (...args) => locations.push(args),
  };
  states(context, ['Data', 'LogLoading', 'LogError', 'LogSelected']);
  return { context, requests, locations, ...execute(workLog, context) };
}

test('documents accept cumulative results without duplication and retain selected rows', async () => {
  const app = documentHarness();
  app.context.response = {
    type: 'document-directory',
    data: { query: '', rows: [{ id: 'a' }, { id: 'b' }] },
  };
  await app.load('/documents/?owner=me&limit=40', true);
  assert.deepEqual(
    app.context.data.rows.map((row) => row.id),
    ['a', 'b'],
  );
  assert.deepEqual([...app.context.selected], ['a']);
  assert.deepEqual(app.locations, [['/documents/?owner=me&limit=40', false]]);
  assert.equal(app.context.read.current, undefined);
});
test('documents reset the visible window on query/filter changes and ignore an older response', async () => {
  const app = documentHarness(),
    waiting = deferred();
  app.context.pageRequest = async () => waiting.promise;
  const pending = app.load('/documents/?limit=40', true);
  app.query('nowy');
  waiting.resolve({ type: 'document-directory', data: { query: '', rows: [{ id: 'stale' }] } });
  await pending;
  assert.deepEqual(app.context.data.rows, [{ id: 'a' }]);
  const target = new URL(app.url({ sort: '-created' }), 'https://app.test');
  assert.equal(target.searchParams.get('q'), 'nowy');
  assert.equal(target.searchParams.get('owner'), 'me');
  assert.equal(target.searchParams.has('limit'), false);
  assert.equal(app.locations.length, 0);
});
test('documents preserve visible rows on failure and retry the same window', async () => {
  const app = documentHarness();
  app.context.pageRequest = async () => {
    throw new Error('GET 503');
  };
  await app.load('/documents/?limit=40', true);
  assert.equal(app.context.moreError, 'GET 503');
  assert.deepEqual([...app.context.selected], ['a']);
  app.context.pageRequest = async () => ({
    type: 'document-directory',
    data: { query: '', rows: [{ id: 'a' }, { id: 'b' }] },
  });
  await app.load('/documents/?limit=40', true);
  assert.equal(app.context.moreError, '');
  assert.equal(app.context.data.rows.length, 2);
});
test('documents do not start overlapping load-more requests or publish data after unmount', async () => {
  const app = documentHarness(),
    waiting = deferred();
  app.context.pageRequest = async (...args) => {
    app.requests.push(args);
    return waiting.promise;
  };
  const pending = app.load('/documents/?limit=40', true);
  await app.load('/documents/?limit=40', true);
  assert.equal(app.requests.length, 1);
  app.context.read.current.abort();
  waiting.resolve({ type: 'document-directory', data: { query: '', rows: [] } });
  await pending;
  assert.equal(app.context.data.rows.length, 1);
});
test('resources replace the cumulative window, retain selection and keep filter URL', async () => {
  const app = resourceHarness();
  app.context.response = {
    query: 'druk',
    results: [{ id: 1 }, { id: 2 }],
    list_url: '/resources/?q=druk&status=available&limit=60',
  };
  await app.load(app.context.response.list_url, true);
  assert.deepEqual(
    app.context.data.results.map((row) => row.id),
    [1, 2],
  );
  assert.deepEqual([...app.context.selected], [1]);
  assert.equal(app.requests[0][0], '/api/resources/?q=druk&status=available&limit=60');
  assert.deepEqual(app.locations, [[app.context.response.list_url]]);
});
test('resources reset the window when sorting or filtering without dropping other filters', async () => {
  const app = resourceHarness(),
    waiting = deferred();
  app.context.request = async (...args) => {
    app.requests.push(args);
    return waiting.promise;
  };
  app.change('sort', '-name');
  const query = new URL(app.requests[0][0], 'https://app.test').searchParams;
  assert.equal(query.get('q'), 'druk');
  assert.equal(query.get('status'), 'available');
  assert.equal(query.get('sort'), '-name');
  assert.equal(query.has('limit'), false);
  waiting.resolve({
    results: [],
    query: 'druk',
    list_url: '/resources/?q=druk&status=available&sort=-name',
  });
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(app.context.selected.size, 0);
});
test('resources reject stale load-more after a newer query and allow retry after an error', async () => {
  const app = resourceHarness(),
    waiting = deferred();
  app.context.request = async () => waiting.promise;
  const pending = app.load('/resources/?q=druk&limit=60', true);
  app.context.queryRef.current = 'nowa';
  waiting.resolve({ query: 'druk', results: [{ id: 2 }] });
  await pending;
  assert.equal(app.context.data.results[0].id, 1);
  app.context.queryRef.current = 'druk';
  app.context.request = async () => {
    throw new Error('GET 503');
  };
  await app.load('/resources/?q=druk&limit=60', true);
  assert.equal(app.context.moreError, 'GET 503');
  assert.equal(app.context.busy, false);
  assert.equal(app.context.listing.current, undefined);
});
test('resource history accepts page and API next URLs, replaces the prefix and preserves scope URL', async () => {
  for (const path of ['/resources/1/', '/api/resources/1/overview/']) {
    const app = resourceHarness();
    app.context.detail = {
      resource: { id: 1 },
      history: [{ id: 1 }],
      history_next: path + '?history_limit=40',
      history_end: 20,
    };
    app.context.response = {
      ...app.context.detail,
      history: [{ id: 1 }, { id: 2 }],
      history_end: 40,
    };
    await app.loadHistory();
    assert.equal(app.requests[0][0], '/api/resources/1/overview/?history_limit=40');
    assert.equal(app.context.detail.history.length, 2);
    assert.equal(app.locations[0][0].searchParams.get('status'), 'available');
    assert.equal(app.locations[0][0].searchParams.get('history_limit'), '40');
  }
});
test('resource history failure keeps the existing entries and releases retry lock', async () => {
  const app = resourceHarness();
  app.context.detail = {
    resource: { id: 1 },
    history: [{ id: 1 }],
    history_next: '/resources/1/?history_limit=40',
  };
  app.context.request = async () => {
    throw new Error('GET 503');
  };
  await app.loadHistory();
  assert.equal(app.context.historyError, 'GET 503');
  assert.equal(app.context.detail.history.length, 1);
  assert.equal(app.context.operation.current, false);
});
test('worklog loading updates only its window and preserves task draft, selected rows and active tab', async () => {
  const app = logHarness();
  app.context.response = {
    type: 'space-task',
    data: {
      item: { title: 'Stale server title' },
      work_log: { results: [{ id: 1 }, { id: 2 }], next: '', count: 2 },
    },
  };
  await app.loadWorkLog();
  assert.equal(app.context.data.item.title, 'Unsaved local title');
  assert.equal(app.context.data.work_log.results.length, 2);
  assert.deepEqual([...app.context.logSelected], [1]);
  assert.equal(app.context.workLogURL.current, '/tasks/T-1/?tab=work-log&work_log_limit=40');
  assert.equal(app.locations[0][0].searchParams.get('tab'), 'comments');
});
test('worklog drops an older request after a task refresh and prevents duplicate reads', async () => {
  const app = logHarness(),
    waiting = deferred();
  app.context.pageRequest = async (...args) => {
    app.requests.push(args);
    return waiting.promise;
  };
  const pending = app.loadWorkLog();
  await app.loadWorkLog();
  assert.equal(app.requests.length, 1);
  app.context.latest.current = { work_log: { results: [] } };
  waiting.resolve({ type: 'space-task', data: { work_log: { results: [{ id: 2 }] } } });
  await pending;
  assert.equal(app.context.data.work_log.results[0].id, 1);
  assert.equal(app.locations.length, 0);
});
test('worklog errors leave data intact and release the request for retry', async () => {
  const app = logHarness();
  app.context.pageRequest = async () => {
    throw new Error('GET 503');
  };
  await app.loadWorkLog();
  assert.equal(app.context.logError, 'GET 503');
  assert.equal(app.context.data.work_log.results.length, 1);
  assert.equal(app.context.logRequest.current, undefined);
});

test('resource bulk actions retain the existing 100-record limit after expanding the list', async () => {
  const app = resourceHarness();
  await app.operate(
    'status',
    Array.from({ length: 101 }, (_, id) => ({ id })),
  );
  assert.equal(app.requests.length, 0);
  assert.equal(app.context.operation.current, false);
});
