import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

// Exercise the real table callbacks and sharing form submission with hook state isolated.
const bundle = await build({
  stdin: {
    contents: `export { Members } from './src/shared/Members';
      export { default as SharingDialog } from './src/shared/SharingDialog';
      export { default as Picker } from './src/workspaces/Picker';`,
    resolveDir: new URL('..', import.meta.url).pathname,
  },
  bundle: true,
  platform: 'node',
  format: 'cjs',
  external: ['react', 'react/jsx-runtime', 'react-dom'],
  write: false,
});
const require = createRequire(import.meta.url);
class DialogFormData extends FormData {
  constructor(form) {
    super();
    for (const [name, value] of form?.values || []) this.append(name, value);
  }
}
function harness(stateful = false) {
  const requests = [];
  const saved = [];
  const hooks = [];
  const timers = new Map();
  let cursor = 0;
  let timerId = 0;
  function useState(initial) {
    if (!stateful) return [typeof initial === 'function' ? initial() : initial, () => {}];
    const index = cursor++;
    if (!(index in hooks)) hooks[index] = typeof initial === 'function' ? initial() : initial;
    return [
      hooks[index],
      (next) => (hooks[index] = typeof next === 'function' ? next(hooks[index]) : next),
    ];
  }
  const module = { exports: {} };
  vm.runInNewContext(bundle.outputFiles[0].text, {
    module,
    exports: module.exports,
    require: (name) =>
      name === 'react'
        ? {
            ...require(name),
            useState,
            useRef: (initial) => useState(() => ({ current: initial }))[0],
            useId: () => 'test-picker',
            useEffect: () => {},
            useLayoutEffect: () => {},
          }
        : require(name),
    AbortController,
    AbortSignal,
    FormData: DialogFormData,
    URL,
    Error,
    setTimeout: (callback) => {
      timers.set(++timerId, callback);
      return timerId;
    },
    clearTimeout: (id) => timers.delete(id),
    location: { origin: 'https://ancore.test' },
    fetch: async (url, options) => {
      requests.push({ url, ...options });
      return {
        ok: true,
        headers: { get: () => 'application/json' },
        json: async () => ({ members: [], results: [], has_more: false }),
      };
    },
  });
  return {
    ...module.exports,
    requests,
    saved,
    render(name, props) {
      cursor = 0;
      return module.exports[name](props);
    },
    async flushTimers() {
      const callbacks = [...timers.values()];
      timers.clear();
      for (const callback of callbacks) await callback();
    },
  };
}
function nodes(element) {
  if (!element || typeof element !== 'object') return [];
  if (Array.isArray(element)) return element.flatMap(nodes);
  return [element, ...nodes(element.props?.children)];
}
function text(element) {
  if (element == null || typeof element === 'boolean') return '';
  if (Array.isArray(element)) return element.map(text).join('');
  if (typeof element !== 'object') return String(element);
  return text(element.props?.children);
}
function input(tree, label) {
  const result = nodes(tree).find((node) => node.props?.['aria-label'] === label);
  assert.ok(result, `Missing control: ${label}`);
  return result;
}
function member(id, role, can_change = true) {
  return {
    id,
    user_id: id,
    name: role,
    email: `${role}@example.test`,
    avatar: {},
    role,
    role_label: role,
    created_at: null,
    can_change,
  };
}
const members = [
  member(1, 'owner', false),
  member(2, 'admin', false),
  member(3, 'member'),
  member(4, 'observer'),
  member('inherited-5', 'inherited', false),
];

test('toolbar selection includes owner and inherited rows without enabling their actions', () => {
  const { Members } = harness();
  let selected = new Set([1, 3, 'inherited-5']);
  const render = () =>
    Members({
      members,
      isOwner: false,
      busy: false,
      rowActions: false,
      selection: { selected, onChange: (next) => (selected = next) },
    });
  let tree = render();
  assert.match(tree.props.className, /workplace-members-sheet--toolbar/);
  assert.equal(
    nodes(tree).some((node) => node.props?.['data-column'] === 'action'),
    false,
  );
  for (const name of ['owner', 'admin', 'inherited']) {
    const checkbox = input(tree, `Zaznacz członka ${name}`);
    assert.equal(checkbox.props.disabled, false);
    assert.equal(checkbox.props.checked, name !== 'admin');
  }
  input(tree, 'Zaznacz wszystkich członków').props.onChange({ target: { checked: true } });
  assert.deepEqual([...selected], [1, 2, 3, 4, 'inherited-5']);
  tree = render();
  assert.equal(input(tree, 'Zaznacz wszystkich członków').props.checked, true);
  input(tree, 'Zaznacz członka owner').props.onChange({ target: { checked: false } });
  assert.deepEqual([...selected], [2, 3, 4, 'inherited-5']);
  tree.props.onKeyDown({ target: tree, currentTarget: tree, key: 'Escape' });
  assert.equal(selected.size, 0);
  let prevented = false;
  tree.props.onKeyDown({
    target: tree,
    currentTarget: tree,
    key: 'a',
    ctrlKey: true,
    preventDefault: () => (prevented = true),
  });
  assert.equal(prevented, true);
  assert.deepEqual([...selected], [1, 2, 3, 4, 'inherited-5']);
});

