import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

const require = createRequire(import.meta.url);
const flush = () => new Promise((resolve) => setImmediate(resolve));
const external = [
  'react',
  'react/jsx-runtime',
  '../shared/Modal',
  '../shared/Select',
  '../shared/Icon',
  '../shared/page',
  '../shared/api',
];
async function compile(file) {
  const result = await build({
    entryPoints: [new URL('../src/spaces/' + file, import.meta.url).pathname],
    bundle: true,
    platform: 'node',
    format: 'cjs',
    external,
    write: false,
  });
  return result.outputFiles[0].text;
}
const [rulesCode, dialogCode] = await Promise.all(['kanban.ts', 'BlockDialog.tsx'].map(compile));
function load(code, mocks = {}) {
  const module = { exports: {} };
  vm.runInNewContext(code, {
    module,
    exports: module.exports,
    FormData,
    AbortController,
    Date,
    console,
    require: (name) => mocks[name] || require(name),
  });
  return module.exports;
}
const rules = load(rulesCode);
function nodes(element) {
  if (!element || typeof element !== 'object') return [];
  if (Array.isArray(element)) return element.flatMap(nodes);
  return [element, ...nodes(element.props?.children)];
}
function text(element) {
  if (element == null || typeof element === 'boolean') return '';
  if (Array.isArray(element)) return element.map(text).join('');
  return typeof element === 'object' ? text(element.props?.children) : String(element);
}
function button(tree, label) {
  const result = nodes(tree).find((node) => node.type === 'button' && text(node) === label);
  assert.ok(result, `Missing button ${label}`);
  return result;
}
function item(changes = {}) {
  return {
    id: 12,
    key: 'KAN-12',
    title: 'Dokumentacja',
    editable: true,
    status: 'doing',
    category: 'in_progress',
    in_backlog: false,
    rank: 1024,
    sprint_id: null,
    url: '/space/produkt/task/KAN-12/',
    edit_url: '/edit/',
    action_url: '/action/',
    transitions: [{ key: 'review', label: 'Weryfikacja', category: 'in_progress' }],
    blocked: null,
    blocked_revision: 4,
    ...changes,
  };
}

test('a full WIP column rejects new work but permits reorder within the same column', () => {
  const full = { key: 'review', wip_limit: 3, wip_count: 3, count: 0 };
  assert.equal(rules.wipReached(full), true, 'filtered count does not decide WIP');
  assert.match(rules.boardMoveError(item(), full), /Limit pracy/);
  assert.equal(rules.boardMoveError(item({ status: 'review' }), full), '');
  assert.equal(rules.boardMoveError(item(), { ...full, wip_count: 2 }), '');
  assert.equal(rules.wipReached({ ...full, wip_limit: null }), false);
  assert.match(rules.boardMoveError(item(), { key: 'done', wip_count: 0 }), /nie jest dozwolone/);
});

test('stage age tolerates missing/invalid/future observations and uses full elapsed days', () => {
  const now = Date.parse('2026-11-01T12:00:00Z');
  assert.equal(rules.flowAge(null, now), '');
  assert.equal(rules.flowAge('invalid', now), '');
  assert.equal(rules.flowAge('2026-11-02T12:00:00Z', now), 'krócej niż godzinę');
  assert.equal(rules.flowAge('2026-11-01T09:00:00Z', now), '3 godz.');
  assert.equal(rules.flowAge('2026-10-31T12:00:00Z', now), '1 dzień');
});

