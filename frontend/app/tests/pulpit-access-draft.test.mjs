import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

// Exercise AccessEditor's actual callbacks, effects and requests without mounting shared layers.
const bundle = await build({
  entryPoints: [new URL('../src/pulpits/AccessEditor.tsx', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  external: ['react', 'react/jsx-runtime', 'react-dom'],
  write: false,
});
const require = createRequire(import.meta.url);

function member(user_id, role, can_change = role !== 'owner') {
  return {
    id: role === 'owner' ? 'owner' : user_id,
    user_id,
    role,
    role_label: role,
    name: `Osoba ${user_id}`,
    email: `osoba${user_id}@example.test`,
    avatar: {},
    created_at: '2026-10-18T12:00:00Z',
    can_change,
  };
}
function fixture(overrides = {}) {
  return {
    name: 'Pulpit testowy',
    visibility: 'private',
    revision: 7,
    is_owner: true,
    can_manage: true,
    can_change_visibility: true,
    members: [member(1, 'owner'), member(2, 'admin'), member(3, 'member'), member(4, 'observer')],
    share_form: {
      fields: [
        {
          name: 'role',
          type: 'select',
          value: 'member',
          attrs: {},
          errors: [],
          choices: [
            { value: 'admin', label: 'Administrator' },
            { value: 'member', label: 'Członek' },
            { value: 'observer', label: 'Obserwator' },
          ],
        },
      ],
      errors: [],
    },
    ...overrides,
  };
}
const candidate = { id: 5, name: 'Anna', email: 'anna@example.test', avatar: {} };
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
function button(tree, label) {
  const result = nodes(tree).find((node) => node.type === 'button' && text(node).trim() === label);
  assert.ok(result, `Missing button: ${label}`);
  return result;
}
function table(tree) {
  const result = nodes(tree).find((node) => node.props?.members && node.props?.selection);
  assert.ok(result, 'Missing members table');
  return result;
}
function dialog(tree) {
  const result = nodes(tree).find((node) => node.props?.onStage);
  assert.ok(result, 'Missing sharing dialog');
  return result;
}
function visibility(tree) {
  const result = nodes(tree).find((node) => node.props?.label?.startsWith('Widoczność:'));
  assert.ok(result, 'Missing visibility picker');
  return result;
}
function snapshot(tree) {
  return JSON.parse(JSON.stringify(table(tree).props.members));
}
function harness(initial = fixture(), options = {}) {
  const hooks = [];
  const requests = [];
  const saved = [];
  const states = [];
  let cursor = 0;
  let changed = false;
  let effects = [];
  function useState(initial) {
    const index = cursor++;
    if (!(index in hooks)) hooks[index] = typeof initial === 'function' ? initial() : initial;
    return [
      hooks[index],
      (next) => {
        const value = typeof next === 'function' ? next(hooks[index]) : next;
        if (!Object.is(value, hooks[index])) {
          hooks[index] = value;
          changed = true;
        }
      },
    ];
  }
  function useEffect(callback, dependencies) {
    const index = cursor++;
    const previous = hooks[index];
    if (!previous || dependencies.some((value, i) => !Object.is(value, previous.dependencies[i]))) {
      effects.push(() => {
        previous?.cleanup?.();
        hooks[index] = { dependencies, cleanup: callback() };
      });
    }
  }
  const app = { requests, saved, states, result: initial, failure: null, status: 200, gate: null };
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
            useEffect,
          }
        : require(name),
    AbortController,
    AbortSignal,
    FormData,
    URL,
    Error,
    location: { origin: 'https://ancore.test' },
    fetch: async (url, options) => {
      requests.push({ url, ...options });
      if (app.gate) await app.gate;
      if (app.failure) throw app.failure;
      return {
        ok: app.status < 400,
        status: app.status,
        headers: { get: () => 'application/json' },
        json: async () => app.result,
      };
    },
  });
  let props = {
    team: initial,
    api: '/workplaces/test/api/v1/page/',
    url: '/workplaces/test/dashboards/test/team/',
    csrfToken: 'token',
    settingsDirty: false,
    blocked: false,
    onSaved: (result) => {
      saved.push(result);
      props = { ...props, team: result };
    },
    onStateChange: (dirty, pending) => {
      states.push({ dirty, pending });
    },
    ...options,
  };
  app.render = (updates = {}) => {
    props = { ...props, ...updates };
    let tree;
    let renders = 0;
    do {
      assert.ok(++renders < 20, 'Effects should settle without a render loop');
      cursor = 0;
      changed = false;
      effects = [];
      tree = module.exports.default(props);
      effects.forEach((callback) => callback());
    } while (changed);
    return tree;
  };
  app.select = (...ids) => {
    table(app.render()).props.selection.onChange(new Set(ids));
    return app.render();
  };
  app.role = (ids, role) => {
    button(app.select(...ids), 'Zmień rolę').props.onClick();
    const modal = dialog(app.render());
    modal.props.onStage({ people: modal.props.people, role });
    return app.render();
  };
  app.share = (person = candidate, role = 'member') => {
    button(app.render(), 'Udostępnij').props.onClick();
    dialog(app.render()).props.onStage({ person, role });
    return app.render();
  };
  app.remove = (...ids) => {
    button(app.select(...ids), 'Odbierz dostęp').props.onClick();
    return app.render();
  };
  app.visibility = (value) => {
    const menu = visibility(app.render()).props.children(() => {});
    button(
      menu,
      value === 'private' ? 'Prywatna — wybrane osoby' : 'Publiczna — cały Workspace',
    ).props.onClick();
    return app.render();
  };
  app.settle = async () => {
    await new Promise((resolve) => setImmediate(resolve));
    return app.render();
  };
  return app;
}

