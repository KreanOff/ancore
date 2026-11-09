import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

// Run the real view, dialog and HTTP helper; only browser surfaces and hooks are controlled.
const bundle = await build({
  stdin: {
    contents: `${await readFile(new URL('../src/spaces/TimelineView.tsx', import.meta.url), 'utf8')}\nexport { DatesDialog };`,
    sourcefile: 'TimelineView.tsx',
    resolveDir: new URL('../src/spaces', import.meta.url).pathname,
    loader: 'tsx',
  },
  bundle: true,
  platform: 'node',
  format: 'cjs',
  jsx: 'automatic',
  external: ['react', 'react/jsx-runtime', 'react-dom'],
  write: false,
});
const require = createRequire(import.meta.url);
const base = '/workplaces/w_test/space/produkt/';
const pageUrl = base + '?view=timeline&assignee=me&page=2';

function nodes(element) {
  if (!element || typeof element !== 'object') return [];
  if (Array.isArray(element)) return element.flatMap(nodes);
  return [
    element,
    ...nodes(element.props?.children),
    ...(element.type?.name === 'ItemToolbar'
      ? [...nodes(element.props?.search), ...nodes(element.props?.actions)]
      : []),
  ];
}
function text(element) {
  if (element == null || typeof element === 'boolean') return '';
  if (Array.isArray(element)) return element.map(text).join('');
  return typeof element === 'object' ? text(element.props?.children) : String(element);
}
function byClass(tree, name) {
  return nodes(tree).find((node) => node.props?.className?.split(' ').includes(name));
}
function dialog(tree) {
  return nodes(tree).find(
    (node) => typeof node.type === 'function' && node.type.name === 'DatesDialog',
  );
}
function dateInputs(tree) {
  return nodes(tree).filter(
    (node) => node.type === 'input' && node.props.type === 'datetime-local',
  );
}
function button(tree, label) {
  return nodes(tree).find((node) => node.type === 'button' && text(node) === label);
}
function deferred() {
  let resolve;
  const promise = new Promise((done) => (resolve = done));
  return { promise, resolve };
}
const settle = () => new Promise(setImmediate);

function item(overrides = {}) {
  return {
    id: 7,
    task_id: 17,
    key: 'PRO-7',
    title: 'Przygotuj kampanię',
    url: base + 'tasks/PRO-7/?view=timeline',
    update_dates_url: base + 'tasks/PRO-7/dates/',
    action_url: base + 'tasks/PRO-7/action/',
    start_at: '2026-10-20T07:15:00Z',
    start_on: '2026-10-20',
    end_on: '2026-10-23',
    due_at: '2026-10-23T14:37:12.987Z',
    due_urgency: 'normal',
    category: 'new',
    status: 'new',
    status_label: 'Do zrobienia',
    transitions: [{ key: 'in_progress', label: 'W toku', category: 'in_progress' }],
    type_label: 'Zadanie',
    type_icon: 'check',
    editable: true,
    assignee: null,
    ...overrides,
  };
}

