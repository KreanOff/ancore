import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import vm from 'node:vm';
import { transform } from 'esbuild';
import ts from 'typescript';

// Run the source callbacks with their component state and HTTP boundaries controlled.
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
    })
  ).code;
}
const schemaCallbacks = await callbacks('tasks/SchemaDialog.tsx', ['save']);
const noteCallbacks = await callbacks('tags/NotesDialog.tsx', [
  'refresh',
  'actionError',
  'retryRefresh',
  'act',
]);
const childCallbacks = await callbacks('tasks/TaskPage.tsx', [
  'refresh',
  'refreshError',
  'retryRefresh',
  'editChild',
  'childSaved',
]);
const autosaveCode = (
  await transform(
    (await readFile(new URL('../src/tasks/useTaskSave.ts', import.meta.url), 'utf8')).replace(
      /^import.*?;\n/gm,
      '',
    ),
    { loader: 'ts', format: 'cjs' },
  )
).code;

function execute(code, context) {
  const module = { exports: {} };
  vm.runInNewContext(code, {
    module,
    exports: module.exports,
    FormData,
    PageError: class PageError extends Error {},
    errorMessage: (error) => error.message,
    ...context,
  });
  return module.exports;
}
function setters(context, names) {
  for (const name of names)
    context['set' + name] = (value) => {
      context[name[0].toLowerCase() + name.slice(1)] = value;
    };
}
function deferred() {
  let resolve;
  const promise = new Promise((done) => (resolve = done));
  return { promise, resolve };
}

function childHarness() {
  class HTMLElement {}
  const trigger = new HTMLElement();
  const requests = [],
    navigations = [],
    context = {
      initial: { api_url: '/api/v1/page/', url: '/space/test/tasks/TS-1/?tab=subtasks' },
      csrfToken: 'token',
      workLogURL: { current: '/space/test/tasks/TS-1/?tab=subtasks' },
      life: { current: new AbortController() },
      actionPending: { current: false },
      dialogReturnFocus: { current: null },
      HTMLElement,
      document: { activeElement: trigger, body: new HTMLElement() },
      childEditor: null,
      saves: 0,
      failAutosave: false,
      failRead: false,
      replyType: 'form',
      auto: {
        synchronize() {},
        save: async () => {
          context.saves++;
          if (context.saveWait) await context.saveWait;
          if (context.autosaveError) throw context.autosaveError;
          return !context.failAutosave;
        },
      },
      pageRequest: async (api, url, token, signal, body) => {
        requests.push({ api, url, token, signal, body });
        if (context.failRead) throw new Error('GET 503');
        return url === context.initial.url
          ? { type: 'space-task', data: { children: [{ title: 'Zmienione podzadanie' }] } }
          : {
              type: context.replyType,
              data: {
                action: url,
                return_url: context.initial.url,
                title: 'Edytuj zadanie',
                form: { fields: [{ name: 'title', value: 'Podzadanie' }] },
              },
            };
      },
      navigate: (url) => navigations.push(url),
    };
  setters(context, ['Busy', 'Error', 'RefreshFailed', 'Data', 'ChildEditor']);
  context.setBusy = (value) => {
    context.busy = value;
    if (value) context.document.activeElement = context.document.body;
  };
  const item = {
    key: 'TS-2',
    title: 'Podzadanie',
    editable: true,
    edit_url: '/space/test/items/2/edit/',
  };
  return { context, requests, navigations, item, trigger, ...execute(childCallbacks, context) };
}