test('space role and sharing dialogs save immediately with the current revision and retain errors for retry', async () => {
  const app = harness(fixture(), { saveOnAction: true, publicVisibility: 'public' });
  let tree = app.render();
  assert.equal(
    nodes(tree).filter((node) => node.props?.className === 'member-access-save-actions').length,
    0,
  );
  button(app.select(3), 'Zmień rolę').props.onClick();
  let sharing = dialog(app.render());
  app.failure = new Error('Sieć niedostępna');
  await assert.rejects(
    sharing.props.onStage({ people: sharing.props.people, role: 'observer' }),
    /Sieć niedostępna/,
  );
  assert.ok(dialog(app.render()));
  assert.equal(app.saved.length, 0);
  app.failure = null;
  app.result = fixture({
    revision: 8,
    members: [member(1, 'owner'), member(2, 'admin'), member(3, 'observer'), member(4, 'observer')],
  });
  sharing = dialog(app.render());
  await sharing.props.onStage({ people: sharing.props.people, role: 'observer' });
  tree = app.render();
  assert.equal(app.requests.length, 2);
  assert.equal(app.requests[1].body.get('revision'), '7');
  assert.equal(
    JSON.parse(app.requests[1].body.get('members')).some((row) => row.user_id === 1),
    false,
  );
  button(tree, 'Udostępnij').props.onClick();
  app.result = fixture({ revision: 9, members: [...app.result.members, member(5, 'member')] });
  await dialog(app.render()).props.onStage({ person: candidate, role: 'member' });
  assert.equal(app.requests[2].body.get('revision'), '8');
  assert.equal(app.saved.length, 2);
});

