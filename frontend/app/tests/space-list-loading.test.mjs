import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import { transform } from 'esbuild';
import ts from 'typescript';

// Exercise production callbacks with only component state and HTTP controlled.
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
  assert.equal(found.size, names.length, 'all requested source callbacks must exist');
  return (
    await transform([...found.values()].join('\n') + `\nexport { ${names.join(', ')} };`, {
      loader: 'tsx',
      format: 'cjs',
      jsx: 'automatic',
    })
  ).code;
}

const detailCallbacks = await callbacks('spaces/DetailPage.tsx', ['loadMore', 'act']);
const detailRender = await callbacks('spaces/DetailPage.tsx', ['DetailPage']);
const queryCallbacks = await callbacks('spaces/ItemToolbar.tsx', ['changeQuery']);
const require = createRequire(import.meta.url);
const path = '/workplaces/w_0123456789abcdefghijklmnop/space/produkt/';
const initialUrl = path + '?view=list&assignee=me&sort=title_asc';
const backlogUrl = path + '?view=backlog&assignee=me&sort=title_asc';
const timelineUrl = path + '?view=timeline&assignee=me&sort=title_asc';

function timelineData(loaded = 20, count = 45) {
  return {
    ...data(loaded, count),
    view: 'timeline',
    items: data(loaded, count).items.slice(0, loaded),
    timeline: {
      count,
      loaded_count: loaded,
      more_url:
        loaded < count ? timelineUrl + '&timeline_limit=' + Math.min(loaded + 20, count) : '',
    },
  };
}

function timelineColumn(snapshot) {
  return { ...snapshot.timeline, key: 'timeline', label: 'Oś czasu' };
}

function execute(code, context) {
  const module = { exports: {} };
  vm.runInNewContext(code, {
    module,
    exports: module.exports,
    require,
    AbortController,
    Error,
    FormData,
    Set,
    URL,
    location: { origin: 'http://localhost' },
    errorMessage: (error) => error.message,
    ...context,
  });
  return module.exports;
}

function deferred() {
  let resolve;
  const promise = new Promise((done) => (resolve = done));
  return { promise, resolve };
}

function data(loaded = 20, count = 45) {
  return {
    space: { id: 7, url: path },
    view: 'list',
    filters: { assignee: 'me' },
    columns: [
      {
        key: 'new',
        label: 'Do zrobienia',
        category: 'new',
        count,
        loaded_count: loaded,
        more_url: loaded < count ? initialUrl + '&list_limit_new=' + (loaded + 20) : '',
      },
      { key: 'review', label: 'Do sprawdzenia', count: 2, loaded_count: 2, more_url: '' },
    ],
    items: [
      ...Array.from({ length: loaded }, (_, index) => ({
        id: index + 1,
        status: 'new',
        editable: true,
      })),
      { id: 101, status: 'review', editable: true },
      { id: 102, status: 'review', editable: true },
    ],
  };
}

function backlogData(loaded = 20, sprintLoaded = 20) {
  const url = (backlogLimit, sprintLimit) =>
      backlogUrl +
      '&backlog_limit_backlog=' +
      backlogLimit +
      '&backlog_limit_sprint_5=' +
      sprintLimit,
    sprint = {
      id: 5,
      name: 'Sprint 5',
      state: 'active',
      state_label: 'Aktywny',
      visible_count: 24,
      finished_count: 3,
      loaded_count: sprintLoaded,
      more_url: sprintLoaded < 21 ? url(loaded, sprintLoaded + 20) : '',
      planning: { total: 24, finished: 3, points: 8, unestimated: 10 },
    };
  return {
    space: { id: 7, url: path, template: 'scrum' },
    view: 'backlog',
    filters: { assignee: 'me' },
    sort: { manual: true },
    columns: [],
    backlog_totals: { total: 45, finished: 0, points: 12, unestimated: 30 },
    backlog_loaded_count: loaded,
    backlog_more_url: loaded < 45 ? url(loaded + 20, sprintLoaded) : '',
    sprints: [
      sprint,
      {
        ...sprint,
        id: 6,
        name: 'Sprint 6',
        state: 'planned',
        state_label: 'Planowany',
        visible_count: 3,
        finished_count: 1,
        loaded_count: 2,
        more_url: '',
        planning: { total: 3, finished: 1, points: 2, unestimated: 1 },
      },
      { ...sprint, id: 7, name: 'Sprint 7', state: 'closed' },
    ],
    items: [
      ...Array.from({ length: loaded }, (_, index) => ({
        id: index + 1,
        sprint_id: null,
        editable: true,
      })),
      ...Array.from({ length: sprintLoaded }, (_, index) => ({
        id: index + 101,
        sprint_id: 5,
        editable: true,
      })),
      { id: 201, sprint_id: 6, editable: true },
      { id: 202, sprint_id: 6, editable: true },
    ],
  };
}

