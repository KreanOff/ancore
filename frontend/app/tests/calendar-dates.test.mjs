import assert from 'node:assert/strict';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

// Exercise local calendar days, including the clock changes used by the app.
process.env.TZ = 'Europe/Warsaw';
const bundle = await build({
  entryPoints: [new URL('../src/calendar/dates.ts', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  write: false,
});
const module = { exports: {} };
vm.runInNewContext(bundle.outputFiles[0].text, {
  module,
  exports: module.exports,
  Date,
});
const { occurs, lanes, bounds } = module.exports;
const at = (value) => new Date(value);
const event = (start, end, extra = {}) => ({
  id: 1,
  title: 'Wydarzenie',
  description: '',
  start,
  end,
  all_day: false,
  color: 'blue',
  source: 'events',
  ...extra,
});

test('a timed event ending at midnight only occupies the preceding day', () => {
  const item = event('2026-10-23T22:00:00+02:00', '2026-10-24T00:00:00+02:00');
  const previous = at('2026-10-23T12:00:00+02:00');
  const next = at('2026-10-24T12:00:00+02:00');
  assert.equal(occurs(item, previous), true);
  assert.equal(occurs(item, next), false);
  assert.equal(lanes([item], previous)[0].end, 1440);
  assert.equal(lanes([item], next).length, 0);
});

test('point deadlines belong to their own day, including exactly midnight', () => {
  for (const time of ['00:00:00', '12:30:00']) {
    const timestamp = `2026-10-24T${time}+02:00`;
    const item = event(timestamp, timestamp, { source: 'tasks' });
    assert.equal(occurs(item, at('2026-10-23T12:00:00+02:00')), false);
    assert.equal(occurs(item, at('2026-10-24T12:00:00+02:00')), true);
    assert.equal(occurs(item, at('2026-10-25T12:00:00+01:00')), false);
    assert.equal(lanes([item], at('2026-10-24T12:00:00+02:00')).length, 1);
  }
});

test('all-day events retain every covered day and stay outside timed lanes', () => {
  const item = event('2026-10-23T00:00:00+02:00', '2026-10-24T23:59:59+02:00', {
    all_day: true,
  });
  assert.equal(occurs(item, at('2026-10-22T12:00:00+02:00')), false);
  for (const day of ['23', '24']) {
    const date = at(`2026-10-${day}T12:00:00+02:00`);
    assert.equal(occurs(item, date), true);
    assert.equal(lanes([item], date).length, 0);
  }
  assert.equal(occurs(item, at('2026-10-25T12:00:00+01:00')), false);
});

test('an event ending at midnight does not create a false overlap on the next day', () => {
  const items = [
    event('2026-10-23T22:00:00+02:00', '2026-10-24T00:00:00+02:00'),
    event('2026-10-24T00:00:00+02:00', '2026-10-24T01:00:00+02:00', { id: 2 }),
    event('2026-10-24T00:30:00+02:00', '2026-10-24T01:30:00+02:00', { id: 3 }),
  ];
  const positioned = lanes(items, at('2026-10-24T12:00:00+02:00'));
  assert.equal(positioned.length, 2);
  assert.equal(positioned[0].event.id, 2);
  assert.equal(positioned[0].lane, 0);
  assert.equal(positioned[1].event.id, 3);
  assert.equal(positioned[1].lane, 1);
  assert.ok(positioned.every((item) => item.count === 2));
});

test('midnight boundaries follow the local day across both daylight-saving changes', () => {
  for (const [start, end, hours, nextDay] of [
    ['2026-03-29T00:00:00+01:00', '2026-03-30T00:00:00+02:00', 23, '2026-03-30T12:00:00+02:00'],
    ['2026-10-25T00:00:00+02:00', '2026-10-26T00:00:00+01:00', 25, '2026-10-26T12:00:00+01:00'],
  ]) {
    const item = event(start, end);
    const date = at(start);
    const range = bounds(date, 'day');
    assert.equal((range.end - range.start) / 3600000, hours);
    assert.equal(occurs(item, date), true);
    assert.equal(occurs(item, at(nextDay)), false);
    assert.equal(lanes([item], date)[0].end, 1440);
    assert.equal(lanes([item], at(nextDay)).length, 0);
  }
});