test('space visibility and removal wait for confirmation, and cancellation never writes access', async () => {
  const app = harness(fixture(), { saveOnAction: true, publicVisibility: 'public' });
  let tree = app.visibility('public');
  let confirmation = nodes(tree).find((node) => node.props?.title === 'Zmień widoczność');
  assert.equal(app.requests.length, 0);
  button(confirmation, 'Anuluj').props.onClick();
  tree = await app.settle();
  assert.equal(visibility(tree).props.label, 'Widoczność: Prywatna');
  tree = app.remove(3, 4);
  confirmation = nodes(tree).find((node) => node.props?.title === 'Odbierz dostęp');
  assert.equal(app.requests.length, 0);
  app.failure = new Error('POST 503');
  await button(confirmation, 'Odbierz dostęp').props.onClick();
  tree = app.render();
  confirmation = nodes(tree).find((node) => node.props?.title === 'Odbierz dostęp');
  assert.match(text(confirmation), /POST 503/);
  button(confirmation, 'Anuluj').props.onClick();
  tree = await app.settle();
  assert.equal(snapshot(tree).length, 4);
  app.failure = null;
  tree = app.visibility('public');
  confirmation = nodes(tree).find((node) => node.props?.title === 'Zmień widoczność');
  app.result = fixture({ revision: 8, visibility: 'public' });
  await button(confirmation, 'Zmień widoczność').props.onClick();
  assert.equal(app.requests[1].body.get('visibility'), 'public');
  assert.deepEqual(JSON.parse(app.requests[1].body.get('members')), []);
});

test('retrying a failed immediate share replaces the attempted recipient instead of granting both', async () => {
  const app = harness(fixture(), { saveOnAction: true, publicVisibility: 'public' });
  button(app.render(), 'Udostępnij').props.onClick();
  app.failure = new Error('POST 503');
  await assert.rejects(dialog(app.render()).props.onStage({ person: candidate, role: 'member' }));
  await assert.rejects(
    dialog(app.render()).props.onStage({ person: candidate, role: 'observer' }),
    /POST 503/,
  );
  assert.equal(app.requests.length, 2);
  app.failure = null;
  const replacement = { ...candidate, id: 6, email: 'nowa@example.test' };
  app.result = fixture({ revision: 8, members: [...fixture().members, member(6, 'observer')] });
  await dialog(app.render()).props.onStage({ person: replacement, role: 'observer' });
  const rows = JSON.parse(app.requests[2].body.get('members'));
  assert.equal(
    rows.some((row) => row.user_id === 5),
    false,
  );
  assert.deepEqual(
    rows.find((row) => row.user_id === 6),
    { user_id: 6, role: 'observer' },
  );
});

test('space sharing conflict blocks another mutation and closing the dialog reloads current access', async () => {
  const app = harness(fixture(), { saveOnAction: true, publicVisibility: 'public' });
  button(app.select(3), 'Zmień rolę').props.onClick();
  let sharing = dialog(app.render());
  app.status = 409;
  app.result = { error: 'Dostęp zmienił się' };
  await assert.rejects(sharing.props.onStage({ people: sharing.props.people, role: 'observer' }));
  sharing = dialog(app.render());
  assert.equal(sharing.props.stageBlocked, true);
  await sharing.props.onStage({ people: sharing.props.people, role: 'observer' });
  assert.equal(app.requests.length, 1);
  app.status = 200;
  app.result = fixture({ revision: 9 });
  sharing.props.onClose();
  const tree = await app.settle();
  assert.equal(
    nodes(tree).some((node) => node.props?.onStage),
    false,
  );
  assert.deepEqual(
    app.requests.map((request) => request.method),
    ['POST', 'GET'],
  );
});

test('role, removal, sharing and visibility edits remain local, and Cancel restores the saved access', () => {
  const initial = fixture();
  const app = harness(initial);
  app.role([3], 'observer');
  app.remove(4);
  let tree = app.share();
  assert.deepEqual(
    snapshot(tree).map(({ user_id, role }) => [user_id, role]),
    [
      [1, 'owner'],
      [2, 'admin'],
      [3, 'observer'],
      [5, 'member'],
    ],
  );
  tree = app.visibility('workspace');
  assert.equal(visibility(tree).props.label, 'Widoczność: Publiczna');
  assert.equal(app.requests.length, 0);
  assert.equal(app.saved.length, 0);
  assert.deepEqual(app.states.at(-1), { dirty: true, pending: false });
  button(tree, 'Anuluj').props.onClick();
  tree = app.render();
  assert.deepEqual(snapshot(tree), initial.members);
  assert.equal(visibility(tree).props.label, 'Widoczność: Prywatna');
  assert.equal(table(tree).props.selection.selected.size, 0);
  assert.equal(button(tree, 'Zapisz').props.disabled, true);
  assert.deepEqual(app.states.at(-1), { dirty: false, pending: false });
  assert.equal(app.requests.length, 0);
});