function backlogColumn(snapshot, sprintId) {
  const sprint = snapshot.sprints.find((item) => item.id === sprintId);
  return sprint
    ? {
        key: 'sprint_' + sprint.id,
        label: sprint.name,
        count: sprint.visible_count - sprint.finished_count,
        loaded_count: sprint.loaded_count,
        more_url: sprint.more_url,
      }
    : {
        key: 'backlog',
        label: 'Backlog',
        count: snapshot.backlog_totals.total,
        loaded_count: snapshot.backlog_loaded_count,
        more_url: snapshot.backlog_more_url,
      };
}

function harness(initialData = data(), url = initialUrl) {
  const requests = [],
    locations = [],
    context = {
      initial: { api_url: '/api/v1/page/', url, data: initialData },
      csrfToken: 'token',
      data: initialData,
      currentUrl: { current: url },
      listScroll: { current: null },
      life: { current: new AbortController() },
      pending: { current: false },
      selected: new Set([1, 101]),
      notice: '',
      error: '',
      listError: null,
      loadingStatus: '',
      busy: false,
      nextData: data(40),
      responseType: 'space-detail',
      fail: false,
      motion: { root: { current: { scrollTop: 360 } }, capture() {}, prepareDrop() {} },
      setPageLocation: (url) => locations.push(url),
      pageRequest: async (api, url, token, signal, body) => {
        requests.push({ api, url, token, signal, body });
        if (context.wait) await context.wait;
        if (context.fail) throw context.failure || new Error('Brak połączenia');
        return { type: context.responseType, url, data: context.nextData };
      },
    };
  for (const name of [
    'Busy',
    'LoadingStatus',
    'ListError',
    'Data',
    'Selected',
    'Notice',
    'Error',
    'Dragged',
  ]) {
    const key = name[0].toLowerCase() + name.slice(1);
    context['set' + name] = (value) => {
      context[key] = typeof value === 'function' ? value(context[key]) : value;
    };
  }
  return { context, requests, locations, ...execute(detailCallbacks, context) };
}

test('timeline loads 20, 40, then the remaining tasks with an accurate completion announcement', async () => {
  const app = harness(timelineData(), timelineUrl);
  for (const loaded of [40, 45]) {
    app.context.nextData = timelineData(loaded);
    await app.loadMore(timelineColumn(app.context.data));
    assert.equal(app.context.data.items.length, loaded);
    assert.equal(app.context.notice, `Oś czasu: wczytano ${loaded} z 45 zadań.`);
    assert.equal(new Set(app.context.data.items.map((item) => item.id)).size, loaded);
    assert.equal(app.context.currentUrl.current, timelineUrl + '&timeline_limit=' + loaded);
  }
  await app.loadMore(timelineColumn(app.context.data));
  assert.equal(app.requests.length, 2);
});