function dialog(task = item()) {
  const states = [],
    refs = [],
    requests = [];
  const controls = { failure: null, refreshFailure: null, wait: null, refreshes: 0, closed: 0 };
  let stateIndex = 0,
    refIndex = 0;
  const { BlockDialog } = load(dialogCode, {
    react: {
      ...require('react'),
      useState(initial) {
        const index = stateIndex++;
        if (!(index in states)) states[index] = initial;
        return [
          states[index],
          (next) => (states[index] = typeof next === 'function' ? next(states[index]) : next),
        ];
      },
      useRef(initial) {
        const index = refIndex++;
        if (!(index in refs)) refs[index] = { current: initial };
        return refs[index];
      },
      useEffect() {},
    },
    '../shared/Modal': { Modal: 'Modal' },
    '../shared/Select': { Select: 'Select' },
    '../shared/api': { errorMessage: (error) => error.message },
    '../shared/page': {
      async pageRequest(api, url, csrf, signal, body) {
        requests.push({ api, url, csrf, signal, body });
        if (controls.wait) await controls.wait;
        if (controls.failure) throw controls.failure;
        return { saved: true };
      },
    },
  });
  function render() {
    stateIndex = 0;
    refIndex = 0;
    return BlockDialog({
      data: { item: task, block_responsible_options: [{ id: 17, label: 'Anna' }] },
      api: '/api/v1/page/',
      csrfToken: 'csrf',
      view: 'board',
      onClose: () => controls.closed++,
      onRefresh: async () => {
        controls.refreshes++;
        if (controls.refreshFailure) throw controls.refreshFailure;
      },
    });
  }
  function edit(reason, responsible = '17') {
    nodes(render())
      .find((node) => node.type === 'textarea')
      .props.onChange({ target: { value: reason } });
    nodes(render())
      .find((node) => node.type === 'Select')
      .props.onChange(responsible);
  }
  function submit() {
    nodes(render())
      .find((node) => node.type === 'form')
      .props.onSubmit({ preventDefault() {} });
  }
  return { render, edit, submit, requests, controls };
}

test('block dialog preserves draft after failed POST and submits responsible plus concurrency revision', async () => {
  const app = dialog();
  app.edit('  Brak decyzji klienta  ');
  app.controls.failure = new Error('Brak połączenia');
  app.submit();
  await flush();
  assert.match(text(app.render()), /Brak połączenia/);
  assert.equal(
    nodes(app.render()).find((node) => node.type === 'textarea').props.value,
    '  Brak decyzji klienta  ',
  );
  const values = Object.fromEntries(app.requests[0].body);
  assert.equal(values.blocked_reason, 'Brak decyzji klienta');
  assert.equal(values.blocked_responsible, '17');
  assert.equal(values.source_status, 'doing');
  assert.equal(values.source_in_backlog, 'false');
  assert.equal(values.source_blocked_revision, '4');
  assert.equal(
    values.source_blocked_at,
    undefined,
    'display timestamps lose microseconds; use revision',
  );
  app.controls.failure = null;
  app.submit();
  await flush();
  assert.equal(app.controls.closed, 1);
  assert.equal(app.controls.refreshes, 1);
});

test('a saved block followed by failed refresh retries only the read', async () => {
  const app = dialog();
  app.edit('Brak dostępu');
  app.controls.refreshFailure = new Error('Odczyt niedostępny');
  app.submit();
  await flush();
  assert.equal(app.requests.length, 1);
  assert.match(text(app.render()), /Zmiana została zapisana/);
  assert.ok(button(app.render(), 'Odśwież widok'));
  assert.equal(
    app.render().props.pending,
    true,
    'protect a committed form until the board is refreshed',
  );
  app.controls.refreshFailure = null;
  app.submit();
  await flush();
  assert.equal(app.requests.length, 1);
  assert.equal(app.controls.refreshes, 2);
  assert.equal(app.controls.closed, 1);
});

test('unblock keeps the observed revision and a pending request prevents duplicate writes', async () => {
  const app = dialog(
    item({
      blocked: {
        reason: 'Dostawca',
        at: '2026-11-01T09:00:00.123Z',
        responsible: { id: 17, label: 'Anna' },
      },
    }),
  );
  let resolve;
  app.controls.wait = new Promise((done) => (resolve = done));
  const remove = button(app.render(), 'Usuń blokadę');
  remove.props.onClick();
  remove.props.onClick();
  assert.equal(app.requests.length, 1);
  assert.equal(app.requests[0].body.get('action'), 'unblock');
  assert.equal(app.requests[0].body.get('source_blocked_revision'), '4');
  resolve();
  await flush();
  assert.equal(app.controls.closed, 1);
});
