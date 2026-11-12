export const RIGHT_SIDEBAR_MIN = 240;
export const RIGHT_SIDEBAR_MAX = 520;
export const RIGHT_SIDEBAR_STORAGE = 'ancoreRightSidebarWidth';

export function savedRightSidebarWidth(value: unknown): number | null {
  return typeof value === 'number' &&
    Number.isFinite(value) &&
    value >= RIGHT_SIDEBAR_MIN &&
    value <= RIGHT_SIDEBAR_MAX
    ? value
    : null;
}

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

export function sidebarWidths({
  viewport,
  scale,
  gap,
  leftPreference,
  leftCollapsed,
  collapsedWidth,
  rightPreference,
  rightDefault,
  rightVisible,
}: {
  viewport: number;
  scale: number;
  gap: number;
  leftPreference: number;
  leftCollapsed: boolean;
  collapsedWidth: number;
  rightPreference: number | null;
  rightDefault: number;
  rightVisible: boolean;
}) {
  const available = Math.floor(viewport / scale - (rightVisible ? 4 : 3) * gap - 360);
  // Allocate from preferences, never from the other panel's measured/clamped box.
  // This keeps ResizeObserver callbacks stable when both panels meet their limits.
  const preferredLeft = leftCollapsed
    ? collapsedWidth
    : clamp(leftPreference, 220, Math.max(220, Math.min(420, available - RIGHT_SIDEBAR_MIN)));
  const rightMax = rightVisible
    ? clamp(available - preferredLeft, RIGHT_SIDEBAR_MIN, RIGHT_SIDEBAR_MAX)
    : RIGHT_SIDEBAR_MAX;
  const right = clamp(rightPreference ?? rightDefault, RIGHT_SIDEBAR_MIN, rightMax);
  const leftMax = clamp(available - (rightVisible ? right : 0), 220, 420);
  return { left: clamp(leftPreference, 220, leftMax), leftMax, right, rightMax };
}

export function rightSidebarDragWidth(
  startWidth: number,
  startX: number,
  clientX: number,
  scale: number,
  max: number,
) {
  return clamp(startWidth + (startX - clientX) / scale, RIGHT_SIDEBAR_MIN, max);
}