function harness(initialItem = item()) {
  const requests = [],
    updates = [],
    navigation = [],
    listeners = new Map();
  const slots = new Map();
  let active,
    cursor = 0,
    effects = [];
  function slot(create) {
    const index = cursor++;
    if (!(index in active)) active[index] = create();
    return active[index];
  }
  const same = (a, b) =>
    a && b && a.length === b.length && a.every((value, index) => Object.is(value, b[index]));
  const react = {
    useState(initial) {
      const state = slot(() => ({ value: typeof initial === 'function' ? initial() : initial }));
      return [
        state.value,
        (next) => {
          state.value = typeof next === 'function' ? next(state.value) : next;
        },
      ];
    },
    useRef(initial) {
      return slot(() => ({ current: initial }));
    },
    useMemo(callback, dependencies) {
      const memo = slot(() => ({}));
      if (!same(memo.dependencies, dependencies)) {
        memo.value = callback();
        memo.dependencies = dependencies;
      }
      return memo.value;
    },
    useEffect(callback, dependencies) {
      const effect = slot(() => ({}));
      if (!same(effect.dependencies, dependencies)) {
        effects.push(() => {
          effect.cleanup?.();
          effect.cleanup = callback();
          effect.dependencies = dependencies;
        });
      }
    },
  };
  react.useLayoutEffect = react.useEffect;
  const viewport = {
    scrollLeft: 0,
    clientWidth: 1100,
    querySelector: () => ({ offsetWidth: 300 }),
  };
  const context = {
    response: {
      start_at: '2026-10-21T07:15:00Z',
      start_on: '2026-10-21',
      end_on: '2026-10-24',
      due_at: '2026-10-24T14:37:12.987Z',
      due_urgency: 'overdue',
    },
    status: 200,
    wait: null,
  };
  const module = { exports: {} };
  vm.runInNewContext(bundle.outputFiles[0].text, {
    module,
    exports: module.exports,
    require: (name) => (name === 'react' ? { ...require('react'), ...react } : require(name)),
    AbortController,
    AbortSignal,
    URL,
    URLSearchParams,
    Error,
    TypeError,
    location: { origin: 'http://localhost' },
    window: {
      location: { origin: 'http://localhost' },
      AncoreApp: { navigate: (url) => navigation.push(url) },
    },
    document: {
      addEventListener: (name, callback) => listeners.set(name, callback),
      removeEventListener: (name, callback) => {
        if (listeners.get(name) === callback) listeners.delete(name);
      },
    },
    getComputedStyle: () => ({ getPropertyValue: () => '560' }),
    fetch: async (url, options) => {
      requests.push({ url: String(url), ...options });
      if (context.wait) await context.wait;
      return {
        ok: context.status < 400,
        status: context.status,
        headers: { get: () => 'application/json' },
        json: async () => context.response,
      };
    },
  });
  const props = {
    data: {
      items: [initialItem],
      filters: {},
      space: { id: 2 },
      timeline: { today: '2026-10-28' },
    },
    url: pageUrl,
    csrfToken: 'timeline-csrf',
    busy: false,
    moreControl: () => null,
    onUpdate: (next) => updates.push(next),
  };
  function renderComponent(name, component, values) {
    if (!slots.has(name)) slots.set(name, []);
    active = slots.get(name);
    cursor = 0;
    effects = [];
    const tree = component(values);
    const scroll = byClass(tree, 'work-timeline-viewport');
    if (scroll?.ref) scroll.ref.current = viewport;
    for (const callback of effects) callback();
    return tree;
  }
  return {
    context,
    props,
    requests,
    updates,
    navigation,
    listeners,
    viewport,
    render(next = {}) {
      Object.assign(props, next);
      return renderComponent('timeline', module.exports.default, props);
    },
    renderDialog(values) {
      return renderComponent('dialog', module.exports.DatesDialog, values);
    },
    destroy() {
      for (const state of slots.values()) for (const current of state) current.cleanup?.();
    },
  };
}

function keyboard(key = 'ArrowRight', shiftKey = false) {
  return { key, shiftKey, preventDefault() {} };
}
function pointerTarget() {
  return {
    captured: [],
    released: [],
    zoom: 1,
    closest() {
      return { offsetWidth: 1000, getBoundingClientRect: () => ({ width: 1000 * this.zoom }) };
    },
    setPointerCapture(id) {
      this.captured.push(id);
    },
    releasePointerCapture(id) {
      this.released.push(id);
    },
  };
}
function pointer(target, clientX, overrides = {}) {
  return {
    button: 0,
    pointerId: 5,
    clientX,
    currentTarget: target,
    stopPropagation() {},
    ...overrides,
  };
}

test('keyboard scheduling sends only date fields and source snapshot to the direct scoped endpoint', async () => {
  const original = item(),
    app = harness(original);
  byClass(app.render(), 'work-timeline-bar-body').props.onKeyDown(keyboard());
  await settle();
  assert.equal(app.requests.length, 1);
  const sent = app.requests[0];
  assert.equal(sent.url, 'http://localhost' + original.update_dates_url);
  assert.equal(sent.method, 'POST');
  assert.equal(sent.credentials, 'same-origin');
  assert.equal(sent.headers['X-CSRFToken'], 'timeline-csrf');
  assert.equal(sent.headers['Content-Type'], 'application/x-www-form-urlencoded;charset=UTF-8');
  assert.deepEqual(Object.fromEntries(sent.body), {
    start_on: '2026-10-21',
    end_on: '2026-10-24',
    source_start_at: original.start_at,
    source_due_at: original.due_at,
  });
  assert.equal(app.updates.length, 1);
  assert.equal(app.updates[0].due_at, app.context.response.due_at);
  assert.equal(app.updates[0].due_urgency, 'overdue');
  assert.equal(app.updates[0].title, original.title);
  assert.equal(app.updates[0].status, original.status);
  assert.equal(original.start_on, '2026-10-20');
  assert.match(text(app.render()), /Zapisano daty PRO-7/);
  assert.deepEqual(app.navigation, []);
  app.destroy();
});