test('opening a subtask waits for parent autosave and blocks a second editor request', async () => {
  const app = childHarness(),
    saving = deferred();
  app.context.saveWait = saving.promise;
  const first = app.editChild(app.item);
  await app.editChild({ ...app.item, key: 'TS-3', edit_url: '/space/test/items/3/edit/' });
  assert.equal(app.context.saves, 1);
  assert.equal(app.requests.length, 0);
  assert.equal(app.context.busy, true);
  assert.equal(app.context.document.activeElement, app.context.document.body);
  assert.equal(app.context.dialogReturnFocus.current, app.trigger);
  saving.resolve();
  await first;
  assert.equal(app.requests.length, 1);
  assert.equal(app.requests[0].url, app.item.edit_url);
  assert.equal(app.requests[0].api, app.context.initial.api_url);
  assert.equal(app.requests[0].token, 'token');
  assert.equal(app.requests[0].signal, app.context.life.current.signal);
  assert.equal(app.requests[0].body, undefined);
  assert.equal(app.context.childEditor.action, app.item.edit_url);
  assert.equal(app.context.childEditor.title, 'Edytuj podzadanie TS-2');
  assert.equal(app.context.childEditor.form.fields[0].value, 'Podzadanie');
  assert.equal(app.context.busy, false);
  assert.equal(
    app.context.dialogReturnFocus.current,
    app.trigger,
    'autosave, loading and rejected overlapping opens retain the original return target',
  );
  assert.deepEqual(app.navigations, []);
});

test('a read-only subtask does not save its parent or request an editor', async () => {
  const app = childHarness();
  await app.editChild({ ...app.item, editable: false });
  assert.equal(app.context.saves, 0);
  assert.equal(app.requests.length, 0);
  assert.equal(app.context.childEditor, null);
});

test('a failed parent autosave keeps the subtask closed and permits a later retry', async () => {
  const app = childHarness();
  app.context.failAutosave = true;
  await app.editChild(app.item);
  assert.equal(app.requests.length, 0);
  assert.equal(app.context.childEditor, null);
  assert.equal(app.context.busy, false);
  app.context.failAutosave = false;
  app.context.autosaveError = new Error('Zapis niedostępny');
  await app.editChild(app.item);
  assert.equal(app.requests.length, 0);
  assert.equal(app.context.error, 'Zapis niedostępny');
  assert.equal(app.context.busy, false);
  app.context.autosaveError = null;
  await app.editChild(app.item);
  assert.equal(app.requests.length, 1);
  assert.equal(app.context.error, '');
  assert.equal(app.context.childEditor.action, app.item.edit_url);
});

test('a failed or invalid subtask response shows an error and permits reopening', async () => {
  const app = childHarness();
  app.context.failRead = true;
  await app.editChild(app.item);
  assert.equal(app.context.childEditor, null);
  assert.equal(app.context.error, 'GET 503');
  assert.equal(app.context.busy, false);
  app.context.failRead = false;
  app.context.replyType = 'space-task';
  await app.editChild(app.item);
  assert.equal(app.context.childEditor, null);
  assert.equal(app.context.error, 'Nie udało się otworzyć edycji podzadania.');
  app.context.replyType = 'form';
  await app.editChild(app.item);
  assert.equal(app.context.childEditor.action, app.item.edit_url);
  assert.equal(app.context.error, '');
  assert.deepEqual(app.navigations, []);
});

test('a saved subtask closes its editor and refreshes the parent without navigation', async () => {
  const app = childHarness();
  await app.editChild(app.item);
  app.context.failRead = true;
  await app.childSaved('/space/test/tasks/TS-2/');
  assert.equal(app.context.childEditor, null);
  assert.equal(app.context.refreshFailed, true);
  assert.match(app.context.error, /^Zapisano zmiany.*GET 503$/);
  assert.equal(app.requests[1].url, app.context.initial.url);
  await app.retryRefresh();
  app.context.failRead = false;
  await app.retryRefresh();
  assert.deepEqual(
    app.requests.slice(1).map((request) => request.url),
    [app.context.initial.url, app.context.initial.url, app.context.initial.url],
  );
  assert.ok(app.requests.every((request) => request.body === undefined));
  assert.equal(app.context.saves, 1, 'refresh retries must not resubmit the parent');
  assert.equal(app.context.refreshFailed, false);
  assert.equal(app.context.error, '');
  assert.equal(app.context.data.children[0].title, 'Zmienione podzadanie');
  assert.equal(app.context.busy, false);
  assert.deepEqual(app.navigations, []);
});

