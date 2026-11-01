import assert from 'node:assert/strict';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

// Exercise the real camera hook. Control only React scheduling and browser event surfaces.
const bundle = await build({
  entryPoints: [new URL('../src/spaces/useWorkflowCamera.ts', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  external: ['react'],
  write: false,
});
const plain = (value) => JSON.parse(JSON.stringify(value));
const close = (actual, expected) => assert.ok(Math.abs(actual - expected) < 1e-8);
const samePoint = (actual, expected) => {
  close(actual.x, expected.x);
  close(actual.y, expected.y);
};

function harness({
  scale = 1,
  positions = [
    { x: -100, y: -40 },
    { x: 240, y: 160 },
  ],
} = {}) {
  const slots = [],
    effects = [],
    windowListeners = new Map(),
    elementListeners = new Map(),
    captures = new Set(),
    observers = [];
  let cursor = 0,
    cancelledNodes = 0;
  const nodes = Object.freeze(positions.map((position) => Object.freeze({ ...position })));
  const slot = (create) => {
    const index = cursor++;
    return (slots[index] ??= create());
  };
  const effect = (callback, dependencies) => {
    const value = slot(() => ({}));
    if (
      !value.dependencies ||
      dependencies.some((dependency, index) => !Object.is(dependency, value.dependencies[index]))
    ) {
      value.dependencies = dependencies;
      effects.push(() => {
        value.cleanup?.();
        value.cleanup = callback();
      });
    }
  };
  const react = {
    useState(initial) {
      const value = slot(() => ({ state: typeof initial === 'function' ? initial() : initial }));
      return [
        value.state,
        (next) => (value.state = typeof next === 'function' ? next(value.state) : next),
      ];
    },
    useRef: (initial) => slot(() => ({ current: initial })),
    useEffect: effect,
    useLayoutEffect: effect,
  };
  const viewport = {
    clientWidth: 900,
    clientHeight: 600,
    closest: () => null,
    focus() {},
    setPointerCapture: (id) => captures.add(id),
    getBoundingClientRect() {
      return {
        left: 100,
        top: 60,
        width: this.clientWidth * scale,
        height: this.clientHeight * scale,
      };
    },
    addEventListener: (name, callback) => elementListeners.set(name, callback),
    removeEventListener: (name, callback) => {
      if (elementListeners.get(name) === callback) elementListeners.delete(name);
    },
  };
  const node = { closest: (selector) => (selector.includes('button') ? node : null) };
  const input = { closest: (selector) => (selector.includes('input') ? input : null) };
  const module = { exports: {} };
  vm.runInNewContext(bundle.outputFiles[0].text, {
    module,
    exports: module.exports,
    require: (name) => {
      assert.equal(name, 'react');
      return react;
    },
    ResizeObserver: class {
      constructor(callback) {
        this.callback = callback;
        observers.push(this);
      }
      observe(element) {
        this.element = element;
      }
      disconnect() {
        this.disconnected = true;
      }
    },
    window: {
      addEventListener: (name, callback) => windowListeners.set(name, callback),
      removeEventListener: (name, callback) => {
        if (windowListeners.get(name) === callback) windowListeners.delete(name);
      },
    },
  });
  const ref = { current: viewport };
  const render = () => {
    cursor = 0;
    const value = module.exports.useWorkflowCamera(ref, nodes, () => cancelledNodes++);
    while (effects.length) effects.shift()();
    return value;
  };
  const event = ({ x = 100, y = 100, target = viewport, ...options } = {}) => ({
    clientX: 100 + x * scale,
    clientY: 60 + y * scale,
    pointerType: 'mouse',
    pointerId: 1,
    button: 0,
    detail: 1,
    currentTarget: viewport,
    target,
    defaultPrevented: false,
    propagationStopped: false,
    preventDefault() {
      this.defaultPrevented = true;
    },
    stopPropagation() {
      this.propagationStopped = true;
    },
    ...options,
  });
  const app = {
    nodes,
    node,
    input,
    viewport,
    captures,
    elementListeners,
    windowListeners,
    render,
    get cancelledNodes() {
      return cancelledNodes;
    },
    get camera() {
      return plain(render().camera);
    },
    dispatch(name, options) {
      const input = event(options);
      render().handlers[name](input);
      return input;
    },
    wheel(options = {}) {
      const input = event({ deltaY: 100, deltaMode: 0, ...options });
      elementListeners.get('wheel')(input);
      return input;
    },
    world(x, y) {
      return render().worldPoint(event({ x, y }));
    },
    resize(width, height) {
      viewport.clientWidth = width;
      viewport.clientHeight = height;
      observers.forEach((observer) => !observer.disconnected && observer.callback());
    },
    destroy() {
      slots.forEach((value) => value.cleanup?.());
      assert.ok(observers.every((observer) => observer.disconnected));
    },
  };
  render();
  app.resize(900, 600);
  return app;
}

test('background pan only changes the camera and consumes the drag click once', () => {
  const app = harness();
  const original = app.camera;
  const nodes = plain(app.nodes);
  const down = app.dispatch('onPointerDownCapture', { x: 100, y: 100 });
  assert.equal(down.defaultPrevented, true);
  assert.equal(down.propagationStopped, true);
  assert.equal(app.render().panning, true);
  assert.ok(app.captures.has(1));
  app.dispatch('onPointerMoveCapture', { x: 101, y: 100 });
  assert.deepEqual(app.camera, original);
  app.dispatch('onPointerMoveCapture', { x: 180, y: 60 });
  samePoint(app.camera, { x: original.x + 80, y: original.y - 40 });
  app.dispatch('onPointerUpCapture', { x: 180, y: 60 });
  assert.equal(app.render().panning, false);
  assert.equal(app.camera.zoom, original.zoom);
  assert.deepEqual(plain(app.nodes), nodes);
  assert.equal(app.dispatch('onClickCapture').defaultPrevented, true);
  assert.equal(app.dispatch('onClickCapture').defaultPrevented, false);
  app.destroy();
});

test('wheel zoom keeps its cursor anchor and panning stays accurate under the app CSS scale', () => {
  const app = harness({ scale: 0.98 });
  const anchor = app.world(217, 381);
  const beforeZoom = app.camera.zoom;
  const wheel = app.wheel({ x: 217, y: 381, deltaY: -120 });
  assert.equal(wheel.defaultPrevented, true);
  assert.ok(app.camera.zoom > beforeZoom);
  samePoint(app.world(217, 381), anchor);
  const beforePan = app.camera;
  app.dispatch('onPointerDownCapture', { x: 120, y: 150 });
  app.dispatch('onPointerMoveCapture', { x: 185, y: 110 });
  samePoint(app.camera, { x: beforePan.x + 65, y: beforePan.y - 40 });
  app.dispatch('onPointerUpCapture');
  app.destroy();
});

test('wheel direction remains correct after fitting a map below the manual zoom limit', () => {
  const app = harness({
    scale: 0.98,
    positions: [
      { x: -100000, y: -90000 },
      { x: 100000, y: 90000 },
    ],
  });
  app.render().fit();
  const fitted = app.camera;
  assert.ok(fitted.zoom < 0.01);
  const anchor = app.world(217, 381);
  app.wheel({ x: 217, y: 381, deltaY: 120 });
  assert.deepEqual(app.camera, fitted);
  app.wheel({ x: 217, y: 381, deltaY: -120 });
  assert.ok(app.camera.zoom > fitted.zoom && app.camera.zoom < 0.01);
  samePoint(app.world(217, 381), anchor);
  app.destroy();
});

test('Escape cancels the current pan and a later gesture starts from the restored camera', () => {
  const app = harness();
  const original = app.camera;
  app.dispatch('onPointerDownCapture', { x: 100, y: 100 });
  app.dispatch('onPointerMoveCapture', { x: 230, y: 180 });
  assert.notDeepEqual(app.camera, original);
  app.dispatch('onKeyDownCapture', { key: 'Escape' });
  assert.deepEqual(app.camera, original);
  assert.equal(app.render().panning, false);
  app.dispatch('onPointerMoveCapture', { x: 600, y: 400 });
  assert.deepEqual(app.camera, original);
  app.dispatch('onPointerDownCapture', { x: 20, y: 20, pointerId: 2 });
  app.dispatch('onPointerMoveCapture', { x: 50, y: 60, pointerId: 2 });
  samePoint(app.camera, { x: original.x + 30, y: original.y + 40 });
  app.dispatch('onPointerUpCapture', { pointerId: 2 });
  app.destroy();
});

test('Space allows camera panning over a node while ordinary node interaction remains available', () => {
  const app = harness();
  const original = app.camera;
  const normal = app.dispatch('onPointerDownCapture', { target: app.node });
  assert.equal(normal.defaultPrevented, false);
  assert.equal(normal.propagationStopped, false);
  assert.equal(app.render().panning, false);
  assert.equal(app.cancelledNodes, 0);
  const space = app.dispatch('onKeyDownCapture', { key: ' ', code: 'Space', target: app.node });
  assert.equal(space.defaultPrevented, true);
  assert.equal(app.render().hand, true);
  const down = app.dispatch('onPointerDownCapture', { target: app.node, x: 100, y: 100 });
  assert.equal(down.propagationStopped, true);
  assert.equal(app.cancelledNodes, 1);
  app.dispatch('onPointerMoveCapture', { target: app.node, x: 145, y: 125 });
  samePoint(app.camera, { x: original.x + 45, y: original.y + 25 });
  app.dispatch('onPointerUpCapture', { target: app.node });
  app.windowListeners.get('keyup')({ code: 'Space' });
  assert.equal(app.render().hand, false);
  const typing = app.dispatch('onKeyDownCapture', { key: ' ', code: 'Space', target: app.input });
  assert.equal(typing.defaultPrevented, false);
  assert.equal(app.render().hand, false);
  app.destroy();
});

test('a second touch cancels node dragging and pinch preserves its moving midpoint anchor', () => {
  const app = harness({ scale: 0.98 });
  const original = app.camera;
  const anchor = app.world(150, 100);
  app.dispatch('onPointerDownCapture', {
    pointerType: 'touch',
    pointerId: 1,
    target: app.node,
    x: 100,
    y: 100,
  });
  assert.equal(app.cancelledNodes, 0);
  app.dispatch('onPointerDownCapture', {
    pointerType: 'touch',
    pointerId: 2,
    target: app.node,
    x: 200,
    y: 100,
  });
  assert.equal(app.cancelledNodes, 1);
  assert.equal(app.render().panning, true);
  app.dispatch('onPointerMoveCapture', {
    pointerType: 'touch',
    pointerId: 2,
    target: app.node,
    x: 260,
    y: 100,
  });
  close(app.camera.zoom, original.zoom * 1.6);
  samePoint(app.world(180, 100), anchor);
  app.dispatch('onPointerUpCapture', { pointerType: 'touch', pointerId: 2 });
  const afterPinch = app.camera;
  app.dispatch('onPointerMoveCapture', { pointerType: 'touch', pointerId: 1, x: 120, y: 130 });
  samePoint(app.camera, { x: afterPinch.x + 20, y: afterPinch.y + 30 });
  app.dispatch('onPointerUpCapture', { pointerType: 'touch', pointerId: 1 });
  assert.equal(app.render().panning, false);
  assert.equal(app.dispatch('onClickCapture').defaultPrevented, true);
  app.destroy();
});

test('pointer cancellation and lost capture restore the camera and clear gesture state', () => {
  for (const interruption of ['onPointerCancelCapture', 'onLostPointerCapture']) {
    const app = harness();
    const original = app.camera;
    app.dispatch('onPointerDownCapture', { x: 100, y: 100 });
    app.dispatch('onPointerMoveCapture', { x: 190, y: 70 });
    app.dispatch(interruption);
    assert.deepEqual(app.camera, original);
    assert.equal(app.render().panning, false);
    app.dispatch('onPointerMoveCapture', { x: 500, y: 300 });
    assert.deepEqual(app.camera, original);
    app.dispatch('onPointerDownCapture', { pointerId: 3, x: 40, y: 40 });
    app.dispatch('onPointerMoveCapture', { pointerId: 3, x: 60, y: 80 });
    samePoint(app.camera, { x: original.x + 20, y: original.y + 40 });
    app.dispatch('onPointerUpCapture', { pointerId: 3 });
    app.destroy();
  }
});

test('wheel events during a gesture cannot scroll the page or change the camera', () => {
  const app = harness();
  app.dispatch('onPointerDownCapture');
  app.dispatch('onPointerMoveCapture', { x: 150, y: 100 });
  const before = app.camera;
  for (const shiftKey of [false, true]) {
    const wheel = app.wheel({ deltaY: 120, shiftKey });
    assert.equal(wheel.defaultPrevented, true);
    assert.deepEqual(app.camera, before);
  }
  app.dispatch('onPointerUpCapture');
  app.destroy();
});

test('viewport resize preserves its world center and blur releases Space and an active gesture', () => {
  const app = harness();
  app.dispatch('onKeyDownCapture', { key: 'ArrowRight' });
  const center = app.render().centerWorld();
  app.resize(620, 480);
  samePoint(app.render().centerWorld(), center);
  const original = app.camera;
  app.dispatch('onKeyDownCapture', { key: ' ', code: 'Space' });
  app.dispatch('onPointerDownCapture');
  app.dispatch('onPointerMoveCapture', { x: 200, y: 130 });
  app.windowListeners.get('blur')();
  assert.deepEqual(app.camera, original);
  assert.equal(app.render().hand, false);
  assert.equal(app.render().panning, false);
  app.destroy();
  assert.equal(app.elementListeners.size, 0);
  assert.equal(app.windowListeners.size, 0);
});

test('keyboard reveal keeps visible cards still and brings offscreen cards into view', () => {
  const app = harness();
  const before = app.camera;
  app.render().reveal(app.nodes[0]);
  assert.deepEqual(app.camera, before);
  const offscreen = { x: -8000, y: 5000 };
  app.render().reveal(offscreen);
  samePoint(app.render().centerWorld(), { x: offscreen.x + 110, y: offscreen.y + 44 });
  assert.equal(app.camera.zoom, before.zoom);
  assert.equal(app.cancelledNodes, 0);
  app.dispatch('onPointerDownCapture');
  const duringPan = app.camera;
  app.render().reveal(app.nodes[0]);
  assert.deepEqual(app.camera, duringPan);
  app.destroy();
});

test('minimap navigation centers exact world points at the current zoom and tracks viewport size', () => {
  const app = harness({ scale: 0.98 });
  const nodes = plain(app.nodes);
  app.render().zoomTo(0.12);
  app.render().panTo({ x: -2400, y: 1800 });
  samePoint(app.render().centerWorld(), { x: -2400, y: 1800 });
  assert.equal(app.camera.zoom, 0.12);
  assert.deepEqual(plain(app.render().viewportSize), { width: 900, height: 600 });
  app.resize(390, 640);
  samePoint(app.render().centerWorld(), { x: -2400, y: 1800 });
  assert.deepEqual(plain(app.render().viewportSize), { width: 390, height: 640 });
  assert.deepEqual(plain(app.nodes), nodes);
  app.destroy();
});