test('loading more preserves the calendar viewport and uses the shared control below its rows', () => {
  const app = harness();
  const control = { type: 'button', props: { children: 'Pokaż więcej' } };
  let tree = app.render({ moreControl: () => control });
  assert.ok(nodes(byClass(tree, 'work-timeline-viewport')).includes(control));
  app.viewport.scrollLeft = 700;
  tree = app.render({ data: { ...app.props.data, items: [item(), item({ id: 8 })] } });
  assert.equal(app.viewport.scrollLeft, 700);
  assert.equal(nodes(tree).filter((node) => node.type === 'tr').length, 3);
  app.destroy();
});

test('timeline search resets its loaded range while retaining filters', () => {
  const app = harness();
  const tree = app.render({ url: pageUrl + '&timeline_limit=60' });
  nodes(tree)
    .find((node) => node.type === 'form')
    .props.onSubmit({ preventDefault() {} });
  const next = new URL(app.navigation[0], 'http://localhost');
  assert.equal(next.searchParams.has('timeline_limit'), false);
  assert.equal(next.searchParams.has('page'), false);
  assert.equal(next.searchParams.get('assignee'), 'me');
  app.destroy();
});

test('pending guard blocks two callbacks before rerender and unlocks after the response', async () => {
  const app = harness(),
    gate = deferred();
  app.context.wait = gate.promise;
  let moreLocked;
  const bar = byClass(
    app.render({
      moreControl: (locked) => {
        moreLocked = locked;
        return null;
      },
    }),
    'work-timeline-bar-body',
  );
  assert.equal(moreLocked, false);
  bar.props.onKeyDown(keyboard());
  bar.props.onKeyDown(keyboard());
  assert.equal(app.requests.length, 1);
  assert.equal(byClass(app.render(), 'work-timeline-bar-body').props['aria-disabled'], true);
  assert.equal(moreLocked, true);
  assert.match(text(app.render()), /Zapisuję daty PRO-7/);
  gate.resolve();
  await settle();
  assert.equal(app.updates.length, 1);
  assert.equal(byClass(app.render(), 'work-timeline-bar-body').props['aria-disabled'], false);
  assert.equal(moreLocked, false);
  app.destroy();
});

test('date editor retains dirty values and server error, then retries the same source snapshot', async () => {
  const app = harness();
  byClass(app.render(), 'work-timeline-bar-body').props.onClick();
  let editing = dialog(app.render()),
    form = app.renderDialog(editing.props);
  assert.equal(form.props.dirty, false);
  dateInputs(form)[0].props.onChange({ target: { value: '2026-10-27T09:15' } });
  dateInputs(form)[1].props.onChange({ target: { value: '2026-10-31T16:37' } });
  form = app.renderDialog(editing.props);
  assert.equal(form.props.dirty, true);
  app.context.status = 503;
  app.context.response = { message: 'Zapis jest chwilowo niedostępny.' };
  nodes(form)
    .find((node) => node.type === 'form')
    .props.onSubmit({ preventDefault() {} });
  await settle();
  assert.equal(app.updates.length, 0);
  editing = dialog(app.render());
  assert.ok(editing, 'a failed save must keep the date editor open');
  form = app.renderDialog(editing.props);
  assert.deepEqual(
    dateInputs(form).map((input) => input.props.value),
    ['2026-10-27T09:15', '2026-10-31T16:37'],
  );
  assert.equal(form.props.dirty, true);
  assert.equal(form.props.pending, false);
  assert.match(text(form), /Zapis jest chwilowo niedostępny/);
  app.context.status = 200;
  app.context.response = {
    start_at: '2026-10-27T08:15:00Z',
    start_on: '2026-10-27',
    end_on: '2026-10-31',
    due_at: '2026-10-31T15:37:12.987Z',
  };
  nodes(form)
    .find((node) => node.type === 'form')
    .props.onSubmit({ preventDefault() {} });
  await settle();
  assert.equal(app.requests.length, 2);
  assert.deepEqual(Object.fromEntries(app.requests[0].body), {
    start_at: '2026-10-27T09:15',
    due_at: '2026-10-31T16:37',
    source_start_at: item().start_at,
    source_due_at: item().due_at,
  });
  assert.deepEqual(
    Object.fromEntries(app.requests[1].body),
    Object.fromEntries(app.requests[0].body),
  );
  assert.equal(app.updates.length, 1);
  assert.equal(dialog(app.render()), undefined);
  app.destroy();
});

