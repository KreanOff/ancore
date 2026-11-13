import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';
import ts from 'typescript';

const bundle = await build({
  stdin: {
    contents: `export * from './src/calendar/colors';
      export { default as CalendarPage } from './src/calendar/CalendarPage';`,
    resolveDir: new URL('..', import.meta.url).pathname,
  },
  bundle: true,
  platform: 'node',
  format: 'cjs',
  external: ['react', 'react/jsx-runtime', 'react-dom'],
  write: false,
});
const require = createRequire(import.meta.url);
const event = {
  id: 7,
  title: 'Własny kolor',
  description: '',
  start: '2026-11-12T09:00:00',
  end: '2026-11-12T10:00:00',
  all_day: false,
  color: '#8B25C7',
  source: 'events',
};

function render(view = 'month', value = event) {
  const module = { exports: {} };
  const react = {
    ...require('react'),
    useState(initial) {
      // Inject the same event feed boundary as the calendar's state.
      const state = typeof initial === 'function' ? initial() : initial;
      return [Array.isArray(state) ? [value] : state === 'month' ? view : state, () => {}];
    },
    useRef: (current) => ({ current }),
    useMemo: (calculate) => calculate(),
    useEffect() {},
  };
  vm.runInNewContext(bundle.outputFiles[0].text, {
    module,
    exports: module.exports,
    require: (name) => (name === 'react' ? react : require(name)),
    Date,
  });
  const tree = module.exports.CalendarPage({
    csrfToken: 'token',
    initial: {
      api_url: '/api/',
      data: {
        config: {
          initialYear: 2026,
          initialMonth: 11,
          initialDay: 12,
          urls: { events: '/calendar/events/' },
        },
      },
    },
  });
  return { tree, ...module.exports };
}

function nodes(element) {
  if (!element || typeof element !== 'object') return [];
  if (Array.isArray(element)) return element.flatMap(nodes);
  if (!element.props) return [];
  return [element, ...Object.values(element.props).flatMap(nodes)];
}

test('saving refreshes the sidebar and reopening immediately uses the saved color', () => {
  const window = new EventTarget();
  let changes = 0;
  window.addEventListener('ancore:calendar-changed', () => changes++);
  const module = { exports: {} },
    slots = [];
  let cursor = 0;
  const react = {
    ...require('react'),
    useState(initial) {
      const index = cursor++;
      if (!(index in slots)) {
        const value = typeof initial === 'function' ? initial() : initial;
        slots[index] = Array.isArray(value) ? [event] : value;
      }
      return [
        slots[index],
        (next) => {
          slots[index] = typeof next === 'function' ? next(slots[index]) : next;
        },
      ];
    },
    useRef: (current) => ({ current }),
    useMemo: (calculate) => calculate(),
    useEffect() {},
  };
  vm.runInNewContext(bundle.outputFiles[0].text, {
    module,
    exports: module.exports,
    require: (name) => (name === 'react' ? react : require(name)),
    Date,
    window,
    Event,
  });
  const page = () => {
    cursor = 0;
    return module.exports.CalendarPage({
      csrfToken: 'token',
      initial: {
        api_url: '/api/',
        data: {
          config: {
            initialYear: 2026,
            initialMonth: 11,
            initialDay: 12,
            urls: { events: '/calendar/events/' },
          },
        },
      },
    });
  };
  const eventButton = (tree) =>
    nodes(tree).find(
      (node) => node.type === 'button' && node.props.className?.startsWith('calendar-event '),
    );
  eventButton(page()).props.onClick({ stopPropagation() {} });
  const editor = nodes(page()).find((node) => node.type?.name === 'EventEditor');
  editor.props.onSaved('Zapisano', { ...event, color: '#123abc' });
  assert.equal(changes, 1);
  const updated = eventButton(page());
  assert.equal(updated.props.style['--calendar-event-color'], '#123abc');
  updated.props.onClick({ stopPropagation() {} });
  assert.equal(
    nodes(page()).find((node) => node.type?.name === 'EventEditor').props.event.color,
    '#123abc',
  );
  nodes(page())
    .find((node) => node.type?.name === 'EventEditor')
    .props.onSaved('Usunięto');
  assert.equal(changes, 2);
});

