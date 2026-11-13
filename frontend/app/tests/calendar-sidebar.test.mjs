import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';
import ts from 'typescript';

process.env.TZ = 'Europe/Warsaw';
const bundle = await build({
  entryPoints: [new URL('../src/calendar/CalendarPage.tsx', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  external: ['react', 'react/jsx-runtime', 'react-dom'],
  write: false,
});
const require = createRequire(import.meta.url);
const colors = ['red', '#8B25C7', 'blue', 'green', '#123abc', 'amber'];
const expectedColors = ['#e04f63', '#8b25c7', '#4f7edb', '#43a36a', '#123abc', '#d79a35'];
const events = colors.map((color, index) => ({
  id: index + 1,
  title: `Wydarzenie ${index + 1}`,
  description: '',
  start: `2026-11-13T${index === 0 ? '00' : String(8 + index).padStart(2, '0')}:00:00+01:00`,
  end: `2026-11-13T${index === 0 ? '23:59' : String(9 + index).padStart(2, '0') + ':00'}:00+01:00`,
  all_day: index === 0,
  color,
  source: 'events',
}));
const feed = [
  ...events,
  ...[12, 14].map((day) => ({
    ...events[1],
    id: day,
    title: `Inny dzień ${day}`,
    start: `2026-11-${day}T09:00:00+01:00`,
    end: `2026-11-${day}T10:00:00+01:00`,
  })),
];

function nodes(element) {
  if (!element || typeof element !== 'object') return [];
  if (Array.isArray(element)) return element.flatMap(nodes);
  if (!element.props) return [];
  return [element, ...Object.values(element.props).flatMap(nodes)];
}
function text(element) {
  if (element == null || typeof element === 'boolean') return '';
  if (Array.isArray(element)) return element.map(text).join('');
  return typeof element === 'object' ? text(element.props?.children) : String(element);
}
const classNodes = (tree, name) =>
  nodes(tree).filter((node) => (node.props.className || '').split(' ').includes(name));
const button = (tree, label) =>
  nodes(tree).find((node) => node.type === 'button' && text(node) === label);
const editor = (tree) => nodes(tree).find((node) => node.type?.name === 'EventEditor');

function harness(readOnly = false) {
  const slots = [];
  let cursor = 0;
  const react = {
    ...require('react'),
    useState(initial) {
      const index = cursor++;
      if (!(index in slots)) {
        const value = typeof initial === 'function' ? initial() : initial;
        // Seed the event-feed boundary; all view/filter/editor handlers remain real.
        slots[index] = Array.isArray(value) ? feed : value;
      }
      return [
        slots[index],
        (next) => (slots[index] = typeof next === 'function' ? next(slots[index]) : next),
      ];
    },
    useRef(initial) {
      const index = cursor++;
      return (slots[index] ||= { current: initial });
    },
    useMemo: (calculate) => calculate(),
    useEffect() {},
  };
  const module = { exports: {} };
  vm.runInNewContext(bundle.outputFiles[0].text, {
    module,
    exports: module.exports,
    require: (name) => (name === 'react' ? react : require(name)),
    Date,
    window: {},
  });
  return {
    render() {
      cursor = 0;
      return module.exports.default({
        csrfToken: 'token',
        initial: {
          api_url: '/api/',
          read_only: readOnly,
          data: {
            config: {
              initialYear: 2026,
              initialMonth: 11,
              initialDay: 1,
              urls: { events: '/calendar/events/' },
            },
          },
        },
      });
    },
  };
}

test('calendar views leave the shared sidebar to the shell without a second agenda or portal', () => {
  const app = harness();
  let tree = app.render();
  for (const view of ['Miesiąc', 'Tydzień', 'Dzień', 'Rok']) {
    button(tree, view).props.onClick();
    tree = app.render();
    assert.equal(
      nodes(tree).filter((node) =>
        ['RightSidebarContent', 'TodaySidebar'].includes(node.type?.name),
      ).length,
      0,
    );
    assert.equal(classNodes(tree, 'calendar-sidebar').length, 0);
    assert.equal(classNodes(tree, 'today-sidebar').length, 0);
    assert.doesNotMatch(text(tree), /Plan dnia|Cały okres|Dodaj w tym dniu/);
    assert.equal(classNodes(tree, 'calendar-main').length, 1);
  }
});

for (const readOnly of [false, true]) {
  test(`month overflow reveals all events in the correct day, read_only=${readOnly}`, () => {
    const app = harness(readOnly);
    let tree = app.render();
    const cell = nodes(tree).find((node) => node.props['data-calendar-date'] === '2026-11-13');
    assert.equal(classNodes(cell, 'calendar-event').length, 3);
    const more = button(cell, '+3 więcej');
    assert.ok(more);
    assert.ok(!more.props.disabled, 'reading additional events remains available to guests');
    let stopped = false;
    more.props.onClick({ stopPropagation: () => (stopped = true) });
    tree = app.render();
    assert.equal(stopped, true);
    assert.equal(button(tree, 'Dzień').props['aria-pressed'], true);
    assert.equal(classNodes(tree, 'calendar-view--day').length, 1);
    assert.match(text(classNodes(tree, 'calendar-week-day-head')[0]), /13/);
    const visible = classNodes(tree, 'calendar-event');
    assert.equal(visible.length, 6);
    assert.doesNotMatch(text(tree), /Inny dzień/);
    for (const [index, event] of events.entries()) {
      const rendered = visible.find(
        (node) => text(classNodes(node, 'calendar-event-title')[0]) === event.title,
      );
      assert.ok(rendered, `${event.title} remains visible after expansion`);
      assert.equal(rendered.props.style['--calendar-event-color'], expectedColors[index]);
    }
    assert.equal(classNodes(tree, 'calendar-event-more').length, 0);
    assert.equal(editor(tree), undefined, 'overflow switches views without opening an editor');
  });

  test(`header and cell creation preserve permissions, read_only=${readOnly}`, () => {
    const app = harness(readOnly);
    let tree = app.render();
    const header = button(tree, 'Nowe wydarzenie');
    assert.equal(header.props.disabled, readOnly);
    header.props.onClick();
    tree = app.render();
    if (readOnly) assert.equal(editor(tree), undefined);
    else {
      assert.equal(editor(tree).props.event, null);
      assert.equal(editor(tree).props.date.getDate(), 1);
      editor(tree).props.onClose();
      tree = app.render();
    }
    const cell = nodes(tree).find((node) => node.props['data-calendar-date'] === '2026-11-13');
    const add = classNodes(cell, 'calendar-day-add')[0];
    assert.equal(add.props.disabled, readOnly);
    add.props.onClick({ stopPropagation() {} });
    tree = app.render();
    if (readOnly) assert.equal(editor(tree), undefined);
    else {
      assert.equal(editor(tree).props.event, null);
      assert.equal(editor(tree).props.date.getDate(), 13);
      assert.equal(editor(tree).props.date.getMonth(), 10);
      assert.equal(editor(tree).props.date.getHours(), 9);
    }
  });
}

test('fallback month overflow opens the chosen day without touching sidebar DOM', async () => {
  const source = ts.createSourceFile(
    'calendar.js',
    await readFile(new URL('../../../static/js/calendar.js', import.meta.url), 'utf8'),
    ts.ScriptTarget.Latest,
    true,
  );
  const functions = [];
  function visit(node) {
    if (
      ts.isFunctionDeclaration(node) &&
      ['appendEventsToCell', 'setView'].includes(node.name?.text)
    )
      functions.push(node.getText());
    ts.forEachChild(node, visit);
  }
  visit(source);
  const chosenDay = new Date(2026, 10, 13);
  const children = [],
    views = [],
    fetches = [];
  const scope = {
    document: {
      createElement: () => ({
        handlers: {},
        addEventListener(name, callback) {
          this.handlers[name] = callback;
        },
      }),
      querySelectorAll: () => [],
      querySelector: () => assert.fail('overflow must not access sidebar DOM'),
    },
    MAX_EVENTS_PER_CELL: 3,
    createEventButton: (event) => ({ event }),
    cloneDate: (date) => new Date(date),
    selectedDate: new Date(2026, 10, 1),
    anchorDate: new Date(2026, 10, 1),
    currentView: 'month',
    viewContainers: { month: {}, day: {} },
    scrollTimeGrid: false,
    renderCurrentView: () => views.push(scope.currentView),
    fetchEvents: () => fetches.push(new Date(scope.anchorDate)),
  };
  vm.runInNewContext(functions.join('\n'), scope);
  scope.appendEventsToCell({ appendChild: (child) => children.push(child) }, events, 3, chosenDay);
  assert.equal(children.length, 4);
  assert.equal(children[3].textContent, '+3 więcej');
  children[3].handlers.click({ stopPropagation() {} });
  assert.equal(scope.currentView, 'day');
  assert.equal(scope.selectedDate.getTime(), chosenDay.getTime());
  assert.equal(scope.anchorDate.getTime(), chosenDay.getTime());
  assert.equal(scope.scrollTimeGrid, true);
  assert.deepEqual(views, ['day']);
  assert.equal(fetches.length, 1);
  assert.equal(fetches[0].getTime(), chosenDay.getTime());
});