test('date editor validates the interval, clears dates, and exposes pending state to the modal', async () => {
  const app = harness(),
    saves = [];
  const props = {
    item: item(),
    pending: false,
    error: '',
    onClose() {},
    onSave: async (...values) => saves.push(values),
  };
  let tree = app.renderDialog(props);
  assert.deepEqual(
    dateInputs(tree).map((input) => input.props.value),
    ['2026-10-20T09:15', '2026-10-23T16:37'],
  );
  dateInputs(tree)[0].props.onChange({ target: { value: '2026-10-23T17:00' } });
  tree = app.renderDialog(props);
  assert.equal(button(tree, 'Zapisz daty').props.disabled, true);
  assert.match(text(tree), /nie może być wcześniejszy/);
  for (const input of dateInputs(tree)) {
    assert.equal(input.props['aria-invalid'], true);
    const description = nodes(tree).find(
      (node) => node.props?.id === input.props['aria-describedby'],
    );
    assert.match(text(description), /nie może być wcześniejszy/);
  }
  nodes(tree)
    .find((node) => node.type === 'form')
    .props.onSubmit({ preventDefault() {} });
  assert.deepEqual(saves, []);
  dateInputs(tree)[0].props.onChange({ target: { value: '2026-10-23T09:15' } });
  tree = app.renderDialog(props);
  assert.equal(button(tree, 'Zapisz daty').props.disabled, false);
  assert.ok(dateInputs(tree).every((input) => !input.props['aria-invalid']));
  nodes(tree)
    .find((node) => node.type === 'form')
    .props.onSubmit({ preventDefault() {} });
  assert.deepEqual(saves, [['2026-10-23T09:15', '2026-10-23T16:37']]);
  saves.length = 0;
  button(tree, 'Usuń daty').props.onClick();
  tree = app.renderDialog(props);
  assert.deepEqual(
    dateInputs(tree).map((input) => input.props.value),
    ['', ''],
  );
  assert.equal(tree.props.dirty, true);
  nodes(tree)
    .find((node) => node.type === 'form')
    .props.onSubmit({ preventDefault() {} });
  assert.deepEqual(saves, [['', '']]);
  tree = app.renderDialog({ ...props, pending: true, error: 'Zachowany komunikat' });
  assert.equal(tree.props.pending, true);
  assert.equal(tree.props.dirty, true);
  assert.ok(dateInputs(tree).every((input) => input.props.disabled));
  assert.equal(button(tree, 'Zapisywanie…').props.disabled, true);
  assert.equal(button(tree, 'Anuluj').props.disabled, true);
  assert.equal(button(tree, 'Usuń daty').props.disabled, true);
  assert.match(text(tree), /Zachowany komunikat/);
});

test('observer has no date mutation controls, and keyboard/pointer cannot schedule', async () => {
  const app = harness(item({ editable: false }));
  let tree = app.render();
  assert.equal(byClass(tree, 'work-timeline-handle'), undefined);
  const bar = byClass(tree, 'work-timeline-bar-body'),
    target = pointerTarget();
  bar.props.onKeyDown(keyboard());
  bar.props.onPointerDown(pointer(target, 100));
  bar.props.onPointerMove(pointer(target, 136));
  bar.props.onPointerUp(pointer(target, 136));
  await settle();
  assert.deepEqual(target.captured, []);
  assert.deepEqual(app.requests, []);
  assert.deepEqual(app.updates, []);
  assert.equal(dialog(app.render()), undefined);
  bar.props.onClick();
  assert.deepEqual(app.navigation, [item().url]);
  tree = app.render({
    data: {
      ...app.props.data,
      items: [item({ editable: false, start_on: null, end_on: null, due_at: null })],
    },
  });
  assert.equal(byClass(tree, 'work-timeline-unscheduled').props.disabled, true);
  app.destroy();
});

test('Escape cancels pointer preview, releases capture and suppresses the following click', async () => {
  const app = harness(),
    target = pointerTarget();
  let bar = byClass(app.render(), 'work-timeline-bar-body');
  bar.props.onPointerDown(pointer(target, 100));
  bar.props.onPointerMove(pointer(target, 172));
  assert.ok(byClass(app.render(), 'work-timeline-drag-label'));
  let prevented = false;
  app.listeners.get('keydown')({
    key: 'Escape',
    preventDefault: () => {
      prevented = true;
    },
  });
  bar = byClass(app.render(), 'work-timeline-bar-body');
  bar.props.onPointerUp(pointer(target, 172));
  bar.props.onClick();
  await settle();
  assert.equal(prevented, true);
  assert.deepEqual(target.released, [5]);
  assert.equal(byClass(app.render(), 'work-timeline-drag-label'), undefined);
  assert.equal(dialog(app.render()), undefined);
  assert.match(text(app.render()), /Anulowano zmianę dat/);
  assert.deepEqual(app.requests, []);
  app.destroy();
  assert.equal(app.listeners.has('keydown'), false);
});

