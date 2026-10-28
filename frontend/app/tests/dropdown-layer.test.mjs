import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import vm from 'node:vm';

const source = await readFile(
  new URL('../../../static/js/dropdown-layer.js', import.meta.url),
  'utf8',
);

function events() {
  const listeners = new Map();
  return {
    addEventListener(type, callback) {
      if (!listeners.has(type)) listeners.set(type, new Set());
      listeners.get(type).add(callback);
    },
    removeEventListener(type, callback) {
      listeners.get(type)?.delete(callback);
    },
    fire(type, values = {}) {
      const event = {
        defaultPrevented: false,
        propagationStopped: false,
        preventDefault() {
          this.defaultPrevented = true;
        },
        stopImmediatePropagation() {
          this.propagationStopped = true;
        },
        ...values,
      };
      for (const callback of listeners.get(type) || []) {
        callback(event);
        if (event.propagationStopped) break;
      }
      return event;
    },
  };
}

function harness({ fixed = false, anchorLeft = 300, anchorTop = 200 } = {}) {
  const frames = new Map();
  let frameId = 0;
  const mutations = [];
  const resizes = [];
  let closed = 0;
  const document = { ...events(), activeElement: null };
  function element({ left = 0, top = 0, width = 30, height = 24, menu = false } = {}) {
    const attributes = new Map();
    const classes = new Set();
    const properties = new Map();
    const node = {
      ...events(),
      attributes,
      rect: { left, top, width, height },
      naturalWidth: 260,
      naturalHeight: 240,
      currentCSSZoom: 1,
      isConnected: true,
      hidden: false,
      shown: false,
      parentElement: null,
      visibility: 'visible',
      overflowX: 'visible',
      overflowY: 'visible',
      position: 'static',
      focusCount: 0,
      classList: {
        add: (name) => classes.add(name),
        remove: (name) => classes.delete(name),
        contains: (name) => classes.has(name),
      },
      style: {
        setProperty: (name, value) => properties.set(name, value),
        getPropertyValue: (name) => properties.get(name) || '',
        removeProperty: (name) => properties.delete(name),
      },
      setAttribute: (name, value) => attributes.set(name, value),
      getAttribute: (name) => attributes.get(name) ?? null,
      hasAttribute: (name) => attributes.has(name),
      removeAttribute: (name) => attributes.delete(name),
      querySelector: () => null,
      querySelectorAll: () => [],
      matches: (selector) => selector === ':popover-open' && node.shown,
      closest: (selector) =>
        selector === '[hidden], [inert], [aria-hidden="true"]' && node.hidden ? node : null,
      contains(other) {
        for (let current = other; current; current = current.parentElement)
          if (current === node) return true;
        return false;
      },
      showPopover() {
        node.shown = true;
      },
      hidePopover() {
        node.shown = false;
      },
      focus() {
        node.focusCount++;
        document.activeElement = node;
      },
      getBoundingClientRect() {
        if (!menu)
          return {
            ...node.rect,
            right: node.rect.left + node.rect.width,
            bottom: node.rect.top + node.rect.height,
          };
        const width = parseFloat(properties.get('--dropdown-layer-width')) || node.naturalWidth;
        const height = Math.min(
          node.naturalHeight,
          parseFloat(properties.get('--dropdown-layer-height')) || Infinity,
        );
        const left = parseFloat(properties.get('--dropdown-layer-left')) || 0;
        const top = parseFloat(properties.get('--dropdown-layer-top')) || 0;
        return { left, top, width, height, right: left + width, bottom: top + height };
      },
      getClientRects() {
        return node.isConnected && !node.hidden ? [node.getBoundingClientRect()] : [];
      },
      get offsetWidth() {
        return menu ? node.getBoundingClientRect().width : node.rect.width;
      },
      get offsetHeight() {
        return menu ? node.getBoundingClientRect().height : node.rect.height;
      },
      get clientHeight() {
        return node.offsetHeight;
      },
      get scrollHeight() {
        return menu ? node.naturalHeight : node.rect.height;
      },
    };
    return node;
  }
  document.body = element({ width: 1200, height: 800 });
  const anchor = element({ left: anchorLeft, top: anchorTop });
  anchor.parentElement = document.body;
  anchor.setAttribute('aria-expanded', 'true');
  const menu = element({ menu: true });
  menu.parentElement = document.body;
  menu.setAttribute('data-dropdown-search-disabled', '');
  if (fixed) menu.setAttribute('data-dropdown-positioning', 'fixed');
  const viewport = { ...events(), width: 1200, height: 800, offsetLeft: 0, offsetTop: 0 };
  const window = { ...events(), visualViewport: viewport };
  const observer = (collection) =>
    class {
      targets = [];
      disconnected = false;
      constructor(callback) {
        this.callback = callback;
        collection.push(this);
      }
      observe(target, options = {}) {
        this.targets.push({ target, options });
      }
      disconnect() {
        this.disconnected = true;
      }
    };
  vm.runInNewContext(source, {
    window,
    document,
    innerWidth: 1200,
    innerHeight: 800,
    MutationObserver: observer(mutations),
    ResizeObserver: observer(resizes),
    requestAnimationFrame(callback) {
      const id = ++frameId;
      frames.set(id, callback);
      return id;
    },
    cancelAnimationFrame: (id) => frames.delete(id),
    getComputedStyle: (node) => ({
      visibility: node.visibility,
      overflowX: node.overflowX,
      overflowY: node.overflowY,
      position: node.position,
      maxHeight: '500px',
      getPropertyValue: (name) =>
        ({ '--dropdown-menu-min-width': '240px', '--dropdown-menu-max-width': '360px' })[name] ||
        '',
    }),
  });
  const notify = (collection, target) => {
    for (const item of collection) {
      if (
        !item.disconnected &&
        item.targets.some(
          (entry) =>
            entry.target === target || (entry.options.subtree && entry.target.contains(target)),
        )
      )
        item.callback([]);
    }
  };
  return {
    window,
    document,
    anchor,
    menu,
    viewport,
    mutations,
    resizes,
    frames,
    layer: window.AncoreDropdownLayer,
    get closed() {
      return closed;
    },
    open() {
      window.AncoreDropdownLayer.open(menu, anchor, () => closed++);
    },
    mutate(target = menu) {
      notify(mutations, target);
    },
    resize(target = menu) {
      notify(resizes, target);
    },
    flush() {
      const pending = [...frames.values()];
      frames.clear();
      pending.forEach((callback) => callback());
    },
  };
}

