import type { CSSProperties } from 'react';

export function issueTypeIconStyle(color?: string): CSSProperties | undefined {
  return color && /^#[0-9a-f]{6}$/i.test(color)
    ? ({ '--tasks-type-icon-color': color } as CSSProperties)
    : undefined;
}

export function issueTypeBadgeStyle(color?: string): CSSProperties | undefined {
  if (!color || !/^#[0-9a-f]{6}$/i.test(color)) return undefined;
  return {
    backgroundColor: `color-mix(in srgb, ${color} 16%, #ffffff)`,
    '--tasks-type-icon-color': 'var(--text-primary)',
  } as CSSProperties;
}
