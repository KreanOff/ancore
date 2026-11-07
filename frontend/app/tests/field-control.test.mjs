import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

// Run the actual field adapter and its DOM effect without mounting unrelated dialogs.
const bundle = await build({
  entryPoints: [new URL('../src/forms/FormDialog.tsx', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  jsx: 'automatic',
  external: ['react', 'react/jsx-runtime', 'react-dom'],
  write: false,
});
const require = createRequire(import.meta.url);

function renderControl(overrides, options = {}) {
  const effects = [];
  const root = {
    children: [],
    append(element) {
      this.children.push(element);
    },
    replaceChildren() {
      this.children = [];
    },
  };
  class Element {
    constructor(tag) {
      this.tag = tag;
      this.children = [];
    }
    setAttribute(name, value) {
      this[name] = value;
    }
    append(...elements) {
      this.children.push(...elements);
    }
  }
  class Input extends Element {}
  const module = { exports: {} };
  vm.runInNewContext(bundle.outputFiles[0].text, {
    module,
    exports: module.exports,
    require: (name) =>
      name === 'react'
        ? {
            ...require(name),
            useRef: () => ({ current: root }),
            useLayoutEffect: (callback) => effects.push(callback),
          }
        : require(name),
    HTMLInputElement: Input,
    HTMLSelectElement: class {},
    document: {
      createElement(tag) {
        return tag === 'input' ? new Input(tag) : new Element(tag);
      },
      createTextNode: (text) => text,
    },
    window: {},
  });
  const tree = module.exports.FieldControl({
    field: {
      name: 'fields-0-required',
      id: 'id_fields-0-required',
      label: 'Wymagane',
      type: 'checkbox',
      value: null,
      checked: false,
      hidden: false,
      required: false,
      disabled: false,
      attrs: {},
      errors: [],
      help_text: '',
      ...overrides,
    },
    ...options,
  });
  effects.forEach((effect) => effect());
  assert.equal(root.children.length, 1);
  return { control: root.children[0], tree };
}
const renderInput = (overrides) => renderControl(overrides).control;

function find(node, predicate) {
  if (Array.isArray(node)) return node.map((child) => find(child, predicate)).find(Boolean);
  if (!node?.props) return undefined;
  return predicate(node) ? node : find(node.props.children, predicate);
}

test('Boolean checkbox controls submit a nonempty value without changing checked state or other field values', () => {
  for (const name of ['fields-0-required', 'types-0-DELETE']) {
    for (const checked of [false, true]) {
      const input = renderInput({ name, checked });
      assert.equal(input.type, 'checkbox');
      assert.equal(input.name, name);
      assert.equal(input.checked, checked);
      assert.equal(input.value, 'on');
    }
  }
  assert.equal(renderInput({ value: 'approved', checked: true }).value, 'approved');
  assert.equal(renderInput({ type: 'text', value: null }).value, '');
  assert.equal(renderInput({ type: 'text', value: '' }).value, '');
  assert.equal(renderInput({ type: 'text', value: 'Szkic' }).value, 'Szkic');
});

test('checkbox groups connect field instructions and errors to each focusable choice', () => {
  const { control: group, tree } = renderControl({
    name: 'modules',
    id: 'id_modules',
    label: 'Moduły',
    type: 'checkboxes',
    value: ['spaces'],
    help_text: 'Wybierz dostępne moduły.',
    errors: ['Wybierz co najmniej jeden moduł.'],
    choices: [
      { value: 'spaces', label: 'Przestrzenie' },
      { value: 'documents', label: 'Dokumenty' },
    ],
  });
  assert.equal(group.id, 'id_modules');
  assert.equal(group.role, 'group');
  assert.equal(group['aria-label'], 'Moduły');
  assert.equal(group['aria-describedby'], 'id_modules_help id_modules_error');
  const choices = group.children.map((row) => row.children[0].children[0]);
  assert.deepEqual(
    choices.map((input) => input.checked),
    [true, false],
  );
  for (const input of choices) {
    assert.equal(input.name, 'modules');
    assert.equal(input['aria-invalid'], 'true');
    assert.equal(input['aria-describedby'], 'id_modules_help id_modules_error');
  }
  const error = find(tree, (node) => node.props.id === 'id_modules_error');
  assert.equal(error.props.role, 'alert');
});

test('a valid disabled checkbox group keeps its state without an invalid or dangling description', () => {
  const group = renderInput({
    type: 'checkboxes',
    disabled: true,
    choices: [{ value: 'spaces', label: 'Przestrzenie' }],
  });
  const input = group.children[0].children[0].children[0];
  assert.equal(input.disabled, true);
  assert.equal(input['aria-invalid'], 'false');
  assert.equal(input['aria-describedby'], undefined);
});

test('bare inline controls retain an accessible description when their visible label is omitted', () => {
  const { control, tree } = renderControl(
    { type: 'text', help_text: 'Wpisz tytuł zadania.' },
    { bare: true },
  );
  const description = find(tree, (node) => node.props.id === control['aria-describedby']);
  assert.equal(description.props.children, 'Wpisz tytuł zadania.');
  assert.equal(description.props.className, 'u-sr-only');
});