for (const view of ['month', 'week', 'day']) {
  test(`custom event color reaches the ${view} grid`, () => {
    const { tree } = render(view);
    const buttons = nodes(tree).filter(
      (node) => node.type === 'button' && node.props.className?.startsWith('calendar-event '),
    );
    assert.ok(buttons.some((node) => node.props.className.startsWith('calendar-event ')));
    for (const button of buttons) {
      assert.equal(button.props.style['--calendar-event-color'], '#8b25c7');
      assert.match(button.props.style['--calendar-event-bg'], /#8b25c7/);
      assert.equal(button.props.style['--calendar-event-ink'], 'var(--text-primary)');
      assert.doesNotMatch(button.props.className, /#/);
    }
    if (view !== 'month') {
      const timed = buttons.find((node) => node.props.className.includes('calendar-time-event'));
      assert.ok(timed.props.style.top, 'custom colors preserve time-grid positioning');
      assert.ok(timed.props.style.height);
    }
  });
}

test('editing named palette colors to HEX preserves their exact appearance', () => {
  const { calendarColor, calendarColorStyle } = render();
  for (const [name, hex, background] of [
    ['red', '#e04f63', '#fff1f3'],
    ['blue', '#4f7edb', '#edf3ff'],
    ['green', '#43a36a', '#edf9f1'],
    ['amber', '#d79a35', '#fff7e8'],
    ['slate', '#7b8493', '#f1f3f6'],
  ]) {
    assert.equal(calendarColor(name), hex);
    assert.equal(calendarColorStyle(name)['--calendar-event-bg'], background);
    assert.deepEqual(calendarColorStyle(name), calendarColorStyle(hex));
  }
});

test('invalid colors never reach inline styles or class names', () => {
  const { calendarColor, calendarColorStyle, calendarColorClass } = render();
  for (const value of ['#abc', 'transparent', 'var(--x)', 'red;display:none', '__proto__', '']) {
    assert.equal(calendarColor(value), '#e04f63');
    assert.equal(calendarColorStyle(value)['--calendar-event-color'], '#e04f63');
    assert.equal(calendarColorClass(value), 'custom');
  }
});

test('fallback calendar renders the same safe colors and backgrounds as React', async () => {
  const source = ts.createSourceFile(
    'calendar.js',
    await readFile(new URL('../../../static/js/calendar.js', import.meta.url), 'utf8'),
    ts.ScriptTarget.Latest,
    true,
  );
  const declarations = [];
  function visit(node) {
    if (
      ts.isVariableDeclaration(node) &&
      ['DEFAULT_EVENT_COLOR', 'EVENT_COLORS'].includes(node.name.getText())
    )
      declarations.push(`const ${node.getText()};`);
    if (
      ts.isFunctionDeclaration(node) &&
      ['calendarColor', 'calendarColorClass', 'applyEventColor'].includes(node.name?.text)
    )
      declarations.push(node.getText());
    ts.forEachChild(node, visit);
  }
  visit(source);
  const scope = {};
  vm.runInNewContext(declarations.join('\n'), scope);
  const { calendarColorStyle, calendarColorClass } = render();
  for (const value of [
    'red',
    'blue',
    'green',
    'amber',
    'slate',
    '#8B25C7',
    '#ffffff',
    '#000000',
    'bad',
  ]) {
    const style = {};
    scope.applyEventColor(
      { style: { setProperty: (name, value) => (style[name] = value) } },
      value,
    );
    assert.deepEqual(style, { ...calendarColorStyle(value) });
    assert.equal(scope.calendarColorClass(value), calendarColorClass(value));
  }
});