function schemaHarness(kind) {
  const requests = [],
    context = {
      dialog: { kind, action: kind === 'subtask' ? 'add_subtask' : 'add_work_log', url: '/task/' },
      api: '/api/',
      csrfToken: 'token',
      form: { current: null },
      life: { current: new AbortController() },
      sending: { current: false },
      committed: { current: false },
      dirty: true,
      saved: false,
      closed: 0,
      failPost: false,
      failRefresh: true,
      pageRequest: async (_api, _url, _token, _signal, body) => {
        requests.push(body);
        if (context.postWait) await context.postWait;
        if (context.failPost) throw new Error('POST 503');
      },
      onSaved: async () => {
        requests.push('GET');
        if (context.failRefresh) throw new Error('GET 503');
      },
      onClose: () => context.closed++,
      // Form data is read only for a mutation, never for a refresh retry.
      FormData: class extends FormData {
        constructor() {
          super();
          this.set('title', 'Szkic');
        }
      },
    };
  setters(context, ['Pending', 'Error', 'Saved', 'Dirty', 'Schema']);
  return { context, requests, ...execute(schemaCallbacks, context) };
}

for (const kind of ['subtask', 'log']) {
  test(`${kind} dialog retries only refresh after its mutation committed`, async () => {
    const app = schemaHarness(kind),
      event = { preventDefault() {} };
    await app.save(event);
    assert.equal(app.requests.length, 2);
    assert.equal(app.requests[0].get('action'), app.context.dialog.action);
    assert.equal(app.context.saved, true);
    assert.equal(app.context.dirty, false);
    assert.match(app.context.error, /^Zapisano zmiany.*GET 503$/);
    await app.save(event);
    assert.deepEqual(app.requests.slice(1), ['GET', 'GET']);
    assert.equal(app.context.closed, 0);
    app.context.failRefresh = false;
    await app.save(event);
    assert.deepEqual(app.requests.slice(1), ['GET', 'GET', 'GET']);
    assert.equal(app.context.closed, 1);
  });
}

test('dialog failed POST preserves its draft and concurrent submits cannot repeat it', async () => {
  const app = schemaHarness('subtask'),
    post = deferred(),
    event = { preventDefault() {} };
  app.context.failPost = true;
  app.context.postWait = post.promise;
  const first = app.save(event);
  await app.save(event);
  assert.equal(app.requests.length, 1);
  post.resolve();
  await first;
  assert.equal(app.context.saved, false);
  assert.equal(app.context.dirty, true);
  assert.equal(app.context.closed, 0);
  assert.equal(app.context.error, 'POST 503');
  app.context.failPost = false;
  app.context.failRefresh = false;
  await app.save(event);
  assert.equal(app.requests.length, 3);
  assert.equal(app.context.closed, 1);
});

function notesHarness() {
  const requests = [],
    context = {
      tag: { id: 1 },
      initial: { api_url: '/api/', url: '/tags/' },
      csrfToken: 'token',
      life: { current: new AbortController() },
      pending: { current: false },
      refreshUrl: { current: null },
      message: 'Nowa notatka',
      editing: 3,
      draft: 'Zmieniona notatka',
      failPost: false,
      failRefresh: true,
      updates: [],
      updated: (data) => context.updates.push(data),
      pageRequest: async (_api, url, _token, _signal, body) => {
        requests.push({ method: body ? 'POST' : 'GET', url, body });
        if (body && context.failPost) throw new Error('POST 503');
        if (!body && context.failRefresh) throw new Error('GET 503');
        return body ? { redirect: '/tags/?page=2' } : { data: { notes: ['Zapisana notatka'] } };
      },
    };
  setters(context, ['Busy', 'Error', 'RefreshFailed', 'Message', 'Editing']);
  return { context, requests, ...execute(noteCallbacks, context) };
}

