import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

// Exercise the shared menu's real callbacks; only React state and navigation are boundaries.
const bundle = await build({
  entryPoints: [new URL('../src/spaces/ItemToolbar.tsx', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  external: ['react', 'react/jsx-runtime', '../shared/page'],
  write: false,
});
const require = createRequire(import.meta.url);

function harness(data, url = '/space/produkt/?view=overview') {
  const states = [],
    navigations = [];
  let cursor = 0,
    closed = 0;
  const react = {
    ...require('react'),
    useState(initial) {
      const index = cursor++;
      if (!(index in states)) states[index] = initial;
      return [
        states[index],
        (value) => {
          states[index] = typeof value === 'function' ? value(states[index]) : value;
        },
      ];
    },
  };
  const module = { exports: {} };
  vm.runInNewContext(bundle.outputFiles[0].text, {
    module,
    exports: module.exports,
    URL,
    location: { origin: 'http://localhost' },
    require: (name) =>
      name === 'react'
        ? react
        : name === '../shared/page'
          ? { navigate: (target) => navigations.push(target) }
          : require(name),
  });
  return {
    navigations,
    get closed() {
      return closed;
    },
    render(next = {}) {
      cursor = 0;
      data = { ...data, ...next };
      const dropdown = module.exports.ItemFiltering({ data, url });
      return { dropdown, menu: dropdown.props.children(() => closed++) };
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
function button(tree, label) {
  const match = nodes(tree).find(
    (node) =>
      node.type === 'button' && (node.props['aria-label'] === label || text(node) === label),
  );
  assert.ok(match, `Missing button: ${label}`);
  return match;
}
function search(tree, value) {
  const input = nodes(tree).find((node) => node.type === 'input');
  assert.ok(input);
  if (value !== undefined) input.props.onChange({ target: { value } });
  return input;
}
function choices(tree) {
  return nodes(tree).filter((node) => node.type === 'button' && node.props.role === 'radio');
}
function freeze(value) {
  if (value && typeof value === 'object') {
    Object.values(value).forEach(freeze);
    Object.freeze(value);
  }
  return value;
}
function data(filters = {}) {
  return freeze({
    filters: {
      q: 'Projekt',
      work_type: '',
      assignee: '',
      status: '',
      priority: '',
      team: '',
      summary: '',
      ...filters,
    },
    summary_filter_label: 'Otwarte zadania',
    filter_options: {
      work_type: [
        ['', 'Wszystkie typy'],
        ['task', 'Zadanie'],
        ['bug', 'Błąd'],
      ],
      assignee: [
        ['', 'Wszyscy wykonawcy'],
        ['me', 'Przypisane do mnie'],
        ['unassigned', 'Nieprzypisane'],
        ['17', 'Żaneta Śliwa'],
      ],
      status: [
        ['', 'Wszystkie statusy'],
        ['new', 'Do zrobienia'],
        ['in_progress', 'W toku'],
        ['closed', 'Gotowe'],
      ],
      priority: [
        ['', 'Wszystkie priorytety'],
        ['high', 'Wysoki'],
        ['low', 'Niski'],
      ],
      team: [
        ['', 'Wszystkie zespoły'],
        ['42', 'Zespół produktu'],
      ],
    },
  });
}

test('filter-only component exposes all five fields without sorting controls or a sort contract', () => {
  const { dropdown, menu } = harness(data()).render();
  assert.equal(dropdown.props.label, 'Filtrowanie zadań');
  assert.equal(dropdown.props.role, 'dialog');
  assert.equal(dropdown.props.triggerClassName.includes('is-active'), false);
  assert.equal(text(dropdown.props.trigger), 'Filtrowanie');
  assert.deepEqual(
    nodes(menu)
      .filter((node) => node.type === 'button')
      .map((node) => node.props['aria-label']),
    [
      'Filtr: Typ zgłoszenia',
      'Filtr: Wykonawca',
      'Filtr: Status',
      'Filtr: Priorytet',
      'Filtr: Zespół',
    ],
  );
  assert.equal(search(menu).props['aria-label'], 'Szukaj pola');
  assert.doesNotMatch(text(menu) + text(dropdown.props.trigger), /Sortowanie|Domyślnie|Wyczyść/);
});

test('active count and selected field labels include the summary drill-down and ignore free text', () => {
  const { dropdown, menu } = harness(
    data({
      work_type: 'bug',
      assignee: '17',
      status: 'closed',
      priority: 'high',
      team: '42',
      summary: 'open',
    }),
  ).render();
  const count = nodes(dropdown.props.trigger).find(
    (node) => node.props?.['aria-label'] === 'Aktywne filtry: 6',
  );
  assert.equal(text(count), '6');
  assert.equal(dropdown.props.triggerClassName.includes('is-active'), true);
  for (const [field, selected] of [
    ['Typ zgłoszenia', 'Błąd'],
    ['Wykonawca', 'Żaneta Śliwa'],
    ['Status', 'Gotowe'],
    ['Priorytet', 'Wysoki'],
    ['Zespół', 'Zespół produktu'],
  ]) {
    assert.equal(text(button(menu, `Filtr: ${field}`)), field + selected);
  }
  assert.equal(text(button(menu, 'Usuń filtr: Otwarte zadania')), 'PodsumowanieOtwarte zadania');
  assert.ok(button(menu, 'Wyczyść'));
});

test('field and option search, empty states, back and reopening use the same filter callbacks', () => {
  const app = harness(data({ priority: 'high' }));
  let view = app.render();
  search(view.menu, '  prIO  ');
  view = app.render();
  assert.equal(
    nodes(view.menu).filter(
      (node) => node.type === 'button' && node.props['aria-label']?.startsWith('Filtr:'),
    ).length,
    1,
  );
  button(view.menu, 'Filtr: Priorytet').props.onClick();
  view = app.render();
  assert.equal(search(view.menu).props.value, '');
  assert.equal(search(view.menu).props['aria-label'], 'Szukaj opcji');
  assert.deepEqual(choices(view.menu).map(text), ['Wszystkie priorytety', 'Wysoki', 'Niski']);
  assert.equal(button(view.menu, 'Wysoki').props['aria-checked'], true);
  search(view.menu, '  WYS  ');
  assert.deepEqual(choices(app.render().menu).map(text), ['Wysoki']);
  search(app.render().menu, 'nieistniejąca opcja');
  assert.match(text(app.render().menu), /Brak pasujących opcji/);
  button(app.render().menu, 'Wróć do pól filtrów').props.onClick();
  view = app.render();
  assert.equal(search(view.menu).props.value, '');
  search(view.menu, 'nieistniejące pole');
  assert.match(text(app.render().menu), /Brak pasujących pól/);
  app.render().dropdown.props.onOpen();
  view = app.render();
  assert.equal(search(view.menu).props.value, '');
  assert.ok(button(view.menu, 'Filtr: Status'));
  assert.equal(app.closed, 0);
  assert.deepEqual(app.navigations, []);
});

test('each filter option preserves a scoped overview URL and combined parameters while resetting page', () => {
  const path = '/workplaces/w_0123456789abcdefghijklmnop/space/produkt/';
  const existing = { work_type: 'task', assignee: 'me', status: 'new', priority: 'low', team: '8' };
  const url =
    path +
    '?view=overview&q=Projekt&summary=open&sort=title_desc&other=keep&page=4&' +
    new URLSearchParams(existing);
  for (const [field, label, key, value] of [
    ['Typ zgłoszenia', 'Błąd', 'work_type', 'bug'],
    ['Wykonawca', 'Żaneta Śliwa', 'assignee', '17'],
    ['Status', 'W toku', 'status', 'in_progress'],
    ['Priorytet', 'Wysoki', 'priority', 'high'],
    ['Zespół', 'Zespół produktu', 'team', '42'],
  ]) {
    const app = harness(data({ ...existing, summary: 'open' }), url);
    button(app.render().menu, `Filtr: ${field}`).props.onClick();
    button(app.render().menu, label).props.onClick();
    assert.equal(app.closed, 1);
    assert.equal(app.navigations.length, 1);
    const target = new URL(app.navigations[0], 'http://localhost');
    assert.equal(target.pathname, path);
    assert.deepEqual(Object.fromEntries(target.searchParams), {
      view: 'overview',
      q: 'Projekt',
      summary: 'open',
      sort: 'title_desc',
      other: 'keep',
      ...existing,
      [key]: value,
    });
  }
});

test('all-options clears only the chosen filter and clear-all retains search, view and sorting', () => {
  const filters = {
    work_type: 'bug',
    assignee: '17',
    status: 'closed',
    priority: 'high',
    team: '42',
    summary: 'open',
  };
  const url =
    '/space/produkt/?view=list&q=Projekt&sort=priority_desc&page=3&' + new URLSearchParams(filters);
  const app = harness(data(filters), url);
  button(app.render().menu, 'Filtr: Status').props.onClick();
  button(app.render().menu, 'Wszystkie statusy').props.onClick();
  let target = new URL(app.navigations[0], 'http://localhost');
  assert.equal(target.searchParams.has('status'), false);
  assert.equal(target.searchParams.get('priority'), 'high');
  assert.equal(target.searchParams.get('summary'), 'open');
  assert.equal(target.searchParams.has('page'), false);
  app.render().dropdown.props.onOpen();
  button(app.render().menu, 'Wyczyść').props.onClick();
  target = new URL(app.navigations[1], 'http://localhost');
  assert.deepEqual(Object.fromEntries(target.searchParams), {
    view: 'list',
    q: 'Projekt',
    sort: 'priority_desc',
  });
  assert.equal(app.closed, 2);
});

test('summary drill-down can be searched and removed without clearing the other filters', () => {
  const app = harness(
    data({ status: 'new', summary: 'open' }),
    '/space/produkt/?view=overview&status=new&summary=open&page=2',
  );
  search(app.render().menu, '  OTWARTE  ');
  const menu = app.render().menu;
  assert.equal(nodes(menu).filter((node) => node.type === 'button').length, 2);
  button(menu, 'Usuń filtr: Otwarte zadania').props.onClick();
  assert.equal(app.navigations[0], '/space/produkt/?view=overview&status=new');
  assert.equal(app.closed, 1);
});

test('block filtering combines with existing board filters and clear-all removes it', () => {
  const base = data({ priority: 'high', blocked: 'yes' });
  const blocked = {
    ...base,
    filter_options: {
      ...base.filter_options,
      blocked: [
        ['', 'Wszystkie zadania'],
        ['yes', 'Zablokowane'],
        ['no', 'Bez blokady'],
      ],
    },
  };
  const app = harness(blocked, '/space/produkt/?view=board&priority=high&blocked=yes');
  assert.ok(
    nodes(app.render().dropdown.props.trigger).some(
      (node) => node.props?.['aria-label'] === 'Aktywne filtry: 2',
    ),
  );
  button(app.render().menu, 'Filtr: Blokada').props.onClick();
  assert.equal(button(app.render().menu, 'Zablokowane').props['aria-checked'], true);
  button(app.render().menu, 'Bez blokady').props.onClick();
  assert.equal(app.navigations[0], '/space/produkt/?view=board&priority=high&blocked=no');
  app.render().dropdown.props.onOpen();
  button(app.render().menu, 'Wyczyść').props.onClick();
  assert.equal(app.navigations[1], '/space/produkt/?view=board');
});