test('busy toolbar cannot change selection and an owner-only table remains selectable', () => {
  const { Members } = harness();
  let changes = 0;
  const tree = Members({
    members,
    isOwner: false,
    busy: true,
    rowActions: false,
    selection: { selected: new Set([3]), onChange: () => changes++ },
  });
  for (const checkbox of nodes(tree).filter((node) => node.type === 'input')) {
    assert.equal(checkbox.props.disabled, true);
    checkbox.props.onChange({ target: { checked: true } });
  }
  tree.props.onKeyDown({ target: tree, currentTarget: tree, key: 'Escape' });
  tree.props.onKeyDown({
    target: tree,
    currentTarget: tree,
    key: 'a',
    metaKey: true,
    preventDefault() {},
  });
  assert.equal(changes, 0);
  let selected = new Set();
  const ownerOnly = Members({
    members: members.slice(0, 1),
    isOwner: false,
    busy: false,
    rowActions: false,
    selection: { selected, onChange: (next) => (selected = next) },
  });
  const selectAll = input(ownerOnly, 'Zaznacz wszystkich członków');
  assert.equal(selectAll.props.disabled, false);
  selectAll.props.onChange({ target: { checked: true } });
  assert.deepEqual([...selected], [1]);
  const empty = Members({ members: [], isOwner: true, busy: false, rowActions: false });
  assert.equal(input(empty, 'Zaznacz wszystkich członków').props.disabled, true);
});

test('existing member tables retain the action column and selectable owner row by default', () => {
  const { Members } = harness();
  const tree = Members({ members, isOwner: true, busy: false, onRole() {}, onRemove() {} });
  assert.doesNotMatch(tree.props.className, /workplace-members-sheet--toolbar/);
  assert.equal(nodes(tree).filter((node) => node.props?.['data-column'] === 'action').length, 6);
  assert.equal(input(tree, 'Zaznacz członka owner').props.disabled, false);
});

const schema = {
  fields: [{ name: 'role', type: 'select', value: 'member', attrs: {}, errors: [] }],
  errors: [],
};
function sharing(app, props) {
  return app.render('SharingDialog', {
    name: 'Pulpit testowy',
    schema,
    api: '/workplaces/test/api/v1/page/',
    url: '/workplaces/test/dashboards/test/team/',
    csrfToken: 'token',
    onClose() {},
    onSaved: (result) => app.saved.push(result),
    ...props,
  });
}
function roleValue(tree) {
  return nodes(tree).find((node) => node.props?.schema)?.props.schema.fields[0].value;
}
async function submit(tree) {
  await nodes(tree)
    .find((node) => node.type === 'form')
    .props.onSubmit({ preventDefault() {}, currentTarget: { values: [['role', 'observer']] } });
}

test('bulk role dialog submits all member IDs through the scoped endpoint without a sharing picker', async () => {
  const app = harness();
  const tree = sharing(app, { people: [member(3, 'admin'), member(4, 'admin')] });
  assert.equal(tree.props.title, 'Zmień rolę');
  assert.equal(roleValue(tree), 'admin');
  assert.equal(
    nodes(tree).some((node) => node.props?.sharing),
    false,
  );
  assert.equal(nodes(tree).filter((node) => node.props?.person).length, 2);
  await submit(tree);
  assert.equal(app.requests.length, 1);
  const request = app.requests[0];
  assert.match(request.url, /^\/workplaces\/test\/api\/v1\/page\/\?url=/);
  assert.equal(request.headers['X-CSRFToken'], 'token');
  assert.equal(request.body.get('action'), 'role');
  assert.equal(request.body.get('role'), 'observer');
  assert.deepEqual(request.body.getAll('member_ids'), ['3', '4']);
  assert.equal(request.body.has('member_id'), false);
  assert.equal(app.saved.length, 1);
});