for (const action of ['add_tag_note', 'edit_tag_note', 'delete_tag_note']) {
  test(`${action} commits once and can retry its read repeatedly`, async () => {
    const app = notesHarness(),
      values = { note_id: '3', message: 'Treść' };
    await app.act(action, values);
    assert.deepEqual(
      app.requests.map((row) => row.method),
      ['POST', 'GET'],
    );
    assert.equal(app.context.refreshFailed, true);
    if (action === 'add_tag_note') assert.equal(app.context.message, '');
    if (action === 'edit_tag_note') assert.equal(app.context.editing, null);
    await app.act(action, values);
    assert.equal(app.requests.length, 2, 'stale mutation controls must stay blocked');
    await app.retryRefresh();
    assert.deepEqual(
      app.requests.map((row) => row.method),
      ['POST', 'GET', 'GET'],
    );
    app.context.failRefresh = false;
    await app.retryRefresh();
    assert.deepEqual(
      app.requests.map((row) => row.method),
      ['POST', 'GET', 'GET', 'GET'],
    );
    assert.equal(app.requests[3].url, '/tags/?page=2');
    assert.equal(app.context.refreshFailed, false);
    assert.equal(app.context.error, '');
    assert.equal(app.context.updates.length, 1);
    await app.retryRefresh();
    assert.equal(app.requests.length, 4);
  });
}

test('failed note POST preserves compose and edit drafts for a real retry', async () => {
  const app = notesHarness();
  app.context.failPost = true;
  await app.act('add_tag_note', { message: 'Nowa notatka' });
  assert.equal(app.context.message, 'Nowa notatka');
  assert.equal(app.context.editing, 3);
  assert.equal(app.context.draft, 'Zmieniona notatka');
  assert.equal(app.context.refreshFailed, false);
  assert.equal(app.requests.length, 1);
  app.context.failPost = false;
  app.context.failRefresh = false;
  await app.act('add_tag_note', { message: 'Nowa notatka' });
  assert.deepEqual(
    app.requests.map((row) => row.method),
    ['POST', 'POST', 'GET'],
  );
  assert.equal(app.context.message, '');
});

