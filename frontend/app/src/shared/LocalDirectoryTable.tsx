import { type ReactNode, useEffect, useLayoutEffect, useRef, useState } from 'react';
import {
  DirectoryColumnManager,
  useDirectoryColumns,
  type DirectoryColumn,
} from './DirectoryColumns';
import { Dropdown } from './Dropdown';
import { EmptyState } from './EmptyState';
import { Icon } from './Icon';
import { Resize } from './table';
import { ViewToolbar } from '../spaces/ViewToolbar';

export interface LocalDirectoryColumn extends DirectoryColumn {
  filterable?: boolean;
}
export interface LocalDirectoryRow<K extends string | number> {
  id: K;
  label: string;
  values: Record<string, string>;
  sortValues?: Record<string, string>;
  cells?: Record<string, ReactNode>;
}

const selectionColumn = { key: 'select', label: 'Zaznaczenie', icon: '', width: 40 };
const normalize = (value: string) =>
  value
    .toLocaleLowerCase('pl')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/ł/g, 'l');

/** The tag directory's sheet and controls for small, already loaded settings lists. */
export function LocalDirectoryTable<K extends string | number>({
  columns,
  rows,
  segment,
  label,
  searchLabel,
  emptyLabel,
  selected,
  onSelect,
  busy,
  controls,
  children,
}: {
  columns: LocalDirectoryColumn[];
  rows: LocalDirectoryRow<K>[];
  segment: string;
  label: string;
  searchLabel: string;
  emptyLabel: string;
  selected: Set<K>;
  onSelect: (next: Set<K>) => void;
  busy: boolean;
  controls?: ReactNode;
  children?: ReactNode;
}) {
  const [query, setQuery] = useState('');
  const [sort, setSort] = useState('');
  const [filters, setFilters] = useState<Record<string, string>>({});
  const all = useRef<HTMLInputElement>(null);
  const aggregate = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    const close = (event: Event) => {
      if (!aggregate.current?.contains(event.target as Node))
        aggregate.current?.removeAttribute('open');
    };
    const escape = (event: KeyboardEvent) => {
      if (
        event.key === 'Escape' &&
        aggregate.current?.open &&
        !aggregate.current.querySelector('.tasks-filter-dropdown.is-open')
      ) {
        aggregate.current.removeAttribute('open');
        aggregate.current.querySelector('summary')?.focus();
      }
    };
    document.addEventListener('click', close);
    document.addEventListener('keydown', escape);
    return () => {
      document.removeEventListener('click', close);
      document.removeEventListener('keydown', escape);
    };
  }, []);
  const sizing = useDirectoryColumns([selectionColumn, ...columns], segment);
  const filtered = !!query || Object.values(filters).some(Boolean);
  const visible = rows.filter(
    (row) =>
      (!query ||
        normalize(Object.values(row.values).join(' ')).includes(normalize(query.trim()))) &&
      Object.entries(filters).every(([key, value]) => !value || row.values[key] === value),
  );
  const [sortKey, direction] = sort.split(':');
  if (sortKey)
    visible.sort(
      (left, right) =>
        (left.sortValues?.[sortKey] ?? left.values[sortKey] ?? '').localeCompare(
          right.sortValues?.[sortKey] ?? right.values[sortKey] ?? '',
          'pl',
          {
            numeric: true,
          },
        ) * (direction === 'desc' ? -1 : 1),
    );
  const selectedCount = visible.filter((row) => selected.has(row.id)).length;
  useLayoutEffect(() => {
    if (all.current)
      all.current.indeterminate = selectedCount > 0 && selectedCount < visible.length;
    if (!busy && selectedCount !== selected.size)
      onSelect(new Set(visible.filter((row) => selected.has(row.id)).map((row) => row.id)));
  }, [selectedCount, visible.length, selected, busy, onSelect]);
  const sortOptions = [
    { value: '', label: 'Kolejność domyślna', icon: 'list-ordered' },
    ...columns.flatMap((column) =>
      (['asc', 'desc'] as const).map((order) => ({
        value: `${column.key}:${order}`,
        label: `${column.label}: ${order === 'asc' ? 'rosnąco' : 'malejąco'}`,
        icon: order === 'asc' ? 'arrow-up-narrow-wide' : 'arrow-down-wide-narrow',
      })),
    ),
  ];
  return (
    <>
      <ViewToolbar
        className="settings-directory-toolbar app-toolbar--embedded"
        actions={children}
        search={
          <form
            className="tasks-search-field work-view-toolbar-search"
            role="search"
            onSubmit={(event) => event.preventDefault()}
          >
            <Icon name="search" />
            <input
              type="search"
              value={query}
              placeholder={searchLabel}
              aria-label={searchLabel}
              autoComplete="off"
              onChange={(event) => {
                setQuery(event.target.value);
                onSelect(new Set());
              }}
            />
            <button type="submit" className="tasks-filter-button" aria-label={searchLabel}>
              <Icon name="arrow-right" />
            </button>
          </form>
        }
      >
        {controls}
        <details
          ref={aggregate}
          className={`tasks-project-filter-builder tasks-directory-filter-aggregate ${Object.values(filters).some(Boolean) ? 'is-active' : ''}`}
        >
          <summary
            className="tasks-filter-button tasks-project-query-trigger"
            aria-label={`Filtrowanie: ${label}`}
          >
            <Icon name="list-filter" />
            <span>Filtruj</span>
            <Icon name="chevron-down" className="tasks-project-query-trigger__chevron" />
          </summary>
          <div
            className="tasks-project-query-panel tasks-directory-filter-aggregate__panel"
            aria-label="Filtry listy"
          >
            <header className="tasks-project-query-panel__header tasks-project-query-panel__header--main">
              <Icon name="list-filter" />
              <strong>Filtry</strong>
            </header>
            <div className="tasks-directory-filter-aggregate__controls">
              {columns
                .filter((column) => column.filterable)
                .map((column) => (
                  <Dropdown
                    key={column.key}
                    label={`Filtr: ${column.label}`}
                    menuClass="tasks-filter-menu--wide"
                    trigger={
                      <>
                        <Icon name={column.icon} />
                        <span>
                          {column.label}
                          {filters[column.key] ? `: ${filters[column.key]}` : ''}
                        </span>
                      </>
                    }
                  >
                    {(close) =>
                      [
                        '',
                        ...new Set(rows.map((row) => row.values[column.key]).filter(Boolean)),
                      ].map((value) => (
                        <button
                          type="button"
                          role="menuitemradio"
                          key={value}
                          aria-checked={(filters[column.key] || '') === value}
                          className={(filters[column.key] || '') === value ? 'is-active' : ''}
                          onClick={() => {
                            setFilters((current) => ({ ...current, [column.key]: value }));
                            onSelect(new Set());
                            close();
                          }}
                        >
                          <span>{value || 'Wszystko'}</span>
                        </button>
                      ))
                    }
                  </Dropdown>
                ))}
              {Object.values(filters).some(Boolean) ? (
                <button
                  type="button"
                  className="tasks-filter-button"
                  onClick={() => {
                    setFilters({});
                    onSelect(new Set());
                  }}
                >
                  Wyczyść filtry
                </button>
              ) : null}
            </div>
          </div>
        </details>
        <Dropdown
          label={`Sortowanie: ${sortOptions.find((option) => option.value === sort)?.label}`}
          className="tasks-sort-dropdown"
          menuClass="tasks-sort-menu"
          triggerClassName="tasks-filter-button tasks-project-query-trigger"
          trigger={
            <>
              <Icon name="arrow-up-down" />
              <span>Sortuj</span>
              <span className="tasks-project-sort-current">
                {sortOptions.find((option) => option.value === sort)?.label}
              </span>
              <Icon name="chevron-down" className="tasks-project-query-trigger__chevron" />
            </>
          }
        >
          {(close) =>
            sortOptions.map((option) => (
              <button
                type="button"
                role="menuitemradio"
                key={option.value}
                aria-checked={sort === option.value}
                className={sort === option.value ? 'is-active' : ''}
                onClick={() => {
                  setSort(option.value);
                  close();
                }}
              >
                <Icon name={option.icon} />
                <span>{option.label}</span>
              </button>
            ))
          }
        </Dropdown>
        <DirectoryColumnManager
          columns={[selectionColumn, ...columns]}
          layout={sizing.layout}
          save={sizing.saveLayout}
          reset={sizing.reset}
        />
      </ViewToolbar>
      <div
        className={`tasks-table-wrap tasks-board tasks-directory-board tasks-directory-sheet tasks-tag-sheet tasks-spreadsheet-sheet tasks-directory-menu-sheet settings-directory-sheet app-data-table${visible.length ? '' : ' tasks-tag-board--empty'}`}
        style={sizing.style}
        role="region"
        aria-label={`${label} — tabela`}
        tabIndex={0}
        onKeyDown={(event) => {
          if (event.target !== event.currentTarget || busy) return;
          if ((event.ctrlKey || event.metaKey) && event.key === 'a') {
            event.preventDefault();
            onSelect(new Set(visible.map((row) => row.id)));
          } else if (event.key === 'Escape') onSelect(new Set());
        }}
      >
        <section
          className="tasks-issue-group tasks-directory-group"
          role="table"
          aria-label={label}
        >
          <div
            className="tasks-directory-header tasks-directory-sheet__header tasks-tag-sheet__header app-table-header"
            role="row"
          >
            {sizing.visible.map((column) => (
              <span
                key={column.key}
                className={`tasks-directory-sheet__cell tasks-tag-sheet__cell${column.key === 'select' ? ' tasks-directory-header-select' : ''}`}
                data-column={column.key}
                role="columnheader"
                aria-sort={
                  sortKey === column.key
                    ? direction === 'desc'
                      ? 'descending'
                      : 'ascending'
                    : undefined
                }
              >
                {column.key === 'select' ? (
                  <input
                    ref={all}
                    type="checkbox"
                    className="tasks-row-checkbox"
                    aria-label="Zaznacz wszystkie widoczne pozycje"
                    disabled={busy || !visible.length}
                    checked={visible.length > 0 && selectedCount === visible.length}
                    onChange={(event) =>
                      onSelect(
                        event.target.checked ? new Set(visible.map((row) => row.id)) : new Set(),
                      )
                    }
                  />
                ) : (
                  <>
                    {column.label.toLocaleUpperCase('pl')}
                    <Icon name={column.icon} />
                    <Resize
                      column={column}
                      width={sizing.widths[column.key] || column.width}
                      resize={sizing.resize}
                    />
                  </>
                )}
              </span>
            ))}
          </div>
          <div
            className="tasks-issue-list tasks-section-list tasks-directory-list tasks-tag-list"
            role="rowgroup"
          >
            {visible.map((row) => (
              <div
                key={row.id}
                className={`tasks-issue-row tasks-section-row tasks-all-groups-row tasks-directory-row tasks-directory-sheet__row tasks-tag-sheet__row app-table-row${selected.has(row.id) ? ' checked' : ''}`}
                role="row"
              >
                {sizing.visible.map((column) =>
                  column.key === 'select' ? (
                    <input
                      key={column.key}
                      type="checkbox"
                      className="tasks-row-checkbox tasks-directory-sheet__cell tasks-tag-sheet__cell"
                      data-column="select"
                      aria-label={`Zaznacz: ${row.label}`}
                      disabled={busy}
                      checked={selected.has(row.id)}
                      onChange={(event) => {
                        const next = new Set(selected);
                        if (event.target.checked) next.add(row.id);
                        else next.delete(row.id);
                        onSelect(next);
                      }}
                    />
                  ) : (
                    <span
                      key={column.key}
                      className="tasks-directory-sheet__cell tasks-tag-sheet__cell"
                      data-column={column.key}
                      role="cell"
                      title={row.values[column.key]}
                    >
                      {row.cells?.[column.key] ?? (
                        <span className="workplace-team__name">
                          {row.values[column.key] || '—'}
                        </span>
                      )}
                    </span>
                  ),
                )}
              </div>
            ))}
            {!visible.length ? (
              <EmptyState
                className="tasks-tag-empty-state"
                illustration="tasks"
                title={filtered ? 'Nie znaleziono wyników.' : emptyLabel}
                description={
                  filtered ? 'Zmień lub wyczyść filtry, aby zobaczyć inne wyniki.' : undefined
                }
              />
            ) : null}
          </div>
        </section>
      </div>
    </>
  );
}