function position(app) {
  const { left, top } = app.menu.getBoundingClientRect();
  return { left, top };
}

test('fixed positioning remains at its opening position after anchor moves, content mutations and resizing', () => {
  const app = harness({ fixed: true });
  app.open();
  const opened = position(app);
  assert.deepEqual(opened, { left: 300, top: 228 });
  app.anchor.rect.left = 750;
  app.anchor.rect.top = 400;
  app.mutate(app.anchor);
  app.flush();
  assert.deepEqual(position(app), opened);
  app.menu.naturalHeight = 340;
  app.mutate();
  app.resize();
  app.flush();
  assert.deepEqual(position(app), opened);
  assert.equal(app.menu.getBoundingClientRect().height, 340);
  app.anchor.rect.left = 450;
  app.anchor.rect.top = 500;
  app.resize(app.anchor);
  app.flush();
  assert.deepEqual(position(app), opened);
  assert.equal(app.menu.shown, true);
  assert.equal(app.closed, 0);
});

test('ordinary dropdowns continue tracking their trigger on mutations and resize', () => {
  const app = harness();
  app.open();
  assert.deepEqual(position(app), { left: 300, top: 228 });
  app.anchor.rect.left = 700;
  app.anchor.rect.top = 400;
  app.mutate(app.anchor);
  app.flush();
  assert.deepEqual(position(app), { left: 700, top: 428 });
  app.anchor.rect.left = 500;
  app.anchor.rect.top = 300;
  app.resize(app.anchor);
  app.flush();
  assert.deepEqual(position(app), { left: 500, top: 328 });
  assert.equal(app.closed, 0);
});

test('fixed configuration panels remain open when editing moves the trigger beyond its scroll container', () => {
  for (const fixed of [true, false]) {
    const app = harness({ fixed });
    app.document.body.overflowY = 'auto';
    app.document.body.rect.height = 500;
    app.open();
    const opened = position(app);
    app.anchor.rect.top = 900;
    app.mutate(app.anchor);
    app.flush();
    assert.equal(app.menu.shown, fixed);
    assert.equal(app.closed, fixed ? 0 : 1);
    if (fixed) assert.deepEqual(position(app), opened);
  }
});

