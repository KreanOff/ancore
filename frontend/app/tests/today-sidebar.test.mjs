import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

const bundle = await build({
  entryPoints: [new URL('../src/shell/TodaySidebar.tsx', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  external: ['react', 'react/jsx-runtime', 'react-dom'],
  plugins: [
    {
      name: 'sidebar-http-boundary',
      setup(builder) {
        builder.onResolve({ filter: /^\.\.\/shared\/page$/ }, () => ({
          path: 'test:page',
          external: true,
        }));
      },
    },
  ],
  write: false,
});
const require = createRequire(import.meta.url);
const sidebarUrl = '/workplaces/w_test/calendar/sidebar/';
const moreUrl = sidebarUrl + '?sidebar_task_limit=24';
const nextTurn = () => new Promise(setImmediate);

class PageError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

function payload(count = 20, extra = {}) {
  return {
    today: '2026-11-12',
    time_zone: 'Europe/Warsaw',
    tasks_enabled: true,
    entries: Array.from({ length: count }, (_, index) => ({
      id: `${index % 2 ? 'events' : 'tasks'}:${Math.floor(index / 2) + 1}`,
      source: index % 2 ? 'events' : 'tasks',
      title: `${index % 2 ? 'Wydarzenie' : 'Zadanie'} na dziś ${index + 1}`,
      url:
        index % 2
          ? `/workplaces/w_test/calendar/?event=${Math.floor(index / 2) + 1}`
          : `/workplaces/w_test/spaces/1/tasks/${Math.floor(index / 2) + 1}/`,
      subtitle: index % 2 ? 'Kalendarz' : `PRZ-${index + 1} · Przestrzeń zespołu`,
      starts_at: '2026-11-12T09:00:00+01:00',
      time_label: '09:00',
      color: index % 2 ? '#8b25c7' : '',
      ...(index % 2
        ? {}
        : {
            key: `PRZ-${index + 1}`,
            space_id: 1,
            space_name: 'Przestrzeń zespołu',
            priority: 'medium',
            priority_label: 'Średni',
            status: 'in_progress',
            status_label: 'Wstrzymane',
            status_color: '#ff00d4',
          }),
    })),
    pagination: { count: 24, has_next: count < 24, next_url: count < 24 ? moreUrl : '' },
    ...extra,
  };
}

function withGroups(data) {
  const groups = new Map();
  for (const entry of data.entries) {
    const id = entry.source === 'events' ? 'events' : `space:${entry.space_id}`;
    if (!groups.has(id))
      groups.set(id, {
        id,
        label: entry.source === 'events' ? 'Kalendarz' : entry.space_name,
        entries: [],
      });
    groups.get(id).entries.push(entry);
  }
  return {
    ...data,
    groups: [...groups.values()]
      .filter((group) => group.id !== 'events')
      .concat(groups.has('events') ? [groups.get('events')] : []),
  };
}

function nodes(element) {
  if (!element || typeof element !== 'object') return [];
  if (Array.isArray(element)) return element.flatMap(nodes);
  if (!element.props) return [];
  const children = Object.values(element.props).flatMap(nodes);
  if (element.type?.name === 'LoadMore') children.push(...nodes(element.type(element.props)));
  return [element, ...children];
}

function text(element) {
  if (element == null || typeof element === 'boolean') return '';
  if (Array.isArray(element)) return element.map(text).join('');
  return typeof element === 'object' ? text(element.props?.children) : String(element);
}

function harness() {
  let cursor = 0,
    dirty = false,
    mounted = true,
    tree,
    writesAfterUnmount = 0;
  let props = {
    api: '/api/v1/page/',
    url: sidebarUrl,
    calendarUrl: '/workplaces/w_test/calendar/',
    token: 'csrf',
    expanded: true,
  };
  const values = [],
    effects = [],
    scheduled = [],
    requests = [],
    timers = new Map();
  const window = new EventTarget();
  let nextTimer = 0;
  window.setInterval = (callback) => {
    const id = ++nextTimer;
    timers.set(id, callback);
    return id;
  };
  const document = {
    visibilityState: 'visible',
    querySelector: () => null,
  };
  const react = {
    ...require('react'),
    useState(initial) {
      const index = cursor++;
      if (!(index in values)) values[index] = typeof initial === 'function' ? initial() : initial;
      return [
        values[index],
        (next) => {
          if (!mounted) {
            writesAfterUnmount++;
            return;
          }
          const value = typeof next === 'function' ? next(values[index]) : next;
          if (!Object.is(value, values[index])) {
            values[index] = value;
            dirty = true;
          }
        },
      ];
    },
    useRef(initial) {
      const index = cursor++;
      if (!(index in values)) values[index] = { current: initial };
      return values[index];
    },
    useEffect(callback, deps) {
      const index = cursor++;
      const previous = effects[index];
      if (!previous || deps.some((value, i) => !Object.is(value, previous.deps[i]))) {
        const effect = { deps, callback, previous };
        effects[index] = effect;
        scheduled.push(effect);
      }
    },
  };
  const module = { exports: {} };
  vm.runInNewContext(bundle.outputFiles[0].text, {
    module,
    exports: module.exports,
    require(name) {
      if (name === 'react') return react;
      if (name === 'test:page')
        return {
          PageError,
          pageRequest: (...args) =>
            new Promise((resolve, reject) => requests.push({ args, resolve, reject })),
        };
      return require(name);
    },
    window,
    document,
    Date,
    Error,
    URLSearchParams,
    AbortController,
    clearInterval: (id) => timers.delete(id),
  });

  function render(next) {
    if (next) props = { ...props, ...next };
    do {
      dirty = false;
      cursor = 0;
      tree = module.exports.default(props);
      const changed = scheduled.splice(0);
      changed.forEach((effect) => effect.previous?.cleanup?.());
      changed.forEach((effect) => (effect.cleanup = effect.callback()));
    } while (dirty);
    return tree;
  }

  return {
    render,
    requests,
    timers,
    document,
    get writesAfterUnmount() {
      return writesAfterUnmount;
    },
    async succeed(index, data = payload()) {
      requests[index].resolve(withGroups(data));
      await nextTurn();
      if (mounted) render();
    },
    async fail(index, error = new Error('Brak połączenia')) {
      requests[index].reject(error);
      await nextTurn();
      if (mounted) render();
    },
    focus: () => window.dispatchEvent(new Event('focus')),
    changed: () => window.dispatchEvent(new Event('ancore:calendar-changed')),
    tick: () => [...timers.values()].forEach((callback) => callback()),
    byClass: (name) =>
      nodes(tree).filter((node) => (node.props.className || '').split(' ').includes(name)),
    groups: () => nodes(tree).filter((node) => node.type?.name === 'StatusGroup'),
    button(label) {
      const button = nodes(tree).find(
        (node) =>
          node.type === 'button' &&
          (typeof label === 'string'
            ? text(node) === label
            : label.test(node.props['aria-label'] || text(node))),
      );
      assert.ok(button, `button ${label} is present`);
      return button;
    },
    allText: () => text(tree),
    unmount() {
      effects.forEach((effect) => effect?.cleanup?.());
      mounted = false;
    },
  };
}

test('today sidebar shows space groups followed by calendar, with task appearance and day links', async () => {
  const app = harness();
  app.render();
  assert.equal(app.requests.length, 1, 'mount and expanded refresh share one pending request');
  assert.match(app.allText(), /Wczytywanie planu/);
  await app.succeed(0);
  const rows = app.byClass('today-sidebar__task');
  assert.equal(rows.length, 20);
  assert.equal(rows[0].props.href, payload().entries[0].url);
  assert.match(text(rows[0]), /Zadanie na dziś 1/);
  assert.equal(text(app.byClass('today-sidebar__task-key')[0]), 'PRZ-1');
  assert.match(rows[0].props.title, /Przestrzeń zespołu/);
  assert.equal(app.byClass('status-indicator')[0].props['aria-label'], 'Wstrzymane');
  assert.equal(app.byClass('status-indicator')[0].props.style['--tasks-status-color'], '#ff00d4');
  assert.match(text(rows[0]), /09:00/);
  assert.equal(rows[0].key, 'tasks:1');
  assert.equal(rows[10].key, 'events:1');
  assert.equal(rows[10].props.href, '/workplaces/w_test/calendar/?event=1');
  assert.match(text(rows[10]), /Wydarzenie na dziś 209:00/);
  assert.equal(app.byClass('today-sidebar__event-color').length, 10);
  assert.equal(app.byClass('today-sidebar__event-color')[0].props.style.backgroundColor, '#8b25c7');
  assert.deepEqual(
    app.groups().map((group) => group.props.label),
    ['Przestrzeń zespołu', 'Kalendarz'],
  );
  assert.deepEqual(
    app.groups().map((group) => group.props.count),
    [10, 10],
  );
  assert.ok(app.groups().every((group) => group.props.icon === null));
  assert.equal(app.byClass('today-sidebar__tasks')[0].props['aria-busy'], false);
  const today = app
    .byClass('today-sidebar__day')
    .find((node) => node.props['aria-current'] === 'date');
  assert.equal(today.props.href, '/workplaces/w_test/calendar/?date=2026-11-12');
  app.unmount();
});

test('load more preserves each group prefix and keys, blocks duplicate requests and stops at all results', async () => {
  const app = harness();
  app.render();
  await app.succeed(0);
  const firstGroups = app.groups().map((group) => ({
    key: group.key,
    links: nodes(group)
      .filter((node) => node.type === 'a')
      .map((node) => node.props.href),
  }));
  const more = app.button(/^Pokaż więcej:/);
  more.props.onClick();
  more.props.onClick();
  app.render();
  assert.equal(app.requests.length, 2);
  assert.equal(app.requests[1].args[1], moreUrl);
  assert.equal(app.byClass('today-sidebar__task').length, 20);
  assert.equal(app.button(/^Wczytywanie…:/).props['aria-disabled'], true);
  await app.succeed(1, payload(24));
  const links = app.byClass('today-sidebar__task').map((node) => node.props.href);
  app.groups().forEach((group, index) => {
    assert.equal(group.key, firstGroups[index].key);
    const groupLinks = nodes(group)
      .filter((node) => node.type === 'a')
      .map((node) => node.props.href);
    assert.deepEqual(
      groupLinks.slice(0, firstGroups[index].links.length),
      firstGroups[index].links,
    );
  });
  assert.equal(new Set(links).size, 24);
  const complete = app.button(/^Wszystkie wyniki:/);
  assert.equal(complete.props['aria-disabled'], true);
  complete.props.onClick();
  assert.equal(app.requests.length, 2);
  app.unmount();
});

test('failed load more retains rows and retries the same cumulative window', async () => {
  const app = harness();
  app.render();
  await app.succeed(0);
  app.button(/^Pokaż więcej:/).props.onClick();
  await app.fail(1);
  assert.equal(app.byClass('today-sidebar__task').length, 20);
  assert.match(text(app.byClass('today-sidebar__error')[0]), /Brak połączenia/);
  const retry = app.button('Spróbuj ponownie');
  retry.props.onClick();
  retry.props.onClick();
  assert.equal(app.requests.length, 3);
  assert.equal(app.requests[2].args[1], moreUrl);
  await app.succeed(2, payload(24));
  assert.equal(app.byClass('today-sidebar__task').length, 24);
  assert.equal(app.byClass('today-sidebar__error').length, 0);
  app.unmount();
});

test('focus and timed refresh retain the loaded window and pause when hidden or collapsed', async () => {
  const app = harness();
  app.render();
  await app.succeed(0);
  app.button(/^Pokaż więcej:/).props.onClick();
  await app.succeed(1, payload(24));
  app.focus();
  app.tick();
  assert.equal(app.requests.length, 3);
  assert.equal(app.requests[2].args[1], moreUrl);
  await app.succeed(2, payload(24));
  app.document.visibilityState = 'hidden';
  app.focus();
  app.tick();
  assert.equal(app.requests.length, 3);
  app.document.visibilityState = 'visible';
  app.render({ expanded: false });
  app.focus();
  assert.equal(app.timers.size, 0);
  assert.equal(app.requests.length, 3);
  app.render({ expanded: true });
  assert.equal(app.requests[3].args[1], moreUrl);
  await app.succeed(3, payload(24));
  assert.equal(app.byClass('today-sidebar__task').length, 24);
  assert.equal(app.timers.size, 1);
  app.unmount();
});

test('changing the Workspace URL aborts old requests and ignores their late response', async () => {
  const app = harness();
  app.render();
  await app.succeed(0);
  app.button(/^Pokaż więcej:/).props.onClick();
  const nextUrl = '/workplaces/w_second/calendar/sidebar/';
  app.render({ url: nextUrl, calendarUrl: '/workplaces/w_second/calendar/' });
  assert.equal(app.requests[1].args[3].aborted, true);
  assert.equal(app.requests.length, 3);
  assert.equal(app.requests[2].args[1], nextUrl);
  assert.equal(app.byClass('today-sidebar__task').length, 0);
  await app.succeed(1, payload(24));
  assert.equal(app.byClass('today-sidebar__task').length, 0);
  assert.equal(app.byClass('today-sidebar__tasks')[0].props['aria-busy'], true);
  await app.succeed(
    2,
    payload(1, { entries: [{ ...payload(1).entries[0], title: 'Nowy Workspace' }] }),
  );
  assert.match(app.allText(), /Nowy Workspace/);
  assert.doesNotMatch(app.allText(), /Zadanie na dziś 1/);
  app.unmount();
});

test('unmount aborts a request and prevents late state writes or refreshes', async () => {
  const app = harness();
  app.render();
  app.unmount();
  assert.equal(app.requests[0].args[3].aborted, true);
  assert.equal(app.timers.size, 0);
  await app.succeed(0, payload(24));
  app.focus();
  assert.equal(app.requests.length, 1);
  assert.equal(app.writesAfterUnmount, 0);
});

test('initial failure keeps calendar usable and retries the original sidebar URL', async () => {
  const app = harness();
  app.render();
  await app.fail(0);
  assert.equal(app.byClass('today-sidebar__task').length, 0);
  assert.equal(app.byClass('today-sidebar__calendar').length, 1);
  assert.doesNotMatch(app.allText(), /Brak zadań i wydarzeń na dziś/);
  app.button('Spróbuj ponownie').props.onClick();
  assert.equal(app.requests[1].args[1], sidebarUrl);
  await app.succeed(1);
  assert.equal(app.byClass('today-sidebar__task').length, 20);
  assert.equal(app.byClass('today-sidebar__error').length, 0);
  app.unmount();
});

test('permission failure removes stale task rows instead of retaining protected data', async () => {
  const app = harness();
  app.render();
  await app.succeed(0);
  app.focus();
  await app.fail(1, new PageError('Brak dostępu.', 403));
  assert.equal(app.byClass('today-sidebar__task').length, 0);
  assert.equal(app.groups().length, 0);
  assert.match(app.allText(), /Brak dostępu/);
  assert.equal(app.byClass('today-sidebar__calendar').length, 1);
  app.unmount();
});

test('disabled spaces still shows calendar events and empty results show the shared empty state', async () => {
  const app = harness();
  app.render();
  await app.succeed(
    0,
    payload(1, {
      tasks_enabled: false,
      entries: [{ ...payload(2).entries[1], time_label: 'Cały dzień' }],
      pagination: { count: 1, has_next: false, next_url: '' },
    }),
  );
  assert.equal(app.byClass('today-sidebar__tasks').length, 1);
  assert.match(app.allText(), /Wydarzenie na dziś 2Cały dzień/);
  assert.deepEqual(
    app.groups().map((group) => group.props.label),
    ['Kalendarz'],
  );
  assert.equal(app.byClass('today-sidebar__calendar').length, 1);
  app.focus();
  await app.succeed(1, payload(0, { pagination: { count: 0, has_next: false, next_url: '' } }));
  assert.equal(app.byClass('today-sidebar__tasks').length, 1);
  assert.match(app.allText(), /Brak zadań i wydarzeń na dziś/);
  assert.equal(app.byClass('app-load-more').length, 0);
  app.unmount();
});

test('calendar changes replace an in-flight refresh and retain the expanded mixed window', async () => {
  const app = harness();
  app.render();
  await app.succeed(0);
  app.button(/^Pokaż więcej:/).props.onClick();
  await app.succeed(1, payload(24));
  app.focus();
  app.changed();
  assert.equal(app.requests[2].args[3].aborted, true);
  assert.equal(app.requests[3].args[1], moreUrl);
  const current = payload(24);
  current.entries[1] = { ...current.entries[1], title: 'Zapisane wydarzenie', color: '#123abc' };
  await app.succeed(3, current);
  await app.succeed(2, payload(24));
  assert.match(app.allText(), /Zapisane wydarzenie/);
  assert.equal(app.byClass('today-sidebar__event-color')[0].props.style.backgroundColor, '#123abc');
  assert.equal(app.byClass('today-sidebar__task').length, 24);
  app.unmount();
  app.changed();
  assert.equal(app.requests.length, 4);
});
