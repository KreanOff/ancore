import {
  DirectoryColumnManager,
  useDirectoryColumns,
  type Layout,
} from '../shared/DirectoryColumns';
export const columns = [
  { key: 'select', label: 'Zaznaczenie', icon: '', width: 40 },
  { key: 'menu', label: 'Działania', icon: 'menu', width: 40 },
  { key: 'inventory_number', label: 'Nr ewidencyjny', icon: 'hash', width: 190 },
  { key: 'name', label: 'Nazwa', icon: 'package', width: 250 },
  { key: 'kind', label: 'Typ', icon: 'shapes', width: 130 },
  { key: 'status', label: 'Status', icon: 'circle-check', width: 140 },
  { key: 'assigned_to', label: 'Odpowiedzialny', icon: 'user-round', width: 245 },
  { key: 'location', label: 'Lokalizacja', icon: 'map-pin', width: 180 },
  { key: 'expires_on', label: 'Ważność / gwarancja', icon: 'calendar-clock', width: 200 },
] as const;
export type Column = (typeof columns)[number];
export function useColumns() {
  return useDirectoryColumns(columns, 'resources');
}
export function ColumnManager(props: {
  layout: Layout;
  save: (value: Layout) => void;
  reset: () => void;
}) {
  return <DirectoryColumnManager columns={columns} {...props} />;
}
