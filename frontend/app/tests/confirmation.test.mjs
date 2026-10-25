import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import vm from 'node:vm';

const source = await readFile(new URL('../../../static/js/modal.js', import.meta.url), 'utf8');

function confirmation(options) {
  const nodes = [];
  const control = { addEventListener() {}, focus() {} };
  const document = {
    querySelector: () => null,
    activeElement: null,
    addEventListener() {},
    body: { appendChild() {} },
    createElement() {
      const classes = new Set();
      const node = {
        classList: { add: (value) => classes.add(value), contains: (value) => classes.has(value) },
        setAttribute() {},
        appendChild() {},
        querySelector: () => control,
        innerHTML: '',
      };
      nodes.push(node);
      return node;
    },
  };
  const window = {};
  vm.runInNewContext(source, { window, document, requestAnimationFrame() {} });
  window.showConfirmModal(options);
  return nodes.find((node) => node.innerHTML)?.innerHTML;
}

test('plain confirmation text never becomes executable profile markup', () => {
  const name = '<img src=x onerror="window.executed=true"> & \'osoba\'';
  const html = confirmation({ messageText: `Odebrać dostęp osobie ${name}?` });
  assert.ok(html.includes('&lt;img src=x onerror=&quot;window.executed=true&quot;&gt;'));
  assert.ok(html.includes('&amp; &#39;osoba&#39;'));
  assert.ok(!html.includes('<img'));
});

test('existing formatted confirmation messages retain their supported HTML', () => {
  assert.ok(
    confirmation({ message: 'Usunąć <strong>element</strong>?' }).includes(
      '<strong>element</strong>',
    ),
  );
});
