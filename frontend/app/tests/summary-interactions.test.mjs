import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

// Expose the actual chart functions for callback tests, without changing production exports.
const bundle = await build({
  stdin: {
    contents: `${await readFile(new URL('../src/spaces/Summary.tsx', import.meta.url), 'utf8')}
      export { StatusChart, PriorityChart, useSummaryMotion };`,
    sourcefile: 'Summary.tsx',
    resolveDir: new URL('../src/spaces', import.meta.url).pathname,
    loader: 'tsx',
  },
  bundle: true,
  platform: 'node',
  format: 'cjs',
  jsx: 'automatic',
  external: ['react', 'react/jsx-runtime'],
  write: false,
});
const require = createRequire(import.meta.url);

function load(react, context = {}) {
  const module = { exports: {} };
  vm.runInNewContext(bundle.outputFiles[0].text, {
    module,
    exports: module.exports,
    require: (name) => (name === 'react' ? { ...require('react'), ...react } : require(name)),
    ...context,
  });
  return module.exports;
}

function chart(name, data, context = {}) {
  const states = [];
  let cursor = 0;
  const components = load(
    {
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
    },
    context,
  );
  return {
    render(next = {}) {
      cursor = 0;
      data = { ...data, ...next };
      return components[name]({ data });
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
function byClass(tree, name) {
  return nodes(tree).find((node) => hasClass(node, name));
}
function arcs(tree) {
  return nodes(tree).filter((node) => hasClass(node, 'work-summary-donut-arc'));
}
function statusLinks(tree) {
  return nodes(byClass(tree, 'work-summary-legend')).filter((node) => node.type === 'a');
}
function priorityLinks(tree) {
  return nodes(tree).filter((node) => hasClass(node, 'work-summary-priority'));
}
function centerValues(tree) {
  return Array.from(byClass(tree, 'work-summary-donut-total').props.children, text);
}
function status(key, count, category = 'in_progress') {
  return {
    key,
    label: key,
    count,
    category,
    url: `/workplaces/w_test/space/produkt/?view=list&status=${key}`,
    arc: '40',
    gap: '60',
    offset: '0',
  };
}
function statusData(statuses = [status('Weryfikacja', 3), status('Akceptacja', 7)]) {
  return {
    statuses,
    total: 10,
    status_total: 10,
    list_url: '/workplaces/w_test/space/produkt/?view=list',
  };
}
function priority(key, count, height = '0') {
  return {
    key,
    label: key,
    count,
    height,
    url: `/workplaces/w_test/space/produkt/?view=list&priority=${key}`,
  };
}
function priorityData(priorities = [priority('urgent', 3, '60'), priority('high', 2, '40')]) {
  return { priorities, open_total: 5, priority_axis: { max: 5, middle: 2.5 } };
}

test('status arc hover synchronizes the center and legend by key, including shared categories', () => {
  const app = chart('StatusChart', statusData());
  let tree = app.render();
  assert.deepEqual(centerValues(tree), ['10', 'zadań', 'Łącznie']);
  arcs(tree)[0].props.onPointerEnter();
  tree = app.render();
  assert.deepEqual(centerValues(tree), ['3', 'Weryfikacja', '30%']);
  assert.deepEqual(
    arcs(tree).map((arc) => hasClass(arc, 'is-active')),
    [true, false],
  );
  assert.deepEqual(
    statusLinks(tree).map((link) => hasClass(link, 'is-active')),
    [true, false],
  );
  arcs(tree)[0].props.onPointerLeave();
  arcs(tree)[1].props.onPointerEnter();
  tree = app.render();
  assert.deepEqual(centerValues(tree), ['7', 'Akceptacja', '70%']);
  assert.deepEqual(
    statusLinks(tree).map((link) => hasClass(link, 'is-active')),
    [false, true],
  );
  byClass(tree, 'work-summary-status').props.onPointerLeave();
  tree = app.render();
  assert.deepEqual(centerValues(tree), ['10', 'zadań', 'Łącznie']);
  assert.equal(hasClass(byClass(tree, 'work-summary-status'), 'has-active-status'), false);
});

test('status keyboard focus survives temporary hover and Escape clears both previews', () => {
  const app = chart('StatusChart', statusData());
  let tree = app.render();
  statusLinks(tree)[0].props.onFocus();
  tree = app.render();
  assert.deepEqual(centerValues(tree), ['3', 'Weryfikacja', '30%']);
  statusLinks(tree)[1].props.onPointerEnter();
  tree = app.render();
  assert.deepEqual(centerValues(tree), ['7', 'Akceptacja', '70%']);
  statusLinks(tree)[1].props.onPointerLeave();
  tree = app.render();
  assert.deepEqual(centerValues(tree), ['3', 'Weryfikacja', '30%']);
  byClass(tree, 'work-summary-status').props.onKeyDown({ key: 'ArrowRight' });
  assert.deepEqual(centerValues(app.render()), ['3', 'Weryfikacja', '30%']);
  statusLinks(tree)[1].props.onPointerEnter();
  byClass(tree, 'work-summary-status').props.onKeyDown({ key: 'Escape' });
  tree = app.render();
  assert.deepEqual(centerValues(tree), ['10', 'zadań', 'Łącznie']);
  statusLinks(tree)[1].props.onFocus();
  statusLinks(app.render())[1].props.onBlur();
  assert.deepEqual(centerValues(app.render()), ['10', 'zadań', 'Łącznie']);
});

test('status drill-down uses application navigation and respects a canceled navigation', () => {
  const data = statusData(),
    calls = [],
    location = { href: 'original' },
    app = chart('StatusChart', data, {
      location,
      window: {
        AncoreApp: {
          canNavigatePartially: () => true,
          navigate: (url) => {
            calls.push(url);
            return false;
          },
        },
      },
    });
  const tree = app.render();
  arcs(tree)[1].props.onClick();
  assert.deepEqual(calls, [data.statuses[1].url]);
  assert.equal(location.href, 'original');
  assert.deepEqual(
    statusLinks(tree).map((link) => link.props.href),
    data.statuses.map((s) => s.url),
  );
});

test('status drill-down falls back to full navigation when partial navigation is unavailable', () => {
  for (const AncoreApp of [undefined, { canNavigatePartially: () => false }]) {
    const location = { href: 'original' },
      data = statusData(),
      app = chart('StatusChart', data, { window: { AncoreApp }, location });
    arcs(app.render())[0].props.onClick();
    assert.equal(location.href, data.statuses[0].url);
  }
});

test('status zero and rare categories keep exact accessible counts without invalid chart values', () => {
  const app = chart('StatusChart', statusData([status('Puste', 0), status('Rzadkie', 1)]));
  let tree = app.render({ total: 1000, status_total: 1000 });
  assert.equal(arcs(tree).length, 1);
  assert.match(statusLinks(tree)[0].props['aria-label'], /Puste: 0 z 1000 zadań, 0%/);
  assert.match(statusLinks(tree)[1].props['aria-label'], /Rzadkie: 1 z 1000 zadań, <1%/);
  statusLinks(tree)[0].props.onFocus();
  assert.deepEqual(centerValues(app.render()), ['0', 'Puste', '0%']);
  tree = app.render({ statuses: [status('Puste', 0)], total: 0, status_total: 0 });
  assert.equal(arcs(tree).length, 0);
  assert.deepEqual(centerValues(tree), ['0', 'Puste', '0%']);
  assert.match(text(tree), /Utwórz pierwsze zadanie/);
  tree = app.render({ statuses: [], total: 4, status_total: 0 });
  assert.deepEqual(centerValues(tree), ['0', 'zadań', 'Łącznie']);
  assert.match(text(tree), /Brak otwartych ani niedawno zakończonych zadań/);
});

test('status preview reads refreshed counts and clears a removed status', () => {
  const app = chart('StatusChart', statusData());
  statusLinks(app.render())[0].props.onFocus();
  let tree = app.render({ statuses: [status('Weryfikacja', 8)], status_total: 8 });
  assert.deepEqual(centerValues(tree), ['8', 'Weryfikacja', '100%']);
  tree = app.render({ statuses: [status('Nowy status', 4)], status_total: 4 });
  assert.deepEqual(centerValues(tree), ['4', 'zadań', 'Łącznie']);
});

test('priority hover and keyboard focus update the footer and Escape restores the total', () => {
  const data = priorityData(),
    app = chart('PriorityChart', data);
  let tree = app.render();
  assert.equal(text(byClass(tree, 'work-summary-insight')), 'Otwarte zadania5');
  priorityLinks(tree)[0].props.onFocus();
  tree = app.render();
  assert.equal(text(byClass(tree, 'work-summary-insight')), 'urgent3 z 5 · 60%');
  priorityLinks(tree)[1].props.onPointerEnter();
  tree = app.render();
  assert.equal(text(byClass(tree, 'work-summary-insight')), 'high2 z 5 · 40%');
  assert.deepEqual(
    priorityLinks(tree).map((link) => hasClass(link, 'is-active')),
    [false, true],
  );
  priorityLinks(tree)[1].props.onPointerLeave();
  tree = app.render();
  assert.equal(text(byClass(tree, 'work-summary-insight')), 'urgent3 z 5 · 60%');
  priorityLinks(tree)[0].props.onKeyDown({ key: 'Escape' });
  tree = app.render();
  assert.equal(text(byClass(tree, 'work-summary-insight')), 'Otwarte zadania5');
  assert.equal(
    hasClass(byClass(tree, 'work-summary-priority-chart'), 'has-active-priority'),
    false,
  );
  priorityLinks(tree)[1].props.onFocus();
  priorityLinks(app.render())[1].props.onBlur();
  tree = app.render();
  assert.equal(text(byClass(tree, 'work-summary-insight')), 'Otwarte zadania5');
  assert.deepEqual(
    priorityLinks(tree).map((link) => link.props.href),
    data.priorities.map((p) => p.url),
  );
});

test('priority preview uses refreshed counts and keeps empty categories reachable', () => {
  const app = chart('PriorityChart', priorityData([priority('none', 0)]));
  let tree = app.render({ open_total: 0, priority_axis: { max: 1, middle: 0.5 } });
  assert.match(text(tree), /Brak otwartych zadań/);
  assert.match(text(priorityLinks(tree)[0]), /Brak$/);
  assert.match(priorityLinks(tree)[0].props['aria-label'], /0 z 0 otwartych zadań, 0%/);
  priorityLinks(tree)[0].props.onPointerEnter();
  tree = app.render();
  assert.equal(text(byClass(tree, 'work-summary-insight')), 'none0 z 0 · 0%');
  tree = app.render({ priorities: [priority('none', 1, '10')], open_total: 1000 });
  assert.equal(text(byClass(tree, 'work-summary-insight')), 'none1 z 1000 · <1%');
  assert.equal(
    byClass(tree, 'work-summary-priority-bar').props.style['--summary-bar-height'],
    '10%',
  );
  tree = app.render({ priorities: [] });
  assert.equal(text(byClass(tree, 'work-summary-insight')), 'Otwarte zadania1000');
});

function motion({ reduced = false, supported = true, element = true } = {}) {
  const listeners = new Set(),
    observers = [],
    panels = [new Set(), new Set()].map((classes) => ({
      classList: { add: (name) => classes.add(name), contains: (name) => classes.has(name) },
    })),
    root = {
      dataset: {},
      querySelectorAll: (selector) => {
        assert.equal(selector, '[data-summary-reveal]');
        return panels;
      },
    },
    preference = {
      matches: reduced,
      addEventListener: (name, listener) => {
        assert.equal(name, 'change');
        listeners.add(listener);
      },
      removeEventListener: (name, listener) => {
        assert.equal(name, 'change');
        listeners.delete(listener);
      },
    };
  class IntersectionObserver {
    constructor(callback) {
      this.callback = callback;
      this.observed = new Set();
      this.disconnected = false;
      observers.push(this);
    }
    observe(panel) {
      this.observed.add(panel);
    }
    unobserve(panel) {
      this.observed.delete(panel);
    }
    disconnect() {
      this.observed.clear();
      this.disconnected = true;
    }
  }
  let effect;
  const window = {
      matchMedia: (query) => {
        assert.equal(query, '(prefers-reduced-motion: reduce)');
        return preference;
      },
      ...(supported ? { IntersectionObserver } : {}),
    },
    hook = load(
      {
        useRef: () => ({ current: element ? root : null }),
        useEffect: (callback) => (effect = callback),
      },
      { window, IntersectionObserver },
    );
  const ref = hook.useSummaryMotion();
  const dispose = effect();
  return {
    root,
    ref,
    panels,
    observers,
    listeners,
    dispose,
    change(reduced) {
      preference.matches = reduced;
      for (const listener of listeners) listener();
    },
  };
}

test('motion reveals intersecting panels once and disposes observation and preference listeners', () => {
  const app = motion(),
    observer = app.observers[0];
  assert.equal(app.ref.current, app.root);
  assert.equal(app.root.dataset.summaryMotion, 'ready');
  assert.equal(observer.observed.size, 2);
  observer.callback([
    { target: app.panels[0], isIntersecting: false },
    { target: app.panels[1], isIntersecting: true },
  ]);
  assert.equal(app.panels[0].classList.contains('is-visible'), false);
  assert.equal(app.panels[1].classList.contains('is-visible'), true);
  assert.deepEqual([...observer.observed], [app.panels[0]]);
  app.dispose();
  assert.equal(observer.disconnected, true);
  assert.equal(observer.observed.size, 0);
  assert.equal(app.listeners.size, 0);
  assert.equal(app.root.dataset.summaryMotion, undefined);
  app.change(false);
  assert.equal(app.observers.length, 1);
});

test('reduced-motion preference skips reveals and reacts to preference changes without duplicate observers', () => {
  const app = motion({ reduced: true });
  assert.equal(app.root.dataset.summaryMotion, undefined);
  assert.equal(app.observers.length, 0);
  app.change(false);
  assert.equal(app.root.dataset.summaryMotion, 'ready');
  assert.equal(app.observers.length, 1);
  app.change(true);
  assert.equal(app.observers[0].disconnected, true);
  assert.equal(app.root.dataset.summaryMotion, undefined);
  app.change(false);
  assert.equal(app.observers.length, 2);
  assert.equal(app.observers[1].observed.size, 2);
  assert.equal(app.listeners.size, 1);
  app.dispose();
  assert.equal(app.observers[1].disconnected, true);
  assert.equal(app.listeners.size, 0);
});

test('motion without IntersectionObserver leaves content visible and cleans up its listener', () => {
  const app = motion({ supported: false });
  assert.equal(app.root.dataset.summaryMotion, undefined);
  assert.equal(app.observers.length, 0);
  app.change(false);
  assert.equal(app.root.dataset.summaryMotion, undefined);
  app.dispose();
  assert.equal(app.listeners.size, 0);
  const detached = motion({ element: false });
  assert.equal(detached.dispose, undefined);
  assert.equal(detached.listeners.size, 0);
  assert.equal(detached.observers.length, 0);
});
