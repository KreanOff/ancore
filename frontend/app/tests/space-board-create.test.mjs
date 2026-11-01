import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import { transform } from 'esbuild';
import ts from 'typescript';

// Exercise the production board render and callbacks with only hooks and HTTP controlled.
const source = ts.createSourceFile(
  'DetailPage.tsx',
  await readFile(new URL('../src/spaces/DetailPage.tsx', import.meta.url), 'utf8'),
  ts.ScriptTarget.Latest,
  true,
  ts.ScriptKind.TSX,
);
const detail = source.statements.find(
  (node) => ts.isFunctionDeclaration(node) && node.name?.text === 'DetailPage',
);
assert.ok(detail, 'the production detail component must exist');
const { code } = await transform(detail.getText(), {
  loader: 'tsx',
  format: 'cjs',
  jsx: 'automatic',
});
const require = createRequire(import.meta.url);
const flush = () => new Promise((resolve) => setImmediate(resolve));

function nodes(element) {
  if (!element || typeof element !== 'object') return [];
  if (Array.isArray(element)) return element.flatMap(nodes);
  return [element, ...nodes(element.props?.children)];
}

function board(path = '/space/produkt/') {
  return {
    space: { id: 7, name: 'Produkt', url: path, template: 'kanban' },
    view: 'board',
    filters: { assignee: 'me' },
    can_edit: true,
    can_manage: false,
    active_sprint: null,
    modal: null,
    sort: { manual: false },
    columns: [
      { key: 'new', label: 'Do zrobienia', category: 'new', count: 0 },
      { key: 'review', label: 'Do sprawdzenia', category: 'in_progress', count: 1 },
    ].map((column) => ({
      ...column,
      create_item_url:
        path +
        'items/create/?view=board&assignee=me&sort=title_asc&status=review&initial_status=' +
        column.key,
    })),
    items: [{ id: 41, key: 'PRO-41', status: 'review', editable: true }],
  };
}

function harness(data = board()) {
  const states = [],
    refs = [],
    requests = [],
    locations = [],
    navigations = [],
    initial = {
      data,
      url: data.space.url + '?view=board&assignee=me&sort=title_asc',
      api_url: '/api/v1/page/',
    },
    response = {
      type: 'form',
      data: { action: data.columns[0].create_item_url, return_url: initial.url },
    },
    controls = { response, failure: null, wait: null };
  let stateIndex = 0,
    refIndex = 0;
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
    useState(value) {
      const index = stateIndex++;
      if (!(index in states)) states[index] = value;
      return [
        states[index],
        (next) => {
          states[index] = typeof next === 'function' ? next(states[index]) : next;
        },
      ];
    },
    useRef(value) {
      const index = refIndex++;
      if (!(index in refs)) refs[index] = { current: value };
      return refs[index];
    },
    useEffect() {},
    useLayoutEffect() {},
    useItemMotion: () => ({ root: { current: null } }),
    SpaceHeader: 'SpaceHeader',
    Avatar: 'Avatar',
    Icon: 'Icon',
    ItemToolbar: 'ItemToolbar',
    ItemCard: 'ItemCard',
    StatusGroup: 'StatusGroup',
    FormDialog: 'FormDialog',
    errorMessage: (error) => error.message,
    setPageLocation: (url) => locations.push(url),
    navigate: (url) => navigations.push(url),
    async pageRequest(api, url, csrfToken, signal, body) {
      requests.push({ api, url, csrfToken, signal, body });
      if (controls.wait) await controls.wait;
      if (controls.failure) throw controls.failure;
      return controls.response;
    },
  });
  function render() {
    stateIndex = 0;
    refIndex = 0;
    return nodes(module.exports.default({ initial, csrfToken: 'csrf-token' }));
  }
  const buttons = () =>
    render().filter(
      (node) => node.type === 'button' && node.props.className?.includes('work-board-create'),
    );
  return { initial, controls, requests, locations, navigations, render, buttons };
}

test('every editable board column offers creation, including empty columns', () => {
  const data = board(),
    app = harness(data),
    groups = app.render().filter((node) => node.type === 'StatusGroup');
  assert.equal(groups.length, 2);
  for (const [index, group] of groups.entries()) {
    const button = nodes(group).find(
      (node) => node.type === 'button' && node.props.className?.includes('work-board-create'),
    );
    assert.ok(button, `${data.columns[index].label} must offer creation`);
    assert.equal(button.props.type, 'button');
    assert.equal(button.props['aria-disabled'], false);
    assert.equal(button.props['aria-haspopup'], 'dialog');
    assert.equal(
      button.props['aria-label'],
      `Utwórz zadanie w statusie ${data.columns[index].label}`,
    );
    assert.ok(button.props.children.includes('Utwórz zadanie'));
  }
});