function autosaveHarness({ inBacklog = false, canEdit = true } = {}) {
  const states = [],
    listeners = {},
    requests = [],
    inputs = new Map(),
    fileInput = { value: 'wybrany plik' },
    controls = {
      failPost: false,
      failRefresh: true,
      updates: [],
      status: 'new',
      inBacklog,
      statuses: [
        { key: 'new', category: 'new' },
        { key: 'in_progress', category: 'in_progress' },
        { key: 'closed', category: 'closed' },
        { key: 'delivered', category: 'closed' },
      ],
    },
    savedItem = { status: 'new', in_backlog: inBacklog };
  const transitions = (status) =>
    controls.statuses.filter((row) =>
      (
        ({ new: ['in_progress'], in_progress: ['closed'], closed: ['in_progress'] })[status] ?? []
      ).includes(row.key),
    );
  class Input {
    constructor(name) {
      this.name = name;
      this.type = name === 'files' ? 'file' : 'text';
      this.value = controls.title || 'Nowy tytuł';
    }
  }
  const context = {
    useState(initial) {
      const index = states.length;
      states.push(typeof initial === 'function' ? initial() : initial);
      return [states[index], (value) => (states[index] = value)];
    },
    useRef: (initial) => ({ current: initial }),
    useEffect: (callback) => callback(),
    AbortController,
    Map,
    Set,
    FormData: class extends FormData {
      constructor(form) {
        super();
        if (form) {
          this.set('title', controls.title || 'Nowy tytuł');
          this.set('status', controls.status);
          if (controls.inBacklog) this.set('in_backlog', 'on');
          this.set('files', new File(['Treść'], 'notatka.txt'));
        }
      }
    },
    HTMLInputElement: Input,
    HTMLTextAreaElement: class extends Input {},
    HTMLSelectElement: class extends Input {},
    setTimeout: () => 1,
    clearTimeout() {},
    document: { addEventListener() {}, removeEventListener() {} },
    window: { addEventListener() {}, removeEventListener() {} },
    pageRequest: async (_api, _url, _token, _signal, body) => {
      requests.push(body || 'GET');
      if (body && controls.postWait) await controls.postWait;
      if (body && controls.failPost) throw new Error('POST 503');
      if (
        body?.has('source_status') &&
        (body.get('source_status') !== savedItem.status ||
          body.get('source_in_backlog') !== String(savedItem.in_backlog))
      )
        throw new Error('Nieaktualne położenie zadania');
      if (body?.has('status')) savedItem.status = body.get('status');
      if (body && JSON.parse(body.get('autosave_fields')).includes('in_backlog'))
        savedItem.in_backlog = body.get('in_backlog') === 'on';
      if (
        body?.has('status') &&
        controls.statuses.find((status) => status.key === savedItem.status)?.category === 'closed'
      )
        savedItem.in_backlog = false;
      if (body) return { redirect: '/task/' };
      if (!body && controls.failRefresh) throw new Error('GET 503');
      return {
        data: {
          title: controls.title || 'Nowy tytuł',
          item: { ...savedItem, transitions: transitions(savedItem.status) },
          statuses: controls.statuses,
          can_edit: canEdit,
        },
      };
    },
  };
  const form = {
    current: {
      addEventListener: (name, callback) => (listeners[name] = callback),
      removeEventListener() {},
      querySelector: () => fileInput,
    },
  };
  const hook = execute(autosaveCode, context).useTaskSave(
    form,
    {
      initial: {
        data: {
          item: { ...savedItem, transitions: transitions(savedItem.status) },
          statuses: controls.statuses,
          form: {
            fields: [
              { name: 'title', errors: [] },
              { name: 'in_backlog', errors: [] },
            ],
          },
          can_edit: canEdit,
          error: '',
        },
        api_url: '/api/',
        url: '/task/',
      },
      csrfToken: 'token',
    },
    (data) => controls.updates.push(data),
    () => {},
  );
  function input(name) {
    if (!inputs.has(name)) inputs.set(name, new Input(name));
    const element = inputs.get(name);
    element.value = name === 'status' ? controls.status : controls.title || 'Nowy tytuł';
    return element;
  }
  return {
    hook,
    controls,
    states,
    requests,
    fileInput,
    savedItem,
    change: (name) => listeners.input({ target: input(name) }),
    blur: (name) => listeners.change({ target: input(name) }),
  };
}

test('task transitions reject skipped stages and read-only changes before sending', async () => {
  const app = autosaveHarness();
  assert.equal(await app.hook.changeStatus('closed'), false);
  assert.equal(app.requests.length, 0);
  const readOnly = autosaveHarness({ canEdit: false });
  assert.equal(await readOnly.hook.changeStatus('in_progress'), false);
  assert.equal(readOnly.requests.length, 0);
});

test('a transition saves the selected stage with an existing draft and blocks duplicate clicks', async () => {
  const app = autosaveHarness(),
    post = deferred();
  app.controls.failRefresh = false;
  app.controls.postWait = post.promise;
  app.change('title');
  const first = app.hook.changeStatus('in_progress');
  assert.equal(await app.hook.changeStatus('in_progress'), false);
  assert.equal(app.requests.length, 1);
  assert.equal(app.requests[0].get('title'), 'Nowy tytuł');
  assert.equal(app.requests[0].get('status'), 'in_progress');
  assert.equal(app.requests[0].get('source_status'), 'new');
  assert.deepEqual(JSON.parse(app.requests[0].get('autosave_fields')), ['title', 'status']);
  assert.equal(app.controls.updates.length, 0, 'the visible stage changes only after confirmation');
  post.resolve();
  assert.equal(await first, true);
  assert.equal(app.controls.updates[0].item.status, 'in_progress');
  assert.equal(
    await app.hook.changeStatus('closed'),
    true,
    'the next stage uses refreshed transitions',
  );
  assert.equal(app.requests[2].get('source_status'), 'in_progress');
});