test('pointer commit schedules the preview once and pointer cancellation never sends it', async () => {
  const app = harness(),
    target = pointerTarget();
  const bar = byClass(app.render(), 'work-timeline-bar-body');
  bar.props.onPointerDown(pointer(target, 100));
  bar.props.onPointerMove(pointer(target, 172, { pointerId: 9 }));
  assert.equal(byClass(app.render(), 'work-timeline-drag-label'), undefined);
  bar.props.onPointerMove(pointer(target, 172));
  bar.props.onPointerUp(pointer(target, 172));
  bar.props.onPointerUp(pointer(target, 172));
  await settle();
  assert.equal(app.requests.length, 1);
  assert.equal(app.requests[0].body.get('start_on'), '2026-10-22');
  assert.equal(app.requests[0].body.get('end_on'), '2026-10-25');
  const nextBar = byClass(app.render(), 'work-timeline-bar-body');
  nextBar.props.onPointerDown(pointer(target, 100));
  nextBar.props.onPointerMove(pointer(target, 136));
  nextBar.props.onPointerCancel(pointer(target, 136));
  await settle();
  assert.equal(app.requests.length, 1);
  assert.equal(byClass(app.render(), 'work-timeline-drag-label'), undefined);
  app.destroy();
});

test('a response arriving after unmount cannot publish stale dates', async () => {
  const app = harness(),
    gate = deferred();
  app.context.wait = gate.promise;
  byClass(app.render(), 'work-timeline-bar-body').props.onKeyDown(keyboard());
  app.destroy();
  assert.equal(app.requests[0].signal.aborted, true);
  gate.resolve();
  await settle();
  assert.deepEqual(app.updates, []);
});

test('drag accounts for CSS zoom and calendar scrolling before persisting days', async () => {
  const app = harness(),
    target = pointerTarget();
  target.zoom = 2;
  const bar = byClass(app.render(), 'work-timeline-bar-body');
  bar.props.onPointerDown(pointer(target, 100));
  app.viewport.scrollLeft += 36;
  bar.props.onPointerMove(pointer(target, 172));
  bar.props.onPointerUp(pointer(target, 172));
  await settle();
  assert.equal(app.requests.length, 1);
  assert.equal(app.requests[0].body.get('start_on'), '2026-10-22');
  assert.equal(app.requests[0].body.get('end_on'), '2026-10-25');
  app.destroy();
});

test('moving a partial schedule preserves the date that was deliberately left empty', async () => {
  for (const [source, expected] of [
    [item({ start_on: null, start_at: null }), { start_on: '', end_on: '2026-10-24' }],
    [item({ end_on: null, due_at: null }), { start_on: '2026-10-21', end_on: '' }],
  ]) {
    const app = harness(source);
    byClass(app.render(), 'work-timeline-bar-body').props.onKeyDown(keyboard());
    await settle();
    assert.equal(app.requests[0].body.get('start_on'), expected.start_on);
    assert.equal(app.requests[0].body.get('end_on'), expected.end_on);
    assert.equal(app.requests[0].body.get('source_start_at'), source.start_at || '');
    assert.equal(app.requests[0].body.get('source_due_at'), source.due_at || '');
    app.destroy();
  }
});

test('conflict response leaves dates unchanged and offers a refresh of the same filtered page', async () => {
  const app = harness();
  app.context.status = 409;
  app.context.response = { message: 'Daty zostały zmienione. Odśwież oś czasu.' };
  byClass(app.render(), 'work-timeline-bar-body').props.onKeyDown(keyboard());
  await settle();
  const tree = app.render();
  assert.deepEqual(app.updates, []);
  assert.equal(byClass(tree, 'work-timeline-drag-label'), undefined);
  assert.match(text(byClass(tree, 'work-timeline-error')), /Daty zostały zmienione/);
  button(tree, 'Odśwież dane').props.onClick();
  assert.deepEqual(app.navigation, [pageUrl]);
  app.destroy();
});