test('Save submits one atomic revisioned snapshot without the owner and adopts the returned state', async () => {
  const app = harness();
  app.role([3], 'observer');
  app.remove(4);
  app.share();
  app.result = fixture({
    revision: 8,
    members: [member(1, 'owner'), member(2, 'admin'), member(3, 'observer'), member(5, 'member')],
  });
  button(app.render(), 'Zapisz').props.onClick();
  const tree = await app.settle();
  assert.equal(app.requests.length, 1);
  const request = app.requests[0];
  assert.equal(request.method, 'POST');
  assert.equal(request.headers['X-CSRFToken'], 'token');
  assert.equal(
    new URL(request.url, 'https://ancore.test').searchParams.get('url'),
    '/workplaces/test/dashboards/test/team/',
  );
  assert.equal(request.body.get('action'), 'save');
  assert.equal(request.body.get('revision'), '7');
  assert.equal(request.body.get('visibility'), 'private');
  assert.deepEqual(JSON.parse(request.body.get('members')), [
    { user_id: 2, role: 'admin' },
    { user_id: 3, role: 'observer' },
    { user_id: 5, role: 'member' },
  ]);
  assert.deepEqual(snapshot(tree), app.result.members);
  assert.equal(app.saved[0], app.result);
  assert.equal(button(tree, 'Zapisz').props.disabled, true);
  assert.doesNotMatch(text(tree), /Dostęp został zapisany/);
  assert.deepEqual(app.states.at(-1), { dirty: false, pending: false });
});

test('owner-only selection cannot mutate access and mixed administrator selection affects only editable people', () => {
  const app = harness(
    fixture({
      is_owner: false,
      can_change_visibility: false,
      members: [
        member(1, 'owner'),
        member(2, 'admin', false),
        member(3, 'member'),
        member(4, 'observer'),
      ],
    }),
  );
  let tree = app.select('owner');
  assert.equal(table(tree).props.selection.selected.has('owner'), true);
  assert.equal(button(tree, 'Zmień rolę').props.disabled, true);
  assert.equal(button(tree, 'Odbierz dostęp').props.disabled, true);
  assert.equal(button(tree, 'Zapisz').props.disabled, true);
  tree = app.role(['owner', 2, 3], 'observer');
  assert.deepEqual(
    snapshot(tree).map(({ user_id, role }) => [user_id, role]),
    [
      [1, 'owner'],
      [2, 'admin'],
      [3, 'observer'],
      [4, 'observer'],
    ],
  );
  tree = app.remove('owner', 2, 3);
  assert.deepEqual(
    snapshot(tree).map(({ user_id }) => user_id),
    [1, 2, 4],
  );
  assert.equal(app.requests.length, 0);
});

test('failed save preserves the complete draft and selection for a retry with the same revision', async () => {
  const app = harness();
  app.role([3], 'observer');
  app.share();
  const sharedId = snapshot(app.render()).find((row) => row.user_id === 5).id;
  const before = snapshot(app.select(3, sharedId));
  app.failure = new Error('Sieć niedostępna');
  button(app.render(), 'Zapisz').props.onClick();
  let tree = await app.settle();
  assert.deepEqual(snapshot(tree), before);
  assert.deepEqual([...table(tree).props.selection.selected], [3, sharedId]);
  assert.match(text(tree), /Sieć niedostępna/);
  assert.equal(button(tree, 'Zapisz').props.disabled, false);
  assert.deepEqual(app.states.at(-1), { dirty: true, pending: false });
  assert.equal(app.saved.length, 0);
  app.failure = null;
  app.result = fixture({ revision: 8, members: before });
  button(tree, 'Zapisz').props.onClick();
  tree = await app.settle();
  assert.equal(app.requests.length, 2);
  assert.deepEqual([...app.requests[1].body], [...app.requests[0].body]);
  assert.equal(button(tree, 'Zapisz').props.disabled, true);
  assert.equal(app.saved.length, 1);
});

