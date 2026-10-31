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

function renderInput(overrides) {
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
  class Input {
    setAttribute(name, value) {
      this[name] = value;
    }
  }
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
        assert.equal(tag, 'input');
        return new Input();
      },
    },
    window: {},
  });
  module.exports.FieldControl({
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
  });
  effects.forEach((effect) => effect());
  assert.equal(root.children.length, 1);
  return root.children[0];
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