for (const path of ['/space/produkt/', '/workplaces/w_0123456789abcdefghijklmnop/space/produkt/']) {
  test(`column creation uses its exact API URL and the shared modal at ${path}`, async () => {
    const data = board(path),
      app = harness(data);
    for (const [index, column] of data.columns.entries()) {
      app.controls.response.data = {
        action: column.create_item_url,
        return_url: app.initial.url,
        form: { fields: [{ name: 'status', value: column.key }] },
      };
      app.buttons()[index].props.onClick();
      await flush();
      const request = app.requests[index];
      assert.equal(request.url, column.create_item_url);
      assert.equal(request.api, app.initial.api_url);
      assert.equal(request.csrfToken, 'csrf-token');
      assert.equal(request.body, undefined, 'opening a form must not create a task yet');
      assert.equal(request.signal.aborted, false);
      const modal = app.render().find((node) => node.type === 'FormDialog');
      assert.ok(modal);
      assert.equal(modal.props.data, app.controls.response.data);
      assert.equal(modal.props.api, app.initial.api_url);
      assert.equal(modal.props.csrfToken, 'csrf-token');
      modal.props.onClose();
      assert.equal(
        app.render().some((node) => node.type === 'FormDialog'),
        false,
      );
    }
    assert.deepEqual(app.locations, [], 'opening and cancelling retains the board URL');
    assert.deepEqual(app.navigations, []);
  });
}

test('read-only boards and columns without an authorized creation URL hide the control', () => {
  const data = board();
  assert.equal(harness({ ...data, can_edit: false }).buttons().length, 0);
  data.columns[0].create_item_url = '';
  delete data.columns[1].create_item_url;
  const app = harness({ ...data, space: { ...data.space, template: 'scrum' } });
  assert.equal(app.buttons().length, 0);
  assert.ok(
    app
      .render()
      .some((node) => node.type === 'a' && node.props.href === data.space.url + '?view=backlog'),
    'a Scrum board without an active sprint still points to its backlog',
  );
});

test('a failed form request shows an error and permits retry without changing board cards', async () => {
  const app = harness(),
    url = app.initial.data.columns[1].create_item_url;
  app.controls.failure = new Error('Brak połączenia');
  app.buttons()[1].props.onClick();
  await flush();
  let tree = app.render();
  const alert = tree.find((node) => node.props?.role === 'alert');
  assert.ok(alert);
  assert.ok(alert.props.children.includes('Brak połączenia'));
  assert.equal(
    tree.some((node) => node.type === 'FormDialog'),
    false,
  );
  assert.deepEqual(
    tree.filter((node) => node.type === 'ItemCard').map((node) => node.props.item.id),
    [41],
  );
  assert.ok(app.buttons().every((button) => button.props['aria-disabled'] === false));
  app.controls.failure = null;
  app.buttons()[1].props.onClick();
  await flush();
  tree = app.render();
  assert.equal(
    tree.some((node) => node.props?.role === 'alert'),
    false,
  );
  assert.ok(tree.some((node) => node.type === 'FormDialog'));
  assert.deepEqual(
    app.requests.map((request) => request.url),
    [url, url],
  );
  assert.deepEqual(app.locations, []);
});

test('unexpected page responses do not open a modal and leave column creation available', async () => {
  const app = harness();
  app.controls.response = { type: 'space-detail', data: board() };
  app.buttons()[0].props.onClick();
  await flush();
  const tree = app.render();
  assert.equal(
    tree.some((node) => node.type === 'FormDialog'),
    false,
  );
  const alert = tree.find((node) => node.props?.role === 'alert');
  assert.ok(alert.props.children.includes('Nie udało się otworzyć formularza.'));
  assert.ok(app.buttons().every((button) => button.props['aria-disabled'] === false));
});

test('an in-flight form request blocks activation while keeping its trigger focusable', async () => {
  const app = harness();
  let resolve;
  app.controls.wait = new Promise((done) => (resolve = done));
  const buttons = app.buttons();
  buttons[0].props.onClick();
  assert.equal(app.requests.length, 1);
  assert.ok(app.buttons().every((button) => button.props['aria-disabled'] === true));
  assert.ok(
    app.buttons().every((button) => button.props.disabled !== true),
    'native disabling would lose the trigger focus before the modal captures it',
  );
  buttons[0].props.onClick();
  buttons[1].props.onClick();
  assert.equal(app.requests.length, 1, 'the request guard also covers stale click handlers');
  resolve();
  await flush();
  assert.ok(app.buttons().every((button) => button.props['aria-disabled'] === false));
  assert.equal(app.render().filter((node) => node.type === 'FormDialog').length, 1);
});