test('a failed timeline load preserves rows and URL, then retries the same batch', async () => {
  const previous = timelineData(),
    app = harness(previous, timelineUrl),
    column = timelineColumn(previous);
  app.context.fail = true;
  await app.loadMore(column);
  assert.equal(app.context.data, previous);
  assert.equal(app.context.currentUrl.current, timelineUrl);
  assert.equal(app.context.listError.key, 'timeline');
  app.context.fail = false;
  app.context.nextData = timelineData(40);
  await app.loadMore(column);
  assert.deepEqual(
    app.requests.map((request) => request.url),
    [column.more_url, column.more_url],
  );
  assert.equal(app.context.listError, null);
  assert.equal(app.context.data.items.length, 40);
});

test('loading a status preserves its existing rows, full total and other status windows', async () => {
  const app = harness(),
    before = app.context.data.items.map((item) => item.id),
    column = app.context.data.columns[0];
  await app.loadMore(column);
  assert.equal(app.requests.length, 1);
  assert.equal(app.requests[0].url, column.more_url);
  assert.equal(app.requests[0].body, undefined);
  assert.equal(app.context.data.columns[0].loaded_count, 40);
  assert.equal(app.context.data.columns[0].count, 45);
  assert.deepEqual(app.context.data.columns[1], data().columns[1]);
  const ids = app.context.data.items.map((item) => item.id);
  assert.equal(new Set(ids).size, ids.length);
  assert.ok(before.every((id) => ids.includes(id)));
  assert.deepEqual([...app.context.selected], [1, 101]);
  assert.equal(app.context.currentUrl.current, column.more_url);
  assert.equal(app.context.listScroll.current, 360);
  assert.deepEqual(app.locations, [column.more_url]);
  assert.equal(app.context.pending.current, false);
  assert.equal(app.context.busy, false);
});

test('the final partial batch consumes only the remaining tasks and cannot load again', async () => {
  const app = harness(data(20, 21));
  app.context.nextData = data(21, 21);
  await app.loadMore(app.context.data.columns[0]);
  assert.equal(app.context.data.columns[0].loaded_count, 21);
  assert.equal(app.context.data.columns[0].count, 21);
  assert.equal(app.context.data.items.filter((item) => item.status === 'new').length, 21);
  assert.equal(app.context.data.columns[0].more_url, '');
  await app.loadMore(app.context.data.columns[0]);
  assert.equal(app.requests.length, 1);
});

test('double clicks and mutations cannot overlap an in-flight load', async () => {
  const app = harness(),
    request = deferred(),
    column = app.context.data.columns[0];
  app.context.wait = request.promise;
  const first = app.loadMore(column);
  assert.equal(app.context.busy, true);
  assert.equal(app.context.loadingStatus, column.key);
  await app.loadMore(column);
  await app.act(path + 'tasks/PRO-1/action/', { action: 'status', status: 'review' });
  assert.equal(app.requests.length, 1);
  request.resolve();
  await first;
  assert.equal(app.context.pending.current, false);
  assert.equal(app.context.busy, false);
});

test('failed loading keeps the rows, selection and URL available for the same retry', async () => {
  const app = harness(),
    previous = app.context.data,
    column = previous.columns[0];
  app.context.fail = true;
  await app.loadMore(column);
  assert.equal(app.context.data, previous);
  assert.deepEqual([...app.context.selected], [1, 101]);
  assert.equal(app.context.currentUrl.current, initialUrl);
  assert.deepEqual(app.locations, []);
  assert.ok(app.context.listError);
  assert.equal(app.context.pending.current, false);
  assert.equal(app.context.busy, false);
  app.context.fail = false;
  await app.loadMore(column);
  assert.deepEqual(
    app.requests.map((request) => request.url),
    [column.more_url, column.more_url],
  );
  assert.equal(app.context.data.columns[0].loaded_count, 40);
  assert.equal(app.context.currentUrl.current, column.more_url);
  assert.deepEqual([...app.context.selected], [1, 101]);
  assert.equal(Boolean(app.context.listError), false);
});

