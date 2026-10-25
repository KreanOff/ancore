import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

// Render TaskPage and its real Members/Dropdown children from the page API contract.
const bundle = await build({
  stdin: {
    contents: `import React from 'react';
      import { renderToStaticMarkup } from 'react-dom/server';
      import TaskPage from './src/tasks/TaskPage';
      export const render = props => renderToStaticMarkup(React.createElement(TaskPage, props));`,
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
  AbortController,
  TextEncoder,
  TextDecoder,
  Buffer,
  console,
  process,
  setTimeout,
  clearTimeout,
  setImmediate,
});

function field(name, type = 'text') {
  return {
    name,
    id: `task-${name}`,
    label: name,
    type,
    value: name === 'title' ? 'Zadanie testowe' : '',
    errors: [],
    attrs: {},
  };
}

function page(viewer) {
  const manager = ['owner', 'admin'].includes(viewer);
  const members = ['owner', 'admin', 'member', 'observer'].map((role, index) => ({
    id: index + 1,
    user_id: index + 1,
    name: role,
    email: `${role}@example.test`,
    avatar: {},
    role,
    role_label: role,
    created_at: null,
    can_change: manager && role !== 'owner' && (viewer === 'owner' || role !== 'admin'),
  }));
  const schema = { fields: [], errors: [] };
  return {
    initial: {
      type: 'space-task',
      url: '/space/test/tasks/TS-1/?tab=members',
      api_url: '/api/v1/page/',
      data: {
        item: { id: 1, key: 'TS-1', title: 'Zadanie testowe' },
        form: { ...schema, fields: [field('title'), field('description', 'textarea')] },
        can_edit: viewer !== 'observer',
        error: '',
        tab: 'members',
        tabs: [{ key: 'members', label: 'Członkowie', icon: 'users' }],
        back_url: '/space/test/',
        visibility: 'private',
        statuses: [{ key: 'new', label: 'Nowe', category: 'new' }],
        status: 'new',
        comments: [],
        children: [],
        files: [],
        history: [],
        mentions: [],
        comment_draft: '',
        created_by: null,
        work_log: { total_minutes: 0, total_label: '0 min', count: 0, pages: 1, results: [] },
        team_url: '/space/test/tasks/TS-1/team/',
        team: {
          can_manage: manager,
          is_owner: viewer === 'owner',
          share_form: { ...schema, fields: [field('email'), field('role', 'select')] },
          members,
        },
      },
    },
    csrfToken: 'token',
  };
}

for (const [viewer, editableRows] of [
  ['owner', ['admin', 'member', 'observer']],
  ['admin', ['member', 'observer']],
  ['member', []],
  ['observer', []],
]) {
  test(`${viewer} sees role and removal actions only for permitted task members`, () => {
    const html = module.exports.render(page(viewer));
    assert.equal((html.match(/>Zmień rolę<\/span>/g) || []).length, editableRows.length);
    assert.equal((html.match(/>Odbierz dostęp<\/span>/g) || []).length, editableRows.length);
    for (const role of ['owner', 'admin', 'member', 'observer']) {
      assert.equal(html.includes(`aria-label="Działania: ${role}"`), editableRows.includes(role));
    }
    assert.equal(html.includes('>Udostępnij</span>'), ['owner', 'admin'].includes(viewer));
  });
}
