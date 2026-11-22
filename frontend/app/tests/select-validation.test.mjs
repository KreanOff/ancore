import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

const require = createRequire(import.meta.url);
const bundle = await build({
  entryPoints: [new URL('../src/shared/Select.tsx', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  write: false,
  external: ['react', 'react/jsx-runtime'],
});

function mount(initial) {
  let cursor = 0,
    effect,
    cleanup,
    control,
    trigger,
    changed;
  const refs = [];
  const body = {};
  const document = { body, activeElement: body };
  const element = () => ({
    attrs: {},
    setAttribute(name, value) {
      this.attrs[name] = value;
    },
    focus() {
      document.activeElement = this;
    },
  });
  const host = {
    append(node) {
      control = node;
    },
    contains(node) {
      return node === control || node === trigger;
    },
    replaceChildren() {
      if (this.contains(document.activeElement)) document.activeElement = body;
      control = undefined;
      trigger = undefined;
    },
    querySelector() {
      return trigger;
    },
  };
  const module = { exports: {} };
  vm.runInNewContext(bundle.outputFiles[0].text, {
    module,
    exports: module.exports,
    require(name) {
      if (name === 'react')
        return {
          ...require(name),
          useRef(value) {
            return (refs[cursor++] ||= { current: value });
          },
          useId: () => 'select-test',
          useLayoutEffect(callback) {
            effect = callback;
          },
        };
      return require(name);
    },
    document: {
      body,
      get activeElement() {
        return document.activeElement;
      },
      createElement() {
        return {
          ...element(),
          choices: [],
          add(option) {
            this.choices.push(option);
          },
          addEventListener(name, callback) {
            this[name] = callback;
          },
        };
      },
    },
    Option: class {
      constructor(label, value) {
        this.label = label;
        this.value = value;
      }
    },
    window: {
      AncoreCustomSelect: {
        refresh() {
          trigger = element();
          trigger.disabled = control.disabled;
        },
      },
    },
  });
  let props = {
    label: 'Kategoria',
    name: 'kind',
    options: [
      ['', 'Wybierz kategorię'],
      ['laptop', 'Laptop'],
    ],
    value: '',
    onChange(value) {
      changed = value;
    },
    ...initial,
  };
  function render(next = {}) {
    props = { ...props, ...next };
    cleanup?.();
    cursor = 0;
    const tree = module.exports.Select(props);
    tree.props.children[1].ref.current = host;
    cleanup = effect();
    return tree;
  }
  render();
  return {
    render,
    document,
    get control() {
      return control;
    },
    get trigger() {
      return trigger;
    },
    get changed() {
      return changed;
    },
  };
}

test('Select conveys required, disabled and error descriptions to the actual select and visible custom control', () => {
  const app = mount({
    required: true,
    disabled: true,
    invalid: true,
    describedBy: 'kind-help kind-error',
  });
  assert.equal(app.control.required, true);
  assert.equal(app.control.disabled, true);
  assert.equal(app.control.attrs['aria-invalid'], 'true');
  assert.equal(app.control.attrs['aria-describedby'], 'kind-help kind-error');
  assert.equal(app.trigger.disabled, true);
  assert.equal(app.trigger.attrs['aria-required'], 'true');
  assert.equal(app.trigger.attrs['aria-invalid'], 'true');
  assert.equal(app.trigger.attrs['aria-describedby'], 'kind-help kind-error');
  app.render({ required: false, disabled: false, invalid: false, describedBy: undefined });
  assert.equal(app.control.required, false);
  assert.equal(app.control.disabled, false);
  assert.equal(app.trigger.attrs['aria-invalid'], 'false');
  assert.equal(app.trigger.attrs['aria-describedby'], undefined);
  assert.equal(app.trigger.attrs['aria-required'], undefined);
});

test('optional validation props leave existing controlled selection and change handling intact', () => {
  const app = mount({ value: 'laptop' });
  assert.equal(app.control.value, 'laptop');
  assert.equal(app.control.required, false);
  app.control.value = '';
  app.control.change();
  assert.equal(app.changed, '');
  app.render({ value: 'laptop' });
  assert.equal(app.control.value, 'laptop');
});

test('controlled updates restore keyboard focus to the replacement trigger only when it held focus', () => {
  const app = mount();
  app.trigger.focus();
  app.render({ value: 'laptop' });
  assert.equal(app.document.activeElement, app.trigger);

  const nextControl = {};
  app.document.activeElement = nextControl;
  app.render({ invalid: true });
  assert.equal(app.document.activeElement, nextControl);

  app.trigger.focus();
  app.render({ disabled: true });
  assert.equal(app.document.activeElement, app.document.body);
});