test('concurrent Save clicks send one request and block edits until the request completes', async () => {
  const app = harness();
  app.role([3], 'observer');
  let release;
  app.gate = new Promise((resolve) => (release = resolve));
  const save = button(app.render(), 'Zapisz');
  save.props.onClick();
  save.props.onClick();
  const tree = app.render();
  assert.equal(app.requests.length, 1);
  assert.equal(button(tree, 'Zapisywanie…').props.disabled, true);
  assert.equal(button(tree, 'Anuluj').props.disabled, true);
  assert.equal(button(tree, 'Udostępnij').props.disabled, true);
  assert.equal(table(tree).props.busy, true);
  assert.equal(visibility(tree).props.disabled, true);
  assert.deepEqual(app.states.at(-1), { dirty: true, pending: true });
  button(tree, 'Anuluj').props.onClick();
  assert.equal(app.requests.length, 1);
  release();
  await app.settle();
  assert.equal(app.saved.length, 1);
});

test('public access saves no individual memberships and inherited rows cannot be changed', async () => {
  const app = harness();
  let tree = app.visibility('workspace');
  tree = app.select('owner', 2, 3);
  assert.equal(button(tree, 'Zmień rolę').props.disabled, true);
  assert.equal(button(tree, 'Odbierz dostęp').props.disabled, true);
  assert.equal(button(tree, 'Udostępnij').props.disabled, true);
  app.result = fixture({ visibility: 'workspace', revision: 8 });
  button(tree, 'Zapisz').props.onClick();
  await app.settle();
  assert.equal(app.requests[0].body.get('visibility'), 'workspace');
  assert.deepEqual(JSON.parse(app.requests[0].body.get('members')), []);
});

test('a settings-only revision update preserves the access draft and uses the latest revision on Save', async () => {
  const initial = fixture();
  const app = harness(initial);
  app.role([3], 'observer');
  let tree = app.render({ team: { ...initial, name: 'Nowa nazwa', revision: 8 } });
  assert.equal(snapshot(tree).find((row) => row.user_id === 3).role, 'observer');
  assert.equal(button(tree, 'Zapisz').props.disabled, false);
  button(tree, 'Zapisz').props.onClick();
  await app.settle();
  assert.equal(app.requests[0].body.get('revision'), '8');
});

test('a revision conflict retains the draft until Cancel reloads current server access', async () => {
  const app = harness();
  app.remove(4);
  app.status = 409;
  app.result = { message: 'Dostęp został zmieniony przez inną osobę.' };
  button(app.render(), 'Zapisz').props.onClick();
  let tree = await app.settle();
  assert.equal(
    snapshot(tree).some((row) => row.user_id === 4),
    false,
  );
  assert.equal(button(tree, 'Zapisz').props.disabled, true);
  assert.match(text(tree), /odrzucić szkic i wczytać aktualny dostęp/);
  app.status = 200;
  app.result = fixture({ revision: 9, members: [member(1, 'owner'), member(4, 'admin')] });
  button(tree, 'Anuluj').props.onClick();
  tree = await app.settle();
  assert.equal(app.requests.length, 2);
  assert.equal(app.requests[1].method, 'GET');
  assert.equal(app.requests[1].body, undefined);
  assert.deepEqual(snapshot(tree), app.result.members);
  assert.equal(button(tree, 'Zapisz').props.disabled, true);
  assert.doesNotMatch(text(tree), /Wczytano aktualny dostęp/);
});