test('a request timeout reports a Polish error and permits retry without losing loaded tasks', async () => {
  const app = harness(),
    previous = app.context.data,
    column = previous.columns[0];
  app.context.fail = true;
  app.context.failure = Object.assign(new Error('signal timed out'), { name: 'TimeoutError' });
  await app.loadMore(column);
  assert.equal(app.context.listError.key, column.key);
  assert.equal(app.context.listError.message, 'Serwer nie odpowiedział na czas. Spróbuj ponownie.');
  assert.equal(app.context.data, previous);
  assert.deepEqual([...app.context.selected], [1, 101]);
  assert.equal(app.context.currentUrl.current, initialUrl);
  assert.deepEqual(app.locations, []);
  assert.equal(app.context.pending.current, false);
  assert.equal(app.context.busy, false);
  assert.equal(app.context.loadingStatus, '');
  app.context.fail = false;
  await app.loadMore(column);
  assert.deepEqual(
    app.requests.map((request) => request.url),
    [column.more_url, column.more_url],
  );
  assert.equal(app.context.data.columns[0].loaded_count, 40);
  assert.equal(app.context.listError, null);
});

test('a response from another page type does not replace the task list', async () => {
  const app = harness(),
    previous = app.context.data;
  app.context.responseType = 'form';
  await app.loadMore(previous.columns[0]);
  assert.equal(app.context.data, previous);
  assert.equal(app.context.currentUrl.current, initialUrl);
  assert.deepEqual(app.locations, []);
  assert.ok(app.context.listError);
});

for (const invalid of [{ view: 'board' }, { view: 'backlog' }, { space: { id: 8 } }]) {
  test(`a response with another ${Object.keys(invalid)[0]} preserves the current list`, async () => {
    const app = harness(),
      previous = app.context.data;
    Object.assign(app.context.nextData, invalid);
    await app.loadMore(previous.columns[0]);
    assert.equal(app.context.data, previous);
    assert.equal(app.context.currentUrl.current, initialUrl);
    assert.deepEqual(app.locations, []);
    assert.ok(app.context.listError);
  });
}

test('loading retains read-only selections and drops only tasks absent from the refreshed list', async () => {
  const app = harness();
  app.context.selected = new Set([1, 2, 101]);
  app.context.nextData.items = app.context.nextData.items.filter((item) => item.id !== 2);
  app.context.nextData.items.find((item) => item.id === 101).editable = false;
  await app.loadMore(app.context.data.columns[0]);
  assert.deepEqual([...app.context.selected], [1, 101]);
});

for (const fail of [false, true]) {
  test(`leaving the page ignores a late ${fail ? 'failed' : 'successful'} load`, async () => {
    const app = harness(),
      previous = app.context.data,
      request = deferred();
    app.context.wait = request.promise;
    app.context.fail = fail;
    const loading = app.loadMore(previous.columns[0]);
    app.context.life.current.abort();
    request.resolve();
    await loading;
    assert.equal(app.requests[0].signal.aborted, true);
    assert.equal(app.context.data, previous);
    assert.equal(app.context.currentUrl.current, initialUrl);
    assert.deepEqual(app.locations, []);
    assert.deepEqual([...app.context.selected], [1, 101]);
    assert.equal(Boolean(app.context.listError), false);
  });
}

test('a task action refreshes the expanded URL instead of resetting the status to twenty', async () => {
  const app = harness(),
    column = app.context.data.columns[0];
  await app.loadMore(column);
  const actionUrl = path + 'tasks/PRO-1/action/';
  await app.act(actionUrl, { action: 'status', status: 'review' });
  assert.equal(app.requests.length, 3);
  assert.equal(app.requests[1].url, actionUrl);
  assert.equal(app.requests[1].body.get('action'), 'status');
  assert.equal(app.requests[2].url, column.more_url);
  assert.equal(app.requests[2].body, undefined);
  assert.equal(app.context.data.columns[0].loaded_count, 40);
});

