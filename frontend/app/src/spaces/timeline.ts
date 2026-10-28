export type TimelineScale = 'weeks' | 'months' | 'quarters';

/** Task dates include both their first and last day. */
export interface DayRange {
  start: number;
  end: number;
}

/** Calendar windows and header segments have an exclusive end boundary. */
export interface TimelineWindow extends DayRange {
  scale: TimelineScale;
  dayWidth: number;
  days: number;
  width: number;
}

export interface TimelineSegment extends DayRange {
  left: number;
  width: number;
  label: string;
  title: string;
  weekend: boolean;
}

const DAY_MS = 86400000;
export const MIN_DAY = -719162; // 0001-01-01, matching Django's date range.
export const MAX_DAY = 2932896; // 9999-12-31.
export const timelineScales: { value: TimelineScale; label: string; dayWidth: number }[] = [
  { value: 'weeks', label: 'Tygodnie', dayWidth: 36 },
  { value: 'months', label: 'Miesiące', dayWidth: 12 },
  { value: 'quarters', label: 'Kwartały', dayWidth: 4 },
];

const date = (day: number) => new Date(day * DAY_MS);
const clamp = (value: number, minimum: number, maximum: number) =>
  Math.max(minimum, Math.min(maximum, value));

/** Parse calendar dates only; Date's permissive rollover must never change a saved date. */
export function parseDay(value: string | null | undefined): number | null {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value) || value.startsWith('0000-')) return null;
  const timestamp = Date.parse(`${value}T00:00:00.000Z`);
  if (!Number.isFinite(timestamp)) return null;
  const parsed = new Date(timestamp);
  return parsed.toISOString().slice(0, 10) === value ? timestamp / DAY_MS : null;
}

export function dayKey(day: number): string {
  if (!Number.isInteger(day) || day < MIN_DAY || day > MAX_DAY)
    throw new RangeError('Data jest poza obsługiwanym zakresem.');
  return date(day).toISOString().slice(0, 10);
}

