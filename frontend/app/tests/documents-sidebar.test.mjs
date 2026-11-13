import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

const bundle = await build({
  entryPoints: [new URL('../src/documents/Sidebar.tsx', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  external: ['react', 'react/jsx-runtime', 'react-dom'],
  plugins: [
    {
      name: 'drive-sidebar-http-boundary',
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
const baseUrl = '/workplaces/w_test/drive/';
const moreUrl = baseUrl + '?q=raport&sidebar_library_limit=40';
const nextTurn = () => new Promise(setImmediate);

class PageError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

function data(count = 20, extra = {}) {
  return {
    office: false,
    libraries: true,
    base_url: baseUrl,
    library: null,
    rows: [{ id: 'main-result', name: 'Wynik wyszukiwania w tabeli' }],
    sidebar: Array.from({ length: count }, (_, index) => ({
      id: String(index + 1),
      name: `Dysk ${index + 1}`,
      url: baseUrl + `libraries/${index + 1}/`,
      target: `library:${index + 1}`,
      color: index % 2 ? '#8b25c7' : '#4285d4',
    })),
    sidebar_window: { count: 24, has_next: count < 24, next_url: count < 24 ? moreUrl : '' },
    ...extra,
  };
}

function text(element) {
  if (element == null || typeof element === 'boolean') return '';
  if (Array.isArray(element)) return element.map(text).join('');
  return typeof element === 'object' ? text(element.props?.children) : String(element);
}

function nodes(element) {
  if (!element || typeof element !== 'object') return [];
  if (Array.isArray(element)) return element.flatMap(nodes);
  if (!element.props) return [];
  const children = Object.values(element.props).flatMap(nodes);
  if (['LoadMore', 'DriveIcon'].includes(element.type?.name))
    children.push(...nodes(element.type(element.props)));
  return [element, ...children];
}

function harness(initial = {}) {
  let cursor = 0,
    dirty = false,
    mounted = true,
    tree,
    writesAfterUnmount = 0;
  const values = [],
    effects = [],
    scheduled = [],
    requests = [],
    opened = [],
    portals = [];
  const host = { id: 'app-right-sidebar-content' };
  let props = {
    data: data(),
    api: '/api/v1/page/',
    token: 'csrf',
    readOnly: false,
    busy: false,
    openModal: (url) => opened.push(url),
    drop: null,
    ...initial,
  };
  const react = {
    ...require('react'),
    useState(initialValue) {
      const index = cursor++;
      if (!(index in values))
        values[index] = typeof initialValue === 'function' ? initialValue() : initialValue;
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
    useRef(initialValue) {
      const index = cursor++;
      if (!(index in values)) values[index] = { current: initialValue };
      return values[index];
    },
    useEffect(callback, deps) {
      const index = cursor++,
        previous = effects[index];
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
      if (name === 'react-dom')
        return {
          createPortal(children, target) {
            portals.push(target);
            return children;
          },
        };
      if (name === 'test:page')
        return {
          PageError,
          pageRequest: (...args) =>
            new Promise((resolve, reject) => requests.push({ args, resolve, reject })),
        };
      return require(name);
    },
    document: { getElementById: (id) => (id === host.id ? host : null) },
    Error,
    AbortController,
  });

  function render(next) {
    if (next) props = { ...props, ...next };
    do {
      dirty = false;
      cursor = 0;
      const root = module.exports.default(props);
      assert.equal(root.type.name, 'RightSidebarContent');
      tree = root.type(root.props);
      const changed = scheduled.splice(0);
      changed.forEach((effect) => effect.previous?.cleanup?.());
      changed.forEach((effect) => (effect.cleanup = effect.callback()));
    } while (dirty);
    return tree;
  }
  return {
    render,
    requests,
    opened,
    portals,
    host,
    get writesAfterUnmount() {
      return writesAfterUnmount;
    },
    get input() {
      return props.data;
    },
    byClass: (name) =>
      nodes(tree).filter((node) => (node.props.className || '').split(' ').includes(name)),
    links: () => nodes(tree).filter((node) => node.type === 'a'),
    button(label) {
      const button = nodes(tree).find(
        (node) => node.type === 'button' && label.test(node.props['aria-label'] || text(node)),
      );
      assert.ok(button, `button ${label} is present`);
      return button;
    },
    buttons: () => nodes(tree).filter((node) => node.type === 'button'),
    async succeed(index, result = data(24)) {
      requests[index].resolve({ type: 'document-directory', data: result });
      await nextTurn();
      if (mounted) render();
    },
    async fail(index, error = new Error('Brak połączenia')) {
      requests[index].reject(error);
      await nextTurn();
      if (mounted) render();
    },
    unmount() {
      effects.forEach((effect) => effect?.cleanup?.());
      mounted = false;
    },
  };
}

test('drive sidebar renders in the common portal with only scoped drive links and their colors', () => {
  const app = harness();
  app.render();
  assert.ok(app.portals.length);
  assert.ok(app.portals.every((target) => target === app.host));
  assert.equal(app.byClass('documents-sidebar--global').length, 1);
  assert.equal(app.requests.length, 0, 'the first render uses the existing page payload');
  const drives = app.links();
  assert.ok(
    drives.every((link) => link.props.className.includes('documents-sidebar-library-link')),
  );
  assert.ok(drives.every((link) => link.props['aria-current'] === undefined));
  assert.equal(drives.length, 20);
  assert.equal(drives[1].props.href, baseUrl + 'libraries/2/');
  assert.equal(drives[1].props['data-doc-target'], 'library:2');
  assert.equal(text(drives[1]), 'Dysk 2');
  assert.equal(
    app.byClass('documents-drive-icon')[1].props.style['--documents-icon-color'],
    '#8b25c7',
  );
  app.button(/^Dodaj dysk$/).props.onClick();
  assert.deepEqual(app.opened, [baseUrl + 'libraries/create/']);
  app.unmount();
});

test('open drive selection and drop feedback survive the portal; read-only retains navigation only', () => {
  const app = harness({
    data: data(20, { libraries: false, library: { id: '2' } }),
    drop: 'library:3',
  });
  app.render();
  assert.equal(app.links()[0].props['aria-current'], undefined);
  assert.equal(app.links()[1].props['aria-current'], 'page');
  assert.equal(app.byClass('is-document-drop-target')[0].props.href, baseUrl + 'libraries/3/');
  app.render({ readOnly: true, drop: null });
  assert.equal(app.links().length, 20);
  assert.ok(app.links().every((link) => link.props['data-doc-target'] === undefined));
  assert.ok(app.buttons().every((button) => button.props['aria-label'] !== 'Dodaj dysk'));
  app.unmount();
});

test('empty and optional pagination payloads remain usable without an extra request', () => {
  const app = harness({ data: data(0, { sidebar_window: undefined }) });
  app.render();
  assert.match(text(app.byClass('documents-sidebar-empty')[0]), /Brak dysków w tym Workspace/);
  assert.equal(app.links().length, 0);
  assert.equal(app.byClass('app-load-more').length, 0);
  assert.equal(app.requests.length, 0);
  app.unmount();
});

test('sidebar loads 20 to 24 drives once without replacing or mutating the main directory rows', async () => {
  const original = data();
  const mainRows = original.rows;
  Object.freeze(mainRows[0]);
  Object.freeze(mainRows);
  Object.freeze(original);
  const app = harness({ data: original });
  app.render();
  const prefix = app.links().map((node) => node.props.href);
  const more = app.button(/^Pokaż więcej:/);
  more.props.onClick();
  more.props.onClick();
  app.render();
  assert.equal(app.requests.length, 1);
  assert.deepEqual(app.requests[0].args.slice(0, 3), ['/api/v1/page/', moreUrl, 'csrf']);
  assert.equal(app.byClass('documents-sidebar-library-link').length, 20);
  assert.equal(app.button(/^Wczytywanie…:/).props['aria-disabled'], true);
  await app.succeed(0, data(24, { rows: [{ id: 'unrelated-page-result' }] }));
  assert.equal(app.byClass('documents-sidebar-library-link').length, 24);
  assert.deepEqual(
    app
      .links()
      .slice(0, 20)
      .map((node) => node.props.href),
    prefix,
  );
  assert.equal(app.input, original);
  assert.equal(app.input.rows, mainRows);
  assert.equal(app.input.rows[0].id, 'main-result');
  assert.equal(app.button(/^Wszystkie wyniki:/).props['aria-disabled'], true);
  app.button(/^Wszystkie wyniki:/).props.onClick();
  assert.equal(app.requests.length, 1);
  app.unmount();
});

test('failed load preserves drives and retries the same window; busy directory blocks loading', async () => {
  const app = harness({ busy: true });
  app.render();
  assert.equal(app.button(/^Dodaj dysk$/).props.disabled, true);
  app.button(/^Pokaż więcej:/).props.onClick();
  assert.equal(app.requests.length, 0);
  app.render({ busy: false });
  app.button(/^Pokaż więcej:/).props.onClick();
  await app.fail(0);
  assert.equal(app.byClass('documents-sidebar-library-link').length, 20);
  assert.match(text(app.byClass('work-list-more-error')[0]), /Brak połączenia/);
  app.button(/^Pokaż więcej:/).props.onClick();
  assert.equal(app.requests.length, 2);
  assert.equal(app.requests[1].args[1], app.requests[0].args[1]);
  await app.succeed(1);
  assert.equal(app.byClass('documents-sidebar-library-link').length, 24);
  assert.equal(app.byClass('work-list-more-error').length, 0);
  app.unmount();
});

test('new page data aborts the old window and ignores its late result', async () => {
  const app = harness();
  app.render();
  app.button(/^Pokaż więcej:/).props.onClick();
  const replacement = data(1, {
    base_url: '/workplaces/another/drive/',
    sidebar: [
      {
        id: 'new',
        name: 'Nowy Workspace',
        url: '/workplaces/another/drive/libraries/1/',
        target: 'library:1',
      },
    ],
    sidebar_window: { count: 1, has_next: false, next_url: '' },
  });
  app.render({ data: replacement });
  assert.equal(app.requests[0].args[3].aborted, true);
  await app.succeed(0);
  assert.equal(app.byClass('documents-sidebar-library-link').length, 1);
  assert.equal(text(app.byClass('documents-sidebar-library-link')[0]), 'Nowy Workspace');
  assert.equal(app.links()[0].props.href, replacement.sidebar[0].url);
  app.unmount();
});

test('credential change aborts the old request and retries with current credentials', async () => {
  const app = harness();
  app.render();
  app.button(/^Pokaż więcej:/).props.onClick();
  app.render({ api: '/api/v2/page/', token: 'new-csrf' });
  assert.equal(app.requests[0].args[3].aborted, true);
  app.button(/^Pokaż więcej:/).props.onClick();
  assert.equal(app.requests.length, 2);
  assert.deepEqual(app.requests[1].args.slice(0, 3), ['/api/v2/page/', moreUrl, 'new-csrf']);
  await app.succeed(0);
  assert.equal(app.byClass('documents-sidebar-library-link').length, 20);
  await app.succeed(1);
  assert.equal(app.byClass('documents-sidebar-library-link').length, 24);
  app.unmount();
});

test('unmount aborts loading and a late response cannot update state', async () => {
  const app = harness();
  app.render();
  app.button(/^Pokaż więcej:/).props.onClick();
  app.unmount();
  assert.equal(app.requests[0].args[3].aborted, true);
  await app.succeed(0);
  assert.equal(app.writesAfterUnmount, 0);
});

test('permission loss clears stale links while a malformed page keeps existing drives and reports error', async () => {
  const app = harness();
  app.render();
  app.button(/^Pokaż więcej:/).props.onClick();
  await app.succeed(0, data(24, { office: true }));
  assert.equal(app.byClass('documents-sidebar-library-link').length, 20);
  assert.match(text(app.byClass('work-list-more-error')[0]), /Nie udało się odczytać listy dysków/);
  app.button(/^Pokaż więcej:/).props.onClick();
  await app.fail(1, new PageError('Brak dostępu', 403));
  assert.equal(app.byClass('documents-sidebar-library-link').length, 0);
  assert.match(text(app.byClass('work-list-more-error')[0]), /Brak dostępu/);
  app.unmount();
});