test('a successful action refresh clears an earlier loading error without retrying its failed URL', async () => {
  const app = harness(),
    column = app.context.data.columns[0];
  app.context.fail = true;
  await app.loadMore(column);
  assert.equal(app.context.listError.key, column.key);
  assert.equal(app.context.currentUrl.current, initialUrl);
  app.context.fail = false;
  app.context.nextData = data();
  const actionUrl = path + 'tasks/PRO-1/action/';
  await app.act(actionUrl, { action: 'status', status: 'review' });
  assert.deepEqual(
    app.requests.map((request) => request.url),
    [column.more_url, actionUrl, initialUrl],
  );
  assert.equal(app.context.data, app.context.nextData);
  assert.equal(app.context.listError, null);
  assert.equal(app.context.error, '');
  assert.equal(app.context.busy, false);
});

test('backlog and sprint loading expands only its group and retains the expanded URL for actions', async () => {
  const previous = backlogData(),
    app = harness(previous, backlogUrl),
    backlog = backlogColumn(previous);
  app.context.nextData = backlogData(40);
  await app.loadMore(backlog);
  assert.equal(app.requests[0].url, backlog.more_url);
  assert.equal(app.requests[0].body, undefined);
  assert.equal(app.context.data.backlog_loaded_count, 40);
  assert.equal(app.context.data.backlog_totals.total, 45);
  assert.deepEqual(
    app.context.data.sprints.map(({ more_url, ...sprint }) => sprint),
    previous.sprints.map(({ more_url, ...sprint }) => sprint),
  );
  assert.deepEqual(
    app.context.data.items.filter((item) => item.sprint_id !== null),
    previous.items.filter((item) => item.sprint_id !== null),
  );
  assert.ok(
    previous.items.every((item) => app.context.data.items.some(({ id }) => id === item.id)),
  );
  assert.deepEqual([...app.context.selected], [1, 101]);
  assert.equal(app.context.notice, 'Backlog: wczytano 40 z 45 zadań.');
  assert.equal(app.context.listScroll.current, 360);

  const sprint = backlogColumn(app.context.data, 5);
  app.context.nextData = backlogData(40, 21);
  await app.loadMore(sprint);
  assert.equal(app.requests[1].url, sprint.more_url);
  assert.equal(
    new URL(sprint.more_url, 'http://localhost').searchParams.get('backlog_limit_backlog'),
    '40',
  );
  assert.equal(app.context.data.backlog_loaded_count, 40);
  assert.equal(app.context.data.sprints[0].loaded_count, 21);
  assert.deepEqual(app.context.data.sprints[1], previous.sprints[1]);
  assert.equal(app.context.notice, 'Sprint 5: wczytano 21 z 21 zadań.');
  assert.deepEqual([...app.context.selected], [1, 101]);
  assert.equal(
    new Set(app.context.data.items.map(({ id }) => id)).size,
    app.context.data.items.length,
  );
  assert.equal(app.context.currentUrl.current, sprint.more_url);
  assert.deepEqual(app.locations, [backlog.more_url, sprint.more_url]);
  await app.loadMore(backlogColumn(app.context.data, 5));
  assert.equal(app.requests.length, 2, 'a completed sprint cannot request another batch');

  await app.act(path + 'tasks/PRO-1/action/', { action: 'status', status: 'review' });
  assert.equal(app.requests.length, 4);
  assert.equal(app.requests[3].url, sprint.more_url);
  assert.equal(app.context.data.backlog_loaded_count, 40);
  assert.equal(app.context.data.sprints[0].loaded_count, 21);
});

