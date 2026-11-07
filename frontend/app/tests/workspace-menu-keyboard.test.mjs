import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

const bundle = await build({
  entryPoints: [new URL('../src/shell/WorkspaceMenu.tsx', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  jsx: 'automatic',
  external: ['react', 'react/jsx-runtime'],
  write: false,
});
const require = createRequire(import.meta.url);

function nodes(element) {
  if (!element || typeof element !== 'object') return [];
  if (Array.isArray(element)) return element.flatMap(nodes);
  return [element, ...nodes(element.props?.children)];
}

test('workspace picker enters its first or last item from search and keeps Home/End in the input', () => {
  class Input {}
  const input = new Input();
  const document = { activeElement: input };
  const refs = [];
  const items = Array.from({ length: 3 }, () => ({
    getClientRects: () => [{}],
    focus() {
      document.activeElement = this;
    },
  }));
  const module = { exports: {} };
  vm.runInNewContext(bundle.outputFiles[0].text, {
    module,
    exports: module.exports,
    document,
    HTMLInputElement: Input,
    require(name) {
      if (name === 'react')
        return {
          useState: (value) => [value, () => {}],
          useRef: (value) => {
            const ref = { current: value };
            refs.push(ref);
            return ref;
          },
          useEffect() {},
        };
      if (name === 'react/jsx-runtime')
        return {
          jsx: (type, props) => ({ type, props }),
          jsxs: (type, props) => ({ type, props }),
        };
      return require(name);
    },
  });
  const tree = module.exports.default({ data: { workplaces: [] }, token: 'csrf' });
  refs[0].current = { querySelectorAll: () => items };
  const menu = nodes(tree).find((node) => node.props?.role === 'menu');
  function press(key) {
    let prevented = false;
    menu.props.onKeyDown({
      key,
      target: document.activeElement,
      preventDefault() {
        prevented = true;
      },
    });
    return prevented;
  }
  assert.equal(press('Home'), false);
  assert.equal(document.activeElement, input);
  assert.equal(press('End'), false);
  assert.equal(document.activeElement, input);
  assert.equal(press('ArrowUp'), true);
  assert.equal(document.activeElement, items[2]);
  press('ArrowDown');
  assert.equal(document.activeElement, items[0]);
  document.activeElement = input;
  press('ArrowDown');
  assert.equal(document.activeElement, items[0]);
});
