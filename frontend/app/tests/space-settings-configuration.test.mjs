import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

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
  configurationMove,
  configurationStage,
  configurationStatusKey,
  configurationAdd,
  configurationRemove,
  configurationDraftSubmission,
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
  for (const [value, expected] of [
    [[''], 'square-check', 'Domyślna dla typu'],
    [['rocket'], 'rocket', 'Wdrożenie'],
    ['rocket', 'rocket', 'Wdrożenie'],
    [null, 'square-check', 'Domyślna dla typu'],
  ]) {
    const table = ConfigurationTable({
      group: {
        key: 'types',
        title: 'Typy zgłoszeń',
        management: fixture().sets[1].management,
        forms: [
          row('types', 0, 'task', [
            ['icon', value, { type: 'select', choices }],
            ['color', '#a153cc'],
          ]),
        ],
      },
      pending: false,
      actions: { dirty: false, onSave() {}, onCancel() {} },
    });
    const directory = nodes(table).find((element) => element?.props?.rows);
    assert.equal(
      directory.props.columns.some((column) => ['icon', 'color'].includes(column.key)),
      false,
    );
    assert.equal(directory.props.rows.length, 1);
    const name = directory.props.rows[0].cells.label.props.children;
    assert.equal(name.props.children.props.style['--tag-color'], '#a153cc');
    const [icon, label] = name.props.children.props.children;
    assert.equal(icon.props.name, expected);
    assert.equal(name.type, 'button');
    assert.equal(label.props.children, 'Nazwa task');
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

test('new stage keys are readable, unique and compatible with backend validation', () => {
  const data = fixture();
  const before = JSON.stringify(data);
  assert.equal(configurationStatusKey(data, 'Żółć — do sprawdzenia!'), 'zolc_do_sprawdzenia');
  assert.equal(configurationStatusKey(data, '123 oczekuje'), 'etap_123_oczekuje');
  assert.equal(configurationStatusKey(data, '🎉'), 'etap');
  assert.equal(configurationStatusKey(data, 'New'), 'new_2');
  assert.equal(JSON.stringify(data), before);
  data.sets[0].forms.push(row('statuses', 3, 'new_2'));
  assert.equal(configurationStatusKey(data, 'New'), 'new_3');
  const label = 'bardzo_dluga_nazwa_etapu_'.repeat(5);
  const first = configurationStatusKey(data, label);
  data.sets[0].forms.push(row('statuses', 4, first));
  const second = configurationStatusKey(data, label);
  assert.notEqual(first, second);
  for (const key of [first, second]) assert.match(key, /^[a-z][a-z0-9_]{0,39}$/);
  assert.equal(second.endsWith('_2'), true);
  const removed = configurationRemove(fixture(), 'statuses', [1]);
  assert.equal(configurationStatusKey(removed, 'Done'), 'done');
});

test('duplicate stage keys reject the local edit without damaging transitions or draft', () => {
  const data = fixture();
  const before = JSON.stringify(data);
  const edited = rowDraft(data, 'statuses', 0);
  edited.set('statuses-0-key', ' done ');
  assert.throws(
    () => configurationStage(data, { section: 'statuses', index: 0 }, edited),
    /Etap z tym kluczem już istnieje/,
  );
  assert.equal(JSON.stringify(data), before);
  edited.set('statuses-0-key', 'new');
  assert.doesNotThrow(() => configurationStage(data, { section: 'statuses', index: 0 }, edited));
  const added = rowDraft(data, 'statuses', 2);
  added.set('statuses-2-key', 'done');
  assert.throws(
    () => configurationStage(data, { section: 'statuses', index: 2 }, added),
    /Etap z tym kluczem już istnieje/,
  );
});

test('renaming an unused stage keeps incoming and self transitions in the full snapshot', () => {
  const data = fixture();
  const before = JSON.stringify(data);
  const edited = rowDraft(data, 'statuses', 0);
  edited.set('statuses-0-key', 'queue');
  const changed = configurationStage(data, { section: 'statuses', index: 0 }, edited);
  const values = configurationDraftSubmission(changed);
  assert.equal(values.get('statuses-0-key'), 'queue');
  assert.deepEqual(values.getAll('statuses-0-transitions'), ['done', 'queue']);
  assert.deepEqual(values.getAll('statuses-1-transitions'), ['queue']);
  assert.equal(values.get('revision'), 'revision-1');
  assert.equal(values.get('types-0-key'), 'task');
  assert.equal(values.get('fields-0-required'), 'on');
  assert.equal(JSON.stringify(data), before);
});

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

// Execute actual components with controlled React hooks and HTTP boundaries.
const formBundle = await build({
  entryPoints: [new URL('../src/spaces/ConfigurationPage.tsx', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  jsx: 'automatic',
  external: ['react', 'react/jsx-runtime', 'react-dom'],
  write: false,
});
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
  const found = nodes(tree).find(
    (element) => element.type === 'button' && text(element).trim() === label,
  );
  assert.ok(found, `Missing button: ${label}`);
  return found;
}
function table(tree) {
  const found = nodes(tree).find((element) => element.props?.group && element.props?.onEdit);
  assert.ok(found, 'Missing configuration table');
  return found;
}
function modal(tree) {
  return nodes(tree).find((element) => element.props?.onClose && element.props?.title);
}
function form(tree) {
  const found = nodes(tree).find((element) => element.type === 'form');
  assert.ok(found, 'Missing configuration editor form');
  return found;
}
function editorSchema(tree) {
  const found = nodes(tree).find((element) => element.props?.schema?.fields);
  assert.ok(found, 'Missing editor fields');
  return found.props.schema;
}
function formValues(schema) {
  const values = new FormData();
  for (const entry of schema.fields) {
    if (entry.type === 'checkbox') {
      if (entry.checked) values.append(entry.name, entry.value || 'on');
    } else if (Array.isArray(entry.value)) {
      for (const value of entry.value) values.append(entry.name, value);
    } else values.append(entry.name, entry.value || '');
  }
  return values;
}
class DialogFormData extends FormData {
  constructor(form) {
    super();
    if (form) for (const [name, value] of form.values) this.append(name, value);
  }
}
function hookHarness(code, exportName, initialProps, globals = {}) {
  const hooks = [];
  let cursor = 0;
  let changed = false;
  let effects = [];
  const app = { props: initialProps };
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
    if (
      !previous ||
      !dependencies ||
      dependencies.some((value, i) => !Object.is(value, previous.dependencies?.[i]))
    ) {
      effects.push(() => {
        previous?.cleanup?.();
        hooks[index] = { dependencies, cleanup: callback() };
      });
    }
  }
  function useMemo(callback, dependencies) {
    const index = cursor++;
    const previous = hooks[index];
    if (!previous || dependencies.some((value, i) => !Object.is(value, previous.dependencies[i]))) {
      hooks[index] = { dependencies, value: callback() };
    }
    return hooks[index].value;
  }
  const component = execute(code, {
    ...globals,
    require: (name) =>
      name === 'react'
        ? {
            ...require(name),
            useState,
            useEffect,
            useLayoutEffect: useEffect,
            useMemo,
            useCallback: (callback, dependencies) => useMemo(() => callback, dependencies),
            useId: () => useState(() => `test-id-${cursor}`)[0],
            useRef: (value) => useState(() => ({ current: value }))[0],
          }
        : name === 'react-dom'
          ? {
              ...require(name),
              flushSync: (callback) => {
                callback();
                app.render?.();
              },
            }
          : require(name),
  })[exportName];
  app.render = (updates = {}) => {
    app.props = { ...app.props, ...updates };
    let tree;
    let renders = 0;
    do {
      assert.ok(++renders < 30, 'React effects should settle without a render loop');
      cursor = 0;
      changed = false;
      effects = [];
      tree = component(app.props);
      if (app.expand) tree = app.expand(tree);
      app.afterRender?.(tree);
      effects.forEach((effect) => effect());
    } while (changed);
    return tree;
  };
  return app;
}
function harness(data = fixture(), section = 'types') {
  const app = {
    requests: [],
    states: [],
    reads: 0,
    focused: 0,
    postStatus: 200,
    postResponse: {},
    postError: null,
    getStatus: 200,
    getResponse: { type: 'space-configuration', data: fixture() },
    getError: null,
    refreshed: { ...fixture(), revision: 'revision-2' },
    readError: null,
    form: {
      values: new FormData(),
      reportValidity: () => true,
      querySelector: () => ({
        closest: () => null,
        focus: () => app.focused++,
        scrollIntoView() {},
      }),
    },
  };
  const runtime = hookHarness(
    formBundle.outputFiles[0].text,
    'ConfigurationForm',
    {
      initial: { api_url: '/workplaces/w_test/api/v1/page/', type: 'space-configuration', data },
      section,
      workflowView: 'map',
      csrfToken: 'token',
      onStateChange: (dirty, pending) => {
        app.states.push({ dirty, pending });
      },
      onSaved: async () => {
        app.reads++;
        if (app.readGate) await app.readGate;
        if (app.readError) throw app.readError;
        runtime.props = {
          ...runtime.props,
          initial: { ...runtime.props.initial, data: app.refreshed },
        };
      },
    },
    {
      FormData: DialogFormData,
      AbortController,
      AbortSignal,
      URL,
      Error,
      location: { origin: 'https://ancore.test' },
      requestAnimationFrame: (callback) => callback(),
      fetch: async (url, options) => {
        app.requests.push({ url, ...options });
        const isPost = options.method === 'POST';
        const gate = isPost ? app.postGate : app.getGate;
        if (gate) await gate;
        const error = isPost ? app.postError : app.getError;
        if (error) throw error;
        const status = isPost ? app.postStatus : app.getStatus;
        return {
          ok: status < 400,
          status,
          headers: { get: () => 'application/json' },
          json: async () => (isPost ? app.postResponse : app.getResponse),
        };
      },
    },
  );
  let activeRef;
  let activeSchema;
  runtime.afterRender = (tree) => {
    const element = nodes(tree).find((element) => element.type === 'form');
    if (!element) {
      if (activeRef) activeRef.current = null;
      activeSchema = undefined;
      return;
    }
    activeRef = element.ref;
    activeRef.current = app.form;
    const schema = editorSchema(tree);
    if (schema !== activeSchema) {
      app.form.values = formValues(schema);
      activeSchema = schema;
    }
  };
  app.render = runtime.render;
  app.open = (index) => {
    table(app.render()).props.onEdit(index);
    return app.render();
  };
  app.add = () => {
    table(app.render()).props.onAdd();
    return app.render();
  };
  app.change = (name, value) => {
    app.form.values.set(name, value);
    form(app.render()).props.onChange();
    return app.render();
  };
  app.stage = async () => {
    await form(app.render()).props.onSubmit({ preventDefault() {} });
    return app.render();
  };
  app.remove = (...indices) => {
    table(app.render()).props.onRemove(indices);
    return app.render();
  };
  app.save = () => {
    table(app.render()).props.actions.onSave();
    return app.render();
  };
  app.cancel = () => {
    table(app.render()).props.actions.onCancel();
    return app.render();
  };
  app.closeEditor = () => {
    modal(app.render()).props.onClose();
    return app.render();
  };
  app.settle = async () => {
    await new Promise((resolve) => setImmediate(resolve));
    return app.render();
  };
  app.render();
  return app;
}
function typeField(tree, index, name) {
  return table(tree).props.group.forms[index].fields.find((entry) => entry.field_name === name);
}
function deleted(tree, index) {
  return typeField(tree, index, 'DELETE').checked;
}
function stageEdit(app, index, label) {
  app.open(index);
  app.change(`types-${index}-label`, label);
  return app.stage();
}
function assertPreservedGroups(values) {
  assert.equal(values.get('statuses-0-key'), 'new');
  assert.deepEqual(values.getAll('statuses-0-transitions'), ['done', 'new']);
  assert.deepEqual(values.getAll('statuses-1-transitions'), ['new']);
  assert.equal(values.get('fields-0-required'), 'on');
  assert.equal(values.has('fields-1-required'), false);
  assert.equal(values.get('fields-0-key'), 'estimate');
  assert.equal(values.get('fields-1-key'), 'notes');
}

for (const [section, noun] of [
  ['categories', 'kategorię'],
  ['groups', 'grupę'],
]) {
  test(`${section} edits submit the selected dictionary and preserve the rest of the configuration`, async () => {
    const data = fixture();
    for (const key of ['categories', 'groups']) {
      data.sets.push({
        key,
        title: key,
        errors: [],
        management: schema([
          field(`${key}-TOTAL_FORMS`, '2', { hidden: true }),
          field(`${key}-INITIAL_FORMS`, '1', { hidden: true }),
        ]),
        forms: [row(key, 0, 'general'), row(key, 1, '')],
      });
    }
    const app = harness(data, section);
    app.refreshed = { ...data, revision: 'revision-2' };
    app.render({ commitOnSubmit: true });
    let tree = app.open(0);
    assert.equal(modal(tree).props.title, `Edytuj ${noun}`);
    app.change(`${section}-0-label`, 'Nowa nazwa');
    app.postStatus = 503;
    tree = await app.stage();
    assert.ok(modal(tree), 'A failed save retains the editor and draft');
    assert.equal(app.form.values.get(`${section}-0-label`), 'Nowa nazwa');
    app.postStatus = 200;
    await app.stage();
    const body = app.requests.at(-1).body;
    assert.equal(body.get('configuration_section'), section);
    assert.equal(body.get(`${section}-0-label`), 'Nowa nazwa');
    assert.equal(
      body.get(`${section === 'groups' ? 'categories' : 'groups'}-0-label`),
      'Nazwa general',
    );
    assert.equal(body.get('types-0-key'), 'task');
    assertPreservedGroups(body);
    assert.equal(modal(app.render()), undefined);
  });
}

test('type dialog commits the complete configuration once and keeps the dialog locked until saved', async () => {
  const app = harness(fixture(), 'statuses');
  await stageWorkflowEdit(app, 0, 'Szkic procesu');
  let tree = app.render({ section: 'types', commitOnSubmit: true });
  assert.equal(table(tree).props.actions, undefined);
  app.open(1);
  app.change('types-1-label', 'Nowy błąd');
  let release;
  app.postGate = new Promise((resolve) => (release = resolve));
  const submit = form(app.render()).props.onSubmit;
  const saving = submit({ preventDefault() {} });
  submit({ preventDefault() {} });
  tree = app.render();
  assert.equal(app.requests.length, 1);
  assert.equal(modal(tree).props.pending, true);
  assert.equal(app.requests[0].body.get('types-1-label'), 'Nowy błąd');
  assert.equal(app.requests[0].body.get('statuses-0-label'), 'Szkic procesu');
  assertPreservedGroups(app.requests[0].body);
  release();
  await saving;
  tree = await app.settle();
  assert.equal(modal(tree), undefined);
  assert.deepEqual(app.states.at(-1), { dirty: false, pending: false });
});

test('failed direct type save can be retried or canceled without losing an earlier workflow draft', async () => {
  const app = harness(fixture(), 'statuses');
  await stageWorkflowEdit(app, 0, 'Wcześniejszy szkic');
  app.render({ section: 'types', commitOnSubmit: true });
  app.postError = new Error('POST 503');
  let tree = await stageEdit(app, 1, 'Nie zapisano');
  assert.ok(modal(tree));
  assert.match(text(tree), /POST 503/);
  app.closeEditor();
  tree = app.render();
  assert.equal(typeField(tree, 1, 'label').value, 'Nazwa bug');
  tree = app.render({ section: 'statuses', commitOnSubmit: false });
  assert.equal(workflowValues(tree).get('statuses-0-label'), 'Wcześniejszy szkic');
  app.render({ section: 'types', commitOnSubmit: true });
  app.postError = null;
  await stageEdit(app, 1, 'Zapisana nazwa');
  assert.equal(app.requests.length, 2);
  assert.equal(app.requests[1].body.get('types-1-label'), 'Zapisana nazwa');
});

test('type deletion asks for confirmation and retries a failed request without staging other deletions', async () => {
  const app = harness();
  app.render({ commitOnSubmit: true });
  let tree = app.remove(1);
  assert.equal(app.requests.length, 0);
  button(modal(tree), 'Anuluj').props.onClick();
  tree = app.render();
  assert.equal(deleted(tree, 1), false);
  tree = app.remove(1);
  app.postError = new Error('POST 503');
  button(modal(tree), 'Usuń').props.onClick();
  tree = await app.settle();
  assert.ok(modal(tree));
  assert.match(text(tree), /POST 503/);
  app.postError = null;
  button(modal(tree), 'Usuń').props.onClick();
  tree = await app.settle();
  assert.equal(modal(tree), undefined);
  assert.equal(app.requests.length, 2);
  assert.equal(app.requests[1].body.get('types-1-DELETE'), 'on');
  assert.equal(app.requests[1].body.has('types-0-DELETE'), false);
  assertPreservedGroups(app.requests[1].body);
});

test('direct type save keeps validation errors editable and offers conflict recovery inside the dialog', async () => {
  const app = harness();
  app.render({ commitOnSubmit: true });
  app.postStatus = 400;
  const corrected = fixture();
  corrected.sets[1].forms[1].fields[1].value = 'Błędna nazwa';
  corrected.sets[1].forms[1].fields[1].errors = ['Błąd walidacji'];
  app.postResponse = { type: 'space-configuration', data: corrected };
  let tree = await stageEdit(app, 1, 'Błędna nazwa');
  assert.ok(modal(tree));
  assert.ok(app.focused > 0);
  app.postStatus = 409;
  app.postResponse = { error: 'Konfiguracja zmieniła się' };
  tree = await app.stage();
  assert.equal(button(modal(tree), 'Zapisz').props.disabled, true);
  button(modal(tree), 'Wczytaj aktualną konfigurację').props.onClick();
  tree = await app.settle();
  assert.equal(modal(tree), undefined);
  assert.deepEqual(
    app.requests.map((request) => request.method),
    ['POST', 'POST', 'GET'],
  );
});

function workflowValues(tree) {
  return configurationDraftSubmission(table(tree).props.data);
}
async function stageWorkflowEdit(app, index, label) {
  app.open(index);
  app.change(`statuses-${index}-label`, label);
  return app.stage();
}
function travelWorkflow(app, direction = 'undo') {
  table(app.render()).props.history[direction === 'undo' ? 'onUndo' : 'onRedo']();
  return app.render();
}

test('switching between states and map preserves list edits and their shared undo history', async () => {
  const app = harness(fixture(), 'statuses');
  let tree = app.render();
  const original = [...workflowValues(tree)];
  tree = app.render({ workflowView: 'states' });
  assert.equal(table(tree).props.data, undefined);
  tree = await stageWorkflowEdit(app, 0, 'Zmieniony stan z listy');
  assert.equal(typeField(tree, 0, 'label').value, 'Zmieniony stan z listy');
  assert.equal(table(tree).props.actions.dirty, true);

  tree = app.render({ workflowView: 'map' });
  const edited = [...workflowValues(tree)];
  assert.equal(workflowValues(tree).get('statuses-0-label'), 'Zmieniony stan z listy');
  assert.equal(table(tree).props.history.canUndo, true);
  tree = travelWorkflow(app);
  assert.deepEqual([...workflowValues(tree)], original);
  tree = app.render({ workflowView: 'states' });
  assert.equal(typeField(tree, 0, 'label').value, 'Nazwa new');
  assert.equal(table(tree).props.actions.dirty, false);

  app.render({ workflowView: 'map' });
  tree = travelWorkflow(app, 'redo');
  assert.deepEqual([...workflowValues(tree)], edited);
  app.refreshed = { ...table(tree).props.data, revision: 'revision-states-saved' };
  app.render({ workflowView: 'states' });
  app.save();
  tree = await app.settle();
  assert.equal(app.requests.length, 1);
  assert.equal(app.requests[0].body.get('configuration_section'), 'statuses');
  assert.equal(app.requests[0].body.get('statuses-0-label'), 'Zmieniony stan z listy');
  assertPreservedGroups(app.requests[0].body);
  assert.equal(table(tree).props.data, undefined);
  assert.equal(typeField(tree, 0, 'label').value, 'Zmieniony stan z listy');
  assert.equal(table(tree).props.actions.dirty, false);
});

test('workflow modal edits undo and redo the complete draft without losing connections or metadata', async () => {
  const data = fixture();
  data.sets[0].forms[0].fields.push(
    field('statuses-0-flow_stage', 'queue', { type: 'select' }),
    field('statuses-0-policy', 'Zakres uzgodniony', { type: 'textarea' }),
    field('statuses-0-position_x', '0', { hidden: true }),
    field('statuses-0-position_y', '240', { hidden: true }),
  );
  const app = harness(data, 'statuses');
  const original = [...workflowValues(app.render())];
  app.open(0);
  app.change('statuses-0-label', 'Do realizacji');
  app.change('statuses-0-policy', 'Zakres i odbiorca uzgodnieni');
  let tree = await app.stage();
  const edited = [...workflowValues(tree)];
  assert.equal(table(tree).props.history.canUndo, true);
  assert.equal(table(tree).props.history.canRedo, false);
  assert.deepEqual(workflowValues(tree).getAll('statuses-1-transitions'), ['new']);
  assert.equal(workflowValues(tree).get('statuses-0-position_x'), '0');
  assert.equal(workflowValues(tree).get('statuses-0-position_y'), '240');
  tree = travelWorkflow(app);
  assert.deepEqual([...workflowValues(tree)], original);
  assert.equal(table(tree).props.actions.dirty, false);
  assert.equal(table(tree).props.history.canRedo, true);
  tree = travelWorkflow(app, 'redo');
  assert.deepEqual([...workflowValues(tree)], edited);
  assert.equal(table(tree).props.actions.dirty, true);
  assert.equal(app.requests.length, 0);
  app.open(1);
  app.change('statuses-1-label', 'Niezastosowana edycja');
  tree = travelWorkflow(app);
  assert.ok(modal(tree));
  assert.deepEqual([...workflowValues(tree)], edited);
  app.closeEditor();
  assert.deepEqual([...workflowValues(travelWorkflow(app))], original);
});

test('undoing a workflow edit preserves incoming transitions and a new edit replaces redo history', async () => {
  const app = harness(fixture(), 'statuses');
  const original = [...workflowValues(app.render())];
  let tree = await stageWorkflowEdit(app, 1, 'Zakończenie');
  assert.equal(workflowValues(tree).get('statuses-1-label'), 'Zakończenie');
  assert.deepEqual(workflowValues(tree).getAll('statuses-0-transitions'), ['done', 'new']);
  tree = travelWorkflow(app);
  assert.deepEqual([...workflowValues(tree)], original);
  assert.deepEqual(workflowValues(tree).getAll('statuses-0-transitions'), ['done', 'new']);
  assert.equal(table(tree).props.history.canRedo, true);
  tree = await stageWorkflowEdit(app, 0, 'Nowy szkic po cofnięciu');
  assert.equal(table(tree).props.history.canRedo, false);
  const changed = [...workflowValues(tree)];
  tree = travelWorkflow(app, 'redo');
  assert.deepEqual([...workflowValues(tree)], changed);
  assert.equal(workflowValues(tree).get('statuses-1-label'), 'Nazwa done');
  assert.equal(app.requests.length, 0);
});

test('workflow Cancel discards both the draft and redo history, and a successful save starts a fresh history', async () => {
  const app = harness(fixture(), 'statuses');
  await stageWorkflowEdit(app, 0, 'Szkic do odrzucenia');
  await stageWorkflowEdit(app, 1, 'Druga zmiana do cofnięcia');
  travelWorkflow(app);
  let tree = app.cancel();
  assert.equal(workflowValues(tree).get('statuses-0-label'), 'Nazwa new');
  assert.equal(table(tree).props.actions.dirty, false);
  assert.equal(table(tree).props.history.canUndo, false);
  assert.equal(table(tree).props.history.canRedo, false);
  tree = await stageWorkflowEdit(app, 0, 'Zapisany etap');
  app.refreshed = { ...table(tree).props.data, revision: 'revision-saved' };
  app.save();
  tree = await app.settle();
  assert.equal(app.requests.length, 1);
  assert.equal(app.requests[0].body.get('configuration_section'), 'statuses');
  assert.equal(app.requests[0].body.get('statuses-0-label'), 'Zapisany etap');
  assert.equal(table(tree).props.history.canUndo, false);
  assert.equal(table(tree).props.history.canRedo, false);
  assert.equal(table(tree).props.actions.dirty, false);
  tree = travelWorkflow(app);
  assert.equal(workflowValues(tree).get('statuses-0-label'), 'Zapisany etap');
  tree = await stageWorkflowEdit(app, 0, 'Kolejna edycja');
  assert.equal(table(tree).props.history.canUndo, true);
  tree = travelWorkflow(app);
  assert.equal(workflowValues(tree).get('statuses-0-label'), 'Zapisany etap');
  assert.equal(workflowValues(tree).get('revision'), 'revision-saved');
  assert.equal(table(tree).props.actions.dirty, false);
});

test('workflow history is locked during POST and remains usable when the POST fails', async () => {
  const app = harness(fixture(), 'statuses');
  const original = [...workflowValues(app.render())];
  let tree = await stageWorkflowEdit(app, 0, 'Szkic zachowany po błędzie');
  const edited = [...workflowValues(tree)];
  const queuedUndo = table(tree).props.history.onUndo;
  let release;
  app.postGate = new Promise((resolve) => (release = resolve));
  app.postError = new Error('HTTP 503');
  app.save();
  queuedUndo();
  tree = travelWorkflow(app);
  assert.equal(table(tree).props.pending, true);
  assert.deepEqual([...workflowValues(tree)], edited);
  assert.equal(app.requests.length, 1);
  release();
  tree = await app.settle();
  assert.equal(table(tree).props.pending, false);
  assert.equal(table(tree).props.history.canUndo, true);
  assert.match(text(tree), /HTTP 503/);
  tree = travelWorkflow(app);
  assert.deepEqual([...workflowValues(tree)], original);
  assert.doesNotMatch(text(tree), /HTTP 503/);
  tree = travelWorkflow(app, 'redo');
  assert.deepEqual([...workflowValues(tree)], edited);
  assert.equal(app.requests.length, 1);
  assert.equal(app.reads, 0);
});

test('a committed workflow save clears history even when the following refresh fails', async () => {
  const app = harness(fixture(), 'statuses');
  let tree = await stageWorkflowEdit(app, 0, 'Etap zapisany na serwerze');
  app.refreshed = { ...table(tree).props.data, revision: 'revision-saved' };
  app.readError = new Error('GET 503');
  app.save();
  tree = await app.settle();
  assert.match(text(tree), /Zmiany zapisano.*GET 503/);
  assert.equal(table(tree).props.history.canUndo, false);
  assert.equal(table(tree).props.history.canRedo, false);
  assert.equal(table(tree).props.pending, true);
  tree = travelWorkflow(app);
  assert.equal(workflowValues(tree).get('statuses-0-label'), 'Etap zapisany na serwerze');
  app.readError = null;
  button(tree, 'Spróbuj ponownie').props.onClick();
  tree = await app.settle();
  assert.equal(app.requests.length, 1);
  assert.equal(app.reads, 2);
  assert.equal(table(tree).props.history.canUndo, false);
  assert.equal(table(tree).props.actions.dirty, false);
});

test('dialog edits stage locally, and toolbar Save submits one complete snapshot despite concurrent clicks', async () => {
  const app = harness();
  let tree = await stageEdit(app, 1, 'Zmieniony błąd');
  assert.equal(modal(tree), undefined);
  assert.equal(typeField(tree, 1, 'label').value, 'Zmieniony błąd');
  assert.equal(app.requests.length, 0);
  assert.deepEqual(app.states.at(-1), { dirty: true, pending: false });
  let release;
  app.postGate = new Promise((resolve) => (release = resolve));
  const save = table(tree).props.actions.onSave;
  save();
  save();
  tree = app.render();
  assert.equal(app.requests.length, 1);
  assert.equal(table(tree).props.pending, true);
  assert.deepEqual(app.states.at(-1), { dirty: true, pending: true });
  release();
  tree = await app.settle();
  const request = app.requests[0];
  assert.equal(request.method, 'POST');
  assert.equal(request.headers['X-CSRFToken'], 'token');
  assert.equal(
    new URL(request.url, 'https://ancore.test').searchParams.get('url'),
    fixture().space_url + 'configuration/',
  );
  assert.equal(request.body.get('revision'), 'revision-1');
  assert.equal(request.body.get('types-1-label'), 'Zmieniony błąd');
  assert.equal(request.body.has('configuration_index'), false);
  assertPreservedGroups(request.body);
  assert.equal(app.reads, 1);
  assert.deepEqual(app.states.at(-1), { dirty: false, pending: false });
  assert.equal(table(tree).props.actions.dirty, false);
});

test('multiple row deletions are local and reversible, then save together without changing other formsets', async () => {
  const app = harness();
  let tree = app.remove(0, 1);
  assert.equal(deleted(tree, 0), true);
  assert.equal(deleted(tree, 1), true);
  assert.equal(app.requests.length, 0);
  tree = app.cancel();
  assert.equal(deleted(tree, 0), false);
  assert.equal(deleted(tree, 1), false);
  assert.equal(app.reads, 0);
  assert.deepEqual(app.states.at(-1), { dirty: false, pending: false });
  app.remove(0, 1);
  app.save();
  await app.settle();
  assert.equal(app.requests.length, 1);
  assert.equal(app.requests[0].body.get('types-0-DELETE'), 'on');
  assert.equal(app.requests[0].body.get('types-1-DELETE'), 'on');
  assertPreservedGroups(app.requests[0].body);
});

test('adding multiple issue types creates separate local rows and preserves their form counts in one save', async () => {
  const app = harness();
  for (const [index, key, label] of [
    [2, 'idea', 'Pomysł'],
    [3, 'story', 'Historia'],
  ]) {
    app.add();
    app.change(`types-${index}-key`, key);
    app.change(`types-${index}-label`, label);
    await app.stage();
  }
  assert.equal(app.requests.length, 0);
  const tree = app.render();
  assert.equal(typeField(tree, 2, 'key').value, 'idea');
  assert.equal(typeField(tree, 3, 'key').value, 'story');
  app.save();
  await app.settle();
  const values = app.requests[0].body;
  assert.equal(values.get('types-2-key'), 'idea');
  assert.equal(values.get('types-3-key'), 'story');
  assert.ok(Number(values.get('types-TOTAL_FORMS')) >= 4);
  assert.equal(values.get('types-INITIAL_FORMS'), '2');
  assertPreservedGroups(values);
});

test('unchanged edits and adding then removing a new type leave no unsaved configuration', async () => {
  const app = harness();
  app.open(1);
  let tree = await app.stage();
  assert.equal(table(tree).props.actions.dirty, false);
  app.add();
  app.change('types-2-key', 'idea');
  app.change('types-2-label', 'Pomysł');
  tree = await app.stage();
  assert.equal(table(tree).props.actions.dirty, true);
  tree = app.remove(2);
  assert.equal(table(tree).props.actions.dirty, false);
  assert.deepEqual(app.states.at(-1), { dirty: false, pending: false });
  app.save();
  await app.settle();
  assert.equal(app.requests.length, 0);
});

test('removing a saved type frees capacity for its replacement without rewriting initial form identities', async () => {
  const data = fixture();
  data.sets[1].management.fields.push(field('types-MAX_NUM_FORMS', '2', { hidden: true }));
  const app = harness(data);
  let tree = app.add();
  assert.equal(modal(tree), undefined);
  assert.match(text(tree), /maksymalnie 2/);
  app.remove(0);
  app.add();
  app.change('types-2-key', 'idea');
  app.change('types-2-label', 'Pomysł');
  await app.stage();
  app.save();
  await app.settle();
  assert.equal(app.requests.length, 1);
  const values = app.requests[0].body;
  assert.equal(values.get('types-INITIAL_FORMS'), '2');
  assert.equal(values.get('types-TOTAL_FORMS'), '3');
  assert.equal(values.get('types-0-key'), 'task');
  assert.equal(values.get('types-0-DELETE'), 'on');
  assert.equal(values.get('types-2-key'), 'idea');
  assertPreservedGroups(values);
});

test('new local type rows use the server default icon for their staged key', async () => {
  const data = fixture();
  data.type_icon_defaults = { story: 'book-open' };
  data.sets[1].forms[2].fields.find((entry) => entry.field_name === 'icon').choices = [
    { value: '', label: 'Domyślna dla typu', icon: 'shapes' },
    { value: 'rocket', label: 'Wdrożenie', icon: 'rocket' },
  ];
  const app = harness(data);
  app.add();
  app.change('types-2-key', 'story');
  app.change('types-2-label', 'Historia');
  const tree = await app.stage();
  assert.equal(typeField(tree, 2, 'icon').value, '');
  assert.equal(typeField(tree, 2, 'icon').choices[0].icon, 'book-open');
  assert.equal(app.requests.length, 0);
});

test('server validation preserves staged rows and deletions and opens the invalid row with errors and focus', async () => {
  const app = harness();
  await stageEdit(app, 1, 'Niedozwolona nazwa');
  app.remove(0);
  const corrected = fixture();
  corrected.sets[1].forms[1].fields[1].value = 'Niedozwolona nazwa';
  corrected.sets[1].forms[1].fields[1].errors = ['Ta nazwa jest zajęta'];
  corrected.sets[1].forms[0].fields.find((entry) => entry.field_name === 'DELETE').checked = true;
  corrected.sets[1].errors = ['Błąd grupy'];
  app.postStatus = 400;
  app.postResponse = { type: 'space-configuration', data: corrected };
  app.save();
  const tree = await app.settle();
  assert.ok(modal(tree));
  assert.equal(editorSchema(tree).fields[1].value, 'Niedozwolona nazwa');
  assert.deepEqual(editorSchema(tree).fields[1].errors, ['Ta nazwa jest zajęta']);
  assert.match(text(tree), /Błąd grupy/);
  assert.equal(deleted(tree, 0), true);
  assert.equal(app.focused, 1);
  assert.equal(app.reads, 0);
  assert.deepEqual(app.states.at(-1), { dirty: true, pending: false });
});

test('a failed POST retains the entire staged snapshot and permits a real save retry', async () => {
  const app = harness();
  await stageEdit(app, 1, 'Zachowany szkic');
  app.remove(0);
  app.postError = new Error('HTTP 503');
  app.save();
  let tree = await app.settle();
  assert.equal(typeField(tree, 1, 'label').value, 'Zachowany szkic');
  assert.equal(deleted(tree, 0), true);
  assert.match(text(tree), /HTTP 503/);
  assert.equal(app.reads, 0);
  assert.equal(table(tree).props.pending, false);
  app.postError = null;
  app.save();
  tree = await app.settle();
  assert.equal(app.requests.length, 2);
  assert.deepEqual([...app.requests[0].body], [...app.requests[1].body]);
  assert.equal(app.reads, 1);
  assert.equal(table(tree).props.actions.dirty, false);
});

test('a committed mutation with a failed refresh retries reads only and blocks stale edits', async () => {
  const app = harness();
  await stageEdit(app, 1, 'Zapisany szkic');
  app.readError = new Error('GET 503');
  app.save();
  let tree = await app.settle();
  assert.equal(modal(tree), undefined);
  assert.match(text(tree), /Zmiany zapisano.*GET 503/);
  assert.equal(table(tree).props.pending, true);
  assert.deepEqual(app.states.at(-1), { dirty: false, pending: false });
  tree = app.open(0);
  assert.equal(modal(tree), undefined);
  button(tree, 'Spróbuj ponownie').props.onClick();
  tree = await app.settle();
  app.readError = null;
  button(tree, 'Spróbuj ponownie').props.onClick();
  tree = await app.settle();
  assert.equal(app.reads, 3);
  assert.equal(app.requests.length, 1);
  assert.equal(table(tree).props.pending, false);
  assert.doesNotMatch(text(tree), /GET 503/);
});

test('a revision conflict retains the draft and blocks Save until Cancel reloads current server values', async () => {
  const app = harness();
  await stageEdit(app, 1, 'Szkic przed konfliktem');
  app.postStatus = 409;
  app.postResponse = { error: 'Konfiguracja została zmieniona w innym oknie.' };
  app.save();
  let tree = await app.settle();
  assert.equal(typeField(tree, 1, 'label').value, 'Szkic przed konfliktem');
  assert.equal(table(tree).props.actions.saveDisabled, true);
  app.getResponse = {
    type: 'space-configuration',
    data: { ...fixture(), revision: 'clean-revision' },
  };
  app.getError = new Error('GET 503');
  app.cancel();
  tree = await app.settle();
  assert.equal(typeField(tree, 1, 'label').value, 'Szkic przed konfliktem');
  assert.match(text(tree), /GET 503/);
  app.getError = null;
  app.cancel();
  tree = await app.settle();
  assert.equal(typeField(tree, 1, 'label').value, 'Nazwa bug');
  assert.equal(table(tree).props.actions.dirty, false);
  assert.equal(app.reads, 0);
  assert.deepEqual(
    app.requests.map((request) => request.method),
    ['POST', 'GET', 'GET'],
  );
});

test('the native 400 configuration revision error also blocks a second mutation until the draft is discarded', async () => {
  const app = harness();
  await stageEdit(app, 1, 'Szkic bez nadpisania');
  const rejected = fixture();
  rejected.sets[1].forms[1].fields[1].value = 'Szkic bez nadpisania';
  rejected.errors = [
    'Konfiguracja zmieniła się od otwarcia formularza. Odśwież stronę przed zapisem.',
  ];
  app.postStatus = 400;
  app.postResponse = { type: 'space-configuration', data: rejected };
  app.save();
  let tree = await app.settle();
  assert.equal(typeField(tree, 1, 'label').value, 'Szkic bez nadpisania');
  assert.equal(table(tree).props.actions.saveDisabled, true);
  assert.equal(modal(tree), undefined);
  assert.match(text(tree), /Wybierz „Anuluj”/);
  app.save();
  await app.settle();
  assert.equal(app.requests.length, 1);
  app.cancel();
  tree = await app.settle();
  assert.equal(typeField(tree, 1, 'label').value, 'Nazwa bug');
  assert.equal(table(tree).props.actions.dirty, false);
  assert.equal(app.requests[1].method, 'GET');
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

test('canceling an ordinary modal closes it without discarding staged edits or issuing requests', async () => {
  const app = harness();
  await stageEdit(app, 1, 'Pierwszy szkic');
  app.open(0);
  app.change('types-0-label', 'Odrzucony szkic w oknie');
  const tree = app.closeEditor();
  assert.equal(modal(tree), undefined);
  assert.equal(typeField(tree, 0, 'label').value, 'Nazwa task');
  assert.equal(typeField(tree, 1, 'label').value, 'Pierwszy szkic');
  assert.equal(app.requests.length, 0);
  assert.equal(app.reads, 0);
  assert.deepEqual(app.states.at(-1), { dirty: true, pending: false });
});

test('canceling a rejected native bootstrap waits for clean values and prevents rejected fields or DELETE leaking', async () => {
  const app = harness(rejectedBootstrap());
  const clean = { ...fixture(), revision: 'clean-revision' };
  app.getResponse = { type: 'space-configuration', data: clean };
  let release;
  app.getGate = new Promise((resolve) => (release = resolve));
  let tree = app.closeEditor();
  assert.ok(modal(tree));
  assert.equal(app.requests.length, 1);
  assert.equal(app.requests[0].method, 'GET');
  assert.equal(table(tree).props.pending, true);
  release();
  tree = await app.settle();
  assert.equal(modal(tree), undefined);
  assert.equal(app.reads, 0);
  assert.equal(typeField(tree, 0, 'label').value, 'Nazwa task');
  await stageEdit(app, 1, 'Zapisany po odrzuceniu');
  app.save();
  await app.settle();
  const posted = app.requests[1].body;
  assert.equal(posted.get('revision'), 'clean-revision');
  assert.equal(posted.get('types-0-label'), 'Nazwa task');
  assert.equal(posted.has('fields-0-DELETE'), false);
  assertPreservedGroups(posted);
});

test('failed discard refresh retains the native rejected modal until a read retry succeeds', async () => {
  const app = harness(rejectedBootstrap());
  app.getError = new Error('GET 503');
  app.closeEditor();
  let tree = await app.settle();
  assert.ok(modal(tree));
  assert.equal(typeField(tree, 0, 'label').value, 'Odrzucony szkic innego typu');
  assert.match(text(tree), /Nie udało się odrzucić zmian.*GET 503/);
  assert.equal(table(tree).props.pending, false);
  app.getError = null;
  app.closeEditor();
  tree = await app.settle();
  assert.equal(modal(tree), undefined);
  assert.equal(typeField(tree, 0, 'label').value, 'Nazwa task');
  assert.equal(app.reads, 0);
  assert.equal(app.requests.length, 2);
  assert.ok(app.requests.every((request) => request.method === 'GET'));
});

function tableHarness(group = fixture().sets[1]) {
  const edits = [],
    removals = [],
    cancels = [];
  const app = hookHarness(
    tableBundle.outputFiles[0].text,
    'default',
    {
      group,
      pending: false,
      onAdd() {},
      onEdit: (index) => edits.push(index),
      onRemove: (indices) => removals.push(indices),
      actions: { dirty: true, onSave() {}, onCancel: () => cancels.push(true) },
    },
    { document: { addEventListener() {}, removeEventListener() {} } },
  );
  app.edits = edits;
  app.removals = removals;
  app.cancels = cancels;
  app.expand = function expand(element) {
    if (Array.isArray(element)) return element.map(expand);
    if (!element?.props) return element;
    if (
      (element.props.rows && element.props.onSelect) ||
      (typeof element.type === 'function' && element.type.name === 'ViewToolbar')
    )
      return expand(element.type(element.props));
    return { ...element, props: { ...element.props, children: expand(element.props.children) } };
  };
  app.select = (label, checked = true) => {
    const checkbox = nodes(app.render()).find(
      (node) => node.type === 'input' && node.props['aria-label'] === label,
    );
    assert.ok(checkbox, `Missing checkbox: ${label}`);
    checkbox.props.onChange({ target: { checked } });
    return app.render();
  };
  return app;
}

test('issue-type toolbar enables Edit for one selection and Delete for current multiple selection without row menus', () => {
  const app = tableHarness();
  let tree = app.render();
  assert.equal(button(tree, 'Edytuj').props.disabled, true);
  assert.equal(button(tree, 'Usuń').props.disabled, true);
  assert.equal(
    nodes(tree).some((node) => node.props?.['data-column'] === 'action'),
    false,
  );
  tree = app.select('Zaznacz: Nazwa task');
  assert.equal(button(tree, 'Edytuj').props.disabled, false);
  button(tree, 'Edytuj').props.onClick();
  assert.deepEqual(app.edits, [0]);
  tree = app.select('Zaznacz: Nazwa bug');
  assert.equal(button(tree, 'Edytuj').props.disabled, true);
  assert.equal(button(tree, 'Usuń').props.disabled, false);
  button(tree, 'Usuń').props.onClick();
  tree = app.render();
  assert.deepEqual(app.removals, [[0, 1]]);
  assert.equal(button(tree, 'Usuń').props.disabled, true);
});

test('table Cancel clears selection and pending locks toolbar and selection controls', () => {
  const app = tableHarness();
  let tree = app.select('Zaznacz wszystkie widoczne pozycje');
  button(tree, 'Anuluj').props.onClick();
  tree = app.render();
  assert.equal(app.cancels.length, 1);
  assert.equal(button(tree, 'Usuń').props.disabled, true);
  assert.equal(
    nodes(tree)
      .filter((node) => node.type === 'input' && node.props.type === 'checkbox')
      .some((node) => node.props.checked),
    false,
  );
  app.select('Zaznacz: Nazwa task');
  tree = app.render({ pending: true });
  for (const label of ['Edytuj', 'Usuń', 'Dodaj typ', 'Zapisywanie…', 'Anuluj'])
    assert.equal(button(tree, label).props.disabled, true);
  assert.ok(
    nodes(tree)
      .filter((node) => node.type === 'input' && node.props.type === 'checkbox')
      .every((node) => node.props.disabled),
  );
});

test('table selection follows row positions across staged key edits and ignores rows removed from the current draft', () => {
  const app = tableHarness();
  app.select('Zaznacz: Nazwa task');
  const changed = fixture().sets[1];
  changed.forms[0].fields[0].value = 'renamed';
  let tree = app.render({ group: changed });
  assert.equal(button(tree, 'Edytuj').props.disabled, false);
  button(tree, 'Edytuj').props.onClick();
  assert.deepEqual(app.edits, [0]);
  changed.forms[0].fields.find((entry) => entry.field_name === 'DELETE').checked = true;
  tree = app.render({ group: { ...changed } });
  assert.equal(button(tree, 'Edytuj').props.disabled, true);
  assert.equal(button(tree, 'Usuń').props.disabled, true);
});

test('filtering clears hidden selections and editing a filtered row uses its original form index', () => {
  const app = tableHarness();
  app.select('Zaznacz: Nazwa task');
  let tree = app.render();
  const search = nodes(tree).find((node) => node.type === 'input' && node.props.type === 'search');
  search.props.onChange({ target: { value: 'BUG' } });
  tree = app.render();
  assert.equal(button(tree, 'Edytuj').props.disabled, true);
  assert.equal(nodes(tree).filter((node) => node.props?.role === 'row').length, 2);
  tree = app.select('Zaznacz wszystkie widoczne pozycje');
  button(tree, 'Edytuj').props.onClick();
  assert.deepEqual(app.edits, [1]);
  search.props.onChange({ target: { value: 'brak-wyników' } });
  tree = app.render();
  assert.equal(button(tree, 'Usuń').props.disabled, true);
  assert.ok(nodes(tree).some((node) => node.props?.title === 'Nie znaleziono wyników.'));
});

const settingsBundle = await build({
  entryPoints: [new URL('../src/spaces/SettingsPage.tsx', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  jsx: 'automatic',
  external: ['react', 'react/jsx-runtime', 'react-dom'],
  write: false,
});
function settingsHarness(configurationData = fixture(), initialTab = 'main') {
  const http = { requests: [], response: null };
  const emitted = [];
  const windowListeners = new Map();
  function eventSurface(listeners = new Map()) {
    return {
      addEventListener(type, callback) {
        const handlers = listeners.get(type) || new Set();
        handlers.add(callback);
        listeners.set(type, handlers);
      },
      removeEventListener(type, callback) {
        listeners.get(type)?.delete(callback);
      },
    };
  }
  const configuration = {
    type: 'space-configuration',
    api_url: '/workplaces/w_test/api/v1/page/',
    data: configurationData,
  };
  const spaceUrl = fixture().space_url;
  class SettingsForm {
    constructor(visibility) {
      this.values = draft([
        ['name', 'Nowa nazwa przestrzeni'],
        ['description', 'Nowy opis'],
        ['visibility', visibility],
      ]);
    }
  }
  const app = hookHarness(
    settingsBundle.outputFiles[0].text,
    'default',
    {
      api: configuration.api_url,
      csrfToken: 'token',
      spaceUrl,
      initialTab,
      initialForm: { form: schema([]), return_url: spaceUrl },
      initialConfiguration: configuration,
      initialDetail: {
        space: { name: 'Przestrzeń testowa', visibility: 'private' },
        team: { name: 'Przestrzeń testowa', visibility: 'private' },
        team_url: spaceUrl + 'team/',
        edit_url: spaceUrl + 'edit/',
        configuration_url: spaceUrl + 'configuration/',
        can_manage: true,
        can_configure: true,
      },
    },
    {
      FormData: DialogFormData,
      HTMLFormElement: SettingsForm,
      AbortController,
      AbortSignal,
      URL,
      CustomEvent: class {
        constructor(type, options = {}) {
          this.type = type;
          this.detail = options.detail;
        }
      },
      location: {
        href: 'https://ancore.test' + spaceUrl + '?view=settings#' + initialTab,
        origin: 'https://ancore.test',
        pathname: spaceUrl,
        search: '?view=settings',
        hash: '#' + initialTab,
      },
      window: {
        ...eventSurface(windowListeners),
        dispatchEvent(event) {
          emitted.push(event);
        },
        AncoreApp: { setLocation() {} },
      },
      document: { ...eventSurface() },
      fetch: async (url, options) => {
        http.requests.push({ url, ...options });
        assert.ok(http.response, 'Initialized settings should not issue an HTTP request.');
        return {
          ok: true,
          status: 200,
          headers: { get: () => 'application/json' },
          json: async () =>
            typeof http.response === 'function' ? http.response(url) : http.response,
        };
      },
    },
  );
  app.http = http;
  app.events = emitted;
  app.beforeUnload = () => {
    const event = {
      prevented: false,
      preventDefault() {
        this.prevented = true;
      },
    };
    windowListeners.get('beforeunload')?.forEach((callback) => callback(event));
    return event;
  };
  app.main = (tree = app.render()) => {
    const component = nodes(tree).find((node) => node.props?.data?.form && node.props?.onSaved);
    assert.ok(component, 'Missing main settings form');
    return component;
  };
  app.configuration = (tree = app.render()) => {
    const component = nodes(tree).find(
      (node) => node.props?.initial?.type === 'space-configuration',
    );
    assert.ok(component, 'The configuration editor must remain mounted');
    return component;
  };
  app.navigation = (tree = app.render()) => {
    const header = nodes(tree).find((node) => node.props?.navigationContent);
    assert.ok(header, 'Missing workflow navigation in the space header');
    return header.props.navigationContent;
  };
  app.access = (tree = app.render()) => {
    const component = nodes(tree).find((node) => node.props?.publicVisibility === 'public');
    assert.ok(component, 'Missing access editor');
    return component;
  };
  app.configState = (dirty, pending = false) => {
    app.configuration().props.onStateChange(dirty, pending);
    return app.render();
  };
  app.submitSettings = (visibility) => {
    const target = new SettingsForm(visibility);
    const event = {
      target,
      prevented: false,
      stopped: false,
      preventDefault() {
        this.prevented = true;
      },
      stopPropagation() {
        this.stopped = true;
      },
    };
    const section = nodes(app.render()).find(
      (node) => node.props?.id === 'space-settings-panel-main',
    );
    assert.ok(section?.props.onSubmitCapture, 'Missing main settings submission guard');
    section.props.onSubmitCapture(event);
    return { event, tree: app.render() };
  };
  app.render();
  return app;
}

test('settings routes categories and groups to their own immediately saved dictionary', () => {
  for (const section of ['categories', 'groups']) {
    const settings = settingsHarness(fixture(), section);
    assert.equal(settings.configuration().props.section, section);
    assert.equal(settings.configuration().props.commitOnSubmit, true);
  }
});

test('settings retains the selected workflow view when a saved revision remounts the configuration', async () => {
  const app = settingsHarness(fixture(), 'statuses');
  let configuration = app.configuration();
  assert.equal(configuration.props.workflowView, 'states');
  assert.equal(button(app.navigation(), 'Stany').props['aria-selected'], true);
  button(app.navigation(), 'Mapa').props.onClick();
  configuration = app.configuration();
  assert.equal(configuration.props.workflowView, 'map');
  assert.equal(button(app.navigation(), 'Mapa').props['aria-selected'], true);
  button(app.navigation(), 'Stany').props.onClick();
  configuration = app.configuration();
  assert.equal(configuration.props.workflowView, 'states');
  assert.equal(button(app.navigation(), 'Stany').props['aria-selected'], true);
  assert.equal(button(app.navigation(), 'Mapa').props.tabIndex, -1);
  const originalKey = configuration.key;
  const saved = {
    ...configuration.props.initial,
    data: { ...fixture(), revision: 'revision-states-saved', workflow_view: 'map' },
  };
  app.http.response = (url) =>
    new URL(url, 'https://ancore.test').searchParams.get('url').endsWith('configuration/')
      ? saved
      : { type: 'space-detail', title: 'Ustawienia przestrzeni', data: app.props.initialDetail };
  await configuration.props.onSaved();
  configuration = app.configuration();
  assert.notEqual(configuration.key, originalKey);
  assert.equal(configuration.key, 'revision-states-saved');
  assert.equal(configuration.props.workflowView, 'states');
  assert.equal(button(app.navigation(), 'Stany').props['aria-selected'], true);
  assert.equal(configuration.props.initial, saved);
  assert.deepEqual(
    app.http.requests.map((request) => [
      request.method,
      new URL(request.url, 'https://ancore.test').searchParams.get('url'),
    ]),
    [
      ['GET', fixture().space_url + '?view=settings'],
      ['GET', fixture().space_url + 'configuration/'],
    ],
  );
  button(app.navigation(), 'Mapa').props.onClick();
  assert.equal(app.configuration().props.workflowView, 'map');
  assert.equal(button(app.navigation(), 'Mapa').props['aria-selected'], true);
  const nativeStates = settingsHarness({ ...fixture(), workflow_view: 'states' }, 'statuses');
  assert.equal(nativeStates.configuration().props.workflowView, 'states');
  assert.equal(button(nativeStates.navigation(), 'Stany').props['aria-selected'], true);
  const nativeMap = settingsHarness({ ...fixture(), workflow_view: 'map' }, 'statuses');
  assert.equal(nativeMap.configuration().props.workflowView, 'map');
  assert.equal(button(nativeMap.navigation(), 'Mapa').props['aria-selected'], true);
});

test('a staged configuration blocks the access visibility control until the configuration is saved or canceled', () => {
  const app = settingsHarness();
  const original = app.configuration();
  assert.equal(app.access().props.settingsDirty, false);
  let tree = app.configState(true);
  assert.equal(app.access(tree).props.settingsDirty, true);
  assert.equal(app.configuration(tree).key, original.key);
  assert.equal(app.configuration(tree).props.initial, original.props.initial);
  tree = app.configState(false);
  assert.equal(app.access(tree).props.settingsDirty, false);
});

test('main settings cannot change visibility and unmount unsaved types, but name and description changes remain allowed', () => {
  const app = settingsHarness();
  const original = app.configuration();
  app.configState(true);
  let result = app.submitSettings('public');
  assert.equal(result.event.prevented, true);
  assert.equal(result.event.stopped, true);
  assert.match(text(result.tree), /Najpierw zapisz lub anuluj zmiany konfiguracji zadań/);
  assert.equal(app.configuration(result.tree).key, original.key);
  assert.equal(app.configuration(result.tree).props.initial, original.props.initial);
  result = app.submitSettings('private');
  assert.equal(result.event.prevented, false);
  assert.equal(result.event.stopped, false);
  assert.equal(result.event.target.values.get('name'), 'Nowa nazwa przestrzeni');
  assert.equal(result.event.target.values.get('description'), 'Nowy opis');
  app.configState(false);
  result = app.submitSettings('public');
  assert.equal(result.event.prevented, false);
  assert.equal(result.event.stopped, false);
});

test('a saved main form refresh removes revoked editors, updates sidebar rights and clears abandoned dirty or pending state', async () => {
  const app = settingsHarness();
  const main = app.main();
  main.props.onStateChange(true, true);
  app.configState(true, true);
  assert.equal(app.beforeUnload().prevented, true);
  app.http.response = {
    type: 'space-detail',
    title: 'Ustawienia przestrzeni · Przestrzeń publiczna',
    data: {
      ...app.props.initialDetail,
      space: {
        ...app.props.initialDetail.space,
        name: 'Przestrzeń publiczna',
        visibility: 'public',
      },
      team: {
        ...app.props.initialDetail.team,
        name: 'Przestrzeń publiczna',
        visibility: 'public',
        can_manage: false,
        can_configure: false,
      },
      can_manage: false,
      can_configure: false,
    },
  };
  await main.props.onSaved();
  const tree = app.render();
  assert.equal(app.http.requests.length, 1);
  assert.equal(app.http.requests[0].method, 'GET');
  assert.equal(
    new URL(app.http.requests[0].url, 'https://ancore.test').searchParams.get('url'),
    fixture().space_url + '?view=settings',
  );
  assert.equal(
    nodes(tree).some((node) => node.props?.data?.form && node.props?.onSaved),
    false,
  );
  assert.equal(
    nodes(tree).some((node) => node.props?.initial?.type === 'space-configuration'),
    false,
  );
  assert.match(text(tree), /Przestrzeń publiczna/);
  assert.equal(app.access(tree).props.settingsDirty, false);
  assert.equal(app.access(tree).props.blocked, false);
  assert.equal(app.beforeUnload().prevented, false);
  const event = app.events.findLast((event) => event.type === 'ancore:space-settings-saved');
  assert.ok(event);
  assert.equal(event.detail.name, 'Przestrzeń publiczna');
  assert.equal(event.detail.canConfigure, false);
});

const typeFieldsBundle = await build({
  entryPoints: [new URL('../src/spaces/TypeFields.tsx', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  jsx: 'automatic',
  external: ['react', 'react/jsx-runtime', 'react-dom'],
  write: false,
});
function typeFieldsHarness(value = '') {
  const schema = row('types', 1, 'task', [
    [
      'icon',
      value,
      {
        type: 'select',
        choices: [
          { value: '', label: 'Domyślna dla typu', icon: 'square-check' },
          ...[
            ['square-check', 'Zadanie'],
            ['circle-alert', 'Błąd'],
            ['book-open', 'Historyjka'],
            ['zap', 'Epik'],
            ['megaphone', 'Kampania'],
            ['file-text', 'Materiał'],
            ['user-round', 'Osoba'],
            ['messages-square', 'Rozmowa'],
            ['ticket', 'Zgłoszenie'],
            ['siren', 'Incydent'],
            ['shapes', 'Kształty'],
            ['lightbulb', 'Pomysł'],
            ['target', 'Cel'],
            ['rocket', 'Wdrożenie'],
            ['wrench', 'Usprawnienie'],
            ['flask-conical', 'Eksperyment'],
            ['shield-check', 'Bezpieczeństwo'],
            ['list-checks', 'Lista kontrolna'],
            ['calendar', 'Wydarzenie'],
            ['flag', 'Kamień milowy'],
            ['briefcase', 'Sprawa'],
            ['palette', 'Projekt graficzny'],
            ['chart-column', 'Raport'],
            ['settings', 'Konfiguracja'],
          ].map(([value, label]) => ({ value, label, icon: value })),
        ],
      },
    ],
    ['description', '', { type: 'textarea' }],
  ]);
  const dom = { activeElement: null };
  const inputEvents = [];
  class Input {}
  const input = {
    value: '',
    dispatchEvent(event) {
      inputEvents.push({ type: event.type, bubbles: event.bubbles });
    },
  };
  const trigger = {
    focus() {
      dom.activeElement = trigger;
    },
    closest() {
      return null;
    },
  };
  let choices = [];
  let gridRef;
  const menu = { querySelector: () => choices[0], querySelectorAll: () => choices };
  const grid = {
    querySelector: () => choices.find((choice) => choice.node.props['data-type-icon']),
    querySelectorAll: () => choices.filter((choice) => choice.node.props['data-type-icon']),
  };
  const search = {
    value: '',
    closest: () => null,
    matches: (selector) => selector === 'input',
    focus() {
      dom.activeElement = search;
    },
  };
  const app = hookHarness(
    typeFieldsBundle.outputFiles[0].text,
    'default',
    {
      schema,
      iconDefaults: { task: 'square-check', story: 'book-open' },
    },
    {
      HTMLInputElement: Input,
      Event,
      document: dom,
      window: { AncoreDropdownLayer: { open() {}, hide() {} } },
      requestAnimationFrame: (callback) => callback(),
    },
  );
  // Mount the icon picker and shared dropdown, while leaving the unrelated
  // field controls and SVG renderer at their component boundaries.
  app.expand = function expand(element) {
    if (!element || typeof element !== 'object') return element;
    if (Array.isArray(element)) return element.map(expand);
    if (
      typeof element.type === 'function' &&
      ((element.props?.field && element.props?.defaultIcon !== undefined) ||
        (element.props?.trigger && typeof element.props?.children === 'function'))
    )
      return expand(element.type(element.props));
    return { ...element, props: { ...element.props, children: expand(element.props?.children) } };
  };
  app.afterRender = (tree) => {
    const hidden = nodes(tree).find(
      (node) => node.type === 'input' && node.props.type === 'hidden',
    );
    assert.ok(hidden);
    hidden.ref.current = input;
    input.value = hidden.props.value;
    input.name = hidden.props.name;
    const triggerNode = nodes(tree).find(
      (node) => node.type === 'button' && node.props['aria-haspopup'] === 'dialog',
    );
    triggerNode.ref.current = trigger;
    const menuNode = nodes(tree).find((node) => node.props?.role === 'dialog');
    menuNode.ref.current = menu;
    const searchNode = nodes(tree).find((node) => node.props?.type === 'search');
    searchNode.ref.current = search;
    search.value = searchNode.props.value;
    const gridNode = nodes(tree).find((node) => node.props?.className === 'emoji-picker-grid');
    if (gridNode) {
      gridRef = gridNode.ref;
      gridRef.current = grid;
    } else if (gridRef) gridRef.current = null;
    choices = nodes(menuNode)
      .filter((node) => node.type === 'button')
      .map((node) => {
        const existing = choices.find((choice) => choice.node.key === node.key);
        if (existing) {
          existing.node = node;
          return existing;
        }
        const choice = {
          node,
          closest: () => null,
          matches: () => false,
          getClientRects: () => [{}],
          scrollIntoView() {},
          click() {
            choice.node.props.onClick();
          },
          focus() {
            dom.activeElement = choice;
          },
        };
        return choice;
      });
  };
  app.trigger = () =>
    nodes(app.render()).find(
      (node) => node.type === 'button' && node.props['aria-haspopup'] === 'dialog',
    );
  app.preview = () =>
    nodes(app.trigger().props.children).find((node) => node.props?.name)?.props.name;
  app.choose = (label) => {
    if (!app.trigger().props['aria-expanded']) app.trigger().props.onClick();
    const tree = app.render();
    const choice = nodes(tree).find(
      (node) =>
        node.type === 'button' &&
        (node.props['aria-label'] === label || text(node).trim() === label),
    );
    assert.ok(choice, `Missing icon choice: ${label}`);
    choice.props.onClick();
    return app.render();
  };
  app.search = (value) => {
    const tree = app.render();
    const searchNode = nodes(tree).find((node) => node.props?.type === 'search');
    search.value = value;
    const event = () => ({
      currentTarget: search,
      propagationStopped: false,
      stopPropagation() {
        this.propagationStopped = true;
      },
    });
    // React dispatches onChange separately from the captured input event;
    // either event reaching the editor form would incorrectly mark it dirty.
    const inputEvent = event();
    const changeEvent = event();
    searchNode.props.onInputCapture(inputEvent);
    searchNode.props.onChange(changeEvent);
    app.render();
    return { input: inputEvent, change: changeEvent };
  };
  app.results = () =>
    nodes(app.render())
      .filter((node) => node.props?.['data-type-icon'])
      .map((node) => node.props['aria-label']);
  app.changeKey = (value, name = 'types-1-key') => {
    const target = Object.assign(new Input(), { name, value });
    const fields = nodes(app.render()).find((node) => node.props?.onInput);
    fields.props.onInput({ target });
    return app.render();
  };
  app.key = (key, source = 'trigger') => {
    const tree = app.render();
    const node =
      source === 'trigger'
        ? nodes(tree).find(
            (node) => node.type === 'button' && node.props['aria-haspopup'] === 'dialog',
          )
        : source === 'grid'
          ? nodes(tree).find((node) => node.props?.className === 'emoji-picker-grid')
          : source === 'search'
            ? nodes(tree).find((node) => node.props?.type === 'search')
            : nodes(tree).find((node) => node.props?.role === 'dialog');
    const event = {
      key,
      defaultPrevented: false,
      propagationStopped: false,
      target: source === 'trigger' ? trigger : dom.activeElement,
      currentTarget:
        source === 'trigger'
          ? trigger
          : source === 'grid'
            ? grid
            : source === 'search'
              ? search
              : menu,
      preventDefault() {
        this.defaultPrevented = true;
      },
      stopPropagation() {
        this.propagationStopped = true;
      },
    };
    node.props.onKeyDown(event);
    app.render();
    return event;
  };
  app.focusedLabel = () =>
    dom.activeElement === trigger
      ? 'trigger'
      : dom.activeElement === search
        ? 'search'
        : dom.activeElement?.node?.props['aria-label'] || text(dom.activeElement?.node).trim();
  app.input = input;
  app.inputEvents = inputEvents;
  app.render();
  return app;
}

test('the type icon picker submits the selected icon under its Django field name and notifies the form only on changes', () => {
  const app = typeFieldsHarness(['rocket']);
  assert.equal(app.input.name, 'types-1-icon');
  assert.equal(app.input.value, 'rocket');
  assert.equal(app.preview(), 'rocket');
  app.choose('Domyślna dla typu');
  assert.equal(app.input.value, '');
  assert.equal(app.preview(), 'square-check');
  assert.deepEqual(app.inputEvents, [
    { type: 'input', bubbles: true },
    { type: 'change', bubbles: true },
  ]);
  assert.equal(app.focusedLabel(), 'trigger');
  app.choose('Domyślna dla typu');
  assert.equal(app.inputEvents.length, 2);
  app.choose('Incydent');
  assert.equal(app.input.value, 'siren');
  assert.equal(app.preview(), 'siren');
  assert.equal(app.inputEvents.length, 4);
});

test('editing the type key updates the default preview while an explicitly chosen icon stays selected', () => {
  const app = typeFieldsHarness();
  app.changeKey('story');
  assert.equal(app.preview(), 'book-open');
  assert.equal(app.input.value, '');
  app.changeKey('task', 'types-1-label');
  assert.equal(app.preview(), 'book-open');
  app.choose('Wdrożenie');
  app.changeKey('task');
  assert.equal(app.preview(), 'rocket');
  assert.equal(app.input.value, 'rocket');
  app.choose('Domyślna dla typu');
  assert.equal(app.preview(), 'square-check');
  app.changeKey('custom');
  assert.equal(app.preview(), 'shapes');
});

test('the type icon picker opens and navigates with the keyboard and restores trigger focus after selection', () => {
  const app = typeFieldsHarness();
  assert.equal(app.key('ArrowDown').defaultPrevented, true);
  assert.equal(app.trigger().props['aria-expanded'], true);
  assert.equal(app.focusedLabel(), 'Domyślna dla typu');
  app.key('End', 'menu');
  assert.equal(app.focusedLabel(), 'Konfiguracja');
  app.key('Home', 'menu');
  assert.equal(app.focusedLabel(), 'Domyślna dla typu');
  app.key('ArrowDown', 'menu');
  assert.equal(app.focusedLabel(), 'Zadanie');
  app.choose('Wdrożenie');
  assert.equal(app.input.value, 'rocket');
  assert.equal(app.trigger().props['aria-expanded'], false);
  assert.equal(app.focusedLabel(), 'trigger');
});

test('the type icon picker searches Polish labels without dirtying the form and resets its search when reopened', () => {
  const app = typeFieldsHarness(['rocket']);
  app.trigger().props.onClick();
  app.render();
  assert.equal(app.focusedLabel(), 'search');
  assert.equal(app.results().length, 24);
  const searchEvents = app.search('  BLAD  ');
  assert.equal(searchEvents.input.propagationStopped, true);
  assert.equal(searchEvents.change.propagationStopped, true);
  assert.deepEqual(app.results(), ['Błąd']);
  app.search('lista KONTROLNA');
  assert.deepEqual(app.results(), ['Lista kontrolna']);
  app.search('nieistniejąca ikona');
  assert.deepEqual(app.results(), []);
  assert.match(text(app.render()), /Brak pasujących ikon\./);
  assert.equal(app.key('Enter', 'search').defaultPrevented, true);
  assert.equal(app.trigger().props['aria-expanded'], true);
  assert.deepEqual(app.inputEvents, []);
  assert.equal(app.input.value, 'rocket');
  app.trigger().props.onClick();
  app.render();
  app.trigger().props.onClick();
  app.render();
  assert.equal(app.results().length, 24);
  assert.equal(app.focusedLabel(), 'search');
  app.search('Wdrozenie');
  assert.deepEqual(app.results(), ['Wdrożenie']);
  const enter = app.key('Enter', 'search');
  assert.equal(enter.defaultPrevented, true);
  assert.equal(enter.propagationStopped, true);
  assert.equal(app.trigger().props['aria-expanded'], false);
  assert.equal(app.focusedLabel(), 'trigger');
  assert.deepEqual(app.inputEvents, []);
});

test('the type icon grid moves by eight columns vertically and one icon horizontally without escaping its boundaries', () => {
  const app = typeFieldsHarness();
  app.trigger().props.onClick();
  app.render();
  const fromSearch = app.key('ArrowDown', 'search');
  assert.equal(fromSearch.defaultPrevented, true);
  assert.equal(fromSearch.propagationStopped, true);
  assert.equal(app.focusedLabel(), 'Zadanie');
  app.key('ArrowLeft', 'grid');
  assert.equal(app.focusedLabel(), 'Zadanie');
  const down = app.key('ArrowDown', 'grid');
  assert.equal(down.defaultPrevented, true);
  assert.equal(down.propagationStopped, true);
  assert.equal(app.focusedLabel(), 'Zgłoszenie');
  app.key('ArrowRight', 'grid');
  assert.equal(app.focusedLabel(), 'Incydent');
  app.key('ArrowUp', 'grid');
  assert.equal(app.focusedLabel(), 'Błąd');
  app.key('End', 'grid');
  assert.equal(app.focusedLabel(), 'Konfiguracja');
  app.key('ArrowDown', 'grid');
  app.key('ArrowRight', 'grid');
  assert.equal(app.focusedLabel(), 'Konfiguracja');
  app.key('Home', 'grid');
  assert.equal(app.focusedLabel(), 'Zadanie');
  assert.deepEqual(app.inputEvents, []);
});

test('workflow reorder preserves metadata and posts contiguous field identities', () => {
  const data = fixture();
  data.section = 'statuses';
  data.sets[0].forms[0].fields.push(field('statuses-0-policy', 'Najpierw zakres pracy'));
  const moved = configurationMove(data, 'statuses', 0, 1);
  const body = configurationDraftSubmission(moved);
  assert.equal(body.get('configuration_section'), 'statuses');
  assert.equal(body.get('statuses-0-key'), 'done');
  assert.equal(body.get('statuses-1-key'), 'new');
  assert.equal(body.get('statuses-1-policy'), 'Najpierw zakres pracy');
  assert.deepEqual(body.getAll('statuses-1-transitions'), ['done', 'new']);
  assert.equal(configurationDraftSubmission(data).get('statuses-0-key'), 'new');
  assert.equal(body.get('types-0-key'), 'task');
});

test('new workflow stages become transition choices before saving and removal clears incoming transitions', () => {
  const data = fixture();
  const draft = formValues(data.sets[0].forms[2]);
  draft.set('statuses-2-key', 'review');
  draft.set('statuses-2-label', 'Weryfikacja');
  const staged = configurationStage(data, { section: 'statuses', index: 2 }, draft);
  const transitions = staged.sets[0].forms[0].fields.find(
    (item) => item.field_name === 'transitions',
  );
  assert.ok(
    transitions.choices.some(
      (choice) => choice.value === 'review' && choice.label === 'Weryfikacja',
    ),
  );
  const removed = configurationRemove(staged, 'statuses', [1]);
  assert.deepEqual(
    Array.from(configurationDraftSubmission(removed).getAll('statuses-0-transitions')),
    ['new'],
  );
});

test('workflow editor passes every process field to the stage dialog', () => {
  const data = fixture();
  data.sets[0].forms[0].fields.push(
    field('statuses-0-flow_stage', 'queue', { type: 'select' }),
    field('statuses-0-wip_limit', '', { type: 'number' }),
    field('statuses-0-policy', '', { type: 'textarea' }),
  );
  const app = hookHarness(
    formBundle.outputFiles[0].text,
    'ConfigurationForm',
    {
      initial: { api_url: '/api/v1/page/', data },
      section: 'statuses',
      workflowView: 'map',
      csrfToken: 'token',
      onSaved: async () => {},
      onStateChange() {},
    },
    { AbortController },
  );
  table(app.render()).props.onEdit(0);
  const tree = app.render();
  assert.equal(modal(tree).props.title, 'Edytuj etap');
  const fields = editorSchema(tree).fields.map((entry) => entry.field_name);
  assert.deepEqual(fields, [
    'key',
    'label',
    'category',
    'transitions',
    'flow_stage',
    'wip_limit',
    'policy',
  ]);
  assert.equal(fields.includes('DELETE'), false);
});

const stageBundle = await build({
  entryPoints: [new URL('../src/spaces/WorkflowStageFields.tsx', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  jsx: 'automatic',
  external: ['react', 'react/jsx-runtime', 'react-dom'],
  write: false,
});
class StageInput {
  constructor(name, value) {
    this.name = name;
    this.value = value;
  }
}

test('editing a stage name preserves its visible key, transitions and board positions', () => {
  const data = fixture();
  data.sets[0].forms[0].fields.push(
    field('statuses-0-position_x', '0', { hidden: true }),
    field('statuses-0-position_y', '240', { hidden: true }),
  );
  const app = hookHarness(
    stageBundle.outputFiles[0].text,
    'default',
    { data, schema: configurationEditorSchema(data.sets[0].forms[0]), adding: false },
    { HTMLInputElement: StageInput },
  );
  let tree = app.render();
  nodes(tree)
    .find((node) => node.props.className === 'space-settings-fields work-flow-stage-form')
    .props.onInput({ target: new StageInput('statuses-0-label', 'Nowa nazwa kolejki') });
  tree = app.render();
  const inputs = nodes(tree).filter((node) => node.type === 'input');
  assert.equal(
    nodes(tree).find((node) => node.props?.field?.field_name === 'key').props.field.value,
    'new',
  );
  assert.deepEqual(
    inputs
      .filter((node) => node.props.name === 'statuses-0-transitions')
      .map((node) => node.props.value),
    ['done', 'new'],
  );
  for (const [name, value] of [
    ['position_x', '0'],
    ['position_y', '240'],
  ]) {
    const control = nodes(tree).find((node) => node.props?.field?.field_name === name);
    assert.equal(control.props.field.value, value);
  }
});

test('adding a stage derives a unique key from its name and allows an explicit key override', () => {
  const data = fixture();
  const app = hookHarness(
    stageBundle.outputFiles[0].text,
    'default',
    { data, schema: configurationEditorSchema(data.sets[0].forms[2]), adding: true },
    { HTMLInputElement: StageInput },
  );
  let tree = app.render();
  nodes(tree)
    .find((node) => node.props.className === 'space-settings-fields work-flow-stage-form')
    .props.onInput({ target: new StageInput('statuses-2-label', 'New') });
  tree = app.render();
  assert.equal(
    nodes(tree).find((node) => node.props?.field?.field_name === 'key').props.field.value,
    'new_2',
  );
  assert.equal(
    nodes(tree).some((node) => node.props?.field?.field_name === 'key' && !node.props.field.hidden),
    true,
  );
  nodes(tree)
    .find((node) => node.props.className === 'space-settings-fields work-flow-stage-form')
    .props.onInput({ target: new StageInput('statuses-2-label', 'Do sprawdzenia') });
  assert.equal(
    nodes(app.render()).find((node) => node.props?.field?.field_name === 'key').props.field.value,
    'do_sprawdzenia',
  );
  tree = app.render();
  const keyControl = nodes(tree).find((node) => node.props?.field?.field_name === 'key');
  const edit = nodes(tree).find(
    (node) => node.props.className === 'space-settings-fields work-flow-stage-form',
  ).props.onInput;
  edit({ target: new StageInput('statuses-2-key', 'moj_klucz') });
  edit({ target: new StageInput('statuses-2-label', 'Inna nazwa') });
  assert.strictEqual(
    nodes(app.render()).find((node) => node.props?.field?.field_name === 'key').props.field,
    keyControl.props.field,
    'Manual key input must not be recreated or overwritten when the name changes',
  );
});

test('generating the new stage key keeps the imperative name control stable while typing', () => {
  const data = fixture();
  const app = hookHarness(
    stageBundle.outputFiles[0].text,
    'default',
    { data, schema: configurationEditorSchema(data.sets[0].forms[2]), adding: true },
    { HTMLInputElement: StageInput },
  );
  let tree = app.render();
  const nameField = nodes(tree).find((node) => node.props?.field?.field_name === 'label').props
    .field;
  // FieldControl recreates its DOM input whenever this object changes. Updating
  // the generated key must therefore retain this object, typed text and focus.
  for (const label of ['D', 'Do', 'Do sprawdzenia']) {
    nodes(tree)
      .find((node) => node.props.className === 'space-settings-fields work-flow-stage-form')
      .props.onInput({ target: new StageInput('statuses-2-label', label) });
    tree = app.render();
    assert.strictEqual(
      nodes(tree).find((node) => node.props?.field?.field_name === 'label').props.field,
      nameField,
    );
    assert.equal(
      nodes(tree).find((node) => node.props?.field?.field_name === 'key').props.field.value,
      configurationStatusKey(data, label),
    );
  }
});

test('stage icons keep their own default while editing keys, and new stages allow WIP', () => {
  const data = fixture();
  const statuses = data.sets[0];
  statuses.forms = statuses.forms.slice(0, 1);
  statuses.forms[0].fields.push(
    field('statuses-0-flow_stage', 'queue', { type: 'select' }),
    field('statuses-0-wip_limit', '', { type: 'number', attrs: { readonly: 'true' } }),
    field('statuses-0-icon', '', {
      type: 'select',
      choices: [
        { value: '', label: 'Domyślna dla etapu', icon: 'circle-dashed' },
        { value: 'hourglass', label: 'Oczekiwanie', icon: 'hourglass' },
        {
          value: 'rocket',
          label: 'Dotychczasowa ikona: Wdrożenie',
          icon: 'rocket',
          preserve_only: true,
        },
      ],
    }),
  );
  data.type_icon_defaults = { task: 'square-check' };
  const edited = rowDraft(data, 'statuses', 0);
  edited.set('statuses-0-key', 'task');
  edited.set('statuses-0-icon', 'hourglass');
  const staged = configurationStage(data, { section: 'statuses', index: 0 }, edited);
  const icon = staged.sets[0].forms[0].fields.find((entry) => entry.field_name === 'icon');
  assert.equal(icon.value, 'hourglass');
  assert.equal(icon.choices[0].icon, 'circle-dashed');
  assert.equal(configurationDraftSubmission(staged).get('statuses-0-icon'), 'hourglass');
  const added = configurationAdd(staged, 'statuses');
  const fields = Object.fromEntries(
    added.data.sets[0].forms[added.index].fields.map((entry) => [entry.field_name, entry]),
  );
  assert.equal(fields.category.value, 'in_progress');
  assert.equal(fields.flow_stage.value, 'active');
  assert.equal(fields.wip_limit.attrs.readonly, undefined);
  assert.equal(fields.icon.value, '');
  assert.equal(fields.icon.choices[0].icon, 'clock');
  assert.deepEqual(
    fields.icon.choices.map((choice) => choice.value),
    ['', 'hourglass'],
  );
});
