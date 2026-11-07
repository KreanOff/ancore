import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

const bundle = await build({
  stdin: {
    contents: `export { default as CalendarPage } from './src/calendar/CalendarPage';
      export { EventEditor } from './src/calendar/EventEditor';
      export { SettingsFields } from './src/workspaces/WorkspaceForm';`,
    resolveDir: new URL('..', import.meta.url).pathname,
  },
  bundle: true,
  platform: 'node',
  format: 'cjs',
  external: ['react', 'react/jsx-runtime', 'react-dom'],
  write: false,
});
const require = createRequire(import.meta.url);

function nodes(element) {
  if (!element || typeof element !== 'object') return [];
  if (Array.isArray(element)) return element.flatMap(nodes);
  if (!element.props) return [];
  const children = Object.values(element.props).flatMap(nodes);
  if (['FieldErrors', 'ModuleFields'].includes(element.type?.name))
    children.push(...nodes(element.type(element.props)));
  return [element, ...children];
}
function text(element) {
  if (element == null || typeof element === 'boolean') return '';
  if (Array.isArray(element)) return element.map(text).join('');
  return typeof element === 'object' ? text(element.props?.children) : String(element);
}
function harness() {
  const slots = [];
  let cursor = 0;
  let effects = [];
  const slot = (initialize) => {
    const index = cursor++;
    if (!(index in slots)) slots[index] = initialize();
    return slots[index];
  };
  const react = {
    ...require('react'),
    useState(initial) {
      const state = slot(() => ({ value: typeof initial === 'function' ? initial() : initial }));
      return [
        state.value,
        (next) => (state.value = typeof next === 'function' ? next(state.value) : next),
      ];
    },
    useRef: (value) => slot(() => ({ current: value })),
    useMemo: (calculate) => calculate(),
    useEffect: (effect) => effects.push(effect),
  };
  class TestFormData extends FormData {
    constructor(form) {
      super();
      for (const [name, value] of Object.entries(form?.values || {})) this.set(name, value);
    }
  }
  const module = { exports: {} };
  let response = { error: 'Sprawdź formularz.', errors: {} };
  vm.runInNewContext(bundle.outputFiles[0].text, {
    module,
    exports: module.exports,
    require: (name) => (name === 'react' ? react : require(name)),
    Date,
    Error,
    TypeError,
    URL,
    URLSearchParams,
    AbortController,
    AbortSignal,
    FormData: TestFormData,
    location: { origin: 'https://ancore.test' },
    window: {},
    fetch: async () => ({
      ok: false,
      status: 400,
      headers: { get: () => 'application/json' },
      json: async () => response,
    }),
  });
  return {
    render(component, props) {
      cursor = 0;
      effects = [];
      return module.exports[component](props);
    },
    effects: () => effects.forEach((effect) => effect()),
    failWith: (next) => (response = next),
  };
}

for (const readOnly of [true, false]) {
  test(`calendar creation affordances respect read_only=${readOnly} in month, week and day`, () => {
    const app = harness();
    const props = {
      csrfToken: 'token',
      initial: {
        api_url: '/api/',
        read_only: readOnly,
        data: {
          config: {
            initialYear: 2026,
            initialMonth: 11,
            initialDay: 5,
            initialEventId: null,
            urls: { events: '/events/', create: '/events/new/' },
          },
        },
      },
    };
    let tree = app.render('CalendarPage', props);
    for (const label of ['Miesiąc', 'Tydzień', 'Dzień']) {
      const view = nodes(tree).find((node) => node.type === 'button' && text(node) === label);
      assert.ok(view, `${label} remains accessible in read-only mode`);
      assert.ok(!view.props.disabled);
      view.props.onClick();
      tree = app.render('CalendarPage', props);
      const creation = nodes(tree).filter(
        (node) =>
          node.type === 'button' &&
          (/^Dodaj (całodzienne )?wydarzenie:/.test(node.props['aria-label'] || '') ||
            ['Nowe wydarzenie', 'Dodaj w tym dniu'].includes(text(node))),
      );
      assert.ok(creation.length > 2);
      assert.ok(creation.every((node) => node.props.disabled === readOnly));
    }
    if (readOnly) assert.doesNotMatch(text(tree), /Dodaj wydarzenie i zaplanuj ten dzień/);
  });
}

for (const field of ['title', 'description', 'start', 'end', 'all_day', 'color', null]) {
  test(`calendar failed save connects ${field || 'general'} error and restores usable focus`, async () => {
    const app = harness();
    app.failWith({
      error: 'Sprawdź formularz.',
      errors: field ? { [field]: ['Popraw wartość.'] } : {},
    });
    const props = {
      event: null,
      date: new Date(2026, 10, 5, 9),
      api: '/api/',
      csrfToken: 'token',
      urls: { create: '/events/new/', update: '', delete: '' },
      onClose() {},
      onSaved() {
        assert.fail('Validation failure must not close the editor');
      },
    };
    let tree = app.render('EventEditor', props);
    const form = nodes(tree).find((node) => node.type === 'form');
    let focused = '';
    const invalidControl = { focus: () => (focused = 'field') };
    form.ref.current = {
      values: { title: 'Plan', start: '2026-11-05T09:00', end: '2026-11-05T10:00' },
      querySelector: () => (field ? invalidControl : null),
    };
    await form.props.onSubmit({ preventDefault() {} });
    tree = app.render('EventEditor', props);
    const summary = nodes(tree).find((node) => node.props.tabIndex === -1);
    assert.ok(summary);
    summary.ref.current = { focus: () => (focused = 'summary') };
    if (field) {
      const control = nodes(tree).find(
        (node) =>
          node.props.name === field ||
          (field === 'color' && node.props.label === 'Kolor wydarzenia'),
      );
      const attributes = field === 'color' ? control.props.triggerProps : control.props;
      assert.equal(attributes['aria-invalid'], true);
      const description = nodes(tree).find(
        (node) => node.props.id === attributes['aria-describedby'],
      );
      assert.equal(text(description), 'Popraw wartość.');
    }
    app.effects();
    assert.equal(focused, field ? 'field' : 'summary');
  });
}

test('workspace field errors remain beside and associated with each invalid control', () => {
  const app = harness();
  const tree = app.render('SettingsFields', {
    schema: {
      fields: [
        { name: 'name', errors: ['Nazwa jest zajęta.'] },
        { name: 'description', errors: ['Opis jest za długi.'] },
        {
          name: 'enabled_modules',
          label: 'Moduły',
          errors: ['Wybierz dostępny moduł.'],
          value: [],
          choices: [{ value: 'spaces', label: 'Przestrzenie', description: 'Zadania' }],
        },
      ],
    },
    id: 'workspace-create-form',
    name: 'Zespół',
    description: 'Opis',
    setName() {},
    setDescription() {},
  });
  for (const name of ['name', 'description', 'enabled_modules']) {
    const control = nodes(tree).find((node) => node.props.name === name);
    assert.equal(control.props['aria-invalid'], true);
    const descriptions = control.props['aria-describedby'].split(' ');
    assert.ok(
      descriptions.some((id) =>
        nodes(tree).some((node) => node.props.id === id && node.props.role === 'alert'),
      ),
    );
  }
});
