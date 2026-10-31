import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import { build, transform } from 'esbuild';
import ts from 'typescript';

const helpers = await build({
  entryPoints: [new URL('../src/spaces/configuration-form.ts', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  write: false,
});
function execute(code, context = {}) {
  const module = { exports: {} };
  if (!context.FormData) context.FormData = FormData;
  Object.assign(context, { module, exports: module.exports });
  vm.runInNewContext(code, context);
  return module.exports;
}
const {
  configurationSubmission,
  configurationEditorSchema,
  configurationHasRow,
  configurationFieldName,
} = execute(helpers.outputFiles[0].text);
const tableBundle = await build({
  entryPoints: [new URL('../src/spaces/ConfigurationTable.tsx', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  jsx: 'automatic',
  external: ['react', 'react/jsx-runtime'],
  write: false,
});
const require = createRequire(import.meta.url);
const ConfigurationTable = execute(tableBundle.outputFiles[0].text, {
  require: (name) =>
    name === 'react'
      ? {
          ...require(name),
          useState: (initial) => [initial, () => {}],
          useRef: () => ({ current: null }),
          useLayoutEffect: () => {},
        }
      : require(name),
}).default;
const schema = (fields, overrides = {}) => ({ fields, errors: [], bound: false, ...overrides });
function field(name, value, overrides = {}) {
  return {
    name,
    field_name: name.split('-').pop(),
    id: 'id_' + name,
    label: name,
    type: 'text',
    value,
    hidden: false,
    checked: false,
    required: false,
    disabled: false,
    errors: [],
    attrs: {},
    help_text: '',
    ...overrides,
  };
}
function row(group, index, key, extra = []) {
  const prefix = `${group}-${index}-`;
  return schema([
    field(prefix + 'key', key),
    field(prefix + 'label', key ? `Nazwa ${key}` : ''),
    ...extra.map(([name, value, attrs]) => field(prefix + name, value, attrs)),
    field(prefix + 'DELETE', null, { type: 'checkbox' }),
  ]);
}

test('type table renders the configured and default icons from Django single-select arrays', () => {
  const choices = [
    { value: '', label: 'Domyślna dla typu', icon: 'square-check' },
    { value: 'rocket', label: 'Wdrożenie', icon: 'rocket' },
  ];
  for (const [value, expected, label] of [
    [[''], 'square-check', 'Domyślna dla typu'],
    [['rocket'], 'rocket', 'Wdrożenie'],
    ['rocket', 'rocket', 'Wdrożenie'],
    [null, 'square-check', 'Domyślna dla typu'],
  ]) {
    const table = ConfigurationTable({
      group: {
        key: 'types',
        title: 'Typy zgłoszeń',
        forms: [row('types', 0, 'task', [['icon', value, { type: 'select', choices }]])],
      },
      pending: false,
    });
    const cells = [];
    function visit(element) {
      if (Array.isArray(element)) return element.forEach(visit);
      if (!element?.props) return;
      if (element.props['data-column'] === 'icon' && element.props.role === 'cell')
        cells.push(element);
      visit(element.props.children);
    }
    visit(table);
    assert.equal(cells.length, 1);
    assert.equal(cells[0].props.children.props.children.props.name, expected);
    assert.equal(cells[0].props.title, label);
  }
});
function fixture() {
  const groups = {
    statuses: [
      row('statuses', 0, 'new', [
        ['category', 'new', { type: 'select' }],
        ['transitions', ['done', 'new'], { type: 'select', multiple: true }],
      ]),
      row('statuses', 1, 'done', [
        ['category', 'closed', { type: 'select' }],
        ['transitions', ['new'], { type: 'select', multiple: true }],
      ]),
      row('statuses', 2, '', [
        ['category', 'new', { type: 'select' }],
        ['transitions', [], { type: 'select', multiple: true }],
      ]),
    ],
    types: [
      row('types', 0, 'task', [
        ['icon', 'square-check', { type: 'select' }],
        ['description', 'Praca do wykonania', { type: 'textarea' }],
      ]),
      row('types', 1, 'bug', [
        ['icon', 'circle-alert', { type: 'select' }],
        ['description', 'Problem do naprawienia', { type: 'textarea' }],
      ]),
      row('types', 2, '', [
        ['icon', '', { type: 'select' }],
        ['description', '', { type: 'textarea' }],
      ]),
    ],
    fields: [
      row('fields', 0, 'estimate', [
        ['type', 'number', { type: 'select' }],
        ['required', null, { type: 'checkbox', checked: true }],
      ]),
      row('fields', 1, 'notes', [
        ['type', 'text', { type: 'select' }],
        ['required', null, { type: 'checkbox' }],
      ]),
      row('fields', 2, '', [
        ['type', 'text', { type: 'select' }],
        ['required', null, { type: 'checkbox' }],
      ]),
    ],
  };
  return {
    name: 'Konfiguracja',
    space_url: '/workplaces/w_test/space/test/',
    revision: 'revision-1',
    shared: true,
    spaces_count: 2,
    errors: [],
    sets: Object.entries(groups).map(([key, forms]) => ({
      key,
      title: key,
      errors: [],
      management: schema([
        field(key + '-TOTAL_FORMS', '3', { hidden: true }),
        field(key + '-INITIAL_FORMS', '2', { hidden: true }),
      ]),
      forms,
    })),
  };
}
function draft(entries) {
  const values = new FormData();
  for (const [name, value] of entries) values.append(name, value);
  return values;
}
function rowDraft(data, section, index) {
  return draft(
    data.sets
      .find((group) => group.key === section)
      .forms[
        index
      ].fields.flatMap((entry) => (entry.type === 'checkbox' ? (entry.checked ? [[entry.name, entry.value || 'on']] : []) : Array.isArray(entry.value) ? entry.value.map((value) => [entry.name, value]) : [[entry.name, entry.value || '']])),
  );
}

test('editing one row retains revision, every formset and unrelated multiple or Boolean values', () => {
  const data = fixture();
  const before = JSON.stringify(data);
  const values = configurationSubmission(
    data,
    { section: 'types', index: 1 },
    draft([
      ['types-1-key', 'bug'],
      ['types-1-label', 'Błąd poprawiony'],
      ['types-1-icon', 'siren'],
      ['types-1-description', 'Awaria wymagająca reakcji'],
      ['statuses-0-key', 'ignored'],
      ['revision', 'ignored'],
    ]),
  );
  assert.equal(values.get('revision'), 'revision-1');
  assert.equal(values.get('configuration_section'), 'types');
  assert.equal(values.get('configuration_index'), '1');
  for (const group of data.sets) {
    assert.equal(values.get(`${group.key}-TOTAL_FORMS`), '3');
    assert.equal(values.get(`${group.key}-INITIAL_FORMS`), '2');
  }
  assert.equal(values.get('types-0-key'), 'task');
  assert.equal(values.get('types-1-label'), 'Błąd poprawiony');
  assert.equal(values.get('types-1-icon'), 'siren');
  assert.equal(values.get('types-1-description'), 'Awaria wymagająca reakcji');
  assert.equal(values.get('types-0-icon'), 'square-check');
  assert.equal(values.get('types-0-description'), 'Praca do wykonania');
  assert.equal(values.get('statuses-0-key'), 'new');
  assert.deepEqual(values.getAll('statuses-0-transitions'), ['done', 'new']);
  assert.equal(values.get('fields-0-required'), 'on');
  assert.equal(values.has('fields-1-required'), false);
  assert.equal(values.has('types-1-DELETE'), false);
  assert.equal(JSON.stringify(data), before);
});

test('adding overlays the existing blank row without changing form counts or saved keys', () => {
  const data = fixture();
  const values = configurationSubmission(
    data,
    { section: 'fields', index: 2 },
    draft([
      ['fields-2-key', 'deadline'],
      ['fields-2-label', 'Termin'],
      ['fields-2-type', 'date'],
      ['fields-2-required', 'on'],
    ]),
  );
  assert.equal(values.get('fields-TOTAL_FORMS'), '3');
  assert.equal(values.get('fields-INITIAL_FORMS'), '2');
  assert.equal(values.get('fields-2-key'), 'deadline');
  assert.equal(values.get('fields-2-required'), 'on');
  assert.equal(values.get('fields-0-key'), 'estimate');
  assert.equal(values.get('fields-1-key'), 'notes');
  assert.equal(values.get('types-2-key'), '');
});

test('unchecked checkbox and cleared multiple select remove their previous submitted values', () => {
  const data = fixture();
  const fieldDraft = rowDraft(data, 'fields', 0);
  fieldDraft.delete('fields-0-required');
  const fields = configurationSubmission(data, { section: 'fields', index: 0 }, fieldDraft);
  assert.equal(fields.has('fields-0-required'), false);
  assert.equal(fields.get('fields-0-type'), 'number');
  const statusDraft = rowDraft(data, 'statuses', 0);
  statusDraft.delete('statuses-0-transitions');
  const statuses = configurationSubmission(data, { section: 'statuses', index: 0 }, statusDraft);
  assert.deepEqual(statuses.getAll('statuses-0-transitions'), []);
  assert.deepEqual(statuses.getAll('statuses-1-transitions'), ['new']);
});

test('resetting the icon and clearing the description submit explicit empty values', () => {
  const data = fixture();
  const edited = rowDraft(data, 'types', 1);
  edited.set('types-1-icon', '');
  edited.set('types-1-description', '');
  const values = configurationSubmission(data, { section: 'types', index: 1 }, edited);
  assert.equal(values.get('types-1-icon'), '');
  assert.equal(values.get('types-1-description'), '');
  assert.equal(values.get('types-0-icon'), 'square-check');
  assert.equal(values.get('types-0-description'), 'Praca do wykonania');
  const editor = configurationEditorSchema(data.sets[1].forms[1]);
  assert.equal(
    editor.fields.find((entry) => configurationFieldName(entry) === 'icon').required,
    false,
  );
  assert.equal(
    editor.fields.find((entry) => configurationFieldName(entry) === 'description').required,
    false,
  );
});

test('deletion marks only the selected row and preserves every saved key and configuration value', () => {
  const data = fixture();
  const values = configurationSubmission(
    data,
    { section: 'types', index: 0, remove: true },
    draft([['types-0-key', 'ignored']]),
  );
  assert.equal(values.get('configuration_remove'), '1');
  assert.equal(values.get('types-0-DELETE'), 'on');
  assert.equal(values.has('types-1-DELETE'), false);
  assert.equal(values.get('types-0-key'), 'task');
  assert.equal(values.get('types-1-key'), 'bug');
  assert.deepEqual(values.getAll('statuses-0-transitions'), ['done', 'new']);
  assert.equal(values.get('fields-0-required'), 'on');
});

test('unavailable rows and unsupported deletions fail before submission', () => {
  const data = fixture();
  assert.throws(
    () => configurationSubmission(data, { section: 'types', index: 99 }, new FormData()),
    /Pozycja konfiguracji jest niedostępna/,
  );
  data.sets[1].forms[0].fields.pop();
  assert.throws(
    () =>
      configurationSubmission(data, { section: 'types', index: 0, remove: true }, new FormData()),
    /Nie można usunąć/,
  );
});

test('dialog schema retains values and errors while requiring row fields and omitting deletion', () => {
  const data = fixture();
  const source = data.sets[0].forms[2];
  source.fields[0].errors = ['Nieprawidłowy klucz'];
  const edited = configurationEditorSchema(source);
  assert.equal(configurationHasRow(source), false);
  assert.equal(configurationHasRow(data.sets[0].forms[0]), true);
  assert.equal(
    edited.fields.some((entry) => configurationFieldName(entry) === 'DELETE'),
    false,
  );
  assert.equal(
    edited.fields.find((entry) => configurationFieldName(entry) === 'key').required,
    true,
  );
  assert.equal(
    edited.fields.find((entry) => configurationFieldName(entry) === 'category').required,
    true,
  );
  assert.equal(
    edited.fields.find((entry) => configurationFieldName(entry) === 'transitions').required,
    false,
  );
  assert.equal(edited.fields[0].errors[0], 'Nieprawidłowy klucz');
  assert.equal(source.fields[0].required, false);
});

// Exercise the real modal callbacks with controlled state and HTTP boundaries.
const source = ts.createSourceFile(
  'ConfigurationPage.tsx',
  await readFile(new URL('../src/spaces/ConfigurationPage.tsx', import.meta.url), 'utf8'),
  ts.ScriptTarget.Latest,
  true,
  ts.ScriptKind.TSX,
);
const names = ['createEditor', 'focusError', 'closeEditor', 'refresh', 'open', 'save'];
const callbacks = new Map();
function visit(node) {
  if (ts.isFunctionDeclaration(node) && names.includes(node.name?.text))
    callbacks.set(node.name.text, node.getText());
  ts.forEachChild(node, visit);
}
visit(source);
assert.equal(callbacks.size, names.length);
const callbackCode = (
  await transform([...callbacks.values()].join('\n') + `\nexport { ${names.join(', ')} };`, {
    loader: 'tsx',
    format: 'cjs',
  })
).code;
class PageError extends Error {
  constructor(data) {
    super('Błąd walidacji');
    this.data = data;
  }
}
class DialogFormData extends FormData {
  constructor(form) {
    super();
    if (form) for (const [name, value] of form.values) this.append(name, value);
  }
}
function harness(data = fixture()) {
  const requests = [];
  const context = {
    data,
    initial: { api_url: '/workplaces/w_test/api/v1/page/' },
    csrfToken: 'token',
    life: new AbortController(),
    sending: { current: false },
    editor: null,
    error: '',
    refreshError: '',
    pending: false,
    reads: 0,
    focused: 0,
    form: {
      current: {
        values: rowDraft(data, 'types', 1),
        reportValidity: () => true,
        querySelector: () => ({
          closest: () => null,
          focus: () => context.focused++,
          scrollIntoView() {},
        }),
      },
    },
    FormData: DialogFormData,
    PageError,
    configurationSubmission,
    configurationEditorSchema,
    configurationHasRow,
    flushSync: (callback) => callback(),
    requestAnimationFrame: (callback) => callback(),
    errorMessage: (error) => error.message,
    pageRequest: async (...args) => {
      requests.push(args);
      if (args[4] === undefined) {
        if (context.waitLoad) await context.waitLoad;
        if (context.loadError) throw context.loadError;
        return context.loadResponse;
      }
      if (context.waitPost) await context.waitPost;
      if (context.postError) throw context.postError;
    },
    onSaved: async () => {
      context.reads++;
      if (context.readError) throw context.readError;
    },
  };
  for (const name of ['Data', 'Editor', 'Pending', 'Error', 'RefreshError']) {
    const key = name[0].toLowerCase() + name.slice(1);
    context['set' + name] = (value) => {
      context[key] = typeof value === 'function' ? value(context[key]) : value;
    };
  }
  const api = execute(callbackCode, context);
  api.open({ section: 'types', index: 1 });
  return { context, requests, ...api, submit: () => api.save({ preventDefault() {} }) };
}

test('dialog success closes the draft and refreshes once while concurrent saves are ignored', async () => {
  const app = harness();
  let release;
  app.context.waitPost = new Promise((resolve) => (release = resolve));
  const first = app.submit();
  await app.submit();
  assert.equal(app.requests.length, 1);
  assert.equal(app.context.pending, true);
  release();
  await first;
  assert.equal(app.requests[0][0], app.context.initial.api_url);
  assert.equal(app.requests[0][1], app.context.data.space_url + 'configuration/');
  assert.equal(app.requests[0][4].get('types-1-key'), 'bug');
  assert.equal(app.context.editor, null);
  assert.equal(app.context.reads, 1);
  assert.equal(app.context.pending, false);
});

test('server validation keeps the dialog open with returned values, errors and focus', async () => {
  const app = harness();
  const corrected = fixture();
  corrected.sets[1].forms[1].fields[1].value = 'Zachowany szkic';
  corrected.sets[1].forms[1].fields[1].errors = ['Ta nazwa jest zajęta'];
  corrected.sets[1].errors = ['Błąd grupy'];
  app.context.postError = new PageError({ type: 'space-configuration', data: corrected });
  await app.submit();
  assert.equal(app.context.editor.section, 'types');
  assert.equal(app.context.editor.schema.fields[1].value, 'Zachowany szkic');
  assert.equal(app.context.editor.schema.fields[1].errors[0], 'Ta nazwa jest zajęta');
  assert.equal(app.context.editor.errors[0], 'Błąd grupy');
  assert.equal(app.context.focused, 1);
  assert.equal(app.context.reads, 0);
  assert.equal(app.context.sending.current, false);
  assert.equal(app.context.pending, false);
});

test('failed POST preserves the dialog draft and permits a real save retry', async () => {
  const app = harness();
  const editor = app.context.editor;
  app.context.postError = new Error('HTTP 503');
  await app.submit();
  assert.equal(app.context.editor, editor);
  assert.equal(app.context.error, 'HTTP 503');
  assert.equal(app.context.reads, 0);
  app.context.postError = null;
  await app.submit();
  assert.equal(app.requests.length, 2);
  assert.deepEqual([...app.requests[0][4]], [...app.requests[1][4]]);
  assert.equal(app.context.editor, null);
  assert.equal(app.context.reads, 1);
});

test('committed mutation with a failed refresh retries only reads and blocks stale edits', async () => {
  const app = harness();
  app.context.readError = new Error('GET 503');
  await app.submit();
  assert.equal(app.context.editor, null);
  assert.match(app.context.refreshError, /^Zmiany zapisano.*GET 503$/);
  app.open({ section: 'types', index: 0 });
  assert.equal(app.context.editor, null);
  await app.refresh();
  app.context.readError = null;
  await app.refresh();
  assert.equal(app.context.reads, 3);
  assert.equal(app.requests.length, 1);
  assert.equal(app.context.refreshError, '');
  assert.equal(app.context.pending, false);
});

function rejectedBootstrap() {
  const data = fixture();
  data.editor = { section: 'types', index: 1 };
  data.revision = 'rejected-revision';
  for (const group of data.sets) for (const form of group.forms) form.bound = true;
  data.sets[1].forms[0].fields[1].value = 'Odrzucony szkic innego typu';
  data.sets[2].forms[0].fields.find((entry) => entry.field_name === 'DELETE').checked = true;
  return data;
}

test('canceling a normal unbound dialog closes it without a request or save notification', async () => {
  const app = harness();
  const data = app.context.data;
  app.context.editor.dirty = true;
  app.context.error = 'Błąd poprzedniej próby';
  await app.closeEditor();
  assert.equal(app.context.editor, null);
  assert.equal(app.context.error, '');
  assert.equal(app.context.data, data);
  assert.equal(app.context.reads, 0);
  assert.equal(app.requests.length, 0);
});

test('canceling a rejected native bootstrap waits for clean values before closing and cannot leak drafts or DELETE', async () => {
  const app = harness(rejectedBootstrap());
  const editor = app.context.editor;
  const clean = fixture();
  clean.revision = 'clean-revision';
  app.context.loadResponse = { type: 'space-configuration', data: clean };
  let release;
  app.context.waitLoad = new Promise((resolve) => (release = resolve));
  const closing = app.closeEditor();
  assert.equal(app.context.editor, editor);
  assert.equal(app.context.pending, true);
  assert.equal(app.requests.length, 1);
  assert.equal(app.requests[0][0], app.context.initial.api_url);
  assert.equal(app.requests[0][1], clean.space_url + 'configuration/');
  assert.equal(app.requests[0][4], undefined);
  release();
  await closing;
  assert.equal(app.context.editor, null);
  assert.equal(app.context.data, clean);
  assert.equal(app.context.pending, false);
  assert.equal(app.context.reads, 0, 'discarding must not announce a successful save');
  app.open({ section: 'types', index: 1 });
  app.context.form.current.values = rowDraft(clean, 'types', 1);
  await app.submit();
  const posted = app.requests[1][4];
  assert.equal(posted.get('revision'), 'clean-revision');
  assert.equal(posted.get('types-0-label'), 'Nazwa task');
  assert.equal(posted.has('fields-0-DELETE'), false);
  assert.equal(posted.get('fields-0-required'), 'on');
});

test('failed discard refresh retains the rejected modal and revision until a read retry succeeds', async () => {
  const app = harness(rejectedBootstrap());
  const data = app.context.data;
  const editor = app.context.editor;
  app.context.loadError = new Error('GET 503');
  await app.closeEditor();
  assert.equal(app.context.editor, editor);
  assert.equal(app.context.data, data);
  assert.equal(app.context.data.revision, 'rejected-revision');
  assert.equal(app.context.pending, false);
  assert.match(app.context.error, /^Nie udało się odrzucić zmian.*GET 503$/);
  app.context.loadError = null;
  app.context.loadResponse = { type: 'space-configuration', data: fixture() };
  await app.closeEditor();
  assert.equal(app.context.editor, null);
  assert.equal(app.context.data, app.context.loadResponse.data);
  assert.equal(app.context.error, '');
  assert.equal(app.context.reads, 0);
  assert.equal(app.requests.length, 2);
  assert.ok(app.requests.every((request) => request[4] === undefined));
});
