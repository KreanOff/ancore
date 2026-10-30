import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

const bundle = await build({
  entryPoints: [new URL('../src/forms/FormDialog.tsx', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  jsx: 'automatic',
  external: ['react', 'react/jsx-runtime', 'react-dom'],
  write: false,
});
const module = { exports: {} };
vm.runInNewContext(bundle.outputFiles[0].text, {
  module,
  exports: module.exports,
  require: createRequire(import.meta.url),
});
const { FormLayout } = module.exports;

function render(fields) {
  return renderToStaticMarkup(
    createElement(FormLayout, {
      fields,
      renderField: (field) =>
        createElement('input', {
          key: field.name,
          name: field.name,
          id: field.id,
          defaultValue: field.value,
        }),
    }),
  );
}

test('subtask layout groups prefixed fields without changing control names or draft values', () => {
  const fields = ['title', 'visibility', 'description', 'status', 'due_at'].map((field_name) => ({
    field_name,
    name: 'subtask-' + field_name,
    id: 'id_subtask-' + field_name,
    value: field_name === 'title' ? 'Szkic podzadania' : '',
  }));
  const html = render(fields);
  assert.match(
    html,
    /class="app-form-heading"><input name="subtask-title"[^>]*value="Szkic podzadania"[^>]*\/><input name="subtask-visibility"[^>]*\/><\/div>/,
  );
  assert.match(
    html,
    /class="app-form-description"><input name="subtask-description"[^>]*\/><\/div><input name="subtask-status"[^>]*\/><input name="subtask-due_at"/,
  );
  for (const field of fields) {
    assert.equal(html.split(`name="${field.name}"`).length - 1, 1);
    assert.ok(html.includes(`id="${field.id}"`));
  }
});

test('layout supports unprefixed schemas without additional metadata', () => {
  const html = render([{ name: 'name' }, { name: 'description' }, { name: 'status' }]);
  assert.match(html, /class="app-form-heading"><input name="name"\/><\/div>/);
  assert.match(html, /class="app-form-description"><input name="description"\/><\/div>/);
  assert.ok(html.endsWith('<input name="status"/></div>'));
});

test('worklog and nested form prefixes use explicit field metadata for the full description', () => {
  for (const prefix of ['worklog', 'items-0-worklog']) {
    const html = render([
      { name: `${prefix}-duration`, field_name: 'duration' },
      { name: `${prefix}-description`, field_name: 'description' },
      { name: `${prefix}-custom-description`, field_name: 'custom-description' },
    ]);
    assert.ok(!html.includes('app-form-heading'));
    assert.ok(
      html.includes(
        `class="app-form-description"><input name="${prefix}-description"/></div><input name="${prefix}-duration"/>`,
      ),
    );
    assert.ok(html.endsWith(`<input name="${prefix}-custom-description"/></div>`));
  }
});
