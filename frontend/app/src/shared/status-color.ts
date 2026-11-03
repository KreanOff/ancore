import type { CSSProperties } from 'react';

// The configured color is resolved by Django for each workflow stage.
// Use the same 16% tint as the stage badge in Space settings.
export function statusColorStyle(color?: string): CSSProperties | undefined {
  if (!color || !/^#[0-9a-f]{6}$/i.test(color)) return undefined;
  return {
    '--tasks-status-color': color,
    '--tasks-status-background': `color-mix(in srgb, ${color} 16%, var(--card-bg))`,
    '--tasks-status-border': `color-mix(in srgb, ${color} 30%, var(--card-bg))`,
  } as CSSProperties;
}

export function statusHeaderStyle(color?: string): CSSProperties | undefined {
  const style = statusColorStyle(color);
  return style ? { ...style, borderColor: 'var(--tasks-status-border)' } : undefined;
}