test('space visibility uses its public token and preserves its complete string revision on Save', async () => {
  const revision = '2026-10-31T09:13:24.123456+00:00';
  const app = harness(fixture({ name: 'Przestrzeń testowa', revision }), {
    publicVisibility: 'public',
    url: '/workplaces/test/space/test/members/',
  });
  const tree = app.visibility('public');
  assert.equal(visibility(tree).props.label, 'Widoczność: Publiczna');
  assert.equal(button(tree, 'Udostępnij').props.disabled, true);
  assert.equal(app.requests.length, 0);
  app.result = fixture({ visibility: 'public', revision: '2026-10-31T09:13:25.123456+00:00' });
  button(tree, 'Zapisz').props.onClick();
  await app.settle();
  const request = app.requests[0];
  assert.equal(request.body.get('revision'), revision);
  assert.equal(request.body.get('visibility'), 'public');
  assert.deepEqual(JSON.parse(request.body.get('members')), []);
  assert.equal(
    new URL(request.url, 'https://ancore.test').searchParams.get('url'),
    '/workplaces/test/space/test/members/',
  );
});

test('public spaces stage the prospective private owner and Cancel restores inherited access', async () => {
  const initial = fixture({
    visibility: 'public',
    revision: '2026-10-31T10:00:00+00:00',
    is_owner: false,
    members: [member(1, 'owner'), member(2, 'member', false), member(9, 'admin', false)],
    private_owner: member(9, 'owner'),
  });
  const app = harness(initial, { publicVisibility: 'public' });
  const inherited = snapshot(app.render());
  let tree = app.visibility('private');
  assert.deepEqual(
    snapshot(tree).map(({ user_id, role }) => [user_id, role]),
    [[9, 'owner']],
  );
  tree = app.select(snapshot(tree)[0].id);
  assert.equal(button(tree, 'Zmień rolę').props.disabled, true);
  assert.equal(button(tree, 'Odbierz dostęp').props.disabled, true);
  tree = app.share();
  assert.equal(app.requests.length, 0);
  button(tree, 'Anuluj').props.onClick();
  tree = app.render();
  assert.deepEqual(snapshot(tree), inherited);
  assert.equal(visibility(tree).props.label, 'Widoczność: Publiczna');
  assert.equal(button(tree, 'Zapisz').props.disabled, true);
  assert.equal(app.requests.length, 0);

  app.visibility('private');
  tree = app.share(candidate, 'observer');
  app.result = fixture({
    revision: '2026-10-31T10:01:00+00:00',
    members: [member(9, 'owner'), member(5, 'observer')],
  });
  button(tree, 'Zapisz').props.onClick();
  await app.settle();
  assert.equal(app.requests[0].body.get('visibility'), 'private');
  assert.deepEqual(JSON.parse(app.requests[0].body.get('members')), [
    { user_id: 5, role: 'observer' },
  ]);
});

test('new user IDs cannot collide with saved membership IDs during role changes or removal', async () => {
  const initial = fixture({
    members: [member(1, 'owner'), { ...member(2, 'member'), id: 5 }],
  });
  const app = harness(initial, { publicVisibility: 'public' });
  let tree = app.share(candidate, 'observer');
  const added = snapshot(tree).find((row) => row.user_id === 5);
  assert.notEqual(added.id, 5);
  assert.equal(new Set(snapshot(tree).map((row) => row.id)).size, 3);
  tree = app.role([5], 'admin');
  assert.deepEqual(
    snapshot(tree).map(({ user_id, role }) => [user_id, role]),
    [
      [1, 'owner'],
      [2, 'admin'],
      [5, 'observer'],
    ],
  );
  tree = app.remove(added.id);
  assert.deepEqual(
    snapshot(tree).map((row) => row.user_id),
    [1, 2],
  );
  app.result = fixture({
    members: [member(1, 'owner'), { ...member(2, 'admin'), id: 5 }],
  });
  button(tree, 'Zapisz').props.onClick();
  await app.settle();
  assert.deepEqual(JSON.parse(app.requests[0].body.get('members')), [
    { user_id: 2, role: 'admin' },
  ]);
});

