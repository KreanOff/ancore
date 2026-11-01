import type { Item, Status } from './types';

/** Counts describe all visible cards, independently of the current filters. */
export function wipReached(column: Status) {
  return column.wip_limit != null && (column.wip_count ?? 0) >= column.wip_limit;
}

export function boardMoveError(item: Item, column: Status) {
  if (item.status === column.key) return '';
  if (!item.transitions.some((status) => status.key === column.key))
    return 'Przejście do tego statusu nie jest dozwolone.';
  if (wipReached(column)) return 'Limit pracy w toku dla tego etapu został osiągnięty.';
  return '';
}

export function flowAge(value: string | null | undefined, now = Date.now()) {
  if (!value) return '';
  const entered = Date.parse(value);
  if (!Number.isFinite(entered)) return '';
  const hours = Math.floor(Math.max(0, now - entered) / 3_600_000);
  return hours < 1
    ? 'krócej niż godzinę'
    : hours < 24
      ? `${hours} godz.`
      : Math.floor(hours / 24) === 1
        ? '1 dzień'
        : `${Math.floor(hours / 24)} dni`;
}
