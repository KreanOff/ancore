import type { CSSProperties } from 'react';

export const DEFAULT_EVENT_COLOR = '#e04f63';

const legacyColors: Record<string, [string, string]> = {
  red: [DEFAULT_EVENT_COLOR, '#fff1f3'],
  blue: ['#4f7edb', '#edf3ff'],
  green: ['#43a36a', '#edf9f1'],
  amber: ['#d79a35', '#fff7e8'],
  slate: ['#7b8493', '#f1f3f6'],
};

export function calendarColor(value?: string) {
  const color = value?.trim().toLowerCase() || '';
  if (/^#[0-9a-f]{6}$/.test(color)) return color;
  return Object.hasOwn(legacyColors, color) ? legacyColors[color][0] : DEFAULT_EVENT_COLOR;
}

export function calendarColorClass(value?: string) {
  return value && Object.hasOwn(legacyColors, value) ? value : 'custom';
}

export function calendarColorStyle(value?: string): CSSProperties {
  const color = calendarColor(value);
  // Keep saved palette colors identical when the editor writes their HEX equivalent.
  const background = Object.values(legacyColors).find(([hex]) => hex === color)?.[1];
  return {
    '--calendar-event-color': color,
    '--calendar-event-bg': background || `color-mix(in srgb, ${color} 10%, #ffffff)`,
    '--calendar-event-ink': 'var(--text-primary)',
  } as CSSProperties;
}
