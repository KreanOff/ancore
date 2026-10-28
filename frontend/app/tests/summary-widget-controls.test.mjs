import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

// Run the real controls and their callbacks without rendering the shared dropdown layer.
const bundle = await build({
  entryPoints: [new URL('../src/spaces/SummaryWidgetControls.tsx', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  external: ['react', 'react/jsx-runtime'],
  write: false,
});
const require = createRequire(import.meta.url);
const module = { exports: {} };
vm.runInNewContext(bundle.outputFiles[0].text, { module, exports: module.exports, require });

function harness(values = {}) {
  const events = [];
  let props = {
    widget: Object.freeze({ id: 'completed', x: 3, y: 2, w: 6, h: 4 }),
    layout: [
      Object.freeze({ id: 'completed', x: 3, y: 2, w: 6, h: 4 }),
      Object.freeze({ id: 'statuses', x: 0, y: 7, w: 6, h: 5 }),
    ],
    label: 'Zakończone',
    minWidth: 3,
    minHeight: 2,
    disabled: false,
    onMove: (direction) => events.push(['move', direction]),
    onResize: (size) => events.push(['resize', { ...size }]),
    onRemove: () => events.push(['remove']),
    ...values,
  };
  return {
    events,
    render(next = {}) {
      props = { ...props, ...next };
      const dropdown = module.exports.SummaryWidgetControls(props);
      return { dropdown, menu: dropdown.props.children(() => events.push(['close'])) };
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
function byLabel(tree, label) {
  const match = nodes(tree).find((node) => node.props?.['aria-label'] === label);
  assert.ok(match, `Missing control: ${label}`);
  return match;
}
function button(tree, label) {
  const match = nodes(tree).find(
    (node) =>
      node.type === 'button' && (node.props['aria-label'] === label || text(node) === label),
  );
  assert.ok(match, `Missing button: ${label}`);
  return match;
}
function byClass(tree, name) {
  const match = nodes(tree).find((node) => node.props?.className?.split(' ').includes(name));
  assert.ok(match, `Missing class: ${name}`);
  return match;
}
function outputs(tree) {
  return nodes(tree)
    .filter((node) => node.type === 'output')
    .map(text);
}

test('widget options group position and size as a dialog with live width, height and selected minimap', () => {
  const { dropdown, menu } = harness().render();
  assert.equal(dropdown.props.role, 'dialog');
  assert.equal(dropdown.props.label, 'Opcje gadżetu: Zakończone');
  assert.equal(dropdown.props.searchable, false);
  assert.equal(dropdown.props.positioning, 'fixed');
  assert.equal(dropdown.props.disabled, false);
  assert.match(text(menu), /Zakończone/);
  assert.equal(byLabel(menu, 'Pozycja gadżetu').props.role, 'group');
  assert.equal(byLabel(menu, 'Rozmiar gadżetu').type, 'section');
  assert.deepEqual(outputs(menu), ['50% pulpitu', '228 px']);
  const preview = byClass(menu, 'work-summary-layout-preview');
  assert.equal(preview.props['aria-hidden'], 'true');
  const tiles = nodes(preview).filter((node) => node.type === 'span');
  assert.equal(tiles.length, 2);
  assert.equal(tiles.filter((node) => node.props.className === 'is-selected').length, 1);
  assert.equal(tiles[0].props.className, 'is-selected');
  assert.equal(tiles[0].props.style.left, '25%');
  assert.equal(tiles[0].props.style.width, '50%');
  assert.ok(Math.abs(parseFloat(tiles[0].props.style.top) - 100 / 6) < 0.00001);
  assert.ok(Math.abs(parseFloat(tiles[0].props.style.height) - 100 / 3) < 0.00001);
});

test('direction buttons pass one grid direction and leave the options dialog open', () => {
  const app = harness();
  const menu = app.render().menu;
  for (const [label, direction] of [
    ['Przesuń w górę', 'up'],
    ['Przesuń w lewo', 'left'],
    ['Przesuń w dół', 'down'],
    ['Przesuń w prawo', 'right'],
  ]) {
    const control = button(menu, label);
    assert.equal(control.props.disabled, false);
    control.props.onClick();
    assert.deepEqual(app.events.at(-1), ['move', direction]);
  }
  assert.equal(app.events.length, 4);
  assert.equal(
    app.events.some(([event]) => event === 'close'),
    false,
  );
});

test('ranges expose native bounds and resize only the selected dimension without closing', () => {
  const app = harness();
  let menu = app.render().menu;
  const width = byLabel(menu, 'Szerokość gadżetu');
  assert.equal(width.props.type, 'range');
  assert.deepEqual(
    [width.props.min, width.props.max, width.props.step, width.props.value],
    [3, 12, 1, 6],
  );
  const height = byLabel(menu, 'Wysokość gadżetu');
  assert.equal(height.props.type, 'range');
  assert.deepEqual(
    [height.props.min, height.props.max, height.props.step, height.props.value],
    [2, 16, 1, 4],
  );
  width.props.onChange({ target: { value: '7' } });
  height.props.onChange({ target: { value: '9' } });
  assert.deepEqual(app.events, [
    ['resize', { w: 7 }],
    ['resize', { h: 9 }],
  ]);
  const widget = Object.freeze({ id: 'completed', x: 0, y: 2, w: 12, h: 16 });
  menu = app.render({ widget, layout: [widget] }).menu;
  assert.deepEqual(outputs(menu), ['100% pulpitu', '948 px']);
  assert.equal(byLabel(menu, 'Szerokość gadżetu').props.value, 12);
  assert.equal(byLabel(menu, 'Wysokość gadżetu').props.value, 16);
  assert.equal(button(menu, 'Szerokość: Cały wiersz pulpitu').props['aria-pressed'], true);
});

test('width presets offer valid metric and panel sizes and update the selected preset on refresh', () => {
  const app = harness();
  let menu = app.render().menu;
  assert.equal(button(menu, 'Szerokość: 1/2 pulpitu').props['aria-pressed'], true);
  button(menu, 'Szerokość: 1/4 pulpitu').props.onClick();
  button(menu, 'Szerokość: 1/2 pulpitu').props.onClick();
  button(menu, 'Szerokość: Cały wiersz pulpitu').props.onClick();
  assert.deepEqual(app.events, [
    ['resize', { w: 3 }],
    ['resize', { w: 6 }],
    ['resize', { w: 12 }],
  ]);
  const widget = Object.freeze({ id: 'statuses', x: 0, y: 3, w: 4, h: 5 });
  menu = app.render({
    widget,
    layout: [widget],
    label: 'Przegląd statusów',
    minWidth: 4,
    minHeight: 5,
  }).menu;
  assert.equal(byLabel(menu, 'Szerokość gadżetu').props.min, 4);
  assert.equal(byLabel(menu, 'Wysokość gadżetu').props.min, 5);
  assert.equal(button(menu, 'Szerokość: 1/3 pulpitu').props['aria-pressed'], true);
  assert.equal(button(menu, 'Szerokość: 1/2 pulpitu').props['aria-pressed'], false);
  button(menu, 'Szerokość: 1/3 pulpitu').props.onClick();
  assert.deepEqual(app.events.at(-1), ['resize', { w: 4 }]);
  assert.equal(
    app.events.some(([event]) => event === 'close'),
    false,
  );
});

test('edge widgets disable impossible directions and cap height at the remaining canvas rows', () => {
  const app = harness({ widget: { id: 'completed', x: 0, y: 0, w: 12, h: 16 } });
  let menu = app.render().menu;
  assert.equal(button(menu, 'Przesuń w górę').props.disabled, true);
  assert.equal(button(menu, 'Przesuń w lewo').props.disabled, true);
  assert.equal(button(menu, 'Przesuń w prawo').props.disabled, true);
  assert.equal(button(menu, 'Przesuń w dół').props.disabled, false);
  menu = app.render({
    widget: { id: 'statuses', x: 8, y: 190, w: 4, h: 5 },
    minWidth: 4,
    minHeight: 5,
  }).menu;
  assert.equal(byLabel(menu, 'Wysokość gadżetu').props.max, 10);
  assert.equal(button(menu, 'Przesuń w prawo').props.disabled, true);
  assert.equal(button(menu, 'Przesuń w dół').props.disabled, false);
  menu = app.render({ widget: { id: 'statuses', x: 8, y: 195, w: 4, h: 5 } }).menu;
  assert.equal(byLabel(menu, 'Wysokość gadżetu').props.max, 5);
  assert.equal(button(menu, 'Przesuń w dół').props.disabled, true);
  assert.equal(button(menu, 'Przesuń w górę').props.disabled, false);
});

test('stacked controls offer only vertical moves bounded by visible y/x order', () => {
  const first = Object.freeze({ id: 'created', x: 0, y: 12, w: 3, h: 2 });
  const middle = Object.freeze({ id: 'completed', x: 6, y: 12, w: 3, h: 2 });
  const last = Object.freeze({ id: 'statuses', x: 0, y: 100, w: 6, h: 5 });
  const layout = Object.freeze([last, middle, first]);
  const app = harness({ stacked: true, widget: first, layout });
  let menu = app.render().menu;
  assert.deepEqual(
    nodes(byLabel(menu, 'Pozycja gadżetu'))
      .filter((node) => node.type === 'button')
      .map((node) => node.props['aria-label']),
    ['Przesuń w górę', 'Przesuń w dół'],
  );
  // The first visible card has no predecessor even though its grid row is 12.
  assert.equal(button(menu, 'Przesuń w górę').props.disabled, true);
  assert.equal(button(menu, 'Przesuń w dół').props.disabled, false);
  button(menu, 'Przesuń w dół').props.onClick();
  menu = app.render({ widget: middle }).menu;
  assert.equal(button(menu, 'Przesuń w górę').props.disabled, false);
  assert.equal(button(menu, 'Przesuń w dół').props.disabled, false);
  button(menu, 'Przesuń w górę').props.onClick();
  menu = app.render({ widget: last }).menu;
  // The last visible card cannot move down even with unused canvas rows below.
  assert.equal(button(menu, 'Przesuń w górę').props.disabled, false);
  assert.equal(button(menu, 'Przesuń w dół').props.disabled, true);
  menu = app.render({ layout: [last] }).menu;
  assert.equal(button(menu, 'Przesuń w górę').props.disabled, true);
  assert.equal(button(menu, 'Przesuń w dół').props.disabled, true);
  assert.deepEqual(app.events, [
    ['move', 'down'],
    ['move', 'up'],
  ]);
  assert.deepEqual(
    layout.map((widget) => widget.id),
    ['statuses', 'completed', 'created'],
  );
});

test('pending changes disable mutation controls while Close can dismiss the menu', () => {
  const app = harness({ disabled: true });
  const { dropdown, menu } = app.render();
  assert.equal(dropdown.props.disabled, true);
  for (const control of nodes(menu).filter((node) => ['button', 'input'].includes(node.type))) {
    if (control.type === 'button' && text(control) === 'Zamknij') continue;
    assert.equal(control.props.disabled, true, text(control) || control.props['aria-label']);
  }
  button(menu, 'Zamknij').props.onClick();
  assert.deepEqual(app.events, [['close']]);
});

test('removal is isolated in the footer and closes before removing the widget', () => {
  const app = harness();
  const menu = app.render().menu;
  const footer = byClass(menu, 'work-summary-controls-footer');
  assert.deepEqual(
    nodes(footer)
      .filter((node) => node.type === 'button')
      .map(text),
    ['Usuń gadżet', 'Zamknij'],
  );
  button(footer, 'Usuń gadżet').props.onClick();
  assert.deepEqual(app.events, [['close'], ['remove']]);
});