test('space settings revision changes preserve the draft while Cancel retains the latest server access', async () => {
  const initial = fixture({ revision: '2026-10-31T10:00:00+00:00' });
  const current = {
    ...initial,
    name: 'Nowa nazwa przestrzeni',
    revision: '2026-10-31T10:01:00+00:00',
  };
  const app = harness(initial, { publicVisibility: 'public' });
  app.role([3], 'observer');
  let tree = app.render({ team: current });
  assert.equal(snapshot(tree).find((row) => row.user_id === 3).role, 'observer');
  assert.equal(button(tree, 'Zapisz').props.disabled, false);
  button(tree, 'Anuluj').props.onClick();
  tree = app.render();
  assert.deepEqual(snapshot(tree), current.members);
  assert.equal(app.requests.length, 0);
  assert.equal(button(tree, 'Zapisz').props.disabled, true);
  tree = app.role([3], 'observer');
  app.result = { ...current, members: snapshot(tree) };
  button(tree, 'Zapisz').props.onClick();
  await app.settle();
  assert.equal(app.requests[0].body.get('revision'), current.revision);
});

test('a visibility change saved in space settings keeps a staged membership draft revisioned until Cancel', async () => {
  const initial = fixture({ revision: 'a'.repeat(64) });
  const app = harness(initial, { publicVisibility: 'public' });
  const drafted = snapshot(app.role([3], 'observer'));
  const current = fixture({ visibility: 'public', revision: 'b'.repeat(64) });
  let tree = app.render({ team: current });
  assert.deepEqual(snapshot(tree), drafted);
  assert.equal(visibility(tree).props.label, 'Widoczność: Prywatna');
  app.status = 409;
  app.result = { message: 'Dostęp został zmieniony przez inną osobę.' };
  button(tree, 'Zapisz').props.onClick();
  tree = await app.settle();
  assert.equal(app.requests[0].body.get('revision'), initial.revision);
  assert.equal(app.requests[0].body.get('visibility'), 'private');
  assert.deepEqual(snapshot(tree), drafted);
  assert.equal(button(tree, 'Zapisz').props.disabled, true);
  app.status = 200;
  app.result = current;
  button(tree, 'Anuluj').props.onClick();
  tree = await app.settle();
  assert.equal(visibility(tree).props.label, 'Widoczność: Publiczna');
  assert.equal(button(tree, 'Zapisz').props.disabled, true);
  assert.equal(app.requests.length, 2);
  assert.equal(app.requests[1].method, 'GET');
});

test('Cancel immediately adopts refreshed access when space settings changed visibility during a draft', () => {
  const app = harness(fixture({ revision: 'a'.repeat(64) }), { publicVisibility: 'public' });
  app.role([3], 'observer');
  const current = fixture({ visibility: 'public', revision: 'b'.repeat(64) });
  const tree = app.render({ team: current });
  button(tree, 'Anuluj').props.onClick();
  const cancelled = app.render();
  assert.equal(visibility(cancelled).props.label, 'Widoczność: Publiczna');
  assert.equal(button(cancelled, 'Zapisz').props.disabled, true);
  assert.equal(table(cancelled).props.selection.selected.size, 0);
  assert.equal(app.requests.length, 0);
  assert.deepEqual(app.states.at(-1), { dirty: false, pending: false });
});

test('an unsaved settings draft disables access visibility while preserving staged member edits', () => {
  const app = harness(fixture(), { publicVisibility: 'public' });
  app.role([3], 'observer');
  let tree = app.render({ settingsDirty: true });
  assert.equal(visibility(tree).props.disabled, true);
  assert.equal(snapshot(tree).find((row) => row.user_id === 3).role, 'observer');
  assert.equal(button(tree, 'Zapisz').props.disabled, false);
  tree = app.render({ settingsDirty: false });
  assert.equal(visibility(tree).props.disabled, false);
  assert.equal(snapshot(tree).find((row) => row.user_id === 3).role, 'observer');
  assert.equal(app.requests.length, 0);
});
