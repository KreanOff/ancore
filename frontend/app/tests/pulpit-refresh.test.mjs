import assert from 'node:assert/strict';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

const bundle = await build({
  entryPoints: [new URL('../src/pulpits/autoRefresh.ts', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  write: false,
});

function clock() {
  const document = new EventTarget();
  document.visibilityState = 'visible';
  let now = 0;
  let nextId = 0;
  const timers = new Map();
  const sandbox = {
    exports: {},
    document,
    setTimeout: (callback, delay) => {
      const id = ++nextId;
      timers.set(id, { callback, at: now + delay });
      return id;
    },
    clearTimeout: (id) => timers.delete(id),
  };
  sandbox.module = { exports: sandbox.exports };
  vm.runInNewContext(bundle.outputFiles[0].text, sandbox);
  return {
    start: sandbox.module.exports.startAutoRefresh,
    timers,
    visibility(value) {
      document.visibilityState = value;
      document.dispatchEvent(new Event('visibilitychange'));
    },
    async advance(ms) {
      now += ms;
      for (const [id, timer] of [...timers])
        if (timer.at <= now) {
          timers.delete(id);
          await timer.callback();
        }
    },
  };
}

test('refresh waits for the chosen interval, repeats, and stops on disposal', async () => {
  const timer = clock();
  let calls = 0;
  const stop = timer.start(60, async () => calls++);
  await timer.advance(59999);
  assert.equal(calls, 0);
  await timer.advance(1);
  assert.equal(calls, 1);
  await timer.advance(60000);
  assert.equal(calls, 2);
  stop();
  await timer.advance(60000);
  assert.equal(calls, 2);
  assert.equal(timer.timers.size, 0);
});

test('hidden tabs stop scheduling and visibility resumes without duplicate timers', async () => {
  const timer = clock();
  let calls = 0;
  const stop = timer.start(300, async () => calls++);
  timer.visibility('hidden');
  assert.equal(timer.timers.size, 0);
  await timer.advance(900000);
  assert.equal(calls, 0);
  timer.visibility('visible');
  timer.visibility('visible');
  assert.equal(timer.timers.size, 1);
  await timer.advance(300000);
  assert.equal(calls, 1);
  stop();
  timer.visibility('visible');
  assert.equal(timer.timers.size, 0);
});

test('off and unsupported intervals do not schedule requests', () => {
  for (const interval of [0, -1, 1, 100, NaN]) {
    const timer = clock();
    timer.start(interval, async () => assert.fail());
    assert.equal(timer.timers.size, 0);
  }
});

test('in-flight requests never overlap and disposal prevents rescheduling after completion', async () => {
  const timer = clock();
  let complete;
  let calls = 0;
  const stop = timer.start(60, () => {
    calls++;
    return new Promise((resolve) => {
      complete = resolve;
    });
  });
  const pending = timer.advance(60000);
  assert.equal(calls, 1);
  timer.visibility('visible');
  assert.equal(timer.timers.size, 0);
  await timer.advance(300000);
  assert.equal(calls, 1);
  stop();
  complete();
  await pending;
  assert.equal(timer.timers.size, 0);
});

test('failed requests preserve the next scheduled attempt', async () => {
  const timer = clock();
  let calls = 0;
  const stop = timer.start(900, async () => {
    if (++calls === 1) throw new Error('offline');
  });
  await timer.advance(900000);
  await timer.advance(900000);
  assert.equal(calls, 2);
  stop();
});
