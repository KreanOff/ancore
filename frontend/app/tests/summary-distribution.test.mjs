import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

// Render the actual component and run its callbacks with only hook state controlled.
const bundle = await build({
  entryPoints: [new URL('../src/spaces/SummaryDistribution.tsx', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  external: ['react', 'react/jsx-runtime'],
  write: false,
});
const require = createRequire(import.meta.url);

function harness(props) {
  const states = [];
  let cursor = 0;
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
    require: (name) => (name === 'react' ? react : require(name)),
  });
  return {
    render(next = {}) {
      cursor = 0;
      props = { ...props, ...next };
      return module.exports.SummaryDistribution(props);
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
function hasClass(element, name) {
  return element.props?.className?.split(' ').includes(name);
}
function links(tree) {
  return nodes(tree).filter((node) => node.type === 'a');
}
function labels(tree) {
  return nodes(tree)
    .filter((node) => hasClass(node, 'work-summary-distribution-percent'))
    .map(text);
}
function control(tree, label) {
  return nodes(tree).find((node) => node.type === 'button' && node.props['aria-label'] === label);
}
function sortChoice(tree, label, onClose) {
  const dropdown = nodes(tree).find((node) => node.props?.label === 'Sortowanie: Typy zgłoszeń');
  const menu = dropdown.props.children(onClose);
  return nodes(menu).find((node) => node.type === 'button' && text(node).includes(label));
}
function row(key, count, percent) {
  return Object.freeze({
    key,
    label: key,
    count,
    percent,
    url: `/workplaces/test/space/produkt/?view=list&work_type=${key}`,
  });
}
const defaults = { title: 'Typy zgłoszeń', description: 'Dostępne zadania.' };

test('distribution exposes counts and exact shares, including zero and less than one percent', () => {
  const rows = Object.freeze([row('Zadanie', 250, 25), row('Puste', 0, 0), row('Rzadkie', 1, 0)]);
  const tree = harness({ ...defaults, rows, total: 1000 }).render();
  assert.deepEqual(labels(tree), ['25%', '0%', '<1%']);
  assert.equal(control(tree, 'Pokaż procenty').props['aria-pressed'], true);
  assert.equal(control(tree, 'Pokaż liczbę zadań').props['aria-pressed'], false);
  assert.deepEqual(
    links(tree).map((link) => link.props.href),
    rows.map((item) => item.url),
  );
  assert.match(links(tree)[2].props['aria-label'], /Rzadkie: 1 z 1000 zadań · <1%/);
  assert.match(links(tree)[1].props.title, /0 z 1000 zadań · 0%/);
  const fills = nodes(tree).filter((node) => hasClass(node, 'work-summary-distribution-fill'));
  assert.deepEqual(
    fills.map((fill) => fill.props.style['--summary-fill-width']),
    ['25%', '0%', '0.1%'],
  );
  const progress = nodes(tree).filter((node) => node.type === 'progress');
  assert.deepEqual(
    progress.map((node) => [node.props.value, node.props.max]),
    [
      [250, 1000],
      [0, 1000],
      [1, 1000],
    ],
  );
});

test('display mode and sorting callbacks update the rendered rows without mutating input', () => {
  const rows = Object.freeze([row('A', 1, 10), row('B', 5, 50), row('C', 4, 40)]);
  const app = harness({ ...defaults, rows, total: 10 });
  let tree = app.render();
  control(tree, 'Pokaż liczbę zadań').props.onClick();
  tree = app.render();
  assert.deepEqual(labels(tree), ['1', '5', '4']);
  assert.equal(control(tree, 'Pokaż liczbę zadań').props['aria-pressed'], true);
  assert.equal(control(tree, 'Pokaż procenty').props['aria-pressed'], false);
  let closed = 0;
  sortChoice(tree, 'Najwięcej zadań', () => closed++).props.onClick();
  tree = app.render();
  assert.deepEqual(
    links(tree).map((link) => link.props.href),
    [rows[1].url, rows[2].url, rows[0].url],
  );
  assert.equal(sortChoice(tree, 'Najwięcej zadań', () => {}).props['aria-checked'], true);
  assert.equal(closed, 1);
  sortChoice(tree, 'Kolejność domyślna', () => closed++).props.onClick();
  control(tree, 'Pokaż procenty').props.onClick();
  tree = app.render();
  assert.deepEqual(
    links(tree).map((link) => link.props.href),
    rows.map((item) => item.url),
  );
  assert.deepEqual(labels(tree), ['10%', '50%', '40%']);
  assert.equal(closed, 2);
  assert.deepEqual(
    rows.map((item) => item.key),
    ['A', 'B', 'C'],
  );
});

test('active sorting uses fresh rows and preserves default order for tied counts', () => {
  const app = harness({ ...defaults, rows: [row('A', 1, 10)], total: 10 });
  sortChoice(app.render(), 'Najwięcej zadań', () => {}).props.onClick();
  const rows = Object.freeze([row('B', 2, 20), row('A', 3, 30), row('C', 3, 30)]);
  const tree = app.render({ rows });
  assert.deepEqual(
    links(tree).map((link) => link.props.href),
    [rows[1].url, rows[2].url, rows[0].url],
  );
});

test('empty workload keeps its useful empty state without controls or empty chart columns', () => {
  const tree = harness({
    ...defaults,
    title: 'Obciążenie zespołu',
    rows: [],
    total: 0,
    people: true,
    className: 'work-summary-workload',
  }).render();
  assert.equal(hasClass(tree, 'work-summary-workload'), true);
  assert.match(text(tree), /Brak otwartych zadań/);
  assert.equal(
    nodes(tree).some((node) => hasClass(node, 'work-summary-controls')),
    false,
  );
  assert.equal(
    nodes(tree).some((node) => hasClass(node, 'work-summary-distribution-heading')),
    false,
  );
  assert.equal(
    nodes(tree).some((node) => node.type === 'progress'),
    false,
  );
});

test('empty type totals remain finite and every zero category stays available as a drill-down', () => {
  const tree = harness({ ...defaults, rows: [row('A', 0, 0), row('B', 0, 0)], total: 0 }).render();
  assert.equal(links(tree).length, 2);
  assert.deepEqual(labels(tree), ['0%', '0%']);
  for (const node of nodes(tree)) {
    if (hasClass(node, 'work-summary-distribution-fill'))
      assert.equal(node.props.style['--summary-fill-width'], '0%');
    if (node.type === 'progress') assert.equal(node.props.max, 1);
  }
});
