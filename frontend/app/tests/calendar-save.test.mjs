import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';
import ts from 'typescript';

// Run the real editor render and save handler, replacing only DOM/HTTP boundaries.
const bundle = await build({
  stdin: {
    contents: `import React from 'react';
      import { renderToStaticMarkup } from 'react-dom/server';
      import { EventEditor } from './src/calendar/EventEditor';
      export const render = props => renderToStaticMarkup(React.createElement(EventEditor, props));`,
    resolveDir: new URL('..', import.meta.url).pathname,
  },
  plugins: [
    {
      name: 'calendar-editor-boundaries',
      setup(builder) {
        builder.onLoad({ filter: /\/calendar\/EventEditor\.tsx$/ }, async ({ path }) => ({
          contents: (await readFile(path, 'utf8')).replace(
            'const fieldErrors =',
            'globalThis.calendarCapture = { save, allDay, form }; const fieldErrors =',
          ),
          loader: 'tsx',
        }));
        builder.onResolve({ filter: /^\.\.\/shared\/(Modal|page)$/ }, (args) => {
          if (args.importer.endsWith('/calendar/EventEditor.tsx'))
            return { path: args.path, namespace: 'calendar-boundary' };
        });
        builder.onLoad({ filter: /.*/, namespace: 'calendar-boundary' }, ({ path }) => ({
          contents: path.endsWith('Modal')
            ? 'export const Modal = props => props.children;'
            : 'export class PageError extends Error {} export const pageRequest = (...args) => globalThis.calendarRequest(...args);',
        }));
      },
    },
  ],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  write: false,
  define: { 'process.env.NODE_ENV': '"production"' },
});

class EditorFormData extends FormData {
  constructor(form) {
    super();
    for (const [name, value] of Object.entries(form?.values || {}))
      if (value !== null) this.set(name, value);
  }
}
const context = {
  module: { exports: {} },
  require: createRequire(import.meta.url),
  AbortController,
  FormData: EditorFormData,
  Date,
  TextEncoder,
  TextDecoder,
  Buffer,
  console,
  process,
  setTimeout,
  clearTimeout,
  setImmediate,
};
context.exports = context.module.exports;
vm.runInNewContext(bundle.outputFiles[0].text, context);

function editor(event, { allDay = false, date = new Date(2026, 5, 1, 10) } = {}) {
  const requests = [],
    notices = [];
  context.calendarRequest = async (...args) => requests.push(args);
  const html = context.module.exports.render({
    event,
    date,
    allDay,
    api: '/api/',
    csrfToken: 'token',
    urls: { create: '/events/create/', update: '/events/__ID__/update/', delete: '' },
    onClose() {},
    onSaved: (message) => notices.push(message),
  });
  const values = {
    title: 'Zmieniony opis',
    color: 'blue',
    all_day: event?.all_day || allDay ? 'on' : null,
  };
  for (const name of ['start', 'end']) {
    const input = html.match(new RegExp(`<input[^>]*name="${name}"[^>]*>`))?.[0];
    values[name] = input?.match(/value="([^"]*)"/)?.[1];
    assert.ok(values[name], `rendered ${name} input`);
  }
  const controls = Object.fromEntries(
    ['start', 'end'].map((name) => [
      name,
      {
        get value() {
          return values[name];
        },
        set value(value) {
          values[name] = value;
        },
      },
    ]),
  );
  const capture = context.calendarCapture;
  capture.form.current = { values, elements: { namedItem: (name) => controls[name] } };
  return {
    values,
    requests,
    notices,
    save: () => capture.save({ preventDefault() {} }),
    allDay: capture.allDay,
  };
}
const event = (start, end, all_day = false) => ({
  id: 7,
  title: 'Spotkanie',
  description: '',
  start,
  end,
  all_day,
  color: 'blue',
  source: 'events',
});

for (const zone of ['UTC', 'Europe/Warsaw', 'America/New_York', 'Pacific/Kiritimati']) {
  test(`timed creation and unchanged edits preserve instants in ${zone}`, async () => {
    process.env.TZ = zone;
    const existing = event('2026-06-01T12:00:00+02:00', '2026-06-01T13:00:00+02:00');
    const edit = editor(existing);
    await edit.save();
    assert.equal(edit.requests[0][1], '/events/7/update/');
    for (const name of ['start', 'end'])
      assert.equal(
        new Date(edit.requests[0][4].get(name)).toISOString(),
        new Date(existing[name]).toISOString(),
      );
    assert.equal(edit.notices.length, 1);
    edit.values.start = '2026-06-02T09:00';
    edit.values.end = '2026-06-02T10:00';
    await edit.save();
    assert.equal(edit.requests[1][4].get('start'), new Date('2026-06-02T09:00').toISOString());
    assert.equal(edit.requests[1][4].get('end'), new Date('2026-06-02T10:00').toISOString());
    const create = editor(null);
    create.values.start = '2026-06-01T10:00';
    create.values.end = '2026-06-01T11:00';
    await create.save();
    assert.equal(create.requests[0][1], '/events/create/');
    assert.equal(create.requests[0][4].get('start'), new Date('2026-06-01T10:00').toISOString());
    assert.match(create.requests[0][4].get('end'), /Z$/);
  });
  test(`all-day editor retains calendar dates in ${zone}`, async () => {
    process.env.TZ = zone;
    const edit = editor(event('2026-03-29T00:00:00+01:00', '2026-03-30T23:59:59+02:00', true));
    assert.equal(edit.values.start, '2026-03-29T00:00');
    assert.equal(edit.values.end, '2026-03-30T23:59');
    await edit.save();
    assert.equal(edit.requests[0][4].get('start'), '2026-03-29T00:00');
    assert.equal(edit.requests[0][4].get('end'), '2026-03-30T23:59');
    const create = editor(null, { allDay: true });
    await create.save();
    assert.equal(create.requests[0][4].get('start'), '2026-06-01T00:00');
    assert.equal(create.requests[0][4].get('end'), '2026-06-01T23:59');
    edit.allDay(false);
    assert.equal(edit.values.start, '2026-03-29T09:00');
    assert.equal(edit.values.end, '2026-03-30T10:00');
  });
}

