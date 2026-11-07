import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

// Run SearchPage, SearchToolbar and the real FieldControl DOM adapter together.
const bundle = await build({
  stdin: {
    contents: `export { default as SearchPage } from './src/filters/SearchPage';
      export { SearchToolbar } from './src/filters/SearchToolbar';
      export { FieldControl } from './src/forms/FormDialog';`,
    resolveDir: new URL('..', import.meta.url).pathname,
  },
  plugins: [
    {
      name: 'filter-data-boundary',
      setup(builder) {
        builder.onResolve({ filter: /\/shared\/(useLoadMorePage|usePageActions)$/ }, (args) => {
          if (!args.importer.endsWith('/filters/SearchPage.tsx')) return;
          return { path: args.path, namespace: 'filter-data-boundary' };
        });
        builder.onLoad({ filter: /.*/, namespace: 'filter-data-boundary' }, (args) => ({
          contents: args.path.endsWith('useLoadMorePage')
            ? 'export const useLoadMorePage = () => globalThis.currentWindow;'
            : 'export const usePageActions = () => ({ busy: false, error: "", modal: null });',
        }));
      },
    },
  ],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  jsx: 'automatic',
  external: ['react', 'react/jsx-runtime', 'react-dom'],
  write: false,
});
const require = createRequire(import.meta.url);
function find(node, component, predicate = () => true) {
  if (Array.isArray(node))
    return node.map((child) => find(child, component, predicate)).find(Boolean);
  if (!node?.props) return undefined;
  if ((!component || node.type === component) && predicate(node)) return node;
  return find(node.props.children, component, predicate);
}
function harness() {
  let previous, cleanup;
  const root = {
    children: [],
    append(element) {
      this.children.push(element);
    },
    replaceChildren() {
      this.children = [];
    },
  };
  class Input {
    setAttribute(name, value) {
      this[name] = value;
    }
  }
  const module = { exports: {} };
  const context = {
    module,
    exports: module.exports,
    require: (name) =>
      name === 'react'
        ? {
            ...require(name),
            useRef: () => ({ current: root }),
            useLayoutEffect: (effect, dependencies) => {
              if (previous && dependencies.every((value, index) => value === previous[index]))
                return;
              cleanup?.();
              previous = dependencies;
              cleanup = effect();
            },
          }
        : require(name),
    HTMLInputElement: Input,
    HTMLSelectElement: class {},
    document: {
      createElement: (tag) => {
        assert.equal(tag, 'input');
        return new Input();
      },
    },
    window: {},
  };
  vm.runInNewContext(bundle.outputFiles[0].text, context);
  const { SearchPage, SearchToolbar, FieldControl } = module.exports;
  return {
    root,
    context,
    render(initial, next = initial.data, fieldName) {
      context.currentWindow = { data: next, loading: false, error: '', loadMore() {} };
      const page = SearchPage({ initial, csrfToken: 'token' });
      const toolbar = find(page, SearchToolbar);
      assert.ok(toolbar, 'the basic filter toolbar remains mounted');
      const tree = SearchToolbar(toolbar.props);
      const field = find(
        tree,
        FieldControl,
        (node) => !fieldName || node.props.field.name === fieldName,
      );
      assert.ok(field);
      FieldControl(field.props);
      return { toolbar: toolbar.props.data, field: field.props.field, tree };
    },
  };
}
function page(value = 'zapisane') {
  return {
    type: 'filter-search',
    title: 'Wyszukaj zadania',
    api_url: '/api/page/',
    url: '/filters/search/',
    data: {
      mode: 'basic',
      items: [],
      can_save: false,
      saved_filter: null,
      search_url: '/filters/search/',
      form: {
        fields: [
          {
            name: 'text',
            id: 'filter-text',
            label: 'Tekst',
            type: 'text',
            value,
            errors: [],
            attrs: {},
          },
        ],
      },
      pagination: { end: 20, count: 45, next: '/filters/search/?limit=40' },
    },
  };
}

test('loading more filter results preserves an unapplied input draft and field identity', () => {
  const app = harness(),
    initial = page();
  const first = app.render(initial);
  const input = app.root.children[0];
  input.value = 'niezastosowany szkic';
  const expanded = {
    ...initial.data,
    form: structuredClone(initial.data.form),
    pagination: { end: 40, count: 45, next: '/filters/search/?limit=45' },
  };
  const next = app.render(initial, expanded);
  assert.equal(next.field, first.field);
  assert.equal(next.toolbar.pagination.end, 40, 'results and counts still receive the new window');
  assert.equal(app.root.children[0], input, 'the imperative field DOM was not replaced');
  assert.equal(input.value, 'niezastosowany szkic');
});

test('a new filter search installs its new criteria instead of retaining the previous draft', () => {
  const app = harness(),
    initial = page();
  app.render(initial);
  const input = app.root.children[0];
  input.value = 'stary szkic';
  const changed = page('nowe zastosowane kryteria');
  const result = app.render(changed);
  assert.equal(result.field, changed.data.form.fields[0]);
  assert.notEqual(app.root.children[0], input);
  assert.equal(app.root.children[0].value, 'nowe zastosowane kryteria');
});

test('the right-side q field retains its draft and identity after loading more, independently of panel filters', () => {
  const app = harness(),
    initial = page();
  const query = initial.data.form.fields[0];
  Object.assign(query, { name: 'q', id: 'filter-q', label: 'Szukaj zadań' });
  initial.data.form.fields.push({
    ...query,
    name: 'status',
    id: 'filter-status',
    label: 'Status',
    value: 'open',
  });
  const first = app.render(initial, initial.data, 'q');
  const input = app.root.children[0];
  input.value = 'niezastosowane wyszukiwanie';
  const expanded = {
    ...initial.data,
    form: structuredClone(initial.data.form),
    pagination: { end: 40, count: 45, next: '/filters/search/?limit=45' },
  };
  const next = app.render(initial, expanded, 'q');
  const searchSlot = find(next.tree, 'div', (node) =>
    node.props.className?.includes('app-toolbar__search'),
  );
  assert.ok(searchSlot, 'q is outside the collapsed filter panel, in the search slot');
  assert.equal(
    find(searchSlot, undefined, (node) => node.props.field?.name === 'q')?.props.field,
    query,
  );
  assert.equal(find(searchSlot, 'label')?.props.htmlFor, query.id);
  assert.equal(input.name, 'q', 'the original form field name is retained');
  assert.equal(next.field, first.field);
  assert.equal(app.root.children[0], input);
  assert.equal(input.value, 'niezastosowane wyszukiwanie');
  const filterMenu = find(next.tree, undefined, (node) => node.props.label === 'Filtrowanie zadań');
  assert.equal(
    find(filterMenu.props.children, undefined, (node) => node.props.field?.name === 'q'),
    undefined,
    'q is not duplicated inside Filtruj',
  );
  assert.ok(
    find(
      filterMenu.props.trigger,
      'span',
      (node) => node.props['aria-label'] === 'Aktywne filtry: 1',
    ),
    'the active panel filter count excludes q',
  );
  const actionsSlot = find(
    next.tree,
    'div',
    (node) => node.props.className === 'app-toolbar__actions',
  );
  assert.ok(
    find(actionsSlot, 'span', (node) => node.props.role === 'status'),
    'the result count remains in the left caption slot',
  );
});
