import { type ReactNode, useLayoutEffect, useRef, useState } from 'react';
import { Dropdown } from '../shared/Dropdown';
import { Icon } from '../shared/Icon';
import { type Column, type useColumns } from './columns';
import { Resize } from '../shared/table';
import type { Resource } from './types';

function Selection({
  checked,
  partial,
  label,
  onChange,
}: {
  checked: boolean;
  partial?: boolean;
  label: string;
  onChange: (checked: boolean) => void;
}) {
  const ref = useRef<HTMLInputElement>(null);
  useLayoutEffect(() => {
    if (ref.current) ref.current.indeterminate = !!partial;
  }, [partial]);
  return (
    <input
      ref={ref}
      type="checkbox"
      className="tasks-row-checkbox"
      aria-label={label}
      checked={checked}
      onChange={(event) => onChange(event.target.checked)}
    />
  );
}

export function ResourceTable({
  results,
  columns,
  baseUrl,
  search,
  open,
  remove,
  busy,
}: {
  results: Resource[];
  columns: ReturnType<typeof useColumns>;
  baseUrl: string;
  search: string;
  open: (id: number | null) => void;
  remove: (resource: Resource) => void;
  busy: boolean;
}) {
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const selectionCount = results.filter((item) => selected.has(item.id)).length;
  function cell(item: Resource, column: Column): ReactNode {
    switch (column.key) {
      case 'select':
        return (
          <Selection
            label={`Zaznacz zasób ${item.name}`}
            checked={selected.has(item.id)}
            onChange={(checked) =>
              setSelected((current) => {
                const next = new Set(current);
                if (checked) next.add(item.id);
                else next.delete(item.id);
                return next;
              })
            }
          />
        );
      case 'menu':
        return (
          <Dropdown
            label={`Działania: ${item.name}`}
            className="resources-react-row-actions"
            menuClass="documents-item-menu"
            role="group"
            trigger={<Icon name="menu" />}
          >
            {(close) => (
              <div className="documents-menu-actions">
                <button
                  type="button"
                  className="tasks-project-menu-button"
                  disabled={busy}
                  onClick={() => {
                    close();
                    open(item.id);
                  }}
                >
                  <Icon name="pencil" />
                  <span>Edytuj zasób</span>
                </button>
                <button
                  type="button"
                  className="tasks-project-menu-button"
                  disabled={busy}
                  onClick={() => {
                    close();
                    remove(item);
                  }}
                >
                  <Icon name="trash-2" />
                  <span>Usuń zasób</span>
                </button>
              </div>
            )}
          </Dropdown>
        );
      case 'name':
        return (
          <a
            className="resources-name"
            href={`${baseUrl}${item.id}/edit/${search}`}
            aria-haspopup="dialog"
            title={item.name}
            onClick={(event) => {
              if (!event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey) {
                event.preventDefault();
                open(item.id);
              }
            }}
          >
            <Icon name={item.icon} />
            <span>{item.name}</span>
          </a>
        );
      case 'kind':
        return item.kind_label;
      case 'status':
        return item.status_label;
      case 'assigned_to':
        return (
          <>
            <Icon name="circle-user-round" />
            <span>{item.assignee_name}</span>
          </>
        );
      case 'expires_on':
        return item.expires_on ? (
          <span
            className={`tasks-project-value-badge ${item.overdue ? 'tasks-project-value-badge--due-overdue' : ''}`}
            title={item.overdue ? 'Termin minął' : undefined}
          >
            {item.overdue ? <span className="u-sr-only">Termin minął: </span> : null}
            {item.expires_on.split('-').reverse().join('.')}
          </span>
        ) : (
          '—'
        );
      default:
        return item[column.key] || '—';
    }
  }
  return (
    <div
      className="tasks-table-wrap tasks-board tasks-directory-board tasks-directory-sheet tasks-project-sheet tasks-project-sheet--selectable tasks-spreadsheet-sheet tasks-directory-menu-sheet resources-sheet"
      data-directory-resize="false"
      style={columns.style}
    >
      <section className="tasks-directory-group" role="table" aria-label="Lista zasobów">
        <div
          className="tasks-directory-header tasks-directory-sheet__header tasks-project-sheet__header"
          role="row"
        >
          {columns.visible.map((column) => (
            <div
              key={column.key}
              className="tasks-directory-sheet__cell tasks-project-sheet__cell"
              data-column={column.key}
              role="columnheader"
            >
              {column.key === 'select' ? (
                <Selection
                  label="Zaznacz wszystkie zasoby"
                  checked={selectionCount === results.length}
                  partial={selectionCount > 0 && selectionCount < results.length}
                  onChange={(checked) =>
                    setSelected(checked ? new Set(results.map((item) => item.id)) : new Set())
                  }
                />
              ) : column.key === 'menu' ? (
                <span className="u-sr-only">Działania</span>
              ) : (
                <>
                  {column.label.toLocaleUpperCase('pl')}
                  <Icon name={column.icon} />
                  <Resize
                    column={column}
                    width={columns.widths[column.key] || column.width}
                    resize={columns.resize}
                  />
                </>
              )}
            </div>
          ))}
        </div>
        <div className="tasks-issue-list tasks-directory-list" role="rowgroup">
          {results.map((item) => (
            <article
              key={item.id}
              className={`tasks-issue-row tasks-directory-row resources-row ${selected.has(item.id) ? 'checked' : ''}`}
              role="row"
            >
              {columns.visible.map((column) => (
                <div
                  key={column.key}
                  className={`tasks-directory-sheet__cell tasks-project-sheet__cell ${column.key === 'assigned_to' ? 'tasks-directory-assignee' : ''}`}
                  data-column={column.key}
                  role="cell"
                  title={
                    column.key === 'assigned_to'
                      ? item.assignee_name
                      : ['inventory_number', 'location'].includes(column.key)
                        ? String(item[column.key as keyof Resource])
                        : undefined
                  }
                >
                  {cell(item, column)}
                </div>
              ))}
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
