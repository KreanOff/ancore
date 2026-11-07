import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

const manager = await readFile(
  new URL('../../../static/js/task-modals.js', import.meta.url),
  'utf8',
);
const bundle = await build({
  entryPoints: [new URL('../src/shared/Modal.tsx', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  jsx: 'automatic',
  external: ['react', 'react/jsx-runtime', 'react-dom'],
  write: false,
});
const require = createRequire(import.meta.url);
const tick = () => new Promise((resolve) => setImmediate(resolve));
const actionsBundle = await build({
  entryPoints: [new URL('../src/shared/usePageActions.ts', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  external: ['react'],
  write: false,
});

// Exercise the real React effect together with the shared DOM modal manager.
function mount(props = {}) {
  class Element extends EventTarget {
    constructor() {
      super();
      this.classes = new Set();
      this.classList = {
        add: (name) => this.classes.add(name),
        remove: (name) => this.classes.delete(name),
        contains: (name) => this.classes.has(name),
      };
      this.attributes = {};
      this.children = [];
      this.isConnected = true;
      this.inert = false;
    }
    setAttribute(name, value) {
      this.attributes[name] = value;
    }
    closest() {
      return null;
    }
    focus() {
      if (!this.inert) document.activeElement = this;
    }
  }
  class CustomEvent extends Event {
    constructor(type, options) {
      super(type, options);
      this.detail = options?.detail;
    }
  }
  const document = new EventTarget();
  const window = new EventTarget();
  const body = new Element();
  const page = new Element();
  const host = new Element();
  const element = new Element();
  const control = new Element();
  const dialog = new Element();
  let finishAnimation;
  const finished = new Promise((resolve) => {
    finishAnimation = resolve;
  });
  dialog.getAnimations = () => (props.reducedMotion ? [] : [{ finished }]);
  document.body = body;
  document.activeElement = props.blurredTrigger ? body : page;
  document.getElementById = () => host;
  document.querySelector = (selector) => {
    if (selector === '.tasks-modal.is-open')
      return element.classList.contains('is-open') ? element : null;
    return selector.startsWith('[data-react-root=') ? page : null;
  };
  document.querySelectorAll = () => (element.classList.contains('is-open') ? [element] : []);
  body.children = [page, host];
  host.parentElement = body;
  host.children = [element];
  element.parentElement = host;
  element.querySelectorAll = () => [control];
  element.querySelector = (selector) => (selector.startsWith(':scope') ? dialog : null);
  element.contains = (node) => node === control;
  control.closest = (selector) => (selector === '.tasks-modal' ? element : null);
  control.matches = () => false;
  let confirmation;
  window.showConfirmModal = (options) => {
    confirmation = options;
  };
  const refs = [];
  const effects = [];
  let cursor = 0;
  let mounted = false;
  const module = { exports: {} };
  const context = {
    module,
    exports: module.exports,
    require: (name) => {
      if (name === 'react')
        return {
          ...require(name),
          useRef: (value) => (refs[cursor++] ||= { current: value }),
          useEffect: (effect) => {
            if (!mounted) effects.push(effect);
          },
        };
      if (name === 'react-dom') return { createPortal: (node) => node };
      return require(name);
    },
    window,
    document,
    HTMLElement: Element,
    CustomEvent,
    AbortController,
    setTimeout() {},
  };
  vm.runInNewContext(manager, context);
  vm.runInNewContext(bundle.outputFiles[0].text, context);
  let cleanup;
  let closed = 0;
  let options = {
    title: 'Okno',
    children: null,
    returnFocus: props.blurredTrigger ? page : undefined,
    onClose() {
      closed++;
      cleanup?.();
    },
    ...props,
  };
  function render(next = {}) {
    options = { ...options, ...next };
    cursor = 0;
    const tree = module.exports.Modal(options);
    element.classes = new Set(tree.props.className.split(/\s+/));
    tree.ref.current = element;
    if (!mounted) {
      cleanup = effects[0]();
      mounted = true;
    } else element.classList.add('is-open');
    return tree;
  }
  render();
  function navigate() {
    const event = new Event('ancore:before-navigate', { cancelable: true });
    document.dispatchEvent(event);
    return event;
  }
  function escape() {
    const event = new Event('keydown', { cancelable: true });
    Object.defineProperty(event, 'key', { value: 'Escape' });
    Object.defineProperty(event, 'target', { value: control });
    document.dispatchEvent(event);
    return event;
  }
  return {
    element,
    page,
    document,
    window,
    render,
    navigate,
    escape,
    finishAnimation,
    close: () => window.AncoreTaskModals.close(element),
    get confirmation() {
      return confirmation;
    },
    get closed() {
      return closed;
    },
  };
}

for (const size of ['panel', 'compact']) {
  test(`${size} closes once after its animation and then restores background and focus`, async () => {
    const modal = mount({ size });
    assert.equal(modal.element.classList.contains('app-modal-panel--compact'), size === 'compact');
    assert.equal(modal.page.inert, true);
    modal.close();
    modal.close();
    assert.equal(modal.closed, 0);
    assert.equal(modal.element.attributes['aria-hidden'], 'true');
    assert.equal(modal.page.inert, true);
    modal.finishAnimation();
    await tick();
    assert.equal(modal.closed, 1);
    assert.equal(modal.page.inert, false);
    assert.equal(modal.document.activeElement, modal.page);
  });
}

test('Escape preserves a dirty draft until discard is confirmed and animation ends', async () => {
  const modal = mount({ dirty: true });
  assert.equal(modal.escape().defaultPrevented, true);
  assert.equal(modal.element.classList.contains('is-open'), true);
  assert.equal(modal.closed, 0);
  assert.equal(modal.confirmation.title, 'Niezapisane zmiany');
  modal.confirmation.onConfirm();
  assert.equal(modal.closed, 0);
  modal.finishAnimation();
  await tick();
  assert.equal(modal.closed, 1);
});

test('pending saves block Escape, close, navigation and unload without discarding a draft', () => {
  const modal = mount({ pending: true, dirty: true });
  modal.escape();
  modal.close();
  assert.equal(modal.navigate().defaultPrevented, true);
  const unload = new Event('beforeunload', { cancelable: true });
  modal.window.dispatchEvent(unload);
  assert.equal(unload.defaultPrevented, true);
  assert.equal(modal.closed, 0);
  assert.equal(modal.confirmation, undefined);
  assert.equal(modal.element.classList.contains('is-open'), true);
});

test('navigation uses current dirty state and the same confirmed close lifecycle', async () => {
  const modal = mount();
  modal.render({ dirty: true });
  assert.equal(modal.navigate().defaultPrevented, true);
  assert.equal(modal.closed, 0);
  modal.confirmation.onConfirm();
  modal.finishAnimation();
  await tick();
  assert.equal(modal.closed, 1);
});

test('a completed save clears pending and dirty guards without a new confirmation', () => {
  const modal = mount({ pending: true, dirty: true, reducedMotion: true });
  modal.render({ pending: false, dirty: false });
  modal.close();
  assert.equal(modal.closed, 1);
  assert.equal(modal.confirmation, undefined);
});

test('reopening a closing panel cancels its stale completion callback', async () => {
  const modal = mount();
  modal.close();
  modal.window.AncoreTaskModals.open(modal.element);
  modal.finishAnimation();
  await tick();
  assert.equal(modal.closed, 0);
  assert.equal(modal.element.classList.contains('is-open'), true);
  assert.equal(modal.page.inert, true);
  modal.close();
  await tick();
  assert.equal(modal.closed, 1);
});

test('an asynchronously opened dialog restores its explicit trigger instead of body', async () => {
  const modal = mount({ blurredTrigger: true });
  assert.equal(modal.document.activeElement, modal.document.body);
  modal.close();
  modal.finishAnimation();
  await tick();
  assert.equal(modal.document.activeElement, modal.page);
});

test('page actions remember the opener before the loading state disables and blurs it', async () => {
  class Element {}
  const trigger = new Element();
  const document = { activeElement: trigger, body: new Element() };
  const hooks = [];
  let cursor = 0;
  let respond;
  const response = new Promise((resolve) => {
    respond = resolve;
  });
  const module = { exports: {} };
  vm.runInNewContext(actionsBundle.outputFiles[0].text, {
    module,
    exports: module.exports,
    require: (name) =>
      name === 'react'
        ? {
            useState(initial) {
              const index = cursor++;
              if (!(index in hooks)) hooks[index] = initial;
              return [
                hooks[index],
                (value) => {
                  hooks[index] = value;
                  if (index === 1 && value) document.activeElement = document.body;
                },
              ];
            },
            useRef: (initial) => (hooks[cursor++] ||= { current: initial }),
            useEffect() {},
          }
        : require(name),
    document,
    HTMLElement: Element,
    AbortController,
    AbortSignal,
    URL,
    location: { origin: 'http://localhost' },
    fetch: () => response,
  });
  const props = {
    initial: { api_url: '/api/v1/page/', url: '/teams/' },
    csrfToken: 'csrf',
  };
  const render = () => {
    cursor = 0;
    return module.exports.usePageActions(props);
  };
  const opening = render().open('/teams/create/');
  assert.equal(document.activeElement, document.body);
  respond({
    ok: true,
    headers: { get: () => 'application/json' },
    json: async () => ({ type: 'form', data: { title: 'Utwórz zespół' } }),
  });
  await opening;
  const actions = render();
  assert.equal(actions.modal.title, 'Utwórz zespół');
  assert.equal(actions.returnFocus, trigger);
  assert.equal(actions.busy, false);
});