test('a rejected transition preserves its target and other edits for retry', async () => {
  const app = autosaveHarness();
  app.controls.failPost = true;
  app.change('title');
  assert.equal(await app.hook.changeStatus('in_progress'), false);
  assert.equal(app.controls.updates.length, 0);
  app.controls.failPost = false;
  app.controls.failRefresh = false;
  assert.equal(await app.hook.save(), true);
  assert.equal(app.requests[1].get('status'), 'in_progress');
  assert.equal(app.requests[1].get('title'), 'Nowy tytuł');
  assert.equal(app.requests[1].get('source_status'), 'new');
});

test('a committed transition blocks further stages until a failed refresh is retried', async () => {
  const app = autosaveHarness();
  assert.equal(await app.hook.changeStatus('in_progress'), false);
  assert.equal(await app.hook.changeStatus('in_progress'), false);
  assert.equal(app.requests.length, 2);
  app.controls.failRefresh = false;
  assert.equal(await app.hook.save(), true);
  assert.deepEqual(app.requests.slice(1), ['GET', 'GET']);
  assert.equal(await app.hook.changeStatus('closed'), true);
  assert.equal(app.requests[3].get('source_status'), 'in_progress');
});

test('an external task refresh synchronizes transition targets, permissions and source snapshots', async () => {
  const app = autosaveHarness();
  app.controls.failRefresh = false;
  app.savedItem.status = 'closed';
  app.hook.synchronize({
    item: { ...app.savedItem, transitions: [{ key: 'in_progress' }] },
    statuses: app.controls.statuses,
    can_edit: true,
  });
  assert.equal(await app.hook.changeStatus('in_progress'), true);
  assert.equal(app.requests[0].get('source_status'), 'closed');
  app.hook.synchronize({
    item: { ...app.savedItem, transitions: [{ key: 'closed' }] },
    statuses: app.controls.statuses,
    can_edit: false,
  });
  assert.equal(await app.hook.changeStatus('closed'), false);
  assert.equal(app.requests.length, 2);
});

test('blurring an unchanged text field after a committed autosave retries only GET', async () => {
  const app = autosaveHarness();
  app.change('title');
  assert.equal(await app.hook.save(), false);
  assert.equal(app.requests.length, 2);
  app.blur('title');
  assert.equal(app.states[1], false, 'blur must not mark committed text dirty again');
  app.controls.failRefresh = false;
  assert.equal(await app.hook.save(), true);
  assert.deepEqual(app.requests.slice(1), ['GET', 'GET']);
  assert.equal(app.states[2], '');
});

test('task autosave retries only GET after a committed upload and clears stale errors', async () => {
  const app = autosaveHarness();
  app.change('title');
  app.change('files');
  assert.equal(await app.hook.save(), false);
  assert.equal(app.requests.length, 2);
  assert.equal(app.requests[0].get('files').name, 'notatka.txt');
  assert.equal(app.fileInput.value, '');
  assert.equal(app.states[1], false, 'committed fields are no longer dirty');
  assert.match(app.states[2], /^Zapisano zmiany.*GET 503$/);
  assert.equal(await app.hook.save(), false);
  assert.deepEqual(app.requests.slice(1), ['GET', 'GET']);
  app.controls.failRefresh = false;
  assert.equal(await app.hook.save(), true);
  assert.deepEqual(app.requests.slice(1), ['GET', 'GET', 'GET']);
  assert.equal(app.states[0], false);
  assert.equal(app.states[1], false);
  assert.equal(app.states[2], '');
  assert.equal(app.states[4], 'Zapisano zmiany.');
  assert.equal(app.controls.updates.length, 1);
  assert.equal(await app.hook.save(), true);
  assert.equal(app.requests.length, 4);
});