test('mixed roles use the form default while single-person and share submissions remain compatible', async () => {
  const app = harness();
  assert.equal(
    roleValue(sharing(app, { people: [member(3, 'admin'), member(4, 'observer')] })),
    'member',
  );
  const single = sharing(app, { person: member(3, 'admin') });
  assert.equal(roleValue(single), 'admin');
  await submit(single);
  assert.equal(app.requests[0].body.get('member_id'), '3');
  assert.equal(app.requests[0].body.has('member_ids'), false);
  const share = sharing(app, { people: [] });
  assert.equal(share.props.title, 'Udostępnij · Pulpit testowy');
  assert.equal(
    nodes(share).some((node) => node.props?.sharing),
    true,
  );
  await submit(share);
  assert.equal(app.requests[1].body.get('action'), 'share');
  assert.equal(app.requests[1].body.has('member_id'), false);
  assert.equal(app.requests[1].body.has('member_ids'), false);
});

test('draft role changes only update the parent draft and explain the final section save', async () => {
  const app = harness(true);
  const people = [member(3, 'admin'), member(4, 'member')];
  const changes = [];
  const tree = sharing(app, { people, onStage: (change) => changes.push(change) });
  assert.match(text(tree), /Dostęp zmieni się po kliknięciu „Zapisz”/);
  assert.equal(
    nodes(tree).find((node) => node.props?.type === 'submit').props.children,
    'Zastosuj',
  );
  await submit(tree);
  assert.equal(changes.length, 1);
  assert.equal(changes[0].people, people);
  assert.equal(changes[0].role, 'observer');
  assert.equal(app.requests.length, 0);
  assert.equal(app.saved.length, 0);
});

test('draft sharing requires a real selected candidate, reports duplicate errors and retries locally', async () => {
  const app = harness(true);
  const candidate = { id: 25, name: 'Anna', email: 'anna@example.test', avatar: {} };
  const changes = [];
  let duplicate = true;
  const props = {
    candidatesUrl: '/workplaces/test/dashboards/test/team/candidates/?draft=1',
    onStage(change) {
      if (duplicate) throw new Error('Ta osoba jest już na liście.');
      changes.push(change);
    },
  };
  let tree = sharing(app, props);
  let picker = nodes(tree).find((node) => node.props?.sharing);
  assert.equal(picker.props.url, props.candidatesUrl);
  assert.equal(nodes(tree).find((node) => node.props?.type === 'submit').props.children, 'Dodaj');
  picker.props.onChange(candidate.email);
  tree = sharing(app, props);
  await submit(tree);
  tree = sharing(app, props);
  assert.match(text(tree), /Wybierz osobę z listy kont Workspace/);
  picker = nodes(tree).find((node) => node.props?.sharing);
  picker.props.onSelect(candidate);
  tree = sharing(app, props);
  await submit(tree);
  tree = sharing(app, props);
  assert.match(text(tree), /Ta osoba jest już na liście/);
  assert.equal(changes.length, 0);
  duplicate = false;
  await submit(tree);
  assert.equal(changes.length, 1);
  assert.equal(changes[0].person, candidate);
  assert.equal(changes[0].role, 'observer');
  assert.equal(app.requests.length, 0);
  assert.equal(app.saved.length, 0);
  picker.props.onChange('inne@example.test');
  await submit(sharing(app, props));
  assert.equal(changes.length, 1, 'editing the search text invalidates the selected candidate');
});

test('candidate search keeps the draft query parameter and also supports ordinary candidate URLs', async () => {
  for (const query of ['', '?draft=1']) {
    const app = harness(true);
    const url = '/workplaces/test/dashboards/test/team/candidates/' + query;
    const tree = app.render('Picker', {
      api: '/workplaces/test/api/v1/page/',
      url,
      token: 'token',
      value: '',
      sharing: true,
      onChange() {},
    });
    input(tree, 'Osoba lub adres e-mail konta Ancore').props.onChange({
      target: { value: 'Anna' },
    });
    await app.flushTimers();
    assert.equal(app.requests.length, 1);
    const target = new URL(app.requests[0].url, 'https://ancore.test').searchParams.get('url');
    assert.equal(target, url + (query ? '&' : '?') + 'q=Anna');
    assert.equal(app.requests[0].method, 'GET');
  }
});
