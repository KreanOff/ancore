import assert from 'node:assert/strict';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

const bundle = await build({
  entryPoints: [new URL('../src/spaces/timeline.ts', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  write: false,
});
const module = { exports: {} };
vm.runInNewContext(bundle.outputFiles[0].text, { module, exports: module.exports, Date, Intl });
const {
  MIN_DAY,
  MAX_DAY,
  parseDay,
  dayKey,
  dayLabel,
  timelineWindow,
  timelineHeaders,
  shiftAnchor,
  taskGeometry,
  shiftTask,
  fitTimeline,
  fittedTimelineWindow,
} = module.exports;
const plain = (value) => JSON.parse(JSON.stringify(value));
const range = (start, end = start) => ({ start: parseDay(start), end: parseDay(end) });

test('strict date parsing rejects impossible dates and timestamps without silently rolling over', () => {
  for (const value of [
    null,
    undefined,
    '',
    '2026-2-01',
    '2026-02-30',
    '2026-02-29',
    '2024-13-01',
    '0000-01-01',
    '2026-10-28T00:00:00Z',
  ])
    assert.equal(parseDay(value), null, String(value));
  for (const value of ['0001-01-01', '0099-12-31', '2024-02-29', '9999-12-31'])
    assert.equal(dayKey(parseDay(value)), value);
  assert.equal(dayKey(MIN_DAY), '0001-01-01');
  assert.equal(dayKey(MAX_DAY), '9999-12-31');
  for (const value of [NaN, Infinity, 1.1, MIN_DAY - 1, MAX_DAY + 1])
    assert.throws(() => dayKey(value), /zakresem/);
});

test('calendar day arithmetic is stable through DST, leap days and year boundaries in every timezone', () => {
  const previousZone = process.env.TZ;
  try {
    for (const zone of ['UTC', 'Europe/Warsaw', 'America/New_York', 'Pacific/Kiritimati']) {
      process.env.TZ = zone;
      for (const [first, next] of [
        ['2024-02-28', '2024-02-29'],
        ['2024-02-29', '2024-03-01'],
        ['2026-03-29', '2026-03-30'],
        ['2026-10-25', '2026-10-26'],
        ['2026-12-31', '2027-01-01'],
      ]) {
        assert.equal(parseDay(next) - parseDay(first), 1, `${zone}: ${first}`);
        assert.equal(dayKey(parseDay(first) + 1), next);
      }
      assert.equal(dayLabel(parseDay('2026-10-25')), '25.10.2026');
    }
  } finally {
    if (previousZone === undefined) delete process.env.TZ;
    else process.env.TZ = previousZone;
  }
});

test('bounded calendar windows align to Monday, month and quarter independently of task dates', () => {
  const anchor = parseDay('2026-10-28');
  const expected = [
    ['weeks', '2026-10-12', '2027-01-04', 36],
    ['months', '2026-09-01', '2027-05-01', 12],
    ['quarters', '2026-07-01', '2028-07-01', 4],
  ];
  for (const [scale, first, end, dayWidth] of expected) {
    const window = timelineWindow(scale, anchor);
    assert.equal(dayKey(window.start), first);
    assert.equal(dayKey(window.end), end);
    assert.equal(window.days, parseDay(end) - parseDay(first));
    assert.equal(window.dayWidth, dayWidth);
    assert.equal(window.width, window.days * dayWidth);
    assert.ok(window.start <= anchor && anchor < window.end);
  }
  assert.equal(timelineWindow('weeks', anchor).days, 84);
  for (const scale of ['weeks', 'months', 'quarters']) {
    const earliest = timelineWindow(scale, MIN_DAY);
    const latest = timelineWindow(scale, MAX_DAY);
    assert.equal(earliest.start, MIN_DAY);
    assert.equal(latest.end, MAX_DAY + 1);
    assert.ok(earliest.days > 0 && latest.days > 0);
  }
});

test('every header row fully covers the same range with no gaps, overlaps or drift', () => {
  for (const value of ['0001-01-01', '2024-02-29', '2026-12-31', '9999-12-31']) {
    for (const scale of ['weeks', 'months', 'quarters']) {
      const window = timelineWindow(scale, parseDay(value));
      const headers = timelineHeaders(window);
      for (const row of [headers.major, headers.minor]) {
        assert.ok(row.length > 0);
        let cursor = window.start;
        let width = 0;
        for (const cell of row) {
          assert.equal(cell.start, cursor);
          assert.ok(cell.end > cell.start);
          assert.equal(cell.left, width);
          assert.equal(cell.width, (cell.end - cell.start) * window.dayWidth);
          assert.ok(cell.label && cell.title);
          cursor = cell.end;
          width += cell.width;
        }
        assert.equal(cursor, window.end);
        assert.equal(width, window.width);
      }
    }
  }
  const headers = timelineHeaders(timelineWindow('weeks', parseDay('2026-10-28')));
  assert.equal(headers.major[0].label, 'październik 2026');
  assert.equal(headers.minor.filter((cell) => cell.weekend).length, 24);
  assert.equal(headers.minor[0].label, '12');
  assert.equal(headers.minor[0].title, '12.10.2026');
});

test('leading headers cover the metadata width and remain continuous through the calendar origin', () => {
  for (const scale of ['weeks', 'months', 'quarters']) {
    const window = Object.freeze(timelineWindow(scale, parseDay('2027-02-01')));
    for (const leadingWidth of [190, 430, 560]) {
      const headers = timelineHeaders(window, leadingWidth);
      for (const row of [headers.major, headers.minor]) {
        assert.ok(row[0].left <= -leadingWidth);
        assert.ok(row[0].left > -leadingWidth - window.dayWidth);
        assert.equal(row[0].start, window.start + row[0].left / window.dayWidth);
        let cursor = row[0].start;
        let left = row[0].left;
        for (const cell of row) {
          assert.equal(cell.start, cursor);
          assert.equal(cell.left, left);
          assert.ok(cell.end > cell.start);
          assert.equal(cell.width, (cell.end - cell.start) * window.dayWidth);
          cursor = cell.end;
          left += cell.width;
        }
        assert.equal(cursor, window.end);
        assert.equal(left, window.width);
        const origin = row.find((cell) => cell.start <= window.start && cell.end > window.start);
        assert.ok(origin);
        assert.equal(origin.left + (window.start - origin.start) * window.dayWidth, 0);
      }
    }
  }
});

test('leading dates preserve header units and alignment with task bars at every scale', () => {
  for (const scale of ['weeks', 'months', 'quarters']) {
    const window = timelineWindow(scale, parseDay('2027-02-01'));
    const original = timelineHeaders(window);
    for (const leadingWidth of [190, 430, 560]) {
      const extended = timelineHeaders(window, leadingWidth);
      for (const name of ['major', 'minor'])
        assert.deepEqual(
          plain(extended[name].filter((cell) => cell.start > window.start)),
          plain(original[name].filter((cell) => cell.start > window.start)),
        );
      if (scale === 'weeks') {
        assert.ok(extended.minor.every((cell) => cell.end - cell.start === 1));
        assert.equal(extended.minor.find((cell) => cell.start === window.start).left, 0);
      }
      for (const day of [window.start, window.start + 15, window.end - 1]) {
        const bar = taskGeometry({ start: day, end: day }, window);
        const cell = extended.minor.find((segment) => segment.start <= day && segment.end > day);
        assert.equal(cell.left + (day - cell.start) * window.dayWidth, bar.left);
        assert.equal(bar.width, window.dayWidth);
      }
    }
    for (const width of [0, -1, -560])
      assert.deepEqual(plain(timelineHeaders(window, width)), plain(original));
  }
});

test('leading headers clamp to the first supported day without moving the calendar origin', () => {
  for (const [scale, nearStart] of [
    ['weeks', '0001-01-22'],
    ['months', '0001-03-01'],
    ['quarters', '0001-07-01'],
  ]) {
    const earliest = timelineWindow(scale, MIN_DAY);
    const window = timelineWindow(scale, parseDay(nearStart));
    for (const leadingWidth of [190, 430, 560]) {
      assert.deepEqual(
        plain(timelineHeaders(earliest, leadingWidth)),
        plain(timelineHeaders(earliest)),
      );
      const headers = timelineHeaders(window, leadingWidth);
      for (const row of [headers.major, headers.minor]) {
        assert.ok(row[0].start >= MIN_DAY);
        assert.equal(row[0].left, (row[0].start - window.start) * window.dayWidth);
        if (leadingWidth === 560) {
          assert.equal(row[0].start, MIN_DAY);
          assert.ok(row[0].left > -leadingWidth);
        }
        const last = row[row.length - 1];
        assert.equal(last.end, window.end);
        assert.equal(last.left + last.width, window.width);
      }
    }
  }
});

test('calendar navigation preserves day where possible and clamps short months and supported years', () => {
  assert.equal(dayKey(shiftAnchor(parseDay('2026-10-28'), 'weeks', 1)), '2026-11-25');
  assert.equal(dayKey(shiftAnchor(parseDay('2026-10-28'), 'weeks', -1)), '2026-09-30');
  assert.equal(dayKey(shiftAnchor(parseDay('2026-11-30'), 'months', 1)), '2027-02-28');
  assert.equal(dayKey(shiftAnchor(parseDay('2024-02-29'), 'quarters', 1)), '2025-02-28');
  for (const scale of ['weeks', 'months', 'quarters']) {
    assert.equal(shiftAnchor(MIN_DAY, scale, -1), MIN_DAY);
    assert.equal(shiftAnchor(MAX_DAY, scale, 1), MAX_DAY);
  }
});

test('bar geometry includes the due date and clips only at visible calendar boundaries', () => {
  const window = timelineWindow('weeks', parseDay('2026-10-28'));
  assert.deepEqual(plain(taskGeometry(range('2026-10-12'), window)), {
    left: 0,
    width: 36,
    clippedStart: false,
    clippedEnd: false,
  });
  assert.equal(taskGeometry(range('2026-10-25', '2026-10-29'), window).width, 180);
  assert.deepEqual(plain(taskGeometry(range('2026-10-01', '2027-02-01'), window)), {
    left: 0,
    width: window.width,
    clippedStart: true,
    clippedEnd: true,
  });
  const last = taskGeometry({ start: window.end - 1, end: window.end - 1 }, window);
  assert.equal(last.left + last.width, window.width);
  assert.equal(last.clippedEnd, false);
  assert.equal(taskGeometry({ start: window.end, end: window.end }, window), null);
  assert.equal(taskGeometry({ start: window.start - 2, end: window.start - 1 }, window), null);
  assert.equal(taskGeometry(range('2026-10-29', '2026-10-25'), window), null);
});

test('dragging preserves inclusive duration and resizing cannot invert dates or cross allowed bounds', () => {
  const source = Object.freeze(range('2026-10-24', '2026-10-27'));
  assert.deepEqual(plain(shiftTask(source, 2, 'move')), range('2026-10-26', '2026-10-29'));
  assert.deepEqual(plain(shiftTask(source, 20, 'start')), range('2026-10-27'));
  assert.deepEqual(plain(shiftTask(source, -20, 'end')), range('2026-10-24'));
  const bounds = range('2026-10-01', '2026-10-31');
  assert.deepEqual(
    plain(shiftTask(source, 100, 'move', bounds)),
    range('2026-10-28', '2026-10-31'),
  );
  assert.deepEqual(
    plain(shiftTask(source, -100, 'move', bounds)),
    range('2026-10-01', '2026-10-04'),
  );
  assert.deepEqual(plain(shiftTask(source, NaN, 'move')), source);
  assert.equal(shiftTask({ start: MIN_DAY, end: MIN_DAY + 3 }, -1, 'move').start, MIN_DAY);
  assert.equal(shiftTask({ start: MAX_DAY - 3, end: MAX_DAY }, 1, 'move').end, MAX_DAY);
});

test('fit chooses a scale that contains tasks and respects viewport width when supplied', () => {
  const fallback = parseDay('2026-10-28');
  assert.deepEqual(plain(fitTimeline([], fallback)), { scale: 'weeks', anchor: fallback });
  for (const [items, expectedScale, width] of [
    [[range('2026-10-10', '2026-11-09')], 'weeks', undefined],
    [[range('2026-10-10', '2026-11-09')], 'months', 700],
    [[range('2026-10-10', '2027-04-01')], 'months', undefined],
    [[range('2026-10-10', '2027-04-01')], 'quarters', 900],
    [[range('2026-10-10', '2027-10-01')], 'quarters', undefined],
  ]) {
    const result = fitTimeline(items, fallback, width);
    assert.equal(result.scale, expectedScale);
    const window = timelineWindow(result.scale, result.anchor);
    assert.ok(window.start <= items[0].start);
    assert.ok(window.end > items[0].end);
    if (width) assert.ok((items[0].end - items[0].start + 1) * window.dayWidth <= width);
  }
});

test('fitting a four-year plan includes both endpoints, visible gutters and the entire duration', () => {
  const items = [range('2024-01-01', '2025-03-20'), range('2027-09-05', '2027-12-31')];
  const window = fittedTimelineWindow(items, parseDay('2026-10-28'), 700);
  assert.equal(window.scale, 'quarters');
  assert.ok(window.dayWidth < 4);
  assert.ok(window.width <= 700);
  assert.equal(window.end - window.start, window.days);
  assert.ok((items[0].start - window.start) / window.days >= 0.03);
  assert.ok((window.end - 1 - items[1].end) / window.days >= 0.03);
  for (const item of items) {
    const geometry = taskGeometry(item, window);
    assert.equal(geometry.clippedStart, false);
    assert.equal(geometry.clippedEnd, false);
    assert.ok(geometry.left > 0);
    assert.ok(geometry.left + geometry.width < window.width);
    assert.ok(Math.abs(geometry.width - (item.end - item.start + 1) * window.dayWidth) < 0.00001);
  }
  const headers = timelineHeaders(window);
  assert.ok(headers.major.length + headers.minor.length < 100);
  assert.ok(headers.minor.some((segment) => segment.label === '2024'));
  assert.ok(headers.minor.some((segment) => segment.label === '2027'));
});

test('fitted headers and bars remain bounded and aligned even across years 0001–9999', () => {
  for (const availableWidth of [1, 150, 700, 12000]) {
    const window = fittedTimelineWindow(
      [{ start: MIN_DAY, end: MAX_DAY }],
      MIN_DAY,
      availableWidth,
    );
    assert.equal(window.start, MIN_DAY);
    assert.equal(window.end, MAX_DAY + 1);
    assert.ok(Number.isFinite(window.dayWidth) && window.dayWidth > 0);
    assert.ok(window.width <= availableWidth);
    const geometry = taskGeometry({ start: MIN_DAY, end: MAX_DAY }, window);
    assert.equal(geometry.left, 0);
    assert.ok(Math.abs(geometry.width - availableWidth) < 0.00001);
    assert.equal(geometry.clippedStart, false);
    assert.equal(geometry.clippedEnd, false);
    const headers = timelineHeaders(window);
    assert.ok(headers.major.length + headers.minor.length < 100);
    for (const row of [headers.major, headers.minor]) {
      let day = window.start;
      let x = 0;
      for (const segment of row) {
        assert.equal(segment.start, day);
        assert.ok(segment.end > segment.start);
        assert.ok(segment.width > 0);
        assert.ok(Math.abs(segment.left - x) < 0.00001);
        assert.ok(segment.label && segment.title);
        day = segment.end;
        x += segment.width;
      }
      assert.equal(day, window.end);
      assert.ok(Math.abs(x - window.width) < 0.00001);
    }
  }
});

test('short fitted plans keep normal day widths, and adapting headers never allocates daily years', () => {
  const fallback = parseDay('2026-10-28');
  const oneDay = fittedTimelineWindow([range('2026-10-28')], fallback, 700);
  assert.equal(oneDay.scale, 'weeks');
  assert.equal(oneDay.dayWidth, 36);
  assert.equal(oneDay.width, 108);
  assert.equal(dayKey(oneDay.start), '2026-10-27');
  assert.equal(dayKey(oneDay.end), '2026-10-30');
  assert.deepEqual(
    plain(fittedTimelineWindow([], fallback, 700)),
    plain(timelineWindow('weeks', fallback)),
  );
  for (const duration of [80, 100, 400, 1000, 4000, 8000, MAX_DAY - MIN_DAY]) {
    for (const width of [150, 700, duration * 36 + 100000]) {
      const window = fittedTimelineWindow(
        [{ start: MIN_DAY, end: MIN_DAY + duration }],
        fallback,
        width,
      );
      const headers = timelineHeaders(window);
      assert.ok(headers.major.length + headers.minor.length < 100, `${duration} days / ${width}px`);
      assert.ok(window.width <= width);
    }
  }
});