test('untouched timed fields retain seconds and both repeated DST occurrences', async () => {
  process.env.TZ = 'Europe/Warsaw';
  const existing = event('2026-10-25T02:45:17+02:00', '2026-10-25T02:15:19+01:00');
  const edit = editor(existing);
  await edit.save();
  assert.equal(edit.requests[0][4].get('start'), existing.start);
  assert.equal(edit.requests[0][4].get('end'), existing.end);
});

for (const [zone, missing, repeated, before, after] of [
  ['Europe/Warsaw', '2026-03-29T02:30', '2026-10-25T02:30', '2026-03-29T01:30', '2026-03-29T03:30'],
  [
    'America/New_York',
    '2026-03-08T02:30',
    '2026-11-01T01:30',
    '2026-03-08T01:30',
    '2026-03-08T03:30',
  ],
]) {
  test(`timed save uses each DST offset and rejects missing hours in ${zone}`, async () => {
    process.env.TZ = zone;
    const create = editor(null);
    create.values.start = before;
    create.values.end = after;
    await create.save();
    const body = create.requests[0][4];
    assert.equal(new Date(body.get('end')) - new Date(body.get('start')), 3600000);
    for (const value of [missing, repeated]) {
      const invalid = editor(null);
      invalid.values.start = value;
      invalid.values.end = after;
      await invalid.save();
      assert.equal(invalid.requests.length, 0);
      assert.equal(invalid.notices.length, 0);
    }
  });
}

// The non-React adapter uses the same date semantics at its actual submit boundary.
const legacy = ts.createSourceFile(
  'calendar.js',
  await readFile(new URL('../../../static/js/calendar.js', import.meta.url), 'utf8'),
  ts.ScriptTarget.Latest,
  true,
);
const functions = [];
const names = new Set([
  'pad',
  'toLocalInputValue',
  'eventDate',
  'eventInputValue',
  'eventDateValue',
  'saveEvent',
]);
function visit(node) {
  if (ts.isFunctionDeclaration(node) && names.has(node.name?.text)) functions.push(node.getText());
  ts.forEachChild(node, visit);
}
visit(legacy);
assert.equal(functions.length, names.size);
for (const zone of ['UTC', 'Europe/Warsaw', 'America/New_York']) {
  test(`fallback submit preserves timed instants and all-day dates in ${zone}`, async () => {
    process.env.TZ = zone;
    for (const existing of [
      event('2026-10-25T02:45:17+02:00', '2026-10-25T02:15:19+01:00'),
      event('2026-03-29T00:00:00+01:00', '2026-03-30T23:59:59+02:00', true),
    ]) {
      const values = { start: '', end: '' },
        requests = [],
        errors = [];
      const scope = {
        Date,
        FormData: EditorFormData,
        saving: false,
        editedEvent: existing,
        eventForm: { values },
        eventAllDayInput: { checked: existing.all_day },
        eventStartInput: {
          get value() {
            return values.start;
          },
        },
        eventEndInput: {
          get value() {
            return values.end;
          },
          focus() {},
        },
        eventTitleInput: { value: 'Opis', focus() {} },
        eventDescInput: { value: '' },
        eventIdInput: { value: '7' },
        clearFormError() {},
        applyAllDayTimes() {},
        showFormError: (message) => errors.push(message),
        setSaving() {},
        apiUrl: () => '/events/7/update/',
        urls: {},
        csrfToken: 'token',
        startOfDay: (date) => date,
        cloneDate: (date) => date,
        closeDialog() {},
        fetchEvents() {},
        fetch: async (url, options) => {
          requests.push(options.body);
          return { ok: true, json: async () => ({ status: 'success', event: existing }) };
        },
      };
      vm.runInNewContext(functions.join('\n') + '\nglobalThis.submit = saveEvent;', scope);
      values.start = scope.eventInputValue(existing, 'start');
      values.end = scope.eventInputValue(existing, 'end');
      await scope.submit({ preventDefault() {} });
      assert.equal(errors.length, 0);
      assert.equal(requests.length, 1);
      assert.equal(
        requests[0].get('start'),
        existing.all_day ? existing.start.slice(0, 16) : existing.start,
      );
      assert.equal(
        requests[0].get('end'),
        existing.all_day ? existing.end.slice(0, 16) : existing.end,
      );
    }
  });
}