test('failed task autosave keeps fields and files for retry', async () => {
  const app = autosaveHarness();
  app.controls.failPost = true;
  app.change('title');
  app.change('files');
  assert.equal(await app.hook.save(), false);
  assert.equal(app.states[1], true);
  assert.equal(app.fileInput.value, 'wybrany plik');
  assert.equal(app.requests.length, 1);
  app.blur('title');
  assert.equal(app.states[1], true, 'an unchanged blur must preserve a failed draft');
  app.controls.failPost = false;
  app.controls.failRefresh = false;
  assert.equal(await app.hook.save(), true);
  assert.equal(app.requests.length, 3);
  assert.equal(app.requests[1].get('title'), 'Nowy tytuł');
  assert.equal(app.requests[1].get('files').name, 'notatka.txt');
  assert.equal(app.states[1], false);
});

test('edits made during a committed autosave survive a failed refresh and save on retry', async () => {
  const app = autosaveHarness(),
    post = deferred();
  app.change('title');
  app.change('files');
  app.controls.postWait = post.promise;
  const first = app.hook.save();
  app.controls.title = 'Nowszy tytuł';
  app.change('title');
  const overlapping = app.hook.save();
  post.resolve();
  assert.equal(await first, false);
  assert.equal(await overlapping, false);
  assert.equal(app.requests.length, 2);
  assert.equal(app.states[1], true);
  app.controls.failRefresh = false;
  assert.equal(await app.hook.save(), true);
  assert.equal(app.requests.length, 4);
  assert.equal(app.requests[0].get('title'), 'Nowy tytuł');
  assert.equal(app.requests[0].get('files').name, 'notatka.txt');
  assert.equal(app.requests[2].get('title'), 'Nowszy tytuł');
  assert.equal(
    app.requests[2].get('files'),
    null,
    'a newer edit must not upload committed files again',
  );
  assert.equal(app.states[1], false);
});

test('workflow autosave sends the last committed state even after a failed refresh', async () => {
  const app = autosaveHarness();
  app.controls.status = 'in_progress';
  app.change('status');
  assert.equal(await app.hook.save(), false);
  assert.equal(app.requests[0].get('source_status'), 'new');
  assert.equal(app.requests[0].get('source_in_backlog'), 'false');
  app.controls.status = 'closed';
  app.change('status');
  app.controls.failRefresh = false;
  assert.equal(await app.hook.save(), true);
  assert.equal(app.requests[2].get('source_status'), 'in_progress');
  assert.equal(app.requests[2].get('status'), 'closed');
});

test('rejected workflow autosave preserves its original concurrency snapshot on retry', async () => {
  const app = autosaveHarness();
  app.controls.status = 'in_progress';
  app.controls.failPost = true;
  app.change('status');
  assert.equal(await app.hook.save(), false);
  app.controls.failPost = false;
  app.controls.failRefresh = false;
  assert.equal(await app.hook.save(), true);
  assert.equal(app.requests[1].get('source_status'), 'new');
  assert.equal(app.requests[1].get('source_in_backlog'), 'false');
});

for (const status of ['closed', 'delivered']) {
  test(`closing backlog work as ${status} preserves the server placement after GET fails`, async () => {
    const app = autosaveHarness({ inBacklog: true });
    app.controls.status = status;
    app.change('status');
    assert.equal(await app.hook.save(), false);
    assert.equal(app.requests[0].get('source_in_backlog'), 'true');
    assert.match(app.states[2], /^Zapisano zmiany.*GET 503$/);
    // The failed GET leaves the old checkbox checked, but the server moved work to the board.
    assert.equal(app.controls.inBacklog, true);
    app.controls.status = 'in_progress';
    app.change('status');
    app.controls.failRefresh = false;
    assert.equal(await app.hook.save(), true);
    assert.equal(app.requests[2].get('source_status'), status);
    assert.equal(app.requests[2].get('source_in_backlog'), 'false');
    assert.equal(app.controls.updates[0].item.in_backlog, false);
  });
}