test('failed sprint loading keeps the backlog and selection intact for retry', async () => {
  const previous = backlogData(40),
    app = harness(previous, backlogUrl + '&backlog_limit_backlog=40'),
    sprint = backlogColumn(previous, 5),
    previousUrl = app.context.currentUrl.current;
  app.context.fail = true;
  await app.loadMore(sprint);
  assert.equal(app.context.data, previous);
  assert.deepEqual([...app.context.selected], [1, 101]);
  assert.equal(app.context.currentUrl.current, previousUrl);
  assert.deepEqual(app.locations, []);
  assert.equal(app.context.listError.key, 'sprint_5');
  assert.equal(app.context.pending.current, false);
  assert.equal(app.context.busy, false);
  app.context.fail = false;
  app.context.nextData = backlogData(40, 21);
  await app.loadMore(sprint);
  assert.deepEqual(
    app.requests.map(({ url }) => url),
    [sprint.more_url, sprint.more_url],
  );
  assert.equal(app.context.currentUrl.current, sprint.more_url);
  assert.equal(app.context.data.backlog_loaded_count, 40);
  assert.equal(app.context.listError, null);
});

for (const invalid of ['list', 'space', 'type']) {
  test(`a ${invalid} response cannot replace the current backlog`, async () => {
    const previous = backlogData(),
      app = harness(previous, backlogUrl);
    app.context.nextData = backlogData(40);
    if (invalid === 'list') app.context.nextData.view = 'list';
    if (invalid === 'space') app.context.nextData.space.id = 8;
    if (invalid === 'type') app.context.responseType = 'form';
    await app.loadMore(backlogColumn(previous));
    assert.equal(app.context.data, previous);
    assert.equal(app.context.currentUrl.current, backlogUrl);
    assert.deepEqual(app.locations, []);
    assert.equal(app.context.listError.key, 'backlog');
  });
}

for (const view of ['list', 'backlog', 'timeline']) {
  for (const values of [{ priority: 'high' }, { sort: 'title_desc' }, { status: '' }]) {
    test(`changing ${Object.keys(values)[0]} in ${view} resets all group windows and retains the scoped context`, () => {
      const navigations = [],
        { changeQuery } = execute(queryCallbacks, { navigate: (url) => navigations.push(url) });
      changeQuery(
        (view === 'list' ? initialUrl : view === 'backlog' ? backlogUrl : timelineUrl) +
          '&status=new&page=3&list_limit_new=60&list_limit_review=40&backlog_limit_backlog=60&backlog_limit_sprint_5=40&timeline_limit=60&other=keep',
        values,
      );
      assert.equal(navigations.length, 1);
      const target = new URL(navigations[0], 'http://localhost');
      assert.equal(target.pathname, path);
      assert.equal(target.searchParams.get('view'), view);
      assert.equal(target.searchParams.get('assignee'), 'me');
      assert.equal(target.searchParams.get('other'), 'keep');
      assert.equal(target.searchParams.has('page'), false);
      assert.equal(target.searchParams.has('timeline_limit'), false);
      assert.equal(
        [...target.searchParams.keys()].some(
          (key) => key.startsWith('list_limit_') || key.startsWith('backlog_limit_'),
        ),
        false,
      );
      for (const [key, value] of Object.entries(values))
        assert.equal(target.searchParams.get(key), value || null);
    });
  }
}

function nodes(element) {
  if (!element || typeof element !== 'object') return [];
  if (Array.isArray(element)) return element.flatMap(nodes);
  return [element, ...nodes(element.props?.children)];
}

function renderDetail(initialData, url = initialUrl) {
  const { DetailPage } = execute(detailRender, {
    useState: (initial) => [initial, () => {}],
    useRef: (initial) => ({ current: initial }),
    useEffect() {},
    useLayoutEffect() {},
    useItemMotion: () => ({ root: { current: null } }),
    SpaceHeader: 'SpaceHeader',
    Avatar: 'Avatar',
    Icon: 'Icon',
    ItemToolbar: 'ItemToolbar',
    Timeline: 'Timeline',
    StatusGroup: 'StatusGroup',
    ItemRow: 'ItemRow',
    EmptyState: 'EmptyState',
    Pagination: 'Pagination',
    dateLabel: (value) => value || '',
  });
  return DetailPage({ initial: { data: initialData, url }, csrfToken: 'token' });
}