test('a short viewport fits a fixed panel on the first frame without a later mutation jump', () => {
  const app = harness({ fixed: true, anchorTop: 150 });
  app.viewport.height = 300;
  app.menu.naturalHeight = 480;
  app.open();
  const opened = app.menu.getBoundingClientRect();
  assert.equal(opened.top, 8);
  assert.equal(opened.height, 284);
  app.mutate();
  app.resize();
  app.flush();
  assert.deepEqual(app.menu.getBoundingClientRect(), opened);
});

test('hiding and reopening a fixed dropdown resets its remembered opening position', () => {
  const app = harness({ fixed: true });
  app.open();
  const first = position(app);
  app.anchor.rect.left = 700;
  app.anchor.rect.top = 450;
  app.mutate(app.anchor);
  app.flush();
  assert.deepEqual(position(app), first);
  app.layer.hide(app.menu);
  app.open();
  assert.deepEqual(position(app), { left: 700, top: 478 });
  assert.equal(app.menu.shown, true);
  assert.equal(app.closed, 0);
});

test('fixed dropdowns clamp to resized visual viewport edges without following the moved trigger', () => {
  const app = harness({ fixed: true, anchorLeft: 900, anchorTop: 500 });
  app.open();
  assert.deepEqual(position(app), { left: 900, top: 528 });
  app.viewport.width = 640;
  app.viewport.height = 480;
  app.viewport.offsetLeft = 40;
  app.viewport.offsetTop = 60;
  app.viewport.fire('resize');
  app.flush();
  const clamped = app.menu.getBoundingClientRect();
  assert.ok(clamped.left >= 48 && clamped.top >= 68);
  assert.ok(clamped.right <= 672 && clamped.bottom <= 532);
  assert.ok(clamped.width > 0 && clamped.height > 0);
  app.anchor.rect.left = 80;
  app.anchor.rect.top = 80;
  app.window.fire('resize');
  app.flush();
  assert.deepEqual(position(app), { left: clamped.left, top: clamped.top });
  assert.equal(app.menu.shown, true);
  app.viewport.width = 1200;
  app.viewport.height = 800;
  app.viewport.offsetLeft = 0;
  app.viewport.offsetTop = 0;
  app.viewport.fire('resize');
  app.flush();
  assert.deepEqual(position(app), { left: 900, top: 528 });
});

test('Escape dismisses a fixed dropdown, restores focus and releases observers and position styles', () => {
  const app = harness({ fixed: true });
  app.open();
  app.mutate();
  assert.equal(app.frames.size, 1);
  const event = app.window.fire('keydown', { key: 'Escape' });
  assert.equal(event.defaultPrevented, true);
  assert.equal(event.propagationStopped, true);
  assert.equal(app.closed, 1);
  assert.equal(app.document.activeElement, app.anchor);
  assert.equal(app.anchor.focusCount, 1);
  assert.equal(app.menu.shown, false);
  assert.equal(app.menu.hasAttribute('popover'), false);
  assert.equal(app.menu.classList.contains('ancore-dropdown-layer'), false);
  assert.equal(app.frames.size, 0);
  for (const item of [...app.mutations, ...app.resizes]) assert.equal(item.disconnected, true);
  for (const property of ['width', 'height', 'left', 'top'])
    assert.equal(app.menu.style.getPropertyValue(`--dropdown-layer-${property}`), '');
  app.flush();
  app.window.fire('keydown', { key: 'Escape' });
  assert.equal(app.closed, 1);
});

test('fixed positioning still dismisses when the trigger is removed or the user clicks outside', () => {
  const removed = harness({ fixed: true });
  removed.open();
  removed.anchor.isConnected = false;
  removed.mutate();
  assert.equal(removed.menu.shown, false);
  assert.equal(removed.closed, 1);
  const outside = harness({ fixed: true });
  outside.open();
  outside.document.fire('pointerdown', { target: outside.menu });
  assert.equal(outside.closed, 0);
  outside.document.fire('pointerdown', { target: outside.anchor });
  assert.equal(outside.closed, 0);
  outside.document.fire('pointerdown', { target: outside.document.body });
  assert.equal(outside.closed, 1);
  assert.equal(outside.menu.shown, false);
});
