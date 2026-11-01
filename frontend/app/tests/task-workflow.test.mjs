import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

const bundle = await build({
  stdin: {
    contents: `import React from 'react';
      import { renderToStaticMarkup } from 'react-dom/server';
      import { TaskWorkflowActions, TaskWorkflowStatus } from './src/tasks/TaskWorkflow';
      export const render = props => renderToStaticMarkup(React.createElement(React.Fragment, null,
        React.createElement(TaskWorkflowActions, props),
        React.createElement(TaskWorkflowStatus, {item: props.item})));`,
    resolveDir: new URL('..', import.meta.url).pathname,
  },
  bundle: true,
  platform: 'node',
  format: 'cjs',
  write: false,
  define: { 'process.env.NODE_ENV': '"production"' },
});
const module = { exports: {} };
vm.runInNewContext(bundle.outputFiles[0].text, {
  module,
  exports: module.exports,
  require: createRequire(import.meta.url),
  TextEncoder,
  TextDecoder,
  Buffer,
  console,
  process,
  setTimeout,
  clearTimeout,
  setImmediate,
});
const item = {
  status: 'new',
  status_label: 'Do zrobienia',
  category: 'new',
  transitions: [{ key: 'in_progress', label: 'W toku', category: 'in_progress' }],
};
const render = (values = {}) =>
  module.exports.render({
    item,
    canEdit: true,
    disabled: false,
    pending: false,
    requestedStatus: '',
    onTransition() {},
    ...values,
  });

test('task workflow exposes the confirmed stage and only available transition buttons', () => {
  const html = render();
  assert.match(html, /Bieżący etap: Do zrobienia/);
  assert.match(html, /Przejdź do: W toku/);
  assert.equal((html.match(/<button/g) || []).length, 1);
  assert.doesNotMatch(html, /<select|role="combobox"|Gotowe/);
});

test('read-only tasks show their current stage without mutation controls', () => {
  const html = render({ canEdit: false });
  assert.match(html, /Bieżący etap: Do zrobienia/);
  assert.doesNotMatch(html, /<button|Dostępne przejścia/);
});

test('a final stage displays an empty transition state and a saving stage stays confirmed', () => {
  assert.match(render({ item: { ...item, transitions: [] } }), /Brak dalszych przejść/);
  const html = render({ pending: true, disabled: true, requestedStatus: 'in_progress' });
  assert.match(html, /aria-busy="true"/);
  assert.match(html, /disabled=""/);
  assert.match(html, /Bieżący etap: Do zrobienia/);
  assert.match(html, /Zapisywanie przejścia: W toku/);
});
