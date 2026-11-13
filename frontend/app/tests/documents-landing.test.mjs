import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

const bundle = await build({
  entryPoints: [new URL('../src/documents/DirectoryPage.tsx', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  external: ['react', 'react/jsx-runtime', 'react-dom'],
  plugins: [
    {
      name: 'directory-effects-boundary',
      setup(builder) {
        builder.onResolve({ filter: /^\.\/use(Actions|Drag)$/ }, ({ path }) => ({
          path: `test:${path.slice(2)}`,
          external: true,
        }));
      },
    },
  ],
  write: false,
});
const require = createRequire(import.meta.url);
const baseUrl = '/workplaces/w_test/drive/';
const row = {
  id: '1',
  name: 'Materiały zespołu',
  row_kind: 'library',
  url: baseUrl + '?library=1',
  date: '13.11.2026',
  datetime: '13.11.2026 10:00',
  size: '0 B',
  edit_url: baseUrl + 'libraries/1/edit/',
  target: 'library:1',
  color: '#4285d4',
};
function data(extra = {}) {
  return {
    office: false,
    libraries: true,
    base_url: baseUrl,
    library: null,
    folder: null,
    rows: [row],
    sidebar: [row],
    breadcrumbs: [],
    query: '',
    active_filters: 0,
    views: [
      {
        value: 'all',
        label: 'Wszystkie pliki',
        active: true,
        icon: 'files',
        url: baseUrl + '?view=all',
      },
    ],
    view: 'all',
    display: 'list',
    display_options: [],
    filter_params: {},
    filters: [],
    sort: 'name',
    sort_fields: [],
    operators: [],
    window: { count: 1, has_next: false, next_url: '' },
    sidebar_window: { count: 1, has_next: false, next_url: '' },
    create_url: baseUrl + 'libraries/create/',
    upload_url: baseUrl + 'upload/',
    folder_create_url: baseUrl + 'folders/create/',
    clear_url: baseUrl,
    modal: null,
    ...extra,
  };
}

function text(element) {
  if (element == null || typeof element === 'boolean') return '';
  if (Array.isArray(element)) return element.map(text).join('');
  return typeof element === 'object' ? text(element.props?.children) : String(element);
}

// Render the pure shared shells and real Rows; action/drag effects are separate boundaries.
function nodes(element) {
  if (!element || typeof element !== 'object') return [];
  if (Array.isArray(element)) return element.flatMap(nodes);
  if (!element.props) return [];
  if (
    ['PageHeader', 'Toolbar', 'ToolbarContents', 'Rows', 'EmptyState', 'LoadMore'].includes(
      element.type?.name,
    )
  )
    return [element, ...nodes(element.type(element.props))];
  return [element, ...Object.values(element.props).flatMap(nodes)];
}

function harness(initialData, readOnly = false) {
  const opened = [],
    toggles = [],
    selectors = [];
  let expanded = false;
  const react = {
    ...require('react'),
    useState: (initial) => [typeof initial === 'function' ? initial() : initial, () => {}],
    useRef: (current) => ({ current }),
    useEffect() {},
    useLayoutEffect() {},
  };
  const module = { exports: {} };
  vm.runInNewContext(bundle.outputFiles[0].text, {
    module,
    exports: module.exports,
    require(name) {
      if (name === 'react') return react;
      if (name === 'test:useActions')
        return {
          useActions: () => ({
            busy: false,
            error: '',
            modal: null,
            open: (...args) => opened.push(args),
          }),
        };
      if (name === 'test:useDrag')
        return {
          useDrag: () => ({
            dragged: null,
            drop: null,
            handlers: {},
            overlay: null,
          }),
        };
      return require(name);
    },
    document: {
      querySelector(selector) {
        selectors.push(selector);
        return !expanded && selector === '[data-right-sidebar-toggle][aria-expanded="false"]'
          ? {
              click() {
                toggles.push(true);
                expanded = true;
              },
            }
          : null;
      },
    },
    URLSearchParams,
    AbortController,
    Error,
  });
  const tree = module.exports.default({
    initial: {
      data: initialData,
      title: initialData.office ? 'Dokumenty' : 'Dysk',
      api_url: '/api/v1/page/',
      read_only: readOnly,
    },
    csrfToken: 'csrf',
  });
  const all = nodes(tree);
  return {
    all,
    opened,
    toggles,
    selectors,
    components: (name) => all.filter((node) => node.type?.name === name),
    byClass: (name) => all.filter((node) => (node.props.className || '').split(' ').includes(name)),
    buttons: (label) => all.filter((node) => node.type === 'button' && text(node) === label),
  };
}

for (const display of ['list', 'grid']) {
  test(`drive index has only the shared sidebar drive list and a chooser, display=${display}`, () => {
    const initialData = data({ display });
    const app = harness(initialData);
    assert.equal(app.components('Rows').length, 0);
    assert.equal(app.components('Toolbar').length, 0);
    assert.equal(app.byClass('documents-library-sheet').length, 0);
    assert.equal(app.byClass('documents-grid--libraries').length, 0);
    assert.equal(app.components('Sidebar').length, 1);
    assert.equal(app.components('Sidebar')[0].props.data, initialData);
    assert.equal(app.components('PageHeader').length, 1);
    const empty = app.components('EmptyState')[0];
    assert.ok(empty);
    assert.equal(empty.props.title, 'Wybierz dysk');
    assert.match(
      text(empty.props.description),
      /Otwórz dysk z prawego panelu, aby zobaczyć foldery i pliki\./,
    );
    const chooser = app.buttons('Wybierz dysk');
    assert.equal(chooser.length, 1);
    chooser[0].props.onClick();
    chooser[0].props.onClick();
    assert.equal(
      app.toggles.length,
      1,
      'the existing shell opener opens, rather than toggles, the right panel',
    );
    assert.ok(
      app.selectors.every(
        (selector) => selector === '[data-right-sidebar-toggle][aria-expanded="false"]',
      ),
    );
    app.buttons('Nowy dysk')[0].props.onClick();
    assert.equal(app.opened.length, 1);
    assert.equal(app.opened[0][0], initialData.create_url);
    assert.equal(app.opened[0][1].length, 0);
  });
}

test('obsolete empty search results cannot replace the chooser while the sidebar still has drives', () => {
  const app = harness(
    data({ rows: [], query: 'nieistniejący', active_filters: 1, window: { count: 0 } }),
  );
  assert.equal(app.components('EmptyState')[0].props.title, 'Wybierz dysk');
  assert.equal(app.components('Rows').length, 0);
  assert.equal(app.components('Toolbar').length, 0);
  assert.equal(app.buttons('Wybierz dysk').length, 1);
});

test('empty Workspace retains the shared first-drive state and header creation action', () => {
  const initialData = data({
    rows: [],
    sidebar: [],
    sidebar_window: { count: 0, has_next: false, next_url: '' },
  });
  const app = harness(initialData);
  assert.equal(app.components('EmptyState')[0].props.title, 'Utwórz pierwszy dysk');
  assert.equal(
    app.components('EmptyState')[0].props.description,
    'Dysk to osobne miejsce na foldery i pliki, np. dla projektu lub działu.',
  );
  assert.equal(app.buttons('Wybierz dysk').length, 0);
  assert.equal(app.components('Rows').length, 0);
  assert.equal(app.components('Toolbar').length, 0);
  app.buttons('Nowy dysk')[0].props.onClick();
  assert.equal(app.opened[0][0], initialData.create_url);
  assert.equal(app.components('Sidebar').length, 1);
});

test('read-only drive index allows choosing a drive without creation controls', () => {
  const app = harness(data(), true);
  assert.equal(app.buttons('Nowy dysk').length, 0);
  assert.equal(app.components('Sidebar')[0].props.readOnly, true);
  app.buttons('Wybierz dysk')[0].props.onClick();
  assert.equal(app.toggles.length, 1);
  assert.equal(app.opened.length, 0);
});

test('chosen drive retains its file rows, toolbar, navigation and upload/folder actions', () => {
  const file = {
    ...row,
    id: 'folder:7',
    name: 'Dokumentacja',
    row_kind: 'folder',
    target: 'folder:7',
    url: baseUrl + '?folder=7',
  };
  const initialData = data({
    libraries: false,
    library: row,
    rows: [file],
    breadcrumbs: [{ name: row.name, target: row.target, url: row.url }],
  });
  const app = harness(initialData);
  assert.equal(app.components('Rows').length, 1);
  assert.equal(app.components('Toolbar').length, 1);
  assert.equal(app.components('Sidebar').length, 1);
  assert.equal(app.buttons('Wybierz dysk').length, 0);
  const link = app.all.find((node) => node.type === 'a' && node.props.href === file.url);
  assert.ok(link);
  assert.equal(text(link), file.name);
  app.buttons('Prześlij pliki')[0].props.onClick();
  app.buttons('Nowy folder')[0].props.onClick();
  assert.deepEqual(
    app.opened.map(([url]) => url),
    [initialData.upload_url, initialData.folder_create_url],
  );
});

test('Office retains document rows, toolbar and quick creation without a drive sidebar', () => {
  const document = {
    ...row,
    id: 'doc:1',
    name: 'Notatka',
    row_kind: 'document',
    url: '/office/doc/1/',
  };
  const initialData = data({
    office: true,
    libraries: false,
    rows: [document],
    sidebar: [],
    base_url: '/office/',
    create_url: '/office/create/',
    upload_url: '/office/upload/',
  });
  const app = harness(initialData);
  assert.equal(app.components('Rows').length, 1);
  assert.equal(app.components('Toolbar').length, 1);
  assert.equal(app.components('Sidebar').length, 0);
  assert.equal(app.buttons('Wybierz dysk').length, 0);
  assert.equal(app.byClass('office-quick-create').length, 1);
  assert.ok(app.all.some((node) => node.type === 'a' && node.props.href === document.url));
  const create = app.all.find(
    (node) => node.type === 'button' && node.props['aria-label'] === 'Utwórz plik: Dokument',
  );
  create.props.onClick();
  assert.equal(app.opened[0][0], '/office/create/?type=word');
  const readOnly = harness(initialData, true);
  assert.equal(readOnly.byClass('office-quick-create').length, 0);
  assert.equal(readOnly.components('Rows').length, 1);
  assert.equal(readOnly.components('Toolbar').length, 1);
});
