export type View = 'day' | 'week' | 'month' | 'year';
export interface CalendarEvent {
  id: number | string;
  title: string;
  description: string;
  start: string;
  end: string;
  all_day: boolean;
  color: string;
  source: string;
  url?: string;
}
export const colors = [
  ['red', 'Czerwony'],
  ['blue', 'Niebieski'],
  ['green', 'Zielony'],
  ['amber', 'Bursztynowy'],
  ['slate', 'Szary'],
];
export const views: [View, string][] = [
  ['day', 'Dzień'],
  ['week', 'Tydzień'],
  ['month', 'Miesiąc'],
  ['year', 'Rok'],
];
export const weekdays = ['Pon', 'Wto', 'Śro', 'Czw', 'Pią', 'Sob', 'Nie'];
export const day = (date: Date) => new Date(date.getFullYear(), date.getMonth(), date.getDate());
export function addDays(date: Date, count: number) {
  const next = new Date(date);
  next.setDate(next.getDate() + count);
  return next;
}
export const dateKey = (date: Date) =>
  `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
export const localInput = (date: Date) =>
  `${dateKey(date)}T${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
export function weekStart(date: Date) {
  return addDays(day(date), -((date.getDay() + 6) % 7));
}
export function monthBounds(date: Date) {
  const start = weekStart(new Date(date.getFullYear(), date.getMonth(), 1));
  const end = addDays(weekStart(new Date(date.getFullYear(), date.getMonth() + 1, 0)), 7);
  return { start, end };
}
export function bounds(date: Date, view: View) {
  if (view === 'month') return monthBounds(date);
  if (view === 'year')
    return {
      start: new Date(date.getFullYear(), 0, 1),
      end: new Date(date.getFullYear() + 1, 0, 1),
    };
  const start = view === 'week' ? weekStart(date) : day(date);
  return { start, end: addDays(start, view === 'week' ? 7 : 1) };
}
export function periodStep(date: Date, view: View, step: number) {
  if (view === 'day' || view === 'week') return addDays(date, step * (view === 'week' ? 7 : 1));
  const year = date.getFullYear() + (view === 'year' ? step : 0);
  const month = date.getMonth() + (view === 'month' ? step : 0);
  return new Date(year, month, Math.min(date.getDate(), new Date(year, month + 1, 0).getDate()));
}
export const formatDate = (date: Date, long = false) =>
  date.toLocaleDateString('pl-PL', {
    day: 'numeric',
    month: 'long',
    ...(long ? { weekday: 'long' } : {}),
  });
export const time = (date: Date) =>
  date.toLocaleTimeString('pl-PL', { hour: '2-digit', minute: '2-digit' });
export const occurs = (event: CalendarEvent, date: Date) =>
  new Date(event.start) < addDays(day(date), 1) && new Date(event.end) >= day(date);
export function lanes(events: CalendarEvent[], date: Date) {
  const positioned = events
    .filter((event) => !event.all_day && occurs(event, date))
    .map((event) => {
      const start = new Date(event.start),
        end = new Date(event.end);
      const minute = start < day(date) ? 0 : start.getHours() * 60 + start.getMinutes();
      return {
        event,
        start: minute,
        end: Math.min(
          1440,
          Math.max(
            minute + 24,
            end >= addDays(day(date), 1) ? 1440 : end.getHours() * 60 + end.getMinutes(),
          ),
        ),
        lane: 0,
        count: 1,
      };
    })
    .sort((a, b) => a.start - b.start || b.end - a.end);
  let group: typeof positioned = [],
    end = -1;
  const finish = () => {
    const occupied: number[] = [];
    for (const item of group) {
      let index = occupied.findIndex((last) => last <= item.start);
      if (index < 0) index = occupied.length;
      occupied[index] = item.end;
      item.lane = index;
    }
    group.forEach((item) => {
      item.count = occupied.length;
    });
  };
  for (const item of positioned) {
    if (group.length && item.start >= end) {
      finish();
      group = [];
      end = -1;
    }
    group.push(item);
    end = Math.max(end, item.end);
  }
  finish();
  return positioned;
}