test('timeline reuses the list control and blocks loading while dates are being saved', () => {
  const tree = nodes(renderDetail(timelineData(20, 21), timelineUrl)),
    timeline = tree.find((node) => node.type === 'Timeline');
  const more = (locked) =>
    nodes(timeline.props.moreControl(locked)).find((node) => node.type === 'button');
  assert.equal(more(false).props['aria-label'], 'Pokaż więcej: Oś czasu (20 / 21)');
  assert.equal(more(false).props['aria-disabled'], false);
  assert.equal(more(true).props['aria-disabled'], true);
  more(true).props.onClick();
  const complete = nodes(renderDetail(timelineData(21, 21), timelineUrl)).find(
    (node) => node.type === 'Timeline',
  );
  assert.equal(
    nodes(complete.props.moreControl(false)).find((node) => node.type === 'button').props[
      'aria-label'
    ],
    'Wszystkie zadania: Oś czasu (21 / 21)',
  );
});

test('list groups show the full total, a 20 / 21 loading control and no global pagination', () => {
  const tree = nodes(renderDetail(data(20, 21))),
    groups = tree.filter((node) => node.type === 'StatusGroup'),
    more = tree.filter(
      (node) => node.type === 'button' && node.props.className?.includes('work-list-more'),
    );
  assert.deepEqual(
    groups.map((group) => group.props.count),
    [21, 2],
  );
  assert.equal(more.length, 1, 'the completed small group needs no loading control');
  assert.equal(more[0].props['aria-label'], 'Pokaż więcej: Do zrobienia (20 / 21)');
  assert.equal(more[0].props['aria-disabled'], false);
  assert.equal(
    tree.some((node) => node.type === 'Pagination'),
    false,
  );
});

test('the final loading control remains focusable with a complete total after the last batch', () => {
  const tree = nodes(renderDetail(data(21, 21))),
    more = tree.find(
      (node) => node.type === 'button' && node.props.className?.includes('work-list-more'),
    );
  assert.ok(more);
  assert.equal(more.props['aria-label'], 'Wszystkie zadania: Do zrobienia (21 / 21)');
  assert.equal(more.props['aria-disabled'], true);
  assert.notEqual(
    more.props.disabled,
    true,
    'the focused button must not disappear or become unfocusable',
  );
  more.props.onClick();
});

test('backlog and open sprints show complete counts and separate loading controls without pagination', () => {
  const tree = nodes(renderDetail(backlogData(), backlogUrl)),
    groups = tree.filter((node) => node.type === 'StatusGroup'),
    more = tree.filter(
      (node) => node.type === 'button' && node.props.className?.includes('work-list-more'),
    );
  assert.deepEqual(
    groups.map(({ props }) => [props.label, props.count]),
    [
      ['Sprint 5', 21],
      ['Sprint 6', 2],
      ['Backlog', 45],
    ],
  );
  assert.deepEqual(
    more.map(({ props }) => props['aria-label']),
    ['Pokaż więcej: Sprint 5 (20 / 21)', 'Pokaż więcej: Backlog (20 / 45)'],
  );
  assert.ok(more.every(({ props }) => props['aria-disabled'] === false));
  assert.equal(
    tree.some((node) => node.type === 'Pagination'),
    false,
  );
});

test('completed backlog and sprint controls stay focusable with full totals', () => {
  const tree = nodes(renderDetail(backlogData(45, 21), backlogUrl)),
    more = tree.filter(
      (node) => node.type === 'button' && node.props.className?.includes('work-list-more'),
    );
  assert.deepEqual(
    more.map(({ props }) => props['aria-label']),
    ['Wszystkie zadania: Sprint 5 (21 / 21)', 'Wszystkie zadania: Backlog (45 / 45)'],
  );
  for (const { props } of more) {
    assert.equal(props['aria-disabled'], true);
    assert.notEqual(props.disabled, true);
    props.onClick();
  }
});
