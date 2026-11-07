import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

// Run production callbacks and chart rendering, replacing only React's hook storage and navigation.
const bundle = await build({
  stdin: {
    contents: `${await readFile(new URL('../src/spaces/ReportsView.tsx', import.meta.url), 'utf8')}\nexport { TrendChart, ViewToolbar };`,
    sourcefile: 'ReportsView.tsx',
    resolveDir: new URL('../src/spaces', import.meta.url).pathname,
    loader: 'tsx',
  },
  bundle: true,
  platform: 'node',
  format: 'cjs',
  jsx: 'automatic',
  external: ['react', 'react/jsx-runtime', '../shared/page'],
  write: false,
});
const require = createRequire(import.meta.url);
function harness(name, initialProps) {
  const states = [],
    refs = [],
    effects = [],
    navigations = [];
  let cursor = 0,
    refCursor = 0,
    mounted = false,
    props = initialProps;
  const react = {
    ...require('react'),
    useId: () => 'report-test',
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
    useRef(value) {
      const index = refCursor++;
      return (refs[index] ||= { current: value });
    },
    useEffect(effect) {
      if (!mounted) effects.push(effect());
    },
  };
  const module = { exports: {} };
  vm.runInNewContext(bundle.outputFiles[0].text, {
    module,
    exports: module.exports,
    URL,
    Error,
    TypeError,
    location: { origin: 'http://localhost' },
    require: (name) =>
      name === 'react'
        ? react
        : name === '../shared/page'
          ? { navigate: (url) => navigations.push(url) }
          : require(name),
  });
  // Render the stateless toolbar shell so its action slot matches the visible React tree.
  function renderToolbar(element) {
    if (!element || typeof element !== 'object') return element;
    if (Array.isArray(element)) return element.map(renderToolbar);
    if (element.type === module.exports.ViewToolbar || ['Toolbar', 'ToolbarContents'].includes(element.type?.name))
      return renderToolbar(element.type(element.props));
    return {
      ...element,
      props: { ...element.props, children: renderToolbar(element.props?.children) },
    };
  }
  return {
    navigations,
    render(next = {}) {
      cursor = 0;
      refCursor = 0;
      props = { ...props, ...next };
      const tree = renderToolbar(module.exports[name](props));
      mounted = true;
      return tree;
    },
    unmount() {
      effects.forEach((cleanup) => cleanup?.());
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
  const result = nodes(tree).find((node) => node.type === 'button' && text(node) === label);
  assert.ok(result, `Missing button: ${label}`);
  return result;
}
function data(total = 8, sprint = 'all') {
  return {
    space: { template: 'scrum', url: '/workplaces/example/space/product/' },
    filters: { assignee: '', status: '', priority: '', q: '', summary: '' },
    filter_options: {
      assignee: [
        ['', 'Wszyscy wykonawcy'],
        ['unassigned', 'Nieprzypisane'],
        ['8', 'Jan Kowalski'],
      ],
    },
    reports: {
      period: {
        days: 7,
        start_on: '2026-10-24',
        end_on: '2026-10-30',
        label: '24.10.2026 – 30.10.2026',
      },
      filters: { report_period: '7', report_sprint: sprint },
      filter_error: '',
      sprint_options: [
        { value: 'all', label: 'Wszystkie sprinty' },
        { value: 'none', label: 'Bez sprintu' },
      ],
      snapshot: {
        total,
        open: total,
        completed: 0,
        overdue: 0,
        completion_percent: 0,
        due_soon: 0,
        unassigned: total,
        points: 0,
        completed_points: 0,
        unestimated: total,
      },
      activity: { created: 1, completed: 1, logged_minutes: 15, logged_label: '15 min' },
      trend: Array.from({ length: 7 }, (_, index) => ({
        date: `2026-10-${24 + index}`,
        label: `${24 + index}.10`,
        created: index === 1 ? 1 : 0,
        completed: index === 4 ? 1 : 0,
        logged_minutes: index === 3 ? 15 : 0,
      })),
      statuses: [],
      priorities: [],
      workload: [],
      sprints: [],
      overdue: { total: 0, items: [] },
      export_url: '/workplaces/example/space/product/?view=reports&report_export=csv',
      reset_url: '/workplaces/example/space/product/?view=reports',
      generated_at: '2026-10-30T12:00:00Z',
    },
  };
}
function reportApp(value = data(), refresh = async () => {}) {
  return harness('default', {
    data: value,
    url: '/workplaces/example/space/product/?view=reports&report_period=7&report_sprint=none&status=new&page=3&list_limit_new=40&timeline_limit=40',
    refresh,
  });
}
function emptyTitle(tree) {
  return nodes(tree).find((node) => node.props?.illustration === 'tasks')?.props.title;
}
const settle = () => new Promise((resolve) => setImmediate(resolve));

test('empty report distinguishes a new space from an actively filtered result', () => {
  const app = reportApp(data(0));
  let tree = app.render();
  assert.equal(emptyTitle(tree), 'Raporty zaczynają się od zadań');
  assert.equal(
    nodes(tree).some((node) => node.type === 'a' && text(node) === 'Wyczyść filtry'),
    false,
  );
  tree = app.render({ data: data(0, 'none') });
  assert.equal(emptyTitle(tree), 'Brak zadań dla wybranych filtrów');
  assert.ok(nodes(tree).some((node) => node.type === 'a' && text(node) === 'Wyczyść filtry'));
  const invalid = data(0, '999');
  invalid.reports.filter_error = 'Wybrany sprint jest niedostępny.';
  tree = app.render({ data: invalid });
  assert.match(
    text(nodes(tree).find((node) => node.props?.role === 'alert')),
    /sprint jest niedostępny/,
  );
});

test('period and assignee changes preserve scoped report filters and remove stale paging', () => {
  const app = reportApp();
  const tree = app.render();
  nodes(tree)
    .find((node) => node.props?.name === 'report_period')
    .props.onChange('90');
  const target = new URL(app.navigations[0], 'http://localhost');
  assert.equal(target.pathname, '/workplaces/example/space/product/');
  assert.equal(target.searchParams.get('report_period'), '90');
  assert.equal(target.searchParams.get('report_sprint'), 'none');
  assert.equal(target.searchParams.get('status'), 'new');
  assert.equal(target.searchParams.get('view'), 'reports');
  for (const key of ['page', 'list_limit_new', 'timeline_limit'])
    assert.equal(target.searchParams.has(key), false);
  nodes(tree)
    .find((node) => node.props?.name === 'assignee')
    .props.onChange('unassigned');
  assert.equal(
    new URL(app.navigations[1], 'http://localhost').searchParams.get('assignee'),
    'unassigned',
  );
  const exported = nodes(tree).find((node) => node.type === 'a' && node.props.download);
  assert.equal(exported.props.href, data().reports.export_url);
});

test('trend provides an accessible chart and a complete table including zero-activity days', () => {
  const app = harness('TrendChart', { report: data().reports });
  let tree = app.render();
  assert.equal(nodes(tree).find((node) => node.type === 'svg').props.role, 'img');
  assert.match(text(tree), /Ponowne otwarcie zadania zmienia ten wynik/);
  assert.equal(button(tree, 'Tabela').props['aria-pressed'], false);
  button(tree, 'Tabela').props.onClick();
  tree = app.render();
  assert.equal(button(tree, 'Wykres').props['aria-pressed'], true);
  const body = nodes(tree).find((node) => node.type === 'tbody');
  const rows = nodes(body).filter((node) => node.type === 'tr');
  assert.equal(rows.length, 7);
  assert.deepEqual(
    nodes(rows[0])
      .filter((node) => node.type === 'td')
      .map(text),
    ['0', '0', '0'],
  );
  assert.deepEqual(
    nodes(rows[3])
      .filter((node) => node.type === 'td')
      .map(text),
    ['0', '0', '15'],
  );
  button(tree, 'Wykres').props.onClick();
  tree = app.render();
  assert.ok(nodes(tree).some((node) => node.type === 'svg'));
});

test('zero and high-volume trends keep finite coordinates and explain a quiet period', () => {
  for (const count of [0, 1, 50000]) {
    const report = data().reports;
    report.trend = report.trend.map((point, index) => ({
      ...point,
      created: index === 1 ? count : 0,
      completed: 0,
    }));
    report.activity.created = count;
    report.activity.completed = 0;
    const tree = harness('TrendChart', { report }).render();
    for (const path of nodes(tree).filter((node) => node.type === 'path')) {
      assert.doesNotMatch(path.props.d, /NaN|Infinity/);
      const coordinates = path.props.d.match(/-?\d+(?:\.\d+)?/g).map(Number);
      assert.ok(coordinates.every((value) => value >= 0 && value <= 680));
    }
    if (!count) assert.match(text(tree), /Brak utworzonych i zakończonych zadań/);
  }
});

test('refresh deduplicates requests, retains the report on failure and allows retry', async () => {
  let calls = 0,
    reject;
  const app = reportApp(data(), () => {
    calls++;
    return new Promise((_, fail) => {
      reject = fail;
    });
  });
  let tree = app.render();
  const control = button(tree, 'Odśwież');
  control.props.onClick();
  control.props.onClick();
  assert.equal(calls, 1);
  tree = app.render();
  assert.equal(button(tree, 'Odświeżanie…').props.disabled, true);
  reject(new Error('Raport jest chwilowo niedostępny.'));
  await settle();
  tree = app.render();
  assert.match(text(tree), /Raport jest chwilowo niedostępny/);
  assert.match(text(tree), /Stan bieżący/);
  button(tree, 'Spróbuj ponownie').props.onClick();
  assert.equal(calls, 2);
  reject(new Error('Ponów odczyt.'));
  await settle();
});

test('successful refresh announces completion and ignores late completion after unmount', async () => {
  let resolve;
  const app = reportApp(
    data(),
    () =>
      new Promise((done) => {
        resolve = done;
      }),
  );
  button(app.render(), 'Odśwież').props.onClick();
  resolve();
  await settle();
  let tree = app.render();
  assert.equal(
    text(nodes(tree).find((node) => node.props?.role === 'status')),
    'Raport został odświeżony.',
  );
  button(tree, 'Odśwież').props.onClick();
  app.unmount();
  resolve();
  await settle();
  tree = app.render();
  assert.equal(text(nodes(tree).find((node) => node.props?.role === 'status')), '');
});
