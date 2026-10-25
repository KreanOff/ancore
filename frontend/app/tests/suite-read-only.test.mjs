import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

// Render the real suite header from the page API contract, including its title controls.
const bundle = await build({
  stdin: {
    contents: `import React from 'react';
      import { renderToStaticMarkup } from 'react-dom/server';
      import SuitePage from './src/documents/SuitePage';
      export const render = props => renderToStaticMarkup(React.createElement(SuitePage, props));`,
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

function page(readOnly, renameUrl, drive = false, board = false) {
  const base = drive ? '/documents/' : '/office/';
  return {
    initial: {
      type: 'office-suite',
      url: `${base}1/editor/`,
      api_url: '/api/v1/page/',
      read_only: readOnly,
      data: {
        document: {
          id: '1',
          name: 'Dokument zespołu',
          variant: board ? 'board' : 'word',
          download_url: `${base}1/download/`,
        },
        drive,
        back_url: base,
        revision: 1,
        rename_url: renameUrl,
        save_url: readOnly ? '' : `${base}1/save/`,
        state_url: `${base}1/state/`,
        board_url: board ? `${base}1/board/` : '',
        editor_config: null,
        api_url: '',
      },
    },
    csrfToken: 'token',
  };
}

function assertPlainTitle(html) {
  assert.match(
    html,
    /<h1[^>]*><span class="office-suite-title-text"[^>]*>Dokument zespołu<\/span><\/h1>/,
  );
  assert.doesNotMatch(html, /Zmień nazwę|Nazwa pliku|suite-title-hint|suite-title-error/);
  assert.doesNotMatch(html, /office-suite-title-button|office-suite-title-input/);
}

for (const [kind, drive, board] of [
  ['office document', false, false],
  ['drive document', true, false],
  ['board', false, true],
]) {
  test(`a guest sees a plain title for a ${kind} without rename controls`, () => {
    assertPlainTitle(module.exports.render(page(true, '', drive, board)));
  });
}

test('read-only access hides renaming even if a stale contract contains a rename URL', () => {
  assertPlainTitle(module.exports.render(page(true, '/office/1/rename/')));
});

test('a missing rename capability shows a plain title even without the read-only flag', () => {
  assertPlainTitle(module.exports.render(page(false, '')));
});

test('an owner keeps the rename button, title input and keyboard instructions', () => {
  const html = module.exports.render(page(false, '/office/1/rename/'));
  assert.match(
    html,
    /<button[^>]*aria-label="Zmień nazwę: Dokument zespołu"[^>]*>Dokument zespołu<\/button>/,
  );
  assert.match(html, /<input[^>]*aria-label="Nazwa pliku"/);
  assert.match(html, /Enter zapisuje nazwę, Escape anuluje/);
  assert.doesNotMatch(html, /office-suite-title-text/);
});