export function dayLabel(day: number): string {
  return date(day).toLocaleDateString('pl-PL', {
    timeZone: 'UTC',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
}

export function todayDay(timeZone = 'Europe/Warsaw'): number {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(new Date());
  const part = (type: string) => parts.find((item) => item.type === type)!.value;
  return parseDay(`${part('year')}-${part('month')}-${part('day')}`)!;
}

// UTC setters also handle years 1–99 correctly, unlike Date.UTC(year, ...).
function calendarDay(year: number, month: number, day = 1): number {
  const value = new Date(0);
  value.setUTCFullYear(year, month, day);
  value.setUTCHours(0, 0, 0, 0);
  return value.getTime() / DAY_MS;
}

function weekStart(day: number): number {
  return day - ((date(day).getUTCDay() + 6) % 7);
}

function monthStart(day: number, offset = 0): number {
  const value = date(day);
  return calendarDay(value.getUTCFullYear(), value.getUTCMonth() + offset);
}

function quarterStart(day: number, offset = 0): number {
  const value = date(day);
  return calendarDay(value.getUTCFullYear(), Math.floor(value.getUTCMonth() / 3) * 3 + offset * 3);
}

function addMonths(day: number, count: number): number {
  const value = date(day);
  const first = monthStart(day, count);
  const last = monthStart(first, 1) - 1;
  return clamp(first + Math.min(value.getUTCDate(), date(last).getUTCDate()) - 1, MIN_DAY, MAX_DAY);
}

export function timelineWindow(scale: TimelineScale, anchor: number): TimelineWindow {
  const bounded = clamp(Math.round(anchor), MIN_DAY, MAX_DAY);
  const start =
    scale === 'weeks'
      ? weekStart(bounded) - 14
      : scale === 'months'
        ? monthStart(bounded, -1)
        : quarterStart(bounded, -1);
  const end = scale === 'weeks' ? start + 84 : monthStart(start, scale === 'months' ? 8 : 24);
  const safeStart = Math.max(MIN_DAY, start);
  const safeEnd = Math.min(MAX_DAY + 1, end);
  const dayWidth = timelineScales.find((item) => item.value === scale)!.dayWidth;
  return {
    scale,
    start: safeStart,
    end: safeEnd,
    days: safeEnd - safeStart,
    dayWidth,
    width: (safeEnd - safeStart) * dayWidth,
  };
}

export function shiftAnchor(anchor: number, scale: TimelineScale, direction: number): number {
  const step = Math.trunc(direction);
  return scale === 'weeks'
    ? clamp(anchor + step * 28, MIN_DAY, MAX_DAY)
    : addMonths(anchor, step * (scale === 'months' ? 3 : 12));
}

type HeaderUnit = 'day' | 'week' | 'month' | 'quarter' | 'year' | number;

function segments(
  window: TimelineWindow,
  unit: HeaderUnit,
  start = window.start,
): TimelineSegment[] {
  const output: TimelineSegment[] = [];
  let cursor = start;
  while (cursor < window.end) {
    const current = date(cursor);
    let end: number;
    let label: string;
    if (typeof unit === 'number') {
      const firstYear = Math.floor(current.getUTCFullYear() / unit) * unit;
      const lastYear = Math.min(9999, firstYear + unit - 1);
      end = calendarDay(firstYear + unit, 0);
      label =
        unit === 1 ? String(current.getUTCFullYear()) : `${Math.max(1, firstYear)}–${lastYear}`;
    } else if (unit === 'day') {
      end = cursor + 1;
      label = String(current.getUTCDate());
    } else if (unit === 'week') {
      end = weekStart(cursor) + 7;
      label = current.toLocaleDateString('pl-PL', {
        timeZone: 'UTC',
        day: 'numeric',
        month: 'short',
      });
    } else if (unit === 'year') {
      end = calendarDay(current.getUTCFullYear() + 1, 0);
      label = String(current.getUTCFullYear());
    } else if (unit === 'quarter') {
      end = quarterStart(cursor, 1);
      label = `${['I', 'II', 'III', 'IV'][Math.floor(current.getUTCMonth() / 3)]} kwartał`;
    } else {
      end = monthStart(cursor, 1);
      label = current.toLocaleDateString('pl-PL', {
        timeZone: 'UTC',
        month: 'long',
        year: 'numeric',
      });
    }
    end = Math.min(end, window.end);
    output.push({
      start: cursor,
      end,
      left: (cursor - window.start) * window.dayWidth,
      width: (end - cursor) * window.dayWidth,
      label,
      title: end === cursor + 1 ? dayLabel(cursor) : `${dayLabel(cursor)} – ${dayLabel(end - 1)}`,
      weekend: unit === 'day' && [0, 6].includes(current.getUTCDay()),
    });
    cursor = end;
  }
  return output;
}

export function timelineHeaders(
  window: TimelineWindow,
  leadingWidth = 0,
): {
  major: TimelineSegment[];
  minor: TimelineSegment[];
} {
  // Fitted windows may cover millennia. Choose calendar units before building
  // the arrays, so neither the DOM nor this calculation grows with every day.
  // Leading dates extend the header without changing units or the calendar origin.
  const start = Math.max(
    MIN_DAY,
    window.start - Math.ceil(Math.max(0, leadingWidth) / window.dayWidth),
  );
  const standard =
    window.scale === 'weeks' && window.days <= 84
      ? { major: 'month' as const, minor: 'day' as const }
      : window.scale !== 'quarters' && window.days <= 480
        ? { major: 'month' as const, minor: 'week' as const }
        : window.scale !== 'quarters' && window.days <= 2200
          ? { major: 'year' as const, minor: 'month' as const }
          : window.scale === 'quarters' && window.days <= 7000 && window.dayWidth * 90 >= 60
            ? { major: 'year' as const, minor: 'quarter' as const }
            : null;
  if (standard)
    return {
      major: segments(window, standard.major, start),
      minor: segments(window, standard.minor, start),
    };
  const years = date(window.end - 1).getUTCFullYear() - date(window.start).getUTCFullYear() + 1;
  const targetCount = Math.max(2, Math.min(48, Math.floor(window.width / 70)));
  const desiredStep = Math.max(1, years / targetCount);
  const power = 10 ** Math.floor(Math.log10(desiredStep));
  const step = [1, 2, 5, 10].find((value) => value * power >= desiredStep)! * power;
  return {
    major: segments(window, step * 5, start),
    minor: segments(window, step, start),
  };
}

export function taskGeometry(
  range: DayRange,
  window: TimelineWindow,
): { left: number; width: number; clippedStart: boolean; clippedEnd: boolean } | null {
  if (range.end < range.start || range.end < window.start || range.start >= window.end) return null;
  const start = Math.max(range.start, window.start);
  const end = Math.min(range.end + 1, window.end);
  return {
    left: (start - window.start) * window.dayWidth,
    width: (end - start) * window.dayWidth,
    clippedStart: range.start < window.start,
    clippedEnd: range.end >= window.end,
  };
}

/** Moving preserves duration; resizing cannot cross the opposite inclusive edge. */
export function shiftTask(
  range: DayRange,
  delta: number,
  mode: 'move' | 'start' | 'end',
  bounds: DayRange = { start: MIN_DAY, end: MAX_DAY },
): DayRange {
  const step = Number.isFinite(delta) ? Math.round(delta) : 0;
  const minimum = Math.max(MIN_DAY, bounds.start);
  const maximum = Math.min(MAX_DAY, bounds.end);
  if (mode === 'start')
    return { start: clamp(range.start + step, minimum, range.end), end: range.end };
  if (mode === 'end')
    return { start: range.start, end: clamp(range.end + step, range.start, maximum) };
  const movement = clamp(step, minimum - range.start, maximum - range.end);
  return { start: range.start + movement, end: range.end + movement };
}

export function fitTimeline(
  ranges: DayRange[],
  fallback: number,
  availableWidth?: number,
): { scale: TimelineScale; anchor: number } {
  const valid = ranges.filter(
    (range) =>
      Number.isFinite(range.start) && Number.isFinite(range.end) && range.start <= range.end,
  );
  if (!valid.length) return { scale: 'weeks', anchor: fallback };
  const first = Math.min(...valid.map((range) => range.start));
  const last = Math.max(...valid.map((range) => range.end));
  const span = last - first + 1;
  for (const { value: scale, dayWidth } of timelineScales) {
    const anchor =
      scale === 'weeks'
        ? first + 14
        : scale === 'months'
          ? monthStart(first, 1)
          : quarterStart(first, 1);
    const window = timelineWindow(scale, anchor);
    const fitsWidth = !availableWidth || span * dayWidth <= availableWidth;
    if (scale === 'quarters' || (window.start <= first && last < window.end && fitsWidth))
      return { scale, anchor: clamp(anchor, MIN_DAY, MAX_DAY) };
  }
  return { scale: 'quarters', anchor: fallback };
}

/** Fit all dates at once; calendar navigation keeps using timelineWindow. */
export function fittedTimelineWindow(
  ranges: DayRange[],
  fallback: number,
  availableWidth: number,
): TimelineWindow {
  const valid = ranges.filter(
    (range) =>
      Number.isInteger(range.start) &&
      Number.isInteger(range.end) &&
      range.start >= MIN_DAY &&
      range.end <= MAX_DAY &&
      range.start <= range.end,
  );
  if (!valid.length) return timelineWindow('weeks', fallback);
  const first = Math.min(...valid.map((range) => range.start));
  const last = Math.max(...valid.map((range) => range.end));
  const span = last - first + 1;
  // Each side gets >=3% of the complete fitted range, rounded to whole days.
  // The first/last supported date cannot have padding beyond Django's limits.
  const padding = Math.max(1, Math.ceil((span * 0.03) / 0.94));
  const start = Math.max(MIN_DAY, first - padding);
  const end = Math.min(MAX_DAY + 1, last + padding + 1);
  const days = end - start;
  const widthLimit = Number.isFinite(availableWidth) ? Math.max(1, availableWidth) : 1000;
  const scale =
    timelineScales.find((candidate) => days * candidate.dayWidth <= widthLimit) ||
    timelineScales[timelineScales.length - 1];
  const width = Math.min(days * scale.dayWidth, widthLimit);
  return {
    start,
    end,
    days,
    width,
    scale: scale.value,
    dayWidth: width / days,
  };
}
